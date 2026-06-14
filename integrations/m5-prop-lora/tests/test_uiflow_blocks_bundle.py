from __future__ import annotations

import importlib.util
import ast
import json
import re
import runpy
import shutil
import subprocess
import sys
import types
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "uiflow" / "dial" / "blocks"
ALPHA2_SOURCE = BLOCKS / "alpha2" / "PropTx.py"
ALPHA2_DIST = BLOCKS / "dist" / "PropTx.m5b2"
SMOKE_EXAMPLE = BLOCKS / "examples" / "prop_tx_smoke.py"
VALIDATOR = ROOT / "tools" / "validate_uiflow_blocks.py"
ARTIFACT_BUILDER = ROOT / "tools" / "build_uiflow_alpha2_artifact.py"
EXPECTED_ALPHA2_METHODS = [
    "__init__",
    "preview",
    "fire",
    "stop",
    "arm",
    "reply",
    "default_colors",
    "first_four",
    "rgb_color",
    "rgb888",
]
TEST_PROP_KEY_HEX = "00112233445566778899aabbccddeeff"


@pytest.fixture(autouse=True)
def provision_test_prop_key(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "prop_key",
        types.SimpleNamespace(
            SHARED_KEY_HEX=TEST_PROP_KEY_HEX,
            ALLOW_PROTOTYPE_SHARED_KEY=True,
        ),
    )
    monkeypatch.delitem(sys.modules, "prop_frame", raising=False)


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_uiflow_blocks", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_artifact_builder():
    spec = importlib.util.spec_from_file_location("build_uiflow_alpha2_artifact", ARTIFACT_BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_uiflow_tree(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "uiflow", tmp_path / "uiflow")
    return tmp_path


def test_uiflow_block_validator_cli_passes_and_reports_manual_bundle():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: 10 UIFlow custom blocks validated" in result.stdout
    assert "uiflow/dial/blocks/prop_tx.json" in result.stdout
    assert "uiflow/dial/blocks/code" in result.stdout
    assert "uiflow/dial/prop_frame.py" in result.stdout
    assert "uiflow/dial/prop_state.py" in result.stdout
    assert "uiflow/dial/prop_ui.py" in result.stdout
    assert "uiflow/dial/blocks/alpha2/PropTx.py" in result.stdout


def test_uiflow_block_manifest_templates_are_consistent():
    validator = load_validator()
    manifest = json.loads((BLOCKS / "prop_tx.json").read_text(encoding="utf-8"))

    report = validator.validate_bundle(ROOT)

    assert report.block_count == len(manifest["blocks"]) == 10
    assert report.category == "PropTx"
    assert report.color == "#2E9E72"
    manifest_names = {block["name"] for block in manifest["blocks"]}
    assert set(report.template_names) == manifest_names
    assert {"default_colors", "first_four", "rgb_color", "rgb888"}.issubset(manifest_names)
    assert not report.errors


def test_manual_reply_template_uses_non_throwing_decode():
    source = (BLOCKS / "code" / "reply.py").read_text(encoding="utf-8")

    assert '.decode("utf-8", "ignore")' in source
    assert ".decode()" not in source

    class FakeUart:
        def __init__(self, value):
            self.value = value

        def any(self):
            return self.value is not False

        def read(self):
            return self.value

    expression = source.splitlines()[-1]
    assert eval(expression, {"prop_uart": FakeUart("OK\n")}) == "OK\n"
    assert eval(expression, {"prop_uart": FakeUart(b"OK\xff\n")}) == "OK\n"
    assert eval(expression, {"prop_uart": FakeUart(None)}) == ""
    assert eval(expression, {"prop_uart": FakeUart(False)}) == ""


def test_manual_send_fire_template_requires_delay_function():
    source = (BLOCKS / "code" / "send_fire.py").read_text(encoding="utf-8")

    assert "import prop_frame" in source
    assert "time.sleep_ms or time.sleep is required for Prop FIRE burst timing" in source
    assert "_prop_delay_ms = lambda ms: time.sleep(ms / 1000)" in source
    assert "_prop_delay_ms(prop_frame.FIRE_BURST_GAP_MS)" in source
    assert "raise RuntimeError" in source


def test_manual_send_stop_template_retries_same_stop_frame():
    source = (BLOCKS / "code" / "send_stop.py").read_text(encoding="utf-8")

    assert "import prop_frame" in source
    assert "prop_tx.stop_lines()" in source
    assert "prop_frame.STOP_RETRY_GAP_MS" in source
    assert "time.sleep_ms or time.sleep is required for Prop STOP retry timing" in source
    assert "prop_tx.stop_line()" not in source


def test_manual_remote_led_templates_are_not_exposed_in_command_only_bundle():
    assert not (BLOCKS / "code" / "remote_led.py").exists()
    assert not (BLOCKS / "code" / "remote_led3.py").exists()
    assert not (BLOCKS / "code" / "remote_led5.py").exists()


def test_uiflow_block_validator_reports_non_object_block(tmp_path):
    repo = copy_uiflow_tree(tmp_path)
    manifest_path = repo / "uiflow" / "dial" / "blocks" / "prop_tx.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["blocks"][0] = "bad"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    validator = load_validator()

    report = validator.validate_bundle(repo)

    assert any("blocks[0] must be an object" in error for error in report.errors)


def test_uiflow_block_validator_reports_non_object_param(tmp_path):
    repo = copy_uiflow_tree(tmp_path)
    manifest_path = repo / "uiflow" / "dial" / "blocks" / "prop_tx.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["blocks"][0]["params"][0] = "bad"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    validator = load_validator()

    report = validator.validate_bundle(repo)

    assert any("blocks[0].params[0] must be an object" in error for error in report.errors)


def test_uiflow_block_validator_reports_non_object_manifest(tmp_path):
    repo = copy_uiflow_tree(tmp_path)
    manifest_path = repo / "uiflow" / "dial" / "blocks" / "prop_tx.json"
    manifest_path.write_text(json.dumps(["bad"]), encoding="utf-8")
    validator = load_validator()

    report = validator.validate_bundle(repo)

    assert any("manifest must be a JSON object" in error for error in report.errors)


def test_uiflow_block_validator_reports_non_object_alpha2_artifact(tmp_path):
    repo = copy_uiflow_tree(tmp_path)
    artifact_path = repo / "uiflow" / "dial" / "blocks" / "dist" / "PropTx.m5b2"
    artifact_path.write_text(json.dumps(["bad"]), encoding="utf-8")
    validator = load_validator()

    report = validator.validate_bundle(repo)

    assert any(
        "uiflow/dial/blocks/dist/PropTx.m5b2: artifact must be a JSON object" in error
        for error in report.errors
    )


def test_uiflow_block_validator_reports_legacy_alpha2_method_drift(tmp_path):
    repo = copy_uiflow_tree(tmp_path)
    blocks_dir = repo / "uiflow" / "dial" / "blocks"
    manifest_path = blocks_dir / "prop_tx.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["blocks"].append(
        {
            "name": "diagnostic_ping",
            "type": "execute",
            "params": [{"name": "Prop diagnostic", "type": "label"}],
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (blocks_dir / "code" / "diagnostic_ping.py").write_text("# diagnostic\n", encoding="utf-8")
    validator = load_validator()

    report = validator.validate_bundle(repo)

    assert any(
        "manifest/templates have blocks without Alpha-2 method mapping: ['diagnostic_ping']"
        in error
        for error in report.errors
    )


def test_uiflow_blocks_readme_documents_validation_and_manual_import_path():
    readme = (BLOCKS / "README.md").read_text(encoding="utf-8")

    for needle in [
        "python tools/validate_uiflow_blocks.py",
        "Validated manual bundle",
        "Alpha-2 .m5b2",
        "UIFlow2 Block Designer Alpha-2",
        "checked by deterministic tests against the builder",
        "uiflow/dial/blocks/alpha2/PropTx.py",
        "uiflow/dial/blocks/dist/PropTx.m5b2",
        "tools/build_uiflow_alpha2_artifact.py",
        "prop_tx.json",
        "code/<name>.py",
        "prop_frame.py",
        "prop_state.py",
        "prop_ui.py",
        "PropTx.py",
        "Custom -> Open",
        "uiflow/dial/blocks/examples/prop_tx_smoke.py",
        "UIFlow2 canvas still needs UIFlow2 Web",
    ]:
        assert needle in readme


def test_alpha2_prop_tx_source_covers_every_prop_block_method():
    source = ALPHA2_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    classes = [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PropTx"
    ]
    assert len(classes) == 1
    methods = {
        node.name: ast.get_docstring(node) or ""
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    assert set(methods) == set(EXPECTED_ALPHA2_METHODS)
    assert "Prop init TX" in methods["__init__"]
    assert "Prop PREVIEW" in methods["preview"]
    assert "colors" in methods["preview"]
    assert "Prop ODPAL" in methods["fire"]
    assert "colors" in methods["fire"]
    assert "Prop STOP" in methods["stop"]
    assert "Prop ARM" in methods["arm"]
    assert "Prop reply" in methods["reply"]
    assert "Prop default colors" in methods["default_colors"]
    assert "Prop first four" in methods["first_four"]
    assert "Prop RGB" in methods["rgb_color"]
    assert "Prop RGB888" in methods["rgb888"]

    for needle in [
        "import prop_frame",
        "import prop_ui",
        "self._tx = prop_frame.PropSender()",
        "self._tx.preview_line(_first_four_for_frame(self, colors))",
        "self._tx.fire_burst_lines(_first_four_for_frame(self, colors))",
        "self._tx.stop_lines()",
        "self._tx.arm_lines()",
        "Prop STOP retry timing",
        "self._prop_ui.palette_from_hues",
        "self._prop_ui.rgb888(color)",
    ]:
        assert needle in source
    assert "remote_led" not in source


def test_alpha2_method_labels_include_designer_instance_placeholder():
    source = ALPHA2_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    prop_tx = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PropTx"
    )
    expected_counts = {
        "__init__": 3,
        "preview": 2,
        "fire": 2,
        "stop": 1,
        "arm": 1,
        "reply": 1,
        "default_colors": 1,
        "first_four": 2,
        "rgb_color": 4,
        "rgb888": 2,
    }

    for method in [node for node in prop_tx.body if isinstance(node, ast.FunctionDef)]:
        doc = ast.get_docstring(method) or ""
        label_line = next(
            line.strip() for line in doc.splitlines() if line.strip().startswith("en:")
        )
        assert label_line.count("%") == expected_counts[method.name], method.name


def test_validator_reports_alpha2_prop_tx_source():
    validator = load_validator()

    report = validator.validate_bundle(ROOT)

    assert report.alpha2_method_count == 10
    assert report.alpha2_source == "uiflow/dial/blocks/alpha2/PropTx.py"
    assert report.alpha2_artifact == "uiflow/dial/blocks/dist/PropTx.m5b2"
    assert report.alpha2_artifact_method_count == 10
    assert report.alpha2_artifact_block_count == 10


def test_alpha2_dist_m5b2_is_exported_for_offline_import():
    data = json.loads(ALPHA2_DIST.read_text(encoding="utf-8"))

    assert data["version"] == "alpha2"
    assert data["category"] == "PropTx"
    assert data["color"] == "#2E9E72"
    assert "from PropTx import PropTx" in data["uiflow2"]["jscode"]
    assert data["data"]["python_file_name"] == "PropTx"
    assert data["data"]["name"] == "PropTx"
    assert [member["name"] for member in data["data"]["members"]] == EXPECTED_ALPHA2_METHODS


def test_alpha2_dist_block_type_entries_match_blockly_registrations():
    data = json.loads(ALPHA2_DIST.read_text(encoding="utf-8"))
    jscode = data["uiflow2"]["jscode"]

    registered = set(re.findall(r'Blockly\.Blocks\["([^"]+)"\]', jscode))

    assert "custom_proptx_init" in registered
    assert set(data["uiflow2"]["block_type"]) == registered


def test_alpha2_dist_import_module_category_and_source_match_manifest():
    manifest = json.loads((BLOCKS / "prop_tx.json").read_text(encoding="utf-8"))
    data = json.loads(ALPHA2_DIST.read_text(encoding="utf-8"))
    import_match = re.search(r"from\s+(\w+)\s+import\s+(\w+)", data["uiflow2"]["jscode"])
    toolbox = ET.fromstring("<root>" + data["uiflow2"]["toolbox"] + "</root>")
    toolbox_category = toolbox.find("category")

    assert import_match
    assert import_match.group(1) == data["data"]["python_file_name"] == "PropTx"
    assert import_match.group(2) == data["data"]["name"] == "PropTx"
    assert manifest["category"] == data["category"] == toolbox_category.get("name")
    assert data["pyCode"] == ALPHA2_SOURCE.read_text(encoding="utf-8")
    for member in data["data"]["members"]:
        assert member["source"].strip() in data["pyCode"]


def test_alpha2_dist_embedded_ui_assets_match_deterministic_builder():
    builder = load_artifact_builder()
    data = json.loads(ALPHA2_DIST.read_text(encoding="utf-8"))

    expected_jscode = builder.build_jscode(data["category"], data["color"])
    expected_toolbox = builder.build_toolbox(data["category"], data["color"])
    actual_jscode = data["uiflow2"]["jscode"]
    actual_toolbox = data["uiflow2"]["toolbox"]

    assert actual_jscode == expected_jscode
    assert actual_toolbox == expected_toolbox


def test_alpha2_dist_m5b2_matches_deterministic_builder_output():
    builder = load_artifact_builder()
    generated = builder.build_artifact_text().encode("utf-8")
    tracked = ALPHA2_DIST.read_bytes()

    assert generated == tracked


def test_alpha2_toolbox_does_not_shadow_structured_inputs_with_empty_text():
    data = json.loads(ALPHA2_DIST.read_text(encoding="utf-8"))
    toolbox = ET.fromstring("<root>" + data["uiflow2"]["toolbox"] + "</root>")

    for member in data["data"]["members"]:
        method = member["name"]
        block_type = f"custom_proptx_{'init' if method == '__init__' else method}"
        block = toolbox.find(f".//block[@type='{block_type}']")
        assert block is not None, block_type
        for param in member["params"]:
            value = block.find(f"value[@name='{param['name']}']")
            shadow = value.find("shadow") if value is not None else None
            if param["type"] in {"list", "tuple"}:
                assert shadow is None, (block_type, param["name"])
            elif param["type"] == "int":
                assert shadow is not None
                assert shadow.get("type") == "math_number"


def test_alpha2_prop_tx_runtime_methods_emit_decodable_frames(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.writes = []
            self.reads = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

        def any(self):
            return bool(self.reads)

        def read(self):
            return self.reads.pop(0) if self.reads else b""

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))
    monkeypatch.setitem(sys.modules, "time", types.SimpleNamespace(sleep_ms=lambda _value: None))

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_under_test", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    uart = FakeUART.instances[-1]
    default_colors = tx.default_colors()
    colors = tx.first_four(default_colors)

    assert uart.kwargs["tx"] == 13
    assert uart.kwargs["rx"] == 15
    assert default_colors == [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 127, 255), (255, 255, 0)]
    assert tx.first_four(default_colors) == default_colors[:4]
    assert tx.rgb_color(-10, 260, 7) == (0, 255, 7)
    assert tx.rgb888((1, 2, 3)) == 0x010203

    tx.preview(colors)
    tx.arm()
    tx.fire(colors)
    tx.stop()
    uart.reads.append(b"OK\n")

    assert tx.reply() == "OK\n"

    from shared.protocol import protocol as proto

    keys = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}
    frame_lines = [
        item
        for item in uart.writes
        if isinstance(item, str) and (item.startswith("FF ") or item.startswith("SEND "))
    ]
    decoded = [
        proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), keys)
        for line in frame_lines
    ]

    assert [int(frame.frame_type) for frame in decoded] == [
        proto.FrameType.PREVIEW,
        proto.FrameType.ARM,
        proto.FrameType.ARM,
        proto.FrameType.FIRE,
        proto.FrameType.FIRE,
        proto.FrameType.FIRE,
        proto.FrameType.STOP,
        proto.FrameType.STOP,
        proto.FrameType.STOP,
    ]
    assert proto.parse_led_payload(bytes(decoded[0].payload))["colors"] == colors
    assert len(set(frame_lines[1:3])) == 1
    assert all(line.startswith("FF ") for line in frame_lines[1:3])
    assert len(set(frame_lines[3:6])) == 1
    assert all(line.startswith("FF ") for line in frame_lines[3:6])
    assert len(set(frame_lines[6:9])) == 1
    assert all(line.startswith("SEND ") for line in frame_lines[6:9])
    assert decoded[1].sequence == decoded[2].sequence
    assert decoded[1].nonce == decoded[2].nonce
    assert decoded[3].sequence == decoded[4].sequence == decoded[5].sequence
    assert decoded[3].nonce == decoded[4].nonce == decoded[5].nonce
    assert decoded[6].sequence == decoded[7].sequence == decoded[8].sequence
    assert decoded[6].nonce == decoded[7].nonce == decoded[8].nonce
    assert len(decoded) == 9


