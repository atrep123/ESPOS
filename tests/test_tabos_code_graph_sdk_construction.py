"""Opt-in, source-backed SDK construction; authored TEST-ONLY fixtures only.

No firmware/LVGL builds, device/network access, or untrusted C++ compilation.
The runtime fixture may link an explicitly supplied EXISTING LVGL library.
"""

import base64
import copy
import os
import pathlib
import shutil
import subprocess

import pytest

from tools.tabos_code_graph import (
    GraphError,
    parse_source,
    process_request,
    restore_graph,
)
from tools.tabos_sdk_node_catalog import catalog, cpp_templates

PROFILE = "tabos-sdk-minimal-1"
PREFIX = "espos_tabos_nodes::"
BINDINGS = {
    PREFIX + "bind_click": {
        "operation": "espos.tabos.lvgl.click.bind.v1",
        "returnType": "lv_event_dsc_t*",
        "parameterTypes": ["lv_obj_t*", "lv_event_cb_t", "void*"],
    },
    PREFIX + "set_label_text": {
        "operation": "espos.tabos.lvgl.label.text.v1",
        "returnType": "tabos::Status",
        "parameterTypes": ["lv_obj_t*", "const char*"],
    },
    PREFIX + "sample_cpu_temperature": {
        "operation": "espos.tabos.metrics.cpu_temp.sample.v1",
        "returnType": "tabos::DataPoint<float>",
        "parameterTypes": ["tabos::ISystemMetrics&"],
    },
}
EMPTY = b"void step(lv_obj_t* label, tabos::ISystemMetrics& metrics) {\r\n}\r\n"
SAMPLE = "auto sample = espos_tabos_nodes::sample_cpu_temperature(metrics);"
ERROR_BRANCH = """if (sample.state == tabos::DataState::Error) {
    auto error_status = espos_tabos_nodes::set_label_text(label, "Error");
} else {
    if (sample.state == tabos::DataState::Unavailable) {
        auto unavailable_status = espos_tabos_nodes::set_label_text(label, "Unavailable");
    } else {
        auto other_status = espos_tabos_nodes::set_label_text(label, "State retained");
    }
}"""


def parsed(source=EMPTY, *, bindings=None, entries=("step",)):
    return parse_source(
        source,
        entries=list(entries),
        bindings=BINDINGS if bindings is None else bindings,
        sdk_profile=PROFILE,
    )


def selected(graph):
    return [n for n in graph.to_dict()["nodes"] if n.get("scope") != "outside-selection"]


def insert(graph, cpp, *, before=None, function=None):
    regions = graph.sdk_construction_regions()
    if function is not None:
        entry_id = next(n["id"] for n in selected(graph) if n.get("function") == function)
        regions = [r for r in regions if r["entryNodeId"] == entry_id]
    region = regions[0]
    return graph.apply_sdk_construction(
        {
            "kind": "insertSdkStatement",
            "regionId": region["id"],
            "beforeNodeId": before,
            "cpp": cpp,
        },
        expected_source_hash=graph.source_hash,
        current_source=graph.source_bytes,
    )


def opaque_bytes(graph):
    return {
        n["id"]: graph.source_bytes[n["sourceSpan"]["startByte"] : n["sourceSpan"]["endByte"]]
        for n in graph.to_dict()["nodes"]
        if n["kind"] == "opaque"
    }


def test_profile_signatures_match_actual_catalog_without_autobinding():
    nodes = {n["id"]: n for n in catalog()["nodes"]}
    for callee, binding in BINDINGS.items():
        node = nodes[binding["operation"]]
        assert callee == PREFIX + node["functions"][0]
        assert binding["parameterTypes"] == [
            p["cpp_type"] for p in node["bindings"] if p["direction"] == "input"
        ]
        assert binding["returnType"] == next(
            p["cpp_type"] for p in node["bindings"] if p["direction"] == "output"
        )
    source = (
        b'void step(lv_obj_t* label){auto status=espos_tabos_nodes::set_label_text(label,"Click");}'
    )
    assert any(n["kind"] == "opaque" for n in selected(parsed(source, bindings={})))
    legacy = parse_source(source, entries=["step"], bindings=BINDINGS)
    assert any(n["kind"] == "opaque" for n in selected(legacy))


