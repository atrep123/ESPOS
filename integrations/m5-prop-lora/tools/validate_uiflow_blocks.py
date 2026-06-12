from __future__ import annotations

import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple


PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
VALID_BLOCK_TYPES = {"execute", "value"}
VALID_PARAM_TYPES = {"label", "number", "variable"}


class BundleReport(NamedTuple):
    category: str
    color: str
    block_count: int
    template_names: list[str]
    alpha2_source: str
    alpha2_method_count: int
    alpha2_artifact: str
    alpha2_artifact_method_count: int
    alpha2_artifact_block_count: int
    errors: list[str]


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def validate_bundle(root: Path | str | None = None) -> BundleReport:
    repo = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    repo = repo.resolve()
    blocks_dir = repo / "uiflow" / "dial" / "blocks"
    code_dir = blocks_dir / "code"
    manifest_path = blocks_dir / "prop_tx.json"
    errors: list[str] = []
    expected_alpha2_methods = {
        "__init__",
        "preview",
        "fire",
        "stop",
        "arm",
        "remote_led",
        "sync_palette",
        "reply",
        "hue_color",
        "default_hues",
        "default_colors",
        "palette_from_hues",
        "set_color",
        "first_four",
        "rgb_color",
        "rgb888",
        "remote_led3",
        "remote_led5",
    }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return BundleReport(
            "", "", 0, [], "", 0, "", 0, 0, [f"missing manifest: {_rel(repo, manifest_path)}"]
        )
    except json.JSONDecodeError as exc:
        return BundleReport(
            "", "", 0, [], "", 0, "", 0, 0, [f"invalid JSON in {_rel(repo, manifest_path)}: {exc}"]
        )

    category = manifest.get("category", "")
    color = manifest.get("color", "")
    blocks = manifest.get("blocks", [])
    if category != "PropTx":
        errors.append("manifest category must be 'PropTx'")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        errors.append("manifest color must be a #RRGGBB value")
    if not isinstance(blocks, list) or not blocks:
        errors.append("manifest must contain at least one block")
        blocks = []

    template_names: list[str] = []
    seen_names: set[str] = set()
    for index, block in enumerate(blocks):
        label = f"blocks[{index}]"
        if not isinstance(block, dict):
            errors.append(f"{label} must be an object")
            continue

        name = block.get("name")
        block_type = block.get("type")
        params = block.get("params", [])
        if not isinstance(name, str) or not name:
            errors.append(f"{label} has no name")
            continue
        if name in seen_names:
            errors.append(f"duplicate block name: {name}")
        seen_names.add(name)
        template_names.append(name)

        if block_type not in VALID_BLOCK_TYPES:
            errors.append(f"{name}: type must be one of {sorted(VALID_BLOCK_TYPES)}")
        if not isinstance(params, list) or not params:
            errors.append(f"{name}: params must be a non-empty list")
            params = []

        input_names: set[str] = set()
        for param_index, param in enumerate(params):
            param_label = f"{label}.params[{param_index}]"
            if not isinstance(param, dict):
                errors.append(f"{param_label} must be an object")
                continue

            param_name = param.get("name")
            param_type = param.get("type")
            if not isinstance(param_name, str) or not param_name:
                errors.append(f"{name}: params[{param_index}] has no name")
                continue
            if param_type not in VALID_PARAM_TYPES:
                errors.append(f"{name}: param {param_name!r} has invalid type {param_type!r}")
                continue
            if param_type != "label":
                input_names.add(param_name)

        template_path = code_dir / f"{name}.py"
        if not template_path.exists():
            errors.append(f"{name}: missing template {_rel(repo, template_path)}")
            continue
        template = template_path.read_text(encoding="utf-8")
        placeholders = set(PLACEHOLDER_RE.findall(template))
        unknown = placeholders - input_names
        unused = input_names - placeholders
        if unknown:
            errors.append(f"{name}: unknown template placeholders {sorted(unknown)}")
        if unused:
            errors.append(f"{name}: input params not used in template {sorted(unused)}")

    manifest_names = set(template_names)
    extra_templates = {
        path.stem
        for path in code_dir.glob("*.py")
        if path.name != "__init__.py" and path.stem not in manifest_names
    }
    if extra_templates:
        errors.append(f"templates without manifest blocks: {sorted(extra_templates)}")

    for library in (
        repo / "uiflow" / "dial" / "prop_frame.py",
        repo / "uiflow" / "dial" / "prop_ui.py",
    ):
        if not library.exists():
            errors.append(f"missing upload library: {_rel(repo, library)}")

    alpha2_path = repo / "uiflow" / "dial" / "blocks" / "alpha2" / "PropTx.py"
    alpha2_source = _rel(repo, alpha2_path)
    alpha2_method_count = 0
    if not alpha2_path.exists():
        errors.append(f"missing Alpha-2 source: {alpha2_source}")
    else:
        try:
            tree = ast.parse(alpha2_path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"invalid Python in {alpha2_source}: {exc}")
        else:
            classes = [
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == "PropTx"
            ]
            if len(classes) != 1:
                errors.append(f"{alpha2_source} must define exactly one PropTx class")
            else:
                methods = {
                    node.name for node in classes[0].body if isinstance(node, ast.FunctionDef)
                }
                alpha2_method_count = len(methods)
                missing = expected_alpha2_methods - methods
                extra = methods - expected_alpha2_methods
                if missing:
                    errors.append(f"{alpha2_source} missing methods: {sorted(missing)}")
                if extra:
                    errors.append(f"{alpha2_source} has unexpected methods: {sorted(extra)}")

    alpha2_artifact_path = repo / "uiflow" / "dial" / "blocks" / "dist" / "PropTx.m5b2"
    alpha2_artifact = _rel(repo, alpha2_artifact_path)
    alpha2_artifact_method_count = 0
    alpha2_artifact_block_count = 0
    if not alpha2_artifact_path.exists():
        errors.append(f"missing Alpha-2 artifact: {alpha2_artifact}")
    else:
        try:
            artifact = json.loads(alpha2_artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in {alpha2_artifact}: {exc}")
        else:
            if artifact.get("version") != "alpha2":
                errors.append(f"{alpha2_artifact}: version must be 'alpha2'")
            if artifact.get("category") != "PropTx":
                errors.append(f"{alpha2_artifact}: category must be 'PropTx'")
            if artifact.get("color") != color:
                errors.append(f"{alpha2_artifact}: color must match manifest color {color}")

            uiflow2 = artifact.get("uiflow2", {})
            jscode = uiflow2.get("jscode", "") if isinstance(uiflow2, dict) else ""
            import_match = re.search(r"from\s+(\w+)\s+import\s+(\w+)", jscode)

            data = artifact.get("data", {})
            python_file_name = data.get("python_file_name") if isinstance(data, dict) else None
            data_name = data.get("name") if isinstance(data, dict) else None
            if not import_match:
                errors.append(f"{alpha2_artifact}: missing runtime import")
            else:
                if import_match.group(1) != python_file_name:
                    errors.append(
                        f"{alpha2_artifact}: runtime import module must match data.python_file_name"
                    )
                if import_match.group(2) != data_name:
                    errors.append(f"{alpha2_artifact}: runtime import class must match data.name")
            if python_file_name != "PropTx":
                errors.append(f"{alpha2_artifact}: data.python_file_name must be 'PropTx'")
            if data_name != "PropTx":
                errors.append(f"{alpha2_artifact}: data.name must be 'PropTx'")

            toolbox = uiflow2.get("toolbox", "") if isinstance(uiflow2, dict) else ""
            try:
                toolbox_root = ET.fromstring("<root>" + toolbox + "</root>")
            except ET.ParseError as exc:
                errors.append(f"{alpha2_artifact}: invalid toolbox XML: {exc}")
            else:
                toolbox_category = toolbox_root.find("category")
                toolbox_name = (
                    toolbox_category.get("name") if toolbox_category is not None else None
                )
                if toolbox_name != category:
                    errors.append(
                        f"{alpha2_artifact}: toolbox category must match manifest category"
                    )

            artifact_py = artifact.get("pyCode")
            if artifact_py is None:
                errors.append(f"{alpha2_artifact}: missing pyCode")
            elif (
                alpha2_path.exists()
                and artifact_py.strip() != alpha2_path.read_text(encoding="utf-8").strip()
            ):
                errors.append(f"{alpha2_artifact}: pyCode must match {alpha2_source}")

            members = data.get("members", []) if isinstance(data, dict) else []
            if not isinstance(members, list):
                errors.append(f"{alpha2_artifact}: data.members must be a list")
                members = []
            artifact_methods = {
                member.get("name")
                for member in members
                if isinstance(member, dict) and isinstance(member.get("name"), str)
            }
            alpha2_artifact_method_count = len(artifact_methods)
            missing_methods = expected_alpha2_methods - artifact_methods
            extra_methods = artifact_methods - expected_alpha2_methods
            if missing_methods:
                errors.append(f"{alpha2_artifact}: missing methods: {sorted(missing_methods)}")
            if extra_methods:
                errors.append(f"{alpha2_artifact}: unexpected methods: {sorted(extra_methods)}")
            if artifact_py is not None:
                for member in members:
                    if isinstance(member, dict) and isinstance(member.get("source"), str):
                        if member["source"].strip() not in artifact_py:
                            errors.append(
                                f"{alpha2_artifact}: member {member.get('name')} source not found in pyCode"
                            )

            registered_blocks = set(re.findall(r'Blockly\.Blocks\["([^"]+)"\]', jscode))
            alpha2_artifact_block_count = len(registered_blocks)
            block_types = uiflow2.get("block_type", []) if isinstance(uiflow2, dict) else []
            if not isinstance(block_types, list):
                errors.append(f"{alpha2_artifact}: uiflow2.block_type must be a list")
                block_types = []
            block_type_set = {item for item in block_types if isinstance(item, str)}
            expected_blocks = {
                f"custom_proptx_{'init' if method == '__init__' else method}"
                for method in expected_alpha2_methods
            }
            if registered_blocks != expected_blocks:
                errors.append(
                    f"{alpha2_artifact}: Blockly registrations must be {sorted(expected_blocks)}"
                )
            if block_type_set != registered_blocks:
                errors.append(
                    f"{alpha2_artifact}: uiflow2.block_type must match Blockly registrations"
                )

    return BundleReport(
        category,
        color,
        len(template_names),
        template_names,
        alpha2_source,
        alpha2_method_count,
        alpha2_artifact,
        alpha2_artifact_method_count,
        alpha2_artifact_block_count,
        errors,
    )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]) if args else Path(__file__).resolve().parents[1]
    report = validate_bundle(root)
    if report.errors:
        for error in report.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: {report.block_count} UIFlow custom blocks validated")
    print(f"Manifest: uiflow/dial/blocks/prop_tx.json ({report.category}, {report.color})")
    print("Templates: uiflow/dial/blocks/code")
    print(f"Alpha-2 source: {report.alpha2_source} ({report.alpha2_method_count} methods)")
    print(
        f"Alpha-2 artifact: {report.alpha2_artifact} "
        f"({report.alpha2_artifact_method_count} methods, "
        f"{report.alpha2_artifact_block_count} blocks)"
    )
    print("Upload libraries: uiflow/dial/prop_frame.py, uiflow/dial/prop_ui.py")
    print("Manual import: copy each code/<name>.py template into M5Stack Block Designer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
