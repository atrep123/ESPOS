"""Editable scalar wires: authored C++ CST fixtures, no compiler/UI/runtime.

Run with --noconftest to avoid unrelated GUI fixtures and environment changes.
Any pytest artifact directory must be fresh and under worker-patches.
"""

import base64
import copy
import os
import subprocess

import pytest

from tools.tabos_code_graph import GraphError, parse_source, process_request, restore_graph


@pytest.fixture(autouse=True)
def forbid_processes(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Scalar wire fixtures must never compile or execute C++")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)


def parsed(raw=b"void step(){ int a=1; int b=2; int target=a; target=target+3; }"):
    return parse_source(raw, entries=["step"])


def variable(graph, name, kind="declaration"):
    return next(
        n for n in graph.to_dict()["nodes"] if n.get("variable") == name and n["kind"] == kind
    )


def wire(graph, target="target", source="b", *, kind="declaration", slot_index=0):
    node = variable(graph, target, kind)
    slot = [s for s in node["editSlots"] if s["kind"] in {"literal", "dataReference"}][slot_index]
    region = next(r for r in graph.construction_regions() if node["id"] in r["nodeIds"])
    return {
        "kind": "rewireDataInput",
        "regionId": region["id"],
        "nodeId": node["id"],
        "slotId": slot["id"],
        "sourceNodeId": variable(graph, source)["id"],
    }


def apply(graph, edits, **kwargs):
    return graph.apply_edits(
        edits,
        expected_source_hash=kwargs.get("hash", graph.source_hash),
        current_source=kwargs.get("raw", graph.source_bytes),
    )


def rejected(graph, edits, **kwargs):
    document, raw = graph.to_dict(), graph.source_bytes
    with pytest.raises(GraphError):
        apply(graph, edits, **kwargs)
    assert graph.to_dict() == document
    assert graph.export_source() == raw


def edge_key(edge):
    return (
        edge["kind"],
        edge["from"]["nodeId"],
        edge["from"]["portId"],
        edge["to"]["nodeId"],
        edge["to"]["portId"],
    )


def opaque_bytes(graph):
    return {
        n["id"]: graph.source_bytes[n["sourceSpan"]["startByte"] : n["sourceSpan"]["endByte"]]
        for n in graph.to_dict()["nodes"]
        if n["kind"] == "opaque"
    }


def envelope(graph, edits):
    return {
        "operation": "edit",
        "sourceBase64": base64.b64encode(graph.source_bytes).decode(),
        "entries": ["step"],
        "graph": graph.to_dict(),
        "expectedSourceHash": graph.source_hash,
        "edits": edits,
    }


@pytest.mark.parametrize("target_kind", ["declaration", "assignment"])
def test_wire_changes_real_cpp_and_only_intended_data_dependency(target_kind):
    graph = parsed()
    operation = wire(graph, kind=target_kind)
    changed = apply(graph, [operation])
    expected = (
        b"void step(){ int a=1; int b=2; int target=b; target=target+3; }"
        if target_kind == "declaration"
        else b"void step(){ int a=1; int b=2; int target=a; target=b+3; }"
    )
    assert changed.export_source() == expected
    old, new = graph.to_dict(), changed.to_dict()
    assert [n["id"] for n in new["nodes"]] == [n["id"] for n in old["nodes"]]
    assert [e for e in new["edges"] if e["kind"] == "execution"] == [
        e for e in old["edges"] if e["kind"] == "execution"
    ]
    before = {edge_key(e): e["id"] for e in old["edges"]}
    after = {edge_key(e): e["id"] for e in new["edges"]}
    assert len(set(before) - set(after)) == len(set(after) - set(before)) == 1
    assert all(after[k] == before[k] for k in set(before) & set(after))
    added = next(e for e in new["edges"] if edge_key(e) not in before)
    assert added["from"] == {"nodeId": operation["sourceNodeId"], "portId": "value"}
    assert added["to"] == {"nodeId": operation["nodeId"], "portId": "use:b"}
    assert graph.export_source() != changed.export_source()
    assert restore_graph(expected, new, entries=["step"]).to_dict() == new


@pytest.mark.parametrize(
    ("cpp_type", "literal"), [("int", "7"), ("float", "7.0f"), ("double", "7.0"), ("bool", "true")]
)
def test_all_four_exact_scalar_types_accept_literal_to_declaration_wire(cpp_type, literal):
    raw = f"void step(){{ {cpp_type} b={literal}; {cpp_type} target={literal}; }}".encode()
    graph = parsed(raw)
    changed = apply(graph, [wire(graph)])
    assert changed.source_bytes == raw.replace(f"target={literal}".encode(), b"target=b")
    assert changed.source_hash != graph.source_hash


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_byte_span_wire_retains_bom_unicode_comments_trivia_opaque_and_ids(bom, newline):
    raw = (
        bom
        + newline.join(
            [
                "// TEST-ONLY: měření 🚦",
                "template<class T> T untouched(T x){return x;}",
                "void step(){",
                "\tconst int měřič = 123; // zdroj",
                "\tint a = 2;",
                "\tint target /* vlevo */ = (a /* vpravo */ + 4);",
                "}",
                "auto opaque=[](){return untouched(3);}; // přesně",
                "",
            ]
        ).encode()
    )
    graph = parsed(raw)
    operation = wire(graph, source="měřič")
    node = variable(graph, "target")
    span = next(s["sourceSpan"] for s in node["editSlots"] if s["id"] == operation["slotId"])
    expected = raw[: span["startByte"]] + "měřič".encode() + raw[span["endByte"] :]
    changed = apply(graph, [operation])
    assert changed.export_source() == expected
    assert opaque_bytes(graph) == opaque_bytes(changed)
    assert changed.source_bytes.startswith(bom)
    if newline == "\r\n":
        assert b"\n" not in changed.source_bytes.replace(b"\r\n", b"")
    assert {n["id"] for n in graph.to_dict()["nodes"]} == {
        n["id"] for n in changed.to_dict()["nodes"]
    }


def test_repeat_reference_and_existing_driver_merge_preserve_surviving_edges():
    graph = parsed(b"void step(){int a=1; int b=2; int target=a+a+b;}")
    changed = apply(graph, [wire(graph)])
    assert changed.source_bytes.endswith(b"int target=b+a+b;}")
    old_data = {edge_key(e): e["id"] for e in graph.to_dict()["edges"] if e["kind"] == "data"}
    new_data = {edge_key(e): e["id"] for e in changed.to_dict()["edges"] if e["kind"] == "data"}
    assert old_data == new_data  # Both references still used; only the CST leaf changes.


def test_two_distinct_wire_slots_and_literal_edit_in_one_atomic_transaction():
    graph = parsed(b"void step(){int a=1; int b=2; int c=3; int target=a+4;}")
    c = variable(graph, "c")
    literal = {"nodeId": c["id"], "slotId": c["editSlots"][0]["id"], "replacement": "300"}
    changed = apply(graph, [wire(graph), wire(graph, source="c", slot_index=1), literal])
    assert changed.source_bytes == b"void step(){int a=1; int b=2; int c=300; int target=b+c;}"


def test_wire_uses_before_assignment_value_and_can_be_rewired_repeatedly():
    graph = parsed()
    changed = apply(graph, [wire(graph, kind="assignment", source="target")])
    assert changed.source_bytes == graph.source_bytes
    assert changed.to_dict() == graph.to_dict()
    changed = apply(graph, [wire(graph)])
    restored = apply(changed, [wire(changed, source="a")])
    assert restored.source_bytes == graph.source_bytes
    assert [n["id"] for n in restored.to_dict()["nodes"]] == [
        n["id"] for n in graph.to_dict()["nodes"]
    ]


@pytest.mark.parametrize("source", ["target", "later"])
def test_self_cycle_and_forward_reference_are_rejected(source):
    graph = parsed(b"void step(){int b=1; int target=b; int later=2;}")
    rejected(graph, [wire(graph, source=source)])


def test_indirect_cycle_is_rejected_without_reordering_statements():
    graph = parsed(b"void step(){int target=1; int b=target;}")
    rejected(graph, [wire(graph)])


@pytest.mark.parametrize(
    ("typ", "literal"), [("float", "2.0f"), ("double", "2.0"), ("bool", "true")]
)
def test_implicit_conversion_is_not_compatible_type_evidence(typ, literal):
    graph = parsed(f"void step(){{{typ} b={literal}; int a=1; int target=a;}}".encode())
    rejected(graph, [wire(graph)])


@pytest.mark.parametrize("statement", ["b=3;", "b=b+3;"])
def test_declaration_with_overwritten_value_is_not_a_source(statement):
    graph = parsed(f"void step(){{int a=1; int b=2; {statement} int target=a;}}".encode())
    rejected(graph, [wire(graph)])


@pytest.mark.parametrize(
    "raw",
    [
        b"void step(){int a=1; int b=2; unknown(); int target=3;}",
        b"void step(){auto b=unknown(); int target=3;}",
        b"void step(){int b=1; int target=missing;}",
        b"void step(){int b=; int target=3;}",
        b"#define b hidden\nvoid step(){int b=1; int target=3;}",
        b"void step(){int b=1; volatile int other=2; int target=3;}",
    ],
)
def test_opaque_macro_unresolved_and_invalid_inputs_have_no_wire_authority(raw):
    graph = parsed(raw)
    assert graph.data_wire_inputs() == []
    rejected(
        graph,
        [
            {
                "kind": "rewireDataInput",
                "regionId": "forged",
                "nodeId": "forged",
                "slotId": "forged",
                "sourceNodeId": "forged",
            }
        ],
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"void step(){int b=1; if(true){} int target=3;}",
        b"void step(){if(true){int b=1;} int target=3;}",
        b"void step(){int b=1; if(true){int target=3;}}",
        b"void other(){int b=1;} void step(){int target=3;}",
        b"void step(){int b=1; int b=2; int target=3;}",
        b"void step(int b){int b=1; int target=3;}",
        b"void step(){int b=1; if(true){int b=2;} int target=3;}",
    ],
)
def test_cross_region_scope_and_shadowed_sources_not_advertised(raw):
    graph = parsed(raw)
    assert graph.data_wire_inputs() == []


