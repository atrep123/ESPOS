"""Maintained canonical boundary/three-profile/SDK source controls; NO native parser.

All graph dictionaries here are TEST_ONLY deliberately incomplete envelopes,
never accepted parser evidence. Rejection spies cannot create a successful edit.
"""

import ast
import base64
import copy
import hashlib
import inspect
import json
import types
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from pathlib import Path
from unittest.mock import patch

from mcp.types import CallToolRequest, CallToolRequestParams

from espos_mcp import codegraph_transforms as c
from espos_mcp import profiles
from espos_mcp.codegraph_transform_tools import _request_schema, register_codegraph_transform_tools
from espos_mcp.profiles import READ_ONLY_TOOLS, build_profiled_server
from espos_mcp.server import build_server

RAW = b"void step() {}\r\n"
MARKER = "TEST_ONLY_C:/not-real-secret/žluťoučký"
REGIONS, EDIT, CONSTRUCT, SDK_REGIONS, SDK_CONSTRUCT = c.OPERATIONS


def request(**changes):
    return {
        "schemaVersion": 1,
        "sourceBase64": base64.b64encode(RAW).decode(),
        "entries": ["step"],
        "graph": {"sourceHash": hashlib.sha256(RAW).hexdigest(), "nodes": [], "edges": []},
        "expectedSourceHash": hashlib.sha256(RAW).hexdigest(),
        **changes,
    }


def complete(coroutine):
    if not inspect.iscoroutine(coroutine):
        raise AssertionError("Expected actual SDK coroutine")
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError("Unexpected suspension; not transport/event-loop proof")


def call(server, name, args):
    actual = CallToolRequest(params=CallToolRequestParams(name=name, arguments=args))
    return complete(server._mcp_server.request_handlers[CallToolRequest](actual)).root


