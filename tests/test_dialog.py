"""Tests for the Qt dialog, run offscreen: python -m unittest discover -s tests"""

import os
from pathlib import Path
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad_part_marking"))

import dialog  # noqa: E402
from marking import MarkingOptions  # noqa: E402


class DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dialog._app()

    def test_defaults(self):
        d = dialog.MarkingDialog()
        self.assertEqual(d.size_edit.text(), "5")
        self.assertEqual(d.side_combo.currentText(), "Front")
        self.assertEqual([d.side_combo.itemText(i) for i in range(d.side_combo.count())], ["Front", "Back"])

    def test_ok_with_valid_settings(self):
        d = dialog.MarkingDialog()
        d.text_edit.setText("  PN-1234 R2 ")
        d.size_edit.setText("4")
        d.side_combo.setCurrentText("Back")
        d.accept()
        self.assertEqual(d.options, MarkingOptions(4.0, "Back", "PN-1234 R2"))
        self.assertEqual(d.result(), dialog.QDialog.DialogCode.Accepted)

    def test_ok_with_bad_settings_warns_and_stays_open(self):
        d = dialog.MarkingDialog()
        d.text_edit.setText("x" * 40)
        with mock.patch.object(dialog.QMessageBox, "warning") as warning:
            d.accept()
        self.assertIsNone(d.options)
        self.assertIn("Too long", warning.call_args.args[2])

    def test_cancel_returns_nothing(self):
        d = dialog.MarkingDialog()
        d.text_edit.setText("PN-1234")
        d.reject()
        self.assertIsNone(d.options)


if __name__ == "__main__":
    unittest.main()