def test_other_function_and_parameter_cannot_be_forged_as_source():
    raw = b"void other(){int other=1;} void step(int seed){int b=1; int target=3;}"
    graph = parse_source(raw, entries=["other", "step"])
    operation = wire(graph)
    for source in (
        variable(graph, "other"),
        next(n for n in graph.to_dict()["nodes"] if n.get("function") == "step"),
    ):
        rejected(graph, [{**operation, "sourceNodeId": source["id"]}])


def test_legacy_text_edit_cannot_bypass_wire_authority():
    graph = parsed()
    operation = wire(graph)
    rejected(
        graph, [{"nodeId": operation["nodeId"], "slotId": operation["slotId"], "replacement": "b"}]
    )
    literal_graph = parsed(b"void step(){int b=1; int target=3;}")
    literal = wire(literal_graph)
    rejected(
        literal_graph,
        [{"nodeId": literal["nodeId"], "slotId": literal["slotId"], "replacement": "b"}],
    )


@pytest.mark.parametrize("failure", ["hash", "bytes", "region", "node", "source", "slot"])
def test_stale_snapshot_and_identifiers_are_rejected_atomically(failure):
    graph = parsed()
    operation = wire(graph)
    kwargs = {}
    if failure == "hash":
        kwargs["hash"] = "0" * 64
    elif failure == "bytes":
        kwargs["raw"] = graph.source_bytes + b" "
    else:
        fields = {
            "region": "regionId",
            "node": "nodeId",
            "source": "sourceNodeId",
            "slot": "slotId",
        }
        operation[fields[failure]] = "stale"
    rejected(graph, [operation], **kwargs)


