#!/usr/bin/env python3
"""
Material Icons → monochrome bitmaps → C arrays for ESP32 OLED.

- Input: SVG icons (e.g. Material Icons, Filled, 24px) from `assets/icons/material/filled`
- Output: `src/icons.c` + `src/icons.h` with packed monochrome bitmaps

Dependencies (optional until used):
- Pillow (PIL)          -> pip install Pillow
- cairosvg              -> pip install cairosvg

This script is designed to be deterministic and safe:
- No network access
- Only reads from input directory and writes to target files when invoked via CLI

Usage examples:
  python tools/icon_pipeline.py --src assets/icons/material/filled --size 16 --out-c src/icons.c --out-h src/icons.h
  python tools/icon_pipeline.py --src assets/icons/material/filled --size 24 --prefix mi_ --threshold 140 

Icon packing:
- 1-bit per pixel, rows packed MSB→LSB into bytes (left→right, top→bottom)
- Width is padded to next multiple of 8 when packing; `stride_bytes = (width + 7) // 8`
- Header provides width, height, stride, and pointer to data

C types:

  typedef struct {
      const char* name;
      uint16_t width;
      uint16_t height;
      uint16_t stride_bytes; // bytes per row
      const uint8_t* data;   // packed 1bpp, MSB-first
  } icon_t;

"""
from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:
    import cairosvg  # type: ignore
except Exception:  # pragma: no cover
    cairosvg = None  # type: ignore


@dataclass
class IconBitmap:
    name: str
    width: int
    height: int
    data: bytes  # packed MSB-first, row-major
    stride_bytes: int


def _ensure_pillow() -> None:
    missing: List[str] = []
    if Image is None:
        missing.append("Pillow")
    if missing:
        raise RuntimeError(
            "Missing deps: " + ", ".join(missing) + "\n"
            "Install with: pip install Pillow"
        )


def _ensure_cairosvg() -> None:
    if cairosvg is None:
        raise RuntimeError(
            "Missing deps: cairosvg (and system cairo on Windows)\n"
            "Options:\n"
            "- Install CairoSVG + cairo runtime, or\n"
            "- Provide PNG inputs instead of SVGs."
        )


def svg_to_bitmap(svg_path: Path, size: Tuple[int, int], threshold: int = 128, invert: bool = False) -> Image.Image:
    """
    Render SVG → PIL grayscale → resize → threshold to 1-bit image (mode '1').
    """
    _ensure_pillow()
    _ensure_cairosvg()
    svg_bytes = svg_path.read_bytes()
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=size[0], output_height=size[1])
    with Image.open(io.BytesIO(png_bytes)) as im:
        # Convert to grayscale and ensure target size (no antialias on small icons)
        g = im.convert("L").resize(size, resample=Image.NEAREST)
        # Threshold to binary (1-bit)
        if invert:
            bw = g.point(lambda p: 0 if p >= threshold else 255, mode="1")
        else:
            bw = g.point(lambda p: 255 if p >= threshold else 0, mode="1")
        return bw


def raster_to_bitmap(img_path: Path, size: Tuple[int, int], threshold: int = 128, invert: bool = False) -> Image.Image:
    """
    Open a raster image (e.g., PNG) → grayscale → resize → threshold to 1-bit.
    """
    _ensure_pillow()
    with Image.open(img_path) as im:
        g = im.convert("L").resize(size, resample=Image.NEAREST)
        if invert:
            bw = g.point(lambda p: 0 if p >= threshold else 255, mode="1")
        else:
            bw = g.point(lambda p: 255 if p >= threshold else 0, mode="1")
        return bw


def bitmap_to_c_array(img: Image.Image) -> IconBitmap:
    """
    Pack mode-'1' image into MSB-first bytes row by row.
    Returns IconBitmap with packed data and stride (bytes per row).
    """
    if img.mode != "1":
        raise ValueError("bitmap_to_c_array expects mode '1' image")
    width, height = img.size
    stride = (width + 7) // 8
    pixels = img.tobytes()  # PIL packs 8 pixels per byte, MSB→LSB for mode '1'
    # Ensure order is row-major as expected. PIL's tobytes() for '1' is row-major packed already.
    if len(pixels) != stride * height:
        # Fallback: pack manually to be safe
        buf = bytearray(stride * height)
        px = img.load()
        for y in range(height):
            byte_val = 0
            bit = 7
            out_off = y * stride
            for x in range(width):
                on = 1 if px[x, y] > 0 else 0
                byte_val |= (on << bit)
                bit -= 1
                if bit < 0:
                    buf[out_off] = byte_val
                    out_off += 1
                    byte_val = 0
                    bit = 7
            if bit != 7:
                buf[out_off] = byte_val
        data = bytes(buf)
    else:
        data = pixels
    return IconBitmap(name="", width=width, height=height, data=data, stride_bytes=stride)


