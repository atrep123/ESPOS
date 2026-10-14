"""Actual source MCP schema/handlers and pinned parser fixtures; no server start."""

import base64
import copy
import os
import subprocess
from unittest.mock import patch

import pytest
from jsonschema import Draft202012Validator
from mcp.types import CallToolRequest, CallToolRequestParams

from espos_mcp import codegraph_transforms as adapter
from espos_mcp.codegraph_transform_tools import _request_schema
from espos_mcp.profiles import CODEGRAPH_TOOLS, build_profiled_server

RAW = (
    b"\xef\xbb\xbf// TEST-ONLY opaque prefix\r\n"
    + (
        "void step(){ int měřič=1; int b=2; int target=měřič; }\r\n"
        "template<class T> T opaque(T x){return x;}\r\n"
    ).encode()
)


@pytest.fixture(autouse=True)
def forbid_processes(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("MCP scalar wire tests cannot spawn, compile or restart")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)


def analyzed(raw=RAW):
    receipt = adapter.source.analyze_receipt(
        {"sourceBase64": base64.b64encode(raw).decode(), "entries": ["step"]}
    )
    assert receipt["ok"], receipt
    data = receipt["data"]
    receipt = adapter.transform_receipt("list_cpp_regions_v1", envelope(data))
    assert receipt["ok"], receipt
    return receipt["data"]


def envelope(data, **fields):
    return {
        "schemaVersion": 1,
        "sourceBase64": data["sourceBase64"],
        "graph": copy.deepcopy(data["graph"]),
        "expectedSourceHash": data["graph"]["sourceHash"],
        **copy.deepcopy(data["parseContext"]),
        **fields,
    }


def operation(data, source="b"):
    target = next(n for n in data["graph"]["nodes"] if n.get("variable") == "target")
    source_node = next(n for n in data["graph"]["nodes"] if n.get("variable") == source)
    capability = next(c for c in data["dataWireInputs"] if c["nodeId"] == target["id"])
    return {k: capability[k] for k in ("kind", "regionId", "nodeId", "slotId")} | {
        "sourceNodeId": source_node["id"]
    }


def opaque(data):
    raw = base64.b64decode(data["sourceBase64"])
    return {
        n["id"]: raw[n["sourceSpan"]["startByte"] : n["sourceSpan"]["endByte"]]
        for n in data["graph"]["nodes"]
        if n["kind"] == "opaque"
    }


def test_source_adapter_roundtrip_rewires_exact_cpp_and_fresh_capabilities():
    before = analyzed()
    request = envelope(before, edits=[operation(before)])
    original = copy.deepcopy(request)
    response = adapter.transform_receipt("edit_cpp_v1", request)
    assert request == original
    assert response["ok"], response
    after = response["data"]
    assert base64.b64decode(after["sourceBase64"]) == RAW.replace(
        "target=měřič".encode(), b"target=b"
    )
    assert opaque(after) == opaque(before)
    assert [n["id"] for n in after["graph"]["nodes"]] == [n["id"] for n in before["graph"]["nodes"]]
    assert after["dataWireVersion"] == 1
    assert after["dataWireInputs"] != before["dataWireInputs"]
    assert after["sourceChanged"] is True
    assert after["ownerValidated"] is after["filesystemWritten"] is False
    restored = adapter.transform_receipt(
        "edit_cpp_v1", envelope(after, edits=[operation(after, "měřič")])
    )
    assert restored["ok"], restored
    assert base64.b64decode(restored["data"]["sourceBase64"]) == RAW


def test_registered_sdk_handler_accepts_union_and_eleven_names_stay_exact():
    def complete(coroutine):
        try:
            coroutine.send(None)
        except StopIteration as done:
            return done.value
        finally:
            coroutine.close()
        raise AssertionError("Source SDK call suspended; not a live transport test")

    def run():
        server = complete(build_profiled_server("codegraph"))
        tools = {t.name: t for t in complete(server.list_tools())}
        assert set(tools) == CODEGRAPH_TOOLS
        assert len(tools) == 11
        data = analyzed()
        request = envelope(data, edits=[operation(data)])
        actual = CallToolRequest(
            params=CallToolRequestParams(name="edit_cpp_v1", arguments={"request": request})
        )
        result = complete(server._mcp_server.request_handlers[CallToolRequest](actual)).root
        assert not result.isError
        assert result.structuredContent["data"]["sourceChanged"] is True
        assert result.structuredContent["data"]["dataWireVersion"] == 1
        schema = tools["edit_cpp_v1"].inputSchema["properties"]["request"]
        Draft202012Validator(schema).validate(request)
        forged = {**request, "dataWireInputs": data["dataWireInputs"]}
        assert list(Draft202012Validator(schema).iter_errors(forged))

    run()


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "connectData"},
        {"kind": "rewireDataInputV2"},
        {"sourceNodeId": "missing"},
        {"regionId": "stale"},
        {"slotId": "missing"},
        {"replacement": "b"},
        {"sourceNodeIds": ["forged"]},
        {"sourceNodeId": True},
    ],
)
def test_unknown_forged_stale_edit_fields_are_rejected_without_output(change):
    data = analyzed()
    request = envelope(data, edits=[{**operation(data), **change}])
    before = copy.deepcopy(request)
    response = adapter.transform_receipt("edit_cpp_v1", request)
    assert request == before
    assert response["ok"] is False
    assert response["data"] is None
    assert response["error"]["code"] in {"InvalidArgument", "ParserRejected"}


