import unittest
import xml.etree.ElementTree as ET

from prepare_junction_fixture import annotate, PREFIX


def fixture(shared=True, connector_tags="", node_tags="", interior=False, collinear=False):
    # Road runs east; connector approaches from the north (left).
    refs = '<nd ref="1"/><nd ref="2"/><nd ref="3"/>' if interior else '<nd ref="1"/><nd ref="2"/>'
    origin = "2" if shared else "4"
    lat = "0" if collinear else "0.001"
    return ET.fromstring(f'''<osm>
      <node id="1" lat="0" lon="0"/>
      <node id="2" lat="0" lon="0.001">{node_tags}</node>
      <node id="3" lat="0" lon="0.002"/>
      <node id="4" lat="0" lon="0.001"/>
      <node id="5" lat="{lat}" lon="0.002"/>
      <way id="10">{refs}<tag k="highway" v="secondary"/>
        <tag k="cycleway:left" v="lane"/></way>
      <way id="20"><nd ref="{origin}"/><nd ref="5"/>
        <tag k="highway" v="cycleway"/>{connector_tags}</way>
    </osm>''')


class JunctionFixtureTest(unittest.TestCase):
    def test_shared_node_authorizes_only_approached_side(self):
        root = fixture()
        self.assertEqual(annotate(root)["junction_sides"], 1)
        annotations = [t.get("k") for t in root.find("way").findall("tag") if t.get("k").startswith(PREFIX)]
        self.assertEqual(annotations, [PREFIX + "left"])

    def test_coincident_coordinates_without_shared_id_do_not_connect(self):
        self.assertEqual(annotate(fixture(shared=False))["junction_sides"], 0)

    def test_interior_shared_node_connects(self):
        self.assertEqual(annotate(fixture(interior=True))["junction_sides"], 1)

    def test_reversed_road_swaps_approached_side(self):
        root = fixture()
        refs = root.find("way").findall("nd")
        refs[0].set("ref", "2")
        refs[1].set("ref", "1")
        self.assertEqual(annotate(root)["roads"][0]["side"], "right")

    def test_restricted_or_grade_separated_connector_is_rejected(self):
        for key, value in (("bicycle", "no"), ("bicycle", "dismount"), ("access", "private"),
                           ("layer", "1"), ("level", "1"), ("area", "yes")):
            with self.subTest(key=key, value=value):
                root = fixture(connector_tags=f'<tag k="{key}" v="{value}"/>')
                self.assertEqual(annotate(root)["junction_sides"], 0)

    def test_node_barrier_or_restriction_is_rejected(self):
        for key, value in (("barrier", "gate"), ("bicycle", "no")):
            self.assertEqual(annotate(fixture(node_tags=f'<tag k="{key}" v="{value}"/>'))["junction_sides"], 0)

    def test_collinear_connection_does_not_guess_side(self):
        self.assertEqual(annotate(fixture(collinear=True))["junction_sides"], 0)

    def test_repeat_annotation_rejected(self):
        root = fixture()
        annotate(root)
        with self.assertRaises(ValueError):
            annotate(root)

    def test_geometry_and_access_tags_unchanged(self):
        root = fixture()
        nodes = [ET.tostring(n) for n in root.findall("node")]
        refs = [[n.get("ref") for n in w.findall("nd")] for w in root.findall("way")]
        old_tags = [[(t.get("k"), t.get("v")) for t in w.findall("tag")] for w in root.findall("way")]
        annotate(root)
        self.assertEqual(nodes, [ET.tostring(n) for n in root.findall("node")])
        self.assertEqual(refs, [[n.get("ref") for n in w.findall("nd")] for w in root.findall("way")])
        self.assertEqual(old_tags, [[(t.get("k"), t.get("v")) for t in w.findall("tag")
                                    if not t.get("k").startswith(PREFIX)] for w in root.findall("way")])


if __name__ == "__main__":
    unittest.main()
