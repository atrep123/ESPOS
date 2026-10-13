"""Small test-only C++ fixtures; no hardware, SDK fakes, or production claims.

Run only this module. Compiler regression invokes at most one lightweight g++
process at a time, never CMake/LVGL/firmware. Temporary files use pytest basetemp.
"""

import base64
import copy
import hashlib
import json
import os
import shutil
import subprocess

import pytest

from tools.tabos_code_graph import (
    GraphError,
    parse_source,
    process_request,
    restore_graph,
    validate_graph,
)


def binding(name, result="void", parameters=()):
    return {
        "operation": "test-only:" + name,
        "returnType": result,
        "parameterTypes": list(parameters),
    }


BINDINGS = {
    "first": binding("first", parameters=("int",)),
    "second": binding("second", parameters=("int",)),
    "tail": binding("tail"),
    "read": binding("read", result="int"),
    "other": binding("other", result="int"),
}


def selected(graph, kind=None):
    return [
        node
        for node in graph.to_dict()["nodes"]
        if node.get("scope") != "outside-selection" and (kind is None or node["kind"] == kind)
    ]


def token_edit(graph, node, kind, replacement, index=0):
    slot = [slot for slot in node["editSlots"] if slot["kind"] == kind][index]
    return {"nodeId": node["id"], "slotId": slot["id"], "replacement": replacement}


