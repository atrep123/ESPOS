import json
from pathlib import Path

import tools.esp32os_launcher as launcher


def test_load_config_with_defaults_and_override(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(launcher, "CONFIG_PATH", cfg_path)
    # No file -> defaults
    cfg = launcher.load_config()
    assert cfg["designer_script"] == launcher.DEFAULT_CONFIG["designer_script"]
    # Write override
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps({"sim_args": ["--foo"], "designer_script": "custom.py"}), encoding="utf-8")
    cfg2 = launcher.load_config()
    assert cfg2["sim_args"] == ["--foo"]
    assert cfg2["designer_script"] == "custom.py"


def test_save_config_writes_file(tmp_path, monkeypatch):
    cfg_path = tmp_path / "cfg.json"
    monkeypatch.setattr(launcher, "CONFIG_PATH", cfg_path)
    data = {"designer_script": "x.py", "sim_args": ["--bar"]}
    launcher.save_config(data)
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["designer_script"] == "x.py"
    assert saved["sim_args"] == ["--bar"]


def test_reset_config(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.json"
    monkeypatch.setattr(launcher, "CONFIG_PATH", cfg_path)
    cfg = launcher.reset_config()
    assert cfg_path.exists()
    loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert loaded["designer_script"] == launcher.DEFAULT_CONFIG["designer_script"]
    assert cfg["simulator_script"] == launcher.DEFAULT_CONFIG["simulator_script"]
