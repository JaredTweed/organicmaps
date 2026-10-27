import tempfile
import unittest
from pathlib import Path

from source_probe import inspect_source


class SourceProbeTests(unittest.TestCase):
    def test_preserves_asymmetry_and_designation_uncertainty(self):
        xml = '''<osm><meta osm_base="fixture"/><node id="1" lat="1" lon="1"/>
          <way id="7"><tag k="highway" v="path"/><tag k="bicycle" v="designated"/>
            <tag k="cycleway:left" v="track"/><tag k="cycleway:right" v="lane"/></way>
          <way id="8"><tag k="highway" v="residential"/><tag k="cycleway" v="lane"/>
            <tag k="cycleway:left" v="no"/><tag k="cycleway:right:oneway" v="-1"/></way>
          <way id="9"><tag k="waterway" v="stream"/></way></osm>'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.osm"
            source.write_text(xml)
            result = inspect_source(source)
        counts = result["counts"]
        self.assertEqual(counts["highway_ways"], 2)
        self.assertEqual(counts["ways_with_explicit_differing_sides"], 1)
        self.assertEqual(counts["ways_with_multiple_positive_categories"], 1)
        self.assertEqual(counts["designated_path_footway_with_additional_facility_tags"], 1)
        self.assertEqual(counts["ways_with_negative_or_separate_and_positive_values"], 1)
        self.assertEqual(result["source_metadata"]["osm_base"], "fixture")


if __name__ == "__main__":
    unittest.main()
