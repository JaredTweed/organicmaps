import tempfile
import unittest
from pathlib import Path
import zipfile

from candidate_apk import ASSETS, replace_assets


class CandidateApkTests(unittest.TestCase):
    def test_replaces_only_selected_assets_and_removes_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resources = root / "resources"
            resources.mkdir()
            for name in ASSETS:
                (resources / name).write_bytes(b"new " + name.encode())
            with zipfile.ZipFile(root / "original.zip", "w") as archive:
                for name in ASSETS:
                    archive.writestr("assets/" + name, b"old")
                archive.writestr("META-INF/OLD.SF", b"signature")
                archive.writestr("assets/untouched", b"original")
            replace_assets(root / "original.zip", resources, root / "new.zip")
            with zipfile.ZipFile(root / "new.zip") as archive:
                self.assertNotIn("META-INF/OLD.SF", archive.namelist())
                self.assertEqual(archive.read("assets/untouched"), b"original")
                for name in ASSETS:
                    self.assertEqual(archive.read("assets/" + name), b"new " + name.encode())


if __name__ == "__main__":
    unittest.main()
