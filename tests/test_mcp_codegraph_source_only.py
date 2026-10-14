"""SOURCE_ONLY: stdlib boundary/static checks and actual stdlib catalog metadata.

No MCP import/registration/transport, native Tree-sitter, parser invocation,
compiler, runtime environment mutation or file write. Boundary spies below are
TEST_ONLY rejection checks, never parser/SDK/runtime substitutes or proof.
"""

import ast
import base64
import copy
import importlib.util
import pathlib
import types
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from unittest.mock import patch

CANDIDATE = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "source_only_readonly_candidate", CANDIDATE / "espos_mcp/codegraph_readonly.py"
)
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


def valid(**updates):
    value = {"sourceBase64": base64.b64encode(b"void step() {}\r\n").decode(), "entries": ["step"]}
    return {**value, **updates}


class Boundaries(unittest.TestCase):
    def rejection_without_backend(self, request, code="InvalidArgument"):
        with patch.object(
            c, "_libraries", side_effect=AssertionError("TEST_ONLY: backend must not be reached")
        ):
            response = c.analyze_receipt(request)
        self.assertFalse(response["ok"])
        self.assertIsNone(response["data"])
        self.assertEqual(response["error"]["code"], code)
        self.assertLessEqual(len(response["error"]["message"]), 256)
        return response

    def test_operation_and_write_fields_are_rejected(self):
        for key in [
            "operation",
            "graph",
            "edits",
            "mutation",
            "expectedSourceHash",
            "path",
            "root",
            "command",
            "owner",
            "sourceBytes",
        ]:
            with self.subTest(key=key):
                self.rejection_without_backend(valid(**{key: "TEST_ONLY rejected extra field"}))
        for value in [None, [], "text", {}, {"entries": ["step"]}]:
            self.rejection_without_backend(value)

    def test_encoded_bound_applies_before_base64_decode_and_backend(self):
        with patch.object(
            c.base64,
            "b64decode",
            side_effect=AssertionError("TEST_ONLY: do not decode over-limit input"),
        ):
            self.rejection_without_backend(
                valid(sourceBase64="A" * (c.MAX_SOURCE_BASE64 + 1)), "LimitExceeded"
            )

    def test_decoded_bound_and_noncanonical_padding(self):
        self.rejection_without_backend(
            valid(sourceBase64=base64.b64encode(b"a" * (c.MAX_SOURCE_BYTES + 1)).decode()),
            "LimitExceeded",
        )
        for value in ["Zh==", "Zg==\n", "Zg=", "AA-_", "\ud800", 1, None, " "]:
            self.rejection_without_backend(valid(sourceBase64=value))

    def test_invalid_utf8_rejected_without_replacement_or_input_echo(self):
        response = self.rejection_without_backend(
            valid(sourceBase64=base64.b64encode(b"// opaque \xff\xfe\n").decode())
        )
        self.assertNotIn("sourceBase64", c.json_text(response))
        self.assertIn("never replaced", response["error"]["message"])

    def test_entries_are_explicit_unique_bounded_strings(self):
        for value in [
            None,
            "step",
            ["step"] * 2,
            ["x"] * 17,
            [""],
            ["x" * 257],
            ["x\n"],
            ["has space"],
            [True],
            ["\udfff"],
        ]:
            self.rejection_without_backend(valid(entries=value))
        raw, context, _ = c._analyze_input(valid(entries=[]))
        self.assertEqual(context["entries"], [])
        self.assertEqual(raw, b"void step() {}\r\n")

    def test_binding_objects_have_fixed_bounded_shape(self):
        good = {"operation": "caller.assertion", "returnType": "int", "parameterTypes": []}
        for value in [
            None,
            [],
            {str(i): good for i in range(33)},
            {"x": {**good, "effects": "invented"}},
            {"x": {"returnType": "int"}},
            {"has space": good},
            {"x": {**good, "parameterTypes": ["int"] * 9}},
            {"x": {**good, "parameterTypes": ["void"]}},
            {"x": {**good, "returnType": {"recursive": True}}},
        ]:
            self.rejection_without_backend(valid(bindings=value))

    def test_event_assertions_do_not_accept_unselected_entries(self):
        for value in [None, [], {"unselected": "TEST_ONLY"}, {"step": ""}, {"step": "\0"}]:
            self.rejection_without_backend(valid(eventBindings=value))
        _, context, _ = c._analyze_input(valid(eventBindings={"step": "LV_EVENT_CLICKED"}))
        self.assertEqual(context["eventBindings"], {"step": "LV_EVENT_CLICKED"})

    def test_unknown_sdk_profiles_and_observation_shapes_rejected(self):
        for profile in [None, True, "unknown", "tabos-sdk-minimal-1\n"]:
            self.rejection_without_backend(valid(sdkProfile=profile))
        observation = {"documentId": "caller-doc", "revision": 0, "targetId": "tab5_1280x720"}
        for value in [
            None,
            {},
            {**observation, "ownerValidated": True},
            {**observation, "revision": True},
            {**observation, "revision": -1},
            {**observation, "revision": 9007199254740992},
            {**observation, "targetId": ""},
            {**observation, "documentId": "x" * 129},
        ]:
            self.rejection_without_backend(valid(observation=value))

    def test_structured_request_limit_checked_before_backend(self):
        # Deliberately temporarily shrink the bound, not the shape enforcement.
        with patch.object(c, "MAX_REQUEST_BYTES", 1):
            self.rejection_without_backend(valid(), "LimitExceeded")

    def test_bom_crlf_unicode_accepted_without_normalization(self):
        raw = b"\xef\xbb\xbf" + "// měřič e\u0301 🚦\r\nvoid krok(){}\r\n".encode()
        request = valid(sourceBase64=base64.b64encode(raw).decode(), entries=["krok"])
        decoded, _, _ = c._analyze_input(request)
        self.assertEqual(decoded, raw)
        max_raw = b" " * c.MAX_SOURCE_BYTES
        self.assertEqual(
            c._analyze_input(valid(sourceBase64=base64.b64encode(max_raw).decode()))[0], max_raw
        )

    def test_detached_assertions_do_not_mutate_caller_context(self):
        request = valid(
            bindings={
                "fn": {"operation": "asserted", "returnType": "int", "parameterTypes": ["int"]}
            },
            observation={"documentId": "caller", "revision": 12, "targetId": "caller-target"},
        )
        _, context, observation = c._analyze_input(request)
        context["entries"].clear()
        context["bindings"]["fn"]["parameterTypes"].clear()
        observation["revision"] = 99
        self.assertEqual(request["entries"], ["step"])
        self.assertEqual(request["bindings"]["fn"]["parameterTypes"], ["int"])
        self.assertEqual(request["observation"]["revision"], 12)

    def test_unavailable_dependency_has_fixed_message_and_source_identity(self):
        with patch.object(
            c, "_libraries", side_effect=c._Unavailable("TEST_ONLY secret path must not escape")
        ):
            response = c.analyze_receipt(valid())
        self.assertEqual(response["error"]["code"], "Unavailable")
        self.assertEqual(response["error"]["sourceIdentity"]["byteLength"], 16)
        self.assertNotIn("secret", c.json_text(response))
        self.assertNotIn("sourceBase64", c.json_text(response))

    def test_missing_or_wrong_pinned_dependency_stops_before_native_import(self):
        for side_effect in [c.metadata.PackageNotFoundError("TEST_ONLY"), None]:
            with (
                patch.object(c.metadata, "version", side_effect=side_effect, return_value="0.0.0"),
                patch.object(
                    c.importlib,
                    "import_module",
                    side_effect=AssertionError("TEST_ONLY native import forbidden"),
                ),
                self.assertRaises(c._Unavailable),
            ):
                c._parser_dependencies()

    def test_host_bytecode_write_policy_is_checked_without_changing_it(self):
        with (
            patch.object(c.sys, "dont_write_bytecode", False),
            patch.object(
                c.importlib,
                "import_module",
                side_effect=AssertionError("TEST_ONLY imports must not write bytecode"),
            ),
        ):
            with self.assertRaises(c._Unavailable):
                c._libraries()
            self.assertFalse(c.sys.dont_write_bytecode)

    def test_backend_rejection_receipt_is_not_exception_or_payload_echo(self):
        class TestOnlyRejected(ValueError):
            pass

        parser_spy = types.SimpleNamespace(
            GraphError=TestOnlyRejected,
            parse_source=lambda *args, **kwargs: (_ for _ in ()).throw(
                TestOnlyRejected("TEST_ONLY private exception")
            ),
        )
        request = valid(
            bindings={"fn": {"operation": "asserted", "returnType": "int", "parameterTypes": []}}
        )
        before = copy.deepcopy(request)
        with (
            patch.object(c, "_libraries", return_value=(parser_spy, None)),
            patch.object(c, "_parser_dependencies", return_value={}),
        ):
            response = c.analyze_receipt(request)
        self.assertEqual(response["error"]["code"], "ParserRejected")
        self.assertNotIn("private", c.json_text(response))
        self.assertEqual(request, before)

    def test_byte_integrity_mismatch_is_rejected_without_success(self):
        # TEST_ONLY boundary spy: no fabricated graph is accepted as real evidence.
        graph_spy = types.SimpleNamespace(
            to_dict=lambda: {}, export_source=lambda: b"TEST_ONLY changed bytes"
        )
        parser_spy = types.SimpleNamespace(
            GraphError=ValueError, parse_source=lambda *args, **kwargs: graph_spy
        )
        with (
            patch.object(c, "_libraries", return_value=(parser_spy, None)),
            patch.object(c, "_parser_dependencies", return_value={}),
        ):
            response = c.analyze_receipt(valid())
        self.assertEqual(response["error"]["code"], "IntegrityError")
        self.assertIsNone(response["data"])

    def test_catalog_input_rejected_before_import(self):
        with patch.object(
            c, "_libraries", side_effect=AssertionError("TEST_ONLY backend forbidden")
        ):
            for offset, limit in [
                (True, 1),
                (0, False),
                (-1, 1),
                (257, 1),
                (0, 0),
                (0, 33),
                ("0", 1),
            ]:
                self.assertEqual(
                    c.catalog_receipt(offset, limit)["error"]["code"], "InvalidArgument"
                )

    def test_source_response_byte_limit_is_explicit_not_truncation(self):
        with patch.object(c, "MAX_RESPONSE_BYTES", 10):
            response = c._success(
                c.ANALYZE, {"sourceBase64": "TEST_ONLY", "sourceIdentity": {"sha256": "TEST_ONLY"}}
            )
        self.assertEqual(response["error"]["code"], "LimitExceeded")
        self.assertIsNone(response["data"])


