"""Guard the explicitly nonvisual ownership revision against source drift."""

from pathlib import Path
import unittest

from audit_nonvisual_refactor import audit


ROOT = Path(__file__).resolve().parents[2]
DOCS = Path(__file__).parent
BASELINE = 'badbc0753b7e2a1b73ebb802fc5c9bf75d37cb7a'


class NonvisualRefactorTests(unittest.TestCase):
    def test_recorded_nonvisual_revision_preserves_assets_codec_and_osm_policy(self):
        # Preserve the historical proof; the later author-approved quiet style
        # is intentionally visual and must not be certified as nonvisual.
        candidate = 'ef743e813409c7b907ca5fe7b98aae2e7ac4157c'
        report = audit(ROOT, BASELINE, candidate)
        self.assertTrue(report['payload_codec_unchanged'])
        self.assertTrue(report['osm_policy_body_moved_verbatim'])
        self.assertEqual(report['changed_assets'], [])

    def test_asset_changes_cannot_be_certified_as_nonvisual(self):
        with self.assertRaises(AssertionError):
            audit(ROOT, '7af82a316aeeacfc304e9f5c2610d20d563b21ae', BASELINE)


if __name__ == '__main__':
    unittest.main()