class Boundary(unittest.TestCase):
    def reject(self, value, operation=REGIONS, code="InvalidArgument"):
        with patch.object(
            c, "_library", side_effect=AssertionError("TEST_ONLY backend must not be reached")
        ):
            response = c.transform_receipt(operation, value)
        self.assertFalse(response["ok"])
        self.assertIsNone(response["data"])
        self.assertEqual(response["error"]["code"], code)
        self.assertFalse(response["error"]["retryable"])
        self.assertNotIn(MARKER, c.source.json_text(response))
        self.assertLessEqual(len(response["error"]["message"]), 256)

    def test_extra_path_owner_command_operation_and_authority_reject(self):
        for name in (
            "path",
            "root",
            "command",
            "operation",
            "owner",
            "grant",
            "document",
            "filesystemWritten",
        ):
            with self.subTest(name=name):
                self.reject(request(**{name: MARKER}))

    def test_strict_version_shape_and_unknown_internal_operation(self):
        for value in (None, [], True, MARKER, {}):
            self.reject(value)
        for version in (True, "1", 2, 1.0):
            self.reject(request(schemaVersion=version))
        for operation in (MARKER, [], None):
            self.reject(request(), operation)

    def test_base64_utf8_and_entries_reuse_actual_readonly_contract(self):
        for encoded in ("Zh==", "Zg==\n", base64.b64encode(b"\xff").decode(), True):
            self.reject(request(sourceBase64=encoded))
        for entries in (["step", "step"], [""], [True], ["step\n"], [MARKER] * 17):
            self.reject(request(entries=entries))

    def test_encoded_and_decoded_source_limits_before_backend(self):
        self.reject(
            request(sourceBase64="A" * (c.source.MAX_SOURCE_BASE64 + 1)), code="LimitExceeded"
        )
        self.reject(
            request(sourceBase64=base64.b64encode(b" " * (c.source.MAX_SOURCE_BYTES + 1)).decode()),
            code="LimitExceeded",
        )

    def test_stale_source_or_snapshot_hash_is_conflict(self):
        self.reject(request(expectedSourceHash="0" * 64), code="Conflict")
        value = request()
        value["graph"]["sourceHash"] = "0" * 64
        self.reject(value, code="Conflict")
        self.reject(request(expectedSourceHash=True))
        self.reject(request(expectedSourceHash="A" * 64))

    def test_graph_shape_and_node_edge_bounds(self):
        for graph in (None, [], {"nodes": {}, "edges": []}, {"nodes": [], "edges": {}}):
            self.reject(request(graph=graph))
        value = request()
        value["graph"]["nodes"] = [None] * (c.source.MAX_GRAPH_NODES + 1)
        self.reject(value, code="LimitExceeded")
        value = request()
        value["graph"]["edges"] = [None] * (c.source.MAX_GRAPH_EDGES + 1)
        self.reject(value, code="LimitExceeded")

    def test_tree_bounds_cycles_types_and_nonfinite_values(self):
        for item in (float("nan"), float("inf"), -(2**60), b"bytes", {1: "bad"}, "\ud800"):
            self.reject(request(graph={"nodes": [], "edges": [], "bad": item}))
        cycle = []
        cycle.append(cycle)
        self.reject(request(graph={"nodes": [], "edges": [], "bad": cycle}), code="LimitExceeded")
        self.reject(
            request(graph={"nodes": [], "edges": [], "bad": [0] * (c.MAX_JSON_ITEMS + 1)}),
            code="LimitExceeded",
        )

    def test_total_request_budget_applies_before_backend(self):
        with patch.object(c, "MAX_JSON_ITEMS", 100000):
            self.reject(
                request(graph={"nodes": [], "edges": [], "bad": MARKER * 16000}),
                code="LimitExceeded",
            )

    def test_edits_are_strict_bounded_unique_without_raw_patch_offsets(self):
        edit = {"nodeId": "node", "slotId": "token-0", "replacement": "2"}
        for edits in (
            None,
            {},
            [edit] * 65,
            [edit, edit],
            [{**edit, "startByte": 1}],
            [{**edit, "replacement": True}],
            [{**edit, "replacement": "\0"}],
        ):
            self.reject(request(edits=edits), EDIT)
        self.reject(request(edits=[{**edit, "replacement": "2" * 257}]), EDIT, "LimitExceeded")
        self.reject(request(edits=[]), REGIONS)

    def test_construction_shapes_anchor_and_sequence_not_arbitrary_graph_wiring(self):
        good = {
            "kind": "insertStatement",
            "regionId": "region",
            "beforeNodeId": None,
            "cpp": "int x=1;",
        }
        for mutation in (
            None,
            {**good, "kind": "addEdge"},
            {**good, "expectedState": "Live"},
            {**good, "beforeNodeId": True},
            {**good, "cpp": "\0"},
            {"kind": "setSequence", "regionId": "region", "nodeIds": ["n", "n"]},
            {"kind": "deleteNode", "regionId": "region", "nodeId": []},
        ):
            self.reject(request(mutation=mutation), CONSTRUCT)
        self.reject(request(mutation={**good, "cpp": "x" * 4097}), CONSTRUCT, "LimitExceeded")

    def test_sdk_profile_and_mutation_kind_are_explicit(self):
        self.reject(request(), SDK_REGIONS)
        self.reject(request(sdkProfile="other"), SDK_REGIONS)
        self.reject(
            request(
                sdkProfile=c.source.SDK_PROFILE,
                mutation={"kind": "deleteNode", "regionId": "region", "nodeId": "node"},
            ),
            SDK_CONSTRUCT,
        )
        self.reject(
            request(
                sdkProfile=c.source.SDK_PROFILE,
                mutation={
                    "kind": "insertSdkStatement",
                    "regionId": "region",
                    "beforeNodeId": None,
                    "cpp": "x;",
                },
            ),
            CONSTRUCT,
        )

    def test_context_observation_no_new_adoption_authority(self):
        self.reject(
            request(observation={"documentId": "doc", "revision": True, "targetId": "caller"})
        )
        self.reject(request(eventBindings={"unselected": "event"}))
        self.reject(
            request(
                bindings={
                    "x": {
                        "operation": "x",
                        "returnType": "int",
                        "parameterTypes": [],
                        "authority": True,
                    }
                }
            )
        )

    def test_accepted_envelope_preserves_original_bom_crlf_unicode_without_parsing(self):
        raw = b"\xef\xbb\xbf" + "// měřič 🚦 e\u0301\r\nvoid step(){}\r\n".encode()
        value = request(
            sourceBase64=base64.b64encode(raw).decode(),
            expectedSourceHash=hashlib.sha256(raw).hexdigest(),
        )
        value["graph"]["sourceHash"] = value["expectedSourceHash"]
        before = copy.deepcopy(value)
        actual, context, observation = c._input(REGIONS, value)
        self.assertEqual(actual, raw)
        self.assertEqual(value, before)
        self.assertEqual(context, {"entries": ["step"]})
        self.assertIsNone(observation)

    def test_missing_backend_returns_unavailable_without_echo(self):
        with patch.object(c, "_library", side_effect=c.source._Unavailable(MARKER)):
            response = c.transform_receipt(REGIONS, request())
        self.assertEqual(response["error"]["code"], "Unavailable")
        self.assertIsNone(response["data"])
        self.assertNotIn(MARKER, json.dumps(response))

    def test_missing_native_dependency_does_not_fake_transformation(self):
        with patch.object(
            c.source, "_parser_dependencies", side_effect=c.source._Unavailable(MARKER)
        ):
            response = c.transform_receipt(EDIT, request(edits=[]))
        self.assertEqual(response["error"]["code"], "Unavailable")
        self.assertEqual(response["error"]["sourceIdentity"], c.source._identity(RAW))

    def test_deliberately_broken_backend_rejection_is_fixed_not_fake_success(self):
        class TEST_ONLY_Rejected(ValueError):
            pass

        def reject(*_args, **_kwargs):
            raise TEST_ONLY_Rejected(MARKER)

        fixture = types.SimpleNamespace(restore_graph=reject, GraphError=TEST_ONLY_Rejected)
        with (
            patch.object(c, "_library", return_value=fixture),
            patch.object(c.source, "_parser_dependencies", return_value={}),
        ):
            response = c.transform_receipt(REGIONS, request())
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "ParserRejected")
        self.assertNotIn(MARKER, json.dumps(response))


