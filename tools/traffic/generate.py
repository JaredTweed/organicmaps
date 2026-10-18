#!/usr/bin/env python3
"""Prepare an offline historical traffic sidecar; Python standard library only.

Inputs are explicit map-build segment matches, never OSM way ids. See docs/OFFLINE_TRAFFIC.md.
"""
import argparse
import csv
import datetime as dt
import json
import gzip
import math
from pathlib import Path
import struct
import zlib
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
EPOCH = dt.date(1970, 1, 1)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def segment_key(feature, segment, forward):
    require(0 <= feature < 2**32 and 0 <= segment < 2**31, "segment id out of range")
    require(type(forward) is bool, "forward must be a boolean")
    return (feature << 32) | (segment << 1) | (not forward)


def varuint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return result


def string(value):
    data = value.encode("utf-8")
    require(len(data) <= 65535, "metadata too long")
    return struct.pack("<H", len(data)) + data


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.utcoffset() == dt.timedelta(0), "validity timestamps must be UTC")
    return int(parsed.timestamp())


def transitions(name, start, end):
    """Resolve IANA rules during preparation. Runtime does not need a timezone database.

    Probe hourly and locate offset changes to a second. This assumes at most one
    change per hour: use audited, pinned modern IANA rules, not custom tzfiles.
    """
    zone = ZoneInfo(name)

    def offset(t):
        return int(dt.datetime.fromtimestamp(t, zone).utcoffset().total_seconds())

    result = [(start, offset(start))]
    cursor = start
    while cursor < end - 1:
        probe = min(cursor + 3600, end - 1)
        if offset(probe) != result[-1][1]:
            lo, hi = cursor, probe
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if offset(mid) == result[-1][1]:
                    lo = mid
                else:
                    hi = mid
            result.append((hi, offset(hi)))
        cursor = probe
    return result


def factor(value):
    require(math.isfinite(value) and 0.25 <= value <= 255 / 128, "factor out of range")
    return int(value * 128 + 0.5)


