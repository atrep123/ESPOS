#!/usr/bin/env python3
"""
Generate 1bpp icon bitmaps for firmware from PNG assets.

Inputs (default):
  assets/icons/material/filled/*_24px.png

Outputs:
  src/icons.h
  src/icons_24.h (compat shim; includes icons.h)
  src/icons.c      (16x16, downscaled from 24px)
  src/icons_24.c   (24x24)
  src/icons_registry.h/.c (name -> icon lookup)

Design notes:
  - Output bitmaps are 1bpp, MSB-first in each byte (x=0 is bit 7).
  - Transparency drives the mask. For fully-opaque assets, we fall back to
    "different from background" detection using edge pixels.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class IconBitmap:
    name: str  # base name, e.g. "network_wifi"
    sym_base: str  # C symbol base, e.g. "mi_network_wifi"
    w: int
    h: int
    stride: int
    data: bytes


def _c_ident(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    if out and out[0].isdigit():
        out.insert(0, "_")
    return "".join(out)


def _chunked(it: Iterable[int], n: int) -> Iterable[list[int]]:
    buf: list[int] = []
    for v in it:
        buf.append(v)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def _ends_with(buf: str, suffix: str) -> bool:
    return len(buf) >= len(suffix) and buf[-len(suffix) :] == suffix


def _surface_bg_rgba(img) -> tuple[int, int, int, int]:
    """Best-effort background color guess from edge pixels (corners + borders)."""
    w, h = img.get_size()
    samples: list[tuple[int, int, int, int]] = []

    # Corners.
    samples.append(img.get_at((0, 0)))
    samples.append(img.get_at((w - 1, 0)))
    samples.append(img.get_at((0, h - 1)))
    samples.append(img.get_at((w - 1, h - 1)))

    # A few edge points.
    for x in (0, w // 2, w - 1):
        samples.append(img.get_at((x, 0)))
        samples.append(img.get_at((x, h - 1)))
    for y in (0, h // 2, h - 1):
        samples.append(img.get_at((0, y)))
        samples.append(img.get_at((w - 1, y)))

    counts: dict[tuple[int, int, int, int], int] = {}
    for rgba in samples:
        key = (int(rgba.r), int(rgba.g), int(rgba.b), int(rgba.a))
        counts[key] = counts.get(key, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _surface_to_mask(img, *, alpha_threshold: int) -> tuple[bytes, int, int, int]:
    """Return (data, w, h, stride_bytes) for 1bpp mask, MSB-first."""
    w, h = img.get_size()
    stride = (w + 7) // 8
    out = bytearray(stride * h)

    # Prefer alpha if present; fall back when fully opaque.
    min_a = 255
    max_a = 0
    for y in range(h):
        for x in range(w):
            a = int(img.get_at((x, y)).a)
            if a < min_a:
                min_a = a
            if a > max_a:
                max_a = a

    use_alpha = min_a < 255
    bg = None
    if not use_alpha:
        bg = _surface_bg_rgba(img)

    for y in range(h):
        for x in range(w):
            px = img.get_at((x, y))
            a = int(px.a)
            on = False
            if use_alpha:
                on = a >= alpha_threshold
            else:
                # Opaque asset: treat pixels that differ from background as "on".
                assert bg is not None
                dr = abs(int(px.r) - bg[0])
                dg = abs(int(px.g) - bg[1])
                db = abs(int(px.b) - bg[2])
                on = (dr + dg + db) >= 30

            if on:
                idx = y * stride + (x // 8)
                out[idx] |= 0x80 >> (x & 7)

    return bytes(out), w, h, stride


def _load_icons(
    asset_dir: Path, *, alpha_threshold: int
) -> tuple[list[IconBitmap], list[IconBitmap]]:
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame  # pylint: disable=import-error

    pygame.display.init()
    pygame.display.set_mode((1, 1))

    icons_24: list[IconBitmap] = []
    icons_16: list[IconBitmap] = []

    files = sorted(asset_dir.glob("*_24px.png"))
    if not files:
        raise SystemExit(f"No '*_24px.png' files found in {asset_dir}")

    for fp in files:
        stem = fp.stem  # e.g. "network_wifi_24px"
        if not _ends_with(stem, "_24px"):
            continue
        base = stem[: -len("_24px")]
        base = base.strip()
        if not base:
            continue

        base_ident = _c_ident(base)
        sym_base = f"mi_{base_ident}"

        src = pygame.image.load(str(fp)).convert_alpha()
        if src.get_width() != 24 or src.get_height() != 24:
            src = pygame.transform.smoothscale(src, (24, 24))

        img24 = src
        img16 = pygame.transform.smoothscale(src, (16, 16))

        data24, w24, h24, stride24 = _surface_to_mask(img24, alpha_threshold=alpha_threshold)
        data16, w16, h16, stride16 = _surface_to_mask(img16, alpha_threshold=alpha_threshold)

        icons_24.append(
            IconBitmap(
                name=base_ident, sym_base=sym_base, w=w24, h=h24, stride=stride24, data=data24
            )
        )
        icons_16.append(
            IconBitmap(
                name=base_ident, sym_base=sym_base, w=w16, h=h16, stride=stride16, data=data16
            )
        )

    # Keep deterministic order.
    icons_24.sort(key=lambda i: i.name)
    icons_16.sort(key=lambda i: i.name)
    return icons_16, icons_24


def _write_icons_c(out_path: Path, icons: list[IconBitmap], *, size_px: int) -> None:
    lines: list[str] = []
    lines.append("#include <stdint.h>")
    lines.append('#include "icons.h"')
    lines.append("")
    lines.append("/* AUTO-GENERATED by tools/gen_icons.py - do not edit by hand. */")
    lines.append("")

    for ic in icons:
        sym = f"{ic.sym_base}_{size_px}px"
        lines.append(f"// {sym}: {ic.w}x{ic.h}, stride {ic.stride} bytes")
        lines.append(f"static const uint8_t {sym}_data[] = {{")

        vals = list(ic.data)
        for chunk in _chunked(vals, 16):
            hexes = ", ".join(f"0x{b:02x}" for b in chunk)
            lines.append(f"    {hexes},")
        lines.append("};")
        lines.append("")
        lines.append(f"const icon_t {sym} = {{")
        lines.append(f'    .name = "{sym}",')
        lines.append(f"    .width = {ic.w},")
        lines.append(f"    .height = {ic.h},")
        lines.append(f"    .stride_bytes = {ic.stride},")
        lines.append(f"    .data = {sym}_data,")
        lines.append("};")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _write_icons_h(out_path: Path, icons: list[IconBitmap]) -> None:
    lines: list[str] = []
    lines.append("#pragma once")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append("/* AUTO-GENERATED by tools/gen_icons.py - do not edit by hand. */")
    lines.append("")
    lines.append("#ifndef HAVE_ICONS")
    lines.append("#define HAVE_ICONS 0")
    lines.append("#endif")
    lines.append("")
    lines.append("typedef struct {")
    lines.append("    const char* name;")
    lines.append("    uint16_t width;")
    lines.append("    uint16_t height;")
    lines.append("    uint16_t stride_bytes;")
    lines.append("    const uint8_t* data;")
    lines.append("} icon_t;")
    lines.append("")

    for ic in icons:
        lines.append(f"extern const icon_t {ic.sym_base}_16px;")
    lines.append("")
    for ic in icons:
        lines.append(f"extern const icon_t {ic.sym_base}_24px;")
    lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _write_icons_24_h(out_path: Path) -> None:
    out_path.write_text(
        '#pragma once\n\n/* Compatibility header (prefer including "icons.h"). */\n\n#include "icons.h"\n',
        encoding="utf-8",
        newline="\n",
    )


def _write_registry(out_h: Path, out_c: Path, icons_16: list[IconBitmap]) -> None:
    # Icons are the same set for 16/24; use 16 list for names.
    lines_h: list[str] = []
    lines_h.append("#pragma once")
    lines_h.append("")
    lines_h.append("#include <stdint.h>")
    lines_h.append('#include "icons.h"')
    lines_h.append("")
    lines_h.append("/* AUTO-GENERATED by tools/gen_icons.py - do not edit by hand. */")
    lines_h.append("")
    lines_h.append("/* Find an icon by name.")
    lines_h.append(" *")
    lines_h.append(
        ' * Accepted forms: "arrow_back", "mi_arrow_back", "mi_arrow_back_16px", "mi_arrow_back_24px".'
    )
    lines_h.append(
        " * size_px: requested pixel size (e.g. 16 or 24). Nearest available is returned."
    )
    lines_h.append(" */")
    lines_h.append("const icon_t *icons_find(const char *name, uint8_t size_px);")
    lines_h.append("")
    out_h.write_text("\n".join(lines_h) + "\n", encoding="utf-8", newline="\n")

    lines_c: list[str] = []
    lines_c.append('#include "icons_registry.h"')
    lines_c.append("")
    lines_c.append("#include <string.h>")
    lines_c.append("")
    lines_c.append("/* AUTO-GENERATED by tools/gen_icons.py - do not edit by hand. */")
    lines_c.append("")
    lines_c.append("typedef struct {")
    lines_c.append("    const char *key; /* base key without prefix/suffix */")
    lines_c.append("    const icon_t *icon16;")
    lines_c.append("    const icon_t *icon24;")
    lines_c.append("} icon_pair_t;")
    lines_c.append("")

    lines_c.append("static const icon_pair_t k_icons[] = {")
    for ic in icons_16:
        lines_c.append(f'    {{"{ic.name}", &{ic.sym_base}_16px, &{ic.sym_base}_24px}},')
    lines_c.append("};")
    lines_c.append("")

    lines_c.append("static int ends_with(const char *s, const char *suffix)")
    lines_c.append("{")
    lines_c.append("    size_t sl = (s != NULL) ? strlen(s) : 0;")
    lines_c.append("    size_t tl = (suffix != NULL) ? strlen(suffix) : 0;")
    lines_c.append("    if (sl < tl) {")
    lines_c.append("        return 0;")
    lines_c.append("    }")
    lines_c.append("    return memcmp(s + (sl - tl), suffix, tl) == 0;")
    lines_c.append("}")
    lines_c.append("")

    lines_c.append("static void normalize_key(const char *name, char *out, size_t out_cap)")
    lines_c.append("{")
    lines_c.append("    if (out == NULL || out_cap == 0) {")
    lines_c.append("        return;")
    lines_c.append("    }")
    lines_c.append("    out[0] = '\\0';")
    lines_c.append("    if (name == NULL || *name == '\\0') {")
    lines_c.append("        return;")
    lines_c.append("    }")
    lines_c.append("")
    lines_c.append("    const char *p = name;")
    lines_c.append('    if (strncmp(p, "mi_", 3) == 0) {')
    lines_c.append("        p += 3;")
    lines_c.append("    }")
    lines_c.append("    size_t n = strnlen(p, out_cap - 1);")
    lines_c.append("    memcpy(out, p, n);")
    lines_c.append("    out[n] = '\\0';")
    lines_c.append("")
    lines_c.append('    if (ends_with(out, "_16px")) {')
    lines_c.append("        out[n - 5] = '\\0';")
    lines_c.append("        return;")
    lines_c.append("    }")
    lines_c.append('    if (ends_with(out, "_24px")) {')
    lines_c.append("        out[n - 5] = '\\0';")
    lines_c.append("        return;")
    lines_c.append("    }")
    lines_c.append("}")
    lines_c.append("")

    lines_c.append("const icon_t *icons_find(const char *name, uint8_t size_px)")
    lines_c.append("{")
    lines_c.append("    if (name == NULL || *name == '\\0') {")
    lines_c.append("        return NULL;")
    lines_c.append("    }")
    lines_c.append("")
    lines_c.append("    char key[64];")
    lines_c.append("    normalize_key(name, key, sizeof(key));")
    lines_c.append("    if (key[0] == '\\0') {")
    lines_c.append("        return NULL;")
    lines_c.append("    }")
    lines_c.append("")
    lines_c.append("    const size_t count = sizeof(k_icons) / sizeof(k_icons[0]);")
    lines_c.append("    for (size_t i = 0; i < count; ++i) {")
    lines_c.append("        const icon_pair_t *p = &k_icons[i];")
    lines_c.append("        if (strcmp(p->key, key) != 0) {")
    lines_c.append("            continue;")
    lines_c.append("        }")
    lines_c.append("        if (size_px >= 24 && p->icon24 != NULL) {")
    lines_c.append("            return p->icon24;")
    lines_c.append("        }")
    lines_c.append("        if (p->icon16 != NULL) {")
    lines_c.append("            return p->icon16;")
    lines_c.append("        }")
    lines_c.append("        return p->icon24;")
    lines_c.append("    }")
    lines_c.append("    return NULL;")
    lines_c.append("}")
    lines_c.append("")
    out_c.write_text("\n".join(lines_c) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate firmware icon bitmaps from PNG assets.")
    parser.add_argument(
        "--assets",
        type=Path,
        default=Path("assets/icons/material/filled"),
        help="Directory containing '*_24px.png' assets.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("src"),
        help="Output directory for generated C/h files.",
    )
    parser.add_argument(
        "--alpha-threshold",
        type=int,
        default=128,
        help="Alpha threshold [0..255] used to generate the 1bpp mask.",
    )
    args = parser.parse_args(argv)

    for name in ("assets", "out_dir"):
        if not str(getattr(args, name)).strip():
            parser.error(f"--{name.replace('_', '-')} cannot be empty or whitespace-only")

    repo_root = Path(__file__).resolve().parents[1]
    asset_dir = (repo_root / args.assets).resolve()
    out_dir = (repo_root / args.out_dir).resolve()

    if not asset_dir.exists():
        print(f"Asset dir not found: {asset_dir}", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    icons_16, icons_24 = _load_icons(asset_dir, alpha_threshold=args.alpha_threshold)

    # icons.h declares both 16px and 24px externs; use 16 list for names.
    _write_icons_h(out_dir / "icons.h", icons_16)
    _write_icons_24_h(out_dir / "icons_24.h")
    _write_icons_c(out_dir / "icons.c", icons_16, size_px=16)
    _write_icons_c(out_dir / "icons_24.c", icons_24, size_px=24)
    _write_registry(out_dir / "icons_registry.h", out_dir / "icons_registry.c", icons_16)

    print(f"Generated {len(icons_16)} icons into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
