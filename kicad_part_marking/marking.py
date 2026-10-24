"""Build a Micro QR part marking and hand it to KiCad for placement.

The marking is two items, grouped:
- a Micro QR barcode on the solder-mask layer, so each module is a mask opening;
- a filled copper square with rounded corners underneath it.
"""

from __future__ import annotations

from dataclasses import dataclass
import string

from kipy.board import Board
from kipy.board_types import (
    Barcode,
    BarcodeErrorCorrection,
    BarcodeKind,
    BoardLayer,
    BoardRectangle,
    Group,
)
from kipy.geometry import Angle, Vector2
from kipy.util.units import from_mm

BORDER_MM = 0.1  # copper showing around the code on each edge
CORNER_RADIUS_MM = 0.1
DEFAULT_SIZE_MM = 3.0
MIN_SIDE_MM = 1.0
MAX_SIDE_MM = 50.0

# (copper layer, mask layer) for each board side.
LAYERS = {
    "Front": (BoardLayer.BL_F_Cu, BoardLayer.BL_F_Mask),
    "Back": (BoardLayer.BL_B_Cu, BoardLayer.BL_B_Mask),
}

# Largest Micro QR (M4) at error-correction level L.
_MAX_NUMERIC = 35
_MAX_ALPHANUMERIC = 21
_MAX_BYTES = 15
_ALPHANUMERIC = set(string.digits + string.ascii_uppercase + " $%*+-./:")


@dataclass(frozen=True)
class MarkingOptions:
    side_mm: float
    board_side: str
    text: str


def parse_options(side_text: str, board_side: str, text: str) -> MarkingOptions:
    """Check the dialog values. Raises ValueError with a message for the user."""
    try:
        side_mm = float(side_text)
    except ValueError:
        raise ValueError("Enter the marking size in millimetres.") from None
    if not MIN_SIDE_MM <= side_mm <= MAX_SIDE_MM:
        raise ValueError(f"The marking size must be between {MIN_SIDE_MM:g} and {MAX_SIDE_MM:g} mm.")
    if board_side not in LAYERS:
        raise ValueError("Choose Front or Back.")
    if not text:
        raise ValueError("Enter the text to encode.")
    check_capacity(text)
    return MarkingOptions(side_mm, board_side, text)


def check_capacity(text: str) -> None:
    """Raise ValueError if the text cannot fit in a Micro QR code at level L."""
    if text.isdigit() and text.isascii():
        limit, kind, length = _MAX_NUMERIC, "digits", len(text)
    elif set(text) <= _ALPHANUMERIC:
        limit, kind, length = _MAX_ALPHANUMERIC, "characters (A-Z, 0-9, space $%*+-./:)", len(text)
    else:
        limit, kind, length = _MAX_BYTES, "bytes of mixed or lower-case text", len(text.encode("utf-8"))
    if length > limit:
        raise ValueError(
            f"Too long for Micro QR: {length} {kind}, the limit is {limit}. "
            "Upper-case text fits more."
        )


def build_items(options: MarkingOptions, center: Vector2) -> tuple[Barcode, BoardRectangle]:
    """Create the barcode and copper backing, centred on `center`. Not yet on the board."""
    copper_layer, mask_layer = LAYERS[options.board_side]
    side = from_mm(options.side_mm)
    code_side = side - 2 * from_mm(BORDER_MM)

    barcode = Barcode()
    barcode.kind = BarcodeKind.BK_MICRO_QR_CODE
    barcode.error_correction = BarcodeErrorCorrection.BEC_L
    barcode.text = options.text
    barcode.layer = mask_layer
    barcode.position = center
    barcode.orientation = Angle.from_degrees(0)
    barcode.width = code_side
    barcode.height = code_side
    barcode.show_text = False
    barcode.knockout = False

    half = side // 2
    backing = BoardRectangle()
    backing.layer = copper_layer
    backing.top_left = Vector2.from_xy(center.x - half, center.y - half)
    backing.bottom_right = Vector2.from_xy(center.x - half + side, center.y - half + side)
    # kicad-python has no wrapper property for the corner radius yet.
    backing.proto.shape.rectangle.corner_radius.value_nm = from_mm(CORNER_RADIUS_MM)
    backing.attributes.fill.filled = True

    return barcode, backing


def board_center(board: Board) -> Vector2:
    """Centre of the board outline, so the marking starts somewhere visible."""
    edges = [shape for shape in board.get_shapes() if shape.layer == BoardLayer.BL_Edge_Cuts]
    boxes = board.get_item_bounding_box(edges) if edges else []
    if not boxes:
        return Vector2.from_xy(0, 0)
    left = min(box.pos.x for box in boxes)
    top = min(box.pos.y for box in boxes)
    right = max(box.pos.x + box.size.x for box in boxes)
    bottom = max(box.pos.y + box.size.y for box in boxes)
    return Vector2.from_xy((left + right) // 2, (top + bottom) // 2)


def place_marking(board: Board, options: MarkingOptions) -> None:
    """Add the grouped marking to the board and start KiCad's interactive move.

    Escape during the move leaves the marking where it started; undoing twice removes it.
    """
    barcode, backing = build_items(options, board_center(board))

    commit = board.begin_commit()
    try:
        members = board.create_items([barcode, backing])
        board.push_commit(commit, "Add part marking")
    except Exception:
        board.drop_commit(commit)
        raise

    # KiCad resolves group members against the board, so the members must be
    # committed before the group is created, or the group comes out empty.
    group = Group()
    group.items = members
    created = board.create_items(group)
    if len(created) != 1 or len(created[0].proto.items) != len(members):
        raise RuntimeError("KiCad did not group the barcode and copper backing.")

    board.interactive_move(created[0].id)
