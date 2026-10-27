"""Derive a style-only clutter experiment without changing map types or routing."""

import copy

OPTIONAL_POIS = ("shop-", "office-", "craft-", "tourism-", "leisure-", "sport-", "historic-", "amenity-")
KEEP_POIS = ("amenity-bicycle_", "amenity-drinking_water", "amenity-water_point", "amenity-toilets",
             "amenity-hospital", "amenity-clinic", "amenity-pharmacy", "amenity-shelter",
             "amenity-ferry_terminal", "amenity-bus_station", "amenity-charging_station-bicycle",
             "tourism-camp_site", "tourism-alpine_hut", "tourism-wilderness_hut", "tourism-hotel",
             "tourism-motel", "tourism-guest_house", "tourism-hostel")
MAJOR_ROADS = ("highway-motorway", "highway-trunk", "highway-primary", "highway-secondary")


def derive(container):
    result = copy.deepcopy(container)
    removed = []
    for entry in result.cont:
        if entry.name.startswith(OPTIONAL_POIS) and not entry.name.startswith(KEEP_POIS):
            changed = False
            for element in entry.element:
                # Keep outlines/areas and connectivity; remove only optional POI overlays.
                for field in ("symbol", "caption", "path_text", "shield"):
                    changed |= getattr(element, field)._is_set()
                    setattr(element, field, type(getattr(element, field))())
            if changed:
                removed.append(entry.name)
        if entry.name.startswith(MAJOR_ROADS):
            for element in entry.element:
                for line in element.lines:
                    line.width *= 0.8
    return result, removed


def compile_pair(blob, kothic, bundle):
    import json
    import subprocess
    import sys

    from style_probe import KOTHIC
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=kothic, text=True).strip()
    if revision != KOTHIC or subprocess.check_output(["git", "diff", "HEAD", "--", "src"], cwd=kothic):
        raise ValueError("Use the pinned, clean Kothic source")
    sys.path.insert(0, str(kothic / "src"))
    import drules

    names, original = drules.parse_binary(blob)
    clean, report = [], {}
    for name, container in zip(names, original):
        variant, removed = derive(container)
        clean.append(variant)
        report[name] = {"overlay_types_reduced": removed, "count": len(removed)}
    (bundle / "baseline.bin").write_bytes(blob)
    generated = drules.serialize_binary(clean, names)
    roundtrip_names, roundtrip = drules.parse_binary(generated)
    if roundtrip_names != names or len(roundtrip) != len(clean):
        raise AssertionError("Style-family round trip failed")
    (bundle / "clean.bin").write_bytes(generated)
    (bundle / "style-report.json").write_text(json.dumps({"variants": report,
        "baseline_bytes": len(blob), "clean_bytes": len(generated),
        "scope": "Outdoors surrogate, not the PR cycling mode or a validated usability winner",
        "major_road_width_scale": 0.8, "new_types": 0}, indent=2) + "\n")
