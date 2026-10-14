"""Real CLI/factory/SDK checks, with TEST_ONLY application transport seams.

No SDK method is replaced. The synchronous registry/dispatch coroutine paths
must finish in one step; suspension fails instead of fabricating a scheduler.
These tests do not execute an event loop, live stdio, a device or a writer.
"""

import inspect
import io
import logging
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from mcp.types import CallToolRequest, CallToolRequestParams

from espos_mcp import __main__ as cli
from espos_mcp import sdk_diagnostics, strict_stdio
from espos_mcp import server as factory
from espos_mcp.profiles import READ_ONLY_TOOLS


def complete(coroutine):
    """TEST_ONLY actual coroutine execution; unexpected suspension is RED."""
    if not inspect.iscoroutine(coroutine):
        raise AssertionError("Expected an actual startup/SDK coroutine")
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError("Unexpected suspension; no event-loop proof is claimed")


def inventory(server):
    return complete(server.list_tools())


def call(server, name, arguments):
    request = CallToolRequest(params=CallToolRequestParams(name=name, arguments=arguments))
    # TEST_ONLY version-bound lookup executes the actual SDK handler unchanged.
    return complete(server._mcp_server.request_handlers[CallToolRequest](request)).root


class CliProfileTests(unittest.TestCase):
    def setUp(self):
        root = logging.getLogger()
        self.root_handlers, self.root_level = tuple(root.handlers), root.level
        self.application_log = io.StringIO()
        self.application_handler = logging.StreamHandler(self.application_log)
        root.handlers = [self.application_handler]
        root.setLevel(logging.INFO)
        startup_patch = patch.object(cli, "_run_startup", side_effect=complete)
        self.startup = startup_patch.start()
        self.addCleanup(startup_patch.stop)
        self.addCleanup(self.restore_logging)

    def restore_logging(self):
        logging.getLogger().handlers = list(self.root_handlers)
        logging.getLogger().setLevel(self.root_level)
        self.application_handler.close()

    def invoke(self, argv, consumer):
        """Replace only the CLI-owned blocking activation point, not the SDK."""
        stdout, stderr = io.StringIO(), io.StringIO()
        built = []
        original_factory = factory.build_server

        def record_factory():
            instance = original_factory()
            built.append(instance)
            return instance

        with (
            patch.object(factory, "build_server", side_effect=record_factory),
            patch.object(strict_stdio, "run_stdio", side_effect=consumer) as transport,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main(argv)
        self.assertEqual(len(built), 1)
        self.assertEqual(transport.call_count, 1)
        self.assertIs(transport.call_args.args[0], built[0])
        self.assertEqual(self.startup.call_count, 1)
        self.assertEqual(tuple(logging.getLogger().handlers), (self.application_handler,))
        self.assertFalse(sdk_diagnostics._ACTIVE)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_default_routes_one_actual_read_only_server_to_strict_transport(self):
        def consume(server):
            self.assertEqual({tool.name for tool in inventory(server)}, READ_ONLY_TOOLS)
            result = call(server, "get_capabilities", {})
            self.assertFalse(result.isError)
            self.assertEqual(
                result.structuredContent["data"]["registeredTools"], sorted(READ_ONLY_TOOLS)
            )

        code, stdout, _ = self.invoke([], consume)
        self.assertEqual((code, stdout), (0, ""))

    def test_explicit_read_only_uses_same_five(self):
        def consume(server):
            self.assertEqual({tool.name for tool in inventory(server)}, READ_ONLY_TOOLS)

        self.assertEqual(self.invoke(["--profile", "read-only"], consume)[0], 0)

    def test_explicit_full_retains_actual_22_schemas_and_capability_inventory(self):
        expected = [tool.model_dump() for tool in inventory(factory.build_server())]
        self.assertEqual(len(expected), 22)

        def consume(server):
            self.assertEqual([tool.model_dump() for tool in inventory(server)], expected)
            result = call(server, "get_capabilities", {})
            self.assertEqual(
                result.structuredContent["data"]["registeredTools"],
                sorted(tool["name"] for tool in expected),
            )

        self.assertEqual(self.invoke(["--profile", "full"], consume)[0], 0)

    def test_removed_direct_calls_are_denied_without_effect_dispatch(self):
        removed = {tool.name for tool in inventory(factory.build_server())} - READ_ONLY_TOOLS
        self.assertEqual(len(removed), 17)

        def consume(server):
            with (
                patch.object(factory, "_atomic_save", side_effect=AssertionError("write")) as save,
                patch.object(factory, "_write_dict", side_effect=AssertionError("write")) as write,
                patch.object(factory, "build_board", side_effect=AssertionError("build")) as build,
                patch.object(factory, "flash_board", side_effect=AssertionError("flash")) as flash,
            ):
                for name in sorted(removed):
                    with self.subTest(name=name):
                        self.assertTrue(call(server, name, {}).isError)
                for effect in (save, write, build, flash):
                    effect.assert_not_called()

        self.assertEqual(self.invoke([], consume)[0], 0)

    def check_listing(self, argv, expected):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(
                strict_stdio, "run_stdio", side_effect=AssertionError("live transport")
            ) as transport,
            patch.object(factory, "build_server", wraps=factory.build_server) as build,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main(argv)
        self.assertEqual(code, 0)
        self.assertEqual(build.call_count, 1)
        transport.assert_not_called()
        self.assertEqual(self.startup.call_count, 2)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(lines[0], f"espos MCP server — {len(expected)} tools:")
        names = [line.split()[0] for line in lines if line.startswith("  ")]
        self.assertEqual(names, sorted(expected))
        self.assertFalse(sdk_diagnostics._ACTIVE)

    def test_list_tools_default_has_five_and_never_serves(self):
        self.check_listing(["--list-tools"], READ_ONLY_TOOLS)

    def test_list_tools_explicit_read_only_has_five(self):
        self.check_listing(["--profile", "read-only", "--list-tools"], READ_ONLY_TOOLS)

    def test_list_tools_full_has_22_without_calling_any_tool(self):
        expected = {tool.name for tool in inventory(factory.build_server())}
        self.assertEqual(len(expected), 22)
        self.check_listing(["--list-tools", "--profile", "full"], expected)

    def test_invalid_profile_fails_before_factory_startup_and_transport(self):
        with (
            patch.object(factory, "build_server", side_effect=AssertionError("factory")) as build,
            patch.object(
                strict_stdio, "run_stdio", side_effect=AssertionError("transport")
            ) as transport,
        ):
            for argv in (
                ["--profile", "FULL"],
                ["--profile", ""],
                ["--list-tools", "--profile", "read-write"],
            ):
                with (
                    self.subTest(argv=argv),
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as stopped,
                ):
                    cli.main(argv)
                self.assertEqual(stopped.exception.code, 2)
            build.assert_not_called()
            transport.assert_not_called()
            self.startup.assert_not_called()

    def test_unsupported_transport_rejected_before_startup(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            cli.main(["--transport", "sse"])
        self.assertEqual(stopped.exception.code, 2)
        self.startup.assert_not_called()

    def test_help_exits_before_startup(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as stopped:
            cli.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("--profile {read-only,full,codegraph}", output.getvalue())
        self.assertIn("transformations without file writes", output.getvalue())
        self.startup.assert_not_called()

    def test_real_sdk_rejection_logs_fixed_diagnostics_and_keeps_application_logs(self):
        marker = "TEST_ONLY_CLI_CALLER_C:/synthetic/žluťoučký"

        def consume(server):
            result = call(server, marker, {})
            self.assertTrue(result.isError)
            self.assertNotIn(marker, result.model_dump_json())
            logging.getLogger("mcp.server.lowlevel.server").error("%s", marker)
            logging.getLogger("TEST_ONLY_application").warning("application unchanged")

        code, _, stderr = self.invoke([], consume)
        self.assertEqual(code, 0)
        self.assertNotIn(marker, stderr)
        self.assertNotIn(marker, self.application_log.getvalue())
        self.assertIn("application unchanged", self.application_log.getvalue())
        self.assertIn("WARNING MCP_SDK_SERVER\n", stderr)
        self.assertIn("ERROR MCP_SDK_SERVER\n", stderr)
        for line in stderr.splitlines(keepends=True):
            self.assertRegex(
                line,
                r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL|OTHER) MCP_SDK_(SERVER|SESSION|DIAGNOSTIC)\n$",
            )
            self.assertLessEqual(len(line.encode()), sdk_diagnostics.MAX_DIAGNOSTIC_LINE_BYTES)

    def test_strict_boundary_failure_is_fixed_and_diagnostics_restored(self):
        def fail(_server):
            raise strict_stdio.StdioBoundaryError("TEST_ONLY_not_public")

        code, _, stderr = self.invoke([], fail)
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "espos MCP stdio session failed; do not automatically retry.\n")

    def test_sdk_diagnostic_failure_is_fixed_and_restored(self):
        def fail(_server):
            raise sdk_diagnostics.SdkDiagnosticError("TEST_ONLY_not_public")

        code, _, stderr = self.invoke([], fail)
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "espos MCP SDK diagnostic output failed.\n")

    def test_keyboard_interrupt_settles_without_automatic_retry(self):
        def stop(_server):
            raise KeyboardInterrupt()

        code, _, stderr = self.invoke([], stop)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "espos MCP server stopped.\n")


if __name__ == "__main__":
    unittest.main()
