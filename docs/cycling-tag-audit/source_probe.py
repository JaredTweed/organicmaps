#!/usr/bin/env python3
"""Count source-tag fidelity requirements; never infer access or safety ratings."""

import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from phone_probe import digest

FACILITIES = {"track": "track", "opposite_track": "track", "protected_lane": "track",
              "lane": "lane", "opposite_lane": "lane", "buffered_lane": "lane",
              "shared_lane": "shared_lane", "share_busway": "shared_lane",
              "opposite_share_busway": "shared_lane", "shoulder": "shared_lane"}
KEYS = ("cycleway", "cycleway:both", "cycleway:left", "cycleway:right",
        "cycleway:forward", "cycleway:backward")


def inspect_source(source):
    counts, values, mixed, examples = Counter(), Counter(), Counter(), {}
    metadata = {}
    root = None
    for event, element in ET.iterparse(source, events=("start", "end")):
        if root is None:
            root = element
        if event != "end":
            continue
        if element.tag == "meta":
            metadata.update(element.attrib)
        if element.tag != "way":
            if element.tag in ("node", "relation"):
                root.clear()
            continue
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}
        if "highway" in tags:
            counts["highway_ways"] += 1
            present = [(key, tags[key]) for key in KEYS if key in tags]
            if present:
                counts["ways_with_facility_keys"] += 1
                for key, value in present:
                    values[key + "=" + value] += 1
                classes = {FACILITIES[value] for _, value in present if value in FACILITIES}
                if classes:
                    counts["ways_with_recognized_positive_category"] += 1
                if len(classes) > 1:
                    counts["ways_with_multiple_positive_categories"] += 1
                    mixed["+".join(sorted(classes))] += 1
                left, right = tags.get("cycleway:left"), tags.get("cycleway:right")
                if left is not None and right is not None and left != right:
                    counts["ways_with_explicit_differing_sides"] += 1
                    examples.setdefault("differing_sides", element.attrib["id"])
                if any(value in ("no", "none", "separate") for _, value in present) and classes:
                    counts["ways_with_negative_or_separate_and_positive_values"] += 1
                if "cycleway" in tags and len(present) > 1:
                    counts["ways_with_generic_and_qualified_values"] += 1
                if any(key.endswith(":oneway") or key.endswith(":conditional") for key in tags
                       if key.startswith("cycleway")):
                    counts["ways_with_facility_direction_or_conditional_details"] += 1
                if tags["highway"] in ("path", "footway") and tags.get("bicycle") == "designated" and classes:
                    counts["designated_path_footway_with_additional_facility_tags"] += 1
                    examples.setdefault("designated_with_facility", element.attrib["id"])
        root.clear()
    return {"scope": "Raw source counts, not normalized semantics, retained types or MWM A/B results",
            "source_sha256": digest(source), "source_bytes": source.stat().st_size,
            "source_metadata": metadata, "counts": dict(sorted(counts.items())),
            "facility_key_values": dict(sorted(values.items())),
            "mixed_category_counts": dict(sorted(mixed.items())), "example_way_ids": examples,
            "limitations": ["Road-only extract is not a representative complete region",
                            "Categories summarize raw values without resolving precedence",
                            "No inference of legal access, protection, comfort or safety",
                            "No correspondence proven between source ways and older stored dump"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_source(args.source), indent=2, sort_keys=True))
