import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from audit import ROOT
from run_validation import validate
from style_probe import ROADS, selected_lines, write_fixture


class StyleProbeTests(unittest.TestCase):
    def test_fixture_mapping_has_contiguous_ids(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_fixture(directory, "combined", ROADS[:3])
            with (directory / "mapcss-mapping.csv").open() as stream:
                rows = list(csv.reader(stream, delimiter=";"))
            self.assertEqual(len(rows), 12)
            self.assertEqual([int(row[5]) for row in rows], list(range(1, 13)))

    def test_tag_vocabulary_is_not_cartesian(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_fixture(directory, "tags", ROADS)
            with (directory / "mapcss-mapping.csv").open() as stream:
                self.assertEqual(len(list(csv.reader(stream, delimiter=";"))), 11)

    def test_fixture_does_not_reuse_old_palettes(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "colors.txt").write_text("123\n")
            (directory / "patterns.txt").write_text("1 2\n")
            write_fixture(directory, "tags", ROADS[:3])
            self.assertFalse((directory / "colors.txt").exists())
            self.assertFalse((directory / "patterns.txt").exists())

    @staticmethod
    def container(predicates):
        return SimpleNamespace(cont=[SimpleNamespace(
            name="highway-tertiary", element=[SimpleNamespace(
                scale=14, apply_if=predicates,
                lines=[SimpleNamespace(width=2, color=0x2266BB, priority=100)])])])

    def test_predicates_are_conjunctive(self):
        container = self.container(["extra_tag=cyclewaytag=track", "extra_tag!=hwtag=yescar"])
        self.assertEqual(selected_lines(container, {"highway-tertiary", "cyclewaytag-track"}, 14),
                         [(2, 0x2266BB, 100)])
        self.assertEqual(selected_lines(container, {
            "highway-tertiary", "cyclewaytag-track", "hwtag-yescar"}, 14), [])

    def test_absent_type_and_zoom_do_not_select(self):
        container = self.container(["extra_tag=cyclewaytag=track"])
        self.assertEqual(selected_lines(container, {"highway-tertiary"}, 14), [])
        self.assertEqual(selected_lines(container, {"highway-tertiary", "cyclewaytag-track"}, 13), [])

    def test_unknown_predicate_is_not_unconditional(self):
        with self.assertRaises(AssertionError):
            selected_lines(self.container(["unhandled=foo"]), {"highway-tertiary"}, 14)

    def test_runner_refuses_generated_output_in_worktree(self):
        with self.assertRaises(ValueError):
            validate(Path("/not-used"), ROOT / "data")


if __name__ == "__main__":
    unittest.main()
