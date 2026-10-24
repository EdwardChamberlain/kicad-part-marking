"""Tests for the command-line entrypoint: python -m unittest discover -s tests"""

import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad_part_marking"))

import main  # noqa: E402


def run(argv):
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = main.main(argv)
    return code, err.getvalue()


class MainTests(unittest.TestCase):
    def test_invalid_cli_settings_fail_before_connecting(self):
        with mock.patch.object(main, "KiCad") as kicad:
            code, err = run(["--text", "a" * 40])
        self.assertEqual(code, 2)
        self.assertIn("Too long", err)
        kicad.assert_not_called()

    def test_cli_mode_places_without_dialog(self):
        with mock.patch.object(main, "KiCad") as kicad, \
                mock.patch.object(main.marking, "place_marking") as place, \
                mock.patch.dict(sys.modules, {"PySide6": None, "dialog": None}):
            code, _ = run(["--text", "PN-1234", "--size", "4", "--side", "bottom"])
        self.assertEqual(code, 0)
        options = place.call_args.args[1]
        self.assertEqual((options.side_mm, options.board_side, options.text), (4.0, "Back", "PN-1234"))
        kicad.return_value.get_board.assert_called_once()

    def test_missing_pyside_gives_clear_message(self):
        with mock.patch.dict(sys.modules, {"PySide6": None, "dialog": None}), \
                mock.patch.object(main, "KiCad") as kicad:
            code, err = run([])
        self.assertEqual(code, 2)
        self.assertIn("PySide6 isn't installed", err)
        kicad.assert_not_called()

    def test_default_size_is_3mm(self):
        with mock.patch.object(main, "KiCad"), mock.patch.object(main.marking, "place_marking") as place:
            run(["--text", "PN-1234"])
        self.assertEqual(place.call_args.args[1].side_mm, 3.0)

    def test_connection_failure_is_reported(self):
        with mock.patch.object(main, "KiCad", side_effect=ConnectionError("no socket")):
            code, err = run(["--text", "PN-1234"])
        self.assertEqual(code, 1)
        self.assertIn("ConnectionError: no socket", err)


if __name__ == "__main__":
    unittest.main()
