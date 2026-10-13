import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

from tools.tabos_sdk_node_catalog import catalog, cpp_templates, main

ROOT = pathlib.Path(__file__).resolve().parents[1]


# TEST-ONLY service doubles: never exported by the catalog or used as a backend.
CPP_TEST = r"""
#include <cassert>
#include <cstring>
#include <type_traits>
static_assert(std::is_same_v<decltype(&espos_tabos_nodes::bind_click),
    lv_event_dsc_t* (*)(lv_obj_t*, lv_event_cb_t, void*)>);
struct TestOnlyFiles final : tabos::IFileService {
    bool fail = true;
    unsigned calls = 0;
    tabos::Result<std::vector<Entry>> list(const char* p) override {
        ++calls; assert(std::strcmp(p, "tabos/test-only") == 0);
        if(fail) return tabos::Result<std::vector<Entry>>::failure(tabos::Error::Unavailable, "test-only:files");
        Entry e{"TEST_ONLY", false, 7, 123, true};
        return tabos::Result<std::vector<Entry>>::success({e}, "test-only:files");
    }
    tabos::Result<size_t> read(const char* p, uint32_t offset, uint8_t* out, size_t len) override {
        ++calls; assert(std::strcmp(p, "tabos/test-only") == 0 && offset == 9 && len == 4);
        if(fail) return tabos::Result<size_t>::failure(tabos::Error::Io, "test-only:read");
        out[0] = 65; out[1] = 0; // Explicit test-only short binary read.
        return tabos::Result<size_t>::success(2, "test-only:read");
    }
    tabos::Status write(const char*, const uint8_t*, size_t) override { assert(false); return tabos::Status::error(tabos::Error::Unavailable); }
    tabos::Result<size_t> append(const char*, const uint8_t*, size_t, KdyzChybi) override { assert(false); return tabos::Result<size_t>::failure(tabos::Error::Unavailable); }
    tabos::Status remove(const char*) override { assert(false); return tabos::Status::error(tabos::Error::Unavailable); }
    tabos::Result<uint64_t> freeBytes() override { assert(false); return tabos::Result<uint64_t>::failure(tabos::Error::Unavailable); }
    bool sdMounted() override { assert(false); return false; }
};
struct TestOnlyMetrics final : tabos::ISystemMetrics {
    tabos::DataPoint<float> expected;
    unsigned calls = 0;
    tabos::Result<std::vector<TaskInfo>> tasks() override { assert(false); return tabos::Result<std::vector<TaskInfo>>::failure(tabos::Error::Unavailable); }
    tabos::Result<HeapInfo> heapInternal() override { assert(false); return tabos::Result<HeapInfo>::failure(tabos::Error::Unavailable); }
    tabos::Result<HeapInfo> heapPsram() override { assert(false); return tabos::Result<HeapInfo>::failure(tabos::Error::Unavailable); }
    tabos::DataPoint<float> fps() override { assert(false); return {}; }
    tabos::DataPoint<uint64_t> uptimeUs() override { assert(false); return {}; }
    tabos::DataPoint<float> cpuTemp() override { ++calls; return expected; }
    tabos::DataPoint<float> radioTemp() override { assert(false); return {}; }
    tabos::DataPoint<float> cpuLoad() override { assert(false); return {}; }
    uint32_t droppedEvents() override { assert(false); return 0; }
};
int main() {
    using namespace espos_tabos_nodes;
    tabos::diag::g_cteniPoSelhaniHook = [](tabos::Error, const char*) { assert(false); };
    TestOnlyFiles files;
    uint8_t bytes[4] = {99,99,99,99};
    auto listing = list_files(files, "tabos/test-only");
    assert(!listing.ok() && listing.error() == tabos::Error::Unavailable);
    assert(std::strcmp(listing.provider().text(), "test-only:files") == 0);
    auto reading = read_file(files, "tabos/test-only", 9, bytes, 4);
    assert(!reading.ok() && reading.error() == tabos::Error::Io && bytes[0] == 99);
    auto invalid = read_file(files, "tabos/test-only", 9, nullptr, 4);
    assert(!invalid.ok() && invalid.error() == tabos::Error::InvalidArgument && files.calls == 2);
    auto invalid_list = list_files(files, nullptr);
    assert(!invalid_list.ok() && files.calls == 2);
    files.fail = false;
    auto good_list = list_files(files, "tabos/test-only");
    assert(good_list.ok() && good_list.value().size() == 1 && good_list.value()[0].hasModifiedTime);
    assert(good_list.value()[0].modifiedUnixSeconds == 123);
    auto good_read = read_file(files, "tabos/test-only", 9, bytes, 4);
    assert(good_read.ok() && good_read.value() == 2 && bytes[0] == 65 && bytes[1] == 0 && bytes[2] == 99);
    assert(std::strcmp(good_read.provider().text(), "test-only:read") == 0);
    TestOnlyMetrics metrics;
    for(auto state : {tabos::DataState::Live, tabos::DataState::Cached, tabos::DataState::Estimated,
                     tabos::DataState::Mock, tabos::DataState::Unavailable, tabos::DataState::Error}) {
        metrics.expected.value = 42.5f; // TEST-ONLY fixture, not an operational measurement.
        metrics.expected.state = state;
        metrics.expected.timestampMs = 1234;
        metrics.expected.provider = "test-only:metrics";
        metrics.expected.error = state == tabos::DataState::Error ? tabos::Error::Io : tabos::Error::None;
        auto sample = sample_cpu_temperature(metrics);
        assert(sample.state == state && sample.timestampMs == 1234 && sample.value == 42.5f);
        assert(sample.error == metrics.expected.error && std::strcmp(sample.provider.text(), "test-only:metrics") == 0);
    }
    assert(metrics.calls == 6);
}
"""


