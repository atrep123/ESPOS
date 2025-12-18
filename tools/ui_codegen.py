"""
Shared UI codegen helpers.

This module is intentionally stdlib-only so it can be used from:
- PlatformIO extra scripts (`scripts/pio_generate_ui_design.py`)
- CLI tools (`tools/ui_export_c_header.py`)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WIDGET_TYPE_MAP: dict[str, str] = {
    "label": "UIW_LABEL",
    "box": "UIW_BOX",
    "button": "UIW_BUTTON",
    "gauge": "UIW_GAUGE",
    "progressbar": "UIW_PROGRESSBAR",
    "checkbox": "UIW_CHECKBOX",
    "radiobutton": "UIW_RADIOBUTTON",
    "slider": "UIW_SLIDER",
    "textbox": "UIW_TEXTBOX",
    "panel": "UIW_PANEL",
    "icon": "UIW_ICON",
    "chart": "UIW_CHART",
}

_BORDER_STYLE_MAP: dict[str, str] = {
    "none": "UI_BORDER_NONE",
    "single": "UI_BORDER_SINGLE",
    "double": "UI_BORDER_DOUBLE",
    "rounded": "UI_BORDER_ROUNDED",
    "bold": "UI_BORDER_BOLD",
    "dashed": "UI_BORDER_DASHED",
}

_ALIGN_MAP: dict[str, str] = {"left": "UI_ALIGN_LEFT", "center": "UI_ALIGN_CENTER", "right": "UI_ALIGN_RIGHT"}
_VALIGN_MAP: dict[str, str] = {"top": "UI_VALIGN_TOP", "middle": "UI_VALIGN_MIDDLE", "bottom": "UI_VALIGN_BOTTOM"}
_OVERFLOW_MAP: dict[str, str] = {
    "ellipsis": "UI_TEXT_OVERFLOW_ELLIPSIS",
    "wrap": "UI_TEXT_OVERFLOW_WRAP",
    "clip": "UI_TEXT_OVERFLOW_CLIP",
    "auto": "UI_TEXT_OVERFLOW_AUTO",
}

_COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
}


@dataclass(frozen=True)
class StringPool:
    mapping: dict[str, str]
    decls: list[str]


def escape_c_string(text: object) -> str:
    return str(text or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def as_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def as_bool(v: object, default: bool = False) -> bool:
    if v is None:
        return bool(default)
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    s = str(hex_color or "").strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        return (255, 255, 255)
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return (r, g, b)
    except Exception:
        return (255, 255, 255)


def _get_rgb(name_or_hex: object) -> tuple[int, int, int]:
    s = str(name_or_hex or "").strip()
    if s.startswith("#"):
        return _hex_to_rgb(s)
    return _COLOR_MAP.get(s.lower(), (255, 255, 255))


def _rgb_to_gray4(r: int, g: int, b: int) -> int:
    try:
        y = 0.2126 * float(r) + 0.7152 * float(g) + 0.0722 * float(b)
    except Exception:
        y = 255.0
    v = int(round((y / 255.0) * 15.0))
    return max(0, min(15, v))


def parse_gray4(name_or_hex: object, *, default: int) -> int:
    s = str(name_or_hex or "").strip()
    if not s:
        return int(default)
    try:
        r, g, b = _get_rgb(s)
        return _rgb_to_gray4(r, g, b)
    except Exception:
        return int(default)


def style_expr(style: object) -> str:
    s = str(style or "").strip().lower()
    flags: list[str] = []
    if "inverse" in s:
        flags.append("UI_STYLE_INVERSE")
    if "highlight" in s:
        flags.append("UI_STYLE_HIGHLIGHT")
    if "bold" in s:
        flags.append("UI_STYLE_BOLD")
    if not flags:
        return "UI_STYLE_NONE"
    if len(flags) == 1:
        return flags[0]
    return "(" + " | ".join(flags) + ")"


def build_string_pool(values: list[str], *, symbol_prefix: str) -> StringPool:
    mapping: dict[str, str] = {}
    decls: list[str] = []
    for s in values:
        if not s:
            continue
        if s in mapping:
            continue
        name = f"{symbol_prefix}{len(mapping)}"
        mapping[s] = name
        decls.append(f'static const char {name}[] = "{escape_c_string(s)}";')
    return StringPool(mapping=mapping, decls=decls)


def select_scene(data: dict[str, Any], prefer_name: str) -> tuple[str, dict[str, Any]]:
    scenes = data.get("scenes", {})
    if isinstance(scenes, dict):
        if prefer_name in scenes and isinstance(scenes[prefer_name], dict):
            return prefer_name, scenes[prefer_name]
        for name, sc in scenes.items():
            if isinstance(sc, dict):
                return str(name), sc
        return prefer_name, {}
    if isinstance(scenes, list):
        for sc in scenes:
            if isinstance(sc, dict):
                name = str(sc.get("name") or sc.get("id") or prefer_name)
                return name, sc
        return prefer_name, {}
    return prefer_name, {}


def sanitize_ident(name: str) -> str:
    s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(name or ""))
    if not s:
        return "scene"
    if s[0].isdigit():
        s = "scene_" + s
    return s.lower()


def collect_widget_strings(widget: dict[str, Any]) -> list[str]:
    widget_id = str(widget.get("_widget_id") or widget.get("id") or "")
    text = str(widget.get("text", "") or "")
    constraints = str(widget.get("constraints_json", "") or widget.get("runtime", "") or "")
    anim_csv = str(widget.get("animations_csv", "") or "")
    if not anim_csv:
        anims = widget.get("animations")
        if isinstance(anims, list) and anims:
            anim_csv = ";".join([str(x) for x in anims])
    out: list[str] = []
    for s in (widget_id, text, constraints, anim_csv):
        if s:
            out.append(s)
    return out


def collect_scenes_strings(scenes: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for _scene_name, scene_data in scenes.items():
        for w in list(scene_data.get("widgets", []) or []):
            if isinstance(w, dict):
                values.extend(collect_widget_strings(w))
    return values


def border_style_for(widget: dict[str, Any], *, border: int) -> str:
    if not border:
        return "UI_BORDER_NONE"
    raw = str(widget.get("border_style", "") or "").lower()
    return _BORDER_STYLE_MAP.get(raw or "single", "UI_BORDER_SINGLE")


def align_for(widget: dict[str, Any]) -> str:
    return _ALIGN_MAP.get(str(widget.get("align", "left") or "left").lower(), "UI_ALIGN_LEFT")


def valign_for(widget: dict[str, Any]) -> str:
    return _VALIGN_MAP.get(str(widget.get("valign", "middle") or "middle").lower(), "UI_VALIGN_MIDDLE")


def overflow_for(widget: dict[str, Any]) -> str:
    return _OVERFLOW_MAP.get(
        str(widget.get("text_overflow", "ellipsis") or "ellipsis").lower(), "UI_TEXT_OVERFLOW_ELLIPSIS"
    )


def write_if_changed(path: Path, content: str) -> bool:
    try:
        existing = path.read_text(encoding="utf-8")
    except Exception:
        existing = None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def generate_ui_design_pair(json_path: Path, *, scene_name: str, source_label: str) -> tuple[str, str]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    selected_name, scene = select_scene(data, scene_name)
    widgets = scene.get("widgets", [])
    if not isinstance(widgets, list):
        widgets = []

    width = as_int(scene.get("width", data.get("width", 128)), 128)
    height = as_int(scene.get("height", data.get("height", 64)), 64)

    pool_values: list[str] = []
    for w in widgets:
        if isinstance(w, dict):
            pool_values.extend(collect_widget_strings(w))

    pool = build_string_pool(pool_values, symbol_prefix="str_")

    # Header
    h_lines: list[str] = []
    h_lines.append("/* Auto-generated: UI design for ESP32OS */")
    h_lines.append(f"/* Source: {escape_c_string(source_label)} (scene: {escape_c_string(selected_name)}) */")
    h_lines.append("#ifndef UI_DESIGN_H")
    h_lines.append("#define UI_DESIGN_H")
    h_lines.append("")
    h_lines.append("#include <stdint.h>")
    h_lines.append('#include "ui_scene.h"')
    h_lines.append("")
    h_lines.append("#define UI_ENABLE_CONSTRAINTS 1")
    h_lines.append("#define UI_ENABLE_ANIMATIONS  1")
    h_lines.append("")
    h_lines.append("#ifdef __cplusplus")
    h_lines.append('extern "C" {')
    h_lines.append("#endif")
    h_lines.append("")
    h_lines.append("/* Exported scene */")
    h_lines.append("extern const UiScene ui_design;")
    h_lines.append("#define UI_SCENE_DEMO ui_design")
    h_lines.append("")
    h_lines.append("#ifdef __cplusplus")
    h_lines.append("}")
    h_lines.append("#endif")
    h_lines.append("")
    h_lines.append("#endif /* UI_DESIGN_H */")
    h_lines.append("")

    # C
    c_lines: list[str] = []
    c_lines.append("/* Auto-generated: UI design for ESP32OS */")
    c_lines.append(f"/* Source: {escape_c_string(source_label)} (scene: {escape_c_string(selected_name)}) */")
    c_lines.append('#include "ui_design.h"')
    c_lines.append("")
    c_lines.append("/* String pool */")
    if pool.decls:
        c_lines.extend(pool.decls)
    else:
        c_lines.append("/* (empty) */")
    c_lines.append("")
    c_lines.append("/* Widget definitions */")
    c_lines.append("static const UiWidget widgets[] = {")

    for idx, w in enumerate(widgets):
        if not isinstance(w, dict):
            continue
        wtype = WIDGET_TYPE_MAP.get(str(w.get("type", "label")).lower(), "UIW_LABEL")
        x = as_int(w.get("x", 0), 0)
        y = as_int(w.get("y", 0), 0)
        ww = as_int(w.get("width", 8), 8)
        hh = as_int(w.get("height", 8), 8)
        border = 1 if as_bool(w.get("border", True), True) else 0
        checked = 1 if as_bool(w.get("checked", False), False) else 0
        value = as_int(w.get("value", 0), 0)
        min_value = as_int(w.get("min_value", 0), 0)
        max_value = as_int(w.get("max_value", 100), 100)

        widget_id = str(w.get("_widget_id") or w.get("id") or "")
        text = str(w.get("text", "") or "")
        constraints = str(w.get("constraints_json", "") or w.get("runtime", "") or "")
        anim_csv = str(w.get("animations_csv", "") or "")
        if not anim_csv:
            anims = w.get("animations")
            if isinstance(anims, list) and anims:
                anim_csv = ";".join([str(x) for x in anims])

        id_ref = pool.mapping.get(widget_id, "") if widget_id else ""
        text_ref = pool.mapping.get(text, "") if text else ""
        c_ref = pool.mapping.get(constraints, "") if constraints else ""
        a_ref = pool.mapping.get(anim_csv, "") if anim_csv else ""

        fg = parse_gray4(w.get("color_fg", ""), default=15)
        bg = parse_gray4(w.get("color_bg", ""), default=0)
        border_style = border_style_for(w, border=border)
        align = align_for(w)
        valign = valign_for(w)
        overflow = overflow_for(w)
        max_lines = as_int(w.get("max_lines", 0), 0)
        if max_lines < 0:
            max_lines = 0
        style = style_expr(w.get("style", ""))
        visible = 1 if as_bool(w.get("visible", True), True) else 0
        enabled = 1 if as_bool(w.get("enabled", True), True) else 0

        preview = text or widget_id or ""
        c_lines.append(f'    {{ /* [{idx}] {wtype} "{escape_c_string(preview)}" */')
        c_lines.append(f"        .type = {wtype},")
        c_lines.append(f"        .x = {x}, .y = {y}, .width = {ww}, .height = {hh},")
        c_lines.append(f"        .border = {border}, .checked = {checked},")
        c_lines.append(f"        .value = {value}, .min_value = {min_value}, .max_value = {max_value},")
        c_lines.append(f"        .id = {id_ref if id_ref else 'NULL'},")
        c_lines.append(f"        .text = {text_ref if text_ref else 'NULL'},")
        c_lines.append(f"        .constraints_json = {c_ref if c_ref else 'NULL'},")
        c_lines.append(f"        .animations_csv = {a_ref if a_ref else 'NULL'},")
        c_lines.append(f"        .fg = {fg}, .bg = {bg},")
        c_lines.append(f"        .border_style = {border_style},")
        c_lines.append(f"        .align = {align}, .valign = {valign},")
        c_lines.append(f"        .text_overflow = {overflow}, .max_lines = {max_lines},")
        c_lines.append(f"        .style = {style},")
        c_lines.append(f"        .visible = {visible}, .enabled = {enabled},")
        c_lines.append("    },")

    c_lines.append("};")
    c_lines.append("")
    c_lines.append("/* Scene definition */")
    c_lines.append("const UiScene ui_design = {")
    c_lines.append(f'    .name = "{escape_c_string(selected_name)}",')
    c_lines.append(f"    .width = {width},")
    c_lines.append(f"    .height = {height},")
    c_lines.append("    .widget_count = (uint16_t)(sizeof(widgets) / sizeof(widgets[0])),")
    c_lines.append("    .widgets = widgets,")
    c_lines.append("};")
    c_lines.append("")

    return "\n".join(c_lines), "\n".join(h_lines)


def load_scenes(json_path: Path) -> dict[str, Any]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    scenes_raw = data.get("scenes", {})
    if isinstance(scenes_raw, list):
        return {
            str(scene.get("id") or scene.get("name") or f"scene_{i}"): scene for i, scene in enumerate(scenes_raw)
        }
    if isinstance(scenes_raw, dict):
        return scenes_raw
    return {}


def generate_scenes_header(
    json_path: Path,
    *,
    guard: str,
    source_name: str,
    generated_ts: str,
) -> str:
    scenes = load_scenes(json_path)
    if not scenes:
        raise ValueError("No scenes found in JSON.")

    pool = build_string_pool(collect_scenes_strings(scenes), symbol_prefix="ui_str_")

    lines: list[str] = []
    lines.append("/*")
    lines.append(" * Auto-generated UI scenes header (ESP32OS)")
    lines.append(f" * Source: {source_name}")
    lines.append(f" * Generated: {generated_ts}")
    lines.append(" * DO NOT EDIT MANUALLY")
    lines.append(" */")
    lines.append("")
    lines.append(f"#ifndef {guard}")
    lines.append(f"#define {guard}")
    lines.append("")
    lines.append('#include "ui_scene.h"')
    lines.append("")

    if pool.decls:
        lines.append("/* String pool */")
        lines.extend(pool.decls)
        lines.append("")

    scene_names: list[str] = []

    for scene_name, scene_data in scenes.items():
        safe = sanitize_ident(scene_name)
        scene_names.append(safe)
        width = as_int(scene_data.get("width", 128), 128)
        height = as_int(scene_data.get("height", 64), 64)
        widgets = list(scene_data.get("widgets", []) or [])
        try:
            widgets.sort(key=lambda ww: (as_int(ww.get("z_index", 0), 0),))
        except Exception:
            pass

        lines.append(f"/* Scene: {scene_name} ({width}x{height}) */")
        lines.append(f"static const UiWidget {safe}_widgets[] = {{")
        if not widgets:
            lines.append("    /* empty */")
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            wtype = WIDGET_TYPE_MAP.get(str(w.get("type", "label")).lower(), "UIW_LABEL")
            x = as_int(w.get("x", 0), 0)
            y = as_int(w.get("y", 0), 0)
            ww = as_int(w.get("width", 8), 8)
            hh = as_int(w.get("height", 8), 8)
            border = 1 if as_bool(w.get("border", True), True) else 0
            checked = 1 if as_bool(w.get("checked", False), False) else 0
            value = as_int(w.get("value", 0), 0)
            min_value = as_int(w.get("min_value", 0), 0)
            max_value = as_int(w.get("max_value", 100), 100)

            widget_id = str(w.get("_widget_id") or w.get("id") or "")
            text = str(w.get("text", "") or "")
            constraints = str(w.get("constraints_json", "") or w.get("runtime", "") or "")
            anim_csv = str(w.get("animations_csv", "") or "")
            if not anim_csv:
                anims = w.get("animations")
                if isinstance(anims, list) and anims:
                    anim_csv = ";".join([str(x) for x in anims])

            id_ref = pool.mapping.get(widget_id, "") if widget_id else ""
            text_ref = pool.mapping.get(text, "") if text else ""
            c_ref = pool.mapping.get(constraints, "") if constraints else ""
            a_ref = pool.mapping.get(anim_csv, "") if anim_csv else ""

            fg = parse_gray4(w.get("color_fg", ""), default=15)
            bg = parse_gray4(w.get("color_bg", ""), default=0)

            border_style = border_style_for(w, border=border)
            align = align_for(w)
            valign = valign_for(w)
            overflow = overflow_for(w)
            max_lines = as_int(w.get("max_lines", 0), 0)
            if max_lines < 0:
                max_lines = 0
            style = style_expr(w.get("style", ""))
            visible = 1 if as_bool(w.get("visible", True), True) else 0
            enabled = 1 if as_bool(w.get("enabled", True), True) else 0

            lines.append(f"    {{ /* [{idx}] {wtype} */")
            lines.append(f"        .type = {wtype},")
            lines.append(f"        .x = {x}, .y = {y}, .width = {ww}, .height = {hh},")
            lines.append(f"        .border = {border}, .checked = {checked},")
            lines.append(f"        .value = {value}, .min_value = {min_value}, .max_value = {max_value},")
            lines.append(f"        .id = {id_ref if id_ref else 'NULL'},")
            lines.append(f"        .text = {text_ref if text_ref else 'NULL'},")
            lines.append(f"        .constraints_json = {c_ref if c_ref else 'NULL'},")
            lines.append(f"        .animations_csv = {a_ref if a_ref else 'NULL'},")
            lines.append(f"        .fg = {fg}, .bg = {bg},")
            lines.append(f"        .border_style = {border_style},")
            lines.append(f"        .align = {align}, .valign = {valign},")
            lines.append(f"        .text_overflow = {overflow}, .max_lines = {max_lines},")
            lines.append(f"        .style = {style},")
            lines.append(f"        .visible = {visible}, .enabled = {enabled},")
            lines.append("    },")
        lines.append("};")
        lines.append("")
        lines.append(f"static const UiScene {safe}_scene = {{")
        lines.append(f'    .name = "{escape_c_string(scene_name)}",')
        lines.append(f"    .width = {width}, .height = {height},")
        lines.append(f"    .widget_count = (uint16_t)(sizeof({safe}_widgets) / sizeof({safe}_widgets[0])),")
        lines.append(f"    .widgets = {safe}_widgets,")
        lines.append("};")
        lines.append("")

    lines.append("/* Scene registry */")
    lines.append("static const UiScene *all_scenes[] = {")
    for safe in scene_names:
        lines.append(f"    &{safe}_scene,")
    lines.append("};")
    lines.append(f"#define UI_SCENE_COUNT {len(scene_names)}")
    lines.append("")
    lines.append(f"#endif /* {guard} */")
    lines.append("")

    return "\n".join(lines)

