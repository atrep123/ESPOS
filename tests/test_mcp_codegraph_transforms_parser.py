"""Actual canonical C++ transformation regressions.

Real pinned parser dependencies are required; missing dependencies fail.
No fake backend, skips, compiler or transport. Snippets are TEST_ONLY source.
"""

import base64
import copy
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009
from espos_mcp import codegraph_transforms as c

PREFIX = (
    b"\xef\xbb\xbf" + "// měřič 🚦 e\u0301\r\ntemplate<class T> T keep(T x){return x;}\r\n".encode()
)
SUFFIX = b"\r\nauto untouched=[](){return keep(8);};\r\n"
RAW = PREFIX + b"void step(){\r\n  int x=1;\r\n  x=x+2;\r\n  x=x+3;\r\n}\r\n" + SUFFIX
BINDINGS = {
    "espos_tabos_nodes::bind_click": {
        "operation": "espos.tabos.lvgl.click.bind.v1",
        "returnType": "lv_event_dsc_t*",
        "parameterTypes": ["lv_obj_t*", "lv_event_cb_t", "void*"],
    },
    "espos_tabos_nodes::set_label_text": {
        "operation": "espos.tabos.lvgl.label.text.v1",
        "returnType": "tabos::Status",
        "parameterTypes": ["lv_obj_t*", "const char*"],
    },
    "espos_tabos_nodes::sample_cpu_temperature": {
        "operation": "espos.tabos.metrics.cpu_temp.sample.v1",
        "returnType": "tabos::DataPoint<float>",
        "parameterTypes": ["tabos::ISystemMetrics&"],
    },
}


def envelope(data, **fields):
    return {
        "schemaVersion": 1,
        "sourceBase64": data["sourceBase64"],
        "graph": copy.deepcopy(data["graph"]),
        "expectedSourceHash": data["graph"]["sourceHash"],
        **copy.deepcopy(data["parseContext"]),
        **fields,
    }


def opaque(data):
    raw = base64.b64decode(data["sourceBase64"], validate=True)
    return {
        n["id"]: raw[n["sourceSpan"]["startByte"] : n["sourceSpan"]["endByte"]]
        for n in data["graph"]["nodes"]
        if n["kind"] == "opaque"
    }


class ActualParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = c._library()
        cls.versions = (
            c.source._parser_dependencies()
        )  # Actual native parser imports; never executed submitted C++.

    def analyze(self, raw=RAW, **context):
        result = c.source.analyze_receipt(
            {"sourceBase64": base64.b64encode(raw).decode(), "entries": ["step"], **context}
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["analysisStatus"], "Analyzed")
        return result["data"]

    def action(self, name, data, **fields):
        request = envelope(data, **fields)
        before = copy.deepcopy(request)
        result = c.transform_receipt(name, request)
        self.assertEqual(request, before)
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["data"]["filesystemWritten"])
        self.assertFalse(result["data"]["ownerValidated"])
        self.assertEqual(result["data"]["backend"]["dependencies"], self.versions)
        return result["data"]

    def test_regions_and_empty_edit_are_byte_identical_actual_snapshot(self):
        data = self.analyze()
        regions = self.action("list_cpp_regions_v1", data)
        self.assertTrue(regions["regions"])
        self.assertEqual(regions["graph"], data["graph"])
        changed = self.action("edit_cpp_v1", data, edits=[])
        self.assertEqual(changed["graph"], data["graph"])
        self.assertEqual(base64.b64decode(changed["sourceBase64"]), RAW)
        self.assertFalse(changed["sourceChanged"])

    def test_actual_literal_edit_preserves_opaque_bytes_ids_bom_unicode_crlf(self):
        data = self.analyze()
        node = next(n for n in data["graph"]["nodes"] if n["kind"] == "declaration")
        slot = next(s for s in node["editSlots"] if s["kind"] == "literal")
        changed = self.action(
            "edit_cpp_v1",
            data,
            edits=[{"nodeId": node["id"], "slotId": slot["id"], "replacement": "7"}],
        )
        self.assertEqual(base64.b64decode(changed["sourceBase64"]), RAW.replace(b"x=1", b"x=7"))
        self.assertEqual(opaque(changed), opaque(data))
        self.assertEqual(
            [n["id"] for n in changed["graph"]["nodes"]], [n["id"] for n in data["graph"]["nodes"]]
        )

    def test_actual_insert_sequence_delete_are_real_bytes_not_metadata(self):
        original = self.analyze()
        data = self.action("list_cpp_regions_v1", original)
        data = self.action(
            "construct_cpp_v1",
            data,
            mutation={
                "kind": "insertStatement",
                "regionId": data["regions"][0]["id"],
                "beforeNodeId": None,
                "cpp": "int y=4;",
            },
        )
        self.assertIn(b"int y=4;", base64.b64decode(data["sourceBase64"]))
        ids = data["regions"][0]["nodeIds"]
        data = self.action(
            "construct_cpp_v1",
            data,
            mutation={
                "kind": "setSequence",
                "regionId": data["regions"][0]["id"],
                "nodeIds": [ids[0], ids[2], ids[1], ids[3]],
            },
        )
        raw = base64.b64decode(data["sourceBase64"])
        self.assertLess(raw.index(b"x=x+3"), raw.index(b"x=x+2"))
        data = self.action(
            "construct_cpp_v1",
            data,
            mutation={"kind": "deleteNode", "regionId": data["regions"][0]["id"], "nodeId": ids[3]},
        )
        self.assertNotIn(b"int y=4;", base64.b64decode(data["sourceBase64"]))
        self.assertEqual(data["changeSet"]["removedNodeIds"], [ids[3]])
        self.assertEqual(opaque(data), opaque(original))

    def test_actual_opaque_body_disables_regions_without_fabricating_support(self):
        data = self.analyze(PREFIX + b"void step(){ mystery(); }" + SUFFIX)
        self.assertEqual(self.action("list_cpp_regions_v1", data)["regions"], [])
        result = c.transform_receipt(
            "construct_cpp_v1",
            envelope(
                data,
                mutation={
                    "kind": "insertStatement",
                    "regionId": "invented",
                    "beforeNodeId": None,
                    "cpp": "int x=1;",
                },
            ),
        )
        self.assertEqual(result["error"]["code"], "ParserRejected")
        self.assertIsNone(result["data"])

    def test_tampered_snapshot_stale_hash_cross_incarnation_and_overlap_reject(self):
        data = self.action("list_cpp_regions_v1", self.analyze())
        alternate = self.action("list_cpp_regions_v1", self.analyze())
        node = next(n for n in data["graph"]["nodes"] if n["editSlots"])
        edit = {"nodeId": node["id"], "slotId": node["editSlots"][0]["id"], "replacement": "9"}
        cases = [
            envelope(data, edits=[edit, edit]),
            envelope(data, edits=[edit], expectedSourceHash="0" * 64),
        ]
        tampered = envelope(data, edits=[edit])
        tampered["graph"]["nodes"][0]["sourceSpan"]["startByte"] += 1
        cases.append(tampered)
        wrong_type = envelope(data, edits=[edit])
        wrong_type["graph"]["schemaVersion"] = (
            True  # Python True == 1 is NOT an exact JSON snapshot.
        )
        cases.append(wrong_type)
        for request in cases:
            result = c.transform_receipt("edit_cpp_v1", request)
            self.assertFalse(result["ok"])
            self.assertIsNone(result["data"])
        request = envelope(
            alternate,
            mutation={
                "kind": "insertStatement",
                "regionId": data["regions"][0]["id"],
                "beforeNodeId": None,
                "cpp": "int y=4;",
            },
        )
        self.assertEqual(
            c.transform_receipt("construct_cpp_v1", request)["error"]["code"], "ParserRejected"
        )

    def test_actual_sdk_three_explicit_signatures_and_error_branch(self):
        raw = (
            PREFIX
            + b"void step(lv_obj_t* label, tabos::ISystemMetrics& metrics, lv_obj_t* button, lv_event_cb_t callback, void* ctx) {}"
            + SUFFIX
        )
        data = self.analyze(raw, sdkProfile=c.source.SDK_PROFILE, bindings=BINDINGS)
        original_opaque = opaque(data)
        data = self.action("list_cpp_sdk_regions_v1", data)
        for cpp in (
            "auto descriptor=espos_tabos_nodes::bind_click(button,callback,ctx);",
            'auto status=espos_tabos_nodes::set_label_text(label,"Kliknutí 🚦");',
            "auto sample=espos_tabos_nodes::sample_cpu_temperature(metrics);",
            'if(sample.state==tabos::DataState::Error){auto error_status=espos_tabos_nodes::set_label_text(label,"Error");}'
            'else{if(sample.state==tabos::DataState::Unavailable){auto unavailable_status=espos_tabos_nodes::set_label_text(label,"Unavailable");}}',
        ):
            data = self.action(
                "construct_cpp_sdk_v1",
                data,
                mutation={
                    "kind": "insertSdkStatement",
                    "regionId": data["sdkRegions"][0]["id"],
                    "beforeNodeId": None,
                    "cpp": cpp,
                },
            )
        self.assertEqual(opaque(data), original_opaque)
        sample = next(n for n in data["graph"]["nodes"] if n.get("variable") == "sample")
        self.assertEqual(sample["cppType"], "tabos::DataPoint<float>")
        changed = base64.b64decode(data["sourceBase64"])
        self.assertIn(b"DataState::Error", changed)
        self.assertIn(b"DataState::Unavailable", changed)
        self.assertNotIn(b"sample.value", changed)
        self.assertNotIn(b"DataState::Live", changed)
        self.assertFalse(any(e["kind"] == "event" for e in data["graph"]["edges"]))

    def test_sdk_string_edit_and_unbound_call_fail_without_unknown_rewrite(self):
        raw = (
            PREFIX
            + b'void step(lv_obj_t* label){auto status=espos_tabos_nodes::set_label_text(label,"old");}'
            + SUFFIX
        )
        data = self.analyze(raw, sdkProfile=c.source.SDK_PROFILE, bindings=BINDINGS)
        node = next(n for n in data["graph"]["nodes"] if n.get("variable") == "status")
        slot = next(s for s in node["editSlots"] if s["kind"] == "string")
        changed = self.action(
            "edit_cpp_v1",
            data,
            edits=[{"nodeId": node["id"], "slotId": slot["id"], "replacement": '"Nové 🚦"'}],
        )
        self.assertEqual(
            base64.b64decode(changed["sourceBase64"]), raw.replace(b'"old"', '"Nové 🚦"'.encode())
        )
        regions = self.action("list_cpp_sdk_regions_v1", changed)
        for cpp in (
            "mystery();",
            "sample.state=tabos::DataState::Live;",
            "auto value=sample.value;",
        ):
            result = c.transform_receipt(
                "construct_cpp_sdk_v1",
                envelope(
                    regions,
                    mutation={
                        "kind": "insertSdkStatement",
                        "regionId": regions["sdkRegions"][0]["id"],
                        "beforeNodeId": None,
                        "cpp": cpp,
                    },
                ),
            )
            self.assertFalse(result["ok"])
            self.assertIsNone(result["data"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
