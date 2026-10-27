import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from regional_ab import annotate


class RegionalABTests(unittest.TestCase):
    def test_annotates_only_supported_unambiguous_ways(self):
        xml = '''<osm><way id="1"><tag k="highway" v="tertiary"/>
          <tag k="cycleway:left" v="lane"/><tag k="cycleway:right" v="lane"/></way>
          <way id="2"><tag k="highway" v="tertiary"/><tag k="cycleway:left" v="track"/>
          <tag k="cycleway:right" v="lane"/></way>
          <way id="3"><tag k="highway" v="residential"/><tag k="cycleway" v="track"/>
          <tag k="cycleway:left" v="no"/></way>
          <way id="4"><tag k="highway" v="path"/><tag k="cycleway" v="lane"/></way></osm>'''
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source.osm", Path(tmp) / "out.osm"
            source.write_text(xml)
            self.assertEqual(annotate(source, output), {"lane": 1})
            ways = list(ET.parse(output).getroot().iter("way"))
            markers = [w.findall("tag[@k='research:facility']") for w in ways]
            self.assertEqual([len(m) for m in markers], [1, 0, 0, 0])
            self.assertEqual(markers[0][0].get("v"), "lane")


if __name__ == "__main__":
    unittest.main()