class ActualMetadataAndSDK(unittest.TestCase):
    def test_actual_capabilities_are_metadata_not_runtime_success(self):
        response = c.capabilities_receipt()
        self.assertTrue(response["ok"], response)
        data = response["data"]
        self.assertEqual(data["backendStatus"], "SourceContractPresent")
        self.assertFalse(data["nativeParserProbed"])
        self.assertEqual(data["runtimeAvailability"], "Unverified")
        self.assertFalse(data["defaultReadOnlyProfileWidened"])
        actual = c._library()
        for method in c._METHODS:
            self.assertTrue(callable(getattr(actual.CodeGraph, method)))

    def test_missing_metadata_no_success(self):
        with patch.object(c, "_library", side_effect=c.source._Unavailable()):
            self.assertEqual(c.capabilities_receipt()["error"]["code"], "Unavailable")

    def test_explicit_same_factory_registration_six_only_and_annotations(self):
        server = build_server()
        before = {tool.name for tool in complete(server.list_tools())}
        self.assertEqual(len(before), 22)
        register_codegraph_transform_tools(server)
        actual = {tool.name: tool for tool in complete(server.list_tools())}
        self.assertEqual(set(actual) - before, {c.CAPABILITIES, *c.OPERATIONS})
        for name in c.OPERATIONS:
            tool = actual[name]
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.destructiveHint)
            self.assertFalse(tool.annotations.openWorldHint)
            self.assertFalse(tool.annotations.idempotentHint)
            self.assertIn("request", tool.inputSchema["properties"])
            self.assertIsNotNone(tool.outputSchema)
        self.assertEqual(len(complete(build_server().list_tools())), 22)
        self.assertEqual(
            {t.name for t in complete(complete(build_profiled_server()).list_tools())},
            READ_ONLY_TOOLS,
        )

    def test_actual_sdk_calls_capability_and_rejects_all_five_bad_requests(self):
        server = build_server()
        register_codegraph_transform_tools(server)
        receipt = call(server, c.CAPABILITIES, {})
        self.assertFalse(receipt.isError)
        self.assertEqual(json.loads(receipt.content[0].text), receipt.structuredContent)
        with patch.object(c, "_library", side_effect=AssertionError("TEST_ONLY parser forbidden")):
            for name in c.OPERATIONS:
                result = call(server, name, {"request": {"path": MARKER}})
                self.assertTrue(result.isError)
                self.assertEqual(result.structuredContent["error"]["code"], "InvalidArgument")
                self.assertNotIn(MARKER, result.model_dump_json())
        for value in (MARKER, True, []):
            result = call(server, EDIT, {"request": value})
            self.assertTrue(result.isError)
            self.assertNotIn(MARKER, result.model_dump_json())

    def test_schema_exposes_explicit_profile_and_only_existing_mutations(self):
        general = _request_schema("construct")
        sdk = _request_schema("constructSdk")
        self.assertFalse(general["additionalProperties"])
        self.assertEqual(
            {x["properties"]["kind"]["const"] for x in general["properties"]["mutation"]["oneOf"]},
            {"insertStatement", "deleteNode", "setSequence"},
        )
        self.assertIn("sdkProfile", sdk["required"])
        self.assertEqual(
            sdk["properties"]["mutation"]["oneOf"][0]["properties"]["kind"]["const"],
            "insertSdkStatement",
        )

    def test_canonical_sources_parse_and_no_path_or_execution_backend(self):
        root = Path(c.__file__).resolve().parent
        self.assertEqual(c.__name__, "espos_mcp.codegraph_transforms")
        self.assertEqual(profiles.__name__, "espos_mcp.profiles")
        for file in (
            root / "codegraph_transforms.py",
            root / "codegraph_transform_tools.py",
            root / "profiles.py",
        ):
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
            calls = {
                ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)
            }
            self.assertFalse(
                calls
                & {
                    "open",
                    "eval",
                    "exec",
                    "compile",
                    "subprocess.run",
                    "FastMCP",
                    "process_request",
                }
            )
        wrapper = ast.parse((root / "codegraph_transforms.py").read_text(encoding="utf-8"))
        calls = {ast.unparse(node.func) for node in ast.walk(wrapper) if isinstance(node, ast.Call)}
        self.assertTrue(
            {
                "library.restore_graph",
                "original.apply_edits",
                "original.apply_construction",
                "original.apply_sdk_construction",
                "result.construction_regions",
                "result.sdk_construction_regions",
            }
            <= calls
        )


