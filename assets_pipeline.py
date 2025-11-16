#!/usr/bin/env python3
"""
Assets Pipeline: Convert PNG icons/fonts into C arrays for firmware

Usage:
  python assets_pipeline.py import <png_path> <symbol_name> [--format 1bpp|4bpp] [--threshold 128] [--out src/assets]

Outputs:
  - src/assets/<symbol_name>.h
  - src/assets/<symbol_name>.c

Format:
  - 1bpp: packed MSB-first, stride = (w+7)//8
  - 4bpp: two pixels per byte, high nibble = left pixel
"""

import os
import sys
import argparse
from typing import Tuple

try:
    from PIL import Image
except Exception as e:
    print("[error] Pillow is required. pip install pillow")
    sys.exit(1)


def load_png(path: str) -> Image.Image:
    img = Image.open(path).convert("L")  # grayscale
    return img


def to_1bpp(img: Image.Image, threshold: int) -> Tuple[bytes, int, int, int]:
    w, h = img.size
    stride = (w + 7) // 8
    out = bytearray(stride * h)
    px = img.load()
    for y in range(h):
        row_off = y * stride
        byte = 0
        bit = 7
        idx = 0
        for x in range(w):
            v = 1 if px[x, y] >= threshold else 0
            if v:
                byte |= (1 << bit)
            bit -= 1
            if bit < 0:
                out[row_off + idx] = byte
                idx += 1
                byte = 0
                bit = 7
        if bit != 7:
            out[row_off + idx] = byte
    return bytes(out), w, h, stride


def to_4bpp(img: Image.Image) -> Tuple[bytes, int, int, int]:
    w, h = img.size
    stride = (w + 1) // 2
    out = bytearray(stride * h)
    px = img.load()
    for y in range(h):
        row_off = y * stride
        idx = 0
        for x in range(0, w, 2):
            p0 = px[x, y] >> 4
            p1 = (px[x+1, y] >> 4) if (x+1) < w else 0
            out[row_off + idx] = (p0 << 4) | p1
            idx += 1
    return bytes(out), w, h, stride


def write_c_files(symbol: str, data: bytes, w: int, h: int, stride: int, fmt: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    h_path = os.path.join(out_dir, f"{symbol}.h")
    c_path = os.path.join(out_dir, f"{symbol}.c")

    header = f"""
#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {{
#endif

typedef struct {{
    uint16_t width;
    uint16_t height;
    uint16_t stride;
    uint8_t  format; /* 1=1bpp, 4=4bpp */
    const uint8_t* data;
}} UiBitmap;

extern const UiBitmap {symbol}_bmp;

#ifdef __cplusplus
}}
#endif
""".lstrip()

    # Format C array
    bytes_per_line = 16
    hex_lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i+bytes_per_line]
        hex_lines.append(", ".join(f"0x{b:02X}" for b in chunk))
    array_body = ",\n    ".join(hex_lines)

    source = f"""
#include "{symbol}.h"

static const uint8_t {symbol}_data[] = {{
    {array_body}
}};

const UiBitmap {symbol}_bmp = {{
    {w}, {h}, {stride}, {1 if fmt=='1bpp' else 4}, {symbol}_data
}};
""".lstrip()

    with open(h_path, 'w', encoding='utf-8') as f:
        f.write(header)
    with open(c_path, 'w', encoding='utf-8') as f:
        f.write(source)
    print(f"[ok] Wrote {h_path}, {c_path}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    imp = sub.add_parser("import", help="Import PNG to C asset")
    imp.add_argument("png")
    imp.add_argument("symbol")
    imp.add_argument("--format", choices=["1bpp", "4bpp"], default="1bpp")
    imp.add_argument("--threshold", type=int, default=128)
    imp.add_argument("--out", default=os.path.join("src", "assets"))

    args = p.parse_args()
    if args.cmd != "import":
        p.print_help()
        return 1

    img = load_png(args.png)
    if args.format == "1bpp":
        data, w, h, stride = to_1bpp(img, args.threshold)
    else:
        data, w, h, stride = to_4bpp(img)

    write_c_files(args.symbol, data, w, h, stride, args.format, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
