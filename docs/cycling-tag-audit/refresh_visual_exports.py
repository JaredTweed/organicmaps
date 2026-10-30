#!/usr/bin/env python3
"""Refresh read-only exports without changing generated maps or losing provenance."""

import argparse
import json
import os
import re
from pathlib import Path
import subprocess

from generate_visual_map import digest, REGION


def refresh(fixture, resources, exporter, previous_label):
    manifest_path = fixture / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    mwm = fixture / "maps" / (REGION + ".mwm")
    if digest(mwm) != manifest["map_sha256"]:
        raise ValueError("Generated map changed")
    for name, expected in manifest["resources"].items():
        if digest(resources / name) != expected:
            raise ValueError(f"Classifier/style resources changed: {name}")
    original = fixture / "features.jsonl"
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", previous_label):
        raise ValueError("Unsafe export label")
    backup = fixture / ("features." + previous_label + ".jsonl")
    temporary = fixture / "features.pending.jsonl"
    if backup.exists() or temporary.exists():
        raise ValueError("Export already refreshed; refusing ambiguous overwrite")
    with temporary.open("w") as out, (fixture / "export-refreshed.log").open("w") as log:
        subprocess.run([str(exporter), str(resources), str(mwm), str(mwm) + ".osm2ft"],
                       stdout=out, stderr=log, check=True,
                       env={**os.environ, "XDG_CONFIG_HOME": str(fixture / "export-config")})
    if digest(mwm) != manifest["map_sha256"]:
        raise ValueError("Exporter modified the map")
    with temporary.open() as stream:
        header = json.loads(next(stream))
        for name in ("classificator.txt", "types.txt"):
            if Path(header["classifier_paths"][name]).resolve() != (resources / name).resolve():
                raise ValueError("Exporter resolved an unrelated classifier")
        for line in stream:
            json.loads(line)
    if "Incorrect type index" in (fixture / "export-refreshed.log").read_text():
        raise ValueError("Exporter encountered invalid feature type indices")
    original.rename(backup)
    (fixture / ("manifest." + previous_label + ".json")).write_text(manifest_path.read_text())
    temporary.rename(original)
    manifest["export_sha256"] = digest(original)
    manifest["exporter_sha256"] = digest(exporter)
    manifest["export_schema"] = "matched-feature-v5-complete-source-identities"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(str(fixture) + ": refreshed read-only export", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, action="append", required=True)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--exporter", type=Path, required=True)
    parser.add_argument("--previous-label", default="original")
    args = parser.parse_args()
    for fixture in args.fixture:
        refresh(fixture.resolve(), args.resources.resolve(), args.exporter.resolve(), args.previous_label)
