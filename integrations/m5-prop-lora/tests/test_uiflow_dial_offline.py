from __future__ import annotations

import json
import hashlib
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


def test_rebuild_tolerated_errors_do_not_mask_key_drift():
    tool = load_offline_tool()

    assert tool._is_rebuild_tolerated_bundle_error(
        "source_sha256 mismatch: blocks/PropTx.m5b2"
    )
    assert tool._is_rebuild_tolerated_bundle_error(
        "local_dependencies mismatch: device/main.py"
    )
    for error in (
        "key_kind mismatch: device/prop_key.py",
        "invalid key_fingerprint in manifest: device/prop_key.py",
        "key_fingerprint mismatch: device/prop_key.py",
    ):
        assert not tool._is_rebuild_tolerated_bundle_error(error)


def test_offline_bundle_contains_runtime_files_and_block_artifact(tmp_path):
    out = tmp_path / "offline"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out), "--dry-smoke"],
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
    assert (out / "device" / "prop_key.py").exists()
    assert (out / "blocks" / "PropTx.m5b2").exists()
    assert (out / "README_OFFLINE.txt").exists()
    manifest = json.loads((out / "offline_manifest.json").read_text(encoding="utf-8"))
    assert [item["device_path"] for item in manifest["device_files"]] == [
        "/flash/prop_frame.py",
        "/flash/prop_state.py",
        "/flash/prop_ui.py",
        "/flash/PropTx.py",
        "/flash/main.py",
        "/flash/prop_key.py",
    ]
    deps = {item["bundle_path"]: item["local_dependencies"] for item in manifest["device_files"]}
    assert deps["device/main.py"] == ["device/prop_frame.py", "device/prop_state.py"]
    assert deps["device/PropTx.py"] == ["device/prop_frame.py", "device/prop_ui.py"]
    assert deps["device/prop_frame.py"] == ["device/prop_key.py"]
    assert deps["device/prop_key.py"] == []
    assert manifest["block_artifacts"][0]["bundle_path"] == "blocks/PropTx.m5b2"
    assert manifest["block_artifacts"][0]["source_bundle_path"] == "device/PropTx.py"
    assert manifest["block_artifacts"][0]["source_sha256"] == next(
        item["sha256"]
        for item in manifest["device_files"]
        if item["bundle_path"] == "device/PropTx.py"
    )
    assert all(len(item["sha256"]) == 64 for item in manifest["device_files"])
    assert len(manifest["block_artifacts"][0]["source_sha256"]) == 64
    offline_readme = (out / "README_OFFLINE.txt").read_text(encoding="utf-8")
    assert "PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload" in offline_readme
    assert "UIFlow2 processes .m5b2 locally" in offline_readme
    assert "PropTx.py is the runtime file uploaded to /flash" in offline_readme
    assert "offline UIFlow Dial bundle" in result.stdout


def test_offline_bundle_runtime_uses_fire_burst_path(tmp_path):
    out = tmp_path / "offline"

    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out), "--dry-smoke"],
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
    assert "self._tx.fire_burst_lines(_first_four_for_frame(self, colors))" in prop_tx
    assert "fire_line(_colors[:4])" not in main_py
    assert "self._tx.fire_line(colors)" not in prop_tx


def test_offline_deploy_dry_run_prints_mpremote_upload_commands(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out), "--dry-smoke"],
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
            "--dry-smoke",
            "--dry-run",
        ],
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
    assert ":/flash/prop_key.py" in result.stdout
    assert "PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload" in result.stdout
    assert "UIFlow2 processes .m5b2 locally" in result.stdout


def test_offline_deploy_rejects_dry_smoke_bundle_without_dry_smoke_flag(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out), "--dry-smoke"],
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

    assert result.returncode == 1
    assert "dry-smoke deploy requires --dry-smoke" in result.stderr