def test_same_bytes_independent_snapshot_ids_cannot_authorize_active_graph():
    earlier, current = parsed(), parsed()
    assert earlier.source_hash == current.source_hash
    rejected(current, [wire(earlier)])
    operation = wire(current)
    operation["sourceNodeId"] = variable(earlier, "b")["id"]
    rejected(current, [operation])


def test_stale_region_after_change_rejected_even_with_surviving_node_ids():
    graph = parsed()
    operation = wire(graph)
    changed = apply(graph, [operation])
    rejected(changed, [operation])
    assert apply(changed, [wire(changed, source="a")]).source_bytes == graph.source_bytes


@pytest.mark.parametrize(
    "bad",
    [None, [], {}, {"kind": "rewireDataInput"}, {"nodeId": [], "slotId": "x", "replacement": "1"}],
)
def test_malformed_operations_reject_without_partial_results(bad):
    graph = parsed()
    rejected(graph, [wire(graph), bad])


def test_overlapping_slot_requests_and_mixed_invalid_batch_are_atomic():
    graph = parsed()
    operation = wire(graph)
    rejected(graph, [operation, operation])
    rejected(graph, [operation, {**operation, "sourceNodeId": operation["nodeId"]}])
    rejected(graph, [operation, {**operation, "replacement": "b; unknown();"}])
    c = variable(graph, "a")
    rejected(
        graph,
        [operation, {"nodeId": c["id"], "slotId": c["editSlots"][0]["id"], "replacement": "true"}],
    )


