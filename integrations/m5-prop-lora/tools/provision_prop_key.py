from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "build" / "prop_key_provisioning"
PROTOTYPE_KEY_HEX = "00112233445566778899aabbccddeeff"
MIN_RUNTIME_KEY_BYTES = 16
MAX_RUNTIME_KEY_BYTES = 64
DEFAULT_NVS_SIZE = "0x6000"
DIAL_NVS_OFFSET = "0x9000"
DIAL_NVS_SIZE = "0x6000"
RECEIPT_TEMPLATE_NAME = "prop_key_receipt.template.json"


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_key_hex(value: str, *, allow_dry_smoke: bool = False) -> str:
    text = "".join(value.strip().replace(":", " ").split()).lower()
    if not text:
        raise ValueError("prop key hex is empty")
    if len(text) % 2:
        raise ValueError("prop key hex must have an even number of digits")
    if any(char not in "0123456789abcdef" for char in text):
        raise ValueError("prop key hex contains a non-hex character")
    key_len = len(text) // 2
    if key_len < MIN_RUNTIME_KEY_BYTES:
        raise ValueError("prop key must provide at least 16 bytes of HMAC key material")
    if key_len > MAX_RUNTIME_KEY_BYTES:
        raise ValueError("prop key must provide at most 64 bytes of HMAC key material")
    if text == PROTOTYPE_KEY_HEX and not allow_dry_smoke:
        raise ValueError("dry-smoke HMAC key requires --allow-dry-smoke and is not production")
    return text


