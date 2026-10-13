"""Independent adversarial guards against the frozen construction parser.

Only benign, explicit TEST-ONLY C++ text is parsed. No C++ compilation/execution,
SDK/device access, or import/re-run of the original 113-test module is allowed.
Confirmed bugs stay ordinary RED tests while production is frozen, not xfails.
Session-generation enforcement is a bridge responsibility: tests pass the active
snapshot and require stale region/node IDs to fail even when source bytes match.
"""

import base64
import copy
import os
import subprocess

import pytest

from tools.tabos_code_graph import (
    GraphError,
    parse_source,
    process_request,
    restore_graph,
)

OBSERVE = {
    "sink": {
        "operation": "test-only:guards-observe",
        "returnType": "void",
        "parameterTypes": ["int"],
    }
}
SOURCE = b"void step(){ int value=1; value=value+1; value=value+1; sink(value); }"


@pytest.fixture(autouse=True)
def forbid_process_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Construction guard tests must never spawn a process")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)


def parsed(source=SOURCE, *, entries=("step",), bindings=None):
    return parse_source(
        source, entries=list(entries), bindings=OBSERVE if bindings is None else bindings
    )


def body_region(graph, function="step"):
    entry = next(
        n for n in graph.to_dict()["nodes"] if n["kind"] == "entry" and n["function"] == function
    )
    return next(r for r in graph.construction_regions() if r["entryNodeId"] == entry["id"])


def mutate(graph, mutation):
    return graph.apply_construction(
        mutation, expected_source_hash=graph.source_hash, current_source=graph.source_bytes
    )


def insertion(graph, cpp, *, function="step", before=None):
    return {
        "kind": "insertStatement",
        "regionId": body_region(graph, function)["id"],
        "beforeNodeId": before,
        "cpp": cpp,
    }


def rejected_unchanged(graph, mutation):
    before, raw = graph.to_dict(), graph.source_bytes
    with pytest.raises(GraphError):
        mutate(graph, mutation)
    assert graph.to_dict() == before
    assert graph.export_source() == raw


def envelope(graph, mutation):
    return {
        "operation": "construct",
        "sourceBase64": base64.b64encode(graph.source_bytes).decode(),
        "entries": ["step"],
        "bindings": OBSERVE,
        "graph": graph.to_dict(),
        "expectedSourceHash": graph.source_hash,
        "mutation": mutation,
    }


def opaque_bytes(graph):
    return {
        n["id"]: graph.source_bytes[n["sourceSpan"]["startByte"] : n["sourceSpan"]["endByte"]]
        for n in graph.to_dict()["nodes"]
        if n["kind"] == "opaque"
    }


@pytest.mark.parametrize(
    "parameter",
    ["const int& reserved", "int* reserved", "GuardType reserved", "int (*reserved)(int)"],
)
def test_unprojected_parameter_still_reserves_its_cpp_name(parameter):
    raw = (
        "struct GuardType {}; void step(" + parameter + "){ int value=1; sink(value); }"
    ).encode()
    graph = parsed(raw)
    assert body_region(graph)["nodeIds"]
    rejected_unchanged(graph, insertion(graph, "int reserved=2;"))


def test_nested_local_name_is_not_available_for_top_level_construction():
    graph = parsed(
        b"void step(int condition){ if(condition>0){int reserved=1;} int value=1; sink(value); }"
    )
    rejected_unchanged(graph, insertion(graph, "int reserved=2;"))


def test_branch_and_other_function_members_cannot_be_deleted_through_outer_region():
    graph = parsed(
        b"void step(int condition){ if(condition>0){int inner=1;} int value=1; sink(value); }"
        b"void other(){int elsewhere=2;}",
        entries=("step", "other"),
    )
    outer = body_region(graph)
    for symbol in ("inner", "elsewhere"):
        target = next(n for n in graph.to_dict()["nodes"] if n.get("variable") == symbol)
        rejected_unchanged(
            graph, {"kind": "deleteNode", "regionId": outer["id"], "nodeId": target["id"]}
        )


def test_unknown_selected_neighbor_does_not_disable_or_change_proven_function():
    raw = (
        b"void unknown(){ auto callback=[](){return 7;}; }\n"
        b"void step(){ int value=1; sink(value); }\n"
    )
    graph = parsed(raw, entries=("unknown", "step"))
    unknown_id = next(n["id"] for n in graph.to_dict()["nodes"] if n.get("function") == "unknown")
    assert all(r["entryNodeId"] != unknown_id for r in graph.construction_regions())
    changed = mutate(graph, insertion(graph, "value=value+3;"))
    assert opaque_bytes(changed) == opaque_bytes(graph)
    assert changed.source_bytes.startswith(raw[: raw.index(b"void step")])


