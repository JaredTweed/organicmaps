import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phone_summary import summarize


class PhoneSummaryTests(unittest.TestCase):
    @patch("phone_summary.verify")
    def test_rejects_default_style_and_wrong_backend(self, verify):
        verify.return_value = {"scope": "fixture", "package": "fixture", "sha256": {}}
        records = [{"scenario": "cycling-research-vancouver", "index": i, "ready": True,
                    "elapsed_ms": 10} for i in range(9)]
        with tempfile.TemporaryDirectory() as tmp:
            capture = Path(tmp)
            (capture / "result.json").write_text(json.dumps({"scenario_finished": True,
                "viewport_records": records, "screenshots_captured": list(range(9)),
                "style": "clean", "theme": "light", "requested_backend": "OpenGLES3"}))
            (capture / "environment.json").write_text(json.dumps({"ro.product.model": "Pixel 8 Pro"}))
            log = "OutdoorsEnabled : true\nMapStyleOutdoorsLight\n/styles/drules_outdoors.bin\n"
            (capture / "logcat.txt").write_text(log + "Renderer = fixture | Api = OpenGLES3 | Version = fixture\n")
            for i in range(9):
                (capture / f"viewport-{i:02d}.png").write_bytes(b"fixture")
            self.assertEqual(summarize(capture, [capture])["captures"][0]["viewports_ready"], 9)
            (capture / "logcat.txt").write_text(log.replace("OutdoorsEnabled : true", "OutdoorsEnabled : false")
                                                + "Renderer = fixture | Api = OpenGLES3 | Version = fixture\n")
            with self.assertRaises(ValueError):
                summarize(capture, [capture])
            (capture / "logcat.txt").write_text(log + "Renderer = fixture | Api = Vulkan | Version = fixture\n")
            with self.assertRaises(ValueError):
                summarize(capture, [capture])


if __name__ == "__main__":
    unittest.main()
