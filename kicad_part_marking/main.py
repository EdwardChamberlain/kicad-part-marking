"""KiCad IPC action entrypoint for the part-marking plugin."""

from kipy import KiCad
from kipy.errors import ConnectionError

from part_marking.dialog import ask_marking_options, show_error
from part_marking.generator import create_and_place


def main() -> None:
    """Ask for part-marking settings, then create and place the marking."""
    options = ask_marking_options()
    if options is None:
        return

    try:
        kicad = KiCad()
        board = kicad.get_board()
    except ConnectionError as exc:
        show_error("KiCad connection failed", str(exc))
        return

    try:
        placed = create_and_place(board, options)
    except Exception as exc:
        show_error("Could not create part marking", str(exc))
        return

    if not placed:
        print("Unplaced QR part marking discarded.")


if __name__ == "__main__":
    main()
