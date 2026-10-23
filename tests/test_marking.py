"""Tests for marking.py that run without KiCad: python -m unittest discover tests"""

from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad_part_marking"))

from kipy.board_types import Barcode, BarcodeKind, BoardLayer, BoardRectangle, Group  # noqa: E402
from kipy.geometry import Box2, Vector2  # noqa: E402
from kipy.util import pack_any  # noqa: E402
from kipy.board_types import unwrap  # noqa: E402

import marking  # noqa: E402


class FakeBoard:
    """Mimics the KiCad behaviour that broke the original plugin:
    created items come back as generic types, and group members are looked
    up among committed items only."""

    def __init__(self, edges=()):
        self.edges = list(edges)
        self.committed = {}
        self.pending = None
        self.moved = None

    def get_shapes(self):
        return self.edges

    def get_item_bounding_box(self, items):
        return [Box2.from_xywh(*item) for item in items]

    def begin_commit(self):
        self.pending = {}
        return object()

    def push_commit(self, _commit, _message=""):
        self.committed.update(self.pending)
        self.pending = None

    def drop_commit(self, _commit):
        self.pending = None

    def create_items(self, items):
        items = [items] if not isinstance(items, list) else items
        created = []
        for item in items:
            proto = type(item.proto)()
            proto.CopyFrom(item.proto)
            proto.id.value = str(uuid.uuid4())
            if isinstance(item, Group):
                kept = [i for i in proto.items if i.value in self.committed]
                del proto.items[:]
                proto.items.extend(kept)
            result = unwrap(pack_any(proto))
            (self.pending if self.pending is not None else self.committed)[proto.id.value] = result
            created.append(result)
        return created

    def interactive_move(self, item_id):
        self.moved = item_id


class FakeEdge:
    layer = BoardLayer.BL_Edge_Cuts

    def __init__(self, x, y, w, h):
        self.box = (x, y, w, h)

    def __iter__(self):
        return iter(self.box)


class ParseOptionsTests(unittest.TestCase):
    def test_valid(self):
        options = marking.parse_options("5", "Bottom", "PN-1234 R2")
        self.assertEqual(options, marking.MarkingOptions(5.0, "Bottom", "PN-1234 R2"))

    def test_rejects_bad_size(self):
        for value in ("", "abc", "0.2", "nan", "inf", "100"):
            with self.assertRaises(ValueError, msg=value):
                marking.parse_options(value, "Top", "A")

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            marking.parse_options("5", "Top", "")

    def test_capacity_limits(self):
        marking.check_capacity("1" * 35)
        marking.check_capacity("A" * 21)
        marking.check_capacity("a" * 15)
        for too_long in ("1" * 36, "A" * 22, "a" * 16):
            with self.assertRaises(ValueError, msg=too_long):
                marking.check_capacity(too_long)


class BuildItemsTests(unittest.TestCase):
    def test_geometry_and_layers(self):
        center = Vector2.from_xy_mm(10, 20)
        barcode, backing = marking.build_items(marking.MarkingOptions(5.0, "Top", "AB12"), center)

        self.assertEqual(barcode.kind, BarcodeKind.BK_MICRO_QR_CODE)
        self.assertEqual(barcode.layer, BoardLayer.BL_F_Mask)
        self.assertEqual(barcode.width, 4_800_000)
        self.assertEqual(barcode.height, 4_800_000)
        self.assertEqual(barcode.position, center)

        self.assertEqual(backing.layer, BoardLayer.BL_F_Cu)
        self.assertEqual(backing.top_left, Vector2.from_xy_mm(7.5, 17.5))
        self.assertEqual(backing.bottom_right, Vector2.from_xy_mm(12.5, 22.5))
        self.assertEqual(backing.proto.shape.rectangle.corner_radius.value_nm, 100_000)
        self.assertTrue(backing.attributes.fill.filled)

    def test_bottom_layers(self):
        barcode, backing = marking.build_items(marking.MarkingOptions(3.0, "Bottom", "1"), Vector2())
        self.assertEqual(barcode.layer, BoardLayer.BL_B_Mask)
        self.assertEqual(backing.layer, BoardLayer.BL_B_Cu)


class PlaceMarkingTests(unittest.TestCase):
    def test_group_has_both_items_and_is_moved(self):
        board = FakeBoard(edges=[FakeEdge(0, 0, 100_000_000, 50_000_000)])
        marking.place_marking(board, marking.MarkingOptions(5.0, "Top", "AB12"))

        groups = [i for i in board.committed.values() if isinstance(i, Group)]
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].proto.items), 2)
        self.assertEqual(board.moved, groups[0].id)

        barcode = next(i for i in board.committed.values() if isinstance(i, Barcode))
        self.assertEqual(barcode.position, Vector2.from_xy_mm(50, 25))

    def test_no_board_outline_starts_at_origin(self):
        board = FakeBoard()
        marking.place_marking(board, marking.MarkingOptions(5.0, "Top", "AB12"))
        barcode = next(i for i in board.committed.values() if isinstance(i, Barcode))
        self.assertEqual(barcode.position, Vector2.from_xy(0, 0))


if __name__ == "__main__":
    unittest.main()
