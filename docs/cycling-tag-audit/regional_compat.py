#!/usr/bin/env python3
"""Read generated candidate maps with the pinned baseline type mapping."""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

from audit import ROOT
from phone_probe import digest
from regional_ab import REGION


def count_highways(path):
    counts = Counter()
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields or not fields[0].isdigit():
            continue
        n = int(fields[0])
        types = [t.rstrip("|") for t in fields[1:]]
        if any(t.startswith("highway|") for t in types):
            counts["features_with_highway_type"] += n
        if any("research_" in t for t in types):
            counts["features_with_research_type"] += n
        counts["features_total"] += n
    return dict(sorted(counts.items()))


def analyze(run_dir, generator):
    result = {"scope": "Pinned current reader and baseline type mapping reading newer research maps; "
                       "not a historical released client or complete app/map migration test",
              "baseline_types_sha256": digest(ROOT / "data/types.txt"), "candidates": {}}
    for name in ("tag", "combined"):
        directory = run_dir / name
        candidate = count_highways(directory / "types-dump.txt")
        old_dump = directory / "baseline-reader-types.txt"
        command = [str(generator), "--threads_count=2", f"--data_path={directory / 'maps'}",
                   f"--user_resource_path={ROOT / 'data'}", f"--output={REGION}", "--dump_types=true"]
        with old_dump.open("w") as stream:
            subprocess.run(command, stdout=stream, check=True)
        result["candidates"][name] = {"candidate_reader": candidate, "baseline_reader": count_highways(old_dump),
                                       "baseline_dump_sha256": digest(old_dump)}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.run.resolve(), args.generator.resolve()), indent=2, sort_keys=True))
