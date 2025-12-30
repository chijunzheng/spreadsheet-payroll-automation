#!/usr/bin/env python3
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


def write_png(path: Path, width: int, height: int, pixels: bytes) -> None:
    if len(pixels) != width * height * 4:
        raise ValueError("Pixel data size mismatch.")

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        start = y * stride
        raw.extend(pixels[start : start + stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = bytearray()
    png.extend(b"\x89PNG\r\n\x1a\n")
    png.extend(chunk(b"IHDR", ihdr))
    png.extend(chunk(b"IDAT", zlib.compress(bytes(raw), level=9)))
    png.extend(chunk(b"IEND", b""))

    path.write_bytes(png)


def draw_icon(size: int) -> bytes:
    width = height = size
    cx = cy = size // 2
    pixels = bytearray(width * height * 4)

    bg_top = (12, 102, 228)
    bg_bottom = (7, 62, 151)
    circle_color = (40, 134, 236)
    check_color = (255, 255, 255)

    radius = int(size * 0.36)
    line_width = int(size * 0.07)

    def set_pixel(x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 4
            pixels[idx : idx + 4] = bytes(color)

    def draw_circle() -> None:
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                dx = x - cx
                dy = y - cy
                if dx * dx + dy * dy <= r2:
                    set_pixel(x, y, (*circle_color, 255))

    def draw_gradient() -> None:
        for y in range(height):
            t = y / (height - 1)
            r = int(bg_top[0] * (1 - t) + bg_bottom[0] * t)
            g = int(bg_top[1] * (1 - t) + bg_bottom[1] * t)
            b = int(bg_top[2] * (1 - t) + bg_bottom[2] * t)
            for x in range(width):
                set_pixel(x, y, (r, g, b, 255))

    def draw_line(x0: float, y0: float, x1: float, y1: float, width_px: int) -> None:
        dx = x1 - x0
        dy = y1 - y0
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return
        half = width_px / 2.0
        min_x = int(max(min(x0, x1) - width_px, 0))
        max_x = int(min(max(x0, x1) + width_px, width - 1))
        min_y = int(max(min(y0, y1) - width_px, 0))
        max_y = int(min(max(y0, y1) + width_px, height - 1))
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                t = ((x - x0) * dx + (y - y0) * dy) / length_sq
                t = max(0.0, min(1.0, t))
                px = x0 + t * dx
                py = y0 + t * dy
                dist = math.hypot(x - px, y - py)
                if dist <= half:
                    set_pixel(x, y, (*check_color, 255))

    draw_gradient()
    draw_circle()
    draw_line(size * 0.30, size * 0.55, size * 0.46, size * 0.70, line_width)
    draw_line(size * 0.45, size * 0.70, size * 0.72, size * 0.38, line_width)

    return bytes(pixels)


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    size = 1024
    pixels = draw_icon(size)
    write_png(output, size, size, pixels)
    print(f"Wrote icon to {output}")


if __name__ == "__main__":
    main()
