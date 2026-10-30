#!/usr/bin/env python3
"""Run the bounded native validation set sequentially and retain exact evidence."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from generate_visual_map import digest


def run(root, build, expected, output):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
    if git("rev-parse", "HEAD") != expected or git("status", "--porcelain"):
        raise ValueError("Expected clean source at the pinned revision")
    if output.exists():
        raise ValueError("Refusing to overwrite native evidence")
    output.mkdir(parents=True)
    checks = [("generator_tests", "OsmType|Metalines"),
              ("drape_frontend_tests", "MetalineData|ClipSplines|DashedLinePhase"),
              ("indexer_tests", None), ("routing_common_tests", None)]
    results = {"source_commit": expected, "assertions": "Debug", "checks": {}}
    cache = (build / "CMakeCache.txt").read_text()
    if "CMAKE_BUILD_TYPE:STRING=Debug\n" not in cache or \
            f"CMAKE_HOME_DIRECTORY:INTERNAL={root}\n" not in cache:
        raise ValueError("CMake must use this source checkout with Debug assertions")
    for target, pattern in checks:
        binary = build / target
        before = digest(binary)
        args = [str(binary), "--user_resource_path=" + str(root / "data"),
                "--writable_path=" + str(output / (target + "-writable"))]
        if pattern:
            args.append("--filter=" + pattern)
        path = output / (target + ".log")
        with path.open("w") as log:
            result = subprocess.run(args, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=1200,
                                    env={**os.environ, "XDG_CONFIG_HOME": str(output / "config")})
        text = path.read_text()
        if digest(binary) != before or git("rev-parse", "HEAD") != expected or git("status", "--porcelain"):
            raise ValueError("Source or test executable changed during validation")
        results["checks"][target] = {"args": args, "binary_sha256": before,
                                     "log_sha256": digest(path), "exit_code": result.returncode,
                                     "tests_run": sum(line.startswith("Running ") for line in text.splitlines())}
        (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        if result.returncode or "All tests passed." not in text or not results["checks"][target]["tests_run"]:
            raise RuntimeError("Native checks failed: " + target + "; see " + str(path))
        print(target + ": passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "build", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected", required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.build.resolve(), args.expected, args.output.resolve())
