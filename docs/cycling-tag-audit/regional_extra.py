#!/usr/bin/env python3
"""Repeat both candidates for an overlapping dense urban subregion."""

import argparse
import json
from pathlib import Path

from phone_probe import digest
from regional_ab import generate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    args = parser.parse_args()
    root, generator = args.run.resolve(), args.generator.resolve()
    source = root / "identical-input.osm"
    result = {"scope": "Overlapping downtown subregion, not an independent geographic sample",
              "annotated_sha256": digest(source), "generator_sha256": digest(generator), "candidates": {}}
    for variant in ("tag", "combined"):
        directory = root / variant / "urban"
        directory.mkdir()
        result["candidates"][variant] = generate(generator, source, root / variant / "data", directory,
                                                  region="ResearchUrban")
    print(json.dumps(result, indent=2, sort_keys=True))
