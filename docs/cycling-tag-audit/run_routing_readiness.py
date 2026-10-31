#!/usr/bin/env python3
"""Run the offline generated-map routing probe and record exact provenance."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--filter", default="CyclingReadiness")
    parser.add_argument("--expected-exit", type=int, default=0)
    args = parser.parse_args()
    root = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name("routing_readiness_probe.cpp")
    command = [str(args.binary.resolve()), "--filter=" + args.filter,
               "--user_resource_path=" + str(root / "data"),
               "--data_path=" + str(root / "data"), "--writable_path=" + str(output / "writable")]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    clean = not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no", "--ignore-submodules"],
        cwd=root, text=True).strip()
    if not clean:
        raise ValueError("Refusing an uncommitted production-source probe")
    log = output / "routing.log"
    with log.open("w") as stream:
        run = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
    text = log.read_text()
    routes = [line for line in text.splitlines() if line.startswith("READINESS_ROUTE ")]
    result = {"source_commit": revision, "tracked_source_clean": clean,
              "probe_source_sha256": digest(source), "probe_binary_sha256": digest(args.binary),
              "command": command, "exit_code": run.returncode, "expected_exit_code": args.expected_exit,
              "passed_tests": text.count("[OK]"),
              "successful_route_checks": len(routes), "verified_routes": routes,
              "all_passed": "All tests passed." in text, "log_sha256": digest(log),
              "scope": "Synthetic OSM -> generated routing/access sections -> production IndexRouter; no downloaded maps"}
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if (run.returncode != args.expected_exit or not routes or
            (args.expected_exit == 0 and (not result["all_passed"] or not result["passed_tests"]))):
        print(text[-12000:], flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