def test_insert_real_typed_metric_and_error_unavailable_branch():
    baseline = parsed()
    sampled = insert(baseline, SAMPLE)
    graph = insert(sampled, ERROR_BRANCH)
    assert not any(n["kind"] == "opaque" for n in selected(graph))
    sample = next(n for n in selected(graph) if n.get("variable") == "sample")
    assert sample["cppType"] == "tabos::DataPoint<float>"
    assert len([n for n in selected(graph) if n["kind"] == "if"]) == 2
    assert sample["id"] == next(n["id"] for n in selected(sampled) if n.get("variable") == "sample")
    assert {e["kind"] for e in graph.to_dict()["edges"]} == {"execution", "data"}
    assert SAMPLE.encode() in graph.source_bytes
    assert b"sample.value" not in graph.source_bytes
    assert all(n["kind"] != "assignment" for n in selected(graph))
    assert baseline.source_bytes == EMPTY


def test_insert_click_uses_explicit_callback_parameter_no_event_magic():
    raw = b"void step(lv_obj_t* button, lv_event_cb_t callback, void* context) {}"
    graph = insert(
        parsed(raw), "auto descriptor = espos_tabos_nodes::bind_click(button, callback, context);"
    )
    node = next(n for n in selected(graph) if n.get("variable") == "descriptor")
    assert node["cppType"] == "lv_event_dsc_t*"
    assert {p["cppType"] for p in node["ports"] if p["kind"] == "data"} == {
        "lv_obj_t*",
        "lv_event_cb_t",
        "void*",
        "lv_event_dsc_t*",
    }
    assert all(e["kind"] != "event" for e in graph.to_dict()["edges"])


def test_known_label_literal_edit_preserves_utf8_crlf_opaque_and_ids():
    prefix = "// měřič 🚦\r\ntemplate<class T> T keep(T x){return x;}\r\n".encode()
    suffix = "\r\nauto opaque=[](){return keep(4);}; // beze změn\r\n".encode()
    raw = b"\xef\xbb\xbf" + prefix + b"void step(lv_obj_t* label) {\r\n}\r\n" + suffix
    old = parsed(raw)
    graph = insert(old, 'auto status = espos_tabos_nodes::set_label_text(label, "Kliknutí");')
    assert opaque_bytes(graph) == opaque_bytes(old)
    node = next(n for n in selected(graph) if n.get("variable") == "status")
    slot = next(s for s in node["editSlots"] if s["kind"] == "string")
    changed = graph.apply_edits(
        [{"nodeId": node["id"], "slotId": slot["id"], "replacement": '"Změna 🚦"'}],
        expected_source_hash=graph.source_hash,
        current_source=graph.source_bytes,
    )
    assert changed.source_bytes == graph.source_bytes.replace(
        '"Kliknutí"'.encode(), '"Změna 🚦"'.encode()
    )
    assert opaque_bytes(changed) == opaque_bytes(old)
    assert [n["id"] for n in changed.to_dict()["nodes"]] == [
        n["id"] for n in graph.to_dict()["nodes"]
    ]


@pytest.mark.parametrize(
    "cpp",
    [
        "mystery();",
        "auto sample = metrics.cpuTemp();",
        "sample.state = tabos::DataState::Live;",
        "auto number = sample.value;",
        'auto text = R"(raw)";',
        'auto text = u8"text";',
        'auto status=espos_tabos_nodes::set_label_text(label, "ok"); mystery();',
        "auto status=espos_tabos_nodes::set_label_text(label, nullptr);",
        "auto status=espos_tabos_nodes::set_label_text(label, factory());",
        "auto sample=espos_tabos_nodes::sample_cpu_temperature(metrics);",
        "if (sample.state == 5) { auto x=1; }",
        "for (;;) {}",
        "return;",
        'auto label=espos_tabos_nodes::set_label_text(label,"shadow");',
        "int x=1;",
        "if(true){int x=1;}",
    ],
)
def test_unsupported_or_shadowing_insert_rejects_without_source_change(cpp):
    graph = insert(parsed(), SAMPLE)
    before = graph.to_dict(), graph.source_bytes
    with pytest.raises(GraphError):
        insert(graph, cpp)
    assert (graph.to_dict(), graph.source_bytes) == before


