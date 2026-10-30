import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from generate_visual_map import digest
from visual_phone import capture, settings, validate_map_reuse, PACKAGE


class SideOffsetToolConfigTest(unittest.TestCase):
    def test_renderer_only_update_can_reuse_the_exact_demo_map(self):
        native = {"commit": "2" * 40, "map_source_commit": "1" * 40, "source_root": "unused"}
        with patch("visual_phone.PACKAGE", "app.organicmaps.cyclingsides.debug"), \
                patch("visual_phone.command", return_value=b"libs/drape_frontend/stylist.cpp\ndocs/demo.md\n"):
            validate_map_reuse(native, {"source_commit": "1" * 40})

    def test_generator_or_classifier_change_cannot_reuse_the_map(self):
        native = {"commit": "2" * 40, "map_source_commit": "1" * 40, "source_root": "unused"}
        for path in (b"generator/osm2type.cpp\n", b"data/types.txt\n", b"libs/indexer/feature_meta.hpp\n"):
            with patch("visual_phone.PACKAGE", "app.organicmaps.cyclingsides.debug"), \
                    patch("visual_phone.command", return_value=path), self.assertRaises(ValueError):
                validate_map_reuse(native, {"source_commit": "1" * 40})

    def test_equivalence_app_cannot_use_prototype_map_reuse(self):
        native = {"commit": "2" * 40, "map_source_commit": "1" * 40, "source_root": "unused"}
        with patch("visual_phone.PACKAGE", "app.organicmaps.cyclingfinal.debug"), self.assertRaises(ValueError):
            validate_map_reuse(native, {"source_commit": "1" * 40})

    def test_default_style_is_explicit_in_demo_settings(self):
        data = settings({"theme": "dark", "backend": "Vulkan", "mode": "Default"})
        self.assertIn("MapStyleMode=Default\n", data)
        self.assertIn("MapStyleKeyV1=MapStyleDefaultDark\n", data)

    def test_unrecognized_style_is_rejected(self):
        with self.assertRaises(ValueError):
            settings({"theme": "light", "backend": "OpenGLES3", "mode": "bad"})

    def test_normal_app_cannot_be_selected(self):
        environment = {**os.environ, "OM_VISUAL_PACKAGE": "app.organicmaps",
                       "PYTHONPATH": str(Path(__file__).parent)}
        result = subprocess.run([sys.executable, "-c", "import visual_phone"], env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"isolated visual-demo packages", result.stderr)

    def bundle(self, root):
        apk, mwm = root / "demo.apk", root / "map.mwm"
        apk.write_bytes(b"test-apk")
        mwm.write_bytes(b"test-map")
        apk.with_suffix(".json").write_text(json.dumps({
            "package": PACKAGE, "apk_sha256": digest(apk), "map": str(mwm),
            "map_sha256": digest(mwm), "source_commit": "local-prototype"}))
        return apk

    def test_prototype_cameras_cannot_redefine_equivalence_app_cameras(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "separate side-offset app"):
                capture(self.bundle(root), root / "missing.json", root / "cameras", root / "out",
                        "unused", prototype_cameras=True)

    def test_reference_camera_preparation_still_requires_original_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "untouched reference"):
                capture(self.bundle(root), root / "missing.json", root / "cameras", root / "out",
                        "unused", prepare_cameras=True)


if __name__ == "__main__":
    unittest.main()