def test_assignment_into_const_local_is_rejected_atomically():
    graph = parsed(b"void step(){ const int value=1; sink(value); }")
    rejected_unchanged(graph, insertion(graph, "value=2;"))


@pytest.mark.parametrize(
    "receiver",
    ["meter", "teploměr", "měřič"],
    ids=["ascii-control", "unicode-receiver-1", "unicode-receiver-2"],
)
def test_receiver_name_shadow_is_rejected_for_every_utf8_identifier(receiver):
    # Explicit harmless source. Introducing a local int with the receiver's exact
    # C++ name changes lookup of receiver.read(); it must not retain that binding.
    raw = (
        f"struct Meter{{void read(){{}}}}; Meter {receiver};\n"
        f"void step(){{ int value=1; {receiver}.read(); }}"
    ).encode()
    bindings = {
        f"{receiver}.read": {
            "operation": "test-only:guards-meter-read",
            "returnType": "void",
            "parameterTypes": [],
        }
    }
    graph = parsed(raw, bindings=bindings)
    assert any(
        n.get("binding", {}).get("callee") == f"{receiver}.read" for n in graph.to_dict()["nodes"]
    )
    rejected_unchanged(graph, insertion(graph, f"int {receiver}=3;"))


@pytest.mark.parametrize(
    ("callee", "reserved"),
    [
        ("měření::teploměr.read", "měření"),
        ("měření::teploměr.read", "teploměr"),
        ("::měření::teploměr.read", "teploměr"),
        ("rack.měřič.read", "měřič"),
    ],
)
def test_qualified_binding_reserves_actual_unicode_cst_leaf_names(callee, reserved):
    # The existing policy conservatively reserves ALL callee identifier leaves.
    # This does not claim that a local always changes explicitly qualified lookup.
    raw = (
        "struct Meter{void read(){}}; namespace měření {Meter teploměr;}\n"
        "struct Rack{Meter měřič;}; Rack rack;\n"
        f"void step(){{int value=1; {callee}();}}"
    ).encode()
    bindings = {
        callee: {
            "operation": "test-only:guards-qualified-read",
            "returnType": "void",
            "parameterTypes": [],
        }
    }
    graph = parsed(raw, bindings=bindings)
    assert any(n.get("binding", {}).get("callee") == callee for n in graph.to_dict()["nodes"])
    rejected_unchanged(graph, insertion(graph, f"int {reserved}=3;"))


def test_binding_comment_text_is_not_a_cst_identifier_reservation():
    raw = (
        "struct Meter{void read(){}}; Meter meter;\n"
        "void step(){int value=1; meter /* měřič */ .read();}"
    ).encode()
    bindings = {
        "meter.read": {
            "operation": "test-only:guards-comment-read",
            "returnType": "void",
            "parameterTypes": [],
        }
    }
    graph = parsed(raw, bindings=bindings)
    changed = mutate(graph, insertion(graph, "int měřič=3;"))
    assert "int měřič=3;".encode() in changed.source_bytes
    assert "meter /* měřič */ .read();".encode() in changed.source_bytes
    assert opaque_bytes(changed) == opaque_bytes(graph)


@pytest.mark.parametrize("gap", ["// mezera: žluťoučký\r\n", "/* měření 🚦 */", "/* A */\t/* B */"])
def test_comment_gaps_are_immutable_reorder_boundaries(gap):
    graph = parsed(("void step(){ int value=1; " + gap + " value=value+1; sink(value); }").encode())
    region = body_region(graph)
    assert "setSequence" not in region["allowedOperations"]
    rejected_unchanged(
        graph,
        {
            "kind": "setSequence",
            "regionId": region["id"],
            "nodeIds": list(reversed(region["nodeIds"])),
        },
    )


def test_internal_utf8_line_comment_moves_with_its_statement_not_neighbor():
    raw = (
        "void step(){\r\n int value=1;\r\n value = // první 🚦\r\n value+2;\r\n"
        " value = /* druhý */ value+3;\r\n sink(value);\r\n}\r\n"
    ).encode()
    graph = parsed(raw)
    ids = body_region(graph)["nodeIds"]
    original_statements = {
        n["id"]: raw[n["sourceSpan"]["startByte"] : n["sourceSpan"]["endByte"]]
        for n in graph.to_dict()["nodes"]
        if n["id"] in ids
    }
    changed = mutate(
        graph,
        {
            "kind": "setSequence",
            "regionId": body_region(graph)["id"],
            "nodeIds": [ids[0], ids[2], ids[1]],
        },
    )
    for node in changed.to_dict()["nodes"]:
        if node["id"] in original_statements:
            span = node["sourceSpan"]
            assert (
                changed.source_bytes[span["startByte"] : span["endByte"]]
                == original_statements[node["id"]]
            )
    assert b"\n" not in changed.source_bytes.replace(b"\r\n", b"")


