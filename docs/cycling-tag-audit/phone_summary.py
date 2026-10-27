#!/usr/bin/env python3
"""Summarize completed local captures without publishing device screenshots or logs."""

import argparse
import json
from pathlib import Path
import re

from phone_probe import digest, validate_records, verify


def summarize(bundle, captures):
    manifest = verify(bundle)
    result = {"scope": manifest["scope"], "package": manifest["package"],
              "input_sha256": manifest["sha256"], "captures": []}
    for directory in captures:
        record = json.loads((directory / "result.json").read_text())
        environment = json.loads((directory / "environment.json").read_text())
        log = (directory / "logcat.txt").read_text()
        if environment.get("ro.product.model") != "Pixel 8 Pro":
            raise ValueError("Capture is not from the expected device")
        if not record.get("scenario_finished") or not validate_records(record["viewport_records"]):
            raise ValueError("Capture is incomplete")
        expected_style = "MapStyleOutdoors" + record["theme"].title()
        if ("OutdoorsEnabled : true" not in log or expected_style not in log
                or "/styles/drules_outdoors.bin" not in log):
            raise ValueError("Capture did not load the requested Outdoors fixture")
        renderer = re.search(r"Renderer = ([^|\n]+) \| Api = ([^|\n]+)", log)
        if not renderer or renderer[2].strip() != record["requested_backend"]:
            raise ValueError("Actual graphics backend does not match the request")
        screenshots = [directory / f"viewport-{i:02d}.png" for i in range(9)]
        if record.get("screenshots_captured") != list(range(9)) or not all(p.is_file() for p in screenshots):
            raise ValueError("Capture is missing screenshots")
        result["captures"].append({"name": directory.name, "model": "Pixel 8 Pro",
                                   "style": record["style"], "theme": record["theme"],
                                   "renderer": renderer[1].strip(), "backend": renderer[2].strip(),
                                   "viewports_ready": 9,
                                   "viewport_elapsed_ms": [r["elapsed_ms"] for r in record["viewport_records"]],
                                   "screenshot_sha256": [digest(p) for p in screenshots]})
    result["limitations"] = ["Debug build: no release-performance conclusion",
                             "Outdoors surrogate, not the dedicated cycling mode",
                             "No controlled map-encoding comparison or usability study",
                             "Screenshots and device logs remain local"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("captures", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(summarize(args.bundle, args.captures), indent=2, sort_keys=True))
