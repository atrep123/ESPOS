from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "build" / "uiflow_dial_offline"
DEFAULT_TARGET_DIR = "/flash"
BUNDLE_NAME = "M5 Prop Dial offline UIFlow bundle"
PROP_KEY_BUNDLE_PATH = "device/prop_key.py"
PROP_KEY_DEVICE_PATH = f"{DEFAULT_TARGET_DIR}/prop_key.py"
PROP_KEY_SOURCE_LABEL = "<local prop-key-hex-file>"
PROTOTYPE_KEY_HEX = "00112233445566778899aabbccddeeff"
MIN_RUNTIME_KEY_BYTES = 16
MAX_RUNTIME_KEY_BYTES = 64
SAFE_PORT_RE = re.compile(r"(COM[0-9]+|/[A-Za-z0-9._/-]+|[A-Za-z0-9][A-Za-z0-9._:-]*)\Z")
M5B2_NOTE = (
    "PropTx.m5b2 is for UIFlow2 Custom -> Open, not device upload. "
    "UIFlow2 processes .m5b2 locally; PropTx.py is the runtime file uploaded to /flash."
)


@dataclass(frozen=True)
class DeviceFile:
    source: str
    bundle_path: str
    device_name: str


@dataclass(frozen=True)
class BlockArtifact:
    source: str
    bundle_path: str
    source_bundle_path: str | None = None


DEVICE_FILES = (
    DeviceFile("uiflow/dial/prop_frame.py", "device/prop_frame.py", "prop_frame.py"),
    DeviceFile("uiflow/dial/prop_state.py", "device/prop_state.py", "prop_state.py"),
    DeviceFile("uiflow/dial/prop_ui.py", "device/prop_ui.py", "prop_ui.py"),
    DeviceFile("uiflow/dial/blocks/alpha2/PropTx.py", "device/PropTx.py", "PropTx.py"),
    DeviceFile("uiflow/dial/main.py", "device/main.py", "main.py"),
)

