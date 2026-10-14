"""PREPARED ONLY: actual parser integration after explicit PRIMARY runtime release.

No fake dependencies/parser. No installation, source write, MCP transport or
compiler. Missing pinned dependencies fail, not skip. Primary runs this file in
the reviewed isolated runtime after Huygens completes its work.
"""

import base64
import copy
import importlib.util
import pathlib
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009

CANDIDATE = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "released_readonly_candidate", CANDIDATE / "espos_mcp/codegraph_readonly.py"
)
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)

RAW = (
    b"\xef\xbb\xbf"
    + "// opaque měřič 🚦\r\ntemplate<class T> T keep(T x){return x;}\r\n".encode()
    + b"""void paint(lv_obj_t* label) {
    espos_tabos_nodes::set_label_text(label, "Ready");
}
int next_count(int current) {
    int step = 1;
    int next = current + step;
    return next;
}
""".replace(b"\n", b"\r\n")
    + "// trailing opaque e\u0301\r\n".encode()
)
BINDING = {
    "espos_tabos_nodes::set_label_text": {
        "operation": "espos.tabos.lvgl.label.text.v1",
        "returnType": "tabos::Status",
        "parameterTypes": ["lv_obj_t*", "const char*"],
    }
}


def request(source=RAW, **updates):
    return {
        "sourceBase64": base64.b64encode(source).decode(),
        "entries": ["paint", "next_count"],
        "bindings": copy.deepcopy(BINDING),
        "sdkProfile": c.SDK_PROFILE,
        **updates,
    }


class RealParserAfterRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph_module, _ = c._libraries()
        cls.versions = c._parser_dependencies()  # No implicit release, install or skip.

    def test_exact_bytes_and_actual_snapshot_restore(self):
        response = c.analyze_receipt(request())
        self.assertTrue(response["ok"], response)
        data = response["data"]
        self.assertEqual(base64.b64decode(data["sourceBase64"]), RAW)
        self.assertEqual(data["backend"]["dependencies"], self.versions)
        self.assertEqual(data["coverage"], "partial")
        self.assertEqual(data["evidence"], "CallerSourceAnalysis")
        self.assertFalse(data["ownerValidated"])
        restored = self.graph_module.restore_graph(
            RAW,
            data["graph"],
            entries=["paint", "next_count"],
            bindings=BINDING,
            sdk_profile=c.SDK_PROFILE,
        )
        self.assertEqual(restored.export_source(), RAW)
        self.assertEqual(restored.to_dict(), data["graph"])

    def test_opaque_hashes_ports_and_supported_wires_are_actual(self):
        data = c.analyze_receipt(request())["data"]
        self.assertEqual(data["analysisStatus"], "Analyzed")
        graph = data["graph"]
        self.assertTrue(
            any(n["kind"] == "opaque" and n.get("scope") == "selected" for n in graph["nodes"])
        )
        self.assertTrue(any("binding" in n for n in graph["nodes"]))
        self.assertTrue(any(e["kind"] == "execution" for e in graph["edges"]))
        self.assertTrue(any(e["kind"] == "data" for e in graph["edges"]))
        for node in graph["nodes"]:
            if node["kind"] == "opaque":
                self.assertEqual(node["ports"], [])
                self.assertEqual(node["editSlots"], [])
                s = node["sourceSpan"]
                self.assertEqual(
                    c.hashlib.sha256(RAW[s["startByte"] : s["endByte"]]).hexdigest(), s["sha256"]
                )

    def test_no_selected_entries_remains_honestly_opaque(self):
        data = c.analyze_receipt(request(entries=[]))["data"]
        self.assertEqual(data["coverage"], "partial")
        self.assertEqual(data["summary"]["supportedNodes"], 0)
        self.assertEqual(data["summary"]["opaqueOutsideSelectionNodes"], 1)
        self.assertEqual(base64.b64decode(data["sourceBase64"]), RAW)

    def test_invalid_cpp_is_observed_not_compilation_success(self):
        raw = b"void broken( {\r\n"
        response = c.analyze_receipt(request(raw, entries=["broken"]))
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["data"]["analysisStatus"], "InvalidCppOrSelection")
        self.assertEqual(base64.b64decode(response["data"]["sourceBase64"]), raw)
        self.assertTrue(
            any(d["severity"] == "error" for d in response["data"]["graph"]["diagnostics"])
        )

    def test_explicit_assertions_cannot_broaden_reviewed_profile(self):
        binding = copy.deepcopy(BINDING)
        binding["espos_tabos_nodes::set_label_text"]["returnType"] = "int"
        response = c.analyze_receipt(request(bindings=binding))
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "ParserRejected")
        self.assertEqual(response["error"]["sourceIdentity"], c._identity(RAW))

    def test_observation_is_preserved_but_never_owner_or_target_authority(self):
        observation = {
            "documentId": "caller-doc",
            "revision": 7,
            "targetId": "caller-not-registered",
        }
        data = c.analyze_receipt(request(observation=observation))["data"]
        self.assertEqual(data["observation"], observation)
        self.assertEqual(data["identityOrigin"], "caller-asserted")
        self.assertFalse(data["ownerValidated"])
        self.assertFalse(data["targetRegistryValidated"])

    def test_large_graph_has_explicit_limit_receipt_not_truncated_graph(self):
        raw = b"void many(){" + b"int x=0;" * (c.MAX_GRAPH_NODES + 1) + b"}"
        self.assertLessEqual(len(raw), c.MAX_SOURCE_BYTES)
        response = c.analyze_receipt(request(raw, entries=["many"], bindings={}))
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "LimitExceeded")
        self.assertIsNone(response["data"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