def test_alpha2_prop_tx_reply_ignores_invalid_utf8_bytes(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.reads = []
            FakeUART.instances.append(self)

        def write(self, data):
            return len(data)

        def any(self):
            return bool(self.reads)

        def read(self):
            return self.reads.pop(0)

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_reply_utf8", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    FakeUART.instances[-1].reads.append(b"OK\xff\n")

    assert tx.reply() == "OK\n"


def test_alpha2_prop_tx_fire_sleeps_between_burst_frames(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.writes = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

    sleep_calls = []

    def sleep_ms(value):
        sleep_calls.append(value)

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))
    monkeypatch.setitem(sys.modules, "time", types.SimpleNamespace(sleep_ms=sleep_ms))

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_fire_sleep", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    tx.arm()
    FakeUART.instances[-1].writes.clear()
    tx.fire([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 180, 0)])

    fire_writes = [
        item
        for item in FakeUART.instances[-1].writes
        if isinstance(item, str) and item.startswith("FF ")
    ]

    assert len(fire_writes) == 3
    assert sleep_calls == [
        tx._prop_frame.FIRE_BURST_GAP_MS,
        tx._prop_frame.FIRE_BURST_GAP_MS,
    ]


def test_alpha2_prop_tx_fire_requires_local_arm(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.writes = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))
    monkeypatch.setitem(sys.modules, "time", types.SimpleNamespace(sleep_ms=lambda _value: None))

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_fire_requires_arm", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    sequence_before = tx._tx.sequence
    with pytest.raises(RuntimeError, match="Prop FIRE requires Prop ARM first"):
        tx.fire([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 180, 0)])
    assert tx._tx.sequence == sequence_before
    assert not [
        item
        for item in FakeUART.instances[-1].writes
        if isinstance(item, str) and item.startswith("FF ")
    ]


