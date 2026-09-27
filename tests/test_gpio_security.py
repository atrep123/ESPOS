"""Invalid hardware operands must fail at validation and direct codegen."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import build
from tools.ui_codegen import LogicCodegenError, generate_ui_design_pair
from tools.validate_design import validate_file


def _gpio_design(pin=21, level=1):
    return {
        "scenes": {
            "main": {
                "width": 256,
                "height": 128,
                "widgets": [],
                "rules": [
                    {
                        "trigger": {"type": "gpio_in", "pin": pin, "edge": "any"},
                        "actions": [{"type": "gpio_write", "pin": pin, "level": level}],
                    }
                ],
            }
        }
    }


@pytest.mark.parametrize("level", [-1, 2, "1", 1.0, True, None])
def test_invalid_gpio_level_rejected_in_both_paths(tmp_path, level):
    path = tmp_path / "design.json"
    path.write_text(json.dumps(_gpio_design(level=level)), encoding="utf-8")
    assert any(
        i.level == "ERROR" and "level" in i.message
        for i in validate_file(path, warnings_as_errors=False)
    )
    with pytest.raises(LogicCodegenError, match="level"):
        generate_ui_design_pair(path, scene_name="main", source_label="design.json")


@pytest.mark.parametrize("pin", [0, 21, 48])
@pytest.mark.parametrize("level", [0, 1])
def test_valid_gpio_boundaries(tmp_path, pin, level):
    path = tmp_path / "design.json"
    path.write_text(json.dumps(_gpio_design(pin=pin, level=level)), encoding="utf-8")
    assert not any(i.level == "ERROR" for i in validate_file(path, warnings_as_errors=False))
    c_text, _ = generate_ui_design_pair(path, scene_name="main", source_label="design.json")
    assert "UI_ACT_GPIO_WRITE" in c_text
    assert "UI_TRIG_GPIO_IN" in c_text


def test_pio_relative_json_resolves_from_project_and_rejects_invalid_reuse(tmp_path, monkeypatch):
    import runpy

    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    path = root / "design.json"
    path.write_text(json.dumps(_gpio_design()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ESP32OS_UI_JSON", "design.json")
    monkeypatch.setenv("ESP32OS_PIO_UI_EXPORT", "1")
    script = Path(__file__).resolve().parents[1] / "scripts/pio_generate_ui_design.py"
    globals_ = {"Import": lambda _: None, "env": {"PROJECT_DIR": str(root)}}
    runpy.run_path(str(script), init_globals=globals_)
    original = (root / "src/ui_design.c").read_bytes()
    path.write_text(json.dumps(_gpio_design(pin=64)), encoding="utf-8")
    monkeypatch.setenv("ESP32OS_PIO_UI_EXPORT", "0")
    monkeypatch.setenv("ESP32OS_UI_VALIDATE", "0")
    with pytest.raises(RuntimeError, match="Validation found"):
        runpy.run_path(str(script), init_globals=globals_)
    assert (root / "src/ui_design.c").read_bytes() == original


@pytest.mark.parametrize("pin", [-1, 49, 64, 256, 2**40, "21", 21.5, True, None])
@pytest.mark.parametrize("kind", ["gpio_write", "gpio_in"])
def test_invalid_pin_rejected_in_both_paths(tmp_path, pin, kind):
    data = {
        "scenes": {
            "main": {
                "width": 256,
                "height": 128,
                "widgets": [],
                "rules": [
                    {
                        "trigger": {"type": "boot"},
                        "actions": [{"type": "gpio_write", "pin": 21, "level": 1}],
                    }
                ],
            }
        }
    }
    rule = data["scenes"]["main"]["rules"][0]
    if kind == "gpio_in":
        rule["trigger"] = {"type": kind, "pin": pin, "edge": "any"}
    else:
        rule["actions"][0]["pin"] = pin
    path = tmp_path / "design.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert any(
        i.level == "ERROR" and kind in i.message
        for i in validate_file(path, warnings_as_errors=False)
    )
    with pytest.raises(LogicCodegenError):
        generate_ui_design_pair(path, scene_name="main", source_label="design.json")


def test_valid_gpio_design_and_build_reject_before_writes(tmp_path, monkeypatch):
    root = tmp_path
    (root / "src").mkdir()
    path = root / "main_scene.json"
    path.write_text(
        json.dumps(
            {
                "scenes": {
                    "main": {
                        "width": 256,
                        "height": 128,
                        "widgets": [],
                        "rules": [
                            {
                                "trigger": {"type": "gpio_in", "pin": 21},
                                "actions": [{"type": "gpio_write", "pin": 21, "level": 1}],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "REPO_ROOT", root)
    assert build.regen_codegen(path, sink=lambda _: None)
    original = (root / "src/ui_design.c").read_bytes()
    data = json.loads(path.read_text())
    data["scenes"]["main"]["rules"][0]["actions"][0]["pin"] = 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(build.BuildError, match="invalid design"):
        build.regen_codegen(path, sink=lambda _: None)
    assert (root / "src/ui_design.c").read_bytes() == original


def test_pio_no_export_still_validates_and_rejects_stale(tmp_path, monkeypatch):
    import runpy

    root = tmp_path
    (root / "src").mkdir()
    (root / "main_scene.json").write_bytes(
        (Path(__file__).resolve().parents[1] / "main_scene.json").read_bytes()
    )
    monkeypatch.setenv("ESP32OS_PIO_UI_EXPORT", "0")
    monkeypatch.setenv("ESP32OS_UI_VALIDATE", "0")
    monkeypatch.delenv("ESP32OS_UI_JSON", raising=False)
    script = Path(__file__).resolve().parents[1] / "scripts/pio_generate_ui_design.py"
    with pytest.raises(RuntimeError, match="generated files do not match"):
        runpy.run_path(
            str(script), init_globals={"Import": lambda _: None, "env": {"PROJECT_DIR": str(root)}}
        )
    monkeypatch.setenv("ESP32OS_PIO_UI_EXPORT", "1")
    runpy.run_path(
        str(script), init_globals={"Import": lambda _: None, "env": {"PROJECT_DIR": str(root)}}
    )
    monkeypatch.setenv("ESP32OS_PIO_UI_EXPORT", "0")
    runpy.run_path(
        str(script), init_globals={"Import": lambda _: None, "env": {"PROJECT_DIR": str(root)}}
    )


def test_direct_cmake_rejects_invalid_json_before_idf_or_source_use(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src").mkdir()
    for name in ("pio_generate_ui_design.py", "validate_idf_ui.py"):
        shutil.copyfile(repo / "scripts" / name, tmp_path / "scripts" / name)
    shutil.copyfile(repo / "CMakeLists.txt", tmp_path / "CMakeLists.txt")
    (tmp_path / "main_scene.json").write_text(
        '{"scenes": {"main": {"width": 256, "height": 128, '
        '"widgets": [], "rules": [{"trigger": {"type": "boot"}, '
        '"actions": [{"type": "gpio_write", "pin": 64, "level": 1}]}]}}}',
        encoding="utf-8",
    )
    old = b"/* stale generated code must not be compiled */"
    (tmp_path / "src/ui_design.c").write_bytes(old)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    env["ESP32OS_UI_VALIDATE"] = "0"
    env.pop("ESP32OS_UI_JSON", None)
    cmake = shutil.which("cmake")
    assert cmake, "direct IDF gate test requires CMake"
    run = subprocess.run(
        [
            cmake,
            "-S",
            str(tmp_path),
            "-B",
            str(tmp_path / "build"),
            "-DPython3_EXECUTABLE=" + sys.executable,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode != 0
    assert "UI validation/generation failed" in run.stdout + run.stderr
    assert "pin" in run.stdout + run.stderr
    assert (tmp_path / "src/ui_design.c").read_bytes() == old
