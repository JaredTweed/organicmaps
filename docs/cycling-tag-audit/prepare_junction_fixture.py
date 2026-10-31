#!/usr/bin/env python3
"""Annotate a local visual fixture with shared-node cycling junctions.

No nodes, ways, access tags or geometry are changed. The private demo tags
only authorize a visual taper; they do not claim a protected/marked crossing.
"""

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

PREFIX = "om:demo:cycle_junctions:"


def tags(element):
    return {t.get("k"): t.get("v") for t in element.findall("tag")}


def accessible(data):
    bicycle = data.get("bicycle", "")
    return bicycle not in {"no", "private", "dismount", "use_sidepath"} and (
        data.get("access") not in {"no", "private"}
        or bicycle in {"yes", "designated", "official", "permissive"})


def dedicated(data):
    return accessible(data) and data.get("area") != "yes" and (
        data.get("highway") == "cycleway" or
        (data.get("highway") in {"path", "footway"} and
         data.get("bicycle") in {"designated", "official"}))


def point(node):
    lat, lon = float(node.get("lat")), float(node.get("lon"))
    return lon, math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def annotate(root):
    nodes = {n.get("id"): n for n in root.findall("node")}
    ways = [(w, tags(w), [n.get("ref") for n in w.findall("nd")]) for w in root.findall("way")]
    if any(k.startswith(PREFIX) for _, data, _ in ways for k in data):
        raise ValueError("Input already contains demo junction annotations")
    connectors = defaultdict(list)
    for way, data, refs in ways:
        if dedicated(data):
            for i, ref in enumerate(refs):
                for j in (i - 1, i + 1):
                    if 0 <= j < len(refs):
                        connectors[ref].append((way.get("id"), data, refs[j]))
    examples = []
    count = 0
    for way, data, refs in ways:
        if dedicated(data) or not accessible(data) or data.get("area") == "yes" or not any(
                k in data for k in ("cycleway:left", "cycleway:right", "cycleway:both")):
            continue
        if data.get("highway") in {None, "construction", "proposed"}:
            continue
        sides = {"left": {}, "right": {}}
        for i, ref in enumerate(refs):
            node = nodes.get(ref)
            if node is None or ref not in connectors or not accessible(tags(node)) or "barrier" in tags(node):
                continue
            p = point(node)
            before = nodes.get(refs[max(0, i - 1)])
            after = nodes.get(refs[min(len(refs) - 1, i + 1)])
            if before is None or after is None:
                continue
            a, b = point(before), point(after)
            tangent = b[0] - a[0], b[1] - a[1]
            for connector_id, connector, neighbour in connectors[ref]:
                # Shared IDs prove topology. Reject inconsistent grade tags rather
                # than joining a bridge/tunnel based on visual proximity.
                if connector_id == way.get("id") or neighbour not in nodes or \
                        connector.get("layer", "0") != data.get("layer", "0") or \
                        connector.get("level", "0") != data.get("level", "0"):
                    continue
                q = point(nodes[neighbour])
                ray = q[0] - p[0], q[1] - p[1]
                norm = math.hypot(*tangent) * math.hypot(*ray)
                cross = tangent[0] * ray[1] - tangent[1] * ray[0]
                if norm == 0 or abs(cross) / norm < 0.15:
                    continue  # Collinear connections do not identify a side.
                side = "left" if cross > 0 else "right"
                if len(sides[side]) < 64:
                    sides[side][ref] = p
        for side, junctions in sides.items():
            if not junctions:
                continue
            value = ";".join(f"{x:.9f},{y:.9f}" for x, y in junctions.values())
            ET.SubElement(way, "tag", k=PREFIX + side, v=value)
            count += len(junctions)
            examples.append({"way": way.get("id"), "name": data.get("name", ""),
                             "side": side, "nodes": list(junctions)})
    return {"junction_sides": count, "roads": examples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        raise ValueError("Refusing to overwrite fixture/provenance")
    tree = ET.parse(args.source)
    result = annotate(tree.getroot())
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    result.update(source=str(args.source.resolve()),
                  source_sha256=hashlib.file_digest(args.source.open("rb"), "sha256").hexdigest(),
                  output_sha256=hashlib.file_digest(args.output.open("rb"), "sha256").hexdigest())
    args.output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Annotated {result['junction_sides']} shared-node side junctions")


if __name__ == "__main__":
    main()