def _c_ident(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum() or ch == '_':
            out.append(ch.lower())
        else:
            out.append('_')
    ident = ''.join(out)
    while '__' in ident:
        ident = ident.replace('__', '_')
    return ident.strip('_')


def _emit_c(icon: IconBitmap, symbol: str) -> str:
    # Format bytes as hex
    bytes_per_line = 12
    # Split into lines
    lines = []
    b = icon.data
    for i in range(0, len(b), bytes_per_line):
        chunk = b[i:i+bytes_per_line]
        lines.append(", ".join(f"0x{v:02x}" for v in chunk))
    body = ",\n        ".join(lines)
    return (
        f"// {symbol}: {icon.width}x{icon.height}, stride {icon.stride_bytes} bytes\n"
        f"static const uint8_t {symbol}_data[] = {{\n        {body}\n}};\n\n"
        f"const icon_t {symbol} = {{\n"
        f"    .name = \"{symbol}\",\n"
        f"    .width = {icon.width},\n"
        f"    .height = {icon.height},\n"
        f"    .stride_bytes = {icon.stride_bytes},\n"
        f"    .data = {symbol}_data,\n"
        f"}};\n\n"
    )


def batch_convert(src_dir: Path, size: int, prefix: str = "mi_", threshold: int = 128, invert: bool = False) -> Tuple[str, str, List[str]]:
    """
    Convert all *.svg in src_dir to a pair of C/H sources. Returns (c_code, h_code, symbols).
    """
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src_dir}")

    c_parts: List[str] = []
    h_parts: List[str] = [
        "#pragma once\n",
        "#ifndef HAVE_ICONS\n",
        "#define HAVE_ICONS 1\n",
        "#endif\n",
        "#include <stdint.h>\n\n",
        "typedef struct {\n",
        "    const char* name;\n",
        "    uint16_t width;\n",
        "    uint16_t height;\n",
        "    uint16_t stride_bytes;\n",
        "    const uint8_t* data;\n",
        "} icon_t;\n\n",
    ]
    symbols: List[str] = []

    # Collect both SVG and PNG inputs
    inputs = list(sorted(src_dir.glob("*.svg"))) + list(sorted(src_dir.glob("*.png")))
    for path in inputs:
        name = path.stem
        sym = _c_ident(f"{prefix}{name}_{size}px")
        try:
            if path.suffix.lower() == ".svg":
                bw = svg_to_bitmap(path, (size, size), threshold=threshold, invert=invert)
            else:
                bw = raster_to_bitmap(path, (size, size), threshold=threshold, invert=invert)
            icon = bitmap_to_c_array(bw)
            icon.name = sym
            c_parts.append(_emit_c(icon, sym))
            h_parts.append(f"extern const icon_t {sym};\n")
            symbols.append(sym)
        except Exception as exc:
            print(f"[icon-pipeline] Skipping {path.name}: {exc}")
            continue

    c_code = (
        "#include <stdint.h>\n"
        "#include \"icons.h\"\n\n"
        + "".join(c_parts)
    )
    h_code = "".join(h_parts)
    return c_code, h_code, symbols


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SVG → 1bpp C arrays for ESP32 icons")
    ap.add_argument("--src", type=Path, default=Path("assets/icons/material/filled"), help="Input directory with *.svg")
    ap.add_argument("--size", type=int, default=16, help="Target icon size (width=height)")
    ap.add_argument("--threshold", type=int, default=128, help="B/W threshold 0-255")
    ap.add_argument("--invert", action="store_true", help="Invert threshold (useful for black PNGs)")
    ap.add_argument("--prefix", type=str, default="mi_", help="C symbol name prefix")
    ap.add_argument("--out-c", type=Path, help="Output C file path (e.g. src/icons.c)")
    ap.add_argument("--out-h", type=Path, help="Output header file path (e.g. src/icons.h)")
    args = ap.parse_args(argv)

    try:
        c_code, h_code, symbols = batch_convert(args.src, args.size, args.prefix, args.threshold, args.invert)
    except Exception as exc:
        print(f"[icon-pipeline] Failed: {exc}")
        return 1

    if args.out_c and args.out_h:
        args.out_c.parent.mkdir(parents=True, exist_ok=True)
        args.out_h.parent.mkdir(parents=True, exist_ok=True)
        args.out_c.write_text(c_code, encoding="utf-8")
        args.out_h.write_text(h_code, encoding="utf-8")
        print(f"[icon-pipeline] Wrote {args.out_c} and {args.out_h} ({len(symbols)} icons)")
    else:
        # Dry-run to stdout
        print("[icon-pipeline] Dry-run (no --out-c/--out-h). Preview header: \n")
        sys.stdout.write(h_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
