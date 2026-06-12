from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "uiflow_dial_offline.py"


def load_offline_tool():
    spec = importlib.util.spec_from_file_location("uiflow_dial_offline_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_offline_bundle_contains_runtime_files_and_block_artifact(tmp_path):
    out = tmp_path / "offline"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (out / "device" / "main.py").exists()
    assert (out / "device" / "prop_frame.py").exists()
    assert (out / "device" / "prop_state.py").exists()
    assert (out / "device" / "prop_ui.py").exists()
    assert (out / "device" / "PropTx.py").exists()
    assert (out / "blocks" / "PropTx.m5b2").exists()
    assert (out / "README_OFFLINE.txt").exists()
    manifest = json.loads((out / "offline_manifest.json").read_text(encoding="utf-8"))
    assert [item["device_path"] for item in manifest["device_files"]] == [
        "/flash/prop_frame.py",
        "/flash/prop_state.py",
        "/flash/prop_ui.py",
        "/flash/PropTx.py",
        "/flash/main.py",
    ]
    assert manifest["block_artifacts"][0]["bundle_path"] == "blocks/PropTx.m5b2"
    assert all(len(item["sha256"]) == 64 for item in manifest["device_files"])
    offline_readme = (out / "README_OFFLINE.txt").read_text(encoding="utf-8")
    assert "PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload" in offline_readme
    assert "offline UIFlow Dial bundle" in result.stdout


def test_offline_bundle_runtime_uses_fire_burst_path(tmp_path):
    out = tmp_path / "offline"

    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    prop_frame = (out / "device" / "prop_frame.py").read_text(encoding="utf-8")
    main_py = (out / "device" / "main.py").read_text(encoding="utf-8")
    prop_tx = (out / "device" / "PropTx.py").read_text(encoding="utf-8")

    assert "def fire_burst_lines" in prop_frame
    assert "tx.fire_burst_lines(_colors[:4])" in main_py
    assert "self._tx.fire_burst_lines(colors)" in prop_tx
    assert "fire_line(_colors[:4])" not in main_py
    assert "self._tx.fire_line(colors)" not in prop_tx


def test_offline_deploy_dry_run_prints_mpremote_upload_commands():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "deploy", "--port", "COM6", "--dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "DRY RUN" in result.stdout
    assert f"{sys.executable} -m mpremote connect COM6 fs mkdir /flash" in result.stdout
    assert f"{sys.executable} -m mpremote connect COM6 fs cp" in result.stdout
    assert ":/flash/prop_frame.py" in result.stdout
    assert ":/flash/prop_state.py" in result.stdout
    assert ":/flash/prop_ui.py" in result.stdout
    assert ":/flash/PropTx.py" in result.stdout
    assert ":/flash/main.py" in result.stdout
    assert "PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload" in result.stdout


def test_offline_verify_accepts_created_bundle(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "verified offline UIFlow Dial bundle" in result.stdout


def test_offline_verify_rejects_tampered_device_file(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    (out / "device" / "PropTx.py").write_text("# tampered\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "sha256 mismatch: device/PropTx.py" in result.stderr


def test_offline_verify_rejects_tampered_block_artifact(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    (out / "blocks" / "PropTx.m5b2").write_text("tampered\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "sha256 mismatch: blocks/PropTx.m5b2" in result.stderr


def test_offline_verify_rejects_non_hex_sha256(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"][0]["sha256"] = "z" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "invalid sha256 in manifest: device/prop_frame.py" in result.stderr
    assert "sha256 mismatch: device/prop_frame.py" not in result.stderr


def test_offline_verify_rejects_partial_manifest(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"] = manifest["device_files"][:1]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "missing manifest entry: device/prop_ui.py" in result.stderr


def test_offline_verify_rejects_bundle_path_traversal(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"][0]["bundle_path"] = "../outside.py"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "bundle_path escapes bundle: ../outside.py" in result.stderr


def test_create_bundle_preserves_existing_output_when_source_preflight_fails(tmp_path, monkeypatch):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    out.mkdir()
    marker = out / "keep.txt"
    marker.write_text("old bundle", encoding="utf-8")
    monkeypatch.setattr(
        tool,
        "BLOCK_ARTIFACTS",
        (tool.BlockArtifact("uiflow/dial/blocks/dist/does-not-exist.m5b2", "blocks/missing.m5b2"),),
    )

    with pytest.raises(ValueError, match="refusing to replace existing non-bundle output"):
        tool.create_bundle(out)

    assert marker.read_text(encoding="utf-8") == "old bundle"


def test_create_bundle_refuses_existing_non_bundle_output(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "important-dir"
    out.mkdir()
    marker = out / "keep.txt"
    marker.write_text("do not delete", encoding="utf-8")

    with pytest.raises(ValueError, match="refusing to replace existing non-bundle output"):
        tool.create_bundle(out)

    assert marker.read_text(encoding="utf-8") == "do not delete"


def test_create_bundle_refuses_existing_invalid_bundle_marker_output(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "important-dir"
    out.mkdir()
    (out / "offline_manifest.json").write_text("{}", encoding="utf-8")
    marker = out / "keep.txt"
    marker.write_text("do not delete", encoding="utf-8")

    with pytest.raises(ValueError, match="refusing to replace invalid existing bundle output"):
        tool.create_bundle(out)

    assert marker.read_text(encoding="utf-8") == "do not delete"


def test_create_bundle_refuses_repo_source_subdirectory():
    tool = load_offline_tool()

    with pytest.raises(ValueError, match="refusing to write bundle inside repository source tree"):
        tool.create_bundle(ROOT / "docs" / "offline")


def test_create_bundle_can_replace_previous_verified_bundle(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"

    tool.create_bundle(out)
    stale = out / "stale.txt"
    stale.write_text("old", encoding="utf-8")

    tool.create_bundle(out)

    assert not stale.exists()
    assert (out / "offline_manifest.json").exists()


def test_offline_deploy_dry_run_uploads_from_bundle_paths(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "deploy",
            "--port",
            "COM6",
            "--bundle",
            str(out),
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert str(out / "device" / "prop_frame.py") in result.stdout
    assert str(out / "device" / "prop_state.py") in result.stdout
    assert str(out / "device" / "prop_ui.py") in result.stdout
    assert str(out / "device" / "PropTx.py") in result.stdout
    assert str(out / "device" / "main.py") in result.stdout


def test_build_deploy_commands_rejects_non_list_device_files(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"] = "bad"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="device_files must be a list"):
        tool.build_deploy_commands("COM6", bundle=out)


def test_build_deploy_commands_rejects_non_object_device_file_entry(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"][0] = "bad"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=r"device_files\[0\] must be an object"):
        tool.build_deploy_commands("COM6", bundle=out)


def test_build_deploy_commands_rejects_missing_bundle_file(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    (out / "device" / "PropTx.py").unlink()

    with pytest.raises(ValueError, match="missing bundle file: device/PropTx.py"):
        tool.build_deploy_commands("COM6", bundle=out)


def test_build_deploy_commands_rejects_device_path_mismatch(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"][0]["device_path"] = "/flash/boot.py"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="device_path mismatch: device/prop_frame.py"):
        tool.build_deploy_commands("COM6", bundle=out)


def test_offline_verify_rejects_source_mismatch(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"][0]["source"] = "uiflow/dial/main.py"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "source mismatch: device/prop_frame.py" in errors


def test_offline_verify_rejects_unmanifested_bundle_file(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    (out / "device" / "extra.py").write_text("# extra\n", encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "unexpected bundle file: device/extra.py" in errors


def test_build_deploy_commands_rejects_bundle_target_dir_override(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)

    with pytest.raises(ValueError, match="invalid target-dir"):
        tool.build_deploy_commands("COM6", target_dir="/sd", bundle=out)


@pytest.mark.parametrize(
    "target_dir",
    ["flash", "/", "../flash", "/flash//nested", "/flash/../boot", r"\flash", "/flash:0"],
)
def test_build_deploy_commands_rejects_unsafe_direct_target_dir(target_dir):
    tool = load_offline_tool()

    with pytest.raises(ValueError, match="invalid target-dir"):
        tool.build_deploy_commands("COM6", target_dir=target_dir)


def test_offline_verify_rejects_bundle_target_dir_mismatch(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_target_dir"] = "/sd"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "device_target_dir must be /flash" in errors


def test_build_deploy_commands_rejects_partial_manifest(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"] = manifest["device_files"][:1]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="missing manifest entry: device/prop_ui.py"):
        tool.build_deploy_commands("COM6", bundle=out)


def test_build_deploy_commands_rejects_duplicate_manifest_entry(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"].append(dict(manifest["device_files"][0]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate manifest entry: device/prop_frame.py"):
        tool.build_deploy_commands("COM6", bundle=out)


def test_offline_deploy_requires_mpremote_for_real_upload(monkeypatch, tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: None)

    rc = tool.deploy("COM6", "/flash", dry_run=False, bundle=out)

    assert rc == 1


def test_offline_deploy_dry_run_warns_when_mpremote_is_missing(monkeypatch, tmp_path, capsys):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: None)

    rc = tool.deploy("COM6", "/flash", dry_run=True, bundle=out)

    assert rc == 0
    assert "mpremote is not installed" in capsys.readouterr().err


def test_offline_deploy_executes_bundle_upload_commands(monkeypatch, tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: object())
    expected = tool.build_deploy_commands("COM6", "/flash", out.resolve())
    calls = []

    def fake_run(command, cwd, check):
        calls.append((command, cwd, check))
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)

    rc = tool.deploy("COM6", "/flash", dry_run=False, bundle=out)

    assert rc == 0
    assert [command for command, _cwd, _check in calls] == expected
    assert {cwd for _command, cwd, _check in calls} == {tool.REPO_ROOT}
    assert {check for _command, _cwd, check in calls} == {False}


def test_uiflow_readme_documents_no_internet_deploy_path():
    readme = (ROOT / "uiflow" / "dial" / "README.md").read_text(encoding="utf-8")

    for needle in [
        "Offline runtime deploy",
        "Runtime-only offline path",
        "Block Designer / canvas path",
        "Choose this when you want the Dial to run without opening UIFlow2",
        "Choose this when you want visual block editing",
        "python tools/uiflow_dial_offline.py bundle",
        "python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline",
        "python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline",
        "python tools/uiflow_dial_offline.py deploy --port COM6",
        "build/uiflow_dial_offline/",
        "uiflow/dial/blocks/dist/PropTx.m5b2",
        "device/PropTx.py",
        "device/prop_state.py",
        "UIFlow2 canvas still needs UIFlow2 Web",
        "Dry smoke is not a production release",
        "The production-release gate stays closed while the prototype HMAC key is compiled in",
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_FILE",
        "~/.gemini_api_key",
        "Gemini code/workflow review gate",
        "python tools/gemini_code_review.py --dry-run --out build/reviews/gemini_code_review_prompt.md",
        "python tools/gemini_code_review.py --out build/reviews/gemini_code_review.md",
        "python tools/gemini_jury.py --dir build/preview",
        "mpremote",
    ]:
        assert needle in readme


def test_build_readme_separates_dry_smoke_from_release_acceptance():
    build = (ROOT / "BUILD.md").read_text(encoding="utf-8")

    for needle in [
        "Acceptance levels",
        "Dry smoke",
        "Production release",
        "prototype HMAC key",
        "PROP_ALLOW_PROTOTYPE_SHARED_KEY=0",
        "PROP_TX_ALLOW_SELFTEST_FIRE=0",
        "SELFTEST_FIRE=0",
        "Do not connect live pyro or actuator outputs",
        "reply must show ARMED",
        "STOP must clear output within one operator-visible cycle",
        "COM6 is only an example",
        "uiflow/dial/README.md",
        "UIFlow2 Dial offline workflow",
    ]:
        assert needle in build
