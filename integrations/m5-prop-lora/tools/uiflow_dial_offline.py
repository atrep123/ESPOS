from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "build" / "uiflow_dial_offline"
DEFAULT_TARGET_DIR = "/flash"


@dataclass(frozen=True)
class DeviceFile:
    source: str
    bundle_path: str
    device_name: str


@dataclass(frozen=True)
class BlockArtifact:
    source: str
    bundle_path: str


DEVICE_FILES = (
    DeviceFile("uiflow/dial/prop_frame.py", "device/prop_frame.py", "prop_frame.py"),
    DeviceFile("uiflow/dial/prop_ui.py", "device/prop_ui.py", "prop_ui.py"),
    DeviceFile("uiflow/dial/blocks/alpha2/PropTx.py", "device/PropTx.py", "PropTx.py"),
    DeviceFile("uiflow/dial/main.py", "device/main.py", "main.py"),
)

BLOCK_ARTIFACTS = (BlockArtifact("uiflow/dial/blocks/dist/PropTx.m5b2", "blocks/PropTx.m5b2"),)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_path(rel: str) -> Path:
    return REPO_ROOT / rel


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _validate_output_path(out: Path) -> None:
    resolved = out.resolve()
    if resolved == REPO_ROOT:
        raise ValueError("refusing to use repository root as bundle output")
    if resolved.parent == resolved:
        raise ValueError("refusing to use filesystem root as bundle output")
    for protected in ("firmware", "shared", "tests", "tools", "uiflow"):
        protected_path = (REPO_ROOT / protected).resolve()
        if _is_relative_to(resolved, protected_path):
            raise ValueError(f"refusing to write bundle inside source tree: {protected}")


def _preflight_sources() -> None:
    for item in DEVICE_FILES + BLOCK_ARTIFACTS:
        src = _repo_path(item.source)
        if not src.exists():
            raise FileNotFoundError(src)


