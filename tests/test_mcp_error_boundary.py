"""Deferred actual-SDK regressions; no transport/event loop/child process.

Only the five real read-only adapters are registered. TEST_ONLY fixtures below
model exceptions/output bugs, NOT production operations or native receipts.
The private handler lookup is a version-bound TEST seam, never a product patch.
run_review.py selects the real baseline or candidate factory before collection.
"""

import inspect
import json
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult
from pydantic import StrictStr

from espos_mcp import codegraph_readonly, discovery
from espos_mcp.codegraph_tools import register_codegraph_tools
from espos_mcp.discovery_tools import register_discovery_tools
from espos_mcp.error_boundary import RedactedToolErrorsFastMCP

SERVER_CLASS = RedactedToolErrorsFastMCP
PUBLIC_TOOL_FAILURE = (
    "Tool request could not be completed. Do not automatically retry; "
    "an operation may already have started."
)
SENTINEL = "TEST_ONLY_SENTINEL_C:/not-a-real-secret/žluťoučký_123"


def complete(coroutine):
    """Drive actual no-suspension SDK call chains, never simulate a scheduler."""
    if not inspect.iscoroutine(coroutine):
        raise AssertionError("Expected an actual coroutine")
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError("Unexpected suspension; do not invent transport/event-loop proof")


def registered(factory=None):
    app = (factory or SERVER_CLASS)("TEST_ONLY_error_boundary")
    register_discovery_tools(app)
    register_codegraph_tools(app)
    return app


def call(app, name, arguments):
    request = CallToolRequest(params=CallToolRequestParams(name=name, arguments=arguments))
    # Executes the ACTUAL registered low-level SDK handler, including its error
    # formatting. Never replace it with a fabricated CallToolResult constructor.
    handler = app._mcp_server.request_handlers[CallToolRequest]
    result = complete(handler(request)).root
    if not isinstance(result, CallToolResult):
        raise AssertionError("Expected actual SDK CallToolResult")
    return result


class ToolErrorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.app = registered()

    def assert_redacted(self, result):
        self.assertTrue(result.isError)
        self.assertIsNone(result.structuredContent)
        self.assertEqual(len(result.content), 1)
        self.assertEqual(result.content[0].text, PUBLIC_TOOL_FAILURE)
        wire = result.model_dump_json(by_alias=True, exclude_none=True)
        self.assertNotIn(SENTINEL, wire)
        self.assertNotIn("input_value", wire)
        self.assertNotIn("Traceback", wire)
        self.assertLess(len(wire.encode("utf-8")), 256)

    def test_rejected_target_type_does_not_echo_nested_input(self):
        self.assert_redacted(call(self.app, "get_target", {"target_id": {"value": SENTINEL}}))

    def test_missing_required_argument_does_not_echo_other_fields(self):
        self.assert_redacted(call(self.app, "get_target", {"caller_path": SENTINEL}))

    def test_pagination_type_errors_do_not_echo_input(self):
        for name in ("list_targets", "list_sdk_nodes_v1"):
            for value in (SENTINEL, {"path": SENTINEL}, [SENTINEL], True):
                with self.subTest(tool=name, kind=type(value).__name__):
                    self.assert_redacted(call(self.app, name, {"offset": value}))

    def test_codegraph_outer_request_type_and_missing_field(self):
        for args in ({"request": SENTINEL}, {"request": [SENTINEL]}, {"path": SENTINEL}):
            with self.subTest(kind=type(args.get("request")).__name__):
                self.assert_redacted(call(self.app, "analyze_cpp_v1", args))

    def test_unknown_tool_name_not_echoed_in_public_result(self):
        self.assert_redacted(call(self.app, SENTINEL, {}))

    def test_long_and_unicode_rejected_values_do_not_expand_error(self):
        for value in (SENTINEL * 4096, "TEST_ONLY_漢字🧰", "TEST_ONLY_\ud800"):
            with self.subTest(length=len(value)):
                self.assert_redacted(call(self.app, "list_targets", {"limit": value}))

    def test_sync_exception_not_echoed_and_no_retry(self):
        calls = []

        @self.app.tool()
        def TEST_ONLY_raises(value: str) -> str:
            calls.append(value)
            raise RuntimeError(value)

        self.assert_redacted(call(self.app, "TEST_ONLY_raises", {"value": SENTINEL}))
        self.assertEqual(calls, [SENTINEL])

    def test_async_exception_not_echoed_and_no_retry(self):
        calls = []

        @self.app.tool()
        async def TEST_ONLY_async_raises(value: str) -> str:
            calls.append(value)
            raise RuntimeError(value)

        self.assert_redacted(call(self.app, "TEST_ONLY_async_raises", {"value": SENTINEL}))
        self.assertEqual(calls, [SENTINEL])

    def test_sdk_output_validation_error_is_redacted(self):
        @self.app.tool(structured_output=True)
        def TEST_ONLY_bad_output() -> dict[str, int]:
            return {"value": SENTINEL}

        self.assert_redacted(call(self.app, "TEST_ONLY_bad_output", {}))

    def test_tool_body_not_reached_on_actual_sdk_validation_error(self):
        calls = []

        @self.app.tool()
        def TEST_ONLY_strict(value: StrictStr) -> str:
            calls.append(value)
            return value

        self.assert_redacted(call(self.app, "TEST_ONLY_strict", {"value": [SENTINEL]}))
        self.assertEqual(calls, [])

    def test_baseexception_still_propagates(self):
        class TEST_ONLY_Stop(BaseException):
            pass

        @self.app.tool()
        def TEST_ONLY_stop() -> str:
            raise TEST_ONLY_Stop()

        with self.assertRaises(TEST_ONLY_Stop):
            call(self.app, "TEST_ONLY_stop", {})


class AdapterCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.app = registered()

    def test_real_registry_success_matches_unchanged_adapter(self):
        result = call(self.app, "get_target", {"target_id": "tab5_1280x720"})
        self.assertFalse(result.isError)
        self.assertEqual(result.structuredContent, discovery.target_receipt("tab5_1280x720"))
        self.assertEqual(result.structuredContent["data"]["target"]["codegen"], "unavailable")

    def test_existing_application_errors_keep_structured_contract(self):
        cases = [
            (
                "get_target",
                {"target_id": "../TEST_ONLY_bad"},
                discovery.target_receipt("../TEST_ONLY_bad"),
            ),
            ("list_targets", {"limit": 0}, discovery.targets_receipt(limit=0)),
            ("list_sdk_nodes_v1", {"limit": 0}, codegraph_readonly.catalog_receipt(limit=0)),
            ("analyze_cpp_v1", {"request": {}}, codegraph_readonly.analyze_receipt({})),
        ]
        for name, args, expected in cases:
            with self.subTest(tool=name):
                result = call(self.app, name, args)
                self.assertTrue(result.isError)
                self.assertEqual(result.structuredContent, expected)
                self.assertEqual(json.loads(result.content[0].text), expected)

    def test_no_tool_schema_annotation_inventory_change(self):
        baseline = complete(registered(FastMCP).list_tools())
        candidate = complete(self.app.list_tools())
        self.assertEqual([t.model_dump() for t in candidate], [t.model_dump() for t in baseline])
        self.assertEqual(len(candidate), 5)

    def test_text_plus_structured_are_one_result_not_two_responses(self):
        result = call(self.app, "list_targets", {"limit": 1})
        body = json.loads(result.model_dump_json(by_alias=True, exclude_none=True))
        self.assertEqual(len(body["content"]), 1)
        self.assertEqual(json.loads(body["content"][0]["text"]), body["structuredContent"])
        # Structured receipt bound is NOT the bound of this serialized MCP body.
        structured = discovery._json(body["structuredContent"]).encode("utf-8")
        self.assertGreater(len(result.model_dump_json().encode("utf-8")), len(structured))

    def test_get_capabilities_inventory_uses_real_registered_tools(self):
        result = call(self.app, "get_capabilities", {})
        self.assertFalse(result.isError)
        names = [tool.name for tool in complete(self.app.list_tools())]
        self.assertEqual(result.structuredContent["data"]["registeredTools"], sorted(names))
