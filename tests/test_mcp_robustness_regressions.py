"""Bounded source regressions, not server/interop/native-parser evidence.

BytesIO and explicitly named TEST_ONLY sentinels are memory-only fixtures.
Closed-wrapper expectations are ordinary regressions: canonical failures must
remain failures until the application-owned transport is separately corrected.
Private SDK handler lookup is a READ-only, version-bound test seam. Real SDK
coroutines must complete without suspension; no scheduler/outcome is invented.
"""

import base64
import hashlib
import inspect
import io
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from contextlib import ExitStack
from unittest.mock import patch

from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult

from espos_mcp import codegraph_readonly as code
from espos_mcp import strict_stdio as transport
from espos_mcp.error_boundary import PUBLIC_TOOL_FAILURE
from espos_mcp.profiles import READ_ONLY_TOOLS, build_profiled_server
from espos_mcp.sdk_diagnostics import cli_sdk_diagnostics
from espos_mcp.server import build_server

PING = b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
MARKER = "TEST_ONLY_not_a_user_file_漢e\u0301"


def complete(coroutine):
    if not inspect.iscoroutine(coroutine):
        raise AssertionError("Actual SDK coroutine required")
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError("Unexpected suspension; source evidence is insufficient")


def call(server, name, arguments):
    request = CallToolRequest(params=CallToolRequestParams(name=name, arguments=arguments))
    handler = server._mcp_server.request_handlers[CallToolRequest]
    result = complete(handler(request)).root
    if not isinstance(result, CallToolResult):
        raise AssertionError("Actual registered SDK result required")
    return result


def request(raw):
    return {"sourceBase64": base64.b64encode(raw).decode("ascii"), "entries": []}


def exact_frame(size, ending=b"\n"):
    prefix = b'{"jsonrpc":"2.0","id":7,"method":"ping","params":{"_meta":{"literal":"'
    suffix = b'"}}}' + ending
    unicode_part = "漢e\u0301".encode("utf-8")
    padding = size - len(prefix) - len(suffix) - len(unicode_part)
    if padding < 0:
        raise AssertionError("Invalid fixed test size")
    return prefix + unicode_part + b"x" * padding + suffix