class ActualCatalogMetadataOnly(unittest.TestCase):
    def test_actual_catalog_roundtrip_and_files_explicitly_opaque(self):
        graph_module, catalog_module = (
            c._libraries()
        )  # Canonical modules contain stdlib imports; no parser call.
        actual = catalog_module.catalog()
        response = c.catalog_receipt()
        self.assertTrue(response["ok"], response)
        data = response["data"]
        self.assertEqual(data["nodes"], actual["nodes"])
        self.assertEqual(data["catalogMetadata"], {k: v for k, v in actual.items() if k != "nodes"})
        self.assertEqual(
            data["parserSupport"]["espos.tabos.files.readonly.v1"]["status"],
            "OpaqueInCurrentProfile",
        )
        self.assertEqual(
            sum(v["status"] == "ExplicitBindingsOnly" for v in data["parserSupport"].values()), 3
        )
        for node in actual["nodes"]:
            support = data["parserSupport"][node["id"]]
            for callee, binding in support["reviewedSignatures"].items():
                self.assertEqual(binding, graph_module._SDK_OPERATIONS[callee])
                self.assertEqual(
                    binding["parameterTypes"],
                    [p["cpp_type"] for p in node["bindings"] if p["direction"] == "input"],
                )
        self.assertFalse(data["ownerValidated"])
        self.assertEqual(data["evidence"], "ReviewedSdkCatalogMetadata")

    def test_pagination_hash_and_repeated_reads_do_not_modify_actual_catalog(self):
        _, module = c._libraries()
        before = module.catalog()
        pages = [c.catalog_receipt(i, 1)["data"] for i in range(len(before["nodes"]))]
        self.assertEqual([p["nodes"][0] for p in pages], before["nodes"])
        self.assertEqual(len({p["catalogHash"] for p in pages}), 1)
        self.assertEqual(module.catalog(), before)
        self.assertEqual(c.catalog_receipt(256, 32)["data"]["nodes"], [])

    def test_unavailable_catalog_and_limits_do_not_report_empty_success(self):
        with patch.object(c, "_libraries", side_effect=c._Unavailable()):
            self.assertEqual(c.catalog_receipt()["error"]["code"], "Unavailable")
        with patch.object(c, "MAX_CATALOG_BYTES", 1):
            self.assertEqual(c.catalog_receipt()["error"]["code"], "LimitExceeded")


