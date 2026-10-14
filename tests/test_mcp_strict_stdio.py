"""Canonical transport-file regressions; BytesIO is not live stdio proof."""

import io
import json
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from mcp import types

from espos_mcp import strict_stdio as ingress


class StrictStdioRegression(unittest.TestCase):
    def test_duplicate_keys_rejected_before_sdk_with_no_tail_loss(self):
        bad_frames = (
            b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}\n',
            b'{"jsonrpc":"2.0","id":1,"\\u0069d":2,"method":"ping"}\n',
            b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"_meta":{"x":1,"x":2}}}\n',
        )
        valid = b'{"jsonrpc":"2.0","id":3,"method":"ping"}\n'
        for bad in bad_frames:
            with self.subTest(frame=bad):
                sink = io.BytesIO()
                output = ingress.BoundedTextOutput(sink)
                reader = ingress.StrictTextInput(io.BytesIO(bad + valid), output)
                self.assertEqual(reader.readline(), "null\n")
                self.assertEqual(reader.readline().encode(), valid)
                self.assertEqual(sink.getvalue(), b"")
                reader.close()
                output.close()

    def test_valid_bytes_and_json_looking_strings_not_normalized(self):
        line = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "ping",
                    "params": {"_meta": {"literal": '{"x":1,"x":2}', "label": "e\u0301漢"}},
                },
                ensure_ascii=False,
            ).encode()
            + b"\r\n"
        )
        self.assertEqual(ingress.admit_frame(line), ("forward", line.decode()))

    def test_invalid_params_correlated_error_and_notification_silence(self):
        request = b'{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":[]}}\n'
        action, text = ingress.admit_frame(request)
        self.assertEqual(action, "reply")
        response = types.JSONRPCMessage.model_validate_json(text).root
        self.assertIsInstance(response, types.JSONRPCError)
        self.assertEqual(response.id, 42)
        self.assertEqual(response.error.code, types.INVALID_PARAMS)
        self.assertEqual(
            ingress.admit_frame(
                b'{"jsonrpc":"2.0","method":"notifications/cancelled","params":{"requestId":[]}}\n'
            ),
            ("drop", None),
        )

    def test_oversize_input_terminal_without_suffix_reinterpretation(self):
        raw = io.BytesIO(
            b"x" * (ingress.MAX_INPUT_FRAME_BYTES + 2) + b"\n"
            b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n'
        )
        output = ingress.BoundedTextOutput(io.BytesIO())
        reader = ingress.StrictTextInput(raw, output)
        with self.assertRaises(ingress.StdioBoundaryError):
            reader.readline()
        position = raw.tell()
        with self.assertRaises(ingress.StdioBoundaryError):
            reader.readline()
        self.assertEqual(raw.tell(), position)
        self.assertEqual(position, ingress.MAX_INPUT_FRAME_BYTES + 1)
        reader.close()
        output.close()

    def test_partial_write_failure_preserves_bytes_and_never_replays(self):
        class PartialThenFailed(io.BytesIO):
            calls = 0

            def write(self, data):
                self.calls += 1
                if self.calls == 1:
                    return super().write(data[:3])
                raise OSError("TEST_ONLY failure")

        sink = PartialThenFailed()
        output = ingress.BoundedTextOutput(sink)
        with self.assertRaises(ingress.StdioBoundaryError):
            output.write('{"jsonrpc":"2.0","id":1,"result":{}}\n')
        self.assertEqual(sink.getvalue(), b'{"j')
        with self.assertRaises(ingress.StdioBoundaryError):
            output.write("{}\n")
        self.assertEqual(sink.calls, 2)
        self.assertEqual(sink.getvalue(), b'{"j')
        output.close()

    def test_closing_wrappers_does_not_close_process_owned_handles(self):
        binary, sink = io.BytesIO(), io.BytesIO()
        output = ingress.BoundedTextOutput(sink)
        reader = ingress.StrictTextInput(binary, output)
        reader.close()
        output.close()
        self.assertFalse(binary.closed)
        self.assertFalse(sink.closed)


if __name__ == "__main__":
    unittest.main()
