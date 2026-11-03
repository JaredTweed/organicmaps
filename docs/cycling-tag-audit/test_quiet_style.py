from types import SimpleNamespace
import unittest

from audit_quiet_style import line_rules


class Line:
    def __init__(self, width, color):
        self.width, self.color = width, color

    def __str__(self):
        return f'{self.width}:{self.color}'


def container(width, color, selector='extra_tag=cyclewaytag=lane'):
    line = Line(width, color)
    element = SimpleNamespace(scale=15, apply_if=[selector], lines=[line])
    return SimpleNamespace(cont=[SimpleNamespace(name='highway-secondary', element=[element])]), line


class QuietStyleAuditTests(unittest.TestCase):
    def test_palette_comparison_does_not_ignore_geometry_or_mutate_input(self):
        a, original = container(2, 100)
        b, _ = container(2, 200)
        c, _ = container(3, 200)
        self.assertEqual(line_rules(a, True), line_rules(b, True))
        self.assertNotEqual(line_rules(a, False), line_rules(b, False))
        self.assertNotEqual(line_rules(a, True), line_rules(c, True))
        self.assertEqual(original.color, 100)

    def test_runtime_selector_is_part_of_line_identity(self):
        a, _ = container(2, 100)
        b, _ = container(2, 100, 'extra_tag=cyclewaytag=track')
        self.assertNotEqual(line_rules(a, True), line_rules(b, True))


if __name__ == '__main__':
    unittest.main()
