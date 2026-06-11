from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


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
    assert (out / "device" / "prop_ui.py").exists()
    assert (out / "device" / "PropTx.py").exists()
    assert (out / "blocks" / "PropTx.m5b2").exists()
    assert (out / "README_OFFLINE.txt").exists()
    manifest = json.loads((out / "offline_manifest.json").read_text(encoding="utf-8"))
    assert [item["device_path"] for item in manifest["device_files"]] == [
        "/flash/prop_frame.py",
        "/flash/prop_ui.py",
        "/flash/PropTx.py",
        "/flash/main.py",
    ]
    assert manifest["block_artifacts"][0]["bundle_path"] == "blocks/PropTx.m5b2"
    assert all(len(item["sha256"]) == 64 for item in manifest["device_files"])
    assert "offline UIFlow Dial bundle" in result.stdout


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
    assert "python -m mpremote connect COM6 fs mkdir /flash" in result.stdout
    assert "python -m mpremote connect COM6 fs cp" in result.stdout
    assert ":/flash/prop_frame.py" in result.stdout
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

    try:
        tool.create_bundle(out)
    except FileNotFoundError as exc:
        assert "does-not-exist.m5b2" in str(exc)
    else:
        raise AssertionError("create_bundle unexpectedly succeeded")

    assert marker.read_text(encoding="utf-8") == "old bundle"


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
        [sys.executable, str(SCRIPT), "deploy", "--port", "COM6", "--bundle", str(out), "--dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert str(out / "device" / "prop_frame.py") in result.stdout
    assert str(out / "device" / "prop_ui.py") in result.stdout
    assert str(out / "device" / "PropTx.py") in result.stdout
    assert str(out / "device" / "main.py") in result.stdout


def test_offline_deploy_requires_mpremote_for_real_upload(monkeypatch, tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: None)

    rc = tool.deploy("COM6", "/flash", dry_run=False, bundle=out)

    assert rc == 1


def test_uiflow_readme_documents_no_internet_deploy_path():
    readme = (ROOT / "uiflow" / "dial" / "README.md").read_text(encoding="utf-8")

    for needle in [
        "Offline runtime deploy",
        "python tools/uiflow_dial_offline.py bundle",
        "python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline",
        "python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline",
        "python tools/uiflow_dial_offline.py deploy --port COM6",
        "build/uiflow_dial_offline/",
        "uiflow/dial/blocks/dist/PropTx.m5b2",
        "device/PropTx.py",
        "UIFlow2 canvas still needs UIFlow2 Web",
        "GEMINI_API_KEY",
        "python tools/gemini_jury.py --dir build/preview",
        "mpremote",
    ]:
        assert needle in readme
