#!/usr/bin/env python3
"""Build the read-only exporter using an existing host generator build's APIs."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def commands(build, source, output):
    entries = json.loads((build / "compile_commands.json").read_text())
    entry = next(item for item in entries if "generator_tool.dir/Unity/" in item["file"])
    compile_command = shlex.split(entry["command"])
    compile_command[compile_command.index(entry["file"])] = str(source)
    compile_command[compile_command.index("-o") + 1] = str(output.with_suffix(".o"))
    compile_command.append("-g0")
    lines = subprocess.check_output(
        ["ninja", "-C", str(build), "-t", "commands", "generator_tool"], text=True).splitlines()
    link = lines[-1]
    if not link.startswith(": && ") or not link.endswith(" && :"):
        raise ValueError("Unrecognized CMake link recipe; refusing shell interpretation")
    link_command = shlex.split(link[5:-5])
    objects = [item for item in link_command if "generator_tool.dir/" in item and item.endswith(".o")]
    if len(objects) != 1:
        raise ValueError("Expected one generator-tool main object")
    link_command[link_command.index(objects[0])] = str(output.with_suffix(".o"))
    link_command[link_command.index("-o") + 1] = str(output)
    link_command = [item for item in link_command if not item.startswith("-Wl,--dependency-file=")]
    return compile_command, link_command


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).with_name("mwm_feature_audit.cpp").resolve()
    build = args.build.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    compile_command, link_command = commands(build, source, output)
    subprocess.run(compile_command, cwd=build, check=True)
    subprocess.run(link_command, cwd=build, check=True)
    output.with_suffix(".build.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "compile": compile_command, "link": link_command,
        "binary_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "scope": "Read-only export using repository MWM/classifier APIs, not a map generator",
    }, indent=2) + "\n")
