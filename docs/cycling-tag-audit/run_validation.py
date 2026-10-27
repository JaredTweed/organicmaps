#!/usr/bin/env python3
"""Run local research checks without altering app code or generated app assets."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from audit import ROOT, audit
from style_probe import run


def execute(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, check=True, **kwargs)


def validate(kothic, output, dump=None, cxx="c++"):
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Use a disposable output directory outside the research worktree")
    output.mkdir(parents=True, exist_ok=True)
    tests = execute([sys.executable, "-B", "-m", "unittest", "discover", "-s",
                     "docs/cycling-tag-audit", "-v"], cwd=ROOT)
    test_log = tests.stdout + tests.stderr
    (output / "unit-tests.log").write_text(test_log)
    parser_source = ROOT / "libs/indexer/drules_selector_parser.cpp"
    probe_source = Path(__file__).with_name("native_parser_probe.cpp")
    binary = output / "native-parser"
    compile_command = [cxx, "-std=c++23", "-DRELEASE", "-I", str(ROOT / "libs"),
                       str(parser_source), str(probe_source), "-o", str(binary)]
    execute(compile_command, cwd=ROOT)
    compiled = run(kothic, output / "styles", binary)
    execute(["git", "diff", "--check"], cwd=ROOT)
    return {
        "scope": "Local research validation, not release certification",
        "audit": audit(dump),
        "unit_tests": {"exit_code": tests.returncode, "log": test_log},
        "native_build": {
            "compiler_version": execute([cxx, "--version"]).stdout.splitlines()[0],
            "flags": ["-std=c++23", "-DRELEASE"],
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (parser_source, probe_source)},
        },
        "style_probe": compiled,
        "diff_check": "passed",
        "not_validated": ["Controlled regional MWM generation for alternative encodings",
                          "C++ TypeSelector/Stylist dispatch and full generator/routing suites",
                          "Old/new app-map compatibility execution",
                          "GPU screenshots and mobile frame/tile timings",
                          "Phone usability and maintainer product/release decisions"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kothic", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dump", type=Path)
    parser.add_argument("--cxx", default="c++")
    args = parser.parse_args()
    print(json.dumps(validate(args.kothic.resolve(), args.output_dir.resolve(), args.dump, args.cxx),
                     indent=2, sort_keys=True))
