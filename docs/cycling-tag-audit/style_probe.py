#!/usr/bin/env python3
"""Compile equivalent synthetic styles with pinned Kothic; no MWM or GPU benchmark."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

from audit import ROOT


KOTHIC = "c5546e4f70128a301fc2f08b391baeafe29e5ee9"
FACILITIES = {"track": "#2266bb", "lane": "#338844", "shared_lane": "#993366"}
ROADS = ("tertiary", "residential", "service", "primary", "secondary", "trunk", "unclassified", "living_street")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(directory, variant, roads):
    directory.mkdir(parents=True, exist_ok=True)
    # Kothic reuses colors and patterns from previous output; start this fixture clean.
    for name in ("colors.txt", "patterns.txt"):
        (directory / name).unlink(missing_ok=True)
    rows = []
    priorities = []
    rules = []

    def mapping(name, selector):
        rows.append([name, selector, "", "", "", str(len(rows) + 1), ""])
        priorities.append(name.replace("|", "-"))

    for road in roads:
        mapping(f"highway|{road}", f"[highway={road}]")
    if variant == "combined":
        for road in roads:
            for facility in FACILITIES:
                mapping(f"highway|{road}|{facility}", f"[highway={road}][fixture={facility}]")
    else:
        for facility in FACILITIES:
            mapping(f"cyclewaytag|{facility}", f"[cyclewaytag={facility}]")

    for index, road in enumerate(roads):
        width = index + 2
        base = f"line|z14-15[highway={road}]"
        if variant == "combined":
            rules.append(f"{base} {{width: {width}; color: #555555;}}")
        else:
            absent = "".join(f"[extra_tag!=cyclewaytag={facility}]" for facility in FACILITIES)
            rules.append(f"{base}{absent} {{width: {width}; color: #555555;}}")
        for facility, color in FACILITIES.items():
            condition = (f"[fixture={facility}]" if variant == "combined"
                         else f"[extra_tag=cyclewaytag={facility}]")
            rules.append(f"{base}{condition} {{width: {width}; color: {color};}}")

    with (directory / "mapcss-mapping.csv").open("w", newline="") as stream:
        csv.writer(stream, delimiter=";", lineterminator="\n").writerows(rows)
    (directory / "mapcss-dynamic.txt").write_text("extra_tag\n")
    (directory / "style.mapcss").write_text("\n".join(rules) + "\n")
    for name in ("1_BG-by-size", "2_BG-top", "3_FG", "4_overlays"):
        content = "\n".join(priorities) + "\n=== 100\n" if name == "3_FG" else ""
        (directory / f"priorities_{name}.prio.txt").write_text(content)


def selected_lines(container, types, zoom):
    """Evaluate only this fixture's exact equality/inequality type predicates."""
    matches = []
    for item in container.cont:
        if item.name not in types:
            continue
        for element in item.element:
            if element.scale != zoom:
                continue
            accepted = True
            for predicate in element.apply_if:
                if predicate.startswith("extra_tag!="):
                    accepted &= predicate[len("extra_tag!="):].replace("=", "-") not in types
                elif predicate.startswith("extra_tag="):
                    accepted &= predicate[len("extra_tag="):].replace("=", "-") in types
                else:
                    raise AssertionError(f"Unexpected fixture predicate: {predicate}")
            if accepted:
                matches.extend((line.width, line.color, line.priority) for line in element.lines)
    return sorted(matches)


def run(kothic, output, native_parser=None):
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Use a disposable output directory outside the research worktree")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=kothic, text=True).strip()
    if revision != KOTHIC:
        raise ValueError(f"Expected Kothic {KOTHIC}, found {revision}")
    if subprocess.check_output(["git", "diff", "HEAD", "--", "src"], cwd=kothic):
        raise ValueError("Kothic source has local changes")
    sys.path.insert(0, str(kothic / "src"))
    from drules import parse_binary

    results = {}
    predicates = []
    for count in (3, 8):
        roads = ROADS[:count]
        containers = {}
        variants = {}
        for variant in ("combined", "tags"):
            directory = output / str(count) / variant
            write_fixture(directory, variant, roads)
            command = [sys.executable, "-B", str(kothic / "src/libkomwm.py"),
                       "-s", str(directory / "style.mapcss"), "-d", str(directory),
                       "-p", str(directory), "-o", str(directory / "rules"), "-x"]
            started = time.perf_counter()
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            elapsed = time.perf_counter() - started
            if "ERROR:" in completed.stdout or "ERROR:" in completed.stderr:
                raise AssertionError(completed.stdout + completed.stderr)
            (directory / "compiler.log").write_text(completed.stdout + completed.stderr)
            blob = (directory / "rules.bin").read_bytes()
            _, decoded = parse_binary(blob)
            containers[variant] = decoded[0]
            elements = [element for item in decoded[0].cont for element in item.element]
            predicates.extend(predicate for element in elements for predicate in element.apply_if)
            variants[variant] = {
                "binary_bytes": len(blob),
                "drawing_elements": len(elements),
                "line_rules": sum(len(e.lines) for e in elements),
                "runtime_predicates": sum(len(e.apply_if) for e in elements),
                "stored_type_entries": len((directory / "types.txt").read_text().split()),
                "compile_wall_seconds_single_run": elapsed,
                "hashes": {name: sha(directory / name) for name in (
                    "style.mapcss", "mapcss-mapping.csv", "rules.bin", "types.txt")},
            }
        checked = 0
        for index, road in enumerate(roads):
            for facility in (None, *FACILITIES):
                combined = {f"highway-{road}" + (f"-{facility}" if facility else "")}
                tags = {f"highway-{road}"}
                if facility:
                    tags.add(f"cyclewaytag-{facility}")
                for zoom in (14, 15):
                    a = selected_lines(containers["combined"], combined, zoom)
                    b = selected_lines(containers["tags"], tags, zoom)
                    color = int(FACILITIES[facility].lstrip("#"), 16) if facility else 0x555555
                    expected = [(float(index + 2), color, 100)]
                    if a != expected or b != expected:
                        raise AssertionError((road, facility, zoom, expected, a, b))
                    checked += 1
        results[str(count)] = {"variants": variants, "equivalent_fixture_cases": checked}
    result = {
        "scope": "Synthetic compiler/binary-decoder fixture; not C++ runtime, MWM or GPU performance",
        "kothic_commit": revision, "python": platform.python_version(),
        "compiler_sha256": sha(kothic / "src/libkomwm.py"),
        "single_run_timing_warning": "Includes interpreter startup and multiprocessing; not a performance ranking",
        "results": results,
    }
    if native_parser:
        completed = subprocess.run([str(native_parser)], input="\n".join(predicates) + "\n",
                                   text=True, capture_output=True, check=True)
        result["native_parser"] = json.loads(completed.stdout)
        result["native_parser"]["binary_sha256"] = sha(native_parser)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kothic", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Disposable directory for generated fixtures and compiler artifacts")
    parser.add_argument("--native-parser", type=Path,
                        help="Compiled native_parser_probe linked with repository parser source")
    args = parser.parse_args()
    print(json.dumps(run(args.kothic.resolve(), args.output_dir.resolve(),
                         args.native_parser.resolve() if args.native_parser else None), indent=2, sort_keys=True))
