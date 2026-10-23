"""Small standard-library dialog for part-marking settings."""

from __future__ import annotations

from dataclasses import dataclass
import math
import tkinter as tk
from tkinter import messagebox, ttk


COPPER_BORDER_MM = 0.1


@dataclass(frozen=True)
class MarkingOptions:
    side_mm: float
    board_side: str
    text: str


def ask_marking_options() -> MarkingOptions | None:
    """Return the user settings, or None when the dialog is cancelled."""
    root = tk.Tk()
    root.title("Generate Part Marking")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=14)
    frame.grid(sticky="nsew")
    frame.columnconfigure(1, weight=1)

    side_var = tk.StringVar(value="5.0")
    board_side_var = tk.StringVar(value="Top")
    text_var = tk.StringVar()
    result: list[MarkingOptions | None] = [None]

    ttk.Label(frame, text="QR code side (mm)").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
    ttk.Entry(frame, textvariable=side_var, width=18).grid(row=0, column=1, sticky="ew", pady=5)
    ttk.Label(
        frame,
        text="Includes the 0.1 mm copper border on each edge.",
    ).grid(row=1, column=1, sticky="w", pady=(0, 7))

    ttk.Label(frame, text="Side").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
    ttk.Combobox(
        frame,
        textvariable=board_side_var,
        values=("Top", "Bottom"),
        state="readonly",
        width=15,
    ).grid(row=2, column=1, sticky="ew", pady=5)

    ttk.Label(frame, text="Code text").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=5)
    ttk.Entry(frame, textvariable=text_var, width=38).grid(row=3, column=1, sticky="ew", pady=5)

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))

    def accept() -> None:
        try:
            side_mm = float(side_var.get())
        except ValueError:
            messagebox.showerror("Invalid size", "Enter the QR code side in millimetres.", parent=root)
            return

        if not math.isfinite(side_mm) or side_mm <= 2 * COPPER_BORDER_MM:
            messagebox.showerror(
                "Invalid size",
                "The overall side must be greater than 0.2 mm so the QR code has a positive size.",
                parent=root,
            )
            return

        if not text_var.get():
            messagebox.showerror("Missing code text", "Enter the text to encode.", parent=root)
            return

        result[0] = MarkingOptions(side_mm, board_side_var.get(), text_var.get())
        root.destroy()

    ttk.Button(buttons, text="Cancel", command=root.destroy).grid(row=0, column=0, padx=(0, 7))
    ttk.Button(buttons, text="Generate", command=accept).grid(row=0, column=1)
    root.bind("<Return>", lambda _event: accept())
    root.bind("<Escape>", lambda _event: root.destroy())

    root.update_idletasks()
    root.transient()
    root.grab_set()
    root.mainloop()
    return result[0]


def show_error(title: str, message: str) -> None:
    """Show a native dialog for errors that occur after settings are accepted."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message, parent=root)
    root.destroy()
