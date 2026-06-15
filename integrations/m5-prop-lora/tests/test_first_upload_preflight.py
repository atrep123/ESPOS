from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_preflight_module():
    tool = ROOT / "tools" / "first_upload_preflight.py"
    spec = importlib.util.spec_from_file_location("first_upload_preflight", tool)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_blocks_when_required_tool_is_missing(monkeypatch) -> None:
    module = load_preflight_module()

    monkeypatch.setattr(
        module,
        "tool_status",
        lambda: [
            ("pio", True, "PlatformIO Core"),
            ("esptool", True, "esptool.py"),
            ("mpremote", False, "No module named mpremote"),
            ("idf.py", True, "ESP-IDF v5.1.3"),
            ("Claude Code via npx", True, "2.1.177"),
        ],
    )
    monkeypatch.setattr(module, "gemini_key_status", lambda: (True, "local key file exists"))
    monkeypatch.setattr(module, "serial_ports", lambda: (True, "COM10\nCOM23\n", ["COM10", "COM23"]))
    monkeypatch.setattr(
        module,
        "render_artifact_rows",
        lambda: [
            (module.ROOT / "build" / "preview" / "contact.png", True, 1),
            (module.ROOT / "build" / "preview" / "terminal_external_oled_128x64_x4.png", True, 1),
            (module.ROOT / "build" / "preview_dinrx" / "contact.png", True, 1),
        ],
    )
    monkeypatch.setattr(
        module,
        "dry_run_flash_commands",
        lambda: [
            ("c6l-modem-dial", True, "DRY RUN"),
            ("c6l-modem-prop", True, "DRY RUN"),
            ("din-rx", True, "DRY RUN"),
            ("sticks3-terminal", True, "DRY RUN"),
            ("dualkey-tx", True, "DRY RUN"),
            ("dial-tx", True, "DRY RUN"),
        ],
    )

    report, blockers = module.build_report()

    assert "- mpremote: BLOCKED - No module named mpremote" in report
    assert any("mpremote" in blocker and "No module named mpremote" in blocker for blocker in blockers)