@pytest.mark.parametrize(
    "body", ["mystery();", "auto x=[](){return 3;};", "sample.value=0;", "if (true) { mystery(); }"]
)
def test_unknown_selected_code_has_no_sdk_region(body):
    graph = parsed(("void step(lv_obj_t* label) {" + body + "}").encode())
    assert graph.sdk_construction_regions() == []
    assert graph.export_source().endswith((body + "}").encode())


@pytest.mark.parametrize(
    "parameter",
    [
        "Alias label",
        "lv_obj_t** label",
        "lv_obj_t*& label",
        "volatile lv_obj_t* label",
        "const tabos::ISystemMetrics& metrics",
    ],
)
def test_unproved_parameter_types_do_not_authorize_construction(parameter):
    graph = parsed(("void step(" + parameter + ") {}").encode())
    assert graph.sdk_construction_regions() == []


def test_signature_mismatch_and_unreviewed_binding_are_explicit_errors():
    for invalid in (
        {PREFIX + "set_label_text": {**BINDINGS[PREFIX + "set_label_text"], "returnType": "int"}},
        {"mystery": {"operation": "not-reviewed", "returnType": "void", "parameterTypes": []}},
    ):
        with pytest.raises(GraphError):
            parsed(bindings=invalid)


def test_sdk_json_roundtrip_stale_hash_and_ids_fail_atomically():
    graph = parsed()
    request = {
        "operation": "constructSdk",
        "sourceBase64": base64.b64encode(EMPTY).decode(),
        "entries": ["step"],
        "bindings": BINDINGS,
        "sdkProfile": PROFILE,
        "graph": graph.to_dict(),
        "expectedSourceHash": graph.source_hash,
        "mutation": {
            "kind": "insertSdkStatement",
            "regionId": graph.sdk_construction_regions()[0]["id"],
            "beforeNodeId": None,
            "cpp": SAMPLE,
        },
    }
    response = process_request(request)
    assert response["ok"] is True, response
    assert response["sdkConstructionVersion"] == 1
    assert len(response["changeSet"]["insertedNodeIds"]) == 1
    assert response["changeSet"]["removedNodeIds"] == []
    restored = restore_graph(
        base64.b64decode(response["sourceBase64"]),
        response["graph"],
        entries=["step"],
        bindings=BINDINGS,
        sdk_profile=PROFILE,
    )
    assert restored.to_dict() == response["graph"]
    for changed in ("hash", "ids", "profile"):
        stale = copy.deepcopy(request)
        if changed == "hash":
            stale["expectedSourceHash"] = "0" * 64
        elif changed == "ids":
            stale["mutation"]["regionId"] = parsed().sdk_construction_regions()[0]["id"]
        else:
            stale.pop("sdkProfile")
        rejected = process_request(stale)
        assert rejected["ok"] is False
        assert "sourceBase64" not in rejected


@pytest.mark.parametrize(
    "replacement", ['"ok"; mystery(); //', 'u8"text"', 'R"(x)"', '"bad\\0"', '"bad\nline"']
)
def test_string_edits_reject_injection_and_unsupported_literals(replacement):
    graph = insert(
        parsed(b"void step(lv_obj_t* label){}"),
        'auto status=espos_tabos_nodes::set_label_text(label,"old");',
    )
    node = next(n for n in selected(graph) if n.get("variable") == "status")
    slot = next(s for s in node["editSlots"] if s["kind"] == "string")
    with pytest.raises(GraphError):
        graph.apply_edits(
            [{"nodeId": node["id"], "slotId": slot["id"], "replacement": replacement}],
            expected_source_hash=graph.source_hash,
            current_source=graph.source_bytes,
        )