def test_capabilities_are_not_caller_request_authority():
    data = analyzed()
    for key, value in (
        ("dataWireVersion", 1),
        ("dataWireInputs", data["dataWireInputs"]),
        ("capabilities", {"all": True}),
    ):
        request = envelope(data, edits=[operation(data)], **{key: value})
        with patch.object(
            adapter, "_library", side_effect=AssertionError("forged envelope reached parser")
        ):
            response = adapter.transform_receipt("edit_cpp_v1", request)
        assert response["error"]["code"] == "InvalidArgument"


def test_wrong_type_forward_cycle_opaque_source_and_legacy_text_bypass_reject():
    data = analyzed(b"void step(){float f=1.0f; int b=2; int target=b; int later=3;}")
    original = operation(data)
    for name in ("f", "target", "later"):
        node = next(n for n in data["graph"]["nodes"] if n.get("variable") == name)
        result = adapter.transform_receipt(
            "edit_cpp_v1", envelope(data, edits=[{**original, "sourceNodeId": node["id"]}])
        )
        assert result["error"]["code"] == "ParserRejected"
        assert result["data"] is None
    opaque_id = next(n["id"] for n in data["graph"]["nodes"] if n["kind"] == "opaque")
    assert (
        adapter.transform_receipt(
            "edit_cpp_v1", envelope(data, edits=[{**original, "sourceNodeId": opaque_id}])
        )["ok"]
        is False
    )
    text = {"nodeId": original["nodeId"], "slotId": original["slotId"], "replacement": "b"}
    assert (
        adapter.transform_receipt("edit_cpp_v1", envelope(data, edits=[text]))["error"]["code"]
        == "ParserRejected"
    )


def test_selected_opaque_body_has_no_wire_inputs():
    data = analyzed(b"void step(){int b=1; mystery(); int target=2;}")
    assert data["dataWireVersion"] == 1
    assert data["dataWireInputs"] == []


def test_stale_hash_full_snapshot_and_mixed_batch_reject_atomically():
    data = analyzed()
    request = envelope(data, edits=[operation(data)])
    for invalid in (
        {**request, "expectedSourceHash": "0" * 64},
        {**request, "sourceBase64": base64.b64encode(RAW + b" ").decode()},
        {**request, "edits": [operation(data), {**operation(data), "sourceNodeId": "missing"}]},
    ):
        response = adapter.transform_receipt("edit_cpp_v1", invalid)
        assert response["ok"] is False
        assert response["data"] is None
    forged = copy.deepcopy(request)
    next(n for n in forged["graph"]["nodes"] if n.get("variable") == "b")["ports"][-1][
        "cppType"
    ] = "bool"
    assert adapter.transform_receipt("edit_cpp_v1", forged)["ok"] is False


def test_peer_without_new_method_advertises_no_wires_and_refuses_new_operation():
    data = analyzed()
    library = adapter._library()
    with patch.object(library.CodeGraph, "data_wire_inputs", None):
        old = adapter.transform_receipt("list_cpp_regions_v1", envelope(data))
        assert old["ok"]
        assert "dataWireVersion" not in old["data"]
        assert "dataWireInputs" not in old["data"]
        assert adapter.capabilities_receipt()["data"]["dataWireVersion"] is None
        rejected = adapter.transform_receipt("edit_cpp_v1", envelope(data, edits=[operation(data)]))
        assert rejected["error"]["code"] == "ParserRejected"
        assert rejected["data"] is None


def test_schema_closed_union_does_not_allow_replacement_or_unknown_operation():
    schema = _request_schema("edit")
    data = analyzed()
    request = envelope(data, edits=[operation(data)])
    validator = Draft202012Validator(schema)
    validator.validate(request)
    for edit in ({**operation(data), "kind": "unknown"}, {**operation(data), "replacement": "b"}):
        assert list(validator.iter_errors(envelope(data, edits=[edit])))