def test_alpha2_prop_tx_fire_falls_back_to_time_sleep(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.writes = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

    sleep_calls = []

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))
    monkeypatch.setitem(sys.modules, "time", types.SimpleNamespace(sleep=sleep_calls.append))

    spec = importlib.util.spec_from_file_location(
        "alpha2_prop_tx_fire_sleep_fallback", ALPHA2_SOURCE
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    tx.arm()
    tx.fire([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 180, 0)])

    assert sleep_calls == [
        tx._prop_frame.FIRE_BURST_GAP_MS / 1000,
        tx._prop_frame.FIRE_BURST_GAP_MS / 1000,
    ]


def test_alpha2_prop_tx_fire_requires_delay_function(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.writes = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))
    monkeypatch.setitem(sys.modules, "time", types.SimpleNamespace())

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_fire_no_sleep", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    sequence_before = tx._tx.sequence
    tx.arm()
    FakeUART.instances[-1].writes.clear()
    with pytest.raises(RuntimeError, match="time.sleep_ms or time.sleep is required"):
        tx.fire([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 180, 0)])
    assert tx._tx.sequence == sequence_before + 1
    assert not [
        item
        for item in FakeUART.instances[-1].writes
        if isinstance(item, str) and item.startswith("FF ")
    ]


def test_alpha2_prop_tx_instances_keep_independent_uart_state(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.writes = []
            self.reads = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

        def any(self):
            return bool(self.reads)

        def read(self):
            return self.reads.pop(0) if self.reads else b""

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_two_instances", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    first = module.PropTx(13, 15)
    second = module.PropTx(17, 18)
    first_uart, second_uart = FakeUART.instances

    first.preview([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)])

    assert any(isinstance(item, str) and item.startswith("FF ") for item in first_uart.writes)
    assert not any(isinstance(item, str) and item.startswith("FF ") for item in second_uart.writes)
    assert first_uart.kwargs["tx"] == 13
    assert second_uart.kwargs["tx"] == 17
    assert first is not second