def test_insert_before_preserves_existing_ids_but_refuses_use_before_sample():
    sampled = insert(parsed(), SAMPLE)
    sample = next(n for n in selected(sampled) if n.get("variable") == "sample")
    with pytest.raises(GraphError):
        insert(sampled, ERROR_BRANCH, before=sample["id"])
    inserted = insert(
        sampled,
        'auto status=espos_tabos_nodes::set_label_text(label,"Reading");',
        before=sample["id"],
    )
    assert (
        next(n["id"] for n in selected(inserted) if n.get("variable") == "sample") == sample["id"]
    )
    assert inserted.source_bytes.index(b"Reading") < inserted.source_bytes.index(b"auto sample")
    assert all(
        kind not in inserted.sdk_construction_regions()[0]["allowedOperations"]
        for kind in ("deleteNode", "setSequence")
    )


@pytest.mark.parametrize(
    "cpp",
    [
        'auto result=espos_tabos_nodes::set_label_text(metrics,"wrong");',
        "auto result=espos_tabos_nodes::bind_click(label,label,label);",
        'if(true){auto same=espos_tabos_nodes::set_label_text(label,"a");'
        'auto same=espos_tabos_nodes::set_label_text(label,"b");}',
        '#define MAGIC 1\nauto result=espos_tabos_nodes::set_label_text(label,"directive");',
        '} void injected(){auto result=espos_tabos_nodes::set_label_text(label,"escape");} void tail(){',
    ],
)
def test_sdk_construct_rejects_type_scope_and_macro_escapes(cpp):
    graph = parsed()
    with pytest.raises(GraphError):
        insert(graph, cpp)
    assert graph.source_bytes == EMPTY


