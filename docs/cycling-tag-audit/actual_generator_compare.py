#!/usr/bin/env python3
"""Summarize two same-input generator dumps; this is not a routing test."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


REGION = "Canada_British Columbia_Vancouver.mwm"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize_dump(path):
    features = 0
    attributes = Counter()
    histogram = Counter()
    with path.open() as source:
        for line in source:
            fields = line.split()
            if not fields or not fields[0].isdigit():
                continue
            count = int(fields[0])
            types = {item.rstrip("|") for item in fields[1:]}
            features += count
            histogram[len(types)] += count
            for item in types:
                if item.startswith(("hwtag|", "psurface|", "cyclewaytag|")):
                    attributes[item] += count
    if not features:
        raise ValueError(f"No feature counts in {path}")
    return {"features": features, "type_count_histogram": dict(sorted(histogram.items())),
            "attribute_counts": dict(sorted(attributes.items()))}


def summarize(directory):
    mwm = directory / "maps" / REGION
    dump = directory / "types-dump.txt"
    return {"map_bytes": mwm.stat().st_size, "map_sha256": digest(mwm),
            "dump_sha256": digest(dump), **summarize_dump(dump)}


def compare(baseline, candidate, source):
    old = summarize(baseline)
    new = summarize(candidate)
    names = old["attribute_counts"].keys() | new["attribute_counts"].keys()
    changed = {name: new["attribute_counts"].get(name, 0) - old["attribute_counts"].get(name, 0)
               for name in sorted(names)
               if new["attribute_counts"].get(name, 0) != old["attribute_counts"].get(name, 0)}
    return {"scope": "Road-only geometry/index MWM; aggregate types, not per-feature routing or compatibility",
            "source_sha256": digest(source), "baseline": old, "candidate": new,
            "attribute_count_deltas": changed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--baseline-generator", required=True, type=Path)
    parser.add_argument("--candidate-generator", required=True, type=Path)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--candidate-commit", required=True)
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate, args.source)
    result["baseline"]["commit"] = args.baseline_commit
    result["baseline"]["generator_sha256"] = digest(args.baseline_generator)
    result["candidate"]["commit"] = args.candidate_commit
    result["candidate"]["generator_sha256"] = digest(args.candidate_generator)
    print(json.dumps(result, indent=2, sort_keys=True))
