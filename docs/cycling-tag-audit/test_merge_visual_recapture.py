import json
from pathlib import Path
import tempfile
import unittest

from generate_visual_map import digest
from merge_visual_recapture import merge
from visual_phone import PACKAGE, unlocked_foreground


class RecaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old, self.new, self.out = (self.root / key for key in ("old", "new", "out"))
        for directory in (self.old, self.new):
            directory.mkdir()
            record = {key: "same" for key in ("package", "source_commit", "apk_sha256", "native_sha256",
                                              "map_sha256", "assets_sha256", "device", "roi")}
            record.update(fixtures=[{"name": "site", "backend": "Vulkan"}],
                          actual_backends={"site": "Vulkan"}, image_sha256={})
            (directory / "site.settings.ini").write_text("same-camera")
            for suffix in ("", ".repeat"):
                path = directory / ("site" + suffix + ".png")
                path.write_bytes(directory.name.encode() + suffix.encode())
                record["image_sha256"][path.name] = digest(path)
            (directory / "capture.json").write_text(json.dumps(record))

    def test_complete_case_replaced_with_raw_evidence_retained(self):
        original = (self.old / "capture.json").read_bytes()
        merge(self.old, self.new, self.out, "Visible Android volume panel")
        self.assertEqual((self.old / "capture.json").read_bytes(), original)
        for suffix in ("", ".repeat"):
            name = "site" + suffix + ".png"
            self.assertEqual((self.out / name).read_bytes(), (self.new / name).read_bytes())
        evidence = json.loads((self.out / "capture.json").read_text())["recaptures"][0]
        self.assertEqual(evidence["original_manifest_sha256"], digest(self.old / "capture.json"))
        self.assertEqual(len(evidence["superseded_image_sha256"]), 2)

    def test_changed_camera_is_rejected_before_copy(self):
        (self.new / "site.settings.ini").write_text("changed-camera")
        with self.assertRaisesRegex(ValueError, "camera/settings"):
            merge(self.old, self.new, self.out, "overlay")
        self.assertFalse(self.out.exists())

    def test_changed_map_is_rejected(self):
        path = self.new / "capture.json"
        record = json.loads(path.read_text())
        record["map_sha256"] = "different"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "map_sha256"):
            merge(self.old, self.new, self.out, "overlay")

    def test_missing_repeat_is_rejected(self):
        (self.new / "site.repeat.png").unlink()
        with self.assertRaises(FileNotFoundError):
            merge(self.old, self.new, self.out, "overlay")

    def test_visible_volume_panel_rejected_even_when_app_retains_focus(self):
        focus = "mCurrentFocus=Window{app " + PACKAGE + "/Activity}\n"
        volume = "  Window #0 Window{a u0 VolumeDialog}:\n    isOnScreen=true\n"
        self.assertFalse(unlocked_foreground(focus + volume, "\n showing=false\n"))
        self.assertTrue(unlocked_foreground(focus + volume.replace("true", "false"), "\n showing=false\n"))


if __name__ == "__main__":
    unittest.main()