def test_alpha2_prop_tx_reply_handles_text_and_bad_bytes(monkeypatch):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.writes = []
            self.reads = []
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

        def any(self):
            return bool(self.reads)

        def read(self):
            return self.reads.pop(0) if self.reads else b""

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_reply", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    uart = FakeUART.instances[-1]
    uart.reads.append("OK\n")
    assert tx.reply() == "OK\n"
    uart.reads.append(b"\xff\xfe")
    assert tx.reply() == ""


def test_block_generated_smoke_example_matches_uiflow2_shape():
    source = SMOKE_EXAMPLE.read_text(encoding="utf-8")

    for needle in [
        "from PropTx import PropTx",
        "proptx_0 = PropTx(13, 15)",
        "colors = proptx_0.default_colors()",
        "proptx_0.preview(proptx_0.first_four(colors))",
        "proptx_0.arm()",
        "proptx_0.stop()",
        "reply = proptx_0.reply()",
    ]:
        assert needle in source
    assert "set_color" not in source
    assert "hue_color" not in source


def test_block_generated_smoke_example_executes_and_emits_valid_frames(monkeypatch, capsys):
    class FakeUART:
        instances = []

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.writes = []
            self.reads = [b"OK\n"]
            FakeUART.instances.append(self)

        def write(self, data):
            self.writes.append(data)
            return len(data)

        def any(self):
            return bool(self.reads)

        def read(self):
            return self.reads.pop(0) if self.reads else b""

    monkeypatch.syspath_prepend(str(ROOT / "uiflow" / "dial"))
    monkeypatch.syspath_prepend(str(BLOCKS / "alpha2"))
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.setitem(sys.modules, "hardware", types.SimpleNamespace(UART=FakeUART))
    monkeypatch.delitem(sys.modules, "PropTx", raising=False)

    runpy.run_path(str(SMOKE_EXAMPLE), run_name="__main__")

    assert capsys.readouterr().out == "OK\n\n"
    assert len(FakeUART.instances) == 1
    uart = FakeUART.instances[0]
    assert uart.kwargs["tx"] == 13
    assert uart.kwargs["rx"] == 15

    from shared.protocol import protocol as proto

    keys = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}
    frame_lines = [
        item
        for item in uart.writes
        if isinstance(item, str) and (item.startswith("FF ") or item.startswith("SEND "))
    ]
    decoded = [
        proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), keys)
        for line in frame_lines
    ]

    assert [int(frame.frame_type) for frame in decoded] == [
        proto.FrameType.PREVIEW,
        proto.FrameType.ARM,
        proto.FrameType.ARM,
        proto.FrameType.STOP,
        proto.FrameType.STOP,
        proto.FrameType.STOP,
    ]
    assert proto.parse_led_payload(bytes(decoded[0].payload))["colors"] == [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (0, 127, 255),
    ]
    assert all(line.startswith("FF ") for line in frame_lines[1:3])
    assert len(set(frame_lines[1:3])) == 1
    assert all(line.startswith("SEND ") for line in frame_lines[3:6])
    assert len(set(frame_lines[3:6])) == 1
