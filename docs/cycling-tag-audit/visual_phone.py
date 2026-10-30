#!/usr/bin/env python3
"""Package native A/B builds and capture the isolated cycling app at saved cameras."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import zipfile

from generate_visual_map import digest, REGION

PACKAGE = os.environ.get("OM_VISUAL_PACKAGE", "app.organicmaps.cyclingfinal.debug")
if PACKAGE not in ("app.organicmaps.cyclingfinal.debug", "app.organicmaps.cyclingsides.debug"):
    raise ValueError("Only explicitly isolated visual-demo packages are permitted")
ACTIVITY = PACKAGE + "/app.organicmaps.SplashActivity"
CORE_ASSETS = ("types.txt", "classificator.txt", "drules_cycling.bin", "colors.txt", "patterns.txt")
REFERENCE_COMMIT = "955cd49403ed025c24beec09f5551e8d274a38ff"


def command(arguments, **kwargs):
    return subprocess.run([str(x) for x in arguments], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=kwargs.pop("timeout", 120), **kwargs).stdout


def asset_hashes(archive):
    result = {}
    for name in archive.namelist():
        if name.startswith("assets/") and not name.endswith("/") and name != "assets/countries.json":
            with archive.open(name) as stream:
                result[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def validate_map_reuse(native, fixture):
    if native["commit"] == fixture["source_commit"]:
        return
    if PACKAGE != "app.organicmaps.cyclingsides.debug" or \
            native.get("map_source_commit") != fixture["source_commit"] or not native.get("source_root"):
        raise ValueError("Native/map source provenance mismatch")
    for revision in (native["commit"], fixture["source_commit"]):
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("Map reuse requires full source pins")
    changed = command(["git", "diff", "--name-only", fixture["source_commit"], native["commit"], "--"],
                      cwd=native["source_root"]).decode().splitlines()
    if any(not path.startswith(("libs/drape_frontend/", "docs/")) for path in changed):
        raise ValueError("Map reuse is allowed only for renderer/documentation-only prototype changes")


def package(shell, library, native_manifest, map_path, output, build_tools, keystore):
    if output.exists():
        raise ValueError("Refusing to overwrite an APK")
    badging = command([build_tools / "aapt", "dump", "badging", shell]).decode()
    if f"package: name='{PACKAGE}' " not in badging or "application-debuggable" not in badging:
        raise ValueError("Only the selected isolated debug package is permitted")
    native = json.loads(native_manifest.read_text())
    fixture = json.loads((map_path.parent.parent / "manifest.json").read_text())
    if native["native_sha256"] != digest(library):
        raise ValueError("Native/map source provenance mismatch")
    validate_map_reuse(native, fixture)
    if fixture["map_sha256"] != digest(map_path):
        raise ValueError("Map changed after generation")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        unsigned, aligned = Path(tmp) / "unsigned.apk", Path(tmp) / "aligned.apk"
        with zipfile.ZipFile(shell) as source, zipfile.ZipFile(unsigned, "w", allowZip64=True) as target:
            assets = asset_hashes(source)
            for name in CORE_ASSETS:
                if assets.get("assets/" + name) != fixture["resources"][name]:
                    raise ValueError(f"Packaged classifier/style mismatch: {name}")
            for info in source.infolist():
                upper = info.filename.upper()
                if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
                    continue
                if info.filename == "lib/arm64-v8a/liborganicmaps.so":
                    with library.open("rb") as inp, target.open(info, "w") as out:
                        shutil.copyfileobj(inp, out, 1024 * 1024)
                elif info.filename == "assets/countries.json":
                    catalogue = json.loads(source.read(info))
                    def update(node):
                        if node.get("id") == REGION:
                            node["s"] = map_path.stat().st_size
                            return 1
                        return sum(update(child) for child in node.get("g", []))
                    if update(catalogue) != 1:
                        raise ValueError("Expected exactly one fixture catalogue entry")
                    target.writestr(info, json.dumps(catalogue, separators=(",", ":")))
                else:
                    with source.open(info) as inp, target.open(info, "w") as out:
                        shutil.copyfileobj(inp, out, 1024 * 1024)
        command([build_tools / "zipalign", "-P", "16", "4", unsigned, aligned])
        command([build_tools / "apksigner", "sign", "--ks", keystore, "--ks-key-alias", "debug",
                 "--ks-pass", "pass:12345678", "--key-pass", "pass:12345678", "--out", output, aligned])
        command([build_tools / "apksigner", "verify", output])
    with zipfile.ZipFile(output) as archive:
        if asset_hashes(archive) != assets:
            raise ValueError("Packaged assets changed while replacing native code")
        with archive.open("lib/arm64-v8a/liborganicmaps.so") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != native["native_sha256"]:
                raise ValueError("Packaged native library mismatch")
    manifest = {"package": PACKAGE, "source_commit": native["commit"],
                "map_source_commit": fixture["source_commit"], "apk_sha256": digest(output),
                "native_sha256": native["native_sha256"], "map_sha256": fixture["map_sha256"],
                "assets_sha256": assets, "shell_apk_sha256": digest(shell), "map": str(map_path)}
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")


def settings(fixture, viewport=""):
    if fixture["theme"] not in ("light", "dark") or fixture["backend"] not in ("OpenGLES3", "Vulkan"):
        raise ValueError("Unsupported theme/backend")
    if viewport and (not viewport.startswith("ScreenClipRect=") or "\n" in viewport):
        raise ValueError("Invalid serialized camera")
    mode = fixture.get("mode", "Cycling")
    if mode not in ("Cycling", "Default"):
        raise ValueError("Unsupported prototype style mode")
    return (f"StoragePath=/data/data/{PACKAGE}/files/\nLastLocationStateMode=NotFollow\n"
            f"MapStyleMode={mode}\nMapStyleKeyV1=MapStyle{mode}{fixture['theme'].title()}\n"
            f"UiThemeSettings={'night' if fixture['theme'] == 'dark' else 'default'}\n"
            f"PreferredGraphicsAPI={fixture['backend']}\nTtsEnabled=false\nDebugInfo=false\nKeepScreenOn=true\n"
            + (viewport + "\n" if viewport else ""))


def backend_from_log(log):
    values = set(re.findall(r"\bApi = (OpenGLES3|Vulkan)\b", log))
    if len(values) != 1:
        raise ValueError("No unambiguous actual graphics backend in native log")
    return values.pop()


def stabilize_camera(viewport, restore, attempts=4):
    history = [viewport]
    for _ in range(attempts):
        actual = restore(viewport)
        history.append(actual)
        if actual == viewport:
            return actual, history
        viewport = actual
    raise ValueError("Reference camera serialization does not reach a fixed point")


def unlocked_foreground(focus, policy):
    locked = re.search(r"\n\s+showing=(true|false)\b", policy)
    windows = re.finditer(r"(?ms)^  Window #\d+ (Window\{[^\n]*\}):\n(.*?)(?=^  Window #|\Z)", focus)
    for window in windows:
        if re.search(r"VolumeDialog|NotificationShade|InputMethod", window[1]) and \
                re.search(r"\bisOnScreen=true\b", window[2]):
            return False
    return bool(re.search(r"mCurrentFocus=.*" + re.escape(PACKAGE) + r"/", focus) and
                locked is not None and locked[1] == "false")


def capture(apk, fixtures_file, camera_dir, output, serial, prepare_cameras=False, prototype_cameras=False):
    from PIL import Image
    if output.exists():
        raise ValueError("Refusing to overwrite a capture")
    bundle = json.loads(apk.with_suffix(".json").read_text())
    if bundle["package"] != PACKAGE or bundle["apk_sha256"] != digest(apk):
        raise ValueError("APK bundle changed")
    if bundle["map_sha256"] != digest(bundle["map"]):
        raise ValueError("Map bundle changed")
    if prepare_cameras and bundle["source_commit"] != REFERENCE_COMMIT:
        raise ValueError("Only the untouched reference may prepare cameras")
    if prototype_cameras and (PACKAGE != "app.organicmaps.cyclingsides.debug" or prepare_cameras):
        raise ValueError("Prototype cameras require the separate side-offset app and cannot prepare reference cameras")
    may_seed = prepare_cameras or prototype_cameras
    camera_source = bundle["source_commit"] if prototype_cameras else REFERENCE_COMMIT
    fixtures = json.loads(fixtures_file.read_text())
    if not fixtures or len({f["name"] for f in fixtures}) != len(fixtures):
        raise ValueError("Expected nonempty unique fixtures")
    for fixture in fixtures:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", fixture["name"]):
            raise ValueError("Unsafe fixture name")
    device = ["adb", "-s", serial]
    def adb(*args, **kwargs):
        return command(device + list(args), **kwargs)
    def text(*args):
        return adb(*args).decode().strip()
    if text("get-state") != "device" or text("shell", "getprop", "ro.product.model") != "Pixel 8 Pro":
        raise ValueError("Expected the authorized Pixel 8 Pro")
    output.mkdir(parents=True)
    camera_dir.mkdir(parents=True, exist_ok=True)
    # Preserve the isolated demo's settings, without clearing its data or
    # touching the normal Organic Maps application.
    for remote, name in (("files/settings.ini", "previous-settings.ini"),
                         ("shared_prefs/OrganicMapsPrefs.xml", "previous-prefs.xml")):
        try:
            (output / name).write_bytes(adb("exec-out", "run-as", PACKAGE, "cat", remote))
        except subprocess.CalledProcessError:
            pass
    command(device + ["install", "-r", apk])
    for permission in ("ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION"):
        adb("shell", "pm", "grant", PACKAGE, "android.permission." + permission)
    adb("shell", "am", "force-stop", PACKAGE)
    with zipfile.ZipFile(apk) as archive:
        version = str(int(json.loads(archive.read("assets/countries.json"))["v"]))
    adb("shell", "run-as", PACKAGE, "mkdir", "-p", "files/" + version, "shared_prefs", "files/styles")
    overrides = text("shell", "run-as", PACKAGE, "find", "files/styles", "-type", "f")
    if overrides:
        raise ValueError("Uncontrolled style overrides exist in the demo app")
    def transfer(data, destination):
        remote = "run-as " + PACKAGE + " sh -c " + shlex.quote("cat > " + shlex.quote(destination))
        adb("shell", "-T", remote, input=data)
    remote_map = f"files/{version}/{REGION}.mwm"
    transfer(Path(bundle["map"]).read_bytes(), remote_map)
    if text("shell", f"run-as {PACKAGE} sha256sum {shlex.quote(remote_map)}").split()[0] != bundle["map_sha256"]:
        raise ValueError("Installed map checksum mismatch")
    transfer(b'<?xml version="1.0" encoding="utf-8"?><map><boolean name="FirstStartDialogSeen" value="true" /></map>\n',
             "shared_prefs/OrganicMapsPrefs.xml")
    result = {**bundle, "device": text("shell", "getprop", "ro.build.fingerprint"),
              "fixtures": fixtures, "actual_backends": {}, "image_sha256": {}, "roi": None}
    def launch(data):
        adb("shell", "am", "force-stop", PACKAGE)
        transfer(data.encode(), "files/settings.ini")
        adb("shell", "am", "start", "-W", "-n", ACTIVITY)
        time.sleep(6)
    def read_viewport(expected=None):
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        time.sleep(1)
        saved = text("shell", "run-as", PACKAGE, "cat", "files/settings.ini")
        values = [line for line in saved.splitlines() if line.startswith("ScreenClipRect=")]
        if len(values) != 1:
            raise ValueError("Viewport was not serialized; cannot certify camera matching")
        if expected and f"MapStyleKeyV1=MapStyle{expected.get('mode', 'Cycling')}{expected['theme'].title()}" not in saved.splitlines():
            raise ValueError("Saved theme differs from the fixture")
        return values[0]
    for fixture in fixtures:
        name = fixture["name"]
        camera_key = f"{fixture['site']}-z{fixture['zoom']}"
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", camera_key):
            raise ValueError("Unsafe camera name")
        camera_file = camera_dir / (camera_key + ".txt")
        stamp_file = camera_dir / (camera_key + ".normalized.json")
        if not camera_file.exists():
            if not may_seed:
                raise ValueError("Reference camera must be prepared first: " + camera_key)
            seed = {**fixture, "theme": "light", "backend": "OpenGLES3"}
            adb("shell", "am", "force-stop", PACKAGE)
            transfer(settings(seed).encode(), "files/settings.ini")
            uri = f"geo:{fixture['lat']},{fixture['lon']}?z={fixture['zoom']}"
            adb("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", uri, "-n", ACTIVITY)
            time.sleep(7)
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(1)
            camera_file.write_text(read_viewport())
        viewport = camera_file.read_text()
        if not stamp_file.exists():
            if not may_seed:
                raise ValueError("Reference camera has not been normalized: " + camera_key)
            seed = {**fixture, "theme": "light", "backend": "OpenGLES3"}
            def restore(value):
                launch(settings(seed, value))
                return read_viewport(seed)
            viewport, history = stabilize_camera(viewport, restore)
            camera_file.write_text(viewport)
            stamp_file.write_text(json.dumps({"source_commit": camera_source, "device": result["device"],
                                              "purpose": "side-offset prototype" if prototype_cameras else "reference comparison",
                                              "viewport_sha256": digest(camera_file), "roundtrips": history}, indent=2) + "\n")
        stamp = json.loads(stamp_file.read_text())
        if stamp["source_commit"] != camera_source or stamp["device"] != result["device"] or \
                stamp["viewport_sha256"] != digest(camera_file):
            raise ValueError("Reference camera provenance changed: " + camera_key)
        data = settings(fixture, viewport)
        (output / (name + ".settings.ini")).write_text(data)
        for suffix in ("", ".repeat"):
            launch(data)
            focus = text("shell", "dumpsys", "window")
            policy = text("shell", "dumpsys", "window", "policy")
            if not unlocked_foreground(focus, policy):
                raise ValueError("The unlocked isolated map must be foreground")
            pid = text("shell", "pidof", PACKAGE)
            if not pid.isdecimal():
                raise ValueError("No unambiguous running app process")
            log = text("logcat", "-d", "--pid=" + pid, "-v", "threadtime")
            (output / (name + suffix + ".log")).write_text(log)
            actual = backend_from_log(log)
            if actual != fixture["backend"]:
                raise ValueError(f"Graphics fallback in {name}: {actual}")
            result["actual_backends"][name] = actual
            screenshot = output / (name + suffix + ".png")
            screenshot.write_bytes(adb("exec-out", "screencap", "-p"))
            after = text("shell", "dumpsys", "window")
            if not unlocked_foreground(after, text("shell", "dumpsys", "window", "policy")):
                raise ValueError("System UI or focus changed during screenshot")
            (output / (name + suffix + ".windows-before.txt")).write_text(focus)
            (output / (name + suffix + ".windows-after.txt")).write_text(after)
            result["image_sha256"][screenshot.name] = digest(screenshot)
            with Image.open(screenshot) as image:
                roi = [int(image.width * .08), int(image.height * .12),
                       int(image.width * .85), int(image.height * .82)]
            if result["roi"] is not None and result["roi"] != roi:
                raise ValueError("Device dimensions changed")
            result["roi"] = roi
            if read_viewport(fixture) != viewport:
                raise ValueError(f"Viewport changed after restore: {name}")
        print("Captured " + name, flush=True)
        (output / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    adb("shell", "am", "start", "-W", "-n", ACTIVITY)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    pack = actions.add_parser("package")
    for name in ("shell", "library", "native-manifest", "map", "output", "build-tools", "keystore"):
        pack.add_argument("--" + name, type=Path, required=True)
    shot = actions.add_parser("capture")
    for name in ("apk", "fixtures", "cameras", "output"):
        shot.add_argument("--" + name, type=Path, required=True)
    shot.add_argument("--serial", required=True)
    shot.add_argument("--prepare-cameras", action="store_true")
    shot.add_argument("--prototype-cameras", action="store_true")
    args = parser.parse_args()
    if args.action == "package":
        package(args.shell, args.library, args.native_manifest, args.map, args.output, args.build_tools, args.keystore)
    else:
        capture(args.apk, args.fixtures, args.cameras, args.output, args.serial,
                args.prepare_cameras, args.prototype_cameras)
