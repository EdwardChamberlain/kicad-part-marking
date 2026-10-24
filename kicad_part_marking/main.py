"""Add a Micro QR part marking to the board open in KiCad.

Run with no arguments (as KiCad does) to get a settings dialog, or pass the
settings on the command line to skip it:

    python main.py --text "PN-1234 R2" --size 3 --side front
"""

import argparse
import sys
import traceback
from typing import List, Optional

from kipy import KiCad

import marking


# KiCad says Front/Back; top/bottom are accepted too.
_SIDES = {"front": "Front", "back": "Back", "top": "Front", "bottom": "Back"}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a Micro QR part marking to the open board.")
    parser.add_argument("--text", help="text to encode; giving this skips the dialog")
    parser.add_argument(
        "--size",
        default=str(marking.DEFAULT_SIZE_MM),
        help=f"overall marking size in mm (default: {marking.DEFAULT_SIZE_MM:g})",
    )
    parser.add_argument(
        "--side",
        default="front",
        choices=list(_SIDES),
        help="board side: front or back (default: front)",
    )
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
                "PySide6 isn't installed, so the settings dialog can't open.\n"
                "Install kicad_part_marking/requirements.txt, or pass the settings instead,\n"
                "e.g. --text \"PN-1234\" --size 3 --side front",
                file=sys.stderr,
            )
            return 2
    else:
        try:
            options = marking.parse_options(args.size, _SIDES[args.side], args.text.strip())
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