class ExplicitCodegraphProfile(unittest.TestCase):
    def test_real_sdk_inventory_has_exact_eleven_reviewed_schemas(self):
        expected = build_server()
        register_codegraph_transform_tools(expected)
        expected_tools = {t.name: t.model_dump() for t in complete(expected.list_tools())}
        selected = complete(profiles.build_profiled_server("codegraph"))
        actual = {t.name: t.model_dump() for t in complete(selected.list_tools())}
        reviewed = READ_ONLY_TOOLS | {c.CAPABILITIES, *c.OPERATIONS}
        self.assertEqual(len(reviewed), 11)
        self.assertEqual(profiles.CODEGRAPH_TOOLS, reviewed)
        self.assertEqual(actual, {name: expected_tools[name] for name in reviewed})
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in actual.values()))

    def test_default_five_and_full_twenty_two_do_not_register_transforms(self):
        expected = [t.model_dump() for t in complete(build_server().list_tools())]
        with patch(
            "espos_mcp.codegraph_transform_tools.register_codegraph_transform_tools",
            side_effect=AssertionError("TEST_ONLY transform registration must not run"),
        ) as registration:
            for profile in (None, "read-only", "full"):
                server = complete(
                    profiles.build_profiled_server()
                    if profile is None
                    else profiles.build_profiled_server(profile)
                )
                inventory = [t.model_dump() for t in complete(server.list_tools())]
                if profile == "full":
                    self.assertEqual(inventory, expected)
                    self.assertEqual(len(inventory), 22)
                else:
                    self.assertEqual({t["name"] for t in inventory}, READ_ONLY_TOOLS)
            registration.assert_not_called()
        self.assertEqual(len(complete(build_server().list_tools())), 22)

    def test_all_removed_direct_calls_denied_without_mutation_callbacks(self):
        selected = complete(profiles.build_profiled_server("codegraph"))
        removed = {t.name for t in complete(build_server().list_tools())} - READ_ONLY_TOOLS
        self.assertEqual(len(removed), 17)
        with (
            patch("espos_mcp.server._atomic_save", side_effect=AssertionError("write")) as save,
            patch("espos_mcp.server._write_dict", side_effect=AssertionError("write")) as write,
            patch("espos_mcp.server.build_board", side_effect=AssertionError("build")) as build,
            patch("espos_mcp.server.flash_board", side_effect=AssertionError("flash")) as flash,
        ):
            for name in sorted(removed):
                with self.subTest(tool=name):
                    result = call(selected, name, {"path": MARKER})
                    self.assertTrue(result.isError)
                    self.assertNotIn(MARKER, result.model_dump_json())
            for effect in (save, write, build, flash):
                effect.assert_not_called()

    def test_future_factory_and_transform_tools_removed_no_callback_dispatch(self):
        selected_factory = build_server()
        calls = []

        @selected_factory.tool()
        def TEST_ONLY_future_factory_tool() -> str:
            calls.append("factory")
            raise AssertionError("Unreviewed factory callback")

        def registration(server):
            register_codegraph_transform_tools(server)

            @server.tool()
            def TEST_ONLY_future_transform_tool() -> str:
                calls.append("transform")
                raise AssertionError("Unreviewed transform callback")

        with (
            patch("espos_mcp.server.build_server", return_value=selected_factory),
            patch(
                "espos_mcp.codegraph_transform_tools.register_codegraph_transform_tools",
                side_effect=registration,
            ),
        ):
            selected = complete(profiles.build_profiled_server("codegraph"))
        self.assertEqual(
            {t.name for t in complete(selected.list_tools())}, profiles.CODEGRAPH_TOOLS
        )
        for name in ("TEST_ONLY_future_factory_tool", "TEST_ONLY_future_transform_tool"):
            self.assertTrue(call(selected, name, {}).isError)
        self.assertEqual(calls, [])

    def test_missing_existing_or_new_required_tool_fails_closed(self):
        for missing in ("get_target", c.CAPABILITIES, "construct_cpp_sdk_v1"):

            def registration(server, missing=missing):
                register_codegraph_transform_tools(server)
                server.remove_tool(missing)

            with (
                self.subTest(tool=missing),
                patch(
                    "espos_mcp.codegraph_transform_tools.register_codegraph_transform_tools",
                    side_effect=registration,
                ),
                self.assertRaisesRegex(RuntimeError, "codegraph tools are unavailable"),
            ):
                complete(profiles.build_profiled_server("codegraph"))

    def test_invalid_profile_fails_before_factory(self):
        with patch(
            "espos_mcp.server.build_server", side_effect=AssertionError("factory")
        ) as factory:
            for value in ("", "CODEGRAPH", "codegraph/full", None, True, ["codegraph"], MARKER):
                with self.subTest(profile=repr(value)), self.assertRaises(ValueError):
                    complete(profiles.build_profiled_server(value))
            factory.assert_not_called()

    def test_profile_actual_sdk_capability_call_and_transform_rejection(self):
        selected = complete(profiles.build_profiled_server("codegraph"))
        result = call(selected, c.CAPABILITIES, {})
        self.assertFalse(result.isError)
        self.assertEqual(result.structuredContent["data"]["runtimeAvailability"], "Unverified")
        for name in c.OPERATIONS:
            result = call(selected, name, {"request": {"path": MARKER}})
            self.assertTrue(result.isError)
            self.assertEqual(result.structuredContent["error"]["code"], "InvalidArgument")
            self.assertNotIn(MARKER, result.model_dump_json())

    def test_actual_canonical_cli_three_profiles_default_remains_read_only(self):
        # Normal canonical import, no loader/overlay/module replacement.
        from espos_mcp import __main__ as cli

        self.assertEqual(cli.PROFILES, ("read-only", "full", "codegraph"))
        self.assertEqual(cli._make_parser().parse_args([]).profile, "read-only")
        for name in ("read-only", "full", "codegraph"):
            self.assertEqual(cli._make_parser().parse_args(["--profile", name]).profile, name)
        self.assertIs(cli.build_profiled_server, profiles.build_profiled_server)


if __name__ == "__main__":
    unittest.main(verbosity=2)
