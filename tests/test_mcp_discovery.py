"""Behavioral discovery tests using the ACTUAL canonical target registry.
Only fault/size fixtures use TEST_ONLY monkeypatches. No fake MCP transport.
"""

import ast
import copy
import importlib.metadata
import json
import unittest

# Keep these executable as standalone unittest suites without a pytest import.
# ruff: noqa: PT009, PT027
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

import espos_targets
from espos_mcp import __version__
from espos_mcp import discovery as d
from ui_designer import HARDWARE_PROFILES


class DiscoveryBehavior(unittest.TestCase):
    def receipt(self, result, ok=True, code=None):
        d.DiscoveryReceipt.model_validate(result)
        self.assertEqual(result["schemaVersion"], 1)
        self.assertIs(result["ok"], ok)
        self.assertLessEqual(len(d._json(result).encode("utf-8")), d.MAX_RESPONSE_BYTES)
        if code:
            self.assertEqual(result["error"]["code"], code)
            self.assertIsNone(result["data"])
        else:
            self.assertIsNone(result["error"])
        return result["data"]

    def test_all_actual_profiles_are_unmodified_registry_serialization(self):
        expected = espos_targets.load_registry().to_dict()
        data = self.receipt(d.targets_receipt(limit=32))
        self.assertEqual(data["targets"], expected["profiles"])
        self.assertEqual([p["profile_id"] for p in data["targets"]], list(HARDWARE_PROFILES))
        self.assertEqual(data["registrySchemaVersion"], expected["schema_version"])
        self.assertIsNone(data["nextOffset"])

    def test_actual_tab5_truthful_declared_runtime_not_legacy_export(self):
        data = self.receipt(d.target_receipt("tab5_1280x720"))
        profile = data["target"]
        self.assertEqual(profile, espos_targets.load_registry().get("tab5_1280x720").to_dict())
        self.assertEqual((profile["width"], profile["height"]), (1280, 720))
        self.assertEqual((profile["input_kind"], profile["runtime"]), ("touch", "tabos_lvgl"))
        self.assertEqual(profile["codegen"], "unavailable")
        self.assertEqual(data["capabilityStatus"]["ui_scene_c_export"], "Unavailable")
        self.assertEqual(set(data["capabilityStatus"]), espos_targets.CAPABILITIES)

    def test_actual_reference_and_generic_are_distinct(self):
        ref = self.receipt(d.target_receipt("esp32os_256x128_gray4"))["target"]
        generic = self.receipt(d.target_receipt("tft_320x240"))["target"]
        self.assertEqual(
            (ref["input_kind"], ref["runtime"]), ("focus_navigation", "espos_ui_scene")
        )
        self.assertEqual(
            (generic["input_kind"], generic["runtime"]), ("unavailable", "unavailable")
        )
        self.assertEqual(generic["codegen"], "tools.ui_codegen")

    def test_every_target_matches_direct_actual_lookup(self):
        registry = espos_targets.load_registry()
        for target_id in registry.ids():
            with self.subTest(target=target_id):
                data = self.receipt(d.target_receipt(target_id))
                self.assertEqual(data["target"], registry.get(target_id).to_dict())
                self.assertEqual(
                    {n for n, v in data["capabilityStatus"].items() if v == "Available"},
                    set(registry.get(target_id).capabilities),
                )

    def test_pagination_is_lossless_stable_and_bounded(self):
        actual, offset, digests = [], 0, set()
        for _ in range(d.MAX_TARGETS):
            data = self.receipt(d.targets_receipt(offset, 3))
            actual.extend(data["targets"])
            digests.add(data["registryHash"])
            self.assertLessEqual(len(data["targets"]), 3)
            if data["nextOffset"] is None:
                break
            self.assertGreater(data["nextOffset"], offset)
            offset = data["nextOffset"]
        else:
            self.fail("pagination did not finish")
        self.assertEqual(actual, espos_targets.load_registry().to_dict()["profiles"])
        self.assertEqual(len(digests), 1)

    def test_empty_tail_page_is_not_unknown_target_success(self):
        data = self.receipt(d.targets_receipt(256, 32))
        self.assertEqual(data["targets"], [])
        self.assertIsNone(data["nextOffset"])
        self.receipt(d.target_receipt("not_registered"), False, "UnknownTarget")

    def test_unknown_valid_id_has_bounded_non_echoed_error(self):
        for name in ("tab5", "not_registered", "z" * d.MAX_TARGET_ID):
            with self.subTest(name=name[:15]):
                result = d.target_receipt(name)
                self.receipt(result, False, "UnknownTarget")
                self.assertNotIn(name, d._json(result))

    def test_board_id_is_not_an_implicit_target_alias(self):
        from board_registry import load_registry

        board = load_registry().boards[0]
        self.assertNotIn(board.id, espos_targets.load_registry().ids())
        self.receipt(d.target_receipt(board.id), False, "UnknownTarget")

    def test_bad_ids_rejected_before_any_registry_lookup(self):
        bad = [
            "",
            "../tab5_1280x720",
            "C:/tmp",
            "tab5;cmd",
            "$(whoami)",
            "tab5\n",
            " tab5_1280x720",
            "Tab5_1280x720",
            "a\x00b",
            "ž",
            "a" * 129,
            None,
            True,
            1,
            [],
        ]
        with patch.object(
            espos_targets, "load_registry", side_effect=AssertionError("TEST_ONLY no lookup")
        ):
            for name in bad:
                with self.subTest(name=repr(name)[:50]):
                    self.receipt(d.target_receipt(name), False, "InvalidArgument")

    def test_pagination_types_and_limits_reject_before_lookup(self):
        with patch.object(
            espos_targets, "load_registry", side_effect=AssertionError("TEST_ONLY no lookup")
        ):
            for offset, limit in [
                (-1, 1),
                (257, 1),
                (0, 0),
                (0, 33),
                (True, 1),
                (0, False),
                ("0", 1),
                (0, "2"),
                (1.0, 1),
                (0, None),
            ]:
                with self.subTest(offset=offset, limit=limit):
                    self.receipt(d.targets_receipt(offset, limit), False, "InvalidArgument")

    def test_actual_registry_unmodified_by_repeated_discovery(self):
        before = copy.deepcopy(HARDWARE_PROFILES)
        for _ in range(20):
            d.targets_receipt()
            d.target_receipt("tab5_1280x720")
        self.assertEqual(HARDWARE_PROFILES, before)

    def test_no_generated_simulator_or_hardware_capabilities(self):
        rows = self.receipt(d.targets_receipt(limit=32))["targets"]
        self.assertEqual(
            {c for row in rows for c in row["capabilities"]}, espos_targets.CAPABILITIES
        )
        for row in rows:
            self.assertNotIn("hardware_verified", row)
            self.assertNotIn("simulator", row)
            self.assertNotIn("studio", row)

    def test_version_and_inventory_receipt_thin_projection(self):
        # TEST_ONLY supplied inventory; real FastMCP inventory is tested only by stdio gate.
        names = ["test_only_beta", "test_only_alpha"]
        data = self.receipt(d.capabilities_receipt(names))
        self.assertEqual(data["registeredTools"], sorted(names))
        self.assertEqual(data["server"]["version"], __version__)
        self.assertEqual(data["server"]["mcpSdkVersion"], importlib.metadata.version("mcp"))
        self.assertEqual(data["registrySchemaVersion"], espos_targets.SCHEMA_VERSION)
        self.assertEqual(data["capabilityVocabulary"], sorted(espos_targets.CAPABILITIES))
        self.assertEqual(data["targetCount"], len(HARDWARE_PROFILES))
        self.assertNotIn("sdkCompatible", data["server"])

    def test_uninstalled_sdk_is_not_fabricated_version(self):
        with patch.object(
            d.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError
        ):
            self.assertIsNone(self.receipt(d.capabilities_receipt([]))["server"]["mcpSdkVersion"])

    def test_inventory_overflow_and_duplicates_are_not_silently_truncated(self):
        for names in (["x"] * 2, ["x" * 129], ["x" + str(n) for n in range(129)], [None], "x"):
            with self.subTest(size=len(names)):
                self.receipt(d.capabilities_receipt(names), False, "LimitExceeded")

    def test_registry_failure_is_unavailable_not_empty_success(self):
        with patch.object(
            espos_targets,
            "load_registry",
            side_effect=RuntimeError("TEST_ONLY secret path C:/private crash"),
        ):
            for result in (
                d.target_receipt("tab5_1280x720"),
                d.targets_receipt(),
                d.capabilities_receipt([]),
            ):
                self.receipt(result, False, "Unavailable")
                self.assertNotIn("private", d._json(result))

    def test_invalid_registry_uses_actual_registry_validator(self):
        actual = espos_targets.load_registry()
        with (
            patch.object(
                actual,
                "to_dict",
                return_value={
                    "schema_version": 1,
                    "profiles": [{"profile_id": "TEST_ONLY_INVALID"}],
                },
            ),
            patch.object(espos_targets, "load_registry", return_value=actual),
        ):
            self.receipt(d.targets_receipt(), False, "Unavailable")

    def test_too_many_real_profile_objects_are_bounded(self):
        base = espos_targets.load_registry().get("oled_128x64")
        fixture = espos_targets.TargetRegistry(
            replace(base, profile_id=f"test_only_{n}") for n in range(257)
        )
        with patch.object(espos_targets, "load_registry", return_value=fixture):
            self.receipt(d.targets_receipt(), False, "LimitExceeded")

    def test_oversized_valid_id_in_registry_is_explicit_limit(self):
        base = espos_targets.load_registry().get("oled_128x64")
        fixture = espos_targets.TargetRegistry([replace(base, profile_id="z" * 129)])
        with patch.object(espos_targets, "load_registry", return_value=fixture):
            self.receipt(d.targets_receipt(), False, "LimitExceeded")

    def test_oversized_registry_is_bounded_without_partial_success(self):
        base = espos_targets.load_registry().get("oled_128x64")
        fixture = espos_targets.TargetRegistry([replace(base, label="x" * d.MAX_REGISTRY_BYTES)])
        with patch.object(espos_targets, "load_registry", return_value=fixture):
            self.receipt(d.targets_receipt(), False, "LimitExceeded")

    def test_utf8_output_bound_counts_bytes_not_characters(self):
        base = espos_targets.load_registry().get("oled_128x64")
        fixture = espos_targets.TargetRegistry([replace(base, label="漢" * 23000)])
        with patch.object(espos_targets, "load_registry", return_value=fixture):
            for result in (d.targets_receipt(), d.target_receipt(base.profile_id)):
                self.receipt(result, False, "LimitExceeded")

    def test_unicode_registry_metadata_roundtrips_exactly(self):
        base = espos_targets.load_registry().get("oled_128x64")
        label = "TEST_ONLY Příliš žluťoučký / 漢字 / 🧰"
        fixture = espos_targets.TargetRegistry([replace(base, label=label)])
        with patch.object(espos_targets, "load_registry", return_value=fixture):
            data = self.receipt(d.target_receipt(base.profile_id))
            self.assertEqual(json.loads(d._json(data))["target"]["label"], label)

    def test_hash_changes_on_actual_metadata_change_no_cached_success(self):
        original = self.receipt(d.targets_receipt())["registryHash"]
        base = espos_targets.load_registry().get("oled_128x64")
        with patch.object(
            espos_targets,
            "load_registry",
            return_value=espos_targets.TargetRegistry([replace(base, label="TEST_ONLY")]),
        ):
            changed = self.receipt(d.targets_receipt())["registryHash"]
            self.assertNotEqual(original, changed)
            self.assertEqual(
                self.receipt(d.target_receipt(base.profile_id))["registryHash"], changed
            )
        self.assertEqual(self.receipt(d.targets_receipt())["registryHash"], original)

    def test_live_registry_lookup_not_separate_hardcoded_profile_model(self):
        base = espos_targets.load_registry().get("oled_128x64")
        extra = replace(base, profile_id="test_only_extension", width=321, height=123)
        with patch.object(
            espos_targets, "load_registry", return_value=espos_targets.TargetRegistry([extra])
        ):
            data = self.receipt(d.target_receipt(extra.profile_id))
            self.assertEqual(data["target"], extra.to_dict())

    def test_invalid_receipt_versions_and_success_error_mix_rejected(self):
        receipt = d.target_receipt("tab5_1280x720")
        for changes in (
            {"schemaVersion": 2},
            {"ok": False},
            {"error": {"code": "Unavailable", "message": "TEST_ONLY", "retryable": False}},
            {"extra": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                d.DiscoveryReceipt.model_validate(dict(receipt, **changes))

    def test_receipt_schema_is_versioned_without_duplicate_profile_model(self):
        schema = d.DiscoveryReceipt.model_json_schema()
        self.assertEqual(schema["properties"]["schemaVersion"]["const"], 1)
        self.assertIs(schema["additionalProperties"], False)
        self.assertNotIn("TargetProfile", schema.get("$defs", {}))
        self.assertEqual(
            set(schema["required"]), {"schemaVersion", "operation", "ok", "data", "error"}
        )

    def test_discovery_cannot_dispatch_build_export_or_process(self):
        # TEST_ONLY audit hook guards actual discovery execution, not fake registry data.
        import sys

        blocked = []
        active = True

        def audit(event, args):
            if active and event in {
                "subprocess.Popen",
                "os.system",
                "socket.connect",
                "socket.getaddrinfo",
                "os.remove",
                "os.rename",
            }:
                blocked.append(event)
                raise AssertionError("TEST_ONLY forbidden effect: " + event)
            if active and event == "open" and args[1] and any(c in args[1] for c in "wax+"):
                blocked.append("write")
                raise AssertionError("TEST_ONLY forbidden write")

        sys.addaudithook(audit)
        try:
            self.receipt(d.targets_receipt())
            self.receipt(d.target_receipt("tab5_1280x720"))
            self.receipt(d.capabilities_receipt([]))
            self.assertEqual(blocked, [])
        finally:
            active = False


class RegistrationSourceControls(unittest.TestCase):
    """STATIC ONLY: do not report these as SDK import/registration/transport PASS."""

    def test_decorator_annotations_and_structured_result_mapping(self):
        path = Path(d.__file__).with_name("discovery_tools.py")
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        annotation = next(
            n
            for n in tree.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "READ_ONLY" for t in n.targets)
        )
        self.assertEqual(
            {k.arg: ast.literal_eval(k.value) for k in annotation.value.keywords},
            {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )
        register = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "register_discovery_tools"
        )
        tools = [n for n in register.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertEqual(
            [n.name for n in tools], ["get_capabilities", "list_targets", "get_target"]
        )
        for tool in tools:
            self.assertEqual(ast.unparse(tool.returns), "Result")
            decorator = tool.decorator_list[0]
            self.assertEqual(
                {k.arg: ast.unparse(k.value) for k in decorator.keywords},
                {"annotations": "READ_ONLY", "structured_output": "True"},
            )
        result_function = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_result"
        )
        returned = next(n.value for n in result_function.body if isinstance(n, ast.Return))
        self.assertEqual(ast.unparse(returned.func), "CallToolResult")
        keywords = {k.arg: ast.unparse(k.value) for k in returned.keywords}
        self.assertEqual(keywords["structuredContent"], "receipt")
        self.assertEqual(keywords["isError"], "not receipt['ok']")

    def test_server_cutover_only_registers_discovery_before_return(self):
        path = Path(d.__file__).with_name("server.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        build = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_server"
        )
        self.assertEqual(ast.unparse(build.body[-3]), "register_discovery_tools(mcp)")
        self.assertEqual(ast.unparse(build.body[-2]), "register_codegraph_tools(mcp)")
        self.assertEqual(ast.unparse(build.body[-1]), "return mcp")


if __name__ == "__main__":
    unittest.main()
