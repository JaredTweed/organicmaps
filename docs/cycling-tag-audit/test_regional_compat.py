import tempfile
import unittest
from pathlib import Path

from regional_compat import count_highways


class RegionalCompatibilityTests(unittest.TestCase):
    def test_counts_weighted_features_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dump"
            path.write_text("3 highway|tertiary| hwtag|research_lane|\n"
                            "2 highway|tertiary|research_lane| highway|tertiary|bridge|\n"
                            "4 amenity|cafe|\n")
            self.assertEqual(count_highways(path), {"features_total": 9, "features_with_highway_type": 5,
                                                    "features_with_research_type": 5})


if __name__ == "__main__":
    unittest.main()
