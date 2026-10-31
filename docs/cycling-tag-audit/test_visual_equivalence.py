import json
from pathlib import Path
import tempfile
import unittest

from visual_equivalence import (compare_cycling_retention, compare_exports, digest, highway_profile,
                                pixel_metrics, verify_capture_binding)
from visual_phone import stabilize_camera, unlocked_foreground


def feature(fid, osm, kind, x):
    return {"kind": "feature", "id": fid, "osm_ids": [osm], "geometry_type": 1,
            "points": [[x, 1.0], [x + 1, 1.0]], "types": [["cyclewaytag", kind]],
            "names": {}, "ref": "", "layer": 0, "rank": 0, "house_number": "", "metadata": {}}


class VisualEquivalenceTests(unittest.TestCase):
    def test_phone_requires_an_unlocked_foreground_map(self):
        focus = "mCurrentFocus=Window{abc u0 app.organicmaps.cyclingfinal.debug/app.organicmaps.MwmActivity}"
        self.assertTrue(unlocked_foreground(focus, "\n showing=false\n"))
        self.assertFalse(unlocked_foreground(focus, "\n showing=true\n"))
        self.assertFalse(unlocked_foreground("mCurrentFocus=launcher", "\n showing=false\n"))
        self.assertFalse(unlocked_foreground("", "\n showing=false\n"))

    def test_reference_camera_requires_an_exact_serialization_fixed_point(self):
        values = iter(["rounded", "rounded"])
        stable, history = stabilize_camera("seed", lambda _: next(values))
        self.assertEqual(stable, "rounded")
        self.assertEqual(history, ["seed", "rounded", "rounded"])
        with self.assertRaises(ValueError):
            stabilize_camera("seed", lambda value: value + "x")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def export(self, name, features, offsets=(0.0, 1.0)):
        path = self.root / name
        records = [{"kind": "metadata", "offsets_present": False, "offsets_applied": False},
                   *features, {"kind": "chain", "features": [f["id"] for f in features],
                               "reversed": [False] * len(features), "offsets": list(offsets)}]
        path.write_text("".join(json.dumps(value) + "\n" for value in records))
        return path

    def test_numeric_feature_renumbering_preserves_semantic_identity(self):
        a = self.export("a", [feature(1, 100, "lane", 0), feature(2, 200, "track", 2)])
        b = self.export("b", [feature(9, 100, "lane", 0), feature(7, 200, "track", 2)])
        self.assertTrue(compare_exports(a, b)["exact_matched_data_equal"])

    def test_retained_type_order_is_compared(self):
        old = feature(1, 100, "lane", 0)
        old["types"].append(["highway", "residential"])
        new = {**old, "types": list(reversed(old["types"]))}
        a = self.export("a", [old], (0,))
        b = self.export("b", [new], (0,))
        self.assertFalse(compare_exports(a, b)["exact_matched_data_equal"])

    def test_highway_constraint_audit_does_not_hide_legacy_exceptions(self):
        ordinary = feature(1, 100, "lane", 0)
        ordinary["types"] += [["highway", "secondary"], ["highway", "secondary", "link"]]
        shared = {**feature(2, 200, "track", 2), "types": [["highway", "footway"], ["highway", "cycleway"]]}
        ford = {**feature(3, 300, "lane", 4), "types": [["highway", "footway"], ["highway", "ford"]]}
        invalid = {**feature(4, 400, "lane", 6), "types": [["highway", "secondary"], ["highway", "cycleway"]]}
        result = highway_profile({f["id"]: f for f in (ordinary, shared, ford, invalid)})
        self.assertEqual(result["multiple_highway_families"],
                         {"cycleway + footway": 1, "cycleway + secondary": 1, "footway + ford": 1})
        self.assertEqual([f["id"] for f in result["non_shared_path_examples"]], [3, 4])

    def test_equal_aggregate_types_can_hide_per_road_swaps(self):
        a = self.export("a", [feature(1, 100, "lane", 0), feature(2, 200, "track", 2)])
        b = self.export("b", [feature(1, 100, "track", 0), feature(2, 200, "lane", 2)])
        result = compare_exports(a, b)
        self.assertFalse(result["exact_matched_data_equal"])
        self.assertEqual(result["changed_feature_groups"], 2)
        self.assertEqual(compare_cycling_retention(a, b)["changed_cycling_type_groups"], 2)

    def test_retention_detects_displaced_access_even_with_same_cycleway(self):
        old = feature(1, 100, "lane", 0)
        old["types"].append(["hwtag", "nocar"])
        new = {**old, "types": [["cyclewaytag", "lane"], ["hwtag", "yescar"]]}
        a = self.export("a", [old], (0,))
        b = self.export("b", [new], (0,))
        self.assertFalse(compare_cycling_retention(a, b)["cycling_types_preserved"])

    def test_retention_does_not_hide_unrelated_identity_changes(self):
        cycling = feature(1, 100, "lane", 0)
        other = {**feature(2, 200, "track", 2), "types": [["junction", "roundabout"]]}
        renamed = {**other, "osm_ids": [300]}
        a = self.export("a", [cycling, other])
        b = self.export("b", [cycling, renamed])
        result = compare_cycling_retention(a, b)
        self.assertTrue(result["cycling_types_preserved"])
        self.assertEqual(result["changed_other_feature_groups"], 2)
        self.assertFalse(compare_exports(a, b)["exact_matched_data_equal"])

    def test_offset_change_is_detected(self):
        features = [feature(1, 100, "lane", 0), feature(2, 200, "track", 2)]
        a = self.export("a", features)
        b = self.export("b", features, (0.0, 1.5))
        result = compare_exports(a, b)
        self.assertFalse(result["exact_matched_data_equal"])
        self.assertGreater(result["chain_differences"], 0)

    def test_ambiguous_identity_is_not_certified(self):
        features = [feature(1, 100, "lane", 0), feature(2, 100, "lane", 0)]
        a = self.export("a", features)
        result = compare_exports(a, a)
        self.assertEqual(result["ambiguous_feature_groups"], 1)
        self.assertFalse(result["exact_matched_data_equal"])

    def test_empty_export_is_not_evidence(self):
        path = self.root / "empty"
        path.write_text("")
        with self.assertRaises(ValueError):
            compare_exports(path, path)

    def test_missing_source_identity_is_not_certified(self):
        item = feature(1, 100, "lane", 0)
        item["osm_ids"] = []
        path = self.export("a", [item], (0,))
        result = compare_exports(path, path)
        self.assertEqual(result["unidentified_features"], 2)
        self.assertFalse(result["exact_matched_data_equal"])

    def test_binary_metadata_differences_are_detected(self):
        old = feature(1, 100, "lane", 0)
        new = {**old, "metadata": {"1": [0, 128, 255]}}
        a = self.export("a", [old], (0,))
        b = self.export("b", [new], (0,))
        self.assertFalse(compare_exports(a, b)["exact_matched_data_equal"])

    def test_capture_must_bind_to_the_exported_map_and_source(self):
        export = self.export("a", [feature(1, 100, "lane", 0)], (0,))
        maps = self.root / "maps"
        maps.mkdir()
        mwm = maps / "fixture.mwm"
        mwm.write_bytes(b"fixture-map")
        manifest = {"export_sha256": digest(export), "map_sha256": digest(mwm), "source_commit": "source-a"}
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        captures = self.root / "captures"
        captures.mkdir()
        record = {"map_sha256": digest(mwm), "source_commit": "source-a"}
        path = captures / "capture.json"
        path.write_text(json.dumps(record))
        verify_capture_binding(export, captures)
        for key in record:
            path.write_text(json.dumps({**record, key: "other"}))
            with self.assertRaises(ValueError):
                verify_capture_binding(export, captures)
        path.write_text(json.dumps(record))
        original = export.read_text()
        export.write_text(original + "\n")
        with self.assertRaises(ValueError):
            verify_capture_binding(export, captures)
        export.write_text(original)
        mwm.write_bytes(b"different-map")
        with self.assertRaises(ValueError):
            verify_capture_binding(export, captures)

    def test_overlapping_chain_order_cannot_be_ignored(self):
        features = [feature(1, 100, "lane", 0), feature(2, 200, "track", 2), feature(3, 300, "lane", 4)]
        a = self.export("a", features, (0, 1, 2))
        records = [json.loads(line) for line in a.read_text().splitlines()]
        first = {"kind": "chain", "features": [1, 2], "reversed": [False, False], "offsets": [0, 1]}
        second = {"kind": "chain", "features": [2, 3], "reversed": [False, False], "offsets": [0, 1]}
        a.write_text("".join(json.dumps(r) + "\n" for r in records[:-1] + [first, second]))
        b = self.root / "b"
        b.write_text("".join(json.dumps(r) + "\n" for r in records[:-1] + [second, first]))
        result = compare_exports(a, b)
        self.assertEqual(result["chain_differences"], 0)
        self.assertTrue(result["overlapping_chain_order_changed"])
        self.assertFalse(result["exact_matched_data_equal"])

    def test_pixel_region_is_explicit_and_differences_are_not_tolerated(self):
        from PIL import Image
        a, b = self.root / "a.png", self.root / "b.png"
        original = Image.new("RGB", (4, 4), "white")
        original.save(a)
        changed = original.copy()
        changed.putpixel((0, 0), (0, 0, 0))
        changed.save(b)
        self.assertTrue(pixel_metrics(a, b, [1, 1, 4, 4])["exact_equal"])
        result = pixel_metrics(a, b, [0, 0, 4, 4])
        self.assertFalse(result["exact_equal"])
        self.assertEqual(result["changed_pixels"], 1)

    def test_invalid_pixel_region_is_rejected(self):
        from PIL import Image
        path = self.root / "a.png"
        Image.new("RGB", (4, 4)).save(path)
        with self.assertRaises(ValueError):
            pixel_metrics(path, path, [0, 0, 5, 4])


if __name__ == "__main__":
    unittest.main()
