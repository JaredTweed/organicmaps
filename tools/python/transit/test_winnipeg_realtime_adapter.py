import tempfile
import unittest
import zipfile
from pathlib import Path

from winnipeg_realtime_adapter import GtfsTripResolver, normalize_stop_schedule


SAMPLE_CAMEL = {
    "stop": {"key": 10064},
    "routeSchedules": [
        {
            "route": {"key": "BLUE", "number": "BLUE"},
            "scheduledStops": [
                {
                    "key": 123,
                    "tripKey": 35833897,
                    "cancelled": False,
                    "times": {
                        "arrival": {
                            "scheduled": "2026-10-12T19:30:00-05:00",
                            "estimated": "2026-10-12T19:34:30-05:00",
                        },
                        "departure": {
                            "scheduled": "2026-10-12T19:30:30-05:00",
                            "estimated": "2026-10-12T19:35:00-05:00",
                        },
                    },
                    "bus": {"key": 641},
                }
            ],
        }
    ],
}


class AdapterTests(unittest.TestCase):
    def test_camel_case_response(self):
        updates = normalize_stop_schedule(SAMPLE_CAMEL)
        self.assertEqual(len(updates), 1)
        update = updates[0]
        self.assertEqual(update.trip_id, "35833897")
        self.assertEqual(update.route_id, "BLUE")
        self.assertEqual(update.stop_id, "10064")
        self.assertEqual(update.arrival_delay_seconds, 270)
        self.assertEqual(update.departure_delay_seconds, 270)
        self.assertEqual(update.bus_id, "641")
        self.assertFalse(update.cancelled)

    def test_hyphenated_response(self):
        payload = {
            "stop": {"key": "10064"},
            "route-schedules": {
                "route-schedule": {
                    "route": {"key": "11"},
                    "scheduled-stops": {
                        "scheduled-stop": {
                            "trip-key": "42",
                            "cancelled": True,
                            "times": {
                                "arrival": {"scheduled": "08:00:00", "estimated": "08:02:00"},
                                "departure": {"scheduled": "08:00:30", "estimated": "08:02:30"},
                            },
                        }
                    },
                }
            },
        }
        update = normalize_stop_schedule(payload)[0]
        self.assertEqual(update.trip_id, "42")
        self.assertEqual(update.arrival_delay_seconds, 120)
        self.assertTrue(update.cancelled)

    def test_gtfs_direct_and_fallback_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            gtfs = Path(tmp) / "gtfs.zip"
            with zipfile.ZipFile(gtfs, "w") as zf:
                zf.writestr(
                    "trips.txt",
                    "route_id,service_id,trip_id,trip_headsign,direction_id,block_id,shape_id\n"
                    "BLUE,WEEKDAY,35833897,Downtown,0,,shape1\n"
                    "11,WEEKDAY,gtfs-trip-2,Portage,0,,shape2\n",
                )
                zf.writestr(
                    "stop_times.txt",
                    "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                    "35833897,19:30:00,19:30:30,10064,1\n"
                    "gtfs-trip-2,08:00:00,08:00:30,10064,1\n",
                )
            resolver = GtfsTripResolver.from_zip(gtfs)
            self.assertEqual(resolver.resolve("35833897", "10064", "BLUE", "19:30:00"), "35833897")
            self.assertEqual(resolver.resolve("api-trip-2", "10064", "11", "08:00:00"), "gtfs-trip-2")
            self.assertIsNone(resolver.resolve("unknown", "10064", "11", "09:00:00"))

    def test_unresolved_trip_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            gtfs = Path(tmp) / "gtfs.zip"
            with zipfile.ZipFile(gtfs, "w") as zf:
                zf.writestr("trips.txt", "route_id,service_id,trip_id\nBLUE,WEEKDAY,different\n")
                zf.writestr(
                    "stop_times.txt",
                    "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                    "different,07:00:00,07:00:30,10064,1\n",
                )
            resolver = GtfsTripResolver.from_zip(gtfs)
            self.assertEqual(normalize_stop_schedule(SAMPLE_CAMEL, resolver=resolver), [])


if __name__ == "__main__":
    unittest.main()
