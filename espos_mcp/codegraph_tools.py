"""Source-only registration candidate for the EXISTING FastMCP server.

No server/transport/config created here. Primary composes this registration with
register_discovery_tools; Huygens discovery then lists the actual shared inventory.
MCP/Pydantic import, registration and transport proof await primary release.
"""

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from espos_mcp.codegraph_readonly import (
    ANALYZE_INPUT_SCHEMA,
    analyze_receipt,
    catalog_receipt,
    json_text,
)


class CodegraphError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Literal[
        "InvalidArgument", "LimitExceeded", "Unavailable", "ParserRejected", "IntegrityError"
    ]
    message: str = Field(max_length=256)
    retryable: Literal[False] = False
    sourceIdentity: dict[str, Any] | None


class CodegraphReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: Literal[1]
    operation: Literal["analyze_cpp_v1", "list_sdk_nodes_v1"]
    ok: bool
    data: dict[str, Any] | None
    error: CodegraphError | None

    @model_validator(mode="after")
    def coherent_outcome(self):
        if self.ok != (self.error is None) or self.ok != (self.data is not None):
            raise ValueError("inconsistent source-analysis outcome")
        return self


READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
Result = Annotated[CallToolResult, CodegraphReceipt]
SourceRequest = Annotated[dict[str, Any], Field(json_schema_extra=ANALYZE_INPUT_SCHEMA)]


def _result(receipt: dict) -> CallToolResult:
    checked = CodegraphReceipt.model_validate(receipt).model_dump()
    return CallToolResult(
        content=[TextContent(type="text", text=json_text(checked))],
        structuredContent=checked,
        isError=not checked["ok"],
    )


def register_codegraph_tools(server: FastMCP) -> None:
    @server.tool(annotations=READ_ONLY, structured_output=True)
    def analyze_cpp_v1(request: SourceRequest) -> Result:
        """Read-only selected C++ analysis of canonical base64 caller bytes.

        <=64 KiB UTF-8, <=16 explicit entries, <=32 bindings, <=8 parameters.
        No project path, command, editor write, graph mutation or owner adoption.
        sourceBase64 is returned byte-exact, including opaque code/BOM/CRLF.
        observation identifies caller-asserted revision/target only; ownerValidated
        stays false. ok means analysis completed, not compilation or valid C++.
        """
        return _result(analyze_receipt(request))

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def list_sdk_nodes_v1(offset: StrictInt = 0, limit: StrictInt = 16) -> Result:
        """Read actual reviewed TabOS SDK helper catalog and parser support.

        Strict offset 0..256, limit 1..32; compare catalogHash across pages.
        OpaqueInCurrentProfile helpers are NOT advertised as lowered SDK nodes.
        No SDK/hardware call, target selection, library install or execution.
        """
        return _result(catalog_receipt(offset, limit))