def test_json_edit_api_advertises_and_applies_real_wire_and_rejects_forgery():
    graph = parsed()
    request = envelope(graph, [wire(graph)])
    response = process_request(request)
    assert response["ok"]
    assert response["dataWireVersion"] == 1
    assert response["dataWireInputs"]
    assert base64.b64decode(response["sourceBase64"]) == apply(graph, [wire(graph)]).source_bytes
    discovery = process_request(
        {"operation": "parse", "sourceBase64": request["sourceBase64"], "entries": ["step"]}
    )
    assert discovery["dataWireInputs"]
    target_id = variable(graph, "target")["id"]
    capability = next(c for c in graph.data_wire_inputs() if c["nodeId"] == target_id)
    assert capability["kind"] == "rewireDataInput"
    assert capability["cppType"] == "int"
    assert capability["sourceNodeIds"] == [variable(graph, "a")["id"], variable(graph, "b")["id"]]
    forged = copy.deepcopy(request)
    node = next(n for n in forged["graph"]["nodes"] if n["id"] == target_id)
    node["editSlots"][0]["sourceSpan"]["startByte"] = 0
    rejected_response = process_request(forged)
    assert rejected_response["ok"] is False
    assert "sourceBase64" not in rejected_response
    assert graph.source_bytes == parsed().source_bytes


def test_backend_capabilities_are_detached_and_json_cannot_add_wires():
    graph = parsed()
    capabilities = graph.data_wire_inputs()
    capabilities[0]["sourceNodeIds"].clear()
    assert graph.data_wire_inputs()[0]["sourceNodeIds"]
    request = envelope(graph, [wire(graph)])
    target_id = request["edits"][0]["nodeId"]
    edge = next(
        e
        for e in request["graph"]["edges"]
        if e["kind"] == "data" and e["to"]["nodeId"] == target_id
    )
    edge["from"]["nodeId"] = variable(graph, "b")["id"]
    response = process_request(request)
    assert response["ok"] is False
    assert "sourceBase64" not in response


def test_unedited_parameter_dependency_survives_new_local_data_wire():
    graph = parsed(b"void step(int seed){int b=1; int target=seed+2;}")
    old_parameter_edge = next(e for e in graph.to_dict()["edges"] if e["kind"] == "data")
    changed = apply(graph, [wire(graph, slot_index=1)])
    assert changed.source_bytes == b"void step(int seed){int b=1; int target=seed+b;}"
    assert old_parameter_edge in changed.to_dict()["edges"]