def test_sdk_parser_and_constructor_never_spawn_processes(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SDK graph core attempted execution")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    graph = sdk_fixture_graph()
    assert not graph.to_dict()["diagnostics"]


def test_sdk_regions_api_and_tampered_type_binding_do_not_authorize_edits():
    graph = parsed()
    request = {
        "operation": "sdkRegions",
        "sourceBase64": base64.b64encode(EMPTY).decode(),
        "entries": ["step"],
        "bindings": BINDINGS,
        "sdkProfile": PROFILE,
        "graph": graph.to_dict(),
        "expectedSourceHash": graph.source_hash,
    }
    response = process_request(request)
    assert response["ok"] and response["sdkRegions"] == graph.sdk_construction_regions()
    request["graph"] = copy.deepcopy(request["graph"])
    request["graph"]["nodes"][0]["ports"][0]["cppType"] = "int"
    rejected = process_request(request)
    assert not rejected["ok"] and "sourceBase64" not in rejected


def test_sdk_unicode_parameters_and_declaration_shadow_guard():
    graph = parsed("void step(lv_obj_t* štítek, tabos::ISystemMetrics& měřič) {}".encode())
    changed = insert(graph, "auto vzorek=espos_tabos_nodes::sample_cpu_temperature(měřič);")
    assert (
        next(n for n in selected(changed) if n.get("variable") == "vzorek")["cppType"]
        == "tabos::DataPoint<float>"
    )
    with pytest.raises(GraphError):
        insert(changed, 'auto štítek=espos_tabos_nodes::set_label_text(štítek,"shadow");')


def test_shadowed_sdk_enum_namespace_is_not_inferred_as_real_state():
    graph = parsed(b"void step(tabos::ISystemMetrics& metrics, lv_obj_t* label, int tabos) {}")
    graph = insert(graph, SAMPLE)
    with pytest.raises(GraphError):
        insert(graph, ERROR_BRANCH)


CPP_BODIES = b"""// TEST-ONLY native SDK/LVGL fixture, no device backend.
void install(lv_obj_t* button, lv_event_cb_t callback, void* context) {}
void paint(lv_obj_t* label) {}
void refresh(lv_obj_t* label, tabos::ISystemMetrics& metrics) {}
// OPAQUE adapter: explicit caller-owned lifetime; never converted by graph.
struct TestOnlyUi {lv_obj_t* label; unsigned clicks=0;};
void test_only_callback(lv_event_t* event) {
    auto* ui=static_cast<TestOnlyUi*>(lv_event_get_user_data(event));
    assert(ui && lv_event_get_code(event)==LV_EVENT_CLICKED);
    ++ui->clicks;
    paint(ui->label);
}
"""


def sdk_fixture_graph():
    graph = parsed(CPP_BODIES, entries=("install", "paint", "refresh"))
    graph = insert(
        graph,
        "auto descriptor=espos_tabos_nodes::bind_click(button,callback,context);",
        function="install",
    )
    graph = insert(
        graph, 'auto status=espos_tabos_nodes::set_label_text(label,"Clicked");', function="paint"
    )
    graph = insert(graph, SAMPLE, function="refresh")
    cases = []
    for state in ("Error", "Unavailable", "Live", "Cached", "Estimated", "Mock"):
        cases.append(
            f"if(sample.state==tabos::DataState::{state})"
            f'{{auto status_{state}=espos_tabos_nodes::set_label_text(label,"TEST-ONLY {state}");}}'
        )
    cpp = (
        " else ".join(cases)
        + ' else {auto invalid=espos_tabos_nodes::set_label_text(label,"Unknown state");}'
    )
    return insert(graph, cpp, function="refresh")


CPP_RUNTIME = r"""
// TEST-ONLY metrics double, never a production backend or physical evidence.
struct TestOnlyMetrics final : tabos::ISystemMetrics {
    tabos::DataPoint<float> expected;
    unsigned calls=0;
    tabos::Result<std::vector<TaskInfo>> tasks() override {assert(false); return tabos::Result<std::vector<TaskInfo>>::failure(tabos::Error::Unavailable);}
    tabos::Result<HeapInfo> heapInternal() override {assert(false); return tabos::Result<HeapInfo>::failure(tabos::Error::Unavailable);}
    tabos::Result<HeapInfo> heapPsram() override {assert(false); return tabos::Result<HeapInfo>::failure(tabos::Error::Unavailable);}
    tabos::DataPoint<float> fps() override {assert(false); return {};}
    tabos::DataPoint<uint64_t> uptimeUs() override {assert(false); return {};}
    tabos::DataPoint<float> cpuTemp() override {++calls; return expected;}
    tabos::DataPoint<float> radioTemp() override {assert(false); return {};}
    tabos::DataPoint<float> cpuLoad() override {assert(false); return {};}
    uint32_t droppedEvents() override {assert(false); return 0;}
};
int main() {
    lv_init();
    auto* display=lv_display_create(320,240);
    assert(display);
    auto* button=lv_button_create(lv_screen_active());
    auto* label=lv_label_create(lv_screen_active());
    TestOnlyUi ui{label};
    const auto count=lv_obj_get_event_count(button);
    for(unsigned cycle=0;cycle<20;++cycle) {
        install(button,test_only_callback,&ui);
        assert(lv_obj_get_event_count(button)==count+1);
        assert(lv_obj_send_event(button,LV_EVENT_CLICKED,nullptr)==LV_RESULT_OK);
        assert(ui.clicks==cycle+1);
        assert(std::strcmp(lv_label_get_text(label),EXPECTED_CLICK)==0);
        assert(lv_obj_remove_event_cb_with_user_data(button,test_only_callback,&ui)==1);
        assert(lv_obj_get_event_count(button)==count);
        assert(lv_obj_send_event(button,LV_EVENT_CLICKED,nullptr)==LV_RESULT_OK);
        assert(ui.clicks==cycle+1);
    }
    const auto invalid=espos_tabos_nodes::set_label_text(button,"not a label");
    assert(!invalid.isOk() && invalid.error()==tabos::Error::InvalidArgument);
    const auto missing=espos_tabos_nodes::set_label_text(nullptr,"missing");
    assert(!missing.isOk() && missing.error()==tabos::Error::InvalidArgument);
    assert(!espos_tabos_nodes::bind_click(nullptr,test_only_callback,&ui));
    assert(!espos_tabos_nodes::bind_click(button,nullptr,&ui));
    TestOnlyMetrics metrics;
    const tabos::DataState states[]={tabos::DataState::Live,tabos::DataState::Error,
        tabos::DataState::Unavailable,tabos::DataState::Cached,tabos::DataState::Estimated,tabos::DataState::Mock};
    const char* text[]={"TEST-ONLY Live","TEST-ONLY Error","TEST-ONLY Unavailable",
        "TEST-ONLY Cached","TEST-ONLY Estimated","TEST-ONLY Mock"};
    for(unsigned i=0;i<6;++i) {
        metrics.expected.value=42.5f;
        metrics.expected.state=states[i];
        metrics.expected.timestampMs=1234;
        metrics.expected.provider="test-only:metrics";
        metrics.expected.error=states[i]==tabos::DataState::Error ? tabos::Error::Io : tabos::Error::None;
        const auto prior=metrics.expected;
        refresh(label,metrics);
        assert(metrics.calls==i+1);
        assert(std::strcmp(lv_label_get_text(label),text[i])==0);
        assert(metrics.expected.value==prior.value && metrics.expected.state==prior.state);
        assert(metrics.expected.timestampMs==prior.timestampMs && metrics.expected.error==prior.error);
        assert(std::strcmp(metrics.expected.provider.text(),prior.provider.text())==0);
    }
    std::printf("SDK_TRACE click=%s samples=%u cycles=%u\n",EXPECTED_CLICK,metrics.calls,ui.clicks);
    lv_display_delete(display);
    lv_deinit();
}
"""


@pytest.mark.parametrize("edited", [False, True], ids=["constructed", "literal-edited"])
def test_real_sdk_compile_and_existing_lvgl_runtime(tmp_path, edited):
    core_path, library_path = (
        os.environ.get("TABOS_CORE_ROOT"),
        os.environ.get("TABOS_GRAPH_LVGL_LIBRARY"),
    )
    if not core_path or not library_path:
        pytest.skip("Explicit real SDK + prebuilt LVGL paths required; no runtime proof")
    core, library = pathlib.Path(core_path), pathlib.Path(library_path)
    assert library.is_file(), "No LVGL rebuild is permitted in this test"
    compiler = shutil.which(os.environ.get("TABOS_GRAPH_CXX", "g++"))
    assert compiler, "Approved lightweight compiler required"
    graph = sdk_fixture_graph()
    initial_opaque = opaque_bytes(parsed(CPP_BODIES, entries=("install", "paint", "refresh")))
    # ID comparison belongs to one construction lineage, byte comparison also
    # verifies the independently parsed original manual callback's exact bytes.
    assert list(opaque_bytes(graph).values()) == list(initial_opaque.values())
    expected = "Clicked"
    if edited:
        node = next(n for n in selected(graph) if n.get("variable") == "status")
        slot = next(s for s in node["editSlots"] if s["kind"] == "string")
        before = graph
        graph = graph.apply_edits(
            [{"nodeId": node["id"], "slotId": slot["id"], "replacement": '"Changed"'}],
            expected_source_hash=graph.source_hash,
            current_source=graph.source_bytes,
        )
        assert graph.source_bytes == before.source_bytes.replace(b'"Clicked"', b'"Changed"')
        assert opaque_bytes(graph) == opaque_bytes(before)
        expected = "Changed"
    source = (
        (
            cpp_templates().replace("#pragma once\n", "")
            + "\n#include <cassert>\n#include <cstring>\n#include <cstdio>\n"
            + f'#define EXPECTED_CLICK "{expected}"\n'
        ).encode()
        + graph.source_bytes
        + CPP_RUNTIME.encode()
    )
    cpp, executable = tmp_path / "sdk_graph_fixture.cpp", tmp_path / "sdk_graph_fixture.exe"
    cpp.write_bytes(source)
    sdk = core / "apps/_src/tabos-sdk"
    compiled = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-O0",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wno-unused-variable",
            "-Wno-unused-but-set-variable",
            "-DPLATFORM_BUILD_DESKTOP",
            f"-DLV_CONF_PATH={core.as_posix()}/lv_conf.h",
            "-I",
            str(core / "dependencies/lvgl"),
            "-I",
            str(sdk / "include"),
            str(cpp),
            str(sdk / "src/result.cpp"),
            str(library),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=tmp_path,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    ran = subprocess.run(
        [str(executable)], capture_output=True, text=True, timeout=10, cwd=tmp_path
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    trace = f"SDK_TRACE click={expected} samples=6 cycles=20"
    assert trace in ran.stdout
    print(trace)
