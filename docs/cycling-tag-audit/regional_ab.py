#!/usr/bin/env python3
"""Regenerate a bounded tag-versus-composite experiment outside the worktree.

This is a centerline storage experiment, not an implementation of PR #12692.
Both encodings use the identical annotated OSM XML and conservative fixture
semantics. It deliberately excludes ambiguous, negative and mixed facilities.
"""

import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

from audit import ROOT
from phone_probe import digest
from source_probe import FACILITIES, KEYS
from style_probe import ROADS

REGION = "Canada_British Columbia_Vancouver"
CATEGORIES = ("track", "lane", "shared_lane")


def annotate(source, target):
    tree = ET.parse(source)
    counts = Counter()
    for way in tree.getroot().iter("way"):
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if "research:facility" in tags:
            raise ValueError("Input already contains the experiment's synthetic key")
        if tags.get("highway") not in ROADS:
            continue
        values = [tags[key] for key in KEYS if key in tags]
        positive = {FACILITIES[v] for v in values if v in FACILITIES}
        if len(positive) != 1 or any(v not in FACILITIES for v in values):
            continue
        category = next(iter(positive))
        ET.SubElement(way, "tag", k="research:facility", v=category)
        counts[category] += 1
    tree.write(target, encoding="utf-8", xml_declaration=True)
    return dict(sorted(counts.items()))