def test_wire_into_comparison_leaf_keeps_result_type_and_other_operand():
    graph = parsed(b"void step(){int b=1; int a=2; bool target=a>0;}")
    changed = apply(graph, [wire(graph, slot_index=1)])
    assert changed.source_bytes == b"void step(){int b=1; int a=2; bool target=a>b;}"
    assert variable(changed, "target")["cppType"] == "bool"
    assert [
        p["cppType"]
        for p in variable(changed, "target")["ports"]
        if p["kind"] == "data" and p["direction"] == "in"
    ] == ["int", "int"]


def test_external_call_is_a_source_and_order_boundary():
    raw = b"void step(){int b=1; sink(b); int a=2; int target=a;}"
    bindings = {
        "sink": {
            "operation": "test-only:wire-sink",
            "returnType": "void",
            "parameterTypes": ["int"],
        }
    }
    graph = parse_source(raw, entries=["step"], bindings=bindings)
    rejected(graph, [wire(graph)])
    changed = apply(graph, [wire(graph, source="a")])
    assert changed.source_bytes == raw
    assert changed.to_dict() == graph.to_dict()


def test_selected_unknown_neighbor_preserves_opaque_bytes_but_allows_proven_body():
    raw = b"void unknown(){auto opaque=[](){return 1;};}\r\nvoid step(){int b=1; int target=2;}"
    graph = parse_source(raw, entries=["unknown", "step"])
    changed = apply(graph, [wire(graph)])
    assert changed.source_bytes == raw.replace(b"target=2", b"target=b")
    assert opaque_bytes(changed) == opaque_bytes(graph)


def test_assignment_node_cannot_pose_as_a_declaration_source():
    graph = parsed(b"void step(){int b=1; b=2; int a=3; int target=a;}")
    operation = wire(graph)
    operation["sourceNodeId"] = variable(graph, "b", "assignment")["id"]
    rejected(graph, [operation])


def test_if_condition_slot_does_not_authorize_data_wire():
    graph = parsed(b"void step(){int b=1; if(b>0){int a=2;}}")
    condition = next(n for n in graph.to_dict()["nodes"] if n["kind"] == "if")
    rejected(
        graph,
        [
            {
                "kind": "rewireDataInput",
                "regionId": graph.construction_regions()[0]["id"],
                "nodeId": condition["id"],
                "slotId": condition["editSlots"][0]["id"],
                "sourceNodeId": variable(graph, "b")["id"],
            }
        ],
    )


@pytest.mark.parametrize("field", ["cppType", "symbol", "kind"])
def test_json_slot_metadata_cannot_authorize_a_different_scalar_input(field):
    graph = parsed()
    request = envelope(graph, [wire(graph)])
    target = next(n for n in request["graph"]["nodes"] if n.get("variable") == "target")
    target["editSlots"][0][field] = "forged"
    response = process_request(request)
    assert response["ok"] is False
    assert "sourceBase64" not in response


def test_stale_region_after_identical_byte_identity_reorder():
    graph = parsed(b"void step(){int b=1; int a=2; a=a+1; a=a+1; int target=b;}")
    region = graph.construction_regions()[0]
    ids = region["nodeIds"]
    changed = graph.apply_construction(
        {
            "kind": "setSequence",
            "regionId": region["id"],
            "nodeIds": [ids[0], ids[1], ids[3], ids[2], ids[4]],
        },
        expected_source_hash=graph.source_hash,
        current_source=graph.source_bytes,
    )
    assert changed.source_bytes == graph.source_bytes
    assert changed.source_hash == graph.source_hash
    rejected(changed, [wire(graph)])
    assert apply(changed, [wire(changed)]).source_bytes == graph.source_bytes


