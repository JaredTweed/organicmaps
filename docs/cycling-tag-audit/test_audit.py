import unittest

from audit import audit, classifier_values, collisions, dump_summary, split_designation, type_mapping


class AuditTests(unittest.TestCase):
    def test_mapping_numbers(self):
        a = type_mapping("*building\n*highway|path\n")
        b = type_mapping("*building\n*cyclewaytag|lane\n*extra\n")
        self.assertEqual(collisions(a, b), [{
            "stored_index": 1, "csv_id": 2,
            "base": "highway|path", "experiment": "cyclewaytag|lane",
        }])

    def test_internal_values_use_sorted_tree_not_mapping_order(self):
        values = classifier_values(
            "world +\n    z +\n        lane -\n        {}\n    a -\n    {}\n"
        )
        self.assertEqual(values["a"], 128)
        self.assertEqual(values["z"], 129)
        self.assertEqual(values["z|lane"], 16385)

    def test_split_adds_slot_for_single_combined_type(self):
        self.assertEqual(len(split_designation({"highway|path|bicycle"})), 2)

    def test_split_reuses_existing_base(self):
        types = {"highway|path|bicycle", "highway|path"}
        self.assertEqual(len(split_designation(types)), 2)

    def test_split_shares_designation_across_two_classes(self):
        types = {"highway|path|bicycle", "highway|footway|bicycle"}
        self.assertEqual(len(split_designation(types)), 3)

    def test_weighted_dump(self):
        result = dump_summary(
            "100 building| \n3 highway|path|bicycle| hwtag|yesbicycle| \n"
            "Total features: 103\nFeatures with names: 0\n"
        )
        self.assertEqual(result["highway_features_by_stored_count"], {2: 3})
        self.assertEqual(result["hypothetical_designation_split_slot_deltas"], {1: 3})

    def test_invalid_dump_rejected(self):
        with self.assertRaises(ValueError):
            dump_summary("3 highway|path| highway|path|\n")

    def test_side_qualification_preserves_association(self):
        self.assertNotEqual({"left_track", "right_lane"}, {"left_lane", "right_track"})
        self.assertEqual({"left", "right", "lane", "track"},
                         {"right", "left", "track", "lane"})

    def test_pinned_source_conflicts_and_internal_values(self):
        result = audit()
        conflicts = {row["stored_index"]: row for row in result["mapping_differences"]}
        self.assertEqual(conflicts[1657]["base"], "railway|station|subway|suzhou")
        self.assertEqual(conflicts[1657]["experiment"], "cyclewaytag|track")
        self.assertEqual(conflicts[1658]["experiment"], "cyclewaytag|lane")
        lane = result["type_identity_examples"]["cyclewaytag|lane"]
        self.assertEqual(lane["stored_index"], 1658)
        self.assertEqual(lane["internal_classifier_value"], 16398)


if __name__ == "__main__":
    unittest.main()
