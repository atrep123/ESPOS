"""``python -m espos_mcp`` entrypoint.

Default behavior: run the read-only espos MCP profile over strict **stdio**.
Use --profile codegraph for detached C++ transformations without file writes,
or --profile full explicitly for the genuine full toolkit factory.
``--list-tools`` prints the registered tool
inventory and exits (useful for verification / discovery without starting the
blocking stdio loop); ``--help`` is standard argparse.

Run::

    python -m espos_mcp                          # strict stdio, read-only profile
    python -m espos_mcp --profile codegraph      # detached caller-byte transforms
    python -m espos_mcp --profile full           # explicit full toolkit profile
    python -m espos_mcp --list-tools             # selected read-only inventory
    python -m espos_mcp --profile full --list-tools
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .profiles import PROFILES, build_profiled_server


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m espos_mcp",
        description=(
            "espos MCP server — exposes the real ESP32OS UI Toolkit "
            "(scenes, widgets, logic rules, board registry, validator, "
            "C/SVG export, PlatformIO build/flash) to any MCP client over "
            "strict stdio. Default: read-only tools; --profile full explicitly "
            "enables the full registry. --profile codegraph selects detached C++ "
            "transformations without file writes. Each tool wraps a genuine espos function."
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
    p.add_argument(
        "--profile",
        choices=PROFILES,
        default="read-only",
        help="server-enforced profile (default: read-only; codegraph transforms caller bytes only; full is explicit)",
    )
    return p


def _run_startup(coroutine):
    """CLI-owned async startup seam; production always uses the real loop."""
    return asyncio.run(coroutine)


def _list_tools(profile: str = "read-only") -> int:
    """Print the inventory of the actual selected, server-enforced profile."""
    server = _run_startup(build_profiled_server(profile))
    # FastMCP exposes its registered tools via the async list_tools() API.
    from .sdk_diagnostics import cli_sdk_diagnostics

    with cli_sdk_diagnostics():
        tools = _run_startup(server.list_tools())
    print(f"espos MCP server — {len(tools)} tools:\n")
    for t in sorted(tools, key=lambda x: x.name):
        summary = (t.description or "").strip().splitlines()
        first = summary[0] if summary else ""
        print(f"  {t.name:24s} {first}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _make_parser().parse_args(argv)

    if args.list_tools:
        return _list_tools(args.profile)

    # Default: strict application-owned files, official SDK stdio/session.
    from .sdk_diagnostics import SdkDiagnosticError, cli_sdk_diagnostics
    from .strict_stdio import StdioBoundaryError, run_stdio

    server = _run_startup(build_profiled_server(args.profile))
    try:
        with cli_sdk_diagnostics():
            run_stdio(server)
    except StdioBoundaryError:
        print("espos MCP stdio session failed; do not automatically retry.", file=sys.stderr)
        return 1
    except SdkDiagnosticError:
        print("espos MCP SDK diagnostic output failed.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover - operator Ctrl-C
        print("espos MCP server stopped.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
