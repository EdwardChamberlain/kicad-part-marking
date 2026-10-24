#!/usr/bin/env python3
"""Generate the plugin icons: a gold (ENIG) Micro QR code on green solder mask.

The code encodes "Hello PCB!". Each size uses whole-pixel modules so the code
stays sharp, and keeps the 2-module quiet zone Micro QR needs.

Needs segno (pip install -r requirements-build.txt). Run directly, or let
scripts/build_plugin.py run it.
"""

from pathlib import Path
import struct
import zlib

import segno

ROOT = Path(__file__).resolve().parents[1]
TEXT = "Hello PCB!"
MASK_GREEN = (0x1B, 0x6B, 0x3A)
ENIG_GOLD = (0xE2, 0xBC, 0x5E)
QUIET_ZONE = 2  # modules, as the Micro QR spec requires

# Output file -> size in pixels. Toolbar icons at 1x/2x/large, plus the PCM icon (64x64).
OUTPUTS = {
    ROOT / "kicad_part_marking" / "icon-24.png": 24,
    ROOT / "kicad_part_marking" / "icon-48.png": 48,
    ROOT / "kicad_part_marking" / "icon-64.png": 64,
    ROOT / "pcm" / "icon.png": 64,
}


def micro_qr_matrix(text: str) -> list:
    qr = segno.make_micro(text, error="L", boost_error=False)
    return [[bool(module) for module in row] for row in qr.matrix]


def corner_alpha(x: int, y: int, size: int, radius: float) -> int:
    """Opacity of pixel (x, y) in a rounded square, 4x4 supersampled at the corners."""
    inside = 0
    for sy in range(4):
        for sx in range(4):
            px, py = x + (sx + 0.5) / 4, y + (sy + 0.5) / 4
            cx = min(max(px, radius), size - radius)
            cy = min(max(py, radius), size - radius)
            inside += (px - cx) ** 2 + (py - cy) ** 2 <= radius ** 2
    return round(255 * inside / 16)


def render(matrix: list, size: int) -> bytes:
    """RGBA pixels for one icon size."""
    modules = len(matrix)
    scale = size // (modules + 2 * QUIET_ZONE)
    if scale < 1:
        raise ValueError(f"{size} px is too small for a {modules}-module code with its quiet zone.")
    offset = (size - modules * scale) // 2
    radius = size / 8

    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            mx, my = (x - offset) // scale, (y - offset) // scale
            gold = 0 <= mx < modules and 0 <= my < modules and matrix[my][mx]
            pixels += bytes(ENIG_GOLD if gold else MASK_GREEN)
            pixels.append(corner_alpha(x, y, size, radius))
    return bytes(pixels)


def write_png(path: Path, size: int, rgba: bytes) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    stride = size * 4
    rows = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(size))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    matrix = micro_qr_matrix(TEXT)
    for path, size in OUTPUTS.items():
        write_png(path, size, render(matrix, size))
        print(f"Generated {path.relative_to(ROOT)} ({size}x{size})")


if __name__ == "__main__":
    main()
