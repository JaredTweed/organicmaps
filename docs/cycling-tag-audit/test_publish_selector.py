import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("publish-selector.sh")
MOCK = r'''#!/usr/bin/python3
import os, sys
args = sys.argv[1:]
if args[:2] == ["auth", "status"]:
    pass
elif args[0] == "api" and "/commits/master" in args[1]:
    print(os.environ.get("MOCK_BASE", "b55c734f33b278c452a070c1465904c4144dc1ad"))
elif args[0] == "api" and "/branches/" in args[1]:
    print(os.environ.get("MOCK_HEAD", "6f9330d5c002abd40fb7fb425ad6cbc33cf377db"))
elif args[0] == "api" and "/pulls?" in args[1]:
    print(os.environ.get("MOCK_EXISTING", "0"))
elif args[:2] == ["pr", "create"]:
    with open(os.environ["MOCK_MARKER"], "w") as output:
        output.write(" ".join(args))
else:
    raise SystemExit("Unexpected mock gh command: " + repr(args))
'''


class PublishSelectorTests(unittest.TestCase):
    def run_script(self, args=(), **env_overrides):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            gh = tmp / "gh"
            gh.write_text(MOCK)
            gh.chmod(0o755)
            marker = tmp / "published"
            env = dict(os.environ, PATH=str(tmp) + os.pathsep + os.environ["PATH"],
                       MOCK_MARKER=str(marker), **env_overrides)
            result = subprocess.run([str(SCRIPT), *args], env=env, text=True, capture_output=True)
            published = marker.read_text() if marker.exists() else ""
            return result, published

    def test_check_is_read_only(self):
        result, published = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(published, "")

    def test_publish_requires_explicit_opt_in(self):
        result, published = self.run_script(["--publish-selector"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(published, "")

    def test_stale_base_or_duplicate_fails_closed(self):
        for changes in ({"MOCK_BASE": "changed"}, {"MOCK_HEAD": "changed"}, {"MOCK_EXISTING": "1"}):
            result, published = self.run_script(["--publish-selector"], PUBLISH_CYCLING_SELECTOR="YES", **changes)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(published, "")

    def test_opted_in_publish_only_targets_new_selector_draft(self):
        result, published = self.run_script(["--publish-selector"], PUBLISH_CYCLING_SELECTOR="YES")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pr create --repo organicmaps/organicmaps", published)
        self.assertIn("--head JaredTweed:prepare/cycling-selector --base master --draft", published)
        self.assertNotIn("12692", published)


if __name__ == "__main__":
    unittest.main()
