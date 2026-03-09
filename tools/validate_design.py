#!/usr/bin/env python3
"""
Validate ESP32OS UI design JSON — comprehensive 122-rule checker.

Covers:
- required fields + basic types
- supported widget types (exportable to `UiWidget` in `src/ui_scene.h`)
- geometry sanity (within scene bounds, integer coords, positive dims, uint16 overflow)
- duplicate widget IDs, ID format
- text overflow (horizontal + vertical), min text height/width, text length
- value range sanity (gauge, slider, progressbar)
- value field type checks + firmware int16 overflow
- border consistency (border=True needs visible border_style, double border min size)
- color parseability, visibility, and contrast
- minimum widget sizes for gauge/slider/progressbar/checkbox/radiobutton/slider-height
- z_index type, runtime format + key validation, edge margins
- widget overlap detection
- empty text without runtime binding, invisible widget with runtime
- font charset compliance
- style field validation
- chart data_points validation
- icon widget requires icon_char
- non-negative padding/margin
- excessive widget count per scene
- scene name validation, animations field type
- locked field type, state_overrides structure
- scene dimension limits, textbox min size, panel border recommendation
- constraints & responsive_rules type, parent_id reference, align-border, widget ID length
- font_size / corner_radius / border_width type, border_color parseability
- mostly-outside-scene detection, bold field type, duplicate geometry, disabled+no-runtime

Usage:
  python tools/validate_design.py main_scene.json
  python tools/validate_design.py main_scene.json --warnings-as-errors
    python tools/validate_design.py main_scene.json --strict-critical
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ui_codegen import WIDGET_TYPE_MAP  # noqa: E402

# ── Enum sets ──────────────────────────────────────────────────────────────
ALLOWED_BORDER_STYLES = {"none", "", "single", "double", "rounded", "bold", "dashed"}
ALLOWED_ALIGN = {"left", "center", "right"}
ALLOWED_VALIGN = {"top", "middle", "bottom"}
ALLOWED_OVERFLOW = {"ellipsis", "wrap", "clip", "auto"}
ALLOWED_STYLES = {"", "default", "bold", "inverse", "highlight", "bar", "line"}

# Widget types that carry visible text and need overflow checks
TEXT_TYPES = {"label", "button", "checkbox", "textbox", "radiobutton"}

# Widget types that carry value/min/max fields
VALUE_TYPES = {"gauge", "progressbar", "slider"}

# Focusable types in firmware (ui_nav.c)
FOCUSABLE_TYPES = {"button", "checkbox", "radiobutton", "slider"}

# Valid constraint dict keys (ui_models.py Constraints TypedDict)
ALLOWED_CONSTRAINT_KEYS = {"b", "ax", "ay", "sx", "sy", "mx", "my", "mr", "mb"}

# Valid runtime meta keys (ui_meta.c ui_meta_parse)
ALLOWED_RUNTIME_META_KEYS = {"bind", "key", "kind", "type", "min", "max", "step", "values"}

# ── Rendering constants (must match drawing.py / firmware) ──────────────
CHAR_W = 6       # font6x8 char width
CHAR_H = 8       # font6x8 char height
RENDER_PAD = 2   # per-side padding (clip_rect = rect.inflate(-4, -4))
MIN_TEXT_H = RENDER_PAD * 2 + CHAR_H  # 12 — minimum for 1 text line

# Firmware field limits (must match uint16_t / int16_t in ui_scene.h)
INT16_MIN = -32768
INT16_MAX = 32767
UINT16_MAX = 65535
MAX_WIDGETS_PER_SCENE = 64  # soft limit; ESP32 memory pressure
MAX_TEXT_LEN = 127           # practical limit for OLED readability

# Valid widget ID pattern: letters, digits, underscore, hyphen, dot
_WIDGET_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
_SCENE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RUNTIME_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

# Supported characters in font6x8 (lowercase auto-mapped to uppercase)
FONT_CHARS = set(" .:_-/%?+<>!=(),#*0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# ── Color helpers ──────────────────────────────────────────────────────────
_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255),
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
    "gray": (128, 128, 128), "grey": (128, 128, 128),
}
MIN_VISIBLE_BRIGHTNESS = 0x20  # ~12 % — anything below is unreadable on OLED
MIN_CONTRAST = 40              # min brightness delta between fg and bg
MIN_EDGE_MARGIN = 2            # px from screen edge for non-full-span widgets

# Warning text fragments promoted to ERROR when strict_critical=True.
CRITICAL_WARNING_MARKERS = (
    "overlap",
    "too short for text",
    "too short to render text",
    "too narrow for text",
    "low contrast",
    "too dim",
    "fully outside scene",
    "outside scene bounds",
)


def _parse_color(s: str) -> tuple[int, int, int] | None:
    if not s:
        return None
    low = s.strip().lower()
    if low in _NAMED_COLORS:
        return _NAMED_COLORS[low]
    m = _HEX_RE.match(s.strip())
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return None


def _brightness(rgb: tuple[int, int, int]) -> int:
    return int(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])


def _is_critical_warning(message: str) -> bool:
    msg = message.lower()
    return any(marker in msg for marker in CRITICAL_WARNING_MARKERS)


# ── Core types ─────────────────────────────────────────────────────────────

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


def _wref(scene_name: str, w: dict[str, Any], idx: int) -> str:
    wid = w.get("_widget_id") or w.get("id") or f"#{idx}"
    return f"scene '{scene_name}': widget[{idx}] ({wid})"


# ── Main validator ─────────────────────────────────────────────────────────

def validate_data(
    data: dict[str, Any],
    *,
    file_label: str,
    warnings_as_errors: bool,
    strict_critical: bool = False,
) -> list[Issue]:
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

    # ── Rule 36: Scene name validation ──
    for scene_name in scenes:
        if not scene_name or not _SCENE_NAME_RE.match(scene_name):
            issues.append(Issue("WARN", f"{file_label}: scene name '{scene_name}' has invalid characters"))

    for scene_name, scene in scenes.items():
        pfx = f"{file_label}: {scene_name}"
        scene_w = scene.get("width", root_w)
        scene_h = scene.get("height", root_h)
        if not _is_int(scene_w) or int(scene_w) <= 0:
            issues.append(Issue("ERROR", f"{pfx}: width must be int >= 1"))
            continue
        if not _is_int(scene_h) or int(scene_h) <= 0:
            issues.append(Issue("ERROR", f"{pfx}: height must be int >= 1"))
            continue
        sw, sh = int(scene_w), int(scene_h)

        widgets = scene.get("widgets", [])
        if not isinstance(widgets, list):
            issues.append(Issue("ERROR", f"{pfx}: widgets must be a list"))
            continue

        # ── Rule 22: Scene must not be empty ──
        if not widgets:
            issues.append(Issue("WARN", f"{pfx}: scene has 0 widgets"))

        seen_ids: set[str] = set()

        for idx, w in enumerate(widgets):
            ref = _wref(scene_name, w, idx)
            wl = f"{pfx}: {ref}"
            if not isinstance(w, dict):
                issues.append(Issue("ERROR", f"{wl}: widget must be an object"))
                continue

            # ── Rule 2: Valid widget type ──
            wtype = w.get("type")
            if not isinstance(wtype, str) or not wtype.strip():
                issues.append(Issue("ERROR", f"{wl}: missing/invalid 'type'"))
                continue
            wt = wtype.lower()
            if wt not in WIDGET_TYPE_MAP:
                issues.append(Issue("ERROR", f"{wl}: unsupported type '{wtype}'"))

            # ── Required geometry fields ──
            for key in ("x", "y", "width", "height"):
                if key not in w:
                    issues.append(Issue("ERROR", f"{wl}: missing '{key}'"))

            x = w.get("x")
            y = w.get("y")
            ww = w.get("width")
            hh = w.get("height")
            text_raw = w.get("text", "")
            text = str(text_raw) if isinstance(text_raw, str) else ""
            has_border = w.get("border", False)
            runtime_raw = w.get("runtime", "")
            runtime = str(runtime_raw) if isinstance(runtime_raw, str) else ""

            # ── Rule 5: Integer coordinates ──
            all_int = True
            for dim_name, dim_val in [("x", x), ("y", y), ("width", ww), ("height", hh)]:
                if not _is_int(dim_val):
                    issues.append(Issue("ERROR", f"{wl}: {dim_name} must be int"))
                    all_int = False
            if not all_int:
                continue
            x, y, ww, hh = int(x), int(y), int(ww), int(hh)  # type: ignore[arg-type]

            # ── Rule 3: Positive dimensions ──
            if ww < 1 or hh < 1:
                issues.append(Issue("ERROR", f"{wl}: dimensions {ww}x{hh} must be >= 1x1"))

            # ── Rule 4: Within scene bounds ──
            if x < 0 or y < 0:
                issues.append(Issue("ERROR", f"{wl}: origin ({x},{y}) is negative"))
            if x + ww > sw or y + hh > sh:
                issues.append(Issue("WARN", f"{wl}: rect ({x},{y},{ww},{hh}) out of bounds {sw}x{sh}"))

            # ── Rule 1: Unique widget IDs ──
            widget_id = w.get("_widget_id") or w.get("id")
            if widget_id is not None:
                if not isinstance(widget_id, str):
                    issues.append(Issue("ERROR", f"{wl}: _widget_id/id must be string"))
                else:
                    if widget_id in seen_ids:
                        issues.append(Issue("ERROR", f"{wl}: duplicate id '{widget_id}'"))
                    seen_ids.add(widget_id)

            # ── Bool fields ──
            for key in ("border", "checked", "visible", "enabled"):
                if key in w and not _is_bool(w.get(key)):
                    issues.append(Issue("ERROR", f"{wl}: '{key}' must be boolean"))

            # ── max_lines ──
            if "max_lines" in w and w.get("max_lines") is not None and not _is_int(w.get("max_lines")):
                issues.append(Issue("ERROR", f"{wl}: max_lines must be int or null"))
            if _is_int(w.get("max_lines")) and int(w.get("max_lines")) < 0:  # type: ignore[arg-type]
                issues.append(Issue("ERROR", f"{wl}: max_lines must be >= 0"))

            # ── Rule 12: Valid border_style ──
            if "border_style" in w:
                bs = w.get("border_style")
                if not isinstance(bs, str) or bs.lower() not in ALLOWED_BORDER_STYLES:
                    issues.append(Issue("ERROR", f"{wl}: invalid border_style '{bs}'"))

            # ── Rule 11: Valid align/valign ──
            if "align" in w:
                a = w.get("align")
                if not isinstance(a, str) or a.lower() not in ALLOWED_ALIGN:
                    issues.append(Issue("ERROR", f"{wl}: invalid align '{a}'"))
            if "valign" in w:
                va = w.get("valign")
                if not isinstance(va, str) or va.lower() not in ALLOWED_VALIGN:
                    issues.append(Issue("ERROR", f"{wl}: invalid valign '{va}'"))

            # ── Rule 14: Valid text_overflow ──
            if "text_overflow" in w:
                ov = w.get("text_overflow")
                if not isinstance(ov, str) or ov.lower() not in ALLOWED_OVERFLOW:
                    issues.append(Issue("ERROR", f"{wl}: invalid text_overflow '{ov}'"))

            # ── Rule 13: border=True requires a visible border_style ──
            bstyle = (str(w.get("border_style", "none")) or "none").lower()
            if has_border is True and bstyle in {"none", ""}:
                issues.append(Issue("WARN", f"{wl}: border=True but border_style='{bstyle}'"))

            # ── Rule 6: Minimum height for text types ──
            if wt in TEXT_TYPES and hh < MIN_TEXT_H:
                issues.append(Issue("WARN", f"{wl}: h={hh} < min {MIN_TEXT_H} for text widget"))

            # ── Rule 8: Minimum widget width for text types ──
            if wt in TEXT_TYPES and text:
                min_w = RENDER_PAD * 2 + CHAR_W
                if ww < min_w:
                    issues.append(Issue("WARN", f"{wl}: w={ww} < min {min_w} (can't fit 1 char)"))

            # ── Rule 7: Text overflow check (H+V) ──
            if wt in TEXT_TYPES and text:
                margin = RENDER_PAD * 2
                inner_w = ww - margin
                inner_h = hh - margin
                max_lines = inner_h // CHAR_H if inner_h > 0 else 0
                max_chars = inner_w // CHAR_W if inner_w > 0 else 0
                if max_lines < 1:
                    issues.append(Issue("WARN", f"{wl}: h={hh} → 0 text lines (need inner_h >= {CHAR_H})"))
                if max_chars > 0 and len(text) > max_chars:
                    issues.append(Issue("WARN", f"{wl}: text '{text}' ({len(text)} ch) > max {max_chars} chars"))

            # ── Rule 9: Value range sanity ──
            if wt in ("gauge", "progressbar", "slider"):
                vmin = w.get("min_value", 0)
                vmax = w.get("max_value", 100)
                val = w.get("value", 0)
                if _is_int(vmin) and _is_int(vmax):
                    if vmin >= vmax:
                        issues.append(Issue("ERROR", f"{wl}: min_value={vmin} >= max_value={vmax}"))
                    if _is_int(val) and (val < vmin or val > vmax):
                        issues.append(Issue("WARN", f"{wl}: value={val} not in [{vmin},{vmax}]"))

            # ── Rule 18: Minimum gauge/slider/progressbar size ──
            if wt == "gauge" and (ww < 8 or hh < 8):
                issues.append(Issue("ERROR", f"{wl}: gauge {ww}x{hh} too small (min 8x8)"))
            if wt == "slider" and ww < 16:
                issues.append(Issue("ERROR", f"{wl}: slider w={ww} too narrow (min 16)"))
            if wt == "progressbar" and ww < 8:
                issues.append(Issue("ERROR", f"{wl}: progressbar w={ww} too narrow (min 8)"))

            # ── Rule 19: z_index is an integer ──
            z = w.get("z_index", 0)
            if not _is_int(z):
                issues.append(Issue("ERROR", f"{wl}: z_index={z!r} must be int"))

            # ── Rule 15: Foreground color parseable + visibility ──
            fg_str = w.get("color_fg", "")
            if fg_str:
                fg_rgb = _parse_color(fg_str)
                if fg_rgb is None:
                    issues.append(Issue("WARN", f"{wl}: can't parse color_fg '{fg_str}'"))
                elif wt in TEXT_TYPES and text:
                    br = _brightness(fg_rgb)
                    if br < MIN_VISIBLE_BRIGHTNESS:
                        issues.append(Issue("WARN", f"{wl}: fg '{fg_str}' too dim ({br}) for text"))

            # ── Rule 16: Background color parseable ──
            bg_str = w.get("color_bg", "")
            if bg_str:
                bg_rgb = _parse_color(bg_str)
                if bg_rgb is None:
                    issues.append(Issue("WARN", f"{wl}: can't parse color_bg '{bg_str}'"))

            # ── Rule 17: Contrast check (fg vs bg for text widgets) ──
            if wt in TEXT_TYPES and text and fg_str and bg_str:
                fg_rgb = _parse_color(fg_str)
                bg_rgb = _parse_color(bg_str)
                if fg_rgb and bg_rgb:
                    contrast = abs(_brightness(fg_rgb) - _brightness(bg_rgb))
                    if contrast < MIN_CONTRAST:
                        issues.append(Issue("WARN", f"{wl}: low contrast ({contrast}) fg='{fg_str}' vs bg='{bg_str}'"))

            # ── Rule 20: runtime string format ──
            if runtime:
                for part in runtime.split(";"):
                    part = part.strip()
                    if not part:
                        continue
                    if "=" not in part:
                        issues.append(Issue("ERROR", f"{wl}: runtime '{part}' missing '='"))
                        break

            # ── Rule 24: Edge margin (non-full-span widgets shouldn't touch edges) ──
            if ww < sw and x > 0 and x + ww > sw - MIN_EDGE_MARGIN:
                issues.append(Issue("WARN", f"{wl}: right edge too close to boundary ({x + ww} > {sw - MIN_EDGE_MARGIN})"))
            if hh < sh and y > 0 and y + hh > sh - MIN_EDGE_MARGIN:
                issues.append(Issue("WARN", f"{wl}: bottom edge too close to boundary ({y + hh} > {sh - MIN_EDGE_MARGIN})"))

            # ── Rule 25: Text widget with no text and no runtime binding ──
            if wt in TEXT_TYPES and not text and not runtime:
                issues.append(Issue("WARN", f"{wl}: {wt} with no text and no runtime binding"))

            # ── Rule 26: Font charset compliance ──
            if wt in TEXT_TYPES and text:
                bad = [ch for ch in text if ch.upper() not in FONT_CHARS]
                if bad:
                    unique = "".join(sorted(set(bad)))
                    issues.append(Issue("WARN", f"{wl}: unsupported chars in text: {unique!r}"))

            # ── Rule 10: Firmware int16 overflow (value/min/max) ──
            for vf in ("value", "min_value", "max_value"):
                vv = w.get(vf)
                if _is_int(vv) and (vv < INT16_MIN or vv > INT16_MAX):
                    issues.append(Issue("ERROR", f"{wl}: {vf}={vv} overflows int16 [{INT16_MIN},{INT16_MAX}]"))

            # ── Rule 23: Style field validation ──
            if "style" in w:
                st = w.get("style")
                if not isinstance(st, str) or st.lower() not in ALLOWED_STYLES:
                    issues.append(Issue("ERROR", f"{wl}: invalid style '{st}'"))

            # ── Rule 27: Widget ID format ──
            if widget_id is not None and isinstance(widget_id, str) and widget_id:
                if not _WIDGET_ID_RE.match(widget_id):
                    issues.append(Issue("ERROR", f"{wl}: id '{widget_id}' contains invalid characters"))

            # ── Rule 28: Chart data_points validation ──
            if wt == "chart":
                dp = w.get("data_points")
                if dp is not None:
                    if not isinstance(dp, list):
                        issues.append(Issue("ERROR", f"{wl}: data_points must be a list"))
                    else:
                        bad_dp = [v for v in dp if not isinstance(v, (int, float)) or isinstance(v, bool)]
                        if bad_dp:
                            issues.append(Issue("ERROR", f"{wl}: data_points contains non-numeric values"))

            # ── Rule 29: Icon widget requires icon_char ──
            if wt == "icon":
                ic = w.get("icon_char", "")
                if not ic:
                    issues.append(Issue("WARN", f"{wl}: icon widget has no icon_char"))

            # ── Rule 30: Checkbox/radiobutton minimum size ──
            if wt in ("checkbox", "radiobutton") and (ww < 10 or hh < 10):
                issues.append(Issue("WARN", f"{wl}: {wt} {ww}x{hh} too small (min 10x10)"))

            # ── Rule 31: Non-negative padding/margin ──
            for pm_key in ("padding_x", "padding_y", "margin_x", "margin_y"):
                pm_val = w.get(pm_key)
                if _is_int(pm_val) and pm_val < 0:
                    issues.append(Issue("ERROR", f"{wl}: {pm_key}={pm_val} must be >= 0"))

            # ── Rule 32: Value field type check ──
            if wt in VALUE_TYPES:
                for vf in ("value", "min_value", "max_value"):
                    vv = w.get(vf)
                    if vv is not None and not _is_int(vv):
                        issues.append(Issue("ERROR", f"{wl}: {vf}={vv!r} must be int"))

            # ── Rule 34: Slider minimum height ──
            if wt == "slider" and hh < MIN_TEXT_H:
                issues.append(Issue("WARN", f"{wl}: slider h={hh} too short (min {MIN_TEXT_H})"))

            # ── Rule 35: Double border minimum size ──
            if bstyle == "double" and (ww < 5 or hh < 5):
                issues.append(Issue("WARN", f"{wl}: double border needs >= 5x5, got {ww}x{hh}"))

            # ── Rule 37: Animations field must be a list ──
            if "animations" in w:
                anim = w.get("animations")
                if anim is not None and not isinstance(anim, list):
                    issues.append(Issue("ERROR", f"{wl}: animations must be a list"))
                elif isinstance(anim, list):
                    bad_items = [a for a in anim if not isinstance(a, str)]
                    if bad_items:
                        issues.append(Issue("ERROR", f"{wl}: animations contains non-string items"))

            # ── Rule 38: Geometry uint16 overflow ──
            for gf, gv in [("x", x), ("y", y), ("width", ww), ("height", hh)]:
                if gv > UINT16_MAX:
                    issues.append(Issue("ERROR", f"{wl}: {gf}={gv} overflows uint16 (max {UINT16_MAX})"))

            # ── Rule 39: Text length warning ──
            if wt in TEXT_TYPES and text and len(text) > MAX_TEXT_LEN:
                issues.append(Issue("WARN", f"{wl}: text length {len(text)} exceeds {MAX_TEXT_LEN} chars"))

            # ── Rule 40: Runtime key validation ──
            if runtime:
                for part in runtime.split(";"):
                    part = part.strip()
                    if not part:
                        continue
                    if "=" in part:
                        key = part.split("=", 1)[0].strip()
                        if key and not _RUNTIME_KEY_RE.match(key):
                            issues.append(Issue("WARN", f"{wl}: runtime key '{key}' has invalid format"))

            # ── Rule 41: Completely invisible widget ──
            if x >= sw and y >= sh:
                issues.append(Issue("WARN", f"{wl}: widget at ({x},{y}) fully outside scene {sw}x{sh}"))

            # ── Rule 42: Hidden widget with runtime binding ──
            if w.get("visible") is False and runtime:
                issues.append(Issue("WARN", f"{wl}: widget is hidden (visible=false) but has runtime binding"))

            # ── Rule 43: locked field must be bool ──
            if "locked" in w and not _is_bool(w.get("locked")):
                issues.append(Issue("ERROR", f"{wl}: 'locked' must be boolean"))

            # ── Rule 44: state_overrides must be a dict of dicts ──
            if "state_overrides" in w:
                so = w.get("state_overrides")
                if so is not None and not isinstance(so, dict):
                    issues.append(Issue("ERROR", f"{wl}: state_overrides must be a dict"))
                elif isinstance(so, dict):
                    for sk, sv in so.items():
                        if not isinstance(sv, dict):
                            issues.append(Issue("ERROR", f"{wl}: state_overrides['{sk}'] must be a dict"))

            # ── Rule 45: Scene dimensions within uint16 ──
        if sw > UINT16_MAX or sh > UINT16_MAX:
            issues.append(Issue("ERROR", f"{pfx}: scene dimensions {sw}x{sh} overflow uint16 (max {UINT16_MAX})"))

        # ── Per-widget rules that need full pass complete ──
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            ref = _wref(scene_name, w, idx)
            wl = f"{pfx}: {ref}"
            wtype = w.get("type")
            if not isinstance(wtype, str) or not wtype.strip():
                continue
            wt = wtype.lower()
            ww = w.get("width", 0)
            hh = w.get("height", 0)
            if not (_is_int(ww) and _is_int(hh)):
                continue

            # ── Rule 46: Textbox minimum size ──
            if wt == "textbox" and (ww < 20 or hh < MIN_TEXT_H):
                issues.append(Issue("WARN", f"{wl}: textbox {ww}x{hh} too small (min 20x{MIN_TEXT_H})"))

            # ── Rule 47: Panel with content but no border or bg ──
            text_raw2 = w.get("text", "")
            text = str(text_raw2) if isinstance(text_raw2, str) else ""
            has_border = w.get("border", False)
            bg_str = w.get("color_bg", "")
            if wt == "panel" and not has_border and not bg_str:
                issues.append(Issue("WARN", f"{wl}: panel has no border and no background color"))

            # ── Rule 48: z_index range warning ──
            z = w.get("z_index", 0)
            if _is_int(z) and (z < -100 or z > 200):
                issues.append(Issue("WARN", f"{wl}: z_index={z} is extreme (typical range -100..200)"))

            # ── Rule 49: Duplicate text in same scene (exact match warning) ──
            # (computed after per-widget loop, below)

            # ── Rule 50: icon_char length check ──
            ic = w.get("icon_char", "")
            if isinstance(ic, str) and len(ic) > 1:
                issues.append(Issue("WARN", f"{wl}: icon_char '{ic}' should be a single character"))

            # ── Rule 51: constraints must be a dict ──
            if "constraints" in w:
                ct = w.get("constraints")
                if ct is not None and not isinstance(ct, dict):
                    issues.append(Issue("ERROR", f"{wl}: constraints must be a dict"))

            # ── Rule 52: responsive_rules must be a list ──
            if "responsive_rules" in w:
                rr = w.get("responsive_rules")
                if rr is not None and not isinstance(rr, list):
                    issues.append(Issue("ERROR", f"{wl}: responsive_rules must be a list"))

            # ── Rule 53: parent_id must reference existing widget ID ──
            pid = w.get("parent_id")
            if pid is not None and isinstance(pid, str) and pid:
                if pid not in seen_ids and pid != (w.get("_widget_id") or w.get("id")):
                    issues.append(Issue("WARN", f"{wl}: parent_id '{pid}' not found in scene"))

            # ── Rule 54: Center-aligned text in very narrow widget ──
            align = str(w.get("align", "left") or "left").lower()
            if wt in TEXT_TYPES and align == "center" and ww < CHAR_W * 3 + RENDER_PAD * 2:
                issues.append(Issue("WARN", f"{wl}: center-aligned in narrow widget (w={ww})"))

            # ── Rule 55: Widget ID max length ──
            wid = w.get("_widget_id") or w.get("id") or ""
            if isinstance(wid, str) and len(wid) > 64:
                issues.append(Issue("WARN", f"{wl}: widget ID length {len(wid)} exceeds 64 chars"))

            # ── Rule 56: data_points on non-chart widget ──
            if wt != "chart" and w.get("data_points"):
                issues.append(Issue("WARN", f"{wl}: data_points on non-chart widget '{wt}'"))

            # ── Rule 57: value fields on non-value widget ──
            if wt not in VALUE_TYPES and wt != "chart":
                for vf in ("min_value", "max_value"):
                    vv57 = w.get(vf)
                    # Ignore schema defaults commonly present on all widgets.
                    if vf == "min_value" and vv57 == 0:
                        continue
                    if vf == "max_value" and vv57 == 100 and w.get("min_value") == 0:
                        continue
                    if vf in w and vv57 != 0:
                        issues.append(Issue("WARN", f"{wl}: {vf} on non-value widget '{wt}'"))

            # ── Rule 58: Negative dimensions ──
            if ww < 0 or hh < 0:
                issues.append(Issue("ERROR", f"{wl}: negative dimension {ww}x{hh}"))

            # ── Rule 59: font_size must be positive int if present ──
            fs = w.get("font_size")
            if fs is not None:
                if not _is_int(fs) or fs < 1:
                    issues.append(Issue("ERROR", f"{wl}: font_size={fs!r} must be a positive int"))

            # ── Rule 60: corner_radius must be non-negative int if present ──
            cr = w.get("corner_radius")
            if cr is not None:
                if not _is_int(cr) or cr < 0:
                    issues.append(Issue("ERROR", f"{wl}: corner_radius={cr!r} must be a non-negative int"))

            # ── Rule 61: border_width must be non-negative int if present ──
            bw = w.get("border_width")
            if bw is not None:
                if not _is_int(bw) or bw < 0:
                    issues.append(Issue("ERROR", f"{wl}: border_width={bw!r} must be a non-negative int"))

            # ── Rule 62: border_color must be parseable if present ──
            bc = w.get("border_color", "")
            if bc:
                if _parse_color(str(bc)) is None:
                    issues.append(Issue("WARN", f"{wl}: can't parse border_color '{bc}'"))

            # ── Rule 63: Widget mostly outside scene (>75% area outside) ──
            if ww > 0 and hh > 0:
                vis_x1 = max(0, min(x, sw))
                vis_y1 = max(0, min(y, sh))
                vis_x2 = max(0, min(x + ww, sw))
                vis_y2 = max(0, min(y + hh, sh))
                vis_area = max(0, vis_x2 - vis_x1) * max(0, vis_y2 - vis_y1)
                total_area = ww * hh
                if total_area > 0 and vis_area < total_area * 0.25:
                    pct = int(100 * vis_area / total_area)
                    issues.append(Issue("WARN", f"{wl}: only {pct}% visible inside scene bounds"))

            # ── Rule 64: bold field must be bool ──
            if "bold" in w and not _is_bool(w.get("bold")):
                issues.append(Issue("ERROR", f"{wl}: 'bold' must be boolean"))

            # ── Rule 67: theme_fg_role / theme_bg_role must be strings ──
            for role_key in ("theme_fg_role", "theme_bg_role"):
                rv = w.get(role_key)
                if rv is not None and not isinstance(rv, str):
                    issues.append(Issue("ERROR", f"{wl}: {role_key}={rv!r} must be a string"))

            # ── Rule 68: state field must be a string ──
            state_val = w.get("state")
            if state_val is not None and not isinstance(state_val, str):
                issues.append(Issue("ERROR", f"{wl}: state={state_val!r} must be a string"))

            # ── Rule 69: max_lines must be >= 1 when set ──
            ml = w.get("max_lines")
            if _is_int(ml) and ml == 0:
                issues.append(Issue("WARN", f"{wl}: max_lines=0 effectively hides all text"))

            # ── Rule 70: text_color / bg_color / color must be parseable if set ──
            for alias_key in ("text_color", "bg_color", "color"):
                alias_val = w.get(alias_key)
                if isinstance(alias_val, str) and alias_val.strip():
                    if _parse_color(alias_val) is None:
                        issues.append(Issue("ERROR", f"{wl}: {alias_key}='{alias_val}' is not a valid color"))

            # ── Rule 71: max_lines excessively large ──
            if _is_int(w.get("max_lines")) and w.get("max_lines") > 100:
                issues.append(Issue("WARN", f"{wl}: max_lines={w.get('max_lines')} seems excessive (>100)"))

            # ── Rule 72: text widget with both static text and runtime binding ──
            _tv = w.get("text", "")
            text_val = str(_tv) if isinstance(_tv, str) else ""
            _rv = w.get("runtime", "")
            runtime_val = str(_rv) if isinstance(_rv, str) else ""
            if wt in TEXT_TYPES and text_val.strip() and runtime_val.strip():
                issues.append(Issue("WARN", f"{wl}: has both text='{text_val}' and runtime='{runtime_val}' (runtime may override text)"))

            # ── Rule 73: icon widget too small for icon_char ──
            if wt == "icon" and (ww < CHAR_W or hh < CHAR_H):
                issues.append(Issue("WARN", f"{wl}: icon {ww}x{hh} too small (min {CHAR_W}x{CHAR_H})"))

            # ── Rule 74: padding larger than widget interior ──
            px = w.get("padding_x")
            py = w.get("padding_y")
            if _is_int(px) and px * 2 >= ww:
                issues.append(Issue("WARN", f"{wl}: padding_x={px} fills entire width {ww}"))
            if _is_int(py) and py * 2 >= hh:
                issues.append(Issue("WARN", f"{wl}: padding_y={py} fills entire height {hh}"))

            # ── Rule 75: Chart minimum size ──
            if wt == "chart" and (ww < 20 or hh < 16):
                issues.append(Issue("WARN", f"{wl}: chart {ww}x{hh} too small (min 20x16)"))

            # ── Rule 76: border_width > 0 but border=False ──
            bw_val = w.get("border_width")
            if _is_int(bw_val) and bw_val > 0 and not w.get("border", False):
                issues.append(Issue("WARN", f"{wl}: border_width={bw_val} but border=false"))

            # ── Rule 77: text_overflow on non-text widget ──
            tof = w.get("text_overflow")
            if isinstance(tof, str) and tof.lower() not in {"", "ellipsis"} and wt not in TEXT_TYPES:
                issues.append(Issue("WARN", f"{wl}: text_overflow='{tof}' on non-text type '{wt}'"))

            # ── Rule 78: align on non-text widget ──
            walign = w.get("align")
            if isinstance(walign, str) and walign.lower() not in {"", "left"} and wt not in TEXT_TYPES:
                issues.append(Issue("WARN", f"{wl}: align='{walign}' on non-text type '{wt}'"))

            # ── Rule 79: widget larger than scene ──
            if ww > sw:
                issues.append(Issue("WARN", f"{wl}: width {ww} > scene width {sw}"))
            if hh > sh:
                issues.append(Issue("WARN", f"{wl}: height {hh} > scene height {sh}"))

            # ── Rule 80: margin pushes widget offscreen ──
            mx = w.get("margin_x")
            my = w.get("margin_y")
            if _is_int(mx) and mx > 0 and x + mx >= sw:
                issues.append(Issue("WARN", f"{wl}: margin_x={mx} pushes widget past scene right edge"))
            if _is_int(my) and my > 0 and y + my >= sh:
                issues.append(Issue("WARN", f"{wl}: margin_y={my} pushes widget past scene bottom edge"))

            # ── Rule 81: progressbar with text (not rendered) ──
            if wt == "progressbar" and text.strip():
                issues.append(Issue("WARN", f"{wl}: progressbar text='{text}' is not rendered"))

            # ── Rule 82: value fields on checkbox/radiobutton ──
            if wt in {"checkbox", "radiobutton"}:
                for vf in ("value", "min_value", "max_value"):
                    vv = w.get(vf)
                    if _is_int(vv) and vv != 0:
                        issues.append(Issue("WARN", f"{wl}: {vf}={vv} on {wt} (not a value widget)"))
                        break

            # ── Rule 83: checked on non-checkbox/radiobutton ──
            if wt not in {"checkbox", "radiobutton"} and w.get("checked") is True:
                issues.append(Issue("WARN", f"{wl}: checked=true on non-checkbox/radiobutton '{wt}'"))

            # ── Rule 84: icon_char on non-icon widget ──
            if wt != "icon" and w.get("icon_char", ""):
                issues.append(Issue("WARN", f"{wl}: icon_char set on non-icon widget '{wt}'"))

            # ── Rule 85: max_lines on non-text widget ──
            if wt not in TEXT_TYPES and w.get("max_lines") is not None:
                ml85 = w.get("max_lines")
                if _is_int(ml85) and ml85 > 0:
                    issues.append(Issue("WARN", f"{wl}: max_lines={ml85} on non-text widget '{wt}'"))

            # ── Rule 86: max_lines firmware uint8 overflow ──
            ml86 = w.get("max_lines")
            if _is_int(ml86) and ml86 > 255:
                issues.append(Issue("ERROR", f"{wl}: max_lines={ml86} overflows uint8 (max 255)"))

            # ── Rule 87: padding/margin must be int ──
            for pm_key in ("padding_x", "padding_y", "margin_x", "margin_y"):
                pm_val = w.get(pm_key)
                if pm_val is not None and not _is_int(pm_val):
                    issues.append(Issue("ERROR", f"{wl}: {pm_key}={pm_val!r} must be int"))

            # ── Rule 88: max_lines with non-wrap text_overflow ──
            tof88 = str(w.get("text_overflow", "") or "").lower()
            ml88 = w.get("max_lines")
            if wt in TEXT_TYPES and _is_int(ml88) and ml88 > 1 and tof88 and tof88 not in {"wrap", "auto", "", "ellipsis"}:
                issues.append(Issue("WARN", f"{wl}: max_lines={ml88} but text_overflow='{tof88}' (max_lines may be ignored)"))

            # ── Rule 89: responsive_rules entries structure ──
            rr89 = w.get("responsive_rules")
            if isinstance(rr89, list):
                for ri, entry in enumerate(rr89):
                    if not isinstance(entry, dict):
                        issues.append(Issue("ERROR", f"{wl}: responsive_rules[{ri}] must be a dict"))
                    elif "condition" not in entry:
                        issues.append(Issue("ERROR", f"{wl}: responsive_rules[{ri}] missing 'condition'"))

            # ── Rule 90: chart data_points int16 overflow ──
            if wt == "chart":
                dp90 = w.get("data_points")
                if isinstance(dp90, list):
                    bad90 = [v for v in dp90 if isinstance(v, (int, float)) and not isinstance(v, bool)
                             and (int(v) < INT16_MIN or int(v) > INT16_MAX)]
                    if bad90:
                        issues.append(Issue("ERROR", f"{wl}: data_points values outside int16 range: {bad90[:3]}"))

            # ── Rule 91: text field must be a string ──
            text_raw = w.get("text")
            if text_raw is not None and not isinstance(text_raw, str):
                issues.append(Issue("ERROR", f"{wl}: text={text_raw!r} must be a string"))

            # ── Rule 92: valign on non-text widget ──
            va92 = str(w.get("valign", "") or "").lower()
            if wt not in TEXT_TYPES and va92 and va92 not in {"middle", ""}:
                issues.append(Issue("WARN", f"{wl}: valign='{va92}' on non-text widget '{wt}'"))

            # ── Rule 93: chart-only style on non-chart widget ──
            st93 = str(w.get("style", "") or "").lower()
            if wt != "chart" and st93 in {"bar", "line"}:
                issues.append(Issue("WARN", f"{wl}: style='{st93}' is chart-specific on non-chart '{wt}'"))

            # ── Rule 94: font_size firmware range ──
            fs94 = w.get("font_size")
            if _is_int(fs94) and fs94 > 255:
                issues.append(Issue("ERROR", f"{wl}: font_size={fs94} overflows uint8 (max 255)"))

            # ── Rule 95: runtime field must be a string ──
            rt95 = w.get("runtime")
            if rt95 is not None and not isinstance(rt95, str):
                issues.append(Issue("ERROR", f"{wl}: runtime={rt95!r} must be a string"))

            # ── Rule 96: state_overrides keys must be valid state names ──
            so96 = w.get("state_overrides")
            if isinstance(so96, dict):
                for sk in so96:
                    if not isinstance(sk, str) or not sk.strip():
                        issues.append(Issue("ERROR", f"{wl}: state_overrides key {sk!r} must be a non-empty string"))

            # ── Rule 97: cross-scene duplicate widget IDs ──
            # (computed after all scenes processed — deferred below)

            # ── Rule 98: corner_radius exceeds half of min dimension ──
            cr98 = w.get("corner_radius")
            if _is_int(cr98) and cr98 > 0:
                half_min = min(ww, hh) // 2
                if cr98 > half_min:
                    issues.append(Issue("WARN", f"{wl}: corner_radius={cr98} exceeds half of min dimension ({half_min})"))

            # ── Rule 99: border_width firmware uint8 overflow ──
            bw99 = w.get("border_width")
            if _is_int(bw99) and bw99 > 255:
                issues.append(Issue("ERROR", f"{wl}: border_width={bw99} overflows uint8 (max 255)"))

            # ── Rule 100: corner_radius firmware uint8 overflow ──
            cr100 = w.get("corner_radius")
            if _is_int(cr100) and cr100 > 255:
                issues.append(Issue("ERROR", f"{wl}: corner_radius={cr100} overflows uint8 (max 255)"))

            # ── Rule 101: chart data_points count limit ──
            if wt == "chart":
                dp101 = w.get("data_points")
                if isinstance(dp101, list) and len(dp101) > 128:
                    issues.append(Issue("WARN", f"{wl}: data_points has {len(dp101)} entries (>128, sub-pixel on 256px display)"))

            # ── Rule 102: empty runtime binding value ──
            _rv102 = w.get("runtime", "")
            rt102 = str(_rv102) if isinstance(_rv102, str) else ""
            if rt102:
                for part102 in rt102.split(";"):
                    part102 = part102.strip()
                    if not part102:
                        continue
                    if "=" in part102:
                        _key102, val102 = part102.split("=", 1)
                        if not val102.strip():
                            issues.append(Issue("WARN", f"{wl}: runtime '{part102}' has empty value after '='"))

            # ── Rule 103: chart with no data and no runtime ──
            if wt == "chart":
                dp103 = w.get("data_points")
                _rv103 = w.get("runtime", "")
                rt103 = str(_rv103) if isinstance(_rv103, str) else ""
                if (dp103 is None or (isinstance(dp103, list) and len(dp103) == 0)) and not rt103:
                    issues.append(Issue("WARN", f"{wl}: chart has no data_points and no runtime binding"))

            # ── Rule 104: animations list contains empty strings ──
            if "animations" in w:
                anim104 = w.get("animations")
                if isinstance(anim104, list):
                    empty_ct = sum(1 for a in anim104 if isinstance(a, str) and not a.strip())
                    if empty_ct:
                        issues.append(Issue("WARN", f"{wl}: animations contains {empty_ct} empty string(s)"))

            # ── Rule 107: text_overflow=wrap with max_lines=1 ──
            ov107 = str(w.get("text_overflow", "") or "").lower()
            ml107 = w.get("max_lines")
            if ov107 == "wrap" and _is_int(ml107) and ml107 == 1:
                issues.append(Issue("WARN", f"{wl}: text_overflow='wrap' with max_lines=1 (wrap can never produce a second line)"))

            # ── Rule 108: slider with height > width ──
            if wt == "slider" and hh > ww:
                issues.append(Issue("WARN", f"{wl}: slider height({hh}) > width({ww}); firmware renders horizontal track"))

            # ── Rule 109: disabled+checked toggle without runtime ──
            if wt in ("checkbox", "radiobutton"):
                r109_en = w.get("enabled")
                r109_chk = w.get("checked")
                _rv109 = w.get("runtime", "")
                rt109 = str(_rv109) if isinstance(_rv109, str) else ""
                if r109_en is False and r109_chk is True and not rt109:
                    issues.append(Issue("WARN", f"{wl}: disabled checked={r109_chk} {wt} with no runtime (stuck state)"))

            # ── Rule 110: widget ID structural issues (.., trailing .- ) ──
            wid110 = w.get("_widget_id") or w.get("id")
            if isinstance(wid110, str) and wid110:
                if ".." in wid110 or wid110.endswith(".") or wid110.endswith("-"):
                    issues.append(Issue("ERROR", f"{wl}: id '{wid110}' has structural issue (consecutive dots, trailing dot/hyphen)"))

            # ── Rule 111: border=false but border_style not none/empty ──
            r111_border = w.get("border")
            r111_bs = str(w.get("border_style", "") or "").lower()
            if r111_border is False and r111_bs and r111_bs not in {"none", "", "single"}:
                issues.append(Issue("WARN", f"{wl}: border=false but border_style='{r111_bs}' (style is ignored)"))

            # ── Rule 112: both visible=false and enabled=false ──
            if w.get("visible") is False and w.get("enabled") is False:
                issues.append(Issue("WARN", f"{wl}: both visible=false and enabled=false (redundant)"))

            # ── Rule 113: text_overflow=wrap but too short for 2 lines ──
            ov113 = str(w.get("text_overflow", "") or "").lower()
            if ov113 == "wrap" and hh < RENDER_PAD * 2 + CHAR_H * 2:
                issues.append(Issue("WARN", f"{wl}: text_overflow='wrap' but height={hh} too short for 2 lines (need {RENDER_PAD * 2 + CHAR_H * 2})"))

            # ── Rule 114: align center/right on checkbox/radiobutton ──
            if wt in ("checkbox", "radiobutton"):
                al114 = str(w.get("align", "") or "").lower()
                if al114 in ("center", "right"):
                    issues.append(Issue("WARN", f"{wl}: align='{al114}' on {wt} (indicator is fixed left-edge)"))

            # ── Rule 116: chart min_value >= max_value ──
            if wt == "chart":
                r116_min = w.get("min_value", 0)
                r116_max = w.get("max_value", 100)
                if _is_int(r116_min) and _is_int(r116_max) and r116_min >= r116_max:
                    issues.append(Issue("ERROR", f"{wl}: chart min_value={r116_min} >= max_value={r116_max}"))

            # ── Rule 117: progressbar height too small for visible fill ──
            if wt == "progressbar" and hh <= 2:
                issues.append(Issue("WARN", f"{wl}: progressbar height={hh} too small for visible fill (need >2)"))

            # ── Rule 118: constraints dict unrecognized keys ──
            r118_con = w.get("constraints")
            if isinstance(r118_con, dict) and r118_con:
                r118_bad = sorted(set(r118_con.keys()) - ALLOWED_CONSTRAINT_KEYS)
                if r118_bad:
                    issues.append(Issue("WARN", f"{wl}: constraints has unrecognized keys: {r118_bad}"))

            # ── Rule 119: icon widget too small for bitmap rendering ──
            if wt == "icon" and w.get("icon_char"):
                if ww < 20 or hh < 20:
                    issues.append(Issue("WARN", f"{wl}: icon {ww}x{hh} too small for bitmap (min 20x20 with border)"))

            # ── Rule 120: checkbox/radiobutton too narrow for label text ──
            if wt in ("checkbox", "radiobutton") and text and ww < 16:
                issues.append(Issue("WARN", f"{wl}: {wt} width={ww} too narrow for label text (min 16)"))

            # ── Rule 121: value/chart widget has text but height < CHAR_H ──
            if wt in ("gauge", "progressbar", "slider", "chart") and text and hh < CHAR_H:
                issues.append(Issue("WARN", f"{wl}: {wt} height={hh} too short to render text (need >={CHAR_H})"))

            # ── Rule 122: runtime meta key validation ──
            if runtime:
                for r122_part in runtime.split(";"):
                    r122_part = r122_part.strip()
                    if not r122_part or "=" not in r122_part:
                        continue
                    r122_key = r122_part.split("=", 1)[0].strip().lower()
                    if r122_key and r122_key not in ALLOWED_RUNTIME_META_KEYS:
                        issues.append(Issue("WARN", f"{wl}: runtime key '{r122_key}' is not a recognized meta key"))

            # ── Rule 106: scene dimensions too small ──
            # (checked once per scene, outside per-widget loop — see below)

        # ── Rule 115: scene has no focusable widgets ──
        has_focusable = False
        for r115_w in widgets:
            if not isinstance(r115_w, dict):
                continue
            r115_t = str(r115_w.get("type", "") or "").lower()
            if r115_t in FOCUSABLE_TYPES and r115_w.get("visible") is not False and r115_w.get("enabled") is not False:
                has_focusable = True
                break
        if not has_focusable and len(widgets) > 0:
            issues.append(Issue("WARN", f"{pfx}: scene has no focusable widgets (navigation dead-end)"))

        # ── Rule 105: overlapping widgets with identical z_index ──
        for i in range(len(widgets)):
            a = widgets[i]
            if not isinstance(a, dict):
                continue
            ax, ay = a.get("x", 0), a.get("y", 0)
            aw, ah = a.get("width", 0), a.get("height", 0)
            az = a.get("z_index", 0)
            if not (_is_int(ax) and _is_int(ay) and _is_int(aw) and _is_int(ah)):
                continue
            ax2, ay2 = ax + aw, ay + ah
            for j in range(i + 1, len(widgets)):
                b = widgets[j]
                if not isinstance(b, dict):
                    continue
                bx, by = b.get("x", 0), b.get("y", 0)
                bw, bh = b.get("width", 0), b.get("height", 0)
                bz = b.get("z_index", 0)
                if not (_is_int(bx) and _is_int(by) and _is_int(bw) and _is_int(bh)):
                    continue
                bx2, by2 = bx + bw, by + bh
                if ax < bx2 and ax2 > bx and ay < by2 and ay2 > by:
                    if _is_int(az) and _is_int(bz) and az == bz:
                        ref_a = _wref(scene_name, a, i)
                        ref_b = _wref(scene_name, b, j)
                        issues.append(Issue("WARN", f"{pfx}: OVERLAP with same z_index={az}: {ref_a} <> {ref_b}"))

        # ── Rule 106: scene dimensions too small ──
        if sw < 8 or sh < 8:
            issues.append(Issue("WARN", f"{pfx}: scene dimensions {sw}x{sh} too small (min 8x8)"))

        # ── Rule 65: Duplicate geometry (same x,y,w,h = likely copy-paste) ──
        geo_map: dict[tuple[int, int, int, int], list[int]] = {}
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            gx, gy, gw, gh = w.get("x"), w.get("y"), w.get("width"), w.get("height")
            if _is_int(gx) and _is_int(gy) and _is_int(gw) and _is_int(gh):
                key = (int(gx), int(gy), int(gw), int(gh))
                geo_map.setdefault(key, []).append(idx)
        for geo, indices in geo_map.items():
            if len(indices) >= 2:
                refs = ", ".join(str(i) for i in indices)
                issues.append(Issue("WARN", f"{pfx}: widgets [{refs}] share identical geometry {geo}"))

        # ── Rule 66: Disabled widget with no runtime (may be unreachable) ──
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            if w.get("enabled") is False and w.get("visible") is not False:
                _rv66 = w.get("runtime", "")
                runtime_val = str(_rv66) if isinstance(_rv66, str) else ""
                if not runtime_val:
                    ref = _wref(scene_name, w, idx)
                    wl = f"{pfx}: {ref}"
                    issues.append(Issue("WARN", f"{wl}: disabled (enabled=false) with no runtime binding"))

        # ── Rule 49: Large number of identical non-empty text strings ──
        text_counts: dict[str, int] = {}
        for w in widgets:
            if not isinstance(w, dict):
                continue
            _t49 = w.get("text", "")
            t = str(_t49) if isinstance(_t49, str) else ""
            if t and len(t) > 3:
                text_counts[t] = text_counts.get(t, 0) + 1
        for t, count in text_counts.items():
            if count >= 4:
                issues.append(Issue("WARN", f"{pfx}: text '{t}' appears {count} times (consider runtime binding)"))

        # ── Rule 33: Excessive widget count per scene ──
        if len(widgets) > MAX_WIDGETS_PER_SCENE:
            issues.append(Issue("WARN", f"{pfx}: {len(widgets)} widgets exceeds recommended max {MAX_WIDGETS_PER_SCENE}"))

        # ── Rule 21: Overlap detection ──
        for i in range(len(widgets)):
            a = widgets[i]
            if not isinstance(a, dict):
                continue
            ax, ay = a.get("x", 0), a.get("y", 0)
            aw, ah = a.get("width", 0), a.get("height", 0)
            if not (_is_int(ax) and _is_int(ay) and _is_int(aw) and _is_int(ah)):
                continue
            ax2, ay2 = ax + aw, ay + ah
            for j in range(i + 1, len(widgets)):
                b = widgets[j]
                if not isinstance(b, dict):
                    continue
                bx, by = b.get("x", 0), b.get("y", 0)
                bw, bh = b.get("width", 0), b.get("height", 0)
                if not (_is_int(bx) and _is_int(by) and _is_int(bw) and _is_int(bh)):
                    continue
                bx2, by2 = bx + bw, by + bh
                if ax < bx2 and ax2 > bx and ay < by2 and ay2 > by:
                    ref_a = _wref(scene_name, a, i)
                    ref_b = _wref(scene_name, b, j)
                    issues.append(Issue("WARN", f"{pfx}: OVERLAP {ref_a} <> {ref_b}"))

    # ── Rule 97: Cross-scene duplicate widget IDs ──
    global_ids: dict[str, str] = {}  # id → first scene name
    for scene_name, scene in scenes.items():
        widgets = scene.get("widgets") or []
        for w in widgets:
            if not isinstance(w, dict):
                continue
            wid = w.get("_widget_id") or w.get("id")
            if not isinstance(wid, str) or not wid:
                continue
            if wid in global_ids and global_ids[wid] != scene_name:
                issues.append(
                    Issue("WARN", f"{file_label}: widget id '{wid}' appears in both '{global_ids[wid]}' and '{scene_name}'")
                )
            else:
                global_ids[wid] = scene_name

    if warnings_as_errors:
        return [Issue("ERROR", i.message) if i.level == "WARN" else i for i in issues]
    if strict_critical:
        return [Issue("ERROR", i.message) if i.level == "WARN" and _is_critical_warning(i.message) else i for i in issues]
    return issues


def validate_file(path: Path, *, warnings_as_errors: bool, strict_critical: bool = False) -> list[Issue]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [Issue("ERROR", f"{path}: failed to parse JSON ({exc})")]
    if not isinstance(data, dict):
        return [Issue("ERROR", f"{path}: root must be a JSON object")]
    return validate_data(
        data,
        file_label=str(path),
        warnings_as_errors=warnings_as_errors,
        strict_critical=strict_critical,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Validate ESP32OS UI design JSON")
    p.add_argument("json", type=Path, help="Input design JSON")
    p.add_argument("--warnings-as-errors", action="store_true", help="Treat warnings as errors")
    p.add_argument(
        "--strict-critical",
        action="store_true",
        help="Treat critical layout/readability warnings as errors",
    )
    args = p.parse_args()

    issues = validate_file(
        args.json,
        warnings_as_errors=args.warnings_as_errors,
        strict_critical=args.strict_critical,
    )
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

