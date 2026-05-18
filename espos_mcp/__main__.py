"""``python -m espos_mcp`` entrypoint.

Default behavior: run the espos MCP server over **stdio** (the transport an
MCP client spawns and talks to). ``--list-tools`` prints the registered tool
inventory and exits (useful for verification / discovery without starting the
blocking stdio loop); ``--help`` is standard argparse.

Run::

    python -m espos_mcp                 # serve over stdio (for an MCP client)
    python -m espos_mcp --list-tools    # print tool inventory and exit
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import List, Optional


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m espos_mcp",
        description=(
            "espos MCP server — exposes the real ESP32OS UI Toolkit "
            "(scenes, widgets, logic rules, board registry, validator, "
            "C/SVG export, PlatformIO build/flash) to any MCP client over "
            "stdio. Each tool wraps a genuine espos library function."
        ),
    )
    p.add_argument(
        "--list-tools",
        action="store_true",
        help="print the registered MCP tools and exit (no server loop)",
    )
    p.add_argument(
        "--transport",
        choices=("stdio",),
        default="stdio",
        help="MCP transport (only stdio is supported; it is the default)",
    )
    return p


def _list_tools() -> int:
    """Print the tool inventory using the real registered server."""
    from .server import build_server

    server = build_server()
    # FastMCP exposes its registered tools via the async list_tools() API.
    tools = asyncio.run(server.list_tools())
    print(f"espos MCP server — {len(tools)} tools:\n")
    for t in sorted(tools, key=lambda x: x.name):
        summary = (t.description or "").strip().splitlines()
        first = summary[0] if summary else ""
        print(f"  {t.name:24s} {first}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _make_parser().parse_args(argv)

    if args.list_tools:
        return _list_tools()

    # Default: run the blocking stdio server an MCP client connects to.
    from .server import build_server

    server = build_server()
    try:
        server.run(transport="stdio")
    except KeyboardInterrupt:  # pragma: no cover - operator Ctrl-C
        print("espos MCP server stopped.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
