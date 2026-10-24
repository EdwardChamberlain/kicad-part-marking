"""Add a Micro QR part marking to the board open in KiCad.

Run with no arguments (as KiCad does) to get a settings dialog, or pass the
settings on the command line to skip it:

    python main.py --text "PN-1234 R2" --size 5 --side top
"""

import argparse
import sys
import traceback
from typing import List, Optional

from kipy import KiCad

import marking


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a Micro QR part marking to the open board.")
    parser.add_argument("--text", help="text to encode; giving this skips the dialog")
    parser.add_argument("--size", default="5", help="overall marking size in mm (default: 5)")
    parser.add_argument("--side", default="top", choices=["top", "bottom"], help="board side (default: top)")
    return parser.parse_args(argv)


def report(title: str, message: str, use_dialog: bool) -> None:
    print(f"{title}: {message}", file=sys.stderr)
    if use_dialog:
        import dialog

        dialog.show_error(title, message)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    use_dialog = args.text is None

    if use_dialog:
        try:
            import dialog
        except ImportError:
            print(
                "This Python has no Tk, so the settings dialog can't open.\n"
                "Pass the settings instead, e.g. --text \"PN-1234\" --size 5 --side top",
                file=sys.stderr,
            )
            return 2
    else:
        try:
            options = marking.parse_options(args.size, args.side.capitalize(), args.text.strip())
        except ValueError as exc:
            print(f"Invalid setting: {exc}", file=sys.stderr)
            return 2

    try:
        board = KiCad().get_board()
    except Exception as exc:
        traceback.print_exc()
        report("Can't connect to KiCad", f"{type(exc).__name__}: {exc}", use_dialog)
        return 1

    if use_dialog:
        options = dialog.ask_options()
        if options is None:
            return 0

    try:
        marking.place_marking(board, options)
    except Exception as exc:
        traceback.print_exc()
        report("Could not create part marking", f"{type(exc).__name__}: {exc}", use_dialog)
        return 1

    if not use_dialog:
        print("Marking created. Click in KiCad to place it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