class StaticRegistrationOnly(unittest.TestCase):
    def test_all_staged_python_sources_are_parseable_without_importing_released_tests(self):
        # The deployment root becomes the whole repository after integration.
        # Check only this slice's four maintained files, not unrelated runtimes.
        sources = (
            "espos_mcp/codegraph_readonly.py",
            "espos_mcp/codegraph_tools.py",
            "tests/test_mcp_codegraph_source_only.py",
            "tests/test_mcp_codegraph_parser_released.py",
        )
        for relative in sources:
            source = CANDIDATE / relative
            with self.subTest(source=source.name):
                ast.parse(source.read_text(encoding="utf-8"), filename=str(source))

    def test_registration_composes_exactly_two_readonly_tools_no_server_cutover(self):
        tree = ast.parse((CANDIDATE / "espos_mcp/codegraph_tools.py").read_text(encoding="utf-8"))
        register = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "register_codegraph_tools"
        )
        functions = [n for n in register.body if isinstance(n, ast.FunctionDef)]
        self.assertEqual([n.name for n in functions], [c.ANALYZE, c.LIST_SDK])
        for fn in functions:
            self.assertEqual(
                ast.unparse(fn.decorator_list[0]),
                "server.tool(annotations=READ_ONLY, structured_output=True)",
            )
        calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertNotIn("FastMCP", calls)
        self.assertNotIn("register_codegraph_tools", calls)
        self.assertFalse(any(".run" in n or "Popen" in n for n in calls))
        self.assertIn("SourceRequest", ast.unparse(functions[0].args))

    def test_module_imports_and_calls_do_not_open_paths_or_route_arbitrary_commands(self):
        tree = ast.parse(
            (CANDIDATE / "espos_mcp/codegraph_readonly.py").read_text(encoding="utf-8")
        )
        imports = {n.name for t in ast.walk(tree) if isinstance(t, ast.Import) for n in t.names}
        self.assertFalse(
            imports & {"subprocess", "os", "pathlib", "mcp", "socket", "requests", "urllib"}
        )
        calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        for banned in [
            "open",
            "exec",
            "eval",
            "compile",
            "__import__",
            "sys.path.insert",
            "process_request",
        ]:
            self.assertNotIn(banned, calls)
        fixed = [
            n.args[0].value
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and ast.unparse(n.func) == "importlib.import_module"
            and isinstance(n.args[0], ast.Constant)
        ]
        self.assertEqual(
            set(fixed),
            {
                "tools.tabos_code_graph",
                "tools.tabos_sdk_node_catalog",
                "tree_sitter",
                "tree_sitter_cpp",
            },
        )

    def test_declared_pins_match_current_product_requirement_source(self):
        import tools.tabos_code_graph as canonical

        requirement = (
            pathlib.Path(canonical.__file__).resolve().parents[1]
            / "requirements-codegraph-win-py312.txt"
        )
        text = requirement.read_text(encoding="utf-8")
        for package, version in c.PARSER_DEPENDENCIES.items():
            self.assertIn(f"{package}=={version} --hash=sha256:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
