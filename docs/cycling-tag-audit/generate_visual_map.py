#!/usr/bin/env python3
"""Build and export a pinned road-map fixture, with one worker and provenance."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

REGION = "Canada_British Columbia_Vancouver"


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def run_fixture(root, build, osm, output, exporter, expected):
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if commit != expected or subprocess.check_output(["git", "status", "--porcelain"], cwd=root):
        raise ValueError("Fixture source must be clean and at the expected commit")
    cache = (build / "CMakeCache.txt").read_text()
    home = next(line.split("=", 1)[1] for line in cache.splitlines()
                if line.startswith("CMAKE_HOME_DIRECTORY:INTERNAL="))
    if Path(home).resolve() != root:
        raise ValueError("CMake cache belongs to a different source checkout")
    if output.exists():
        raise ValueError("Refusing to overwrite a fixture")
    output.mkdir(parents=True)
    with (output / "build.log").open("w") as log:
        subprocess.run(["cmake", "--build", str(build), "--target", "generator_tool", "-j1"],
                       cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
    generator = build / "generator_tool"
    generator_digest = digest(generator)
    maps = output / "maps"
    intermediate = output / "intermediate"
    (maps / "borders").mkdir(parents=True)
    intermediate.mkdir()
    environment = {**os.environ, "XDG_CONFIG_HOME": str(output / "config")}
    shutil.copy2(root / "data/borders" / (REGION + ".poly"), maps / "borders")
    common = [str(generator), "--threads_count=1", f"--data_path={maps}",
              f"--intermediate_data_path={intermediate}", f"--cache_path={intermediate}",
              f"--user_resource_path={root / 'data'}", "--node_storage=map"]
    phases = [("preprocess", [f"--osm_file_name={osm}", "--osm_file_type=xml", "--preprocess=true"]),
              ("features", [f"--osm_file_name={osm}", "--osm_file_type=xml", "--generate_features=true"]),
              ("geometry", ["--planet_version=1786991694", "--generate_geometry=true",
                            "--generate_index=true", f"--output={REGION}"])]
    elapsed = {}
    for name, arguments in phases:
        start = time.monotonic()
        with (output / (name + ".log")).open("w") as log:
            subprocess.run(common + arguments, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True,
                           env=environment)
        elapsed[name] = time.monotonic() - start
    mwm = maps / (REGION + ".mwm")
    mapping = maps / (REGION + ".mwm.osm2ft")
    with (output / "features.jsonl").open("w") as data, (output / "export.log").open("w") as log:
        subprocess.run([str(exporter), str(root / "data"), str(mwm), str(mapping)], cwd=root,
                       stdout=data, stderr=log, check=True, env=environment)
    resources = ("classificator.txt", "types.txt", "drules_cycling.bin", "drules_cycling.txt", "colors.txt", "patterns.txt")
    (output / "data").mkdir()
    for name in resources:
        shutil.copy2(root / "data" / name, output / "data" / name)
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() != expected or \
            subprocess.check_output(["git", "status", "--porcelain"], cwd=root) or digest(generator) != generator_digest:
        raise ValueError("Source or generator changed during the audit")
    manifest = {"source_commit": commit, "source_clean": True, "osm_sha256": digest(osm),
                "generator_sha256": generator_digest, "map_sha256": digest(mwm),
                "map_bytes": mwm.stat().st_size, "osm2ft_sha256": digest(mapping),
                "export_sha256": digest(output / "features.jsonl"),
                "exporter_sha256": digest(exporter),
                "resources": {name: digest(root / "data" / name) for name in resources},
                "submodules": subprocess.check_output(["git", "submodule", "status", "--recursive"], cwd=root, text=True),
                "generation_workers": 1, "elapsed_seconds": elapsed,
                "scope": "Road-only geometry/index/metalines fixture, not a production or routing-graph map"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"commit": commit, "map_bytes": manifest["map_bytes"], "output": str(output)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "build", "osm", "output", "exporter"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    run_fixture(args.source.resolve(), args.build.resolve(), args.osm.resolve(),
                args.output.resolve(), args.exporter.resolve(), args.commit)
