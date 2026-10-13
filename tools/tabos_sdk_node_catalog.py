"""Source-backed TabOS C++ node templates; catalog emission performs no SDK calls.

Destination: research/ESPOS/tools. Stable node IDs and contract_version=1 are
the integration proposal to the primary graph/code generator. No graph parser,
frontend, interpreter, hardware action, or opaque C++ rewriting is implemented.
"""

import copy
import json
import sys

CONTRACT_VERSION = 1
CPP_PREAMBLE = """#pragma once
#include <lvgl.h>
#include <tabos/result.h>
#include <tabos/data_source.h>
#include <tabos/services/file.h>
#include <tabos/services/system_metrics.h>
"""

CLICK = """inline lv_event_dsc_t* bind_click(lv_obj_t* object, lv_event_cb_t callback, void* user_data) {
    if (!object || !callback) return nullptr;
    return lv_obj_add_event_cb(object, callback, LV_EVENT_CLICKED, user_data);
}
"""
LABEL = """inline tabos::Status set_label_text(lv_obj_t* label, const char* text) {
    if (!label || !text || !lv_obj_check_type(label, &lv_label_class))
        return tabos::Status::error(tabos::Error::InvalidArgument, "espos:label-input");
    lv_label_set_text(label, text);
    return tabos::Status::ok();
}
"""
FILES = """inline tabos::Result<std::vector<tabos::IFileService::Entry>> list_files(
        tabos::IFileService& files, const char* relative_path) {
    if (!relative_path)
        return tabos::Result<std::vector<tabos::IFileService::Entry>>::failure(
            tabos::Error::InvalidArgument, "espos:file-input");
    return files.list(relative_path);
}
inline tabos::Result<size_t> read_file(tabos::IFileService& files, const char* relative_path,
        uint32_t offset, uint8_t* output, size_t capacity) {
    if (!relative_path || (!output && capacity != 0))
        return tabos::Result<size_t>::failure(tabos::Error::InvalidArgument, "espos:file-input");
    return files.read(relative_path, offset, output, capacity);
}
"""
METRIC = """inline tabos::DataPoint<float> sample_cpu_temperature(tabos::ISystemMetrics& metrics) {
    return metrics.cpuTemp();
}
"""


def port(name, cpp_type, direction, ownership="borrowed"):
    return {"name": name, "cpp_type": cpp_type, "direction": direction, "ownership": ownership}


