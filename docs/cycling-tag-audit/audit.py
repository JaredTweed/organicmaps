#!/usr/bin/env python3
"""Read-only, pinned-source audit. This does not generate or benchmark MWMs."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BASE = "936c7834fb"
EXPERIMENT = "955cd49403"


def git_file(ref, path):
    return subprocess.check_output(
        ["git", "show", f"{ref}:{path}"], cwd=ROOT, text=True
    )


def type_mapping(text):
    return [line.removeprefix("*") for line in text.split()]


def collisions(left, right):
    return [
        {"stored_index": i, "csv_id": i + 1, "base": a, "experiment": b}
        for i, (a, b) in enumerate(zip(left, right)) if a != b
    ]


def classifier_values(text):
    children = defaultdict(set)
    stack = []
    paths = []
    for line in text.splitlines():
        words = line.split()
        if not words or words[0] == "{}":
            continue
        depth = (len(line) - len(line.lstrip())) // 4
        if depth == 0:
            continue
        stack = stack[:depth - 1]
        stack.append(words[0])
        path = tuple(stack)
        children[path[:-1]].add(path[-1])
        paths.append(path)
    ordered = {parent: sorted(names) for parent, names in children.items()}
    result = {}
    for path in paths:
        if len(path) > 4:
            raise ValueError("Classifier exceeds four path levels")
        value = 1 << (7 * len(path))
        for level, name in enumerate(path):
            index = ordered[path[:level]].index(name)
            if index > 127:
                raise ValueError("Classifier child index exceeds seven bits")
            value |= index << (7 * level)
        result["|".join(path)] = value
    return result


def split_designation(types):
    result = set(types)
    for kind in ("path", "footway"):
        combined = f"highway|{kind}|bicycle"
        if combined in result:
            result.remove(combined)
            result.update((f"highway|{kind}", "bicycletag|designated"))
    return result


def dump_summary(text):
    histogram = Counter()
    highway = Counter()
    bike = Counter()
    saturated = Counter()
    split_deltas = Counter()
    for line in text.splitlines():
        fields = line.split()
        if not fields or not fields[0].isdigit():
            continue
        if len(fields) < 2 or not all(t.endswith("|") for t in fields[1:]):
            raise ValueError(f"Invalid dump row: {line}")
        count = int(fields[0])
        types = {t.rstrip("|") for t in fields[1:]}
        if len(types) != len(fields) - 1 or not 1 <= len(types) <= 8:
            raise ValueError(f"Invalid stored type set: {line}")
        n = len(types)
        histogram[n] += count
        roads = sorted(t for t in types if t.startswith("highway|"))
        if roads:
            highway[n] += count
            if "hwtag|yesbicycle" in types:
                bike[n] += count
            if n == 8:
                saturated[" + ".join(roads)] += count
            split_deltas[len(split_designation(types)) - n] += count
    if not histogram:
        raise ValueError("No type-combination rows found")
    return {
        "all_features_by_stored_count": dict(sorted(histogram.items())),
        "highway_features_by_stored_count": dict(sorted(highway.items())),
        "highway_yesbicycle_by_stored_count": dict(sorted(bike.items())),
        "saturated_highway_combinations": dict(sorted(saturated.items())),
        "hypothetical_designation_split_slot_deltas": dict(sorted(split_deltas.items())),
        "warning": "Post-truncation counts; source tags and candidate coverage unknown. "
                   "Split model is set replacement only, not the generator pipeline.",
    }


def audit(dump=None):
    left = type_mapping(git_file(BASE, "data/types.txt"))
    right = type_mapping(git_file(EXPERIMENT, "data/types.txt"))
    values = classifier_values(git_file(EXPERIMENT, "data/classificator.txt"))
    names = ["cyclewaytag|track", "cyclewaytag|lane", "cyclewaytag|shared_lane",
             "hwtag|yesbicycle", "psurface|paved_good"]
    result = {
        "scope": "Source/data audit only; no size, speed, routing or rendering benchmark",
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", BASE], cwd=ROOT, text=True).strip(),
        "experimental_commit": subprocess.check_output(
            ["git", "rev-parse", EXPERIMENT], cwd=ROOT, text=True).strip(),
        "mapping_differences": collisions(left, right),
        "type_identity_examples": {
            name: {"stored_index": right.index(name), "csv_id": right.index(name) + 1,
                   "internal_classifier_value": values[name]} for name in names
        },
        "designation_split_example": {
            "before": ["highway|path|bicycle"],
            "after": sorted(split_designation({"highway|path|bicycle"})),
            "slot_delta": 1,
        },
    }
    if dump:
        raw = dump.read_bytes()
        result["dump_sha256"] = hashlib.sha256(raw).hexdigest()
        result["dump"] = dump_summary(raw.decode())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, help="Existing generator_tool --dump_types stdout")
    args = parser.parse_args()
    print(json.dumps(audit(args.dump), indent=2, sort_keys=True))
