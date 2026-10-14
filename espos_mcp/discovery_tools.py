"""Thin MCP registration for read-only registry discovery.

Real SDK imports only. No fallback/dependency shim or alternative transport.
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import StrictInt, StrictStr

from espos_mcp.discovery import (
    DiscoveryReceipt,
    _json,
    capabilities_receipt,
    error_receipt,
    target_receipt,
    targets_receipt,
)

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
Result = Annotated[CallToolResult, DiscoveryReceipt]


def _result(receipt: dict) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=_json(receipt))],
        structuredContent=receipt,
        isError=not receipt["ok"],
    )


def register_discovery_tools(server: FastMCP) -> None:
    @server.tool(annotations=READ_ONLY, structured_output=True)
    async def get_capabilities() -> Result:
        """Discover actual registered tools, receipt/registry versions and metadata limits.

        Inventory only: does not probe compilers/devices or claim backend readiness.
        """
        try:
            tools = await server.list_tools()
            receipt = capabilities_receipt([tool.name for tool in tools])
        except Exception:
            receipt = error_receipt(
                "get_capabilities", "Unavailable", "Registered tool inventory is unavailable."
            )
        return _result(receipt)

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def list_targets(offset: StrictInt = 0, limit: StrictInt = 16) -> Result:
        """Read canvas target profiles, in registry order, without selecting a board.

        offset 0..256, limit 1..32. Compare registryHash when joining pages.
        Metadata is not device/driver or simulator evidence.
        """
        return _result(targets_receipt(offset, limit))

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def get_target(target_id: StrictStr) -> Result:
        """Read one exact target profile and declared capability availability.

        No path, alias, board mutation, generator execution or backend launch.
        Tab5 runtime metadata must not be interpreted as available legacy C export.
        """
        return _result(target_receipt(target_id))