def edit(graph, edits):
    return graph.apply_edits(
        edits, expected_source_hash=graph.source_hash, current_source=graph.source_bytes
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
@pytest.mark.parametrize("final_newline", [False, True])
def test_source_graph_source_exact_unicode_trivia(newline, bom, final_newline):
    text = newline.join(
        [
            "// Test-only: žluťoučký, \t  ",
            "void step() {",
            "\tint x = 1; // přesně  ",
            "\tx = x + 2;",
            "}",
        ]
    ) + (newline if final_newline else "")
    raw = bom + text.encode("utf-8")
    graph = parse_source(raw, entries=["step"])
    assert graph.export_source() == raw
    assert graph.source_hash == hashlib.sha256(raw).hexdigest()
    assert graph.to_dict()["projection"] == "complete"
    assert [n["kind"] for n in selected(graph)] == ["entry", "declaration", "assignment"]
    # JSON really is serializable, detached, with byte-based exact span hashes.
    document = json.loads(json.dumps(graph.to_dict()))
    for node in document["nodes"]:
        span = node["sourceSpan"]
        assert (
            span["sha256"] == hashlib.sha256(raw[span["startByte"] : span["endByte"]]).hexdigest()
        )
    document["nodes"].clear()
    assert graph.to_dict()["nodes"]


def test_known_call_and_literal_edits_preserve_opaque_bytes_and_ids():
    raw = (
        "// test-only fixture\r\nvoid step() {\r\n"
        "  int x = 10 /* český komentář */;\r\n"
        "  first /* volání */ (x);\r\n"
        "  auto opaque = [ ] (int z) { return z * 3; }; // NEVER normalized\r\n"
        "  UNKNOWN(opaque);\r\n}\r\n"
    ).encode()
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    before = graph.to_dict()
    declaration = selected(graph, "declaration")[0]
    call = selected(graph, "call")[0]
    changed = edit(
        graph,
        [
            token_edit(graph, declaration, "literal", "12345"),
            token_edit(graph, call, "call", "second"),
        ],
    )
    expected = raw.replace(b"10 /*", b"12345 /*").replace(b"first /*", b"second /*")
    assert changed.export_source() == expected
    assert graph.export_source() == raw
    assert [n["id"] for n in before["nodes"]] == [n["id"] for n in changed.to_dict()["nodes"]]
    assert [e["id"] for e in before["edges"]] == [e["id"] for e in changed.to_dict()["edges"]]
    for old, new in zip(before["nodes"], changed.to_dict()["nodes"], strict=True):
        if old["kind"] == "opaque":
            a, b = old["sourceSpan"], new["sourceSpan"]
            assert raw[a["startByte"] : a["endByte"]] == expected[b["startByte"] : b["endByte"]]
    # Repeated edits use the same IDs but the new spans/hash.
    new_call = selected(changed, "call")[0]
    again = edit(changed, [token_edit(changed, new_call, "call", "first")])
    assert again.export_source() == raw.replace(b"10 /*", b"12345 /*")
    assert selected(again, "call")[0]["id"] == call["id"]


@pytest.mark.parametrize(
    "statement",
    [
        "mystery();",
        "auto f = [](int x){ return x + 1; };",
        "obj.member = 1;",
        "int a = 1, b = 2;",
        "int x{1};",
        "volatile int x = 1;",
        "for (int i = 0; i < 2; ++i) { tail(); }",
        "return;",
        "auto p = new int(3);",
        "if constexpr (true) { tail(); }",
        "auto f = thing<int>();",
        "goto end; end: tail();",
    ],
)
def test_uncertain_construct_is_opaque_not_converted(statement):
    raw = ("void step() { " + statement + " }").encode()
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    assert graph.export_source() == raw
    opaque = selected(graph, "opaque")
    assert opaque
    assert all(n["ports"] == [] and n["editSlots"] == [] for n in opaque)
    assert graph.to_dict()["projection"] == "partial"


def test_macros_and_templates_are_not_resolved_even_with_matching_binding():
    raw = b"#define tail() hidden()\ntemplate<class T> void templ(T x) { tail(); }\nvoid step(){ tail(); }"
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    assert not selected(graph, "call")
    assert graph.export_source() == raw
    template = parse_source(raw, entries=["templ"], bindings=BINDINGS)
    assert any(d["code"] == "entry-selection" for d in template.to_dict()["diagnostics"])


def test_no_implicit_entry_binding_or_macro_preprocessing():
    raw = b"void step(){ tail(); } void other_step(){ tail(); }"
    none = parse_source(raw, entries=[])
    assert not selected(none)
    graph = parse_source(raw, entries=["step"])
    assert len(selected(graph, "entry")) == 1
    assert not selected(graph, "call")
    assert graph.export_source() == raw
    hidden = parse_source(b"#if BUILD\nvoid step(){tail();}\n#endif", entries=["step"])
    assert any(d["code"] == "entry-selection" for d in hidden.to_dict()["diagnostics"])


def test_execution_and_data_edges_if_branches_and_explicit_event():
    raw = b"void step(int seed){ int x = seed; x = x + 2; if (x > 0) { first(x); } else { second(x); } tail(); }"
    graph = parse_source(
        raw,
        entries=["step"],
        bindings=BINDINGS,
        event_bindings={"step": "test-only:explicit-caller"},
    )
    document = graph.to_dict()
    assert not document["diagnostics"]
    validate_graph(document)
    assert {e["kind"] for e in document["edges"]} == {"data", "execution"}
    entry = selected(graph, "entry")[0]
    assert {p["kind"] for p in entry["ports"]} == {"data", "execution", "event"}
    assert "payloadCppType" not in entry["ports"][0]  # No invented event payload.
    calls = {n["binding"]["callee"]: n for n in selected(graph, "call")}
    tail_in = [e for e in document["edges"] if e["to"]["nodeId"] == calls["tail"]["id"]]
    assert {e["from"]["nodeId"] for e in tail_in} == {calls["first"]["id"], calls["second"]["id"]}
    assert not any(
        e["from"]["nodeId"] == calls["first"]["id"] and e["to"]["nodeId"] == calls["second"]["id"]
        for e in document["edges"]
    )


def test_assignment_invalidates_branch_join_instead_of_inventing_phi():
    raw = b"void step(){ int x = 1; if (x > 0) { x = 2; } first(x); }"
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    assert selected(graph, "assignment")
    assert not selected(graph, "call")
    assert selected(graph, "opaque")[-1]["reason"].startswith("Unsupported")


def test_opaque_is_execution_barrier_and_invalidates_values():
    raw = b"void step(){ int x = 1; unknown(); first(x); tail(); }"
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    calls = selected(graph, "call")
    assert [n["binding"]["callee"] for n in calls] == ["tail"]
    assert not any(e["to"]["nodeId"] == calls[0]["id"] for e in graph.to_dict()["edges"])


@pytest.mark.parametrize(
    "statement",
    [
        "const int x = 1; x = 2;",
        "int x = 1; x += 2;",
        "double x = 1;",
        "auto x = first(1);",
        "first(1.0);",
        "first(read());",
        "int x = 2147483648;",
        "int x = 01;",
    ],
)
def test_unproven_type_conversion_and_nested_effects_not_claimed(statement):
    graph = parse_source(
        ("void step(){ " + statement + " }").encode(), entries=["step"], bindings=BINDINGS
    )
    assert selected(graph, "opaque")


@pytest.mark.parametrize(
    "raw", [b"void step( {", b"void step(){ int x = ; }", b"void step(){ int x = 1 }"]
)
def test_invalid_cpp_has_diagnostic_and_never_editable(raw):
    graph = parse_source(raw, entries=["step"])
    assert graph.export_source() == raw
    assert any(
        d["code"] == "invalid-cpp" and d["severity"] == "error"
        for d in graph.to_dict()["diagnostics"]
    )
    with pytest.raises(GraphError, match="syntax/selection"):
        edit(graph, [])


def test_stale_source_hash_or_bytes_rejected_without_mutation():
    graph = parse_source(b"void step(){ int x = 1; }", entries=["step"])
    before = graph.to_dict()
    changes = [token_edit(graph, selected(graph, "declaration")[0], "literal", "2")]
    with pytest.raises(GraphError, match="Stale"):
        graph.apply_edits(changes, expected_source_hash="0" * 64, current_source=graph.source_bytes)
    with pytest.raises(GraphError, match="Stale"):
        graph.apply_edits(
            changes,
            expected_source_hash=graph.source_hash,
            current_source=graph.source_bytes + b"\n",
        )
    assert graph.to_dict() == before
    assert graph.export_source() == b"void step(){ int x = 1; }"


def test_overlapping_patches_and_injection_rejected():
    graph = parse_source(
        b"void step(){ int x = 1; first(x); }", entries=["step"], bindings=BINDINGS
    )
    change = token_edit(graph, selected(graph, "declaration")[0], "literal", "2")
    with pytest.raises(GraphError, match="Overlapping"):
        edit(graph, [change, change])
    with pytest.raises(GraphError, match="single identifier"):
        edit(graph, [token_edit(graph, selected(graph, "call")[0], "call", "tail);hidden(")])
    with pytest.raises(GraphError, match="numeric/bool"):
        edit(graph, [{**change, "replacement": "2; hidden()"}])


@pytest.mark.parametrize("replacement", ["2.0", "true", "2147483648", "01"])
def test_type_or_catalog_changes_rejected(replacement):
    graph = parse_source(b"void step(){ int x = 1; }", entries=["step"])
    with pytest.raises(GraphError):
        edit(graph, [token_edit(graph, selected(graph, "declaration")[0], "literal", replacement)])


def test_unbound_call_replacement_rejected():
    graph = parse_source(b"void step(){ tail(); }", entries=["step"], bindings=BINDINGS)
    with pytest.raises(GraphError, match="structure"):
        edit(graph, [token_edit(graph, selected(graph, "call")[0], "call", "not_bound")])


def test_duplicate_statements_have_distinct_ids_after_edit():
    graph = parse_source(b"void step(){ tail(); tail(); }", entries=["step"], bindings=BINDINGS)
    calls = selected(graph, "call")
    assert calls[0]["id"] != calls[1]["id"]
    changed = edit(graph, [token_edit(graph, calls[0], "call", "tail")])
    assert [n["id"] for n in selected(changed, "call")] == [n["id"] for n in calls]


@pytest.mark.parametrize("defect", ["dangling", "cycle", "kind", "type", "duplicate", "driver"])
def test_invalid_wires_report_error_not_rewrite(defect):
    graph = parse_source(b"void step(){ int x = 1; int y = x; y = y + 1; }", entries=["step"])
    document = graph.to_dict()
    if defect == "dangling":
        document["edges"][0]["to"]["nodeId"] = "missing"
    elif defect == "cycle":
        declarations = selected(graph, "declaration")
        assignment = selected(graph, "assignment")[0]
        document["edges"].append(
            {
                "id": "cycle",
                "kind": "execution",
                "from": {"nodeId": assignment["id"], "portId": "next"},
                "to": {"nodeId": declarations[0]["id"], "portId": "in"},
            }
        )
    elif defect == "kind":
        document["edges"][0]["kind"] = "data"
    elif defect == "type":
        for node in document["nodes"]:
            for port in node["ports"]:
                if port["kind"] == "data" and port["direction"] == "in":
                    port["cppType"] = "double"
    elif defect == "duplicate":
        document["edges"].append(copy.deepcopy(document["edges"][0]))
    else:
        extra = copy.deepcopy(next(e for e in document["edges"] if e["kind"] == "data"))
        extra["id"] = "second-driver"
        document["edges"].append(extra)
    with pytest.raises(GraphError):
        validate_graph(document)
    assert graph.export_source() == b"void step(){ int x = 1; int y = x; y = y + 1; }"
    validate_graph(graph.to_dict())


def test_sdk_calls_require_explicit_bindings_and_preserve_full_datapoint():
    # These spellings/signatures exist in the actual SDK. Nothing is executed.
    bindings = {
        f"context().services().systemMetrics().{name}": {
            "operation": f"tabos::ISystemMetrics::{name}",
            "returnType": "tabos::DataPoint<float>",
            "parameterTypes": [],
        }
        for name in ("radioTemp", "cpuTemp")
    }
    raw = b"void Monitor::onUpdate(){ const auto sample = context().services().systemMetrics().radioTemp(); custom(sample); }"
    graph = parse_source(raw, entries=["Monitor::onUpdate"], bindings=bindings)
    node = selected(graph, "declaration")[0]
    assert node["cppType"] == "tabos::DataPoint<float>"
    assert node["typeEvidence"] == "explicit-binding"
    changed = edit(graph, [token_edit(graph, node, "call", "cpuTemp")])
    assert changed.export_source() == raw.replace(b"radioTemp", b"cpuTemp")
    assert selected(changed, "opaque")
    unbound = parse_source(raw, entries=["Monitor::onUpdate"])
    assert not selected(unbound, "declaration")


def test_ambiguous_entry_and_bad_bindings_diagnostic():
    graph = parse_source(b"void step(){} void step(int x){}", entries=["step"])
    assert any(d["code"] == "entry-selection" for d in graph.to_dict()["diagnostics"])
    with pytest.raises(GraphError, match="Binding requires"):
        parse_source(b"", entries=[], bindings={"tail": {"returnType": "void"}})
    with pytest.raises(GraphError, match="Event bindings"):
        parse_source(b"", entries=[], event_bindings={"step": "imagined"})


@pytest.mark.parametrize(
    "raw",
    [
        b"void step(int tail){ tail(); }",
        b"void step(){ int tail = 1; unknown(); tail(); }",
        b"void step(){ int x = 0, tail = 1; tail(); }",
        b"void step(){ auto [tail, x] = pair(); tail(); }",
        b"void step(){ auto tail = []{}; tail(); }",
        b"#define true false\nvoid step(){ if (true) { tail(); } }",
    ],
)
def test_local_shadow_and_known_keyword_macro_never_claim_bound_call(raw):
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    assert not selected(graph, "call")
    assert selected(graph, "opaque")


@pytest.mark.parametrize("return_type", ["int&", "const int", "auto", "decltype(auto)"])
def test_unresolved_auto_deduction_is_opaque(return_type):
    graph = parse_source(
        b"void step(){ auto value = read(); }",
        entries=["step"],
        bindings={"read": binding("read", result=return_type)},
    )
    assert not selected(graph, "declaration")
    assert selected(graph, "opaque")


def test_json_api_parse_edit_and_restore_stable_ids():
    raw = "// pouze test: žluťoučký\r\nvoid step(){ int x = 1; first(x); }".encode()
    request = {
        "operation": "parse",
        "sourceBase64": base64.b64encode(raw).decode(),
        "entries": ["step"],
        "bindings": BINDINGS,
    }
    parsed = process_request(json.loads(json.dumps(request)))
    assert parsed["ok"] is True
    assert base64.b64decode(parsed["sourceBase64"]) == raw
    snapshot = parsed["graph"]
    restored = restore_graph(raw, snapshot, entries=["step"], bindings=BINDINGS)
    assert restored.to_dict() == snapshot
    call = selected(restored, "call")[0]
    edited = process_request(
        {
            **request,
            "operation": "edit",
            "graph": snapshot,
            "expectedSourceHash": snapshot["sourceHash"],
            "edits": [token_edit(restored, call, "call", "second")],
        }
    )
    assert edited["ok"] is True, edited
    assert base64.b64decode(edited["sourceBase64"]) == raw.replace(b"first(x)", b"second(x)")
    assert [n["id"] for n in edited["graph"]["nodes"]] == [n["id"] for n in snapshot["nodes"]]
    assert process_request({"operation": "validate", "graph": edited["graph"]}) == {"ok": True}
    # Same original snapshot cannot authorize overwriting the changed source.
    stale = process_request(
        {
            **request,
            "operation": "edit",
            "graph": snapshot,
            "sourceBase64": edited["sourceBase64"],
            "expectedSourceHash": snapshot["sourceHash"],
            "edits": [],
        }
    )
    assert stale["ok"] is False and "Stale" in stale["diagnostics"][0]["message"]


@pytest.mark.parametrize("mutation", ["span", "slots", "binding", "edges", "diagnostic", "node_id"])
def test_untrusted_json_snapshot_cannot_authorize_unrelated_patch(mutation):
    graph = parse_source(
        b"void step(){ int x = 1; first(x); }", entries=["step"], bindings=BINDINGS
    )
    snapshot = graph.to_dict()
    node = next(n for n in snapshot["nodes"] if n["kind"] == "declaration")
    if mutation == "span":
        node["sourceSpan"]["startByte"] += 1
    elif mutation == "slots":
        node["editSlots"][0]["sourceSpan"]["startByte"] = 0
    elif mutation == "binding":
        next(n for n in snapshot["nodes"] if n["kind"] == "call")["binding"]["operation"] = (
            "invented"
        )
    elif mutation == "edges":
        snapshot["edges"].pop()
    elif mutation == "diagnostic":
        snapshot["diagnostics"].append({"code": "invented", "severity": "warning"})
    else:
        node["id"] = snapshot["nodes"][0]["id"]
    with pytest.raises(GraphError):
        restore_graph(graph.source_bytes, snapshot, entries=["step"], bindings=BINDINGS)


@pytest.mark.parametrize(
    "api_request",
    [
        None,
        {},
        {"operation": "shell"},
        {"operation": "parse", "sourceBase64": "?invalid", "entries": []},
        {"operation": "parse", "sourceBase64": "", "entries": None},
        {"operation": "validate", "graph": {"schemaVersion": 1, "nodes": None}},
    ],
)
def test_bad_json_api_request_returns_diagnostic_not_exception(api_request):
    response = process_request(api_request)
    assert response["ok"] is False
    assert response["diagnostics"][0]["code"] == "request-error"


def test_parser_never_invokes_compiler_or_executes_fixture(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Parser attempted subprocess execution")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    raw = b'void step(){ system("DO_NOT_EXECUTE"); }'
    graph = parse_source(raw, entries=["step"])
    assert graph.export_source() == raw
    assert selected(graph, "opaque")


@pytest.mark.parametrize("condition", ["true", "false", "!false", "(1 < 2)", "1 + 2 > 0"])
def test_restricted_if_conditions(condition):
    raw = ("void step(){ if (" + condition + ") { tail(); } }").encode()
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    assert selected(graph, "if")
    assert not selected(graph, "opaque")


def test_real_compiler_behavior_call_literal_if_sequence_and_unknown_preservation(tmp_path):
    compiler = shutil.which(os.environ.get("TABOS_GRAPH_CXX", "g++"))
    if not compiler:
        pytest.skip("No approved lightweight C++ compiler; no runtime proof")
    # All functions below are TEST-ONLY counters, not simulated SDK/hardware.
    raw = b"""#include <cstdio>
static int trace = 0;
void first(int x) { trace = trace * 10 + x; }
void second(int x) { trace = trace * 10 + x + 1; }
void tail() { trace = trace * 10 + 9; }
template<class T> T opaque_template(T x) { return x; }
void step() {
  int x = 1; // keep exactly
  if (x > 0) { first(x); } else { second(x); }
  tail();
  auto opaque = []{ return opaque_template(7); }; // opaque, but actual C++ executes
  trace = trace * 10 + opaque();
}
int main() { step(); std::printf("%d\\n", trace); }
"""
    graph = parse_source(raw, entries=["step"], bindings=BINDINGS)
    first = next(n for n in selected(graph, "call") if n["binding"]["callee"] == "first")
    changed = edit(
        graph,
        [
            token_edit(graph, selected(graph, "declaration")[0], "literal", "2"),
            token_edit(graph, first, "call", "second"),
        ],
    )
    false_branch = edit(
        graph, [token_edit(graph, selected(graph, "declaration")[0], "literal", "0")]
    )
    for index, (source, expected) in enumerate(
        [(raw, "197"), (changed.export_source(), "397"), (false_branch.export_source(), "197")]
    ):
        cpp = tmp_path / f"test_only_graph_{index}.cpp"
        exe = tmp_path / f"test_only_graph_{index}.exe"
        cpp.write_bytes(source)
        compiled = subprocess.run(
            [compiler, "-std=c++17", "-O0", "-Wall", "-Wextra", str(cpp), "-o", str(exe)],
            capture_output=True,
            text=True,
            timeout=40,
            cwd=tmp_path,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=5, cwd=tmp_path)
        assert run.returncode == 0, run.stderr
        assert run.stdout.strip() == expected


CONSTRUCTION_SOURCE = b"void step(){ int x = 1; x = x * 10 + 2; x = x * 10 + 3; first(x); }"


def construction_graph(source=CONSTRUCTION_SOURCE):
    return parse_source(source, entries=["step"], bindings=BINDINGS)


def construct(graph, kind, **fields):
    return graph.apply_construction(
        {"kind": kind, "regionId": graph.construction_regions()[0]["id"], **fields},
        expected_source_hash=graph.source_hash,
        current_source=graph.source_bytes,
    )


def test_construction_regions_are_proven_runs_and_fences():
    graph = construction_graph()
    region = graph.construction_regions()[0]
    assert len(region["nodeIds"]) == 3
    assert set(region["allowedOperations"]) == {"insertStatement", "deleteNode", "setSequence"}
    assert selected(graph, "call")[0]["id"] not in region["nodeIds"]
    with pytest.raises(GraphError, match="outside"):
        construct(graph, "deleteNode", nodeId=selected(graph, "call")[0]["id"])
    mixed = construction_graph(b"void step(){ int x=1; unknown(); int y=2; }")
    assert mixed.construction_regions() == []
    broken = construction_graph(b"void step(){ int x=; }")
    assert broken.construction_regions() == []
    fenced = construction_graph(b"void step(){ int x=1; if (x>0) { tail(); } int y=2; }")
    assert len(fenced.construction_regions()) == 2
    assert all(len(r["nodeIds"]) == 1 for r in fenced.construction_regions())


@pytest.mark.parametrize(
    "raw",
    [b"void step(){}", b"void step(){\r\n}\r\n", b"\xef\xbb\xbfvoid step(){ /* preserve */ }\r\n"],
)
def test_insert_into_empty_body_and_keep_surviving_ids(raw):
    graph = construction_graph(raw)
    old_ids = {n["id"] for n in graph.to_dict()["nodes"]}
    changed = construct(graph, "insertStatement", beforeNodeId=None, cpp="int count = 7;")
    assert len(selected(changed, "declaration")) == 1
    assert old_ids < {n["id"] for n in changed.to_dict()["nodes"]}
    assert graph.export_source() == raw
    assert b"int count = 7;" in changed.export_source()
    assert changed.export_source().startswith(b"\xef\xbb\xbf") == raw.startswith(b"\xef\xbb\xbf")
    if b"\r\n" in raw:
        assert b"\n" not in changed.export_source().replace(b"\r\n", b"")
    if b"preserve" in raw:
        assert b"/* preserve */" in changed.export_source()


def test_insert_assignment_delete_and_data_edge_reaching_definition():
    graph = construction_graph()
    changed = construct(graph, "insertStatement", beforeNodeId=None, cpp="x = x * 10 + 4;")
    assert len(selected(changed, "assignment")) == 3
    assert [n["id"] for n in selected(changed, "assignment")[:2]] == [
        n["id"] for n in selected(graph, "assignment")
    ]
    last_assignment = selected(changed, "assignment")[-1]
    call = selected(changed, "call")[0]
    assert any(
        e["kind"] == "data"
        and e["from"]["nodeId"] == last_assignment["id"]
        and e["to"]["nodeId"] == call["id"]
        for e in changed.to_dict()["edges"]
    )
    deleted = construct(changed, "deleteNode", nodeId=last_assignment["id"])
    assert b"x = x * 10 + 4;" not in deleted.export_source()
    assert len(selected(deleted, "assignment")) == 2
    before = graph.to_dict()
    with pytest.raises(GraphError, match=r"opaque|unresolved|preserve"):
        construct(graph, "deleteNode", nodeId=selected(graph, "declaration")[0]["id"])
    assert graph.to_dict() == before


def test_insert_before_member_and_reject_shadowing_even_unknown_parameter():
    graph = construction_graph()
    target = selected(graph, "assignment")[0]
    changed = construct(graph, "insertStatement", beforeNodeId=target["id"], cpp="int extra = 8;")
    assert changed.export_source().index(b"int extra") < changed.export_source().index(
        b"x = x * 10 + 2;"
    )
    with pytest.raises(GraphError, match=r"shadows|contract|dependency"):
        construct(graph, "insertStatement", beforeNodeId=None, cpp="int x = 2;")
    unknown_parameter = construction_graph(b"void step(Custom x){}")
    with pytest.raises(GraphError, match="shadows"):
        construct(unknown_parameter, "insertStatement", beforeNodeId=None, cpp="int x = 2;")


def test_insert_cannot_shadow_explicit_binding_receiver():
    graph = parse_source(
        b"void step(){ int x=1; receiver.read(); }",
        entries=["step"],
        bindings={"receiver.read": binding("read")},
    )
    with pytest.raises(GraphError, match="shadows"):
        construct(graph, "insertStatement", beforeNodeId=None, cpp="int receiver = 3;")


@pytest.mark.parametrize(
    "cpp",
    [
        "int a=1; int b=2;",
        "tail();",
        "int x = read();",
        "auto p = new int(1);",
        "int& y = x;",
        "int x = missing;",
        "#define x 5",
        "} void injected(){",
        "for (;;) {}",
        "if (true) {}",
        "// only a comment",
        "",
        "return;",
    ],
)
def test_insert_rejects_outside_constructor_subset_atomically(cpp):
    graph = construction_graph()
    before = graph.to_dict()
    with pytest.raises(GraphError):
        construct(graph, "insertStatement", beforeNodeId=None, cpp=cpp)
    assert graph.to_dict() == before
    assert graph.export_source() == CONSTRUCTION_SOURCE


def test_set_sequence_preserves_ids_bytes_and_changes_actual_order():
    graph = construction_graph()
    declaration = selected(graph, "declaration")[0]
    a, b = selected(graph, "assignment")
    changed = construct(graph, "setSequence", nodeIds=[declaration["id"], b["id"], a["id"]])
    expected = b"void step(){ int x = 1; x = x * 10 + 3; x = x * 10 + 2; first(x); }"
    assert changed.export_source() == expected
    assert [n["id"] for n in selected(changed, "assignment")] == [b["id"], a["id"]]
    assert selected(changed, "call")[0]["id"] == selected(graph, "call")[0]["id"]
    assert selected(changed, "entry")[0]["id"] == selected(graph, "entry")[0]["id"]
    # Data producers follow the requested order, not the original graph.
    assert any(
        e["kind"] == "data" and e["from"]["nodeId"] == b["id"] and e["to"]["nodeId"] == a["id"]
        for e in changed.to_dict()["edges"]
    )


def test_duplicate_statement_move_keeps_distinct_node_identity():
    graph = construction_graph(b"void step(){ int x=1; x=x+1; x=x+1; first(x); }")
    ids = graph.construction_regions()[0]["nodeIds"]
    changed = construct(graph, "setSequence", nodeIds=[ids[0], ids[2], ids[1]])
    assert changed.export_source() == graph.export_source()
    assert [n["id"] for n in selected(changed, "assignment")] == [ids[2], ids[1]]
    restored = restore_graph(
        changed.source_bytes, changed.to_dict(), entries=["step"], bindings=BINDINGS
    )
    assert restored.to_dict() == changed.to_dict()


@pytest.mark.parametrize("defect", ["missing", "duplicate", "foreign", "use-before-definition"])
def test_rewire_bad_sequence_is_not_silently_sorted(defect):
    graph = construction_graph()
    ids = graph.construction_regions()[0]["nodeIds"]
    order = {
        "missing": ids[:-1],
        "duplicate": [ids[0], ids[1], ids[1]],
        "foreign": [ids[0], ids[1], selected(graph, "call")[0]["id"]],
        "use-before-definition": [ids[1], ids[0], ids[2]],
    }[defect]
    with pytest.raises(GraphError):
        construct(graph, "setSequence", nodeIds=order)
    assert graph.export_source() == CONSTRUCTION_SOURCE


def test_construction_opaque_file_regions_crlf_unicode_comments():
    prefix = "// přesný opaque prefix\r\ntemplate<class T> T keep(T x){return x;}\r\n".encode()
    suffix = b"\r\nauto opaque=[](){return keep(3);}; // exact suffix\r\n"
    body = b"void step(){\r\n int x=1;\r\n x=x+2;\r\n first(x);\r\n}"
    graph = construction_graph(prefix + body + suffix)
    changed = construct(graph, "insertStatement", beforeNodeId=None, cpp="x = x + 3;")
    assert changed.export_source().startswith(prefix)
    assert changed.export_source().endswith(suffix)
    assert b"\n" not in changed.export_source().replace(b"\r\n", b"")
    for old in (n for n in graph.to_dict()["nodes"] if n["kind"] == "opaque"):
        new = next(n for n in changed.to_dict()["nodes"] if n["id"] == old["id"])
        a, b = old["sourceSpan"], new["sourceSpan"]
        assert (
            graph.source_bytes[a["startByte"] : a["endByte"]]
            == changed.source_bytes[b["startByte"] : b["endByte"]]
        )


def test_reorder_comment_ownership_rejected_but_delete_keeps_outside_comment():
    raw = b"void step(){ int x=1; /* outside, do not attach by guess */ x=x+2; first(x); }"
    graph = construction_graph(raw)
    region = graph.construction_regions()[0]
    assert "setSequence" not in region["allowedOperations"]
    with pytest.raises(GraphError, match="comments"):
        construct(graph, "setSequence", nodeIds=region["nodeIds"])
    changed = construct(graph, "deleteNode", nodeId=selected(graph, "assignment")[0]["id"])
    assert changed.export_source() == raw.replace(b"x=x+2;", b"")
    internal = construction_graph(
        b"void step(){ int x=1; x /* A */ =x+1; x /* B */ =x+2; first(x); }"
    )
    ids = internal.construction_regions()[0]["nodeIds"]
    moved = construct(internal, "setSequence", nodeIds=[ids[0], ids[2], ids[1]])
    assert b"x /* B */ =x+2; x /* A */ =x+1;" in moved.export_source()


def test_json_regions_construct_and_stale_rejections():
    graph = construction_graph()
    envelope = {
        "operation": "regions",
        "sourceBase64": base64.b64encode(graph.source_bytes).decode(),
        "entries": ["step"],
        "bindings": BINDINGS,
        "graph": graph.to_dict(),
        "expectedSourceHash": graph.source_hash,
    }
    discovered = process_request(envelope)
    assert discovered["ok"] and discovered["constructionVersion"] == 1
    assert discovered["graph"] == graph.to_dict()
    mutation = {
        "kind": "insertStatement",
        "regionId": discovered["regions"][0]["id"],
        "beforeNodeId": None,
        "cpp": "x = x + 4;",
    }
    response = process_request({**envelope, "operation": "construct", "mutation": mutation})
    assert response["ok"], response
    assert len(response["changeSet"]["insertedNodeIds"]) == 1
    assert response["changeSet"]["removedNodeIds"] == []
    stale = process_request(
        {
            **envelope,
            "operation": "construct",
            "mutation": mutation,
            "sourceBase64": response["sourceBase64"],
        }
    )
    assert not stale["ok"] and "Stale" in stale["diagnostics"][0]["message"]
    bad_region = process_request(
        {**envelope, "operation": "construct", "mutation": {**mutation, "regionId": "spoofed"}}
    )
    assert not bad_region["ok"]
    extra = process_request(
        {**envelope, "operation": "construct", "mutation": mutation, "edits": []}
    )
    assert not extra["ok"]
    old_expected = process_request({**envelope, "expectedSourceHash": "0" * 64})
    assert not old_expected["ok"]


def test_real_compiler_construction_insert_delete_and_rewire_trace(tmp_path):
    compiler = shutil.which(os.environ.get("TABOS_GRAPH_CXX", "g++"))
    if not compiler:
        pytest.skip("No approved lightweight C++ compiler; no runtime proof")
    # Explicit TEST-ONLY observation function, never a simulated SDK service.
    prefix = b"#include <cstdio>\nint observed=0; void first(int x){observed=x;}\n"
    suffix = b'\nint main(){step(); std::printf("%d\\n",observed);}\n'
    graph = construction_graph(prefix + CONSTRUCTION_SOURCE + suffix)
    ids = graph.construction_regions()[0]["nodeIds"]
    reordered = construct(graph, "setSequence", nodeIds=[ids[0], ids[2], ids[1]])
    inserted = construct(graph, "insertStatement", beforeNodeId=None, cpp="x = x * 10 + 4;")
    deleted = construct(graph, "deleteNode", nodeId=ids[2])
    for index, (fixture, expected) in enumerate(
        [(graph, "123"), (reordered, "132"), (inserted, "1234"), (deleted, "12")]
    ):
        cpp, exe = tmp_path / f"construction_{index}.cpp", tmp_path / f"construction_{index}.exe"
        cpp.write_bytes(fixture.export_source())
        compiled = subprocess.run(
            [compiler, "-std=c++17", "-O0", "-Wall", "-Wextra", str(cpp), "-o", str(exe)],
            capture_output=True,
            text=True,
            timeout=40,
            cwd=tmp_path,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=5, cwd=tmp_path)
        assert run.returncode == 0 and run.stdout.strip() == expected, run.stdout + run.stderr
