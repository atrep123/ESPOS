"""Explicit registration only. No canonical factory/profile/CLI change on import."""

import copy
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from espos_mcp import codegraph_transforms as adapter
from espos_mcp.codegraph_tools import CodegraphError, CodegraphReceipt


class TransformError(CodegraphError):
    code: Literal[
        "InvalidArgument",
        "LimitExceeded",
        "Unavailable",
        "ParserRejected",
        "IntegrityError",
        "Conflict",
    ]


class TransformReceipt(CodegraphReceipt):
    operation: Literal[
        "get_cpp_transform_capabilities_v1",
        "list_cpp_regions_v1",
        "edit_cpp_v1",
        "construct_cpp_v1",
        "list_cpp_sdk_regions_v1",
        "construct_cpp_sdk_v1",
    ]
    error: TransformError | None


def _request_schema(action):
    schema = copy.deepcopy(adapter.source.ANALYZE_INPUT_SCHEMA)
    schema["required"] += ["schemaVersion", "graph", "expectedSourceHash"]
    props = schema["properties"]
    props.update(
        schemaVersion={"type": "integer", "const": 1},
        graph={
            "type": "object",
            "description": "Entire actual parser snapshot; backend reparses and checks every field.",
        },
        expectedSourceHash={"type": "string", "pattern": "^[0-9a-f]{64}$"},
    )
    identifier = {"type": "string", "minLength": 1, "maxLength": 128}
    if action == "edit":
        props["edits"] = {
            "type": "array",
            "maxItems": adapter.MAX_EDITS,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["nodeId", "slotId", "replacement"],
                        "properties": {
                            "nodeId": identifier,
                            "slotId": identifier,
                            "replacement": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": adapter.MAX_TOKEN_BYTES,
                            },
                        },
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["kind", "regionId", "nodeId", "slotId", "sourceNodeId"],
                        "properties": {
                            "kind": {"const": "rewireDataInput"},
                            "regionId": identifier,
                            "nodeId": identifier,
                            "slotId": identifier,
                            "sourceNodeId": identifier,
                        },
                    },
                ]
            },
        }
        schema["required"].append("edits")
    if action in {"construct", "constructSdk"}:
        kinds = (
            ["insertSdkStatement"]
            if action == "constructSdk"
            else ["insertStatement", "deleteNode", "setSequence"]
        )
        alternatives = []
        for kind in kinds:
            fields = {"kind": {"const": kind}, "regionId": identifier}
            if kind in {"insertStatement", "insertSdkStatement"}:
                fields.update(
                    beforeNodeId={"anyOf": [identifier, {"type": "null"}]},
                    cpp={"type": "string", "minLength": 1, "maxLength": adapter.MAX_CPP_BYTES},
                )
            elif kind == "deleteNode":
                fields["nodeId"] = identifier
            else:
                fields["nodeIds"] = {
                    "type": "array",
                    "maxItems": adapter.source.MAX_GRAPH_NODES,
                    "uniqueItems": True,
                    "items": identifier,
                }
            alternatives.append(
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(fields),
                    "properties": fields,
                }
            )
        props["mutation"] = {"oneOf": alternatives}
        schema["required"].append("mutation")
    if action in {"sdkRegions", "constructSdk"}:
        schema["required"].append("sdkProfile")
    return schema


RegionsRequest = Annotated[
    dict[str, Any], Field(strict=True, json_schema_extra=_request_schema("regions"))
]
EditRequest = Annotated[
    dict[str, Any], Field(strict=True, json_schema_extra=_request_schema("edit"))
]
ConstructRequest = Annotated[
    dict[str, Any], Field(strict=True, json_schema_extra=_request_schema("construct"))
]
SdkRegionsRequest = Annotated[
    dict[str, Any], Field(strict=True, json_schema_extra=_request_schema("sdkRegions"))
]
SdkConstructRequest = Annotated[
    dict[str, Any], Field(strict=True, json_schema_extra=_request_schema("constructSdk"))
]
Result = Annotated[CallToolResult, TransformReceipt]
# readOnlyHint concerns external state, not whether RETURNED caller bytes differ.
# Insertion may allocate new snapshot IDs, so identical response/idempotence is
# deliberately not promised. These hints never widen the canonical five-tool profile.
DETACHED = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False
)
METADATA = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


def _result(receipt):
    checked = TransformReceipt.model_validate(receipt).model_dump()
    return CallToolResult(
        content=[TextContent(type="text", text=adapter.source.json_text(checked))],
        structuredContent=checked,
        isError=not checked["ok"],
    )


def register_codegraph_transform_tools(server: FastMCP) -> None:
    """Compose only when explicitly approved; does not construct another server."""

    @server.tool(annotations=METADATA, structured_output=True)
    def get_cpp_transform_capabilities_v1() -> Result:
        """Actual backend source contract/limits, NOT native parser or hardware readiness."""
        return _result(adapter.capabilities_receipt())

    @server.tool(annotations=DETACHED, structured_output=True)
    def list_cpp_regions_v1(request: RegionsRequest) -> Result:
        """Restore full caller snapshot; discover actual scalar construction regions.

        Canonical base64 UTF-8 <=64KiB; request <=512KiB, JSON depth<=24.
        No file/editor owner, authority, execution or source change.
        """
        return _result(adapter.transform_receipt("list_cpp_regions_v1", request))

    @server.tool(annotations=DETACHED, structured_output=True)
    def edit_cpp_v1(request: EditRequest) -> Result:
        """Return detached exact bytes after <=64 token or rewireDataInput edits.

        Full snapshot/hash/context required. Backend preserves opaque bytes and
        surviving IDs; scalar wires require fresh backend-derived dataWireInputs.
        No caller capabilities or free-text identifier replacement. Not a file save.
        """
        return _result(adapter.transform_receipt("edit_cpp_v1", request))

    @server.tool(annotations=DETACHED, structured_output=True)
    def construct_cpp_v1(request: ConstructRequest) -> Result:
        """One real scalar insert/delete/exact sequence transaction in a proven region.

        cpp is ordinary C++, not a DSL; <=4096B. No arbitrary wire rewrites,
        parent regeneration, opaque edits, scope inference or filesystem writes.
        """
        return _result(adapter.transform_receipt("construct_cpp_v1", request))

    @server.tool(annotations=DETACHED, structured_output=True)
    def list_cpp_sdk_regions_v1(request: SdkRegionsRequest) -> Result:
        """Discover actual SDK insertion regions with explicit tabos-sdk-minimal-1.

        Caller supplies bindings/context. No callback/event/peripheral invention;
        no SDK service call is performed. Empty eligible regions are not HW status.
        """
        return _result(adapter.transform_receipt("list_cpp_sdk_regions_v1", request))

    @server.tool(annotations=DETACHED, structured_output=True)
    def construct_cpp_sdk_v1(request: SdkConstructRequest) -> Result:
        """Insert one backend-proven explicit SDK declaration/if tree, <=4096B C++.

        Reviewed bindings only; no auto-bind/force-Live/unwrapping DataPoint,
        function/callback generation, SDK deletion/reorder or owner adoption.
        Returns detached source; does not save or execute it.
        """
        return _result(adapter.transform_receipt("construct_cpp_sdk_v1", request))
