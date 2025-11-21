#!/usr/bin/env python3
"""
Asset Pipeline QA
- Scans one or more asset folders for images
- Lints file names, checks palette/bit-depth constraints (1bpp/4bpp)
- Emits JSON report and optional HTML gallery
- Optionally generates C source embedding assets as byte arrays

Usage examples:
  python tools/asset_pipeline_qa.py --assets ui_sim assets --profile 4bpp \
    --report reports/assets_qa_4bpp.json --emit-html reports/assets_qa_4bpp.html \
    --emit-c generated/assets_embedded.c

Notes:
- Full analysis requires Pillow (PIL). Without it, the script will still lint names
  and emit a basic report, but color/bit-depth checks will be limited.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, Set, cast

class ImageProto(Protocol):
    size: tuple[int, int]
    def getcolors(self, maxcolors: int = ...) -> Optional[List[Any]]: ...
    def convert(self, mode: str) -> "ImageProto": ...
    def getdata(self) -> Iterable[Any]: ...

pil_available = False
PILImage: Any = None
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    from PIL import Image as PILImage  # type: ignore[import-not-found]
    pil_available = True
except Exception:
    PILImage = None  # type: ignore[assignment]
    pil_available = False

NAME_RE = re.compile(r"^[a-z0-9_]+$")
IMG_EXTS = {".png", ".bmp", ".jpg", ".jpeg"}


def list_images(roots: List[Path]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if p.is_file() and p.suffix.lower() in IMG_EXTS:
                files.append(p)
    return files


def count_colors(img: ImageProto, max_sample: int = 500000) -> int:
    # Try fast path
    try:
        colors = img.getcolors(maxcolors=max_sample)
        if colors is not None:
            return len(colors)
    except Exception:
        pass
    # Fallback: convert to RGB and sample pixels
    try:
        rgb = img.convert('RGB')
        data = list(rgb.getdata())
        # Limit to first N pixels for speed on very large images
        N = min(len(data), max_sample)
        uniq: Set[Any] = set(data[:N])
        return len(uniq)
    except Exception:
        return -1


def analyze_image(path: Path, profile: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        'path': str(path),
        'file': path.name,
        'name_ok': bool(NAME_RE.match(path.stem)),
        'width': None,
        'height': None,
        'colors': None,
        'palette_ok': None,
        'profile': profile,
        'warnings': [],
        'errors': [],
    }
    # Name lint
    if not info['name_ok']:
        info['warnings'].append('name: use lowercase letters, digits, and underscore only')

    if pil_available and PILImage is not None:
        try:
            with PILImage.open(path) as img_handle:  # type: ignore[call-arg]
                imc = cast(ImageProto, img_handle)
                info['width'], info['height'] = imc.size
                num_colors = count_colors(imc)
                info['colors'] = num_colors if num_colors >= 0 else None
                # Heuristic constraints per profile
                if profile == '1bpp':
                    if info['colors'] is not None and info['colors'] > 2:
                        info['errors'].append('palette: >2 colors for 1bpp')
                elif profile == '4bpp':
                    if info['colors'] is not None and info['colors'] > 16:
                        info['errors'].append('palette: >16 colors for 4bpp')
                # Recommend even widths/heights for packed formats
                if info['width'] and info['width'] % 2 != 0:
                    info['warnings'].append('width is not even (may affect packing)')
                if info['height'] and info['height'] % 2 != 0:
                    info['warnings'].append('height is not even (may affect packing)')
                # OK flag
                if profile in ('1bpp', '4bpp') and info['colors'] is not None:
                    limit = 2 if profile == '1bpp' else 16
                    info['palette_ok'] = info['colors'] <= limit
        except Exception as e:
            info['errors'].append(f'open: {e}')
    else:
        info['warnings'].append('Pillow not installed: skipping color analysis')
    return info


def html_gallery(items: List[Dict[str, Any]], out_html: Path) -> None:
    out_html.parent.mkdir(parents=True, exist_ok=True)
    rows: List[str] = []
    rows.append('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Assets QA</title>')
    rows.append('<style>body{font-family:Arial;background:#111;color:#eee;padding:16px} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px} .card{background:#1c1c1c;border:1px solid #333;padding:10px;border-radius:8px} img{max-width:100%;background:#000;border:1px solid #333} .bad{color:#ff6961} .warn{color:#ffd166} .ok{color:#8bd17c}</style>')
    rows.append('</head><body>')
    rows.append('<h2>Assets QA</h2>')
    rows.append('<div class="grid">')
    for it in items:
        errs = it.get('errors', [])
        warns = it.get('warnings', [])
        rows.append('<div class="card">')
        # Image tag
        src = Path(it['path']).as_posix()
        rows.append(f'<div><img src="{src}" alt="{it["file"]}"></div>')
        rows.append(f'<div><strong>{it["file"]}</strong></div>')
        rows.append(f'<div>size: {it.get("width")}×{it.get("height")} | colors: {it.get("colors")}</div>')
        if errs:
            rows.append('<div class="bad">errors:<ul>' + ''.join(f'<li>{e}</li>' for e in errs) + '</ul></div>')
        if warns:
            rows.append('<div class="warn">warnings:<ul>' + ''.join(f'<li>{w}</li>' for w in warns) + '</ul></div>')
        if not errs and not warns:
            rows.append('<div class="ok">OK</div>')
        rows.append('</div>')
    rows.append('</div></body></html>')
    out_html.write_text('\n'.join(rows), encoding='utf-8')


def emit_c_assets(items: List[Dict[str, Any]], out_c: Path, out_h: Optional[Path] = None) -> None:
    out_c.parent.mkdir(parents=True, exist_ok=True)
    if out_h is None:
        out_h = out_c.with_suffix('.h')
    # Header
    out_h.write_text('#pragma once\n\n#include <stdint.h>\n\n#ifdef __cplusplus\nextern "C" {\n#endif\n\n// Auto-generated, do not edit\n\ntypedef struct { const char* name; const uint8_t* data; unsigned int size; } asset_entry_t;\n\nextern const asset_entry_t g_assets[];\nextern const unsigned int g_assets_count;\n\n#ifdef __cplusplus\n}\n#endif\n', encoding='utf-8')
    # C source
    lines: List[str] = []
    lines.append('#include <stdint.h>')
    lines.append('#include "{}"'.format(out_h.name))
    lines.append('// Auto-generated asset data')
    table: List[str] = []
    count = 0
    for it in items:
        if it.get('errors'):
            continue
        p = Path(it['path'])
        try:
            data = p.read_bytes()
        except Exception:
            continue
        sym = re.sub(r'[^a-z0-9_]', '_', p.stem.lower())
        arr_name = f'asset_{sym}'
        # Emit array
        lines.append(f'static const uint8_t {arr_name}[] = {{')
        # Chunk hex values for readability
        chunk: List[str] = []
        for b in data:
            chunk.append(f'0x{b:02x}')
            if len(chunk) >= 16:
                lines.append('  ' + ', '.join(chunk) + ',')
                chunk = []
        if chunk:
            lines.append('  ' + ', '.join(chunk) + ',')
        lines.append('};')
        table.append(f'  {{"{p.stem}", {arr_name}, (unsigned int)sizeof({arr_name})}}')
        count += 1
    lines.append('')
    lines.append('const asset_entry_t g_assets[] = {')
    lines.extend(table)
    lines.append('};')
    lines.append(f'const unsigned int g_assets_count = {count};')
    out_c.write_text('\n'.join(lines), encoding='utf-8')


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description='Asset Pipeline QA')
    ap.add_argument('--assets', nargs='+', default=['ui_sim', 'assets'], help='Folders to scan')
    ap.add_argument('--profile', default='4bpp', choices=['1bpp', '4bpp', 'any'], help='Bit-depth profile')
    ap.add_argument('--report', default='reports/assets_qa.json', help='Path to JSON report')
    ap.add_argument('--emit-html', default='', help='Path to HTML gallery report')
    ap.add_argument('--emit-c', default='', help='Path to generated C file for embedded assets')
    args = ap.parse_args(argv)

    roots = [Path(p).resolve() for p in args.assets]
    images = list_images(roots)
    if not images:
        logger.warning('No images found in: %s', ', '.join(str(r) for r in roots))
    results: List[Dict[str, Any]] = []
    for p in images:
        res = analyze_image(p, args.profile)
        results.append(res)

    # Summary
    total = len(results)
    errs = sum(1 for r in results if r.get('errors'))
    warns = sum(1 for r in results if r.get('warnings'))
    logger.info("Scanned %d assets | errors: %d | warnings: %d", total, errs, warns)

    # Write JSON report
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'profile': args.profile, 'total': total, 'results': results}, f, indent=2)
    logger.info("Report: %s", report_path)

    # Optional HTML
    if args.emit_html:
        out_html = Path(args.emit_html)
        html_gallery(results, out_html)
        logger.info("Gallery: %s", out_html)

    # Optional C emit
    if args.emit_c:
        out_c = Path(args.emit_c)
        emit_c_assets(results, out_c)
        logger.info("C assets: %s (+ %s)", out_c, out_c.with_suffix('.h'))

    # Exit code: non-zero if any errors
    return 1 if errs > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
