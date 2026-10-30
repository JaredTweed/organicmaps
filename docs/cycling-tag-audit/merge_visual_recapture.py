#!/usr/bin/env python3
"""Replace contaminated complete capture cases without overwriting raw evidence."""

import argparse
import json
from pathlib import Path
import re
import shutil

from generate_visual_map import digest


def merge(original, recapture, output, reason):
    if output.exists() or not reason.strip():
        raise ValueError("Require a new output directory and an explicit recapture reason")
    old_path, new_path = original / "capture.json", recapture / "capture.json"
    old, new = json.loads(old_path.read_text()), json.loads(new_path.read_text())
    for key in ("package", "source_commit", "apk_sha256", "native_sha256", "map_sha256",
                "assets_sha256", "device", "roi"):
        if not old.get(key) or old[key] != new[key]:
            raise ValueError("Recapture provenance mismatch: " + key)
    fixtures = {item["name"]: item for item in old["fixtures"]}
    replacements = [item["name"] for item in new["fixtures"]]
    if not replacements or len(set(replacements)) != len(replacements):
        raise ValueError("Require unique nonempty complete cases")
    replaced = {}
    for item in new["fixtures"]:
        name = item["name"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name) or fixtures.get(name) != item:
            raise ValueError("Recapture fixture mismatch")
        if (original / (name + ".settings.ini")).read_bytes() != \
                (recapture / (name + ".settings.ini")).read_bytes():
            raise ValueError("Recapture camera/settings mismatch")
        if any(record["actual_backends"].get(name) != item["backend"] for record in (old, new)):
            raise ValueError("Unverified recapture backend")
        for suffix in ("", ".repeat"):
            filename = name + suffix + ".png"
            for directory, record in ((original, old), (recapture, new)):
                if record["image_sha256"].get(filename) != digest(directory / filename):
                    raise ValueError("Capture checksum mismatch")
            replaced[filename] = old["image_sha256"][filename]
    shutil.copytree(original, output)
    for name in replacements:
        for path in recapture.iterdir():
            if path.name.startswith(name + ".") and path.is_file():
                shutil.copy2(path, output / path.name)
        for suffix in ("", ".repeat"):
            filename = name + suffix + ".png"
            old["image_sha256"][filename] = new["image_sha256"][filename]
    old.setdefault("recaptures", []).append({
        "reason": reason, "cases": replacements,
        "original_manifest_sha256": digest(old_path), "recapture_manifest_sha256": digest(new_path),
        "superseded_image_sha256": replaced,
        "policy": "Replace both cold starts of every contaminated case; never select by pixel agreement"})
    (output / "capture.json").write_text(json.dumps(old, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("original", "recapture", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    merge(args.original, args.recapture, args.output, args.reason)
