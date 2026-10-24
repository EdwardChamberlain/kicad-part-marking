"""Qt dialogs for the part-marking settings and errors.

Laid out like KiCad's own dialogs: label / field / units rows, native
OK/Cancel buttons bottom right, and the platform's native style so it
follows light and dark mode the way KiCad does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from marking import BORDER_MM, LAYERS, MarkingOptions, parse_options

ICON = Path(__file__).with_name("icon-64.png")


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setWindowIcon(QIcon(str(ICON)))
    return app


def _bring_to_front(widget) -> None:
    # KiCad starts the plugin as a separate process, so the window can open behind KiCad.
    widget.show()
    widget.raise_()
    widget.activateWindow()


class MarkingDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Generate Part Marking")
        self.options: Optional[MarkingOptions] = None

        self.size_edit = QLineEdit("5")
        self.side_combo = QComboBox()
        self.side_combo.addItems(list(LAYERS))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("e.g. PN-1234 R2")
        self.text_edit.setMinimumWidth(240)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.addWidget(QLabel("Code text:"), 0, 0)
        grid.addWidget(self.text_edit, 0, 1, 1, 2)
        grid.addWidget(QLabel("Size:"), 1, 0)
        grid.addWidget(self.size_edit, 1, 1)
        grid.addWidget(QLabel("mm"), 1, 2)
        grid.addWidget(QLabel("Side:"), 2, 0)
        grid.addWidget(self.side_combo, 2, 1, 1, 2)

        note = QLabel(f"Size is the overall square, including a {BORDER_MM:g} mm copper border.")
        note.setEnabled(False)  # greyed, like KiCad's help text

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addWidget(note)
        layout.addSpacing(6)
        layout.addWidget(buttons)
        self.setFixedSize(self.sizeHint())
        self.text_edit.setFocus()

    def accept(self) -> None:
        try:
            self.options = parse_options(
                self.size_edit.text().strip(),
                self.side_combo.currentText(),
                self.text_edit.text().strip(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Generate Part Marking", str(exc))
            return
        super().accept()


def ask_options() -> Optional[MarkingOptions]:
    """Show the settings dialog. Returns None if the user cancels."""
    _app()
    dialog = MarkingDialog()
    _bring_to_front(dialog)
    dialog.exec()
    return dialog.options


def show_error(title: str, message: str) -> None:
    _app()
    box = QMessageBox(QMessageBox.Icon.Critical, title, message)
    _bring_to_front(box)
    box.exec()
