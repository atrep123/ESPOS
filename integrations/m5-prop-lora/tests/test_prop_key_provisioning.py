from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "provision_prop_key.py"
KEY_HEX = "102132435465768798a9babbdcddedef"
DRY_SMOKE_HEX = "00112233445566778899aabbccddeeff"


def _write_key(tmp_path: Path, value: str = KEY_HEX) -> Path:
    key_file = tmp_path / "prop-key.hex"
    key_file.write_text(value + "\n", encoding="ascii")
    return key_file


def test_provisioning_material_writes_secret_artifacts_without_printing_key(tmp_path):
    key_file = _write_key(tmp_path)
    out = tmp_path / "factory-out"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--key-file",
            str(key_file),
            "--out",
            str(out),
            "--allow-external-output",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert KEY_HEX not in result.stdout
    assert KEY_HEX not in result.stderr
    assert "key fingerprint sha256:" in result.stdout

    csv_text = (out / "prop_key.nvs.csv").read_text(encoding="utf-8")
    header_text = (out / "prop_key_bytes.h").read_text(encoding="utf-8")
    readme_text = (out / "README_PROVISIONING.txt").read_text(encoding="utf-8")
    receipt_text = (out / "prop_key_receipt.template.json").read_text(encoding="utf-8")
    receipt = json.loads(receipt_text)
    manifest = json.loads((out / "prop_key_manifest.json").read_text(encoding="utf-8"))

    assert "prop_key,namespace,," in csv_text
    assert f"shared,data,hex2bin,{KEY_HEX}" in csv_text
    assert "PROP_PROVISIONING_KEY" in header_text
    assert "0x10, 0x21, 0x32" in header_text
    assert KEY_HEX not in readme_text
    assert KEY_HEX not in receipt_text
    assert manifest["namespace"] == "prop_key"
    assert manifest["key"] == "shared"
    assert manifest["key_length_bytes"] == 16
    assert manifest["secret_artifacts"] == ["prop_key.nvs.csv", "prop_key_bytes.h"]
    assert "prop_key_receipt.template.json" in manifest["non_secret_artifacts"]
    assert receipt["schema"] == "prop-key-provisioning-receipt-v1"
    assert receipt["status"] == "PENDING_HARDWARE"
    assert receipt["expected_key_fingerprint_sha256"] == manifest["key_fingerprint_sha256"]
    assert receipt["expected_key_length_bytes"] == 16
    assert receipt["dial"]["nvs_offset"] == "0x9000"
    assert receipt["dial"]["nvs_size"] == "0x6000"
    assert "read_flash 0x9000 0x6000" in " ".join(receipt["dial"]["commands"])
    assert receipt["dinmeter"]["nvs_offset"] == "<DIN_NVS_OFFSET>"
    assert receipt["dinmeter"]["nvs_size"] == "<DIN_NVS_SIZE>"
    assert "complete NVS partition image" in receipt["nvs_image_warning"]
    assert "readback/*.bin" in receipt["secret_material_warning"]


def test_provisioning_material_rejects_source_tree_output(tmp_path):
    key_file = _write_key(tmp_path)
    out = ROOT / "tools" / "_bad_prop_key_out"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--key-file", str(key_file), "--out", str(out)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "source tree" in result.stderr
    assert not out.exists()


def test_provisioning_material_rejects_dry_smoke_key_without_flag(tmp_path):
    key_file = _write_key(tmp_path, DRY_SMOKE_HEX)
    out = tmp_path / "factory-out"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--key-file",
            str(key_file),
            "--out",
            str(out),
            "--allow-external-output",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "dry-smoke HMAC key requires --allow-dry-smoke" in result.stderr
    assert DRY_SMOKE_HEX not in result.stderr


def test_provisioning_material_can_invoke_nvs_partition_generator(tmp_path):
    key_file = _write_key(tmp_path)
    out = tmp_path / "factory-out"
    fake_gen = tmp_path / "nvs_partition_gen.py"
    fake_gen.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import json, sys",
                "Path(sys.argv[3]).write_bytes(b'NVS')",
                "Path(sys.argv[3]).with_suffix('.args.json').write_text(json.dumps(sys.argv[1:]))",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--key-file",
            str(key_file),
            "--out",
            str(out),
            "--allow-external-output",
            "--generate-nvs-bin",
            "--nvs-partition-gen",
            str(fake_gen),
            "--partition-size",
            "0x7000",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (out / "prop_key.nvs.bin").read_bytes() == b"NVS"
    manifest = json.loads((out / "prop_key_manifest.json").read_text(encoding="utf-8"))
    assert "prop_key.nvs.bin" in manifest["secret_artifacts"]
    assert manifest["nvs_partition_gen_command"][-1] == "0x7000"