_NODES = [
    {
        "id": "espos.tabos.lvgl.click.bind.v1",
        "status": "implemented",
        "title": "Bind click",
        "sources": [
            "LVGL 9.2.2 src/core/lv_obj_event.h:lv_obj_add_event_cb",
            "LVGL 9.2.2 src/misc/lv_event.h:lv_event_cb_t",
        ],
        "execution": "explicit UI lifecycle binding; callback runs on LVGL event thread",
        "bindings": [
            port("object", "lv_obj_t*", "input"),
            port("callback", "lv_event_cb_t", "input"),
            port("user_data", "void*", "input"),
            port("descriptor", "lv_event_dsc_t*", "output"),
        ],
        "functions": ["bind_click"],
        "cpp_definition": CLICK,
        "failure": "nullptr for missing object/callback or LVGL registration failure",
        "lifetime": "user_data and callback targets outlive registration; descriptor is owned by LVGL object",
        "graph_event": {
            "code": "LV_EVENT_CLICKED",
            "argument": "lv_event_t*",
            "callback_abi": "void (*)(lv_event_t*)",
        },
    },
    {
        "id": "espos.tabos.lvgl.label.text.v1",
        "status": "implemented",
        "title": "Set label text",
        "sources": [
            "LVGL 9.2.2 src/widgets/label/lv_label.h:lv_label_set_text",
            "tabos/result.h:Status",
        ],
        "execution": "explicit UI thread invocation",
        "bindings": [
            port("label", "lv_obj_t*", "input"),
            port("text", "const char*", "input"),
            port("status", "tabos::Status", "output", "value"),
        ],
        "functions": ["set_label_text"],
        "cpp_definition": LABEL,
        "failure": "InvalidArgument for null/non-label target or null text; no SDK callback invented",
        "lifetime": "LVGL copies text; caller must supply a valid NUL-terminated UTF-8 string during call",
    },
    {
        "id": "espos.tabos.files.readonly.v1",
        "status": "implemented",
        "title": "Files list/read",
        "sources": [
            "tabos/services/file.h:IFileService::list",
            "tabos/services/file.h:IFileService::read",
            "tabos/result.h:Result<T>",
        ],
        "execution": "explicit worker invocation; never under LVGL lock",
        "bindings": [
            port("files", "tabos::IFileService&", "input"),
            port("relative_path", "const char*", "input"),
            port("offset", "uint32_t", "input"),
            port("output", "uint8_t*", "input"),
            port("capacity", "size_t", "input"),
            port(
                "entries",
                "tabos::Result<std::vector<tabos::IFileService::Entry>>",
                "output",
                "value",
            ),
            port("read_result", "tabos::Result<size_t>", "output", "value"),
        ],
        "operations": {
            "list": {
                "function": "list_files",
                "inputs": ["files", "relative_path"],
                "output": "entries",
            },
            "read": {
                "function": "read_file",
                "inputs": ["files", "relative_path", "offset", "output", "capacity"],
                "output": "read_result",
            },
        },
        "functions": ["list_files", "read_file"],
        "cpp_definition": FILES,
        "failure": "preserve original Result error/provider; access value only after ok(); short read is not an error",
        "lifetime": "caller owns service, path and output buffer; only successful Result<size_t>.value() bytes are readable",
        "scheduling": "host owns worker scheduling and posts UI updates through existing UI lifecycle; no automatic IAsync job",
    },
    {
        "id": "espos.tabos.metrics.cpu_temp.sample.v1",
        "status": "implemented",
        "title": "Sample CPU temperature",
        "sources": [
            "tabos/services/system_metrics.h:ISystemMetrics::cpuTemp",
            "tabos/data_source.h:DataPoint<T>",
        ],
        "execution": "explicit invocation of supplied service; no timer/polling created",
        "bindings": [
            port("metrics", "tabos::ISystemMetrics&", "input"),
            port("sample", "tabos::DataPoint<float>", "output", "value"),
        ],
        "functions": ["sample_cpu_temperature"],
        "cpp_definition": METRIC,
        "sample_fields": {
            "value": "float",
            "state": "tabos::DataState",
            "timestampMs": "uint32_t",
            "provider": "tabos::Puvodce",
            "error": "tabos::Error",
        },
        "failure": "Unavailable/Error stay unavailable; no zero-as-measurement, no forced Live, no fabricated provider",
        "lifetime": "DataPoint owns provenance bytes; copying sample preserves state/provenance",
        "data_policy": "Estimated/Mock require explicit presentation; usable() is not permission to render smalt",
    },
]


def catalog():
    return {
        "contract_version": CONTRACT_VERSION,
        "language": "cpp17",
        "namespace": "espos_tabos_nodes",
        "profile": "tab5",
        "kind": "cpp-template-catalog",
        "auto_execute": False,
        "general_cpp": {"opaque_unsupported_code": "preserve unchanged; no parser in this tool"},
        "cpp_preamble": CPP_PREAMBLE,
        "nodes": copy.deepcopy(_NODES),
        "planned": [
            {
                "id": "espos.tabos.planned.additional-sdk",
                "status": "planned",
                "reason": "Other services/widgets require separate contract review; no callable template",
            }
        ],
    }


def cpp_templates():
    return (
        CPP_PREAMBLE
        + "namespace espos_tabos_nodes {\n"
        + "".join(n["cpp_definition"] for n in _NODES)
        + "}\n"
    )


def main(argv=None):
    # stdout only; no file writes or execution capabilities.
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print("usage: tabos_sdk_node_catalog.py (prints catalog JSON)", file=sys.stderr)
        return 2
    print(json.dumps(catalog(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
