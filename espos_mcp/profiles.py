"""Server-enforced tool profiles, independent of client discovery filters.

Build one genuine server and finish selection before admitting a session.
This is not a runtime authorization switch or a sandbox for Python callers.
Full mode preserves the existing toolkit factory; restricted profiles remove
every tool not explicitly reviewed here, including any future registration.
Codegraph transforms caller buffers only; it does not write files or owners.
"""

from __future__ import annotations

READ_ONLY_TOOLS = frozenset(
    {
        "get_capabilities",
        "list_targets",
        "get_target",
        "analyze_cpp_v1",
        "list_sdk_nodes_v1",
    }
)
# Explicit review set, not derived from a potentially expanding registration.
CODEGRAPH_TOOLS = READ_ONLY_TOOLS | frozenset(
    {
        "get_cpp_transform_capabilities_v1",
        "list_cpp_regions_v1",
        "edit_cpp_v1",
        "construct_cpp_v1",
        "list_cpp_sdk_regions_v1",
        "construct_cpp_sdk_v1",
    }
)
PROFILES = ("read-only", "full", "codegraph")


async def build_profiled_server(profile: str = "read-only"):
    """Return the actual factory after public SDK registry restriction.

    A missing reviewed tool is a startup failure, never a fallback to full.
    Inventory/capabilities are generated from the same restricted server;
    neither registration nor selection serves a request or parses C++.
    """
    if type(profile) is not str or profile not in PROFILES:
        raise ValueError("Unknown ESPOS MCP tool profile")
    from .server import build_server

    server = build_server()
    if profile == "full":
        return server
    required = READ_ONLY_TOOLS
    if profile == "codegraph":
        from .codegraph_transform_tools import register_codegraph_transform_tools

        register_codegraph_transform_tools(server)
        required = CODEGRAPH_TOOLS
    inventory = await server.list_tools()
    names = {tool.name for tool in inventory}
    if not required <= names:
        raise RuntimeError(f"Required ESPOS MCP {profile} tools are unavailable")
    for name in sorted(names - required):
        server.remove_tool(name)
    selected = {tool.name for tool in await server.list_tools()}
    if selected != required:
        raise RuntimeError(f"ESPOS MCP {profile} tool selection failed")
    return server
