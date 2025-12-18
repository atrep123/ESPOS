#!/usr/bin/env python3
"""
Validate ESP32OS UI design JSON (structure + firmware-export compatibility).

This is a lightweight validator (stdlib-only). It focuses on:
- required fields + basic types
- supported widget types (exportable to `UiWidget` in `src/ui_scene.h`)
- geometry sanity (within scene bounds)
- duplicate widget ids

Usage:
  python tools/validate_design.py main_scene.json
  python tools/validate_design.py main_scene.json --warnings-as-errors
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ui_codegen import WIDGET_TYPE_MAP  # noqa: E402

ALLOWED_BORDER_STYLES = {"none", "single", "double", "rounded", "bold", "dashed"}
ALLOWED_ALIGN = {"left", "center", "right"}
ALLOWED_VALIGN = {"top", "middle", "bottom"}
ALLOWED_OVERFLOW = {"ellipsis", "wrap", "clip", "auto"}


@dataclass(frozen=True)
class Issue:
    level: str  # "ERROR" | "WARN"
    message: str


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_bool(v: object) -> bool:
    return isinstance(v, bool)


def _scenes_from_data(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scenes_raw = data.get("scenes", {})
    if isinstance(scenes_raw, dict):
        out: dict[str, dict[str, Any]] = {}
        for name, scene in scenes_raw.items():
            if isinstance(scene, dict):
                out[str(name)] = scene
        return out
    if isinstance(scenes_raw, list):
        out = {}
        for i, scene in enumerate(scenes_raw):
            if not isinstance(scene, dict):
                continue
            name = str(scene.get("id") or scene.get("name") or f"scene_{i}")
            out[name] = scene
        return out
    return {}


def validate_data(data: dict[str, Any], *, file_label: str, warnings_as_errors: bool) -> list[Issue]:
    issues: list[Issue] = []

    root_w = data.get("width")
    root_h = data.get("height")
    if root_w is not None and not _is_int(root_w):
        issues.append(Issue("ERROR", f"{file_label}: root.width must be int"))
    if root_h is not None and not _is_int(root_h):
        issues.append(Issue("ERROR", f"{file_label}: root.height must be int"))

    scenes = _scenes_from_data(data)
    if not scenes:
        issues.append(Issue("ERROR", f"{file_label}: no scenes found (missing/invalid 'scenes')"))
        return issues

    for scene_name, scene in scenes.items():
        scene_label = f"{file_label}: scene '{scene_name}'"
        scene_w = scene.get("width", root_w)
        scene_h = scene.get("height", root_h)
        if not _is_int(scene_w) or int(scene_w) <= 0:
            issues.append(Issue("ERROR", f"{scene_label}: width must be int >= 1"))
            continue
        if not _is_int(scene_h) or int(scene_h) <= 0:
            issues.append(Issue("ERROR", f"{scene_label}: height must be int >= 1"))
            continue

        widgets = scene.get("widgets", [])
        if not isinstance(widgets, list):
            issues.append(Issue("ERROR", f"{scene_label}: widgets must be a list"))
            continue

        seen_ids: set[str] = set()

        for idx, w in enumerate(widgets):
            widget_label = f"{scene_label}: widget[{idx}]"
            if not isinstance(w, dict):
                issues.append(Issue("ERROR", f"{widget_label}: widget must be an object"))
                continue

            wtype = w.get("type")
            if not isinstance(wtype, str) or not wtype.strip():
                issues.append(Issue("ERROR", f"{widget_label}: missing/invalid 'type'"))
                continue
            if wtype.lower() not in WIDGET_TYPE_MAP:
                issues.append(Issue("ERROR", f"{widget_label}: unsupported type '{wtype}'"))

            for key in ("x", "y", "width", "height"):
                if key not in w:
                    issues.append(Issue("ERROR", f"{widget_label}: missing '{key}'"))
            x = w.get("x")
            y = w.get("y")
            ww = w.get("width")
            hh = w.get("height")

            if _is_int(x) and _is_int(y) and _is_int(ww) and _is_int(hh):
                if int(ww) <= 0 or int(hh) <= 0:
                    issues.append(Issue("ERROR", f"{widget_label}: width/height must be >= 1"))
                if int(x) < 0 or int(y) < 0:
                    issues.append(Issue("ERROR", f"{widget_label}: x/y must be >= 0"))
                if int(x) + int(ww) > int(scene_w) or int(y) + int(hh) > int(scene_h):
                    msg = f"{widget_label}: rect out of bounds ({x},{y},{ww},{hh}) in {scene_w}x{scene_h}"
                    issues.append(Issue("WARN", msg))
            else:
                if not _is_int(x):
                    issues.append(Issue("ERROR", f"{widget_label}: x must be int"))
                if not _is_int(y):
                    issues.append(Issue("ERROR", f"{widget_label}: y must be int"))
                if not _is_int(ww):
                    issues.append(Issue("ERROR", f"{widget_label}: width must be int"))
                if not _is_int(hh):
                    issues.append(Issue("ERROR", f"{widget_label}: height must be int"))

            widget_id = w.get("_widget_id") or w.get("id")
            if widget_id is not None:
                if not isinstance(widget_id, str):
                    issues.append(Issue("ERROR", f"{widget_label}: _widget_id/id must be string"))
                else:
                    if widget_id in seen_ids:
                        issues.append(Issue("ERROR", f"{widget_label}: duplicate id '{widget_id}'"))
                    seen_ids.add(widget_id)

            for key in ("border", "checked", "visible", "enabled"):
                if key in w and not _is_bool(w.get(key)):
                    issues.append(Issue("ERROR", f"{widget_label}: '{key}' must be boolean"))

            if "max_lines" in w and not _is_int(w.get("max_lines")):
                issues.append(Issue("ERROR", f"{widget_label}: max_lines must be int"))
            if _is_int(w.get("max_lines")) and int(w.get("max_lines")) < 0:  # type: ignore[arg-type]
                issues.append(Issue("ERROR", f"{widget_label}: max_lines must be >= 0"))

            if "border_style" in w:
                bs = w.get("border_style")
                if not isinstance(bs, str) or bs.lower() not in ALLOWED_BORDER_STYLES:
                    issues.append(Issue("ERROR", f"{widget_label}: invalid border_style '{bs}'"))
            if "align" in w:
                a = w.get("align")
                if not isinstance(a, str) or a.lower() not in ALLOWED_ALIGN:
                    issues.append(Issue("ERROR", f"{widget_label}: invalid align '{a}'"))
            if "valign" in w:
                va = w.get("valign")
                if not isinstance(va, str) or va.lower() not in ALLOWED_VALIGN:
                    issues.append(Issue("ERROR", f"{widget_label}: invalid valign '{va}'"))
            if "text_overflow" in w:
                ov = w.get("text_overflow")
                if not isinstance(ov, str) or ov.lower() not in ALLOWED_OVERFLOW:
                    issues.append(Issue("ERROR", f"{widget_label}: invalid text_overflow '{ov}'"))

    if warnings_as_errors:
        return [Issue("ERROR", i.message) if i.level == "WARN" else i for i in issues]
    return issues


def validate_file(path: Path, *, warnings_as_errors: bool) -> list[Issue]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [Issue("ERROR", f"{path}: failed to parse JSON ({exc})")]
    if not isinstance(data, dict):
        return [Issue("ERROR", f"{path}: root must be a JSON object")]
    return validate_data(data, file_label=str(path), warnings_as_errors=warnings_as_errors)


def main() -> int:
    p = argparse.ArgumentParser(description="Validate ESP32OS UI design JSON")
    p.add_argument("json", type=Path, help="Input design JSON")
    p.add_argument("--warnings-as-errors", action="store_true", help="Treat warnings as errors")
    args = p.parse_args()

    issues = validate_file(args.json, warnings_as_errors=args.warnings_as_errors)
    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    for i in issues:
        print(f"[{i.level}] {i.message}")

    if errors:
        print(f"[FAIL] {len(errors)} error(s), {len(warns)} warning(s)")
        return 1
    if warns:
        print(f"[WARN] {len(warns)} warning(s)")
    else:
        print("[OK] Design looks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

