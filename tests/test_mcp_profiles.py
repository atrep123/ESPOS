"""Real factory/SDK dispatch checks; no stdio, device, parser or write run."""

import inspect
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from functools import wraps
from unittest.mock import patch

from espos_mcp.profiles import READ_ONLY_TOOLS, build_profiled_server
from espos_mcp.server import build_server


def source_coroutine_test(function):
    """Drive the actual synchronous SDK paths without Windows loop IPC.

    Any real suspension is a failed test, not a mocked asynchronous outcome.
    Live stdio verification is separate; these registry paths require no loop.
    """

    @wraps(function)
    def run(self):
        coroutine = function(self)
        self.assertTrue(inspect.iscoroutine(coroutine))
        try:
            coroutine.send(None)
        except StopIteration:
            return
        finally:
            coroutine.close()
        self.fail("Unexpected suspension; registry source check needs live verification")

    return run


class ProfileTests(unittest.TestCase):
    @source_coroutine_test
    async def test_default_is_server_enforced_read_only(self):
        server = await build_profiled_server()
        self.assertEqual({t.name for t in await server.list_tools()}, READ_ONLY_TOOLS)

    @source_coroutine_test
    async def test_full_preserves_same_factory_inventory_and_schemas(self):
        expected = [t.model_dump() for t in await build_server().list_tools()]
        actual = [t.model_dump() for t in await (await build_profiled_server("full")).list_tools()]
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 22)

    @source_coroutine_test
    async def test_removed_tools_cannot_be_called_directly(self):
        full = build_server()
        removed = {t.name for t in await full.list_tools()} - READ_ONLY_TOOLS
        server = await build_profiled_server()
        # Unknown-tool dispatch rejects before input validation or tool effects;
        # even a caller ignoring the advertised list cannot enter the handlers.
        with (
            patch("espos_mcp.server._atomic_save", side_effect=AssertionError("write")) as save,
            patch("espos_mcp.server._write_dict", side_effect=AssertionError("write")) as write,
            patch("espos_mcp.server.build_board", side_effect=AssertionError("build")) as build,
            patch("espos_mcp.server.flash_board", side_effect=AssertionError("flash")) as flash,
        ):
            for name in removed:
                with self.subTest(tool=name):
                    result = await server.call_tool(name, {})
                    self.assertTrue(result.isError)
            for effect in (save, write, build, flash):
                effect.assert_not_called()
        self.assertEqual(len(removed), 17)

    @source_coroutine_test
    async def test_inventory_does_not_poison_a_later_full_instance(self):
        await build_profiled_server()
        self.assertEqual(len(await build_server().list_tools()), 22)

    @source_coroutine_test
    async def test_invalid_profile_fails_before_factory(self):
        with patch("espos_mcp.server.build_server", side_effect=AssertionError("factory entered")):
            for value in ("", "readonly", "FULL", None, 1, ["full"]):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    await build_profiled_server(value)

    @source_coroutine_test
    async def test_missing_required_tool_cannot_fall_back_to_full(self):
        server = build_server()
        server.remove_tool("get_target")
        with (
            patch("espos_mcp.server.build_server", return_value=server),
            self.assertRaisesRegex(RuntimeError, "read-only tools are unavailable"),
        ):
            await build_profiled_server()

    @source_coroutine_test
    async def test_future_tool_is_removed_without_calling_its_body(self):
        server = build_server()
        calls = []

        @server.tool()
        def future_mutation() -> str:
            calls.append("entered")
            raise AssertionError("Unreviewed tool executed")

        with patch("espos_mcp.server.build_server", return_value=server):
            selected = await build_profiled_server()
        self.assertEqual({t.name for t in await selected.list_tools()}, READ_ONLY_TOOLS)
        self.assertTrue((await selected.call_tool("future_mutation", {})).isError)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
