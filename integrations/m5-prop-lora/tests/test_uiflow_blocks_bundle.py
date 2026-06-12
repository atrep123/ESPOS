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


ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "uiflow" / "dial" / "blocks"
ALPHA2_SOURCE = BLOCKS / "alpha2" / "PropTx.py"
ALPHA2_DIST = BLOCKS / "dist" / "PropTx.m5b2"
SMOKE_EXAMPLE = BLOCKS / "examples" / "prop_tx_smoke.py"
VALIDATOR = ROOT / "tools" / "validate_uiflow_blocks.py"
EXPECTED_ALPHA2_METHODS = [
    "__init__",
    "preview",
    "fire",
    "stop",
    "arm",
    "remote_led",
    "sync_palette",
    "reply",
    "hue_color",
    "default_hues",
    "default_colors",
    "palette_from_hues",
    "set_color",
    "first_four",
    "rgb_color",
    "rgb888",
    "remote_led3",
    "remote_led5",
]


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_uiflow_blocks", VALIDATOR)
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
    assert "OK: 18 UIFlow custom blocks validated" in result.stdout
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

    assert report.block_count == len(manifest["blocks"]) == 18
    assert report.category == "PropTx"
    assert report.color == "#2E9E72"
    manifest_names = {block["name"] for block in manifest["blocks"]}
    assert set(report.template_names) == manifest_names
    assert {
        "default_hues",
        "default_colors",
        "palette_from_hues",
        "set_color",
        "first_four",
        "rgb_color",
        "rgb888",
        "remote_led3",
        "remote_led5",
    }.issubset(manifest_names)
    assert not report.errors


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


