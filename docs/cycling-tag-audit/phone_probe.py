#!/usr/bin/env python3
"""Stage and capture an isolated Pixel 8 Pro research build; never reset app data."""

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "app.organicmaps.cyclingresearch.debug"
REGION = "Canada_British Columbia_Vancouver"


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=kwargs.pop("timeout", 120), **kwargs).stdout


def digest(path):
    with path.open("rb") as source:
        result = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
        return result.hexdigest()


def scenario():
    steps = []
    for lat, lon in ((49.2827, -123.1207), (49.2698, -123.1310), (49.2778, -123.1145)):
        for zoom in (14, 16, 18):
            steps += [{"actionType": "centerViewport", "center": {"lat": lat, "lon": lon},
                       "zoomLevel": zoom, "animated": False, "waitForReady": True},
                      {"actionType": "waitForTime", "timeMs": 3000}]
    return {"scenarios": [{"name": "cycling-research-vancouver", "steps": steps}]}


def launcher_from_xml(xml):
    android = "{http://schemas.android.com/apk/res/android}"
    root = ET.fromstring(xml)
    if root.attrib.get("package") != PACKAGE:
        raise ValueError("Packaged manifest has another application ID")
    application = root.find("application")
    if application is not None:
        for component in application:
            if component.tag not in ("activity", "activity-alias"):
                continue
            for intent in component.findall("intent-filter"):
                actions = {item.get(android + "name") for item in intent.findall("action")}
                categories = {item.get(android + "name") for item in intent.findall("category")}
                if ("android.intent.action.MAIN" in actions and "android.intent.category.LAUNCHER" in categories
                        and component.get(android + "enabled") != "false"):
                    name = component.attrib[android + "name"]
                    return PACKAGE + name if name.startswith(".") else name
    raise ValueError("APK has no enabled launcher activity or alias")


def prepare(apk, map_path, bundle, aapt, kothic, apkanalyzer=None):
    if bundle.exists():
        raise ValueError("Bundle output must not already exist")
    if map_path.name != "Vancouver.mwm":
        raise ValueError("This viewport fixture requires Vancouver.mwm")
    badging = run([aapt, "dump", "badging", apk]).decode()
    if not re.search(r"^package: name='" + re.escape(PACKAGE) + r"' ", badging, re.M):
        raise ValueError("Refusing APK with a non-research package")
    if "application-debuggable" not in badging or "arm64-v8a" not in badging:
        raise ValueError("Requires a debuggable ARM64 build")
    launch = re.search(r"^launchable-activity: name='([^']+)'", badging, re.M)
    if launch:
        activity = launch[1]
    else:
        analyzer = apkanalyzer or Path(aapt).resolve().parents[2] / "cmdline-tools/latest/bin/apkanalyzer"
        activity = launcher_from_xml(run([analyzer, "manifest", "print", apk]).decode())
    with zipfile.ZipFile(apk) as archive:
        countries = json.loads(archive.read("assets/countries.json"))
        version = str(int(countries["v"]))
        rules = archive.read("assets/drules_outdoors.bin")
    def leaves(node):
        return {node["id"]} if "g" not in node else set().union(*(leaves(child) for child in node["g"]))
    if REGION not in leaves(countries):
        raise ValueError("The APK catalogue does not include the fixture region")
    bundle.mkdir(parents=True)
    for source in (apk, map_path, Path(__file__).with_name("display-track.kml")):
        shutil.copy2(source, bundle / source.name)
    (bundle / "scenario.json").write_text(json.dumps(scenario(), indent=2) + "\n")
    (bundle / "badging.txt").write_text(badging)
    from clean_style import compile_pair
    compile_pair(rules, kothic, bundle)
    manifest = {"package": PACKAGE, "activity": activity, "map_directory": version,
                "map_filename": REGION + ".mwm",
                "scope": "baseline functional capture, not candidate A/B or release performance",
                "apk": apk.name, "map": map_path.name,
                "sha256": {p.name: digest(p) for p in bundle.iterdir() if p.is_file()}}
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest["package"] != PACKAGE or not re.fullmatch(r"\d+", manifest["map_directory"]):
        raise ValueError("Unsafe package or map directory")
    if manifest.get("map_filename") != REGION + ".mwm":
        raise ValueError("Unexpected fixture region filename")
    for name, expected in manifest["sha256"].items():
        if Path(name).name != name or digest(bundle / name) != expected:
            raise ValueError(f"Missing, unsafe or changed bundle file: {name}")
    for key in ("apk", "map"):
        if manifest[key] not in manifest["sha256"]:
            raise ValueError("Unsigned bundle input")
    if not re.fullmatch(r"[a-zA-Z0-9_.]+", manifest["activity"]):
        raise ValueError("Unsafe activity")
    return manifest