class TransportRobustnessTests(unittest.TestCase):
    def test_exact_input_byte_cap_lf_and_crlf_preserves_multibyte_text(self):
        for ending in (b"\n", b"\r\n"):
            with self.subTest(ending=repr(ending)):
                raw = exact_frame(transport.MAX_INPUT_FRAME_BYTES, ending)
                self.assertEqual(len(raw), transport.MAX_INPUT_FRAME_BYTES)
                self.assertEqual(transport.admit_frame(raw), ("forward", raw.decode("utf-8")))

    def test_over_cap_read_is_terminal_before_sdk_and_does_not_drain_tail(self):
        binary = io.BytesIO(exact_frame(transport.MAX_INPUT_FRAME_BYTES + 1) + PING)
        output = transport.BoundedTextOutput(io.BytesIO())
        reader = transport.StrictTextInput(binary, output)
        with patch.object(
            transport.types.JSONRPCMessage,
            "model_validate_json",
            side_effect=AssertionError("TEST_ONLY SDK must not run"),
        ) as sdk:
            with self.assertRaises(transport.StdioBoundaryError):
                reader.readline()
            position = binary.tell()
            with self.assertRaises(transport.StdioBoundaryError):
                reader.readline()
            sdk.assert_not_called()
        self.assertEqual(position, transport.MAX_INPUT_FRAME_BYTES + 1)
        self.assertEqual(binary.tell(), position)
        reader.close()
        output.close()

    def test_large_escaped_duplicate_is_rejected_before_sdk_without_echo(self):
        raw = (
            b'{"jsonrpc":"2.0","id":7,"method":"ping","params":{"_meta":{'
            b'"x":"' + b"z" * 300000 + b'","\\u0078":"TEST_ONLY_rejected"}}}\n'
        )
        with patch.object(
            transport.types.JSONRPCMessage,
            "model_validate_json",
            side_effect=AssertionError("TEST_ONLY SDK must not run"),
        ) as sdk:
            self.assertEqual(transport.admit_frame(raw), ("reject", "null\n"))
            sdk.assert_not_called()

    def test_nonfinite_and_huge_integer_json_reject_before_sdk(self):
        values = (b"NaN", b"Infinity", b"-Infinity", b"1e9999", b"9" * 10000)
        for value in values:
            with self.subTest(kind=value[:12]):
                raw = (
                    b'{"jsonrpc":"2.0","id":7,"method":"ping","params":{"_meta":{"x":'
                    + value
                    + b"}}}\n"
                )
                with patch.object(
                    transport.types.JSONRPCMessage,
                    "model_validate_json",
                    side_effect=AssertionError("TEST_ONLY SDK must not run"),
                ) as sdk:
                    self.assertEqual(transport.admit_frame(raw), ("reject", "null\n"))
                    sdk.assert_not_called()

    def test_deep_valid_json_rejects_at_actual_admission_and_retains_valid_tail(self):
        # A JSON depth cap is NOT an application-owned strict-JSON contract.
        # The stdlib may admit this syntax; the actual SDK still parses/rejects.
        # Never replace SDK parsing with a rejection mock in this case.
        value = b"[" * 2000 + b"0" + b"]" * 2000
        raw = b'{"jsonrpc":"2.0","id":7,"method":"ping","params":{"_meta":{"x":' + value + b"}}}\n"
        output = transport.BoundedTextOutput(io.BytesIO())
        reader = transport.StrictTextInput(io.BytesIO(raw + PING), output)
        self.assertEqual(reader.readline(), "null\n")
        self.assertEqual(reader.readline().encode("utf-8"), PING)
        reader.close()
        output.close()

    def test_malformed_large_line_does_not_consume_next_valid_request(self):
        sink = io.BytesIO()
        output = transport.BoundedTextOutput(sink)
        binary = io.BytesIO(b'{"TEST_ONLY":' + b"x" * 300000 + b"}\n" + PING)
        reader = transport.StrictTextInput(binary, output)
        self.assertEqual(reader.readline(), "null\n")
        self.assertEqual(reader.readline().encode("utf-8"), PING)
        self.assertEqual(reader.readline(), "")
        self.assertEqual(sink.getvalue(), b"")
        reader.close()
        output.close()

    def test_invalid_utf8_is_not_replaced_and_valid_tail_remains(self):
        output = transport.BoundedTextOutput(io.BytesIO())
        reader = transport.StrictTextInput(io.BytesIO(b'"\xff"\n' + PING), output)
        self.assertEqual(reader.readline(), "null\n")
        self.assertEqual(reader.readline().encode("utf-8"), PING)
        reader.close()
        output.close()

    def test_valid_escaped_spelling_json_looking_code_and_crlf_remain_exact(self):
        raw = (
            b'{ "jsonrpc":"2.0", "id":7, "method":"ping", "params":{"_meta":'
            b'{"literal":"{\\"x\\":1,\\"x\\":2}","code":"\\u0065\\u0301\\r\\n",'
            b'"path":"TEST_ONLY_a\\\\b"}}}\r\n'
        )
        action, forwarded = transport.admit_frame(raw)
        self.assertEqual(action, "forward")
        self.assertEqual(forwarded.encode("utf-8"), raw)

    def test_exact_output_byte_cap_preserves_utf8_and_reports_character_count(self):
        raw = b'{"value":"' + "漢".encode()
        suffix = b'"}\n'
        raw += b"x" * (transport.MAX_OUTPUT_FRAME_BYTES - len(raw) - len(suffix)) + suffix
        sink = io.BytesIO()
        output = transport.BoundedTextOutput(sink)
        self.assertEqual(output.write(raw.decode("utf-8")), len(raw.decode("utf-8")))
        self.assertEqual(sink.getvalue(), raw)
        output.close()

    def test_oversize_output_is_sticky_and_writes_no_following_frame(self):
        sink = io.BytesIO()
        output = transport.BoundedTextOutput(sink)
        with self.assertRaises(transport.StdioBoundaryError):
            output.write("x" * transport.MAX_OUTPUT_FRAME_BYTES + "\n")
        with self.assertRaises(transport.StdioBoundaryError):
            output.write("{}\n")
        self.assertEqual(sink.getvalue(), b"")
        output.close()

    def test_surrogate_and_embedded_line_output_fail_without_partial_bytes(self):
        for value in ('"\ud800"\n', "{}\n{}\n", "{}"):
            with self.subTest(kind=ascii(value)):
                sink = io.BytesIO()
                output = transport.BoundedTextOutput(sink)
                with self.assertRaises(transport.StdioBoundaryError):
                    output.write(value)
                with self.assertRaises(transport.StdioBoundaryError):
                    output.write("{}\n")
                self.assertEqual(sink.getvalue(), b"")
                output.close()

    def test_short_successful_writes_preserve_bytes_without_frame_replay(self):
        class TEST_ONLY_ShortSink(io.BytesIO):
            def write(self, raw):
                return super().write(raw[:3])

        sink = TEST_ONLY_ShortSink()
        output = transport.BoundedTextOutput(sink)
        self.assertEqual(output.write(PING.decode()), len(PING))
        self.assertEqual(sink.getvalue(), PING)
        output.close()

    def test_closed_reader_cannot_consume_process_owned_input(self):
        binary = io.BytesIO(PING)
        output = transport.BoundedTextOutput(io.BytesIO())
        reader = transport.StrictTextInput(binary, output)
        reader.close()
        rejected = False
        try:
            reader.readline()
        except (ValueError, transport.StdioBoundaryError):
            rejected = True
        output.close()
        self.assertFalse(binary.closed)
        self.assertEqual(
            (reader.closed, binary.tell(), rejected),
            (True, 0, True),
            "Closed wrapper must reject before consuming process-owned bytes",
        )

    def test_closed_writer_cannot_append_to_process_owned_output(self):
        sink = io.BytesIO()
        output = transport.BoundedTextOutput(sink)
        output.close()
        rejected = False
        try:
            output.write(PING.decode())
        except (ValueError, transport.StdioBoundaryError):
            rejected = True
        self.assertFalse(sink.closed)
        self.assertEqual(
            (output.closed, len(sink.getvalue()), rejected),
            (True, 0, True),
            "Closed wrapper must reject before appending process-owned bytes",
        )


