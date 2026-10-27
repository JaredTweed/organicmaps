import json
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phone_probe import PACKAGE, REGION, capture, digest, launcher_from_xml, scenario, validate_records, verify


class PhoneProbeTests(unittest.TestCase):
    def test_launcher_alias_in_packaged_manifest(self):
        xml = f'''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{PACKAGE}">
          <application><activity-alias android:name="app.organicmaps.DownloadResourcesActivity">
            <intent-filter><action android:name="android.intent.action.MAIN"/>
            <category android:name="android.intent.category.LAUNCHER"/></intent-filter>
          </activity-alias></application></manifest>'''
        self.assertEqual(launcher_from_xml(xml), "app.organicmaps.DownloadResourcesActivity")
        with self.assertRaises(ValueError):
            launcher_from_xml(xml.replace(PACKAGE, "app.organicmaps"))

    @patch("phone_probe.time.sleep")
    @patch("phone_probe.run")
    def test_capture_records_every_view_and_never_resets_apps(self, command, sleep):
        progress = 0
        transferred_hash = None

        def response(arguments, **kwargs):
            nonlocal progress, transferred_hash
            arguments = [str(arg) for arg in arguments]
            if "stdin" in kwargs:
                transferred_hash = digest(Path(kwargs["stdin"].name))
            if "sha256sum" in arguments[-1]:
                return ((transferred_hash + "  fixture\n").encode() if transferred_hash else b"")
            if "getprop" in arguments:
                return {"ro.product.model": b"Pixel 8 Pro", "ro.product.cpu.abi": b"arm64-v8a",
                        "ro.build.fingerprint": b"fixture"}[arguments[-1]]
            if "install" in arguments:
                return b"Success\n"
            if "pidof" in arguments:
                return b"1234"
            if "logcat" in arguments:
                progress += 1
                records = [{"scenario": "cycling-research-vancouver", "index": i,
                            "ready": True, "elapsed_ms": 10} for i in range(progress)]
                log = "\n".join("DrapeViewport " + json.dumps(record) for record in records)
                if progress == 9:
                    log += "\nDrape scenario finished: cycling-research-vancouver"
                return log.encode()
            if "screencap" in arguments:
                return b"\x89PNG\r\n\x1a\nfixture"
            return b""

        command.side_effect = response
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = self.fixture(directory)
            manifest["scope"] = "fixture"
            for name in ("scenario.json", "baseline.bin", "clean.bin"):
                (directory / name).write_bytes(b"fixture")
                manifest["sha256"][name] = digest(directory / name)
            (directory / "manifest.json").write_text(json.dumps(manifest))
            capture(directory, directory / "capture", "adb", "serial", 20)
            result = json.loads((directory / "capture/result.json").read_text())
            self.assertTrue(result["all_viewports_ready"])
            self.assertEqual(result["screenshots_captured"], list(range(9)))
            self.assertFalse(result["release_performance_validated"])
        commands = [" ".join(map(str, call.args[0])) for call in command.call_args_list]
        self.assertFalse(any("uninstall" in cmd or "pm clear" in cmd or "logcat -c" in cmd for cmd in commands))
        self.assertTrue(all(PACKAGE in cmd for cmd in commands if "force-stop" in cmd or "run-as" in cmd))
        transfers = [shlex.split(shlex.split(call.args[0][-1])[-1]) for call in command.call_args_list
                     if "stdin" in call.kwargs]
        self.assertTrue(all(len(parts) == 3 and parts[:2] == ["cat", ">"] for parts in transfers))
        self.assertTrue(any(parts[-1].endswith(REGION + ".mwm") for parts in transfers))

    def test_incomplete_or_failed_viewports_are_not_success(self):
        records = [{"scenario": "cycling-research-vancouver", "index": i, "ready": True,
                    "elapsed_ms": 10} for i in range(9)]
        self.assertTrue(validate_records(records))
        self.assertFalse(validate_records(records[:-1]))
        self.assertFalse(validate_records(records[::-1]))
        records[2]["ready"] = False
        self.assertFalse(validate_records(records))

    def test_scenario_has_fixed_ready_viewports(self):
        steps = scenario()["scenarios"][0]["steps"]
        centers = [s for s in steps if s["actionType"] == "centerViewport"]
        self.assertEqual(len(centers), 9)
        self.assertTrue(all(s["waitForReady"] and not s["animated"] for s in centers))
        self.assertEqual({s["zoomLevel"] for s in centers}, {14, 16, 18})

    def fixture(self, directory):
        (directory / "probe.apk").write_bytes(b"fixture")
        manifest = {"package": PACKAGE, "map_directory": "261025", "activity": "app.organicmaps.Main",
                    "map_filename": REGION + ".mwm",
                    "apk": "probe.apk", "map": "probe.apk",
                    "sha256": {"probe.apk": digest(directory / "probe.apk")}}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_bundle_detects_modified_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            self.assertEqual(verify(directory)["package"], PACKAGE)
            (directory / "probe.apk").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify(directory)

    def test_regular_app_and_unsafe_paths_refused(self):
        for changes in ({"package": "app.organicmaps"}, {"map_directory": "../data"},
                        {"activity": "Main;rm"}, {"sha256": {"../probe.apk": "x"}},
                        {"apk": "/tmp/probe.apk"}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                manifest = self.fixture(directory)
                manifest.update(changes)
                (directory / "manifest.json").write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    verify(directory)

    @patch("phone_probe.run")
    def test_wrong_device_refused_before_install(self, command):
        command.return_value = b"not a Pixel"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            with self.assertRaises(ValueError):
                capture(directory, directory / "capture", "adb", "serial", 5)
            self.assertFalse(any("install" in call.args[0] for call in command.call_args_list))


if __name__ == "__main__":
    unittest.main()
