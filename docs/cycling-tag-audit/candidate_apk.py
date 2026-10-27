#!/usr/bin/env python3
"""Repackage the isolated Debug research APK with candidate-generated assets."""

import argparse
import shutil
import subprocess
from pathlib import Path
import zipfile

from phone_probe import PACKAGE, run

ASSETS = ("classificator.txt", "types.txt", "drules_default.bin", "drules_outdoors.bin",
          "drules_vehicle.bin", "colors.txt")


def replace_assets(original, resources, output):
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(output, "w", allowZip64=True) as target:
        present = set(source.namelist())
        missing = {"assets/" + name for name in ASSETS} - present
        if missing:
            raise ValueError(f"Missing original APK assets: {sorted(missing)}")
        for info in source.infolist():
            upper = info.filename.upper()
            if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
                continue
            replacement = resources / info.filename.removeprefix("assets/")
            if info.filename in {"assets/" + name for name in ASSETS}:
                with replacement.open("rb") as inp, target.open(info, "w") as out:
                    shutil.copyfileobj(inp, out)
            else:
                with source.open(info) as inp, target.open(info, "w") as out:
                    shutil.copyfileobj(inp, out)


def build(original, resources, output, aapt, zipalign, apksigner, keystore):
    if output.exists():
        raise ValueError("Refusing to overwrite an APK")
    badging = run([aapt, "dump", "badging", original]).decode()
    if f"package: name='{PACKAGE}' " not in badging or "application-debuggable" not in badging:
        raise ValueError("Only the isolated debuggable research APK may be repackaged")
    output.parent.mkdir(parents=True, exist_ok=True)
    unsigned = output.with_suffix(".unsigned.zip")
    aligned = output.with_suffix(".aligned.apk")
    if unsigned.exists() or aligned.exists():
        raise ValueError("Temporary output already exists")
    replace_assets(original, resources, unsigned)
    subprocess.run([str(zipalign), "-P", "16", "4", str(unsigned), str(aligned)], check=True)
    subprocess.run([str(apksigner), "sign", "--ks", str(keystore), "--ks-key-alias", "debug",
                    "--ks-pass", "pass:12345678", "--key-pass", "pass:12345678",
                    "--out", str(output), str(aligned)], check=True)
    subprocess.run([str(apksigner), "verify", "--verbose", str(output)], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "resources", "output", "aapt", "zipalign", "apksigner", "keystore"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.original, args.resources, args.output, args.aapt, args.zipalign, args.apksigner, args.keystore)