def viewport_records(log):
    return [json.loads(line.split("DrapeViewport ", 1)[1]) for line in log.splitlines()
            if "DrapeViewport " in line]


def validate_records(records):
    expected = [("cycling-research-vancouver", i) for i in range(9)]
    if [(r.get("scenario"), r.get("index")) for r in records] != expected:
        return False
    return all(r.get("ready") is True and type(r.get("elapsed_ms")) in (int, float)
               and 0 < r["elapsed_ms"] <= 30000 for r in records)


def capture(bundle, output, adb, serial, timeout, style="baseline", theme="light", backend="OpenGLES3"):
    manifest = verify(bundle)
    if output.exists():
        raise ValueError("Capture output must not already exist")
    device = [adb, "-s", serial]

    def adb_text(*args):
        return run(device + list(args)).decode().strip()

    properties = {key: adb_text("shell", "getprop", key) for key in
                  ("ro.product.model", "ro.product.cpu.abi", "ro.build.fingerprint")}
    if properties["ro.product.model"] != "Pixel 8 Pro" or properties["ro.product.cpu.abi"] != "arm64-v8a":
        raise ValueError("Expected an authorized Pixel 8 Pro ARM64 device")
    output.mkdir(parents=True)
    (output / "environment.json").write_text(json.dumps(properties, indent=2) + "\n")
    for service in ("battery", "thermalservice"):
        (output / (service + ".txt")).write_text(adb_text("shell", "dumpsys", service))
    paths = adb_text("shell", "pm", "path", PACKAGE).splitlines()
    identical = False
    if len(paths) == 1 and paths[0].startswith("package:"):
        path = paths[0][len("package:"):]
        if re.fullmatch(r"/[a-zA-Z0-9_./=+~\-]+", path):
            installed = adb_text("shell", "sha256sum", path).split()
            identical = bool(installed and installed[0] == manifest["sha256"][manifest["apk"]])
    install = "Success\nAlready installed with matching SHA-256" if identical else adb_text(
        "install", "-r", str(bundle / manifest["apk"]))
    (output / "install.txt").write_text(install + "\n")
    if "Success" not in install.splitlines():
        raise RuntimeError("Research APK installation failed")
    adb_text("shell", "am", "force-stop", PACKAGE)
    version = manifest["map_directory"]
    if (style not in ("baseline", "clean") or theme not in ("light", "dark")
            or backend not in ("OpenGLES3", "Vulkan")):
        raise ValueError("Unknown style, theme or backend")
    adb_text("shell", f"run-as {PACKAGE} mkdir -p files/{version} files/styles shared_prefs")
    old_name = f"files/{version}/Vancouver.mwm"
    try:
        previous = adb_text("shell", f"run-as {PACKAGE} sha256sum {old_name}").split()
    except subprocess.CalledProcessError:
        previous = []
    if previous:
        if previous[0] != manifest["sha256"][manifest["map"]]:
            raise ValueError("An unrecognized old fixture exists; refusing to replace it")
        adb_text("shell", f"run-as {PACKAGE} rm {old_name}")

    def transfer(source, destination):
        expected = digest(source)
        quoted = shlex.quote(destination)
        try:
            existing = adb_text("shell", f"run-as {PACKAGE} sha256sum {quoted}").split()
            if existing and existing[0] == expected:
                return
        except subprocess.CalledProcessError:
            pass
        with source.open("rb") as stream:
            script = shlex.quote("cat > " + quoted)
            run(device + ["shell", "-T", f"run-as {PACKAGE} sh -c {script}"], stdin=stream)
        actual = adb_text("shell", f"run-as {PACKAGE} sha256sum {quoted}").split()
        if not actual or actual[0] != expected:
            raise RuntimeError(f"Device fixture checksum mismatch: {destination}")

    settings = (f"StoragePath=/data/data/{PACKAGE}/files/\nLastLocationStateMode=NotFollow\n"
                "OutdoorsEnabled=true\n"
                f"MapStyleKeyV1=MapStyleOutdoors{theme.title()}\nUiThemeSettings={'night' if theme == 'dark' else 'default'}\n"
                f"PreferredGraphicsAPI={backend}\nTtsEnabled=false\nKeepScreenOn=true\n")
    (output / "settings.ini").write_text(settings)
    (output / "OrganicMapsPrefs.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?><map>'
        '<boolean name="FirstStartDialogSeen" value="true" /></map>\n')
    for source, target in ((bundle / manifest["map"], f"files/{version}/" + manifest["map_filename"]),
                           (bundle / (style + ".bin"), "files/styles/drules_outdoors.bin"),
                           (bundle / "scenario.json", "files/graphics_benchmark.json"),
                           (output / "settings.ini", "files/settings.ini"),
                           (output / "OrganicMapsPrefs.xml", "shared_prefs/OrganicMapsPrefs.xml")):
        transfer(source, target)
    adb_text("shell", "am", "start", "-W", "-n", PACKAGE + "/" + manifest["activity"])
    pid = adb_text("shell", "pidof", PACKAGE)
    if not pid.isdecimal():
        raise RuntimeError("Research app did not start; unlock phone and inspect startup dialogs")
    deadline = time.monotonic() + timeout
    finished = False
    screenshots = set()
    records = []

    def screenshot(destination):
        png = run(device + ["exec-out", "screencap", "-p"])
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Device screenshot was not a PNG")
        destination.write_bytes(png)

    while time.monotonic() < deadline:
        log = adb_text("logcat", "-d", "--pid=" + pid, "-v", "threadtime")
        (output / "logcat.txt").write_text(log)
        records = viewport_records(log)
        if records:
            index = records[-1].get("index")
            if type(index) is int and 0 <= index < 9 and index not in screenshots:
                screenshot(output / f"viewport-{index:02d}.png")
                screenshots.add(index)
        if "Drape scenario finished:" in log:
            finished = True
            break
        if any(marker in log for marker in ("Drape scenario failed", "FATAL EXCEPTION", "Fatal signal")):
            break
        time.sleep(0.25)
    screenshot(output / "screen.png")
    (output / "memory.txt").write_text(adb_text("shell", "dumpsys", "meminfo", PACKAGE))
    (output / "result.json").write_text(json.dumps({"scenario_finished": finished,
        "style": style, "theme": theme,
        "requested_backend": backend, "actual_backend_requires_log_review": True,
        "outdoors_layer_requested": True,
        "viewport_records": records, "all_viewports_ready": validate_records(records),
        "screenshots_captured": sorted(screenshots),
        "scope": manifest["scope"], "pixel_review_required": True,
        "release_performance_validated": False}, indent=2) + "\n")
    if not finished or not validate_records(records) or len(screenshots) != 9:
        raise RuntimeError("Incomplete capture; inspect screenshot, startup UI and logcat")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("prepare")
    stage.add_argument("--apk", type=Path, required=True)
    stage.add_argument("--map", type=Path, required=True)
    stage.add_argument("--aapt", required=True)
    stage.add_argument("--bundle", type=Path, required=True)
    stage.add_argument("--kothic", type=Path, required=True)
    stage.add_argument("--apkanalyzer", type=Path)
    probe = commands.add_parser("capture")
    probe.add_argument("--bundle", type=Path, required=True)
    probe.add_argument("--output", type=Path, required=True)
    probe.add_argument("--adb", default="adb")
    probe.add_argument("--serial", required=True)
    probe.add_argument("--timeout", type=int, default=180)
    probe.add_argument("--style", choices=("baseline", "clean"), default="baseline")
    probe.add_argument("--theme", choices=("light", "dark"), default="light")
    probe.add_argument("--backend", choices=("OpenGLES3", "Vulkan"), default="OpenGLES3")
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.apk, args.map, args.bundle, args.aapt, args.kothic, args.apkanalyzer), indent=2))
    else:
        capture(args.bundle, args.output, args.adb, args.serial, args.timeout, args.style, args.theme, args.backend)


if __name__ == "__main__":
    main()
