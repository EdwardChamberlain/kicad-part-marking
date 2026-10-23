"""Tk dialogs for the part-marking settings and errors."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from marking import BORDER_MM, LAYERS, MarkingOptions, parse_options


def _new_root(title: str) -> tk.Tk:
    root = tk.Tk()
    root.title(title)
    # KiCad launches the plugin as a separate process, so bring the window to the front.
    root.lift()
    root.attributes("-topmost", True)
    root.after_idle(root.attributes, "-topmost", False)
    return root


def ask_options() -> Optional[MarkingOptions]:
    """Show the settings dialog. Returns None if the user cancels."""
    root = _new_root("Generate Part Marking")
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=14)
    frame.grid()

    side_var = tk.StringVar(value="5.0")
    board_side_var = tk.StringVar(value="Top")
    text_var = tk.StringVar()
    result: list = [None]

    def row(label: str, widget: tk.Widget, line: int) -> None:
        ttk.Label(frame, text=label).grid(row=line, column=0, sticky="w", padx=(0, 12), pady=5)
        widget.grid(row=line, column=1, sticky="ew", pady=5)

    row("Marking size (mm)", ttk.Entry(frame, textvariable=side_var, width=18), 0)
    ttk.Label(frame, text=f"Overall square, including {BORDER_MM:g} mm copper border.").grid(
        row=1, column=1, sticky="w"
    )
    row("Side", ttk.Combobox(frame, textvariable=board_side_var, values=list(LAYERS), state="readonly"), 2)
    text_entry = ttk.Entry(frame, textvariable=text_var, width=38)
    row("Code text", text_entry, 3)

    def accept(_event=None) -> None:
        try:
            result[0] = parse_options(side_var.get().strip(), board_side_var.get(), text_var.get().strip())
        except ValueError as exc:
            messagebox.showerror("Invalid setting", str(exc), parent=root)
            return
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(buttons, text="Cancel", command=root.destroy).grid(row=0, column=0, padx=(0, 7))
    ttk.Button(buttons, text="Generate", command=accept).grid(row=0, column=1)
    root.bind("<Return>", accept)
    root.bind("<Escape>", lambda _event: root.destroy())

    text_entry.focus_force()
    root.mainloop()
    return result[0]


def show_error(title: str, message: str) -> None:
    root = _new_root(title)
    root.withdraw()
    messagebox.showerror(title, message, parent=root)
    root.destroy()
