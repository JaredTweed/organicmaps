#!/usr/bin/env python3
"""Capture the existing Qt screenshot mode with isolated settings and fixed points."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from visual_equivalence import digest
from generate_visual_map import REGION


def capture(binary, fixture_dir, resources, output, sites, themes, densities, software=False):
    from PIL import Image
    if output.exists():
        raise ValueError("Refusing to overwrite visual evidence")
    fixture = json.loads((fixture_dir / "manifest.json").read_text())
    build = json.loads(binary.with_suffix(".json").read_text())
    if build["source_commit"] != fixture["source_commit"] or build["binary_sha256"] != digest(binary):
        raise ValueError("Desktop binary and fixture source do not match")
    map_path = fixture_dir / "maps" / (REGION + ".mwm")
    if digest(map_path) != fixture["map_sha256"]:
        raise ValueError("Map changed")
    for name, expected in fixture["resources"].items():
        if digest(resources / name) != expected:
            raise ValueError("Style/classifier changed: " + name)
    if not sites or len({s["name"] for s in sites}) != len(sites):
        raise ValueError("Expected unique, nonempty sites")
    for site in sites:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", site["name"]):
            raise ValueError("Unsafe site name")
    output.mkdir(parents=True)
    staged = output / "resources"
    staged.mkdir()
    for path in resources.iterdir():
        if path.name != "countries.json":
            (staged / path.name).symlink_to(path.resolve(), target_is_directory=path.is_dir())
    countries = json.loads((resources / "countries.json").read_text())
    pending, matched = [countries], 0
    while pending:
        country = pending.pop()
        if country.get("id") == REGION:
            country["s"] = map_path.stat().st_size
            matched += 1
        pending.extend(country.get("g", []))
    if matched != 1:
        raise ValueError("Ambiguous fixture region")
    (staged / "countries.json").write_text(json.dumps(countries))
    writable = output / "maps"
    version = writable / str(countries["v"])
    version.mkdir(parents=True)
    (version / map_path.name).symlink_to(map_path.resolve())
    for name in ("World.mwm", "WorldCoasts.mwm"):
        (writable / name).symlink_to((resources / name).resolve())
    width, height = 1008, 720
    result = {"source_commit": fixture["source_commit"], "map_sha256": fixture["map_sha256"],
              "binary_sha256": build["binary_sha256"], "assets_sha256": fixture["resources"],
              "device": os.uname().nodename + (":Qt-software" if software else ":Qt-desktop"), "fixtures": [],
              "actual_backends": {}, "image_sha256": {}, "roi": [0, 0, width, height],
              "shutdown_cleanup": {}}
    for theme in themes:
        for density in densities:
            group = f"{theme}-dpi{density}"
            config = output / (group + "-config")
            settings_dir = config / "OMaps"
            settings_dir.mkdir(parents=True)
            settings = ("EulaAccepted=true\nMapStyleMode=Cycling\n"
                        f"MapStyleKeyV1=MapStyleCycling{theme.title()}\n")
            cases = [{**site, "theme": theme, "density": density, "backend": "OpenGLES3",
                      "name": f"{site['name']}-{group}"} for site in sites]
            points = ";".join(f"{s['lat']},{s['lon']},{s['zoom']}" for s in sites)
            for suffix in ("", ".repeat"):
                (settings_dir / "settings.ini").write_text(settings)
                destination = output / (group + suffix)
                destination.mkdir()
                args = [str(binary), "--data_path=" + str(writable), "--resources_path=" + str(staged),
                        "--points=" + points, "--dst_path=" + str(destination), "--lang=en",
                        f"--width={width}", f"--height={height}", f"--dpi_scale={density}"]
                log_path = output / (group + suffix + ".log")
                terminated = False
                environment = {**os.environ, "XDG_CONFIG_HOME": str(config), "QT_QPA_PLATFORM": "xcb",
                               "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent/organicmaps-audit"}
                if software:
                    environment.update(LIBGL_ALWAYS_SOFTWARE="1", LP_NUM_THREADS="1")
                with log_path.open("w") as log:
                    process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                                               env=environment)
                    try:
                        deadline = time.monotonic() + 300
                        while process.poll() is None and time.monotonic() < deadline:
                            if "state: Done" in log_path.read_text():
                                try:
                                    process.wait(timeout=10)
                                except subprocess.TimeoutExpired:
                                    terminated = True
                                    process.terminate()
                                    process.wait(timeout=10)
                                break
                            time.sleep(.5)
                        if process.poll() is None:
                            raise TimeoutError("Screenshot mode did not finish")
                        if process.returncode and not terminated:
                            raise subprocess.CalledProcessError(process.returncode, args)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                result["shutdown_cleanup"][group + suffix] = terminated
                log_text = log_path.read_text()
                if "state: Done" not in log_text:
                    raise ValueError("Screenshot mode never reported completion")
                if "Location updated with valid coordinates" in log_text or "Registering downloaded file" in log_text:
                    raise ValueError("Uncontrolled location or downloaded map invalidates fixed-camera evidence")
                apis = set(re.findall(r"Api = (OpenGLES3|Vulkan)", log_text))
                if apis != {"OpenGLES3"}:
                    raise ValueError("Actual OpenGL backend was not verified: " + str(apis))
                if software and "llvmpipe" not in log_text:
                    raise ValueError("Software rendering was requested but not verified")
                images = sorted(destination.glob("*.png"))
                if len(images) != len(cases):
                    raise ValueError("Screenshot mode did not complete all fixtures")
                for case, image in zip(cases, images):
                    target = output / (case["name"] + suffix + ".png")
                    shutil.copyfile(image, target)
                    with Image.open(target) as bitmap:
                        if bitmap.size != (width, height) or len(bitmap.convert("RGB").getcolors(width * height) or []) < 10:
                            raise ValueError("Blank or incorrectly sized screenshot")
                    result["image_sha256"][target.name] = digest(target)
                    result["actual_backends"][case["name"]] = "OpenGLES3"
                    (output / (case["name"] + ".settings.ini")).write_text(
                        settings + json.dumps(case, sort_keys=True) + "\n")
            result["fixtures"].extend(cases)
            (output / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
            print("Captured " + group, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "fixture", "resources", "output", "sites"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--themes", nargs="+", choices=("light", "dark"), default=["light", "dark"])
    parser.add_argument("--densities", nargs="+", type=float, default=[1.0, 2.0])
    parser.add_argument("--software", action="store_true")
    args = parser.parse_args()
    capture(args.binary.resolve(), args.fixture.resolve(), args.resources.resolve(), args.output.resolve(),
            json.loads(args.sites.read_text()), args.themes, args.densities, args.software)