def test_uiflow_blocks_readme_documents_validation_and_manual_import_path():
    readme = (BLOCKS / "README.md").read_text(encoding="utf-8")

    for needle in [
        "python tools/validate_uiflow_blocks.py",
        "Validated manual bundle",
        "Alpha-2 .m5b2",
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
    assert "Prop remote LED" in methods["remote_led"]
    assert "Prop sync palette" in methods["sync_palette"]
    assert "Prop reply" in methods["reply"]
    assert "Prop hue" in methods["hue_color"]
    assert "Prop default hues" in methods["default_hues"]
    assert "Prop default colors" in methods["default_colors"]
    assert "Prop colors from hues" in methods["palette_from_hues"]
    assert "Prop set color" in methods["set_color"]
    assert "Prop first four" in methods["first_four"]
    assert "Prop RGB" in methods["rgb_color"]
    assert "Prop RGB888" in methods["rgb888"]
    assert "Prop remote LED3" in methods["remote_led3"]
    assert "Prop remote LED5" in methods["remote_led5"]

    for needle in [
        "import prop_frame",
        "import prop_ui",
        "self._tx = prop_frame.PropSender()",
        "self._tx.preview_line(colors)",
        "self._tx.fire_burst_lines(colors)",
        "self._tx.stop_line()",
        "self._tx.arm_line()",
        "self._tx.remote_led_line(",
        "self._tx.palette_line(1, False, colors, track_ack=False)",
        "self._prop_ui.hsv(deg)",
        "self._prop_ui.palette_from_hues",
        "self._prop_ui.rgb888(color)",
        "self.remote_led(3)",
        "self.remote_led(5)",
    ]:
        assert needle in source


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
        "remote_led": 2,
        "sync_palette": 2,
        "reply": 1,
        "hue_color": 2,
        "default_hues": 1,
        "default_colors": 1,
        "palette_from_hues": 2,
        "set_color": 4,
        "first_four": 2,
        "rgb_color": 4,
        "rgb888": 2,
        "remote_led3": 1,
        "remote_led5": 1,
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

    assert report.alpha2_method_count == 18
    assert report.alpha2_source == "uiflow/dial/blocks/alpha2/PropTx.py"
    assert report.alpha2_artifact == "uiflow/dial/blocks/dist/PropTx.m5b2"
    assert report.alpha2_artifact_method_count == 18
    assert report.alpha2_artifact_block_count == 18


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
    assert data["pyCode"].strip() == ALPHA2_SOURCE.read_text(encoding="utf-8").strip()
    for member in data["data"]["members"]:
        assert member["source"].strip() in data["pyCode"]


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

    spec = importlib.util.spec_from_file_location("alpha2_prop_tx_under_test", ALPHA2_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tx = module.PropTx(13, 15)
    uart = FakeUART.instances[-1]
    colors = [tx.hue_color(0), tx.hue_color(120), tx.hue_color(240), tx.hue_color(60)]
    default_hues = tx.default_hues()
    default_colors = tx.default_colors()
    updated_colors = tx.set_color(default_colors, 5, tx.rgb_color(-10, 260, 7))

    assert uart.kwargs["tx"] == 13
    assert uart.kwargs["rx"] == 15
    assert colors[0] == (255, 0, 0)
    assert default_hues == [0, 120, 240, 210, 60]
    assert default_colors == tx.palette_from_hues(default_hues)
    assert tx.first_four(default_colors) == default_colors[:4]
    assert tx.rgb_color(-10, 260, 7) == (0, 255, 7)
    assert tx.rgb888((1, 2, 3)) == 0x010203
    assert updated_colors[:4] == default_colors[:4]
    assert updated_colors[4] == (0, 255, 7)
    assert default_colors[4] != updated_colors[4]

    tx.preview(colors)
    tx.fire(colors)
    tx.stop()
    tx.arm()
    tx.remote_led(3)
    tx.remote_led(5)
    writes_before_invalid_remote_led = len(uart.writes)
    tx.remote_led(4)
    assert len(uart.writes) == writes_before_invalid_remote_led
    tx.remote_led3()
    tx.remote_led5()
    tx.sync_palette(default_colors)
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
        proto.FrameType.FIRE,
        proto.FrameType.FIRE,
        proto.FrameType.FIRE,
        proto.FrameType.STOP,
        proto.FrameType.ARM,
        proto.FrameType.REMOTE_LED,
        proto.FrameType.REMOTE_LED,
        proto.FrameType.REMOTE_LED,
        proto.FrameType.REMOTE_LED,
        proto.FrameType.PALETTE_SET,
    ]
    assert proto.parse_led_payload(bytes(decoded[0].payload))["colors"] == colors
    assert len(set(frame_lines[1:4])) == 1
    assert all(line.startswith("FF ") for line in frame_lines[1:4])
    assert decoded[1].sequence == decoded[2].sequence == decoded[3].sequence
    assert decoded[1].nonce == decoded[2].nonce == decoded[3].nonce
    assert (
        proto.parse_remote_led(bytes(decoded[6].payload))
        == tx._prop_frame.REMOTE_LED_BIT_LED3
    )
    assert (
        proto.parse_remote_led(bytes(decoded[7].payload))
        == tx._prop_frame.REMOTE_LED_BIT_LED5
    )
    assert (
        proto.parse_remote_led(bytes(decoded[8].payload))
        == tx._prop_frame.REMOTE_LED_BIT_LED3
    )
    assert (
        proto.parse_remote_led(bytes(decoded[9].payload))
        == tx._prop_frame.REMOTE_LED_BIT_LED5
    )


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
        "colors = proptx_0.set_color(colors, 5, proptx_0.hue_color(60))",
        "proptx_0.preview(proptx_0.first_four(colors))",
        "proptx_0.remote_led3()",
        "proptx_0.remote_led5()",
        "proptx_0.stop()",
        "reply = proptx_0.reply()",
    ]:
        assert needle in source


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
    frame_lines = [item for item in uart.writes if isinstance(item, str) and item.startswith("FF ")]
    decoded = [
        proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), keys)
        for line in frame_lines
    ]

    assert [int(frame.frame_type) for frame in decoded] == [
        proto.FrameType.PREVIEW,
        proto.FrameType.REMOTE_LED,
        proto.FrameType.REMOTE_LED,
        proto.FrameType.STOP,
    ]
    assert proto.parse_led_payload(bytes(decoded[0].payload))["colors"] == [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (0, 127, 255),
    ]
    assert proto.parse_remote_led(bytes(decoded[1].payload)) == proto.REMOTE_LED_BIT_LED3
    assert proto.parse_remote_led(bytes(decoded[2].payload)) == proto.REMOTE_LED_BIT_LED5