def _write_bundle(out: Path) -> dict:
    out.mkdir(parents=True)

    manifest: dict[str, object] = {
        "name": "M5 Prop Dial offline UIFlow bundle",
        "device_target_dir": DEFAULT_TARGET_DIR,
        "device_files": [],
        "block_artifacts": [],
    }

    for item in DEVICE_FILES:
        src = _repo_path(item.source)
        dst = out / item.bundle_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest["device_files"].append(
            {
                "source": item.source,
                "bundle_path": item.bundle_path,
                "device_path": f"{DEFAULT_TARGET_DIR}/{item.device_name}",
                "sha256": _sha256(src),
            }
        )

    for item in BLOCK_ARTIFACTS:
        src = _repo_path(item.source)
        dst = out / item.bundle_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest["block_artifacts"].append(
            {
                "source": item.source,
                "bundle_path": item.bundle_path,
                "sha256": _sha256(src),
            }
        )

    (out / "offline_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "README_OFFLINE.txt").write_text(
        "\n".join(
            [
                "M5 Prop offline UIFlow Dial bundle",
                "",
                "Device upload files:",
                "  device/prop_frame.py -> /flash/prop_frame.py",
                "  device/prop_ui.py    -> /flash/prop_ui.py",
                "  device/PropTx.py     -> /flash/PropTx.py",
                "  device/main.py       -> /flash/main.py",
                "",
                "Custom block artifact:",
                "  blocks/PropTx.m5b2 -> UIFlow2 Custom -> Open",
                "",
                "Upload with:",
                "  python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline",
                "  python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def create_bundle(out: Path) -> dict:
    out = out.resolve()
    _validate_output_path(out)
    _preflight_sources()

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".{out.name}.tmp-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        manifest = _write_bundle(tmp)
        errors = verify_bundle(tmp)
        if errors:
            raise RuntimeError("staged bundle verification failed: " + "; ".join(errors))
        if out.exists():
            shutil.rmtree(out)
        shutil.move(str(tmp), str(out))
        return manifest
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def _load_bundle_manifest(bundle: Path) -> dict:
    manifest_path = bundle / "offline_manifest.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing manifest: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid manifest JSON: {manifest_path}: {exc}") from exc


def _expected_device_paths() -> dict[str, str]:
    return {item.bundle_path: f"{DEFAULT_TARGET_DIR}/{item.device_name}" for item in DEVICE_FILES}


def _expected_artifact_paths() -> set[str]:
    return {item.bundle_path for item in BLOCK_ARTIFACTS}


def _bundle_file_path(bundle: Path, bundle_path: str) -> Path | None:
    candidate = Path(bundle_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (bundle / candidate).resolve()
    if not _is_relative_to(resolved, bundle.resolve()):
        return None
    return resolved


def verify_bundle(bundle: Path) -> list[str]:
    errors: list[str] = []
    bundle = bundle.resolve()
    try:
        manifest = _load_bundle_manifest(bundle)
    except ValueError as exc:
        return [str(exc)]
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    expected_sections = {
        "device_files": set(_expected_device_paths()),
        "block_artifacts": _expected_artifact_paths(),
    }

    for section, expected_paths in expected_sections.items():
        entries = manifest.get(section, [])
        if not isinstance(entries, list):
            errors.append(f"{section} must be a list")
            continue
        seen_paths: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"{section} entry must be an object")
                continue
            bundle_path = entry.get("bundle_path")
            expected_hash = entry.get("sha256")
            if not isinstance(bundle_path, str) or not bundle_path:
                errors.append(f"{section} entry has no bundle_path")
                continue
            if bundle_path in seen_paths:
                errors.append(f"duplicate manifest entry: {bundle_path}")
                continue
            seen_paths.add(bundle_path)
            if bundle_path not in expected_paths:
                errors.append(f"unexpected manifest entry: {bundle_path}")
            path = _bundle_file_path(bundle, bundle_path)
            if path is None:
                errors.append(f"bundle_path escapes bundle: {bundle_path}")
                continue
            if not path.exists():
                errors.append(f"missing bundle file: {bundle_path}")
                continue
            if section == "device_files":
                expected_device_path = _expected_device_paths().get(bundle_path)
                if entry.get("device_path") != expected_device_path:
                    errors.append(f"device_path mismatch: {bundle_path}")
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                errors.append(f"invalid sha256 in manifest: {bundle_path}")
                continue
            actual_hash = _sha256(path)
            if actual_hash != expected_hash:
                errors.append(f"sha256 mismatch: {bundle_path}")
        for missing in sorted(expected_paths - seen_paths):
            errors.append(f"missing manifest entry: {missing}")

    return errors


def mpremote_command_prefix(port: str) -> list[str]:
    return [sys.executable, "-m", "mpremote", "connect", port]


def build_deploy_commands(
    port: str,
    target_dir: str = DEFAULT_TARGET_DIR,
    bundle: Path | None = None,
) -> list[list[str]]:
    commands = [mpremote_command_prefix(port) + ["fs", "mkdir", target_dir]]
    if bundle is not None:
        manifest = _load_bundle_manifest(bundle)
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be a JSON object")
        items = manifest.get("device_files")
        if not isinstance(items, list):
            raise ValueError("device_files must be a list")
        expected_device_paths = _expected_device_paths()
        for index, entry in enumerate(items):
            if not isinstance(entry, dict):
                raise ValueError(f"device_files[{index}] must be an object")
            bundle_path = entry.get("bundle_path")
            device_path = entry.get("device_path")
            if not isinstance(bundle_path, str) or not bundle_path:
                raise ValueError(f"device_files[{index}] has no bundle_path")
            if not isinstance(device_path, str) or not device_path:
                raise ValueError(f"device_files[{index}] has no device_path")
            src_path = _bundle_file_path(bundle, bundle_path)
            if src_path is None:
                raise ValueError(f"bundle_path escapes bundle: {bundle_path}")
            if not src_path.exists():
                raise ValueError(f"missing bundle file: {bundle_path}")
            if device_path != expected_device_paths.get(bundle_path):
                raise ValueError(f"device_path mismatch: {bundle_path}")
            device_name = Path(device_path).name
            dst = f":{target_dir.rstrip('/')}/{device_name}"
            commands.append(mpremote_command_prefix(port) + ["fs", "cp", str(src_path), dst])
        return commands

    for item in DEVICE_FILES:
        src = str(_repo_path(item.source))
        dst = f":{target_dir.rstrip('/')}/{item.device_name}"
        commands.append(mpremote_command_prefix(port) + ["fs", "cp", src, dst])
    return commands


def format_command(command: list[str]) -> str:
    display = ["python" if part == sys.executable else part for part in command]
    return subprocess.list2cmdline(display)


def deploy(port: str, target_dir: str, dry_run: bool, bundle: Path | None = None) -> int:
    bundle_path = bundle.resolve() if bundle is not None else None
    if bundle_path is not None:
        errors = verify_bundle(bundle_path)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1

    if not dry_run and importlib.util.find_spec("mpremote") is None:
        print(
            "mpremote is not installed for this Python; install it before real deploy",
            file=sys.stderr,
        )
        return 1

    commands = build_deploy_commands(port, target_dir, bundle_path)
    if dry_run:
        print("DRY RUN: mpremote commands for offline Dial upload")
        for command in commands:
            print(format_command(command))
        print("PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload")
        return 0

    for index, command in enumerate(commands):
        print(format_command(command))
        result = subprocess.run(command, cwd=REPO_ROOT, check=False)
        if result.returncode != 0 and index == 0:
            print(
                f"warning: could not create {target_dir}; continuing in case it already exists",
                file=sys.stderr,
            )
            continue
        if result.returncode != 0:
            return result.returncode
    print("Offline Dial runtime uploaded.")
    print("PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or upload the offline UIFlow Dial bundle."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bundle_parser = sub.add_parser(
        "bundle", help="copy runtime files and block artifacts into a local bundle"
    )
    bundle_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)

    verify_parser = sub.add_parser("verify", help="verify bundle manifest files and SHA-256 hashes")
    verify_parser.add_argument("--bundle", type=Path, default=DEFAULT_OUT)

    deploy_parser = sub.add_parser(
        "deploy", help="upload runtime files to a USB-connected M5 Dial via mpremote"
    )
    deploy_parser.add_argument("--port", required=True, help="serial port, for example COM6")
    deploy_parser.add_argument("--bundle", type=Path, default=None)
    deploy_parser.add_argument("--target-dir", default=DEFAULT_TARGET_DIR)
    deploy_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "bundle":
        manifest = create_bundle(args.out)
        print(f"offline UIFlow Dial bundle written to {args.out}")
        print(f"device files: {len(manifest['device_files'])}")
        print(f"block artifacts: {len(manifest['block_artifacts'])}")
        return 0
    if args.command == "verify":
        bundle = args.bundle.resolve()
        errors = verify_bundle(bundle)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"verified offline UIFlow Dial bundle: {bundle}")
        return 0
    if args.command == "deploy":
        return deploy(args.port, args.target_dir, args.dry_run, args.bundle)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