class SourceByteBoundaryTests(unittest.TestCase):
    def reject_without_backend(self, value, expected):
        with (
            patch.object(
                code, "_libraries", side_effect=AssertionError("TEST_ONLY backend forbidden")
            ) as libraries,
            patch.object(
                code,
                "_parser_dependencies",
                side_effect=AssertionError("TEST_ONLY native forbidden"),
            ) as native,
        ):
            result = code.analyze_receipt(value)
            libraries.assert_not_called()
            native.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], expected)
        self.assertIsNone(result["error"]["sourceIdentity"])
        self.assertLess(len(code.json_text(result).encode("utf-8")), 512)
        self.assertNotIn(MARKER, code.json_text(result))

    def test_exact_raw_cap_bom_crlf_opaque_code_unicode_remains_authoritative(self):
        # Unsupported-looking C++ is a BYTE fixture, not a fabricated opaque graph.
        prefix = (
            '\ufeff#if TEST_ONLY\r\n// e\u0301漢\r\nauto x = R"tag({"x":1,"x":2})tag";\r\n'
        ).encode("utf-8")
        raw = prefix + b" " * (code.MAX_SOURCE_BYTES - len(prefix))
        supplied = request(raw)
        actual, context, observation = code._analyze_input(supplied)
        self.assertEqual(actual, raw)
        self.assertEqual(base64.b64encode(actual).decode(), supplied["sourceBase64"])
        self.assertEqual(code._identity(actual)["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(code._identity(actual)["byteLength"], code.MAX_SOURCE_BYTES)
        self.assertEqual(context, {"entries": []})
        self.assertIsNone(observation)

    def test_decoded_cap_plus_one_rejects_even_when_encoded_size_fits(self):
        value = request(b"x" * (code.MAX_SOURCE_BYTES + 1))
        self.assertEqual(len(value["sourceBase64"]), code.MAX_SOURCE_BASE64)
        self.reject_without_backend(value, "LimitExceeded")

    def test_encoded_cap_plus_one_rejects_before_base64_decode(self):
        value = {"sourceBase64": "A" * (code.MAX_SOURCE_BASE64 + 1), "entries": []}
        with patch.object(
            code.base64, "b64decode", side_effect=AssertionError("TEST_ONLY decode forbidden")
        ) as decode:
            self.reject_without_backend(value, "LimitExceeded")
            decode.assert_not_called()

    def test_noncanonical_padding_and_base64_whitespace_reject(self):
        for encoded in ("Zh==", "Zg==\n", " Zg==", "Zg", "Zg==="):
            with self.subTest(encoded=encoded):
                self.reject_without_backend(
                    {"sourceBase64": encoded, "entries": []}, "InvalidArgument"
                )

    def test_invalid_utf8_source_is_not_replaced_or_backend_analyzed(self):
        for raw in (b"\xff", b"\xef\xbb\xbf\xc3", b"\xed\xa0\x80"):
            with self.subTest(raw=raw):
                self.reject_without_backend(request(raw), "InvalidArgument")

    def test_structured_utf8_total_limit_is_distinct_from_source_and_field_caps(self):
        value = request(b"x" * code.MAX_SOURCE_BYTES)
        label = "漢" * code.MAX_TEXT_CHARACTERS
        value["bindings"] = {
            "callee" + str(i): {
                "operation": label,
                "returnType": label,
                "parameterTypes": [label] * code.MAX_PARAMETERS,
            }
            for i in range(code.MAX_BINDINGS)
        }
        self.assertGreater(len(code.json_text(value).encode("utf-8")), code.MAX_REQUEST_BYTES)
        self.reject_without_backend(value, "LimitExceeded")

    def test_context_and_observation_are_detached_without_source_normalization(self):
        raw = "\ufeffvoid f(){}\r\n// e\u0301漢\r\n".encode("utf-8")
        value = request(raw)
        value.update(
            entries=["f"],
            bindings={
                "callee": {"operation": "TEST_ONLY", "returnType": "int", "parameterTypes": ["int"]}
            },
            eventBindings={"f": "TEST_ONLY_event"},
            observation={"documentId": "TEST_ONLY", "revision": 0, "targetId": "TEST_ONLY"},
        )
        actual, context, observation = code._analyze_input(value)
        value["entries"].append("other")
        value["bindings"]["callee"]["parameterTypes"].append("bool")
        value["eventBindings"]["f"] = "changed"
        value["observation"]["revision"] = 1
        self.assertEqual(actual, raw)
        self.assertEqual(context["entries"], ["f"])
        self.assertEqual(context["bindings"]["callee"]["parameterTypes"], ["int"])
        self.assertEqual(context["eventBindings"], {"f": "TEST_ONLY_event"})
        self.assertEqual(observation["revision"], 0)


class DisabledToolAdmissionTests(unittest.TestCase):
    def assert_redacted(self, result):
        self.assertTrue(result.isError)
        self.assertIsNone(result.structuredContent)
        self.assertEqual([item.text for item in result.content], [PUBLIC_TOOL_FAILURE])
        wire = result.model_dump_json(by_alias=True, exclude_none=True)
        self.assertLess(len(wire.encode("utf-8")), 256)
        self.assertNotIn(MARKER, wire)

    def test_all_seventeen_disabled_tools_reject_large_malformed_arguments_before_body(self):
        full = build_server()
        removed = {tool.name for tool in complete(full.list_tools())} - READ_ONLY_TOOLS
        server = complete(build_profiled_server())
        payload = {"path": MARKER * 8192, "request": [MARKER] * 256, "limit": {"bad": MARKER}}
        # Tripwires guard application-owned effects only; SDK registry/handler
        # and returned result remain actual. Never invoke disabled tool bodies.
        with ExitStack() as stack:
            effects = [
                stack.enter_context(
                    patch(
                        "espos_mcp.server." + name,
                        side_effect=AssertionError("TEST_ONLY effect forbidden"),
                    )
                )
                for name in (
                    "_resolve_design_path",
                    "_load_designer",
                    "_atomic_save",
                    "_write_dict",
                    "build_board",
                    "flash_board",
                    "export_header",
                    "export_svg",
                )
            ]
            diagnostics = io.StringIO()
            stack.enter_context(cli_sdk_diagnostics(stream=diagnostics))
            for name in sorted(removed):
                with self.subTest(tool=name):
                    self.assert_redacted(call(server, name, payload))
            for effect in effects:
                effect.assert_not_called()
        self.assertEqual(len(removed), 17)
        self.assertNotIn(MARKER, diagnostics.getvalue())
        self.assertEqual({tool.name for tool in complete(server.list_tools())}, READ_ONLY_TOOLS)
        self.assertEqual(len(complete(build_server().list_tools())), 22)

    def test_readonly_validation_rejects_large_bad_types_before_application_body(self):
        server = complete(build_profiled_server())
        cases = (
            ("get_target", {"target_id": {"bad": MARKER * 8192}}),
            ("list_targets", {"limit": [MARKER] * 4096}),
            ("analyze_cpp_v1", {"request": MARKER * 8192}),
        )
        with ExitStack() as stack:
            bodies = [
                stack.enter_context(
                    patch(path, side_effect=AssertionError("TEST_ONLY body forbidden"))
                )
                for path in (
                    "espos_mcp.codegraph_readonly.analyze_receipt",
                    "espos_mcp.discovery.target_receipt",
                    "espos_mcp.discovery.targets_receipt",
                )
            ]
            stack.enter_context(cli_sdk_diagnostics(stream=io.StringIO()))
            for name, args in cases:
                with self.subTest(tool=name):
                    self.assert_redacted(call(server, name, args))
            for body in bodies:
                body.assert_not_called()

    def test_large_unknown_name_is_not_echoed_in_result_or_cli_sdk_diagnostic(self):
        server = complete(build_profiled_server())
        diagnostics = io.StringIO()
        with cli_sdk_diagnostics(stream=diagnostics):
            self.assert_redacted(call(server, MARKER * 8192, {"bad": MARKER}))
        self.assertNotIn(MARKER, diagnostics.getvalue())
        self.assertTrue(
            all(len(line.encode()) <= 48 for line in diagnostics.getvalue().splitlines(True))
        )

    def test_large_or_wrong_typed_profile_fails_before_factory_without_full_fallback(self):
        with patch(
            "espos_mcp.server.build_server",
            side_effect=AssertionError("TEST_ONLY factory forbidden"),
        ) as factory:
            for value in (MARKER * 8192, ["full"], {"profile": "full"}, True):
                with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                    complete(build_profiled_server(value))
            factory.assert_not_called()

    def test_future_tool_removed_then_denied_with_large_input_without_body_entry(self):
        server = build_server()
        entered = []

        @server.tool()
        def TEST_ONLY_future_mutation(value: str) -> str:
            entered.append(value)
            raise AssertionError("TEST_ONLY future body forbidden")

        with patch("espos_mcp.server.build_server", return_value=server):
            restricted = complete(build_profiled_server())
        with cli_sdk_diagnostics(stream=io.StringIO()):
            self.assert_redacted(
                call(restricted, "TEST_ONLY_future_mutation", {"value": MARKER * 8192})
            )
        self.assertEqual(entered, [])
        self.assertEqual({tool.name for tool in complete(restricted.list_tools())}, READ_ONLY_TOOLS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