def test_offline_deploy_rejects_dry_smoke_with_key_file(tmp_path, capsys):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    tool.create_bundle(out, dry_smoke=True)

    rc = tool.deploy(
        "COM6",
        "/flash",
        dry_run=True,
        bundle=out,
        dry_smoke=True,
        prop_key_hex_file=key_file,
    )

    assert rc == 1
    assert "--dry-smoke cannot be combined with --prop-key-hex-file" in capsys.readouterr().err


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


def test_offline_verify_production_rejects_dry_smoke_bundle(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out), "--dry-smoke"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out), "--production"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "device/prop_key.py must set ALLOW_PROTOTYPE_SHARED_KEY = False" in result.stderr


def test_production_bundle_requires_explicit_external_output_for_secret_material(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")

    rejected = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert rejected.returncode == 1
    assert "refusing external output for production bundle" in rejected.stderr
    assert "102132435465768798a9babbdcddedef" not in rejected.stdout
    assert "102132435465768798a9babbdcddedef" not in rejected.stderr

    accepted = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert accepted.returncode == 0, accepted.stderr
    assert "secret device/prop_key.py material" in accepted.stderr
    assert "102132435465768798a9babbdcddedef" not in accepted.stdout
    assert "102132435465768798a9babbdcddedef" not in accepted.stderr


def test_offline_bundle_can_include_non_source_prop_key_for_production(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")

    bundle = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert bundle.returncode == 0, bundle.stderr
    prop_key = out / "device" / "prop_key.py"
    assert prop_key.exists()
    prop_key_text = prop_key.read_text(encoding="utf-8")
    assert "ALLOW_PROTOTYPE_SHARED_KEY = False" in prop_key_text
    assert 'SHARED_KEY_HEX = "102132435465768798a9babbdcddedef"' in prop_key_text
    manifest = json.loads((out / "offline_manifest.json").read_text(encoding="utf-8"))
    manifest_text = (out / "offline_manifest.json").read_text(encoding="utf-8")
    device_paths = [item["device_path"] for item in manifest["device_files"]]
    assert "/flash/prop_key.py" in device_paths
    prop_key_entry = next(
        item for item in manifest["device_files"] if item["bundle_path"] == "device/prop_key.py"
    )
    assert prop_key_entry["key_kind"] == "production"
    assert (
        prop_key_entry["key_fingerprint"]
        == "c02c42cb6182084362983304a0eb7c1b0b9d9fc035018b1ab35881830714a8a9"
    )
    assert "102132435465768798a9babbdcddedef" not in manifest_text
    offline_readme = (out / "README_OFFLINE.txt").read_text(encoding="utf-8")
    assert "verify --bundle build/uiflow_dial_offline --production --prop-key-hex-file <local-key-file>" in offline_readme
    assert "deploy --port COM6 --bundle build/uiflow_dial_offline --production --prop-key-hex-file <local-key-file>" in offline_readme

    verify = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "verify",
            "--bundle",
            str(out),
            "--production",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert verify.returncode == 0, verify.stderr
    assert "verified production offline UIFlow Dial bundle" in verify.stdout

    dry_run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "deploy",
            "--port",
            "COM6",
            "--bundle",
            str(out),
            "--production",
            "--prop-key-hex-file",
            str(key_file),
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert dry_run.returncode == 0, dry_run.stderr
    assert ":/flash/prop_key.py" in dry_run.stdout
    assert "102132435465768798a9babbdcddedef" not in dry_run.stdout


def test_offline_bundle_rejects_key_file_without_production_ack(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "--prop-key-hex-file requires --production" in result.stderr
    assert not out.exists()


def test_offline_verify_rejects_key_file_without_production_ack(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    tool.create_bundle(out)

    errors = tool.verify_bundle(out, prop_key_hex_file=key_file)

    assert "--prop-key-hex-file requires --production" in errors


def test_offline_verify_production_requires_local_key_file(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    verify = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--bundle", str(out), "--production"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert verify.returncode == 1
    assert "--production requires --prop-key-hex-file" in verify.stderr


def test_offline_verify_rejects_production_key_bundle_without_production_flag(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    verify = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "verify",
            "--bundle",
            str(out),
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert verify.returncode == 1
    assert "production bundle requires --production" in verify.stderr


def test_offline_deploy_rejects_production_key_bundle_without_local_key_file(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    deploy = subprocess.run(
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

    assert deploy.returncode == 1
    assert "production bundle requires --production" in deploy.stderr
    assert "production bundle requires --prop-key-hex-file" in deploy.stderr


def test_offline_deploy_rejects_production_key_bundle_without_production_flag(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    deploy = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "deploy",
            "--port",
            "COM6",
            "--bundle",
            str(out),
            "--prop-key-hex-file",
            str(key_file),
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert deploy.returncode == 1
    assert "--prop-key-hex-file requires --production" in deploy.stderr


def test_offline_verify_rejects_mismatched_production_key_file(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    other_key_file = tmp_path / "other.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    other_key_file.write_text("202132435465768798a9babbdcddedef\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    verify = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "verify",
            "--bundle",
            str(out),
            "--production",
            "--prop-key-hex-file",
            str(other_key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert verify.returncode == 1
    assert "prop_key_hex_file mismatch: device/prop_key.py" in verify.stderr


def test_offline_bundle_refuses_prototype_prop_key_file(tmp_path):
    tool = load_offline_tool()
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("00112233445566778899aabbccddeeff\n", encoding="utf-8")

    with pytest.raises(ValueError, match="refusing to bundle prototype HMAC key"):
        tool.create_bundle(
            tmp_path / "offline",
            production=True,
            prop_key_hex_file=key_file,
            allow_external_output=True,
        )


def test_offline_bundle_refuses_keys_longer_than_cxx_runtime_limit(tmp_path):
    tool = load_offline_tool()
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("aa" * 65 + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="at most 64 bytes"):
        tool.create_bundle(
            tmp_path / "offline",
            production=True,
            prop_key_hex_file=key_file,
            allow_external_output=True,
        )


def test_offline_verify_rejects_non_bool_prototype_flag(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    prop_key = out / "device" / "prop_key.py"
    prop_key.write_text(
        'ALLOW_PROTOTYPE_SHARED_KEY = "yes"\n'
        'SHARED_KEY_HEX = "00112233445566778899aabbccddeeff"\n',
        encoding="utf-8",
    )
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry["bundle_path"] == "device/prop_key.py":
            entry["sha256"] = tool._sha256(prop_key)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "device/prop_key.py ALLOW_PROTOTYPE_SHARED_KEY must be literal True or False" in errors
    assert "key_kind mismatch: device/prop_key.py" not in errors


def test_offline_verify_production_rejects_shadowing_shared_key(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    tool.create_bundle(
        out,
        production=True,
        prop_key_hex_file=key_file,
        allow_external_output=True,
    )

    prop_key = out / "device" / "prop_key.py"
    prop_key.write_text(
        'ALLOW_PROTOTYPE_SHARED_KEY = False\n'
        'SHARED_KEY_HEX = "102132435465768798a9babbdcddedef"\n'
        'SHARED_KEY = bytes.fromhex("00112233445566778899aabbccddeeff")\n',
        encoding="utf-8",
    )
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry["bundle_path"] == "device/prop_key.py":
            entry["sha256"] = tool._sha256(prop_key)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out, production=True)

    assert "device/prop_key.py must not define SHARED_KEY; use SHARED_KEY_HEX" in errors


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
    assert "source_sha256 mismatch: blocks/PropTx.m5b2" in result.stderr


def test_offline_verify_production_rejects_tampered_artifact_source(tmp_path):
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bundle",
            "--out",
            str(out),
            "--production",
            "--allow-external-output",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    (out / "device" / "PropTx.py").write_text("# tampered\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "verify",
            "--bundle",
            str(out),
            "--production",
            "--prop-key-hex-file",
            str(key_file),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "sha256 mismatch: device/PropTx.py" in result.stderr
    assert "source_sha256 mismatch: blocks/PropTx.m5b2" in result.stderr


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


def test_offline_verify_rejects_artifact_pycode_drift_even_with_refreshed_manifest_hash(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    artifact_path = out / "blocks" / "PropTx.m5b2"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["pyCode"] = "# drifted runtime source\n"
    artifact_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["block_artifacts"][0]["sha256"] = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
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
    assert "sha256 mismatch: blocks/PropTx.m5b2" not in result.stderr
    assert "block artifact pyCode mismatch: blocks/PropTx.m5b2" in result.stderr


def test_offline_verify_rejects_device_file_drift_from_current_repo_source(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    prop_tx = out / "device" / "PropTx.py"
    prop_tx.write_text(prop_tx.read_text(encoding="utf-8") + "\n# stale bundle copy\n", encoding="utf-8")
    artifact_path = out / "blocks" / "PropTx.m5b2"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["pyCode"] = prop_tx.read_text(encoding="utf-8")
    artifact_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry["bundle_path"] == "device/PropTx.py":
            entry["sha256"] = tool._sha256(prop_tx)
    for entry in manifest["block_artifacts"]:
        if entry["bundle_path"] == "blocks/PropTx.m5b2":
            entry["sha256"] = tool._sha256(artifact_path)
            entry["source_sha256"] = tool._sha256(prop_tx)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "current source mismatch: device/PropTx.py" in errors
    assert "sha256 mismatch: device/PropTx.py" not in errors
    assert "source_sha256 mismatch: blocks/PropTx.m5b2" not in errors


def test_offline_verify_rejects_block_artifact_drift_from_current_repo_source(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    artifact_path = out / "blocks" / "PropTx.m5b2"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["data"]["members"].append({"name": "sync_palette", "type": "method"})
    artifact_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["block_artifacts"]:
        if entry["bundle_path"] == "blocks/PropTx.m5b2":
            entry["sha256"] = tool._sha256(artifact_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "current source mismatch: blocks/PropTx.m5b2" in errors
    assert "sha256 mismatch: blocks/PropTx.m5b2" not in errors


def test_create_bundle_can_replace_previous_bundle_with_current_source_drift(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    prop_tx = out / "device" / "PropTx.py"
    prop_tx.write_text(prop_tx.read_text(encoding="utf-8") + "\n# stale bundle copy\n", encoding="utf-8")
    artifact_path = out / "blocks" / "PropTx.m5b2"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["pyCode"] = prop_tx.read_text(encoding="utf-8")
    artifact_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry["bundle_path"] == "device/PropTx.py":
            entry["sha256"] = tool._sha256(prop_tx)
    for entry in manifest["block_artifacts"]:
        if entry["bundle_path"] == "blocks/PropTx.m5b2":
            entry["sha256"] = tool._sha256(artifact_path)
            entry["source_sha256"] = tool._sha256(prop_tx)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    tool.create_bundle(out)

    assert tool.verify_bundle(out) == []


def test_offline_verify_rejects_missing_artifact_source_hash(tmp_path):
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
    manifest["block_artifacts"][0].pop("source_sha256")
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
    assert "invalid source_sha256 in manifest: blocks/PropTx.m5b2" in result.stderr


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


def test_create_bundle_runs_block_artifact_preflight(monkeypatch, tmp_path):
    tool = load_offline_tool()

    def fail_validation():
        raise ValueError("UIFlow block validation failed: drift")

    monkeypatch.setattr(tool, "_validate_block_artifacts", fail_validation)

    with pytest.raises(ValueError, match="UIFlow block validation failed: drift"):
        tool.create_bundle(tmp_path / "offline")


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


def test_create_bundle_refuses_generated_looking_but_incomplete_bundle_output(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "important-dir"
    out.mkdir()
    marker = out / "keep.txt"
    marker.write_text("do not delete", encoding="utf-8")
    (out / "offline_manifest.json").write_text(
        json.dumps(
            {
                "name": "M5 Prop Dial offline UIFlow bundle",
                "device_target_dir": "/flash",
                "device_files": [],
                "block_artifacts": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="refusing to replace invalid existing bundle output"):
        tool.create_bundle(out)

    assert marker.read_text(encoding="utf-8") == "do not delete"


def test_create_bundle_refuses_repo_source_subdirectory():
    tool = load_offline_tool()

    with pytest.raises(ValueError, match="refusing to write bundle inside repository source tree"):
        tool.create_bundle(ROOT / "docs" / "offline")


def test_create_bundle_refuses_existing_bundle_with_unexpected_files(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"

    tool.create_bundle(out)
    manual = out / "manual-notes.txt"
    manual.write_text("keep me\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected bundle file: manual-notes.txt"):
        tool.create_bundle(out)

    assert manual.read_text(encoding="utf-8") == "keep me\n"


def test_create_bundle_can_replace_previous_verified_bundle(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"

    tool.create_bundle(out)
    tool.create_bundle(out)

    assert (out / "offline_manifest.json").exists()


def test_create_bundle_can_replace_previous_bundle_schema_without_local_dependencies(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"

    tool.create_bundle(out)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        entry.pop("local_dependencies", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    tool.create_bundle(out)
    refreshed = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert all("local_dependencies" in entry for entry in refreshed["device_files"])


def test_create_bundle_can_replace_previous_bundle_schema_without_key_fingerprint(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"

    tool.create_bundle(out, dry_smoke=True)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry.get("bundle_path") == "device/prop_key.py":
            entry.pop("key_kind", None)
            entry.pop("key_fingerprint", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    tool.create_bundle(out, dry_smoke=True)
    refreshed = json.loads(manifest_path.read_text(encoding="utf-8"))
    prop_key_entry = next(
        entry for entry in refreshed["device_files"] if entry["bundle_path"] == "device/prop_key.py"
    )

    assert prop_key_entry["key_kind"] == "dry-smoke"
    assert len(prop_key_entry["key_fingerprint"]) == 64


def test_create_bundle_can_replace_previous_production_bundle(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")

    tool.create_bundle(
        out,
        production=True,
        prop_key_hex_file=key_file,
        allow_external_output=True,
    )
    tool.create_bundle(
        out,
        production=True,
        prop_key_hex_file=key_file,
        allow_external_output=True,
    )

    errors = tool.verify_bundle(out, production=True, prop_key_hex_file=key_file)
    assert errors == []


def test_offline_deploy_dry_run_uploads_from_bundle_paths(tmp_path):
    out = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(SCRIPT), "bundle", "--out", str(out), "--dry-smoke"],
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
            "--dry-smoke",
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
    assert str(out / "device" / "prop_key.py") in result.stdout


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


def test_build_deploy_commands_rejects_key_file_without_production_ack(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    key_file = tmp_path / "prop_key.hex"
    key_file.write_text("102132435465768798a9babbdcddedef\n", encoding="utf-8")
    tool.create_bundle(out)

    with pytest.raises(ValueError, match="--prop-key-hex-file requires --production"):
        tool.build_deploy_commands("COM6", bundle=out, prop_key_hex_file=key_file)


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
    [
        "flash",
        "/",
        "../flash",
        "/flash//nested",
        "/flash/../boot",
        r"\flash",
        "/flash:0",
        "/flash/nested",
        "/flash/boot.py",
        "/flash/foo bar",
    ],
)
def test_build_deploy_commands_rejects_unsafe_direct_target_dir(target_dir):
    tool = load_offline_tool()

    with pytest.raises(ValueError, match="invalid target-dir"):
        tool.build_deploy_commands("COM6", target_dir=target_dir)


@pytest.mark.parametrize(
    "port",
    ["", "COM6&whoami", "COM6;whoami", "COM6|whoami", "COM6>out", "COM6 name"],
)
def test_build_deploy_commands_rejects_shell_unsafe_port(port):
    tool = load_offline_tool()

    with pytest.raises(ValueError, match="invalid port"):
        tool.build_deploy_commands(port)


def test_offline_deploy_cli_reports_invalid_target_dir_without_traceback():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "deploy",
            "--port",
            "COM6",
            "--target-dir",
            "/flash/nested",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "invalid target-dir: /flash/nested" in result.stderr
    assert "Traceback" not in result.stderr


def test_offline_verify_rejects_bundle_target_dir_mismatch(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_target_dir"] = "/sd"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "device_target_dir must be /flash" in errors


def test_offline_verify_rejects_local_dependency_mismatch(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry["bundle_path"] == "device/main.py":
            entry["local_dependencies"] = ["device/prop_frame.py"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "local_dependencies mismatch: device/main.py" in errors


def test_offline_verify_computes_local_dependencies_from_bundle_files(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    main_py = out / "device" / "main.py"
    main_py.write_text("import prop_frame as pf\nprint(pf.MAGIC)\n", encoding="utf-8")
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["device_files"]:
        if entry["bundle_path"] == "device/main.py":
            entry["sha256"] = tool._sha256(main_py)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = tool.verify_bundle(out)

    assert "local_dependencies mismatch: device/main.py" in errors


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


def test_offline_deploy_requires_mpremote_for_real_upload(monkeypatch, tmp_path, capsys):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: None)

    rc = tool.deploy("COM6", "/flash", dry_run=False, bundle=out, dry_smoke=True)

    assert rc == 1
    assert "mpremote is not installed" in capsys.readouterr().err


def test_offline_deploy_reports_no_key_bundle_before_mpremote_check(
    monkeypatch, tmp_path, capsys
):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: None)

    rc = tool.deploy("COM6", "/flash", dry_run=False, bundle=out)

    assert rc == 1
    stderr = capsys.readouterr().err
    assert (
        "deploy bundle requires device/prop_key.py; rebuild with --dry-smoke "
        "or --production --prop-key-hex-file"
    ) in stderr
    assert "mpremote is not installed" not in stderr


def test_offline_deploy_dry_run_warns_when_mpremote_is_missing(monkeypatch, tmp_path, capsys):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: None)

    rc = tool.deploy("COM6", "/flash", dry_run=True, bundle=out, dry_smoke=True)

    assert rc == 0
    assert "mpremote is not installed" in capsys.readouterr().err


def test_offline_deploy_executes_bundle_upload_commands(monkeypatch, tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    monkeypatch.setattr(tool.importlib.util, "find_spec", lambda name: object())
    expected = tool.build_deploy_commands("COM6", "/flash", out.resolve(), dry_smoke=True)
    calls = []

    def fake_run(command, cwd, check):
        calls.append((command, cwd, check))
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)

    rc = tool.deploy("COM6", "/flash", dry_run=False, bundle=out, dry_smoke=True)

    assert rc == 0
    assert [command for command, _cwd, _check in calls] == expected
    assert {cwd for _command, cwd, _check in calls} == {tool.REPO_ROOT}
    assert {check for _command, _cwd, check in calls} == {False}


def test_offline_deploy_uses_canonical_dependency_first_upload_order(tmp_path):
    tool = load_offline_tool()
    out = tmp_path / "offline"
    tool.create_bundle(out, dry_smoke=True)
    manifest_path = out / "offline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["device_files"] = list(reversed(manifest["device_files"]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    commands = tool.build_deploy_commands("COM6", bundle=out, dry_smoke=True)
    uploads = [command for command in commands if command[-1].startswith(":/flash/")]

    assert [command[-1] for command in uploads] == [
        ":/flash/prop_key.py",
        ":/flash/prop_frame.py",
        ":/flash/prop_state.py",
        ":/flash/prop_ui.py",
        ":/flash/PropTx.py",
        ":/flash/main.py",
    ]


def test_uiflow_readme_documents_no_internet_deploy_path():
    readme = (ROOT / "uiflow" / "dial" / "README.md").read_text(encoding="utf-8")

    for needle in [
        "Offline runtime deploy",
        "Runtime-only offline path",
        "Block Designer / canvas path",
        "Choose this when you want the Dial to run without opening UIFlow2",
        "Choose this when you want visual block editing",
        "python tools/uiflow_dial_offline.py bundle --dry-smoke",
        "python tools/uiflow_dial_offline.py bundle --production --prop-key-hex-file",
        "python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline",
        "python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline --production",
        "production verify",
        "--prop-key-hex-file ...",
        "python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline",
        "python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline --dry-smoke --dry-run",
        "python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline --production --prop-key-hex-file C:\\path\\to\\prop-key.hex",
        "build/uiflow_dial_offline/",
        "uiflow/dial/blocks/dist/PropTx.m5b2",
        "build/uiflow_dial_offline/blocks/PropTx.m5b2",
        "`prop_key.py`, `prop_frame.py`",
        "device/prop_key.py",
        "device/PropTx.py",
        "device/prop_state.py",
        "local runtime dependency list",
        "non-secret SHA-256 fingerprint",
        "mismatched key files fail verification",
        "UIFlow2 canvas still needs UIFlow2 Web",
        "Dry smoke is not a production release",
        "runtime has no compiled HMAC key",
        "fails closed until `/flash/prop_key.py` is uploaded",
        "C++ Dial/DinMeter firmware also loads its HMAC key at runtime",
        "prop_key/shared",
        "must come from the same local secret",
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_FILE",
        "~/.gemini_api_key",
        "Gemini code/workflow review gate",
        "python tools/gemini_code_review.py --dry-run --out build/reviews/gemini_code_review_prompt.md",
        "python tools/gemini_code_review.py --out build/reviews/gemini_code_review.md",
        "python tools/gemini_jury.py --dir build/preview",
        "mpremote",
        "current C++ firmware FIRE path",
        "receiver reboot clears the volatile STOP latch",
        "lastSeq/epoch replay high-water persists",
    ]:
        assert needle in readme

    for stale in [
        "production FIRE path",
        "production C++ default",
        "Import `blocks/PropTx.m5b2`",
    ]:
        assert stale not in readme


def test_build_readme_separates_dry_smoke_from_release_acceptance():
    build = (ROOT / "BUILD.md").read_text(encoding="utf-8")

    for needle in [
        "Acceptance levels",
        "Dry smoke",
        "Production release",
        "runtime key from NVS/Preferences namespace `prop_key`, key `shared`",
        "there is no compiled fallback",
        "runtime key is present on target",
        "PROP_TX_ALLOW_SELFTEST_FIRE=0",
        "SELFTEST_FIRE=0",
        "Do not connect live pyro or actuator outputs",
        "reply must show ARMED",
        "STOP must clear output within one operator-visible cycle",
        "COM6 is only an example",
        "uiflow/dial/README.md",
        "UIFlow2 Dial offline workflow",
        "Receiver reboot clears the volatile STOP latch",
        "lastSeq/epoch replay high-water persists",
    ]:
        assert needle in build


def test_bench_checklist_states_field_acceptance_status():
    checklist = (ROOT / "docs" / "bench_test_checklist.md").read_text(
        encoding="utf-8"
    )

    for needle in [
        "Field acceptance status",
        "Dry smoke only",
        "dummy/LED-only load",
        "Production release requires",
        "same non-source HMAC key",
        "COM ports below are examples",
        "docs/cxx_key_provisioning.md",
        "sha256(key_bytes)",
        "KEY MISSING` for the HMAC runtime key",
        "separate from the physical",
        "mpremote",
        "UIFlow2 canvas still needs UIFlow2 Web",
        "No Gemini secret is committed",
        "GEMINI_API_KEY",
        "receiver reboot clears STOP latch as a local reset",
        "lastSeq/epoch replay high-water persists",
        "Chain Key",
        "FIRE KEY MISSING",
        "press before ARM must not fire",
        "ARM then physical Chain Key press fires",
        "missing/undetected key fails safe",
    ]:
        assert needle in checklist
