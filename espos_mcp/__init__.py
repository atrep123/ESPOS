"""espos MCP server package.

A thin, well-typed Model Context Protocol (stdio) server that exposes the
**real** ESP32OS UI Toolkit library to any MCP client (an external
orchestrator, an IDE agent, etc.). Every tool is a thin wrapper over a genuine
espos function — there are no stub tools and no fabricated return values:

* scene/widget CRUD  -> ``ui_designer.UIDesigner`` (load/save/mutate)
* logic model (#36)  -> schema-valid ``events`` / ``rules`` edits, atomic write
* board registry     -> ``board_registry.load_registry``
* validation         -> ``tools.validate_design.validate_file``
* C export           -> ``tools.ui_export_c_header.export_header``
* SVG export         -> ``tools.ui_export_svg.export_svg``
* build / flash      -> ``tools.build.build_board`` / ``flash_board``

The server contains no business logic; it validates inputs at the boundary,
delegates to the real library, and returns structured results.

Run it with::

    python -m espos_mcp
"""

from __future__ import annotations

__all__ = ["__version__", "build_server", "main"]

__version__ = "0.1.0"


def build_server():
    """Return the configured :class:`FastMCP` server instance.

    Imported lazily so ``import espos_mcp`` does not hard-require the optional
    ``mcp`` dependency (e.g. for ``--help`` / introspection in environments
    where the SDK is not yet installed).
    """
    from .server import build_server as _build

    return _build()


def main(argv=None) -> int:
    """Console entrypoint (see :mod:`espos_mcp.__main__`)."""
    from .__main__ import main as _main

    return _main(argv)