BLOCK_ARTIFACTS = (
    BlockArtifact(
        "uiflow/dial/blocks/dist/PropTx.m5b2",
        "blocks/PropTx.m5b2",
        "device/PropTx.py",
    ),
)
RUNTIME_IMPORT_ROOTS = (
    REPO_ROOT / "uiflow" / "dial",
    REPO_ROOT / "uiflow" / "dial" / "blocks" / "alpha2",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256_hex(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def _repo_path(rel: str) -> Path:
    return REPO_ROOT / rel


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _validate_output_path(out: Path, *, allow_external_output: bool = False) -> None:
    resolved = out.resolve()
    if resolved == REPO_ROOT:
        raise ValueError("refusing to use repository root as bundle output")
    if resolved.parent == resolved:
        raise ValueError("refusing to use filesystem root as bundle output")
    build_root = (REPO_ROOT / "build").resolve()
    if _is_relative_to(resolved, REPO_ROOT) and not _is_relative_to(resolved, build_root):
        raise ValueError("refusing to write bundle inside repository source tree")
    for protected in ("firmware", "shared", "tests", "tools", "uiflow"):
        protected_path = (REPO_ROOT / protected).resolve()
        if _is_relative_to(resolved, protected_path):
            raise ValueError(f"refusing to write bundle inside source tree: {protected}")
    if not allow_external_output and not _is_relative_to(resolved, build_root):
        raise ValueError(
            "refusing external output for production bundle; use build/ or "
            "--allow-external-output"
        )


def _validate_replace_target(
    out: Path,
    *,
    production: bool = False,
    prop_key_hex_file: Path | None = None,
) -> None:
    if out.exists() and not (out / "offline_manifest.json").is_file():
        raise ValueError("refusing to replace existing non-bundle output")
    if out.exists():
        try:
            manifest = _load_bundle_manifest(out)
        except ValueError as exc:
            raise ValueError(f"refusing to replace invalid existing bundle output: {exc}") from exc
        if not _looks_like_generated_bundle_manifest(manifest):
            raise ValueError("refusing to replace invalid existing bundle output")
        errors = [
            error
            for error in verify_bundle(
                out,
                production=production,
                prop_key_hex_file=prop_key_hex_file,
            )
            if not _is_rebuild_tolerated_bundle_error(error)
            and not _is_legacy_prop_key_metadata_error(manifest, error)
        ]
        if errors:
            raise ValueError(
                "refusing to replace invalid existing bundle output: " + "; ".join(errors)
            )


def _looks_like_generated_bundle_manifest(manifest: object) -> bool:
    return (
        isinstance(manifest, dict)
        and manifest.get("name") == BUNDLE_NAME
        and isinstance(manifest.get("device_files"), list)
        and isinstance(manifest.get("block_artifacts"), list)
    )


def _key_fingerprint(key_hex: str) -> str:
    return _sha256_bytes(bytes.fromhex(key_hex))


def _is_rebuild_tolerated_bundle_error(error: str) -> bool:
    return (
        error.startswith("local_dependencies mismatch:")
        or error.startswith("current source mismatch:")
        or error.startswith("source_bundle_path mismatch:")
        or error.startswith("invalid source_sha256 in manifest:")
        or error.startswith("source_sha256 mismatch:")
    )


def _is_legacy_prop_key_metadata_error(manifest: object, error: str) -> bool:
    if error not in (
        "key_kind mismatch: device/prop_key.py",
        "invalid key_fingerprint in manifest: device/prop_key.py",
    ):
        return False
    if not isinstance(manifest, dict):
        return False
    for entry in manifest.get("device_files", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("bundle_path") == PROP_KEY_BUNDLE_PATH:
            return "key_kind" not in entry or "key_fingerprint" not in entry
    return False


def _preflight_sources() -> None:
    for item in DEVICE_FILES + BLOCK_ARTIFACTS:
        src = _repo_path(item.source)
        if not src.exists():
            raise FileNotFoundError(src)
    dependency_errors = _device_dependency_errors()
    if dependency_errors:
        raise ValueError("; ".join(dependency_errors))
    _validate_block_artifacts()


def _load_local_tool(module_name: str, filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_block_artifacts() -> None:
    validator = _load_local_tool("validate_uiflow_blocks_for_offline_bundle", "validate_uiflow_blocks.py")
    report = validator.validate_bundle(REPO_ROOT)
    if report.errors:
        raise ValueError("UIFlow block validation failed: " + "; ".join(report.errors))


def _normalize_key_hex(text: str, allow_prototype: bool = False) -> str:
    value = "".join(str(text).strip().replace(":", " ").split()).lower()
    if len(value) < MIN_RUNTIME_KEY_BYTES * 2 or len(value) % 2:
        raise ValueError("prop key hex must contain at least 16 bytes")
    if len(value) > MAX_RUNTIME_KEY_BYTES * 2:
        raise ValueError("prop key hex must contain at most 64 bytes")
    if any(char not in "0123456789abcdef" for char in value):
        raise ValueError("prop key hex contains a non-hex character")
    if value == PROTOTYPE_KEY_HEX and not allow_prototype:
        raise ValueError("refusing to bundle prototype HMAC key")
    return value


def _read_prop_key_hex_file(path: Path) -> str:
    try:
        return _normalize_key_hex(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing prop key hex file: {path}") from exc


def _write_prop_key_module(path: Path, key_hex: str, allow_prototype: bool) -> None:
    path.write_text(
        "\n".join(
            [
                "# Generated by tools/uiflow_dial_offline.py from a local key file.",
                "# Do not commit generated production key bundles.",
                f"ALLOW_PROTOTYPE_SHARED_KEY = {allow_prototype!r}",
                f'SHARED_KEY_HEX = "{key_hex}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _extract_prop_key_module_settings(path: Path) -> tuple[bool | None, str | None, bool, bool]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    allow_prototype: bool | None = None
    key_hex: str | None = None
    has_shared_key = False
    invalid_allow_prototype = False
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "SHARED_KEY" in names:
            has_shared_key = True
        if "ALLOW_PROTOTYPE_SHARED_KEY" in names and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, bool):
                allow_prototype = node.value.value
            else:
                invalid_allow_prototype = True
        if "SHARED_KEY_HEX" in names and isinstance(node.value, ast.Constant):
            key_hex = str(node.value.value)
    return allow_prototype, key_hex, has_shared_key, invalid_allow_prototype


def _validate_prop_key_bundle_file(path: Path, production: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        allow_prototype, key_hex, has_shared_key, invalid_allow_prototype = (
            _extract_prop_key_module_settings(path)
        )
    except (SyntaxError, OSError) as exc:
        return [f"invalid production prop key module: {exc}"]
    if has_shared_key:
        errors.append("device/prop_key.py must not define SHARED_KEY; use SHARED_KEY_HEX")
    if invalid_allow_prototype:
        errors.append("device/prop_key.py ALLOW_PROTOTYPE_SHARED_KEY must be literal True or False")
    if production and allow_prototype is not False:
        errors.append("device/prop_key.py must set ALLOW_PROTOTYPE_SHARED_KEY = False")
    if key_hex is None:
        errors.append("device/prop_key.py must provide SHARED_KEY_HEX")
    else:
        try:
            _normalize_key_hex(key_hex, allow_prototype=allow_prototype is True and not production)
        except ValueError as exc:
            errors.append(f"device/prop_key.py invalid SHARED_KEY_HEX: {exc}")
    return errors


def _device_module_bundle_paths(include_prop_key: bool = False) -> dict[str, str]:
    paths = {Path(item.device_name).stem: item.bundle_path for item in DEVICE_FILES}
    if include_prop_key:
        paths["prop_key"] = PROP_KEY_BUNDLE_PATH
    return paths


def _iter_imported_modules(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def _is_local_runtime_module(module_name: str, roots=RUNTIME_IMPORT_ROOTS) -> bool:
    return any((root / f"{module_name}.py").is_file() for root in roots)


def _local_dependency_result(
    source: Path,
    bundle_path: str,
    module_bundle_paths: dict[str, str],
    roots=RUNTIME_IMPORT_ROOTS,
) -> tuple[list[str], list[str]]:
    dependencies: set[str] = set()
    errors: list[str] = []
    try:
        imported_modules = _iter_imported_modules(source)
    except SyntaxError as exc:
        return [], [f"invalid Python syntax in {source}: {exc}"]
    except OSError as exc:
        return [], [f"cannot read {source}: {exc}"]

    for module_name in sorted(imported_modules):
        dependency_path = module_bundle_paths.get(module_name)
        if dependency_path is not None:
            if dependency_path != bundle_path:
                dependencies.add(dependency_path)
            continue
        if _is_local_runtime_module(module_name, roots):
            errors.append(f"unbundled local import: {bundle_path} imports {module_name}")
    return sorted(dependencies), errors


def _expected_device_dependencies(include_prop_key: bool = False) -> dict[str, list[str]]:
    module_bundle_paths = _device_module_bundle_paths(include_prop_key)
    expected: dict[str, list[str]] = {}
    for item in DEVICE_FILES:
        dependencies, _errors = _local_dependency_result(
            _repo_path(item.source),
            item.bundle_path,
            module_bundle_paths,
        )
        expected[item.bundle_path] = dependencies
    if include_prop_key:
        expected[PROP_KEY_BUNDLE_PATH] = []
    return expected


def _device_dependency_errors(include_prop_key: bool = False) -> list[str]:
    module_bundle_paths = _device_module_bundle_paths(include_prop_key)
    errors: list[str] = []
    for item in DEVICE_FILES:
        _dependencies, item_errors = _local_dependency_result(
            _repo_path(item.source),
            item.bundle_path,
            module_bundle_paths,
        )
        errors.extend(item_errors)
    return errors


def _write_bundle(
    out: Path,
    prop_key_hex: str | None = None,
    dry_smoke: bool = False,
) -> dict:
    out.mkdir(parents=True)

    manifest: dict[str, object] = {
        "name": BUNDLE_NAME,
        "device_target_dir": DEFAULT_TARGET_DIR,
        "device_files": [],
        "block_artifacts": [],
    }
    if dry_smoke and prop_key_hex is not None:
        raise ValueError("dry-smoke and production prop key inputs are mutually exclusive")
    if dry_smoke:
        prop_key_hex = _normalize_key_hex(PROTOTYPE_KEY_HEX, allow_prototype=True)
    include_prop_key = prop_key_hex is not None
    expected_dependencies = _expected_device_dependencies(include_prop_key)

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
                "local_dependencies": expected_dependencies[item.bundle_path],
                "sha256": _sha256(src),
            }
        )

    if prop_key_hex is not None:
        dst = out / PROP_KEY_BUNDLE_PATH
        dst.parent.mkdir(parents=True, exist_ok=True)
        _write_prop_key_module(dst, prop_key_hex, allow_prototype=dry_smoke)
        manifest["device_files"].append(
            {
                "source": PROP_KEY_SOURCE_LABEL,
                "bundle_path": PROP_KEY_BUNDLE_PATH,
                "device_path": PROP_KEY_DEVICE_PATH,
                "local_dependencies": [],
                "sha256": _sha256(dst),
                "key_kind": "dry-smoke" if dry_smoke else "production",
                "key_fingerprint": _key_fingerprint(prop_key_hex),
            }
        )

    for item in BLOCK_ARTIFACTS:
        src = _repo_path(item.source)
        dst = out / item.bundle_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        artifact_entry = {
            "source": item.source,
            "bundle_path": item.bundle_path,
            "sha256": _sha256(src),
        }
        if item.source_bundle_path is not None:
            source_bundle_file = out / item.source_bundle_path
            artifact_entry["source_bundle_path"] = item.source_bundle_path
            artifact_entry["source_sha256"] = _sha256(source_bundle_file)
        manifest["block_artifacts"].append(artifact_entry)

    (out / "offline_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    upload_lines = [
        "Upload with:",
    ]
    if include_prop_key:
        if dry_smoke:
            upload_lines.extend(
                [
                    "  python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline",
                    "  python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline --dry-smoke",
                ]
            )
        else:
            upload_lines.extend(
                [
                    "  python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline --production --prop-key-hex-file <local-key-file>",
                    "  python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline --production --prop-key-hex-file <local-key-file>",
                ]
            )
    else:
        upload_lines.extend(
            [
                "  python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline",
                "  This no-key bundle is not deployable; rebuild with --dry-smoke or",
                "  --production --prop-key-hex-file before uploading to /flash.",
            ]
        )

    (out / "README_OFFLINE.txt").write_text(
        "\n".join(
            [
                "M5 Prop offline UIFlow Dial bundle",
                "",
                "Device upload files:",
                "  device/prop_frame.py -> /flash/prop_frame.py",
                "  device/prop_state.py -> /flash/prop_state.py",
                "  device/prop_ui.py    -> /flash/prop_ui.py",
                "  device/PropTx.py     -> /flash/PropTx.py",
                "  device/main.py       -> /flash/main.py",
                "  device/prop_key.py   -> /flash/prop_key.py (dry-smoke and production-key bundles)",
                "",
                "Custom block artifact:",
                "  blocks/PropTx.m5b2 -> UIFlow2 Custom -> Open",
                f"  {M5B2_NOTE}",
                "",
                *upload_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def create_bundle(
    out: Path,
    prop_key_hex_file: Path | None = None,
    dry_smoke: bool = False,
    production: bool = False,
    allow_external_output: bool = False,
) -> dict:
    out = out.resolve()
    _validate_output_path(
        out,
        allow_external_output=allow_external_output or not production,
    )
    if prop_key_hex_file is not None and not production:
        raise ValueError("--prop-key-hex-file requires --production")
    if production and prop_key_hex_file is None:
        raise ValueError("--production requires --prop-key-hex-file")
    if dry_smoke and prop_key_hex_file is not None:
        raise ValueError("--dry-smoke cannot be combined with --prop-key-hex-file")
    if dry_smoke and production:
        raise ValueError("--production cannot be combined with --dry-smoke")
    _validate_replace_target(
        out,
        production=production,
        prop_key_hex_file=prop_key_hex_file,
    )
    _preflight_sources()
    prop_key_hex = _read_prop_key_hex_file(prop_key_hex_file) if prop_key_hex_file else None

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".{out.name}.tmp-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        manifest = _write_bundle(tmp, prop_key_hex, dry_smoke=dry_smoke)
        errors = verify_bundle(
            tmp,
            production=prop_key_hex is not None,
            prop_key_hex_file=prop_key_hex_file,
        )
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


def _manifest_has_prop_key(manifest: dict) -> bool:
    entries = manifest.get("device_files", [])
    return isinstance(entries, list) and any(
        isinstance(entry, dict) and entry.get("bundle_path") == PROP_KEY_BUNDLE_PATH
        for entry in entries
    )


def _manifest_prop_key_kind(manifest: dict) -> str | None:
    entries = manifest.get("device_files", [])
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("bundle_path") == PROP_KEY_BUNDLE_PATH:
            kind = entry.get("key_kind")
            return kind if isinstance(kind, str) else None
    return None


def _expected_device_paths(include_prop_key: bool = False) -> dict[str, str]:
    paths = {item.bundle_path: f"{DEFAULT_TARGET_DIR}/{item.device_name}" for item in DEVICE_FILES}
    if include_prop_key:
        paths[PROP_KEY_BUNDLE_PATH] = PROP_KEY_DEVICE_PATH
    return paths


def _expected_device_sources(include_prop_key: bool = False) -> dict[str, str]:
    sources = {item.bundle_path: item.source for item in DEVICE_FILES}
    if include_prop_key:
        sources[PROP_KEY_BUNDLE_PATH] = PROP_KEY_SOURCE_LABEL
    return sources


def _canonical_device_bundle_paths(include_prop_key: bool = False) -> list[str]:
    paths = [item.bundle_path for item in DEVICE_FILES]
    if include_prop_key:
        paths.insert(0, PROP_KEY_BUNDLE_PATH)
    return paths


def _expected_artifact_paths() -> set[str]:
    return {item.bundle_path for item in BLOCK_ARTIFACTS}


def _expected_artifact_sources() -> dict[str, str]:
    return {item.bundle_path: item.source for item in BLOCK_ARTIFACTS}


def _expected_artifact_source_bundle_paths() -> dict[str, str | None]:
    return {item.bundle_path: item.source_bundle_path for item in BLOCK_ARTIFACTS}


def _bundle_file_path(bundle: Path, bundle_path: str) -> Path | None:
    candidate = Path(bundle_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (bundle / candidate).resolve()
    if not _is_relative_to(resolved, bundle.resolve()):
        return None
    return resolved


def _validate_block_artifact_runtime_parity(
    artifact_path: Path,
    source_path: Path,
    bundle_path: str,
) -> list[str]:
    errors: list[str] = []
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid block artifact JSON: {bundle_path}: {exc}"]
    if not isinstance(artifact, dict):
        return [f"block artifact must be a JSON object: {bundle_path}"]

    data = artifact.get("data", {})
    if not isinstance(data, dict):
        errors.append(f"block artifact data must be an object: {bundle_path}")
        data = {}
    uiflow2 = artifact.get("uiflow2", {})
    jscode = uiflow2.get("jscode", "") if isinstance(uiflow2, dict) else ""
    python_file_name = data.get("python_file_name")
    data_name = data.get("name")
    if python_file_name != "PropTx":
        errors.append(f"block artifact data.python_file_name must be PropTx: {bundle_path}")
    if data_name != "PropTx":
        errors.append(f"block artifact data.name must be PropTx: {bundle_path}")
    if "from PropTx import PropTx" not in jscode:
        errors.append(f"block artifact runtime import mismatch: {bundle_path}")

    pycode = artifact.get("pyCode")
    if not isinstance(pycode, str):
        errors.append(f"block artifact missing pyCode: {bundle_path}")
    elif pycode.strip() != source_path.read_text(encoding="utf-8").strip():
        errors.append(f"block artifact pyCode mismatch: {bundle_path}")
    return errors


def _current_repo_source_error(
    bundle_path: str,
    source_rel: object,
    bundle_file: Path,
) -> str | None:
    if not isinstance(source_rel, str) or source_rel == PROP_KEY_SOURCE_LABEL:
        return None
    source_path = _repo_path(source_rel)
    if not source_path.exists():
        return f"missing current source file: {bundle_path}"
    if _sha256(bundle_file) != _sha256(source_path):
        return f"current source mismatch: {bundle_path}"
    return None


def verify_bundle(
    bundle: Path,
    production: bool = False,
    prop_key_hex_file: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    bundle = bundle.resolve()
    expected_prop_key_fingerprint: str | None = None
    if prop_key_hex_file is not None and not production:
        errors.append("--prop-key-hex-file requires --production")
    elif prop_key_hex_file is not None:
        try:
            expected_prop_key_fingerprint = _key_fingerprint(
                _read_prop_key_hex_file(prop_key_hex_file)
            )
        except ValueError as exc:
            errors.append(str(exc))
    try:
        manifest = _load_bundle_manifest(bundle)
    except ValueError as exc:
        return [str(exc)]
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]
    if manifest.get("device_target_dir") != DEFAULT_TARGET_DIR:
        errors.append(f"device_target_dir must be {DEFAULT_TARGET_DIR}")
    include_prop_key = _manifest_has_prop_key(manifest)
    prop_key_kind = _manifest_prop_key_kind(manifest)
    if prop_key_kind == "production" and not production:
        errors.append("production bundle requires --production")
    if prop_key_kind == "production" and prop_key_hex_file is None:
        errors.append("production bundle requires --prop-key-hex-file")
    if production and not include_prop_key:
        errors.append(f"production bundle requires {PROP_KEY_BUNDLE_PATH}")
    if production and prop_key_hex_file is None:
        errors.append("--production requires --prop-key-hex-file")

    expected_sections = {
        "device_files": (
            set(_expected_device_paths(include_prop_key)),
            _expected_device_sources(include_prop_key),
        ),
        "block_artifacts": (_expected_artifact_paths(), _expected_artifact_sources()),
    }
    expected_artifact_source_paths = _expected_artifact_source_bundle_paths()
    device_module_bundle_paths = _device_module_bundle_paths(include_prop_key)
    bundle_device_root = bundle / "device"

    manifest_paths: set[str] = set()
    for section, (expected_paths, expected_sources) in expected_sections.items():
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
            manifest_paths.add(bundle_path)
            if entry.get("source") != expected_sources.get(bundle_path):
                errors.append(f"source mismatch: {bundle_path}")
            path = _bundle_file_path(bundle, bundle_path)
            if path is None:
                errors.append(f"bundle_path escapes bundle: {bundle_path}")
                continue
            if not path.exists():
                errors.append(f"missing bundle file: {bundle_path}")
                continue
            current_source_error = _current_repo_source_error(
                bundle_path,
                expected_sources.get(bundle_path),
                path,
            )
            if current_source_error is not None:
                errors.append(current_source_error)
            if section == "device_files":
                expected_device_path = _expected_device_paths(include_prop_key).get(bundle_path)
                if entry.get("device_path") != expected_device_path:
                    errors.append(f"device_path mismatch: {bundle_path}")
                expected_dependencies, dependency_errors = _local_dependency_result(
                    path,
                    bundle_path,
                    device_module_bundle_paths,
                    roots=(bundle_device_root,),
                )
                errors.extend(dependency_errors)
                if entry.get("local_dependencies") != expected_dependencies:
                    errors.append(f"local_dependencies mismatch: {bundle_path}")
            if section == "block_artifacts":
                expected_source_bundle_path = expected_artifact_source_paths.get(bundle_path)
                if entry.get("source_bundle_path") != expected_source_bundle_path:
                    errors.append(f"source_bundle_path mismatch: {bundle_path}")
                source_hash = entry.get("source_sha256")
                if expected_source_bundle_path is not None:
                    if not _is_sha256_hex(source_hash):
                        errors.append(f"invalid source_sha256 in manifest: {bundle_path}")
                    else:
                        source_bundle = _bundle_file_path(bundle, expected_source_bundle_path)
                        if source_bundle is None or not source_bundle.exists():
                            errors.append(
                                f"missing artifact source bundle file: {expected_source_bundle_path}"
                            )
                        elif _sha256(source_bundle) != source_hash:
                            errors.append(f"source_sha256 mismatch: {bundle_path}")
                        else:
                            errors.extend(
                                _validate_block_artifact_runtime_parity(
                                    path,
                                    source_bundle,
                                    bundle_path,
                                )
                            )
            if not _is_sha256_hex(expected_hash):
                errors.append(f"invalid sha256 in manifest: {bundle_path}")
                continue
            actual_hash = _sha256(path)
            if actual_hash != expected_hash:
                errors.append(f"sha256 mismatch: {bundle_path}")
            if bundle_path == PROP_KEY_BUNDLE_PATH:
                errors.extend(_validate_prop_key_bundle_file(path, production=production))
                try:
                    allow_prototype, key_hex, _has_shared_key, _invalid_allow_prototype = (
                        _extract_prop_key_module_settings(path)
                    )
                except (SyntaxError, OSError):
                    allow_prototype, key_hex = None, None
                key_kind = (
                    "dry-smoke"
                    if allow_prototype is True
                    else ("production" if allow_prototype is False else None)
                )
                if key_kind is not None and entry.get("key_kind") != key_kind:
                    errors.append(f"key_kind mismatch: {bundle_path}")
                key_fingerprint = entry.get("key_fingerprint")
                if not _is_sha256_hex(key_fingerprint):
                    errors.append(f"invalid key_fingerprint in manifest: {bundle_path}")
                elif key_hex is not None:
                    try:
                        normalized_key = _normalize_key_hex(
                            key_hex,
                            allow_prototype=allow_prototype is True and not production,
                        )
                    except ValueError:
                        normalized_key = None
                    if normalized_key is not None:
                        actual_key_fingerprint = _key_fingerprint(normalized_key)
                        if actual_key_fingerprint != key_fingerprint:
                            errors.append(f"key_fingerprint mismatch: {bundle_path}")
                        if (
                            expected_prop_key_fingerprint is not None
                            and actual_key_fingerprint != expected_prop_key_fingerprint
                        ):
                            errors.append(f"prop_key_hex_file mismatch: {bundle_path}")
        for missing in sorted(expected_paths - seen_paths):
            errors.append(f"missing manifest entry: {missing}")

    expected_bundle_files = manifest_paths | {"offline_manifest.json", "README_OFFLINE.txt"}
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle).as_posix()
        if rel not in expected_bundle_files:
            errors.append(f"unexpected bundle file: {rel}")

    return errors


def mpremote_command_prefix(port: str) -> list[str]:
    _validate_port(port)
    return [sys.executable, "-m", "mpremote", "connect", port]


def _validate_port(port: str) -> None:
    if not isinstance(port, str) or not SAFE_PORT_RE.fullmatch(port):
        raise ValueError(f"invalid port: {port}")


def _validate_device_target_dir(target_dir: str) -> None:
    if target_dir != DEFAULT_TARGET_DIR:
        raise ValueError(f"invalid target-dir: {target_dir}")


def build_deploy_commands(
    port: str,
    target_dir: str = DEFAULT_TARGET_DIR,
    bundle: Path | None = None,
    production: bool = False,
    prop_key_hex_file: Path | None = None,
    dry_smoke: bool = False,
) -> list[list[str]]:
    _validate_device_target_dir(target_dir)
    _validate_port(port)
    if production and dry_smoke:
        raise ValueError("deploy cannot combine --production and --dry-smoke")
    if dry_smoke and prop_key_hex_file is not None:
        raise ValueError("--dry-smoke cannot be combined with --prop-key-hex-file")
    if prop_key_hex_file is not None and not production:
        raise ValueError("--prop-key-hex-file requires --production")
    if production and bundle is None:
        raise ValueError("production deploy requires a verified bundle with device/prop_key.py")
    if bundle is None:
        raise ValueError("deploy commands require a verified bundle")
    commands = [mpremote_command_prefix(port) + ["fs", "mkdir", target_dir]]
    if bundle is not None:
        manifest = _load_bundle_manifest(bundle)
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be a JSON object")
        manifest_target_dir = manifest.get("device_target_dir", DEFAULT_TARGET_DIR)
        if target_dir != manifest_target_dir:
            raise ValueError(
                f"target-dir mismatch: bundle expects {manifest_target_dir}, got {target_dir}"
            )
        items = manifest.get("device_files")
        if not isinstance(items, list):
            raise ValueError("device_files must be a list")
        for index, entry in enumerate(items):
            if not isinstance(entry, dict):
                raise ValueError(f"device_files[{index}] must be an object")
        include_prop_key = _manifest_has_prop_key(manifest)
        prop_key_kind = _manifest_prop_key_kind(manifest)
        if prop_key_kind == "production" and prop_key_hex_file is None:
            raise ValueError("production deploy requires --prop-key-hex-file")
        if prop_key_kind == "production" and not production:
            raise ValueError("production bundle requires --production")
        if prop_key_kind == "dry-smoke" and not dry_smoke:
            raise ValueError("dry-smoke deploy requires --dry-smoke")
        errors = verify_bundle(
            bundle,
            production=production,
            prop_key_hex_file=prop_key_hex_file,
        )
        if errors:
            raise ValueError("; ".join(errors))
        if not include_prop_key:
            raise ValueError(
                "deploy bundle requires device/prop_key.py; rebuild with --dry-smoke "
                "or --production --prop-key-hex-file"
            )
        expected_device_paths = _expected_device_paths(include_prop_key)
        entries_by_path: dict[str, dict] = {}
        for index, entry in enumerate(items):
            bundle_path = entry.get("bundle_path")
            if isinstance(bundle_path, str):
                entries_by_path[bundle_path] = entry

        for bundle_path in _canonical_device_bundle_paths(include_prop_key):
            entry = entries_by_path.get(bundle_path)
            if not isinstance(entry, dict):
                raise ValueError(f"missing manifest entry: {bundle_path}")
            device_path = entry.get("device_path")
            if not isinstance(device_path, str) or not device_path:
                raise ValueError(f"device_files entry has no device_path: {bundle_path}")
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


def format_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def deploy(
    port: str,
    target_dir: str,
    dry_run: bool,
    bundle: Path | None = None,
    production: bool = False,
    prop_key_hex_file: Path | None = None,
    dry_smoke: bool = False,
) -> int:
    try:
        _validate_device_target_dir(target_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    bundle_path = bundle.resolve() if bundle is not None else None
    if production and dry_smoke:
        print("deploy cannot combine --production and --dry-smoke", file=sys.stderr)
        return 1
    if dry_smoke and prop_key_hex_file is not None:
        print("--dry-smoke cannot be combined with --prop-key-hex-file", file=sys.stderr)
        return 1
    if prop_key_hex_file is not None and not production:
        print("--prop-key-hex-file requires --production", file=sys.stderr)
        return 1
    if bundle_path is None:
        print(
            "deploy requires --bundle generated with --dry-smoke or "
            "--production --prop-key-hex-file",
            file=sys.stderr,
        )
        return 1
    if bundle_path is not None:
        errors = verify_bundle(
            bundle_path,
            production=production,
            prop_key_hex_file=prop_key_hex_file,
        )
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1

    try:
        commands = build_deploy_commands(
            port,
            target_dir,
            bundle_path,
            production=production,
            prop_key_hex_file=prop_key_hex_file,
            dry_smoke=dry_smoke,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    mpremote_missing = importlib.util.find_spec("mpremote") is None
    if dry_run and mpremote_missing:
        print(
            "warning: mpremote is not installed for this Python; dry-run commands "
            "will need it before real deploy",
            file=sys.stderr,
        )

    if not dry_run and mpremote_missing:
        print(
            "mpremote is not installed for this Python; install it before real deploy",
            file=sys.stderr,
        )
        return 1

    if dry_run:
        print("DRY RUN: mpremote commands for offline Dial upload")
        for command in commands:
            print(format_command(command))
        print(M5B2_NOTE)
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
    print(M5B2_NOTE)
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
    bundle_parser.add_argument(
        "--prop-key-hex-file",
        type=Path,
        default=None,
        help="local file containing a non-prototype HMAC key hex for production bundles",
    )
    bundle_parser.add_argument(
        "--production",
        action="store_true",
        help="require --prop-key-hex-file and generate a production-key bundle",
    )
    bundle_parser.add_argument(
        "--dry-smoke",
        action="store_true",
        help="generate an explicit dry-smoke bundle using the prototype bench key",
    )
    bundle_parser.add_argument(
        "--allow-external-output",
        action="store_true",
        help=(
            "allow a production bundle outside build/; device/prop_key.py contains "
            "secret key material"
        ),
    )

    verify_parser = sub.add_parser("verify", help="verify bundle manifest files and SHA-256 hashes")
    verify_parser.add_argument("--bundle", type=Path, default=DEFAULT_OUT)
    verify_parser.add_argument(
        "--production",
        action="store_true",
        help="require a non-prototype /flash/prop_key.py in the bundle",
    )
    verify_parser.add_argument(
        "--prop-key-hex-file",
        type=Path,
        default=None,
        help="optional local key file; verify bundle prop_key.py has the same fingerprint",
    )

    deploy_parser = sub.add_parser(
        "deploy", help="upload runtime files to a USB-connected M5 Dial via mpremote"
    )
    deploy_parser.add_argument("--port", required=True, help="serial port, for example COM6")
    deploy_parser.add_argument("--bundle", type=Path, default=None)
    deploy_parser.add_argument("--target-dir", default=DEFAULT_TARGET_DIR)
    deploy_parser.add_argument("--dry-run", action="store_true")
    deploy_parser.add_argument(
        "--production",
        action="store_true",
        help="require a verified production-key bundle before upload",
    )
    deploy_parser.add_argument(
        "--dry-smoke",
        action="store_true",
        help="explicitly acknowledge upload of a bench-only dry-smoke bundle",
    )
    deploy_parser.add_argument(
        "--prop-key-hex-file",
        type=Path,
        default=None,
        help="optional local key file; verify bundle prop_key.py has the same fingerprint before upload",
    )

    args = parser.parse_args(argv)
    if args.command == "bundle":
        if args.production and args.prop_key_hex_file is None:
            print("--production requires --prop-key-hex-file", file=sys.stderr)
            return 1
        if args.production and args.dry_smoke:
            print("--production cannot be combined with --dry-smoke", file=sys.stderr)
            return 1
        manifest = create_bundle(
            args.out,
            prop_key_hex_file=args.prop_key_hex_file,
            dry_smoke=args.dry_smoke,
            production=args.production,
            allow_external_output=args.allow_external_output,
        )
        if args.production and args.allow_external_output:
            print(
                "warning: production bundle outside build/ contains secret "
                "device/prop_key.py material",
                file=sys.stderr,
            )
        print(f"offline UIFlow Dial bundle written to {args.out}")
        print(f"device files: {len(manifest['device_files'])}")
        print(f"block artifacts: {len(manifest['block_artifacts'])}")
        return 0
    if args.command == "verify":
        bundle = args.bundle.resolve()
        errors = verify_bundle(
            bundle,
            production=args.production,
            prop_key_hex_file=args.prop_key_hex_file,
        )
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        label = "production offline UIFlow Dial bundle" if args.production else "offline UIFlow Dial bundle"
        print(f"verified {label}: {bundle}")
        return 0
    if args.command == "deploy":
        return deploy(
            args.port,
            args.target_dir,
            args.dry_run,
            args.bundle,
            production=args.production,
            prop_key_hex_file=args.prop_key_hex_file,
            dry_smoke=args.dry_smoke,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
