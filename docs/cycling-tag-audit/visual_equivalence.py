#!/usr/bin/env python3
"""Compare matched features/chains and fixed-camera screenshots, failing closed."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def load_export(path):
    features = {}
    chains = []
    metadata = None
    with Path(path).open() as stream:
        for line in stream:
            value = json.loads(line)
            if value["kind"] == "metadata":
                if metadata is not None:
                    raise ValueError("Duplicate metadata")
                metadata = value
            elif value["kind"] == "feature":
                if value["id"] in features:
                    raise ValueError("Duplicate feature ID")
                features[value["id"]] = value
            elif value["kind"] == "chain":
                chains.append(value)
            else:
                raise ValueError("Unknown export record")
    if metadata is None or not features:
        raise ValueError("Incomplete feature export")
    if metadata["offsets_present"] and not metadata["offsets_applied"]:
        raise ValueError("Optional phase data was not validated")
    return features, chains, metadata


def feature_identity(feature):
    geometry = canonical([feature["geometry_type"], feature["points"]])
    return canonical([sorted(feature["osm_ids"]), hashlib.sha256(geometry.encode()).hexdigest()])


def feature_payload(feature):
    return canonical({key: feature[key] for key in
                      ("types", "names", "ref", "layer", "rank", "house_number", "metadata")})


def highway_profile(features):
    pairs = Counter()
    examples = []
    for feature in features.values():
        if feature["geometry_type"] != 1:
            continue
        kinds = sorted({path[1] for path in feature["types"] if len(path) > 1 and path[0] == "highway"})
        if len(kinds) < 2:
            continue
        pairs[" + ".join(kinds)] += 1
        if kinds != ["cycleway", "footway"] and len(examples) < 20:
            examples.append({"id": feature["id"], "osm_ids": feature["osm_ids"], "highways": kinds})
    return {"scope": "Line features; nested subtypes count as one highway family",
            "multiple_highway_families": dict(sorted(pairs.items())), "non_shared_path_examples": examples,
            "note": "Observation, not approval of extra exceptions. Legacy highway|ford needs explicit clarification."}


def compare_exports(baseline, candidate):
    old, old_chains, old_meta = load_export(baseline)
    new, new_chains, new_meta = load_export(candidate)

    def index(features):
        groups = defaultdict(Counter)
        identities = {}
        for fid, feature in features.items():
            identity = feature_identity(feature)
            identities[fid] = identity
            groups[identity][feature_payload(feature)] += 1
        return groups, identities

    old_groups, old_ids = index(old)
    new_groups, new_ids = index(new)
    unidentified = sum(not f["osm_ids"] for f in old.values()) + sum(not f["osm_ids"] for f in new.values())
    keys = old_groups.keys() | new_groups.keys()
    changed = [key for key in sorted(keys) if old_groups[key] != new_groups[key]]
    ambiguous = sorted(key for key in keys
                       if sum(old_groups[key].values()) > 1 or sum(new_groups[key].values()) > 1)

    def resolve(chains, identities):
        result = []
        for chain in chains:
            ids = chain["features"]
            if len(ids) != len(chain["reversed"]) or len(ids) != len(chain["offsets"]):
                raise ValueError("Incomplete chain offsets/reversal")
            result.append(canonical([[(identities[fid], reverse) for fid, reverse in
                                      zip(ids, chain["reversed"])], chain["offsets"]]))
        return result

    old_resolved = resolve(old_chains, old_ids)
    new_resolved = resolve(new_chains, new_ids)
    old_counts, new_counts = Counter(old_resolved), Counter(new_resolved)
    chain_differences = sum((old_counts - new_counts).values()) + sum((new_counts - old_counts).values())
    def overlapping(chains):
        memberships = Counter(fid for chain in chains for fid in set(chain["features"]))
        return sum(count > 1 for count in memberships.values())
    overlaps = overlapping(old_chains) + overlapping(new_chains)
    # Runtime keeps the first chain claiming a feature, so order cannot be
    # discarded if chains overlap. Be conservative rather than simulate it.
    overlapping_order_changed = bool(overlaps and old_resolved != new_resolved)
    return {
        "scope": "OSM identity plus exact geometry, retained types/names/ref/layer/rank/address/metadata, directed chains and offsets",
        "baseline_features": len(old), "candidate_features": len(new),
        "changed_feature_groups": len(changed), "ambiguous_feature_groups": len(ambiguous),
        "unidentified_features": unidentified,
        "changed_examples": [{"identity": key, "baseline": dict(old_groups[key]),
                              "candidate": dict(new_groups[key])} for key in changed[:30]],
        "baseline_chains": len(old_chains), "candidate_chains": len(new_chains),
        "baseline_highway_profile": highway_profile(old), "candidate_highway_profile": highway_profile(new),
        "chain_differences": chain_differences,
        "overlapping_feature_memberships": overlaps,
        "overlapping_chain_order_changed": overlapping_order_changed,
        "exact_matched_data_equal": not changed and not ambiguous and not unidentified and
                                    chain_differences == 0 and not overlapping_order_changed,
        "baseline_metadata": old_meta, "candidate_metadata": new_meta,
    }


def compare_cycling_retention(baseline, candidate):
    """Measure all retained types on cycling features, without certifying the whole map."""
    old, _, _ = load_export(baseline)
    new, _, _ = load_export(candidate)

    def index(features):
        groups = defaultdict(Counter)
        cycling = set()
        missing = count = 0
        for feature in features.values():
            identity = feature_identity(feature)
            groups[identity][canonical(feature["types"])] += 1
            if any(path[0] == "cyclewaytag" for path in feature["types"]):
                cycling.add(identity)
                count += 1
                missing += not feature["osm_ids"]
        return groups, cycling, missing, count

    old_groups, old_cycling, old_missing, old_count = index(old)
    new_groups, new_cycling, new_missing, new_count = index(new)
    cycling = old_cycling | new_cycling
    if not cycling:
        raise ValueError("No cycling features in retention comparison")
    keys = set(old_groups) | set(new_groups)
    changed = [key for key in keys if old_groups[key] != new_groups[key]]
    cycling_changes = sum(key in cycling for key in changed)
    ambiguous = sum(sum(old_groups[key].values()) > 1 or sum(new_groups[key].values()) > 1 for key in cycling)
    return {"scope": "All retained types and their order on matched cycling features; not whole-map equivalence",
            "baseline_cycling_features": old_count, "candidate_cycling_features": new_count,
            "changed_cycling_type_groups": cycling_changes, "changed_other_feature_groups": len(changed)-cycling_changes,
            "ambiguous_cycling_groups": ambiguous, "unidentified_cycling_features": old_missing+new_missing,
            "cycling_types_preserved": not cycling_changes and not ambiguous and not old_missing and not new_missing}


def pixel_metrics(baseline, candidate, roi):
    import numpy as np
    from PIL import Image

    with Image.open(baseline) as a, Image.open(candidate) as b:
        if a.size != b.size:
            raise ValueError("Mismatched screenshot dimensions")
        x0, y0, x1, y1 = roi
        if not (0 <= x0 < x1 <= a.width and 0 <= y0 < y1 <= a.height):
            raise ValueError("Invalid map-region bounds")
        old = np.asarray(a.convert("RGB"))[y0:y1, x0:x1].astype(np.int16)
        new = np.asarray(b.convert("RGB"))[y0:y1, x0:x1].astype(np.int16)
    delta = np.abs(old - new)
    changed = np.any(delta != 0, axis=2)
    return {"roi": list(roi), "pixels": int(changed.size),
            "changed_pixels": int(changed.sum()), "max_channel_difference": int(delta.max()),
            "mean_absolute_difference": float(delta.mean()), "exact_equal": not bool(changed.any())}


def compare_captures(baseline, candidate):
    baseline, candidate = Path(baseline), Path(candidate)
    a = json.loads((baseline / "capture.json").read_text())
    b = json.loads((candidate / "capture.json").read_text())
    if a["fixtures"] != b["fixtures"] or a["roi"] != b["roi"] or a["device"] != b["device"]:
        raise ValueError("Fixtures, map region and device must match")
    if not a.get("assets_sha256") or a["assets_sha256"] != b.get("assets_sha256"):
        raise ValueError("Packaged style assets must match")
    if not a["fixtures"]:
        raise ValueError("An empty capture is not equivalence evidence")
    cases = {}
    for fixture in a["fixtures"]:
        name = fixture["name"]
        if a["actual_backends"].get(name) != fixture["backend"] or \
                b["actual_backends"].get(name) != fixture["backend"]:
            raise ValueError(f"Unverified graphics backend: {name}")
        for directory, manifest in ((baseline, a), (candidate, b)):
            for suffix in ("", ".repeat"):
                filename = name + suffix + ".png"
                if manifest["image_sha256"].get(filename) != digest(directory / filename):
                    raise ValueError(f"Screenshot checksum mismatch: {filename}")
        old_camera = (baseline / (name + ".settings.ini")).read_text()
        new_camera = (candidate / (name + ".settings.ini")).read_text()
        if old_camera != new_camera:
            raise ValueError(f"Camera/settings mismatch: {name}")
        result = pixel_metrics(baseline / (name + ".png"), candidate / (name + ".png"), a["roi"])
        result["baseline_stable"] = pixel_metrics(baseline / (name + ".png"),
                                                  baseline / (name + ".repeat.png"), a["roi"])["exact_equal"]
        result["candidate_stable"] = pixel_metrics(candidate / (name + ".png"),
                                                   candidate / (name + ".repeat.png"), a["roi"])["exact_equal"]
        cases[name] = result
    return {"cases": cases, "case_count": len(cases),
            "baseline_manifest_sha256": digest(baseline / "capture.json"),
            "candidate_manifest_sha256": digest(candidate / "capture.json"),
            "baseline_recaptures": a.get("recaptures", []),
            "candidate_recaptures": b.get("recaptures", []),
            "exact_tested_viewports_equal": all(item["exact_equal"] and item["baseline_stable"] and
                                                item["candidate_stable"] for item in cases.values()),
            "scope": "Only the recorded device/backends/viewports; not universal visual equivalence"}


def verify_export_manifest(export):
    export = Path(export)
    fixture = json.loads((export.parent / "manifest.json").read_text())
    if fixture["export_sha256"] != digest(export):
        raise ValueError("Feature export checksum mismatch")
    maps = list((export.parent / "maps").glob("*.mwm"))
    if len(maps) != 1 or digest(maps[0]) != fixture["map_sha256"]:
        raise ValueError("Generated map checksum mismatch")
    return fixture


def verify_capture_binding(export, captures):
    fixture = verify_export_manifest(export)
    capture = json.loads((Path(captures) / "capture.json").read_text())
    if capture["map_sha256"] != fixture["map_sha256"] or \
            capture["source_commit"] != fixture["source_commit"]:
        raise ValueError("Screenshots and feature export must use the same source and map")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-export", type=Path, required=True)
    parser.add_argument("--candidate-export", type=Path, required=True)
    parser.add_argument("--baseline-captures", type=Path)
    parser.add_argument("--candidate-captures", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-only", action="store_true")
    args = parser.parse_args()
    provenance = {"baseline": verify_export_manifest(args.baseline_export),
                  "candidate": verify_export_manifest(args.candidate_export)}
    report = {"data": compare_exports(args.baseline_export, args.candidate_export), "provenance": provenance,
              "screenshots": None, "verified_tested_visual_equivalence": False}
    if bool(args.baseline_captures) != bool(args.candidate_captures):
        parser.error("Both capture directories are required")
    if args.baseline_captures:
        verify_capture_binding(args.baseline_export, args.baseline_captures)
        verify_capture_binding(args.candidate_export, args.candidate_captures)
        report["screenshots"] = compare_captures(args.baseline_captures, args.candidate_captures)
        report["verified_tested_visual_equivalence"] = (report["data"]["exact_matched_data_equal"] and
                                                         report["screenshots"]["exact_tested_viewports_equal"])
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"data_equal": report["data"]["exact_matched_data_equal"],
                      "verified_tested_visual_equivalence": report["verified_tested_visual_equivalence"]}))
    if args.data_only:
        raise SystemExit(0 if report["data"]["exact_matched_data_equal"] else 1)
    raise SystemExit(0 if report["verified_tested_visual_equivalence"] else 2)