def read_key_file(path: Path, *, allow_dry_smoke: bool = False) -> tuple[str, bytes]:
    try:
        raw = path.read_text(encoding="ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("prop key file must be ASCII hex") from exc
    key_hex = normalize_key_hex(raw, allow_dry_smoke=allow_dry_smoke)
    return key_hex, bytes.fromhex(key_hex)


def validate_output_path(out: Path, *, allow_external_output: bool = False) -> Path:
    resolved = out.resolve()
    if resolved == REPO_ROOT:
        raise ValueError("refusing to write provisioning material to repository root")
    if resolved.parent == resolved:
        raise ValueError("refusing to write provisioning material to filesystem root")
    build_root = (REPO_ROOT / "build").resolve()
    if _is_relative_to(resolved, REPO_ROOT) and not _is_relative_to(resolved, build_root):
        raise ValueError("refusing to write secret provisioning material inside source tree")
    if not allow_external_output and not _is_relative_to(resolved, build_root):
        raise ValueError("refusing external output without --allow-external-output")
    return resolved


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _header_bytes(key_bytes: bytes) -> str:
    rows = []
    for offset in range(0, len(key_bytes), 12):
        chunk = key_bytes[offset : offset + 12]
        rows.append("    " + ", ".join(f"0x{byte:02x}" for byte in chunk) + ",")
    return "\n".join(rows)


def _receipt_template(fingerprint: str, key_len: int) -> dict[str, object]:
    return {
        "schema": "prop-key-provisioning-receipt-v1",
        "status": "PENDING_HARDWARE",
        "namespace": "prop_key",
        "key": "shared",
        "expected_key_fingerprint_sha256": fingerprint,
        "expected_key_length_bytes": key_len,
        "secret_material_warning": (
            "Do not commit key files, prop_key.nvs.csv, prop_key_bytes.h, "
            "prop_key.nvs.bin, or readback/*.bin. Record only fingerprints."
        ),
        "nvs_image_warning": (
            "prop_key.nvs.bin is a complete NVS partition image and can overwrite "
            "existing target NVS settings."
        ),
        "dial": {
            "target": "M5 Dial ESP32-S3",
            "nvs_offset": DIAL_NVS_OFFSET,
            "nvs_size": DIAL_NVS_SIZE,
            "port": "<DIAL_COM>",
            "chip_id": "<esptool chip_id>",
            "mac": "<esptool read_mac>",
            "firmware_build": "<dial firmware build id / release flags>",
            "device_reported_key_fingerprint_sha256": "<sha256 from trusted readback or device report>",
            "nvs_readback_sha256": "<sha256(readback/dial_nvs.bin)>",
            "protection_posture": "<flash encryption / secure boot / waiver id>",
            "commands": [
                "python -m esptool --chip esp32s3 --port <DIAL_COM> chip_id",
                "python -m esptool --chip esp32s3 --port <DIAL_COM> read_mac",
                (
                    "python -m esptool --chip esp32s3 --port <DIAL_COM> "
                    f"read_flash {DIAL_NVS_OFFSET} {DIAL_NVS_SIZE} "
                    "build/prop_key_provisioning/readback/dial_nvs.bin"
                ),
                (
                    "python -c \"import hashlib,pathlib; "
                    "print(hashlib.sha256(pathlib.Path('build/prop_key_provisioning/"
                    "readback/dial_nvs.bin').read_bytes()).hexdigest())\""
                ),
            ],
        },
        "dinmeter": {
            "target": "M5 DinMeter / StampS3 ESP32-S3",
            "nvs_offset": "<DIN_NVS_OFFSET>",
            "nvs_size": "<DIN_NVS_SIZE>",
            "port": "<DIN_COM>",
            "chip_id": "<esptool chip_id>",
            "mac": "<esptool read_mac>",
            "firmware_build": "<din-rx firmware build id / release flags>",
            "device_reported_key_fingerprint_sha256": "<sha256 from trusted readback or device report>",
            "nvs_readback_sha256": "<sha256(readback/dinmeter_nvs.bin)>",
            "protection_posture": "<flash encryption / secure boot / waiver id>",
            "commands": [
                "python -m esptool --chip esp32s3 --port <DIN_COM> chip_id",
                "python -m esptool --chip esp32s3 --port <DIN_COM> read_mac",
                (
                    "python -m esptool --chip esp32s3 --port <DIN_COM> "
                    "read_flash 0x8000 0x1000 "
                    "build/prop_key_provisioning/readback/dinmeter_partitions.bin"
                ),
                "parse dinmeter_partitions.bin to find the active data,nvs offset and size",
                (
                    "python -m esptool --chip esp32s3 --port <DIN_COM> "
                    "read_flash <DIN_NVS_OFFSET> <DIN_NVS_SIZE> "
                    "build/prop_key_provisioning/readback/dinmeter_nvs.bin"
                ),
            ],
        },
        "acceptance": {
            "power_cycle_after_provisioning": False,
            "missing_or_mismatched_key_fails_closed": False,
            "dummy_load_positive_smoke_passed": False,
            "operator": "<name>",
            "date": "<YYYY-MM-DD>",
            "notes": "<non-secret notes only>",
        },
    }


def write_material(out: Path, key_hex: str, key_bytes: bytes) -> dict[str, object]:
    fingerprint = _sha256_bytes(key_bytes)
    csv_path = out / "prop_key.nvs.csv"
    header_path = out / "prop_key_bytes.h"
    manifest_path = out / "prop_key_manifest.json"
    readme_path = out / "README_PROVISIONING.txt"
    receipt_path = out / RECEIPT_TEMPLATE_NAME

    _write_text(
        csv_path,
        "\n".join(
            [
                "key,type,encoding,value",
                "prop_key,namespace,,",
                f"shared,data,hex2bin,{key_hex}",
                "",
            ]
        ),
    )
    _write_text(
        header_path,
        "\n".join(
            [
                "// GENERATED SECRET ARTIFACT. Do not commit or paste this file.",
                "// Include only in one-shot local provisioning firmware.",
                "#pragma once",
                "#include <stddef.h>",
                "#include <stdint.h>",
                "",
                f"static const uint8_t PROP_PROVISIONING_KEY[{len(key_bytes)}] = {{",
                _header_bytes(key_bytes),
                "};",
                f"static const size_t PROP_PROVISIONING_KEY_LEN = {len(key_bytes)};",
                "",
            ]
        ),
    )
    manifest = {
        "namespace": "prop_key",
        "key": "shared",
        "key_length_bytes": len(key_bytes),
        "key_fingerprint_sha256": fingerprint,
        "secret_artifacts": [
            csv_path.name,
            header_path.name,
        ],
        "non_secret_artifacts": [
            manifest_path.name,
            readme_path.name,
            receipt_path.name,
        ],
    }
    _write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    _write_text(
        receipt_path,
        json.dumps(_receipt_template(fingerprint, len(key_bytes)), indent=2, sort_keys=True)
        + "\n",
    )
    _write_text(
        readme_path,
        "\n".join(
            [
                "PropTx C++ runtime key provisioning material",
                "",
                "WARNING: prop_key.nvs.csv and prop_key_bytes.h contain secret key bytes.",
                "Keep this directory under ignored build output or another local secret store.",
                "",
                "NVS namespace/key:",
                "  namespace: prop_key",
                "  key: shared",
                "",
                "Use the same source key file for UIFlow:",
                "  python tools/uiflow_dial_offline.py bundle --production --prop-key-hex-file <key-file>",
                "  python tools/uiflow_dial_offline.py verify --production --prop-key-hex-file <key-file>",
                "",
                "Optional ESP-IDF NVS binary generation:",
                "  python tools/provision_prop_key.py --key-file <key-file> --generate-nvs-bin",
                "",
                "Hardware receipt template:",
                f"  {RECEIPT_TEMPLATE_NAME}",
                "Fill it only with device IDs, hashes, protection posture, and pass/fail",
                "evidence. Never paste key bytes into the receipt.",
                "",
                "Hardware acceptance still requires writing this material to the actual Dial and",
                "DinMeter, reading it back, and running the positive/negative smoke tests.",
                "",
            ]
        ),
    )
    return manifest


def find_nvs_partition_gen(explicit: str | None = None) -> Path | None:
    if explicit:
        return Path(explicit).resolve()
    from_path = shutil.which("nvs_partition_gen.py")
    if from_path:
        return Path(from_path).resolve()
    idf_path = os.environ.get("IDF_PATH")
    if idf_path:
        candidate = (
            Path(idf_path)
            / "components"
            / "nvs_flash"
            / "nvs_partition_generator"
            / "nvs_partition_gen.py"
        )
        if candidate.exists():
            return candidate.resolve()
    return None


def generate_nvs_bin(
    out: Path,
    *,
    nvs_partition_gen: Path | None = None,
    partition_size: str = DEFAULT_NVS_SIZE,
) -> list[str]:
    tool = find_nvs_partition_gen(str(nvs_partition_gen) if nvs_partition_gen else None)
    if tool is None or not tool.exists():
        raise ValueError(
            "nvs_partition_gen.py not found; pass --nvs-partition-gen or set IDF_PATH"
        )
    csv_path = out / "prop_key.nvs.csv"
    bin_path = out / "prop_key.nvs.bin"
    command = [
        sys.executable,
        str(tool),
        "generate",
        str(csv_path),
        str(bin_path),
        partition_size,
    ]
    subprocess.run(command, check=True)
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate ignored local provisioning material for PropTx C++ runtime keys."
    )
    parser.add_argument("--key-file", required=True, type=Path, help="local ignored hex key file")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument(
        "--allow-dry-smoke",
        action="store_true",
        help="allow the bench-only dry-smoke key; never use for production",
    )
    parser.add_argument(
        "--allow-external-output",
        action="store_true",
        help="allow output outside build/ for factory workstations",
    )
    parser.add_argument(
        "--generate-nvs-bin",
        action="store_true",
        help="also invoke ESP-IDF nvs_partition_gen.py to write prop_key.nvs.bin",
    )
    parser.add_argument("--nvs-partition-gen", type=Path, help="path to nvs_partition_gen.py")
    parser.add_argument("--partition-size", default=DEFAULT_NVS_SIZE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        key_hex, key_bytes = read_key_file(args.key_file, allow_dry_smoke=args.allow_dry_smoke)
        out = validate_output_path(args.out, allow_external_output=args.allow_external_output)
        manifest = write_material(out, key_hex, key_bytes)
        if args.generate_nvs_bin:
            command = generate_nvs_bin(
                out,
                nvs_partition_gen=args.nvs_partition_gen,
                partition_size=args.partition_size,
            )
            manifest["secret_artifacts"].append("prop_key.nvs.bin")
            manifest["nvs_partition_gen_command"] = command
            _write_text(out / "prop_key_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"wrote PropTx provisioning material to {out}")
        print(f"key length: {manifest['key_length_bytes']} bytes")
        print(f"key fingerprint sha256: {manifest['key_fingerprint_sha256']}")
        print("secret artifacts: " + ", ".join(manifest["secret_artifacts"]))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
