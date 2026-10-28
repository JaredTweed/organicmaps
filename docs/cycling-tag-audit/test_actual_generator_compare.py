import tempfile
from pathlib import Path
import unittest

from actual_generator_compare import summarize_dump


class ActualGeneratorCompareTests(unittest.TestCase):
    def test_counts_are_weighted_by_feature_combinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / "dump.txt"
            dump.write_text("2 highway|secondary| hwtag|yesbicycle| cyclewaytag|lane|\n"
                            "3 highway|footway| psurface|paved_good|\n")
            result = summarize_dump(dump)
        self.assertEqual(result["features"], 5)
        self.assertEqual(result["type_count_histogram"], {2: 3, 3: 2})
        self.assertEqual(result["attribute_counts"]["cyclewaytag|lane"], 2)
        self.assertEqual(result["attribute_counts"]["psurface|paved_good"], 3)


if __name__ == "__main__":
    unittest.main()