def test_delete_removes_only_owned_span_not_leading_or_trailing_comments():
    raw = (
        "void step(){\r\n int value=1;\r\n // vedlejší komentář 🚦\r\n"
        " int unused /* uvnitř vlastněného příkazu */ =2; // trailing zůstává\r\n sink(value);\r\n}"
    ).encode()
    graph = parsed(raw)
    target = next(n for n in graph.to_dict()["nodes"] if n.get("variable") == "unused")
    span = target["sourceSpan"]
    changed = mutate(
        graph, {"kind": "deleteNode", "regionId": body_region(graph)["id"], "nodeId": target["id"]}
    )
    assert changed.export_source() == raw[: span["startByte"]] + raw[span["endByte"] :]


@pytest.mark.parametrize("construction", ["insert", "delete", "reorder"])
def test_bom_multibyte_prefix_and_opaque_suffix_are_exact_for_each_mutation(construction):
    prefix = ("// TEST-ONLY: měřič 🚦\r\ntemplate<class T> T keep(T x){return x;}\r\n").encode()
    suffix = ("\r\nauto opaque=[](){return keep(3);}; // žluťoučký\r\n").encode()
    body = (
        b"void step(){\r\n int value=1;\r\n value=value+2;\r\n value=value+3;\r\n sink(value);\r\n}"
    )
    raw = b"\xef\xbb\xbf" + prefix + body + suffix
    graph = parsed(raw)
    region = body_region(graph)
    ids = region["nodeIds"]
    if construction == "insert":
        mutation = insertion(graph, "value=value+4;")
    elif construction == "delete":
        mutation = {"kind": "deleteNode", "regionId": region["id"], "nodeId": ids[2]}
    else:
        mutation = {
            "kind": "setSequence",
            "regionId": region["id"],
            "nodeIds": [ids[0], ids[2], ids[1]],
        }
    changed = mutate(graph, mutation)
    assert opaque_bytes(changed) == opaque_bytes(graph)
    assert changed.source_bytes.startswith(b"\xef\xbb\xbf" + prefix)
    assert changed.source_bytes.endswith(suffix)
    assert b"\n" not in changed.source_bytes.replace(b"\r\n", b"")


def test_old_region_rejected_after_same_bytes_duplicate_identity_reorder():
    original = parsed()
    region = body_region(original)
    ids = region["nodeIds"]
    current = mutate(
        original,
        {"kind": "setSequence", "regionId": region["id"], "nodeIds": [ids[0], ids[2], ids[1]]},
    )
    assert current.source_bytes == original.source_bytes
    assert current.source_hash == original.source_hash
    assert body_region(current)["nodeIds"] == [ids[0], ids[2], ids[1]]
    assert body_region(current)["id"] != region["id"]
    stale = {"kind": "deleteNode", "regionId": region["id"], "nodeId": ids[1]}
    rejected_unchanged(current, stale)
    response = process_request(envelope(current, stale))
    assert response["ok"] is False
    assert "sourceBase64" not in response
    assert "stale" in response["diagnostics"][0]["message"].lower()
    # Proof that rejection is the stale anchor, not an unusable valid current graph.
    restored = restore_graph(
        current.source_bytes, current.to_dict(), entries=["step"], bindings=OBSERVE
    )
    assert restored.to_dict() == current.to_dict()


def test_old_node_ids_rejected_with_fresh_region_after_independent_parse():
    earlier, current = parsed(), parsed()
    assert earlier.source_hash == current.source_hash
    stale_ids = body_region(earlier)["nodeIds"]
    region = body_region(current)
    assert set(stale_ids).isdisjoint(region["nodeIds"])
    rejected_unchanged(
        current, {"kind": "setSequence", "regionId": region["id"], "nodeIds": stale_ids}
    )
    rejected_unchanged(
        current, {"kind": "deleteNode", "regionId": region["id"], "nodeId": stale_ids[1]}
    )


def test_old_and_current_identical_bytes_snapshots_cannot_be_partially_grafted():
    earlier, current = parsed(), parsed()
    mutation = insertion(current, "value=value+3;")
    request = envelope(current, mutation)
    request["graph"] = copy.deepcopy(request["graph"])
    # This is NOT replay of a complete historical snapshot (bridge-generation
    # ownership). It is an invalid mixed snapshot, which core must reject itself.
    request["graph"]["nodes"] = earlier.to_dict()["nodes"]
    response = process_request(request)
    assert response["ok"] is False
    assert "sourceBase64" not in response
    assert current.source_bytes == SOURCE