def test_contract_ids_and_implemented_scope():
    value = catalog()
    assert value["contract_version"] == 1
    assert not value["auto_execute"]
    assert value["language"] == "cpp17"
    assert len(value["nodes"]) == 4
    assert len({node["id"] for node in value["nodes"]}) == 4
    for node in value["nodes"]:
        assert node["status"] == "implemented"
        assert node["id"].startswith("espos.tabos.")
        assert node["id"].endswith(".v1")
        assert node["sources"]
        assert node["bindings"]
    for node in value["planned"]:
        assert node["status"] == "planned"
        assert "cpp_definition" not in node


def test_catalog_copy_and_serialization_are_deterministic():
    first = json.dumps(catalog(), sort_keys=True)
    changed = catalog()
    changed["nodes"][0]["bindings"].clear()
    assert json.dumps(catalog(), sort_keys=True) == first
    assert cpp_templates() == cpp_templates()


def test_file_operations_use_only_declared_bindings():
    node = catalog()["nodes"][2]
    names = {binding["name"] for binding in node["bindings"]}
    for operation in node["operations"].values():
        assert set(operation["inputs"]) <= names
        assert operation["output"] in names
        assert operation["function"] in node["functions"]


def test_cli_stdout_catalog_only():
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools/tabos_sdk_node_catalog.py")],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == catalog()
    assert main(["--execute"]) == 2


def test_current_real_sdk_compile_and_test_only_service_results():
    core_env = os.environ.get("TABOS_CORE_ROOT")
    if not core_env:
        pytest.skip("TABOS_CORE_ROOT required; SDK compile NOT VERIFIED")
    core = pathlib.Path(core_env)
    sdk = core / "apps/_src/tabos-sdk"
    compiler = shutil.which("g++")
    assert compiler, "g++ required for the explicitly selected real SDK"
    with tempfile.TemporaryDirectory(prefix="node-catalog-test-") as directory:
        tmp = pathlib.Path(directory)
        source, exe = tmp / "catalog.cpp", tmp / ("catalog.exe" if os.name == "nt" else "catalog")
        # Strip pragma once from a translation unit; it is appropriate in the exported header.
        source.write_text(
            cpp_templates().replace("#pragma once\n", "") + CPP_TEST, encoding="utf-8"
        )
        result = subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-DLV_CONF_SKIP=1",
                "-I",
                str(core / "dependencies/lvgl"),
                "-I",
                str(sdk / "include"),
                str(source),
                str(sdk / "src/result.cpp"),
                "-o",
                str(exe),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        runtime = subprocess.run([str(exe)], capture_output=True, text=True, timeout=20)
        assert runtime.returncode == 0, runtime.stdout + runtime.stderr
