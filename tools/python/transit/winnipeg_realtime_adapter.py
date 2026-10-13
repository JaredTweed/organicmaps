#!/usr/bin/env python3
"""Winnipeg Transit realtime -> GTFS-style stop update adapter.

Winnipeg Transit exposes realtime predictions through a proprietary stop-schedule
API rather than GTFS-Realtime. Organic Maps consumes realtime updates per stop,
so this adapter normalizes one Winnipeg stop-schedule response into records that
carry GTFS trip/route/stop identifiers and arrival/departure delays.

The adapter accepts both Winnipeg API v4 camelCase JSON (json-camel-case=true)
and the legacy hyphenated field names.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class StopUpdate:
    trip_id: str
    route_id: str | None
    stop_id: str
    scheduled_arrival: str | None
    estimated_arrival: str | None
    arrival_delay_seconds: int | None
    scheduled_departure: str | None
    estimated_departure: str | None
    departure_delay_seconds: int | None
    cancelled: bool
    bus_id: str | None = None


class GtfsTripResolver:
    """Resolve Winnipeg trip keys to static-GTFS trip_ids.

    Winnipeg currently appears to expose a numeric `trip-key`. If that key is
    also a GTFS `trip_id`, resolution is direct. If not, a conservative fallback
    matches stop + route + scheduled time and only succeeds when there is a
    unique candidate.
    """

    def __init__(self, trip_ids: set[str], by_stop_route_time: dict[tuple[str, str, str], set[str]]):
        self._trip_ids = trip_ids
        self._by_stop_route_time = by_stop_route_time

    @classmethod
    def from_zip(cls, path: str | Path) -> "GtfsTripResolver":
        with zipfile.ZipFile(path) as zf:
            with zf.open("trips.txt") as raw:
                rows = list(csv.DictReader((line.decode("utf-8-sig") for line in raw)))
            trip_ids = {row["trip_id"] for row in rows}
            route_by_trip = {row["trip_id"]: row["route_id"] for row in rows}

            by_key: dict[tuple[str, str, str], set[str]] = {}
            with zf.open("stop_times.txt") as raw:
                for row in csv.DictReader((line.decode("utf-8-sig") for line in raw)):
                    trip_id = row["trip_id"]
                    route_id = route_by_trip.get(trip_id)
                    if route_id is None:
                        continue
                    for field in ("arrival_time", "departure_time"):
                        value = row.get(field)
                        if not value:
                            continue
                        key = (row["stop_id"], route_id, value)
                        by_key.setdefault(key, set()).add(trip_id)
        return cls(trip_ids, by_key)

    def resolve(self, trip_key: str, stop_id: str, route_id: str | None, scheduled_time: str | None) -> str | None:
        if trip_key in self._trip_ids:
            return trip_key
        if route_id is None or scheduled_time is None:
            return None
        gtfs_time = _to_gtfs_clock(scheduled_time)
        if gtfs_time is None:
            return None
        candidates = self._by_stop_route_time.get((stop_id, route_id, gtfs_time), set())
        return next(iter(candidates)) if len(candidates) == 1 else None


def _get(mapping: dict[str, Any] | None, *names: str, default: Any = None) -> Any:
    if not isinstance(mapping, dict):
        return default
    for name in names:
        if name in mapping:
            return mapping[name]
    return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = _get(value, "key", "id", "number")
    return None if value is None else str(value)


def _parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%H:%M:%S"):
        try:
            parsed = dt.datetime.strptime(value, fmt)
            return parsed
        except ValueError:
            continue
    return None


def _delay_seconds(scheduled: str | None, estimated: str | None) -> int | None:
    a = _parse_time(scheduled)
    b = _parse_time(estimated)
    if a is None or b is None:
        return None
    if a.tzinfo is None and b.tzinfo is not None:
        a = a.replace(tzinfo=b.tzinfo)
    elif b.tzinfo is None and a.tzinfo is not None:
        b = b.replace(tzinfo=a.tzinfo)
    return round((b - a).total_seconds())


def _to_gtfs_clock(value: str) -> str | None:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    return parsed.strftime("%H:%M:%S")


def _route_schedules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = _get(payload, "routeSchedules", "route-schedules")
    if isinstance(value, dict):
        value = _get(value, "routeSchedule", "route-schedule", default=value)
    return [item for item in _as_list(value) if isinstance(item, dict)]


def _scheduled_stops(route_schedule: dict[str, Any]) -> list[dict[str, Any]]:
    value = _get(route_schedule, "scheduledStops", "scheduled-stops")
    if isinstance(value, dict):
        value = _get(value, "scheduledStop", "scheduled-stop", default=value)
    return [item for item in _as_list(value) if isinstance(item, dict)]


def normalize_stop_schedule(
    payload: dict[str, Any], *, resolver: GtfsTripResolver | None = None, requested_stop_id: str | None = None
) -> list[StopUpdate]:
    stop_id = requested_stop_id or _id(_get(payload, "stop"))
    if stop_id is None:
        raise ValueError("Winnipeg response does not identify the requested stop")

    updates: list[StopUpdate] = []
    for route_schedule in _route_schedules(payload):
        route_id = _id(_get(route_schedule, "route"))
        for scheduled_stop in _scheduled_stops(route_schedule):
            trip_key = _id(_get(scheduled_stop, "tripKey", "trip-key"))
            if trip_key is None:
                continue

            times = _get(scheduled_stop, "times", default={})
            arrival = _get(times, "arrival", default={})
            departure = _get(times, "departure", default={})
            scheduled_arrival = _get(arrival, "scheduled")
            estimated_arrival = _get(arrival, "estimated")
            scheduled_departure = _get(departure, "scheduled")
            estimated_departure = _get(departure, "estimated")

            trip_id = trip_key
            if resolver is not None:
                resolved = resolver.resolve(
                    trip_key,
                    stop_id,
                    route_id,
                    scheduled_arrival or scheduled_departure,
                )
                if resolved is None:
                    # Do not emit a guessed GTFS identifier.
                    continue
                trip_id = resolved

            bus_id = _id(_get(scheduled_stop, "bus"))
            updates.append(
                StopUpdate(
                    trip_id=trip_id,
                    route_id=route_id,
                    stop_id=stop_id,
                    scheduled_arrival=scheduled_arrival,
                    estimated_arrival=estimated_arrival,
                    arrival_delay_seconds=_delay_seconds(scheduled_arrival, estimated_arrival),
                    scheduled_departure=scheduled_departure,
                    estimated_departure=estimated_departure,
                    departure_delay_seconds=_delay_seconds(scheduled_departure, estimated_departure),
                    cancelled=bool(_get(scheduled_stop, "cancelled", default=False)),
                    bus_id=bus_id,
                )
            )
    return updates


def fetch_stop_schedule(stop_id: str, api_key: str, *, timeout: float = 10.0) -> dict[str, Any]:
    query = urllib.parse.urlencode({"api-key": api_key, "json-camel-case": "true"})
    url = f"https://api.winnipegtransit.com/v4/stops/{urllib.parse.quote(stop_id)}/schedule.json?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "OrganicMaps-Winnipeg-Transit-Adapter/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Winnipeg Transit returned HTTP {response.status}")
        return json.load(response)


def _serialize(updates: Iterable[StopUpdate]) -> dict[str, Any]:
    return {"formatVersion": 1, "updates": [asdict(update) for update in updates]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stop_id", help="Winnipeg Transit/GTFS stop id")
    parser.add_argument("--api-key", help="Winnipeg Transit API key")
    parser.add_argument("--input", type=Path, help="Read a saved Winnipeg API JSON response instead of calling the API")
    parser.add_argument("--gtfs", type=Path, help="Static Winnipeg GTFS zip; enables conservative trip-id validation/fallback")
    args = parser.parse_args(argv)

    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if not args.api_key:
            parser.error("--api-key is required unless --input is supplied")
        payload = fetch_stop_schedule(args.stop_id, args.api_key)

    resolver = GtfsTripResolver.from_zip(args.gtfs) if args.gtfs else None
    updates = normalize_stop_schedule(payload, resolver=resolver, requested_stop_id=args.stop_id)
    json.dump(_serialize(updates), sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
