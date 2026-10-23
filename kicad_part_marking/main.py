"""KiCad IPC action: add a Micro QR part marking to the open board."""

import traceback

from kipy import KiCad

import dialog
import marking


def main() -> None:
    try:
        board = KiCad().get_board()
    except Exception as exc:
        traceback.print_exc()
        dialog.show_error("Can't connect to KiCad", f"{type(exc).__name__}: {exc}")
        return

    options = dialog.ask_options()
    if options is None:
        return

    try:
        marking.place_marking(board, options)
    except Exception as exc:
        traceback.print_exc()
        dialog.show_error("Could not create part marking", f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