def cluster_profile(profile, tolerance):
    """Quantize a weekly profile with a deterministic maximum absolute error.

    All speeds assigned to the same representative differ from the prepared
    aggregate by at most |tolerance| km/h. Missing buckets stay missing.
    """
    if tolerance == 0:
        return profile
    step = 2 * tolerance
    return bytes(0 if speed == 0 else max(1, min(200, ((speed + step // 2) // step) * step))
                 for speed in profile)


def cluster_profiles(raw_profiles, tolerance, limit=65535):
    profiles, ids = [], {}
    for profile in raw_profiles:
        representative = cluster_profile(profile, tolerance)
        if representative not in ids:
            require(len(profiles) < limit,
                    "too many profile clusters at the requested tolerance; partition the region "
                    "or explicitly choose a larger cluster_tolerance_kmh")
            ids[representative] = len(profiles)
            profiles.append(representative)
    return profiles, ids


def encode(manifest, observations):
    start, end = timestamp(manifest["valid_from"]), timestamp(manifest["valid_until"])
    require(946684800 <= start < end <= 4102444800, "validity must be within 2000-2099")
    require(end - start <= 5 * 366 * 86400, "limit package prediction horizon to five years")
    source = manifest["source"]
    require(source.get("name") and source.get("license") and source.get("tzdb"), "source, license and tzdb required")
    require(type(source.get("synthetic")) is bool, "explicit synthetic flag required")
    minimum = manifest.get("minimum_samples", 5)
    require(type(minimum) is int and minimum > 0, "positive minimum_samples required")
    matches = {}
    used_keys = set()
    for s in manifest["segments"]:
        key = segment_key(s["feature_id"], s["segment_idx"], s["forward"])
        require(key not in used_keys and s["id"] not in matches, "duplicate segment or provider id")
        used_keys.add(key)
        matches[s["id"]] = (key, s["timezone"], factor(s.get("factor", 1.0)))
    require(matches, "no segment matches")
    # Harmonic average of speed observations weighted by sample count: distance / travel time.
    buckets = {}
    observations = sorted(observations, key=lambda r: (r["id"], int(r["weekday"]), int(r["hour"]),
                                                       float(r["speed_kmh"]), int(r["samples"])))
    for row in observations:
        require(row["id"] in matches, "observation has no segment match")
        weekday, hour = int(row["weekday"]), int(row["hour"])
        speed, count = float(row["speed_kmh"]), int(row["samples"])
        require(0 <= weekday < 7 and 0 <= hour < 24, "invalid weekly bucket")
        require(math.isfinite(speed) and 1 <= speed <= 200 and count > 0, "invalid observation")
        k = (row["id"], weekday * 24 + hour)
        n, seconds = buckets.get(k, (0, 0.0))
        buckets[k] = (n + count, seconds + count / speed)
    zones = sorted({s[1] for s in matches.values()})
    require(len(zones) <= 256, "too many timezones")
    requested_tolerance = manifest.get("cluster_tolerance_kmh", 1)
    require(type(requested_tolerance) is int and 0 <= requested_tolerance <= 25,
            "cluster_tolerance_kmh must be an integer in [0, 25]")
    raw_profile_ids, raw_profiles, records = {}, [], []
    for identifier, (key, zone, scale) in sorted(matches.items(), key=lambda item: item[1][0]):
        profile = bytearray(168)
        for hour in range(168):
            n, total = buckets.get((identifier, hour), (0, 0.0))
            if n >= minimum:
                profile[hour] = max(1, min(200, int(n / total + 0.5)))
        # Omit uncovered segments. Their existing road estimator remains authoritative.
        if not any(profile):
            continue
        profile = bytes(profile)
        if profile not in raw_profile_ids:
            raw_profile_ids[profile] = len(raw_profiles)
            raw_profiles.append(profile)
        records.append((key, raw_profile_ids[profile], zones.index(zone), scale))
    require(records, "no observations meet minimum sample count")
    profiles_before_clustering = len(raw_profiles)
    tolerance = requested_tolerance
    profiles, cluster_ids = cluster_profiles(raw_profiles, tolerance)
    representative_ids = {raw_profile_ids[profile]: cluster_ids[cluster_profile(profile, tolerance)]
                          for profile in raw_profiles}
    records = [(key, representative_ids[profile_id], zone, scale)
               for key, profile_id, zone, scale in records]
    source = dict(source)
    source["profile_cluster_tolerance_kmh"] = tolerance
    source["profiles_before_clustering"] = profiles_before_clustering
    out = bytearray(struct.pack("<4sHHQQqq", b"OMHT", 1, 0, manifest["map_build"], manifest["map_size"], start, end))
    require(len(manifest["map_hash"]) == 12, "map_hash must be the exported 12-character BLAKE3 digest")
    out += string(manifest["region"]) + string(manifest["map_hash"])
    out += string(json.dumps(source, sort_keys=True, separators=(",", ":")))
    out += struct.pack("<HHI", len(profiles), len(zones), len(records))
    out += b"".join(profiles)
    for name in zones:
        changes = transitions(name, start, end)
        adjustments = manifest.get("date_adjustments", {}).get(name, {})
        dates = sorted(((dt.date.fromisoformat(day) - EPOCH).days, factor(value))
                       for day, value in adjustments.items())
        require(len(changes) <= 65535 and len(dates) <= 65535, "calendar too large")
        out += struct.pack("<HH", len(changes), len(dates))
        for utc, offset in changes:
            out += struct.pack("<qi", utc, offset)
        for day, scale in dates:
            require(0 <= day <= 50000, "date adjustment out of range")
            out += struct.pack("<iB", day, scale)
    previous = 0
    for i, (key, profile, zone, scale) in enumerate(records):
        out += varuint(key if i % 64 == 0 else key - previous)
        out += struct.pack("<HBB", profile, zone, scale)
        previous = key
    out += struct.pack("<I", zlib.crc32(out))
    require(len(out) <= 128 * 1024 * 1024, "package too large")
    return bytes(out), {"segments": len(records), "profiles": len(profiles),
                        "profiles_before_clustering": profiles_before_clustering,
                        "cluster_tolerance_kmh": tolerance, "bytes": len(out),
                        "gzip_bytes": len(gzip.compress(out, mtime=0))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cpp-fixture", type=Path, help="Also write the synthetic C++ test fixture header")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if args.cpp_fixture:
        require(manifest["source"]["synthetic"], "C++ fixtures must be explicitly synthetic")
    with args.observations.open(newline="") as stream:
        data, stats = encode(manifest, csv.DictReader(stream))
    # Atomic install/update; routing retains its immutable snapshot until the route finishes.
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(args.output)
    if args.cpp_fixture:
        rows = ("  " + ", ".join(str(b) for b in data[i:i + 24]) + ",\n"
                for i in range(0, len(data), 24))
        args.cpp_fixture.write_text(
            "// Generated from tools/traffic/sample by generate.py. Synthetic CC0 test data.\n"
            "#pragma once\n#include <cstdint>\ninline constexpr uint8_t kHistoricalTrafficFixture[] = {\n"
            + "".join(rows) + "};\n")
    print(json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
