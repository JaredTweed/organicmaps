"""Guard the explicitly nonvisual ownership revision against source drift."""

from pathlib import Path
import re
import unittest

from audit_nonvisual_refactor import audit


ROOT = Path(__file__).resolve().parents[2]
DOCS = Path(__file__).parent
BASELINE = 'badbc0753b7e2a1b73ebb802fc5c9bf75d37cb7a'


class NonvisualRefactorTests(unittest.TestCase):
    def test_current_style_preserves_assets_codec_and_osm_policy(self):
        candidate = re.search(r'^readonly STYLE_HEAD=(\w+)$',
                              (DOCS / 'rollout.sh').read_text(), re.M).group(1)
        report = audit(ROOT, BASELINE, candidate)
        self.assertTrue(report['payload_codec_unchanged'])
        self.assertTrue(report['osm_policy_body_moved_verbatim'])
        self.assertEqual(report['changed_assets'], [])

    def test_asset_changes_cannot_be_certified_as_nonvisual(self):
        with self.assertRaises(AssertionError):
            audit(ROOT, '7af82a316aeeacfc304e9f5c2610d20d563b21ae', BASELINE)


if __name__ == '__main__':
    unittest.main()