def make_resources(source, destination, variant):
    shutil.copytree(source, destination, symlinks=True)
    mapping = destination / "mapcss-mapping.csv"
    next_id = len((source / "types.txt").read_text().split()) + 1
    rows = []
    if variant == "tag":
        rows = [(f"hwtag|research_{kind}", f"[research:facility={kind}]") for kind in CATEGORIES]
    elif variant == "combined":
        rows = [(f"highway|{road}|research_{kind}", f"[highway={road}][research:facility={kind}]")
                for road in ROADS for kind in CATEGORIES]
    else:
        raise ValueError("Unknown candidate")
    with mapping.open("a", newline="") as stream:
        writer = csv.writer(stream, delimiter=";", lineterminator="\n")
        for name, selector in rows:
            writer.writerow([name, selector, "", "", "", next_id, ""])
            next_id += 1
    for path in (destination / "styles").glob("*/include/priorities_*.prio.txt"):
        output, added_research = [], set()
        for line in path.read_text().splitlines(keepends=True):
            output.append(line)
            for road in ROADS:
                pattern = r"^(\s*)highway-" + re.escape(road) + r"(?=\s|#|::)"
                if variant == "combined" and re.match(pattern, line):
                    for kind in CATEGORIES:
                        output.append(re.sub(pattern, r"\1highway-" + road + "-research_" + kind, line, count=1))
                if path.name == "priorities_3_FG.prio.txt":
                    token = line.split("#", 1)[0].strip().split()
                    name = token[0].split("::", 1)[0] if token else ""
                    prefix = "highway-" + road
                    if name == prefix or name.startswith(prefix + "-"):
                        if name not in added_research:
                            output.append(name + "::research\n")
                            added_research.add(name)
                    if variant == "combined" and name == prefix:
                        for kind in CATEGORIES:
                            candidate = name + "-research_" + kind
                            if candidate not in added_research:
                                output.append(candidate + "::research\n")
                                added_research.add(candidate)
        path.write_text("".join(output))
    dynamic = destination / "mapcss-dynamic.txt"
    if "extra_tag" not in dynamic.read_text().splitlines():
        with dynamic.open("a") as stream:
            stream.write("\nextra_tag\n")
    roads = destination / "styles/outdoors/include/Roads.mapcss"
    colors = {"track": "#2266bb", "lane": "#338844", "shared_lane": "#993366"}
    with roads.open("a") as stream:
        stream.write("\n/* Synthetic research fixture, not the PR's cycling style. */\n")
        for road in ROADS:
            for kind, color in colors.items():
                predicate = (f"extra_tag=hwtag=research_{kind}" if variant == "tag"
                             else f"research:facility={kind}")
                stream.write(f"line|z14-18[highway={road}][{predicate}]::research "
                             f"{{width: 2; color: {color};}}\n")
    env = dict(os.environ, DATA_PATH=str(destination), OMIM_PATH=str(ROOT))
    started = time.monotonic()
    with (destination.parent / "style-build.log").open("w") as log:
        subprocess.run([str(ROOT / "tools/unix/generate_drules.sh")], env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    return {"seconds_single_run": time.monotonic() - started,
            "mapping_sha256": digest(mapping), "types_sha256": digest(destination / "types.txt"),
            "classifier_sha256": digest(destination / "classificator.txt"),
            "drules_merged_bytes": (destination / "drules_merged.bin").stat().st_size}


def generate(generator, source, resources, directory, region=REGION, planet_version=1786991694):
    maps, intermediate = directory / "maps", directory / "intermediate"
    (maps / "borders").mkdir(parents=True)
    intermediate.mkdir()
    if region == REGION:
        shutil.copy2(ROOT / "data/borders" / (REGION + ".poly"), maps / "borders")
    elif region == "ResearchUrban":
        (maps / "borders/ResearchUrban.poly").write_text(
            "ResearchUrban\n1\n -123.145 49.255\n -123.095 49.255\n"
            " -123.095 49.295\n -123.145 49.295\n -123.145 49.255\nEND\nEND\n")
    else:
        raise ValueError("Unknown region")
    common = [str(generator), "--threads_count=2", f"--data_path={maps}",
              f"--intermediate_data_path={intermediate}", f"--cache_path={intermediate}",
              f"--user_resource_path={resources}", "--node_storage=map"]
    stages = [common + [f"--osm_file_name={source}", "--osm_file_type=xml", "--preprocess=true"],
              common + [f"--osm_file_name={source}", "--osm_file_type=xml", "--generate_features=true"],
              common + [f"--planet_version={planet_version}", "--generate_geometry=true", "--generate_index=true",
                        f"--output={region}"]]
    timings = {}
    for name, command in zip(("preprocess", "features", "geometry"), stages):
        started = time.monotonic()
        with (directory / (name + ".log")).open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        timings[name] = time.monotonic() - started
    output = maps / (region + ".mwm")
    with (directory / "types-dump.txt").open("w") as dump:
        subprocess.run(common + [f"--output={region}", "--dump_types=true"], stdout=dump, check=True)
    warnings = [line.strip() for line in (directory / "features.log").read_text().splitlines()
                if "Exceeded types count for:" in line]
    combinations, categories, protected = Counter(), Counter(), Counter()
    for line in (directory / "types-dump.txt").read_text().splitlines():
        fields = line.split()
        if not fields or not fields[0].isdigit():
            continue
        count = int(fields[0])
        types = [t.rstrip("|") for t in fields[1:]]
        combinations[len(types)] += count
        for kind in CATEGORIES:
            if any(t == f"hwtag|research_{kind}" or t.endswith(f"|research_{kind}") for t in types):
                categories[kind] += count
        for type_name in types:
            if type_name.startswith(("hwtag|", "psurface|")) and "|research_" not in type_name:
                protected[type_name] += count
    return {"map_bytes": output.stat().st_size, "map_sha256": digest(output),
            "stage_seconds_single_run": timings, "overflow_warnings": warnings,
            "dump_sha256": digest(directory / "types-dump.txt"),
            "stored_count_histogram": dict(sorted(combinations.items())),
            "category_feature_counts": dict(sorted(categories.items())),
            "existing_attribute_counts": dict(sorted(protected.items()))}


def run(source, output, generator):
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError("Output must be a new directory outside the worktree")
    output.mkdir(parents=True)
    annotated = output / "identical-input.osm"
    counts = annotate(source, annotated)
    result = {"scope": "One road-only region; centerline fixture, not release or side-aware comparison",
              "source_sha256": digest(source), "annotated_sha256": digest(annotated),
              "annotated_categories": counts, "generator_sha256": digest(generator), "candidates": {}}
    for variant in ("tag", "combined"):
        directory = output / variant
        directory.mkdir()
        resources = directory / "data"
        styles = make_resources(ROOT / "data", resources, variant)
        result["candidates"][variant] = {"styles": styles,
                                         "map": generate(generator, annotated, resources, directory)}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source.resolve(), args.output.resolve(), args.generator.resolve()), indent=2, sort_keys=True))