@pytest.mark.parametrize(
    "raw",
    [
        b"void step(){int a=1; const int b=2; auto target=(a+a*b)+3;}",
        b"void step(int seed){int a=1; int b=2; bool flag=a>seed; int target=a+3;}",
        b"void step(){float a=1.0f; float b=2.0f; float target=-a+3.0f; target=b;}",
        b"void step(){double a=1.0; double b=2.0; double target=a/3.0;}",
        b"void step(){bool a=true; bool b=false; bool target=!a||b;}",
    ],
)
def test_every_advertised_source_is_accepted_and_changes_only_owned_leaf(raw):
    graph = parsed(raw)
    document = graph.to_dict()
    nodes = {n["id"]: n for n in document["nodes"]}
    capabilities = graph.data_wire_inputs()
    assert capabilities
    for capability in capabilities:
        target = nodes[capability["nodeId"]]
        span = next(s["sourceSpan"] for s in target["editSlots"] if s["id"] == capability["slotId"])
        for source_id in capability["sourceNodeIds"]:
            operation = {k: capability[k] for k in ("kind", "regionId", "nodeId", "slotId")}
            operation["sourceNodeId"] = source_id
            changed = apply(graph, [operation])
            expected = (
                raw[: span["startByte"]]
                + nodes[source_id]["variable"].encode()
                + raw[span["endByte"] :]
            )
            assert changed.source_bytes == expected
            assert (
                restore_graph(expected, changed.to_dict(), entries=["step"]).to_dict()
                == changed.to_dict()
            )
    assert graph.to_dict() == document


def public_regions(raw, entries=("step",)):
    # Actual detached caller API, with real parser dependencies; no MCP import,
    # fabricated graph, transport, loader, or receipt/capability replacement.
    from espos_mcp.codegraph_readonly import analyze_receipt
    from espos_mcp.codegraph_transforms import transform_receipt

    encoded = base64.b64encode(raw).decode("ascii")
    analyzed = analyze_receipt({"sourceBase64": encoded, "entries": list(entries)})
    assert analyzed["ok"], analyzed
    assert analyzed["data"]["analysisStatus"] == "Analyzed"
    before = analyzed["data"]
    request = {
        "schemaVersion": 1,
        "sourceBase64": encoded,
        "entries": list(entries),
        "graph": before["graph"],
        "expectedSourceHash": before["graph"]["sourceHash"],
    }
    original = copy.deepcopy(request)
    discovered = transform_receipt("list_cpp_regions_v1", request)
    assert discovered["ok"], discovered
    assert request == original
    data = discovered["data"]
    assert data["sourceBase64"] == encoded
    assert data["graph"] == before["graph"]
    assert data["sourceChanged"] is False
    assert data["ownerValidated"] is data["filesystemWritten"] is False
    assert data["constructionVersion"] == data["dataWireVersion"] == 1
    return data, request


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_actual_public_unicode_identifier_discovery_and_wire_roundtrip(bom, newline):
    from espos_mcp.codegraph_transforms import transform_receipt

    raw = bom + newline.join(
        [
            "// TEST-ONLY měření 🚦",
            "template<class T> T opaque(T x){return x;}",
            "void step(){ int měřič=1; int b=2; int target=měřič; }",
            "auto untouched=[](){return opaque(3);};",
            "",
        ]
    ).encode("utf-8")
    data, request = public_regions(raw)
    graph = restore_graph(raw, data["graph"], entries=["step"])
    assert data["regions"] == graph.construction_regions()
    assert data["dataWireInputs"] == graph.data_wire_inputs()
    target = variable(graph, "target")
    assert any(p["id"] == "use:měřič" for p in target["ports"])
    changed = transform_receipt("edit_cpp_v1", {**request, "edits": [wire(graph)]})
    assert changed["ok"], changed
    changed_data = changed["data"]
    expected = raw.replace("target=měřič".encode(), b"target=b")
    assert base64.b64decode(changed_data["sourceBase64"]) == expected
    newer = restore_graph(expected, changed_data["graph"], entries=["step"])
    assert opaque_bytes(newer) == opaque_bytes(graph)
    assert [n["id"] for n in newer.to_dict()["nodes"]] == [
        n["id"] for n in graph.to_dict()["nodes"]
    ]
    restored = transform_receipt(
        "edit_cpp_v1",
        {
            **request,
            "sourceBase64": changed_data["sourceBase64"],
            "expectedSourceHash": newer.source_hash,
            "graph": changed_data["graph"],
            "edits": [wire(newer, source="měřič")],
        },
    )
    assert restored["ok"], restored
    assert base64.b64decode(restored["data"]["sourceBase64"]) == raw
    assert restored["data"]["dataWireVersion"] == 1


