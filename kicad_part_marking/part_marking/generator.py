"""Create and place a native KiCad Micro QR and copper backing group."""

from __future__ import annotations

import math
import time

from kipy.board import Board
from kipy.board_types import (
    Barcode,
    BarcodeErrorCorrection,
    BarcodeKind,
    BoardLayer,
    BoardPolygon,
    Group,
)
from kipy.client import ApiError
from kipy.geometry import Angle, ArcStartMidEnd, PolyLine, PolyLineNode, PolygonWithHoles, Vector2
from kipy.proto.common.envelope_pb2 import ApiStatusCode
from kipy.util.units import from_mm

from .dialog import COPPER_BORDER_MM, MarkingOptions


# New objects start safely outside normal board extents. If the user cancels
# KiCad's interactive move, the barcode remains at this sentinel position.
_PLACEMENT_SENTINEL_MM = -1000.0
_CORNER_RADIUS_MM = 0.1
_PLACEMENT_POLL_SECONDS = 0.2


def _rounded_rectangle(
    left: int,
    top: int,
    right: int,
    bottom: int,
    radius: int,
) -> PolygonWithHoles:
    """Build a closed, true-arc rounded rectangle outline."""
    diagonal = int(round(radius / math.sqrt(2)))
    outline = PolyLine()

    def point(x: int, y: int) -> PolyLineNode:
        return PolyLineNode.from_point(Vector2.from_xy(x, y))

    def arc(start: tuple[int, int], mid: tuple[int, int], end: tuple[int, int]) -> PolyLineNode:
        shape = ArcStartMidEnd()
        shape.start = Vector2.from_xy(*start)
        shape.mid = Vector2.from_xy(*mid)
        shape.end = Vector2.from_xy(*end)
        node = PolyLineNode()
        node.arc = shape
        return node

    outline.append(point(left + radius, top))
    outline.append(point(right - radius, top))
    outline.append(
        arc(
            (right - radius, top),
            (right - radius + diagonal, top + radius - diagonal),
            (right, top + radius),
        )
    )
    outline.append(point(right, bottom - radius))
    outline.append(
        arc(
            (right, bottom - radius),
            (right - radius + diagonal, bottom - radius + diagonal),
            (right - radius, bottom),
        )
    )
    outline.append(point(left + radius, bottom))
    outline.append(
        arc(
            (left + radius, bottom),
            (left + radius - diagonal, bottom - radius + diagonal),
            (left, bottom - radius),
        )
    )
    outline.append(point(left, top + radius))
    outline.append(
        arc(
            (left, top + radius),
            (left + radius - diagonal, top + radius - diagonal),
            (left + radius, top),
        )
    )
    outline.closed = True

    polygon = PolygonWithHoles()
    polygon.outline = outline
    return polygon


def _make_copper_backing(side_mm: float, layer: int, center: Vector2) -> BoardPolygon:
    side_nm = from_mm(side_mm)
    half_side = side_nm // 2
    radius = from_mm(_CORNER_RADIUS_MM)
    copper = BoardPolygon()
    copper.layer = layer
    copper.attributes.fill.filled = True
    copper.polygons.append(
        _rounded_rectangle(
            center.x - half_side,
            center.y - half_side,
            center.x + (side_nm - half_side),
            center.y + (side_nm - half_side),
            radius,
        )
    )
    return copper


def _wait_for_move(board: Board, barcode_id) -> Barcode:
    """Poll until KiCad finishes its asynchronous interactive placement."""
    while True:
        try:
            items = board.get_items_by_id([barcode_id])
            if not items:
                raise RuntimeError("KiCad no longer has the generated QR code.")
            barcode = items[0]
            if not isinstance(barcode, Barcode):
                raise RuntimeError("KiCad returned an unexpected item for the generated QR code.")
            return barcode
        except ApiError as exc:
            if exc.code != ApiStatusCode.AS_BUSY:
                raise
            time.sleep(_PLACEMENT_POLL_SECONDS)


def _discard_group(board: Board, group: Group, barcode: Barcode, backing: BoardPolygon) -> None:
    """Remove the group and both members as one cleanup operation."""
    commit = board.begin_commit()
    try:
        board.remove_items([group, barcode, backing])
        board.push_commit(commit, "Discard unplaced part marking")
    except Exception:
        board.drop_commit(commit)
        raise


def create_and_place(board: Board, options: MarkingOptions) -> bool:
    """Create the grouped marking and start cursor placement.

    Return True when placed and False when Escape discarded it.
    """
    side_nm = from_mm(options.side_mm)
    code_side_nm = side_nm - 2 * from_mm(COPPER_BORDER_MM)
    center = Vector2.from_xy_mm(_PLACEMENT_SENTINEL_MM, _PLACEMENT_SENTINEL_MM)

    if options.board_side == "Top":
        copper_layer = BoardLayer.BL_F_Cu
        mask_layer = BoardLayer.BL_F_Mask
    else:
        copper_layer = BoardLayer.BL_B_Cu
        mask_layer = BoardLayer.BL_B_Mask

    barcode = Barcode()
    barcode.text = options.text
    barcode.kind = BarcodeKind.BK_MICRO_QR_CODE
    barcode.error_correction = BarcodeErrorCorrection.BEC_L
    barcode.position = center
    barcode.orientation = Angle.from_degrees(0)
    barcode.layer = mask_layer
    barcode.width = code_side_nm
    barcode.height = code_side_nm
    barcode.show_text = False
    barcode.knockout = False
    backing = _make_copper_backing(options.side_mm, copper_layer, center)

    commit = board.begin_commit()
    try:
        created = board.create_items([barcode, backing])
        created_barcode = next(item for item in created if isinstance(item, Barcode))
        created_backing = next(item for item in created if isinstance(item, BoardPolygon))

        group = Group()
        group.items = [created_barcode, created_backing]
        created_group = board.create_items(group)[0]
        if not isinstance(created_group, Group):
            raise RuntimeError("KiCad did not create the marking group.")
        board.push_commit(commit, "Create QR part marking")
    except Exception:
        board.drop_commit(commit)
        raise

    try:
        board.interactive_move(created_group.id)
        placed_barcode = _wait_for_move(board, created_barcode.id)
    except Exception:
        # If the interactive tool could not start, remove the temporary group.
        _discard_group(board, created_group, created_barcode, created_backing)
        raise

    if placed_barcode.position == center:
        _discard_group(board, created_group, created_barcode, created_backing)
        return False
    return True
