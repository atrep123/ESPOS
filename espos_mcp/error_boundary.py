"""Fixed public tool-exception text; no transport, validation or policy change.

Use at the existing server's construction seam. In reviewed MCP 1.30.0,
FastMCP registers self.call_tool, with low-level input validation disabled.
Do not catch failures only inside tool bodies: SDK argument validation happens
before those bodies. No SDK private field is read or patched here.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

PUBLIC_TOOL_FAILURE = (
    "Tool request could not be completed. Do not automatically retry; "
    "an operation may already have started."
)


class RedactedToolErrorsFastMCP(FastMCP):
    """Keep real results; redact ordinary exceptions crossing tool dispatch.

    This is not raw JSON ingress, an error log filter, a frame-size limit or
    rollback. BaseException cancellation/shutdown signals still propagate.
    No tool is retried and no caller input or exception is formatted here.
    Current ESPOS tools do not use URL elicitation; introducing that feature
    requires explicit review of this deliberately generic exception boundary.
    """

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        try:
            return await super().call_tool(name, arguments)
        except Exception:
            # Same MCP error-result shape as the SDK's outer exception handler.
            # No invented tool-specific schemaVersion/operation/source identity:
            # argument rejection may have happened before any tool body ran.
            return CallToolResult(
                content=[TextContent(type="text", text=PUBLIC_TOOL_FAILURE)],
                isError=True,
            )
