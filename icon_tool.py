"""
Icon management CLI for ESP32OS

Features:
- list: list all icons (filter by category)
- search: search icons by name/usage substring
- show: show details for an icon (by name or symbol)
- stats: show counts per category
- ascii: print ASCII/Unicode mapping for a symbol

Usage examples:
  python icon_tool.py list --category navigation
  python icon_tool.py search --contains save
  python icon_tool.py show --name "Check"
  python icon_tool.py show --symbol mi_home_24px
  python icon_tool.py stats
  python icon_tool.py ascii --symbol mi_wifi_24px
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from ui_icons import (
    MATERIAL_ICONS,
    get_all_categories,
    get_icon_by_name,
    get_icon_by_symbol,
    get_icons_by_category,
)

try:
    from sim_icon_support import get_icon_ascii
except Exception:
    # Fallback if simulator mapping isn't present
    def get_icon_ascii(symbol: str, fallback: str = "?") -> str:  # type: ignore
        icon = get_icon_by_symbol(symbol)
        return icon["ascii"] if icon else fallback


def _print_table(rows: List[List[str]], headers: List[str] | None = None) -> None:
    cols = list(zip(*(headers and [headers] or []) + rows))
    widths = [max(len(str(cell)) for cell in col) for col in cols] if cols else []
    def fmt(row: List[str]) -> str:
        return "  ".join(str(cell).ljust(width) for cell, width in zip(row, widths))
    if headers:
        print(fmt(headers))
        print("  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))


def cmd_list(args: argparse.Namespace) -> int:
    icons = MATERIAL_ICONS
    if args.category:
        icons = get_icons_by_category(args.category)
    rows: List[List[str]] = []
    for ic in icons:
        rows.append([ic["name"], ic["symbol"], ic["category"], ic["ascii"]])
    if args.json:
        print(json.dumps(icons, ensure_ascii=False, indent=2))
        return 0
    _print_table(rows, headers=["Name", "Symbol", "Category", "ASCII"])
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    needle = args.contains.lower()
    results = [ic for ic in MATERIAL_ICONS if needle in ic["name"].lower() or needle in ic["usage"].lower()]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    rows = [[ic["name"], ic["symbol"], ic["category"], ic["ascii"]] for ic in results]
    _print_table(rows, headers=["Name", "Symbol", "Category", "ASCII"])
    return 0


def _icon_to_public(ic: Mapping[str, Any]) -> Dict[str, str]:
    return {
        "name": ic["name"],
        "symbol": ic["symbol"],
        "category": ic["category"],
        "usage": ic["usage"],
        "ascii": ic["ascii"],
        "size_16": ic["size_16"],
        "size_24": ic["size_24"],
    }


def cmd_show(args: argparse.Namespace) -> int:
    icon = None
    if args.name:
        icon = get_icon_by_name(args.name)
    elif args.symbol:
        icon = get_icon_by_symbol(args.symbol)
    if not icon:
        print("Icon not found", file=sys.stderr)
        return 1
    data = _icon_to_public(icon)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        rows = [["Name", data["name"]], ["Symbol", data["symbol"]], ["Category", data["category"]], ["Usage", data["usage"]], ["ASCII", data["ascii"]], ["Size 16", data["size_16"]], ["Size 24", data["size_24"]]]
        _print_table(rows)
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    cats = get_all_categories()
    rows = []
    total = 0
    for c in cats:
        n = len(get_icons_by_category(c))
        total += n
        rows.append([c, str(n)])
    rows.append(["TOTAL", str(total)])
    _print_table(rows, headers=["Category", "Count"])
    return 0


def cmd_ascii(args: argparse.Namespace) -> int:
    sym = args.symbol
    ch = get_icon_ascii(sym, fallback="?")
    print(ch)
    return 0


def _filter_icons(category: str | None):
    if category:
        return get_icons_by_category(category)
    return MATERIAL_ICONS


def _to_csv(rows: Iterable[Mapping[str, Any]]) -> str:
    import csv
    import io
    buf = io.StringIO()
    writer = csv.writer(buf)
    headers = ["name", "symbol", "category", "usage", "ascii", "size_16", "size_24"]
    writer.writerow(headers)
    for ic in rows:
        writer.writerow([ic["name"], ic["symbol"], ic["category"], ic["usage"], ic["ascii"], ic["size_16"], ic["size_24"]])
    return buf.getvalue()


def _to_markdown(rows: Iterable[Mapping[str, Any]]) -> str:
    headers = ["Name", "Symbol", "Category", "Usage", "ASCII", "Size 16", "Size 24"]
    sep = ["---"] * len(headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    for ic in rows:
        lines.append("| " + " | ".join([
            ic["name"], ic["symbol"], ic["category"], ic["usage"], ic["ascii"], ic["size_16"], ic["size_24"]
        ]) + " |")
    return "\n".join(lines)


def cmd_export(args: argparse.Namespace) -> int:
    icons = _filter_icons(args.category)
    if args.format == "csv":
        content = _to_csv(icons)
    elif args.format == "md":
        content = _to_markdown(icons)
    else:
        print("Unsupported format; use csv or md", file=sys.stderr)
        return 1
    if args.out:
        Path(args.out).write_text(content, encoding="utf-8")
    else:
        print(content)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="icon_tool", description="Icon management CLI for ESP32OS")
    sub = p.add_subparsers(dest="cmd", required=True)

    OUTPUT_JSON_HELP = "Output JSON"

    p_list = sub.add_parser("list", help="List icons")
    p_list.add_argument("--category", choices=get_all_categories(), help="Filter by category")
    p_list.add_argument("--json", action="store_true", help=OUTPUT_JSON_HELP)
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser("search", help="Search by name/usage substring")
    p_search.add_argument("--contains", required=True, help="Substring to search for")
    p_search.add_argument("--json", action="store_true", help=OUTPUT_JSON_HELP)
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", help="Show icon details")
    g = p_show.add_mutually_exclusive_group(required=True)
    g.add_argument("--name", help="Icon display name")
    g.add_argument("--symbol", help="Icon symbol name")
    p_show.add_argument("--json", action="store_true", help=OUTPUT_JSON_HELP)
    p_show.set_defaults(func=cmd_show)

    p_stats = sub.add_parser("stats", help="Show counts per category")
    p_stats.set_defaults(func=cmd_stats)

    p_ascii = sub.add_parser("ascii", help="Print ASCII/Unicode for a symbol")
    p_ascii.add_argument("--symbol", required=True, help="Icon symbol name, e.g. mi_home_24px")
    p_ascii.set_defaults(func=cmd_ascii)

    p_export = sub.add_parser("export", help="Export icon catalog")
    p_export.add_argument("--format", choices=["csv", "md"], required=True, help="Output format")
    p_export.add_argument("--category", choices=get_all_categories(), help="Filter by category")
    p_export.add_argument("--out", help="Write to file (default: stdout)")
    p_export.set_defaults(func=cmd_export)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
