from types import SimpleNamespace
import unittest

from clean_style import derive


class Overlay:
    def __init__(self, visible=False):
        self.visible = visible

    def _is_set(self):
        return self.visible


def element():
    return SimpleNamespace(symbol=Overlay(True), caption=Overlay(True), path_text=Overlay(True),
                           shield=Overlay(True), lines=[SimpleNamespace(width=5)], area="retained")


class CleanStyleTests(unittest.TestCase):
    def test_clutter_removal_preserves_geometry_and_cycling_services(self):
        original = SimpleNamespace(cont=[SimpleNamespace(name=name, element=[element()]) for name in
                                        ("shop-clothes", "amenity-bicycle_repair_station", "highway-crossing",
                                         "amenity-drinking_water", "highway-primary")])
        clean, removed = derive(original)
        self.assertEqual(removed, ["shop-clothes"])
        self.assertFalse(clean.cont[0].element[0].symbol.visible)
        self.assertEqual(clean.cont[0].element[0].area, "retained")
        for entry in clean.cont[1:]:
            self.assertTrue(entry.element[0].symbol.visible)
        self.assertEqual(clean.cont[-1].element[0].lines[0].width, 4)
        self.assertTrue(original.cont[0].element[0].symbol.visible)
        self.assertEqual(original.cont[-1].element[0].lines[0].width, 5)


if __name__ == "__main__":
    unittest.main()
