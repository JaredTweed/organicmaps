#!/usr/bin/env python3
"""Install the isolated thin-offset demo without clearing its existing data."""

import argparse
import hashlib
import json
import shlex
from pathlib import Path
import subprocess
import zipfile


PACKAGE = "app.organicmaps.cyclingsides.debug"
ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial")
    args = parser.parse_args()
    apk = ROOT / "build-visual-artifacts/side-offsets/thin-offsets/phone.apk"
    manifest = json.loads(apk.with_suffix(".json").read_text())
    map_path = Path(manifest["map"])
    if not map_path.is_absolute():
        map_path = ROOT / map_path
    if manifest["package"] != PACKAGE or digest(apk) != manifest["apk_sha256"]:
        raise SystemExit("Unexpected or modified APK")
    if digest(map_path) != manifest["map_sha256"]:
        raise SystemExit("Modified fixture map")
    devices = subprocess.check_output(["adb", "devices"], text=True).splitlines()[1:]
    authorized = [line.split()[0] for line in devices if line.endswith("\tdevice")]
    serial = args.serial or (authorized[0] if len(authorized) == 1 else None)
    if serial not in authorized:
        raise SystemExit("Connect and authorize one phone, or specify --serial")
    adb = ["adb", "-s", serial]

    def run(*command, **kwargs):
        return subprocess.run(adb + list(command), check=True, timeout=180, **kwargs)

    with zipfile.ZipFile(apk) as archive:
        version = str(int(json.loads(archive.read("assets/countries.json"))["v"]))
    run("install", "-r", str(apk))
    run("shell", "am", "force-stop", PACKAGE)
    run("shell", "run-as", PACKAGE, "mkdir", "-p", f"files/{version}", "files/bookmarks")
    for source, destination in (
        (map_path, f"files/{version}/{map_path.name}"),
        (ROOT / "docs/side-offset-examples.kml", "files/bookmarks/side-offset-examples.kml"),
    ):
        with source.open("rb") as stream:
            command = "cat > " + shlex.quote(destination)
            run("shell", "-T", f"run-as {PACKAGE} sh -c {shlex.quote(command)}", stdin=stream)
    actual = subprocess.check_output(
        adb + ["shell", f"run-as {PACKAGE} sha256sum {shlex.quote(f'files/{version}/{map_path.name}')}"], text=True
    ).split()[0]
    if actual != manifest["map_sha256"]:
        raise SystemExit("Installed map verification failed")
    run("shell", "am", "start", "-W", "-n", f"{PACKAGE}/app.organicmaps.SplashActivity")
    print("Installed OM Side Offsets. Open its side-offset example bookmarks.")


if __name__ == "__main__":
    main()