@pytest.mark.parametrize(
    ("cpp_type", "literal"), [("int", "2"), ("float", "2.0f"), ("double", "2.0"), ("bool", "true")]
)
def test_literal_unicode_declaration_and_parameter_keep_exact_symbol_proof(cpp_type, literal):
    raw = (
        f"void step({cpp_type} vstup){{{cpp_type} měřič={literal}; {cpp_type} cíl=vstup; cíl=cíl;}}"
    ).encode()
    graph = parsed(raw)
    changed = apply(graph, [wire(graph, target="cíl", source="měřič")])
    assert changed.source_bytes == raw.replace("cíl=vstup".encode(), "cíl=měřič".encode())
    assert (
        restore_graph(changed.source_bytes, changed.to_dict(), entries=["step"]).to_dict()
        == changed.to_dict()
    )


@pytest.mark.parametrize(
    "body",
    [
        "void step(){int měřič=1; int měřič=2; int target=3;}",
        "void step(int měřič){int měřič=1; int target=3;}",
        "void step(){int měřič=1; if(true){int měřič=2;} int target=3;}",
    ],
)
def test_unicode_duplicate_parameter_and_nested_shadow_have_no_wire_proof(body):
    graph = parsed(body.encode("utf-8"))
    assert graph.data_wire_inputs() == []
    rejected(graph, [wire(graph, source="měřič")])


@pytest.mark.parametrize(
    "raw",
    [
        "void step(){float měřič=2.0f; int a=1; int target=a;}",
        "void step(){int target=1; int měřič=target;}",
        "void step(){int měřič=1; int target=měřič;}",
        "void step(){int a=1; int měřič=2; měřič=3; int target=a;}",
        "void step(){int měřič=1; if(true){} int target=3;}",
    ],
)
def test_unicode_wrong_type_cycle_assignment_and_region_fences(raw):
    graph = parsed(raw.encode("utf-8"))
    source = "target" if "int target=měřič" in raw else "měřič"
    rejected(graph, [wire(graph, source=source)])


def test_unicode_confusable_spelling_cannot_supply_wrong_type_or_unresolved_reference():
    # Latin a and Cyrillic а are separate byte spellings, never aliases.
    graph = parsed("void step(){int a=1; float а=2.0f; int target=a;}".encode())
    target = variable(graph, "target")
    assert target["editSlots"][0]["symbol"] == "a"
    rejected(graph, [wire(graph, source="а")])
    assert apply(graph, [wire(graph, source="a")]).to_dict() == graph.to_dict()
    unresolved = parsed("void step(){int а=1; int target=a;}".encode())
    assert unresolved.data_wire_inputs() == []
    assert any(
        n["kind"] == "opaque" and n["scope"] == "selected" for n in unresolved.to_dict()["nodes"]
    )


@pytest.mark.parametrize(
    "unsupported",
    [
        r"void suspect(){int \u011b=1; int target=2;}",
        r"void suspect(){int b=1; int \u0062=2; int target=3;}",
        r"void suspect(int \u0062){int b=1; int target=2;}",
        r"void suspect(int \u0062){}",
        r"void suspect(int \u0062){/* TEST-ONLY */}",
        r"void suspect(){int b=1; if(true){int \U00000062=2;} int target=3;}",
        r"void suspect(){int měřič=1; int target=\u006děřič;}",
        "void suspect(){int é=1; int e\u0301=2; int target=3;}",
        "void suspect(int e\u0301){int b=1; int target=2;}",
    ],
)
def test_unsupported_identifier_scopes_are_opaque_but_other_public_regions_work(unsupported):
    raw = b"\xef\xbb\xbf// TEST-ONLY\r\n" + (
        unsupported + "\r\nvoid step(){int b=1; int target=2;}\r\n"
    ).encode("utf-8")
    data, _request = public_regions(raw, entries=("suspect", "step"))
    graph = restore_graph(raw, data["graph"], entries=["suspect", "step"])
    entry = next(n for n in data["graph"]["nodes"] if n.get("function") == "suspect")
    assert entry["ports"] == entry["editSlots"] == []
    assert all(r["entryNodeId"] != entry["id"] for r in data["regions"])
    assert all(
        n.get("variable") not in {"é", "e\u0301", "měřič", r"\u011b", r"\u0062"}
        for n in data["graph"]["nodes"]
    )
    operation = wire(graph)
    changed = apply(graph, [operation])
    assert changed.source_bytes == raw.replace(
        b"void step(){int b=1; int target=2;}", b"void step(){int b=1; int target=b;}"
    )
    assert opaque_bytes(changed) == opaque_bytes(graph)
    opaque = next(
        n for n in data["graph"]["nodes"] if n["kind"] == "opaque" and n["scope"] == "selected"
    )
    rejected(graph, [{**operation, "nodeId": opaque["id"]}])


def test_escaped_and_combining_text_in_comments_strings_and_opaque_is_not_an_identifier():
    raw = (
        "// TEST-ONLY \\u0062 e\u0301\r\n"
        'const char* text="\\u0062 e\u0301";\r\n'
        "void step(){/* \\u0062 e\u0301 */ int b=1; int target=2;}\r\n"
    ).encode("utf-8")
    data, _request = public_regions(raw)
    graph = restore_graph(raw, data["graph"], entries=["step"])
    assert data["dataWireInputs"]
    changed = apply(graph, [wire(graph)])
    assert changed.source_bytes == raw.replace(b"target=2", b"target=b")
    assert opaque_bytes(changed) == opaque_bytes(graph)


@pytest.mark.parametrize("name", [r"\u0062", "e\u0301"])
def test_unsupported_macro_identifier_cannot_alias_a_proven_local(name):
    raw = (f"#define {name} hidden\r\nvoid step(){{int b=1; int target=2;}}\r\n").encode()
    data, _request = public_regions(raw)
    assert data["regions"] == data["dataWireInputs"] == []
    graph = restore_graph(raw, data["graph"], entries=["step"])
    assert graph.export_source() == raw
    assert any(n["kind"] == "opaque" and n["scope"] == "selected" for n in data["graph"]["nodes"])


@pytest.mark.parametrize(
    "unproven",
    [
        "void suspect(){int měřič;}",
        "int měřič; void suspect(){int target=měřič;}",
    ],
)
def test_public_uninitialized_unicode_declaration_has_no_inferred_scalar_value(unproven):
    raw = (unproven + "\r\nvoid step(){int b=1; int target=2;}\r\n").encode("utf-8")
    data, _request = public_regions(raw, entries=("suspect", "step"))
    graph = restore_graph(raw, data["graph"], entries=["suspect", "step"])
    suspect = next(n for n in data["graph"]["nodes"] if n.get("function") == "suspect")
    assert all(r["entryNodeId"] != suspect["id"] for r in data["regions"])
    assert not any(n.get("variable") == "měřič" for n in data["graph"]["nodes"])
    changed = apply(graph, [wire(graph)])
    assert changed.source_bytes == raw.replace(
        b"void step(){int b=1; int target=2;}", b"void step(){int b=1; int target=b;}"
    )
    assert opaque_bytes(changed) == opaque_bytes(graph)
