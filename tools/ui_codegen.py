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
    "list": "UIW_LIST",
    "toggle": "UIW_TOGGLE",
}

_BORDER_STYLE_MAP: dict[str, str] = {
    "none": "UI_BORDER_NONE",
    "single": "UI_BORDER_SINGLE",
    "double": "UI_BORDER_DOUBLE",
    "rounded": "UI_BORDER_ROUNDED",
    "bold": "UI_BORDER_BOLD",
    "dashed": "UI_BORDER_DASHED",
}

_ALIGN_MAP: dict[str, str] = {
    "left": "UI_ALIGN_LEFT",
    "center": "UI_ALIGN_CENTER",
    "right": "UI_ALIGN_RIGHT",
}
_VALIGN_MAP: dict[str, str] = {
    "top": "UI_VALIGN_TOP",
    "middle": "UI_VALIGN_MIDDLE",
    "bottom": "UI_VALIGN_BOTTOM",
}
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


import re as _re


def escape_c_string(text: object) -> str:
    s = (
        str(text or "")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return _re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
        lambda m: f"\\x{ord(m.group()):02x}",
        s,
    )


def escape_c_comment(text: object) -> str:
    """Escape text for safe inclusion inside a C block comment."""
    s = (
        str(text or "")
        .replace("*/", "* /")
        .replace("/*", "/ *")
        .replace("\n", " ")
        .replace("\r", " ")
    )
    return _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)


def as_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return int(default)


def _clamp(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def as_uint16(v: object, default: int = 0) -> int:
    return _clamp(as_int(v, default), 0, 65535)


def as_int16(v: object, default: int = 0) -> int:
    return _clamp(as_int(v, default), -32768, 32767)


def as_uint8(v: object, default: int = 0) -> int:
    return _clamp(as_int(v, default), 0, 255)


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
    except ValueError:
        return (255, 255, 255)


def _get_rgb(name_or_hex: object) -> tuple[int, int, int]:
    s = str(name_or_hex or "").strip()
    if s.startswith("#"):
        return _hex_to_rgb(s)
    return _COLOR_MAP.get(s.lower(), (255, 255, 255))


def _rgb_to_gray4(r: int, g: int, b: int) -> int:
    try:
        y = 0.2126 * float(r) + 0.7152 * float(g) + 0.0722 * float(b)
    except (TypeError, ValueError):
        y = 255.0
    v = round((y / 255.0) * 15.0)
    return max(0, min(15, v))


def parse_gray4(name_or_hex: object, *, default: int) -> int:
    s = str(name_or_hex or "").strip()
    if not s:
        return int(default)
    try:
        r, g, b = _get_rgb(s)
        return _rgb_to_gray4(r, g, b)
    except (TypeError, ValueError):
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


_DATA_POINTS_MAX = 128  # mirrors validate_design.py Rule 101 (sub-pixel beyond 128)


def chart_data_points(widget: dict[str, Any]) -> list[int]:
    """Return the chart series clamped to int16 and capped at _DATA_POINTS_MAX.

    Only meaningful for chart widgets; callers gate on widget type. Non-numeric
    or boolean entries are skipped so generated C always compiles.
    """
    raw = widget.get("data_points")
    if not isinstance(raw, list) or not raw:
        return []
    out: list[int] = []
    for v in raw:
        if isinstance(v, bool):
            continue
        if not isinstance(v, (int, float)):
            continue
        out.append(_clamp(int(v), -32768, 32767))
        if len(out) >= _DATA_POINTS_MAX:
            break
    return out


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
    # For list widgets: join items into newline-separated text
    raw_items = widget.get("items") or widget.get("list_items")
    if isinstance(raw_items, list) and raw_items and not text:
        text = "\n".join(str(s) for s in raw_items)
    constraints = str(widget.get("constraints_json", "") or widget.get("runtime", "") or "")
    anim_csv = str(widget.get("animations_csv", "") or "")
    if not anim_csv:
        anims = widget.get("animations")
        if isinstance(anims, list) and anims:
            anim_csv = ";".join([str(x) for x in anims])
    icon_char = str(widget.get("icon_char", "") or "")
    out: list[str] = []
    for s in (widget_id, text, constraints, anim_csv, icon_char):
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
    return _VALIGN_MAP.get(
        str(widget.get("valign", "middle") or "middle").lower(), "UI_VALIGN_MIDDLE"
    )


def overflow_for(widget: dict[str, Any]) -> str:
    return _OVERFLOW_MAP.get(
        str(widget.get("text_overflow", "ellipsis") or "ellipsis").lower(),
        "UI_TEXT_OVERFLOW_ELLIPSIS",
    )


def write_if_changed(path: Path, content: str) -> bool:
    try:
        existing = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        existing = None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")  # type: ignore[call-arg]
    return True


def _widgets_in_paint_order(widgets: list[Any]) -> list[Any]:
    """Stable-sort widgets by ``z_index`` so generated C matches the designer's
    paint order (equal z_index keeps authoring order). Non-dict entries sort as
    z_index 0 and are skipped later by the emitters. Mirrors the ordering the
    multi-scene header path already applies.
    """
    ordered = list(widgets)
    try:
        ordered.sort(
            key=lambda ww: as_int(ww.get("z_index", 0), 0) if isinstance(ww, dict) else 0
        )
    except (TypeError, ValueError, AttributeError):
        return list(widgets)
    return ordered


def build_data_point_arrays(
    widgets: list[Any], *, symbol_prefix: str
) -> tuple[list[str], dict[int, str]]:
    """Emit per-chart ``static const int16_t`` data arrays.

    Returns ``(decls, by_id)`` where ``by_id`` maps ``id(widget_dict)`` to the
    C symbol of its array. Arrays are emitted in widget order so the generated
    C is deterministic. Charts without numeric data produce no array (the
    widget keeps ``data_points = NULL``).
    """
    decls: list[str] = []
    by_id: dict[int, str] = {}
    seq = 0
    for w in widgets:
        if not isinstance(w, dict):
            continue
        if str(w.get("type", "")).lower() != "chart":
            continue
        pts = chart_data_points(w)
        if not pts:
            continue
        name = f"{symbol_prefix}{seq}"
        seq += 1
        by_id[id(w)] = name
        decls.append(
            f"static const int16_t {name}[] = {{ {', '.join(str(v) for v in pts)} }};"
        )
    return decls, by_id


# --------------------------------------------------------------------------- #
# Visual-backend logic (events / rules) -> deterministic C
#
# The designer stores per-widget `events` ({on_press|on_change|on_focus:[..]})
# and per-scene `rules` ([{trigger, conditions?, actions}, ...]). These are
# compiled into the flat PODs declared in src/ui_logic.h and executed by the
# firmware logic service. Every action type emits real, working C — there is
# no inert/TODO path.
# --------------------------------------------------------------------------- #

_TRIG_MAP = {
    "boot": "UI_TRIG_BOOT",
    "timer": "UI_TRIG_TIMER",
    "gpio_in": "UI_TRIG_GPIO_IN",
    "ble_recv": "UI_TRIG_BLE_RECV",
    "lora_recv": "UI_TRIG_LORA_RECV",
    "widget": "UI_TRIG_WIDGET",
}
_WEV_MAP = {
    "on_press": "UI_WEV_PRESS",
    "on_change": "UI_WEV_CHANGE",
    "on_focus": "UI_WEV_FOCUS",
}
_EDGE_MAP = {"any": "UI_EDGE_ANY", "rising": "UI_EDGE_RISING", "falling": "UI_EDGE_FALLING"}
_ACT_MAP = {
    "set_scene": "UI_ACT_SET_SCENE",
    "set_widget": "UI_ACT_SET_WIDGET",
    "set_var": "UI_ACT_SET_VAR",
    "gpio_write": "UI_ACT_GPIO_WRITE",
    "toast": "UI_ACT_TOAST",
    "start_timer": "UI_ACT_START_TIMER",
    "stop_timer": "UI_ACT_STOP_TIMER",
    "ble_send": "UI_ACT_BLE_SEND",
    "lora_send": "UI_ACT_LORA_SEND",
}
_PROP_MAP = {
    "value": "UI_PROP_VALUE",
    "text": "UI_PROP_TEXT",
    "checked": "UI_PROP_CHECKED",
    "visible": "UI_PROP_VISIBLE",
    "enabled": "UI_PROP_ENABLED",
}
_CMP_MAP = {
    "==": "UI_CMP_EQ",
    "!=": "UI_CMP_NE",
    "<": "UI_CMP_LT",
    ">": "UI_CMP_GT",
    "<=": "UI_CMP_LE",
    ">=": "UI_CMP_GE",
}
_JOIN_MAP = {"&&": "UI_JOIN_AND", "||": "UI_JOIN_OR"}
_ARITH_MAP = {"+": 0, "-": 1, "*": 2, "/": 3}
_LOGIC_MAX_VARS = 32  # mirrors UI_LOGIC_MAX_VARS in services/logic/logic.c


class LogicCodegenError(ValueError):
    """Raised on a structurally invalid event/rule (defensive; the validator
    is the primary gate but codegen must never emit broken C)."""


def _logic_collect_strings(scenes: dict[str, Any]) -> list[str]:
    """Every string literal referenced by events/rules (widget ids, toast
    text, payloads, rule names) so they share the design string pool."""
    out: list[str] = []

    def _from_actions(actions: Any) -> None:
        # Only collect strings that _emit_action actually emits as C
        # ``const char *`` refs. ``scene`` resolves to a scene *index* and
        # ``var``/``expr`` names resolve to integer *var indices* — pooling
        # them would create unreferenced statics (-Werror=unused-const).
        if not isinstance(actions, list):
            return
        for a in actions:
            if not isinstance(a, dict):
                continue
            t = str(a.get("type", "")).strip().lower()
            if t == "set_widget":
                wid = a.get("widget")
                if isinstance(wid, str) and wid:
                    out.append(wid)
                if str(a.get("prop", "value") or "value").lower() == "text":
                    txt = a.get("text", a.get("value", ""))
                    if isinstance(txt, str) and txt:
                        out.append(txt)
            elif t == "toast":
                v = a.get("text")
                if isinstance(v, str) and v:
                    out.append(v)
            elif t in ("ble_send", "lora_send"):
                v = a.get("bytes")
                if isinstance(v, str) and v:
                    out.append(v)
            # set_scene (scene->index) and set_var (var/expr->index) emit NO
            # string refs — intentionally not pooled.

    def _from_operand(ref: Any) -> None:
        if isinstance(ref, str) and ref.startswith("widget:"):
            wid = ref[len("widget:") :].split(".", 1)[0]
            if wid:
                out.append(wid)

    for _name, scene in scenes.items():
        for w in list(scene.get("widgets", []) or []):
            if not isinstance(w, dict):
                continue
            ev = w.get("events")
            if isinstance(ev, dict):
                for key in ("on_press", "on_change", "on_focus"):
                    _from_actions(ev.get(key))
        for r in list(scene.get("rules", []) or []):
            if not isinstance(r, dict):
                continue
            nm = r.get("name")
            if isinstance(nm, str) and nm:
                out.append(nm)
            trig = r.get("trigger") or {}
            if isinstance(trig, dict):
                wid = trig.get("widget")
                if isinstance(wid, str) and wid:
                    out.append(wid)
            for cond in list(r.get("conditions", []) or []):
                if isinstance(cond, dict):
                    _from_operand(cond.get("lhs"))
                    _from_operand(cond.get("rhs"))
            _from_actions(r.get("actions"))
    return out


def _scene_index_map(scene_keys: list[str]) -> dict[str, int]:
    return {k: i for i, k in enumerate(scene_keys)}


class _VarTable:
    """Stable name -> index allocator for integer logic variables."""

    def __init__(self) -> None:
        self.order: list[str] = []
        self.index: dict[str, int] = {}

    def intern(self, name: str) -> int:
        name = str(name or "").strip()
        if not name:
            raise LogicCodegenError("empty variable name")
        if name not in self.index:
            if len(self.order) >= _LOGIC_MAX_VARS:
                raise LogicCodegenError(
                    f"too many logic variables (max {_LOGIC_MAX_VARS}): {name!r}"
                )
            self.index[name] = len(self.order)
            self.order.append(name)
        return self.index[name]


def _str_ref(pool: StringPool, s: str) -> str:
    ref = pool.mapping.get(s, "") if s else ""
    return ref if ref else "NULL"


_TOKEN_RE = _re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*|-?\d+|[+\-*/])\s*")


def _emit_operand_from_token(tok: str, vt: _VarTable) -> str:
    """A bare set_var term: integer literal or a variable name."""
    if _re.fullmatch(r"-?\d+", tok):
        return f"{{ .kind = UI_OPND_LITERAL, .value = {int(tok)}, .s0 = NULL }}"
    vi = vt.intern(tok)
    return f"{{ .kind = UI_OPND_VAR, .value = {vi}, .s0 = NULL }}"


def _emit_operand_ref(ref: Any, vt: _VarTable, pool: StringPool) -> str:
    """A condition operand: int literal, 'var:<n>', or 'widget:<id>.value|checked'."""
    if isinstance(ref, bool):
        raise LogicCodegenError("boolean operand not allowed; use 0/1")
    if isinstance(ref, int):
        return f"{{ .kind = UI_OPND_LITERAL, .value = {int(ref)}, .s0 = NULL }}"
    s = str(ref or "").strip()
    if _re.fullmatch(r"-?\d+", s):
        return f"{{ .kind = UI_OPND_LITERAL, .value = {int(s)}, .s0 = NULL }}"
    if s.startswith("var:"):
        vi = vt.intern(s[len("var:") :])
        return f"{{ .kind = UI_OPND_VAR, .value = {vi}, .s0 = NULL }}"
    if s.startswith("widget:"):
        body = s[len("widget:") :]
        wid, _, attr = body.partition(".")
        wid = wid.strip()
        attr = (attr or "value").strip().lower()
        if not wid:
            raise LogicCodegenError(f"widget operand missing id: {s!r}")
        kind = "UI_OPND_WIDGET_CHECKED" if attr == "checked" else "UI_OPND_WIDGET_VALUE"
        return f"{{ .kind = {kind}, .value = 0, .s0 = {_str_ref(pool, wid)} }}"
    raise LogicCodegenError(f"unparseable operand: {ref!r}")


def _emit_expr(expr: Any, vt: _VarTable) -> str:
    """Compile a bounded set_var expression into a UiLogicExpr initializer.

    Accepts a single optional binary op: ``A``, ``A + B`` (+,-,*,/). A and B
    are integer literals or variable names. This is intentionally bounded but
    fully real (the executor evaluates it)."""
    s = str(expr or "").strip()
    if not s:
        raise LogicCodegenError("set_var requires a non-empty expr")
    toks: list[str] = []
    pos = 0
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            raise LogicCodegenError(f"bad token in expr {s!r} at {s[pos:]!r}")
        toks.append(m.group(1))
        pos = m.end()
    if len(toks) == 1:
        lhs = _emit_operand_from_token(toks[0], vt)
        return (
            f"{{ .lhs = {lhs}, .arith = 0, .has_rhs = 0, "
            f".rhs = {{ .kind = UI_OPND_LITERAL, .value = 0, .s0 = NULL }} }}"
        )
    if len(toks) == 3 and toks[1] in _ARITH_MAP:
        lhs = _emit_operand_from_token(toks[0], vt)
        rhs = _emit_operand_from_token(toks[2], vt)
        return (
            f"{{ .lhs = {lhs}, .arith = {_ARITH_MAP[toks[1]]}, "
            f".has_rhs = 1, .rhs = {rhs} }}"
        )
    raise LogicCodegenError(
        f"expr {s!r} too complex (only 'A' or 'A op B' with +,-,*,/ supported)"
    )


_EMPTY_EXPR = (
    "{ .lhs = { .kind = UI_OPND_LITERAL, .value = 0, .s0 = NULL }, "
    ".arith = 0, .has_rhs = 0, "
    ".rhs = { .kind = UI_OPND_LITERAL, .value = 0, .s0 = NULL } }"
)


def _emit_action(
    a: dict[str, Any],
    scene_idx: dict[str, int],
    vt: _VarTable,
    pool: StringPool,
) -> str:
    t = str(a.get("type", "")).strip().lower()
    if t not in _ACT_MAP:
        raise LogicCodegenError(f"unknown action type {t!r}")
    sym = _ACT_MAP[t]
    i0, i1, prop, s0, s1, expr = 0, 0, "UI_PROP_VALUE", "NULL", "NULL", _EMPTY_EXPR

    if t == "set_scene":
        target = str(a.get("scene", "") or "")
        if target not in scene_idx:
            raise LogicCodegenError(f"set_scene -> unknown scene {target!r}")
        i0 = scene_idx[target]
    elif t == "set_widget":
        wid = str(a.get("widget", "") or "")
        if not wid:
            raise LogicCodegenError("set_widget requires 'widget'")
        s0 = _str_ref(pool, wid)
        prop_name = str(a.get("prop", "value") or "value").lower()
        if prop_name not in _PROP_MAP:
            raise LogicCodegenError(f"set_widget bad prop {prop_name!r}")
        prop = _PROP_MAP[prop_name]
        if prop_name == "text":
            s1 = _str_ref(pool, str(a.get("text", a.get("value", "")) or ""))
        else:
            v = a.get("value", 0)
            i0 = (1 if v else 0) if isinstance(v, bool) else as_int(v, 0)
    elif t == "set_var":
        i0 = vt.intern(str(a.get("var", "") or ""))
        expr = _emit_expr(a.get("expr", ""), vt)
    elif t == "gpio_write":
        i0 = as_int(a.get("pin", 0), 0)
        i1 = 1 if as_int(a.get("level", 0), 0) else 0
    elif t == "toast":
        s0 = _str_ref(pool, str(a.get("text", "") or ""))
    elif t == "start_timer":
        i0 = as_int(a.get("timer_id", 0), 0)
        i1 = as_int(a.get("ms", 1000), 1000)
        if i1 < 1:
            i1 = 1
    elif t == "stop_timer":
        i0 = as_int(a.get("timer_id", 0), 0)
    elif t in ("ble_send", "lora_send"):
        s0 = _str_ref(pool, str(a.get("bytes", "") or ""))

    return (
        f"{{ .type = {sym}, .i0 = {i0}, .i1 = {i1}, .prop = {prop}, "
        f".s0 = {s0}, .s1 = {s1}, .expr = {expr} }}"
    )


def _emit_cond(c: dict[str, Any], vt: _VarTable, pool: StringPool) -> str:
    op = str(c.get("op", "==")).strip()
    if op not in _CMP_MAP:
        raise LogicCodegenError(f"bad condition op {op!r}")
    lhs = _emit_operand_ref(c.get("lhs"), vt, pool)
    rhs = _emit_operand_ref(c.get("rhs"), vt, pool)
    join = _JOIN_MAP.get(str(c.get("join", "&&")).strip(), "UI_JOIN_AND")
    return (
        f"{{ .lhs = {lhs}, .op = {_CMP_MAP[op]}, .rhs = {rhs}, .join = {join} }}"
    )


def build_logic_tables(
    scenes: dict[str, Any],
    scene_keys: list[str],
    pool: StringPool,
    *,
    symbol_prefix: str,
) -> tuple[list[str], list[str], int]:
    """Compile every scene's events+rules into flat C tables.

    Returns ``(c_decls, h_lines, var_count)``. ``c_decls`` defines the action
    /cond/rule arrays + ``ui_logic_programs[]`` (index-aligned with
    ``ui_scenes[]``). ``h_lines`` exports it. Deterministic ordering: scene
    order, then rule order, then action order.
    """
    scene_idx = _scene_index_map(scene_keys)
    vt = _VarTable()
    c: list[str] = []
    prog_inits: list[str] = []

    for s_i, key in enumerate(scene_keys):
        scene = scenes.get(key, {})
        safe = sanitize_ident(key)
        rules_out: list[str] = []  # per-rule UiLogicRule initializer text

        # Synthesize widget-event rules first (deterministic: widget order,
        # then on_press/on_change/on_focus), then explicit scene rules.
        synth: list[dict[str, Any]] = []
        for w in list(scene.get("widgets", []) or []):
            if not isinstance(w, dict):
                continue
            wid = str(w.get("_widget_id") or w.get("id") or "")
            ev = w.get("events")
            if not wid or not isinstance(ev, dict):
                continue
            for ek in ("on_press", "on_change", "on_focus"):
                acts = ev.get(ek)
                if isinstance(acts, list) and acts:
                    synth.append(
                        {
                            "name": f"{wid}.{ek}",
                            "trigger": {"type": "widget", "widget": wid, "event": ek},
                            "actions": acts,
                        }
                    )
        explicit = [r for r in list(scene.get("rules", []) or []) if isinstance(r, dict)]
        all_rules = synth + explicit

        for r_i, rule in enumerate(all_rules):
            trig = rule.get("trigger") or {}
            if not isinstance(trig, dict):
                raise LogicCodegenError(f"{key}: rule {r_i} missing trigger")
            ttype = str(trig.get("type", "")).strip().lower()
            if ttype not in _TRIG_MAP:
                raise LogicCodegenError(f"{key}: rule {r_i} bad trigger {ttype!r}")
            trig_i0 = 0
            trig_edge = "UI_EDGE_ANY"
            trig_s0 = "NULL"
            trig_wev = "UI_WEV_PRESS"
            if ttype == "timer":
                trig_i0 = as_int(trig.get("timer_id", 0), 0)
            elif ttype == "gpio_in":
                trig_i0 = as_int(trig.get("pin", 0), 0)
                trig_edge = _EDGE_MAP.get(
                    str(trig.get("edge", "any")).strip().lower(), "UI_EDGE_ANY"
                )
            elif ttype == "widget":
                wid = str(trig.get("widget", "") or "")
                if not wid:
                    raise LogicCodegenError(f"{key}: rule {r_i} widget trigger needs id")
                trig_s0 = _str_ref(pool, wid)
                trig_wev = _WEV_MAP.get(
                    str(trig.get("event", "on_press")).strip().lower(), "UI_WEV_PRESS"
                )

            conds = [
                c2 for c2 in list(rule.get("conditions", []) or []) if isinstance(c2, dict)
            ]
            acts = [
                a for a in list(rule.get("actions", []) or []) if isinstance(a, dict)
            ]
            if not acts:
                raise LogicCodegenError(f"{key}: rule {r_i} has no actions")

            cond_sym = "NULL"
            if conds:
                cond_sym = f"{symbol_prefix}{safe}_r{r_i}_conds"
                c.append(f"static const UiLogicCond {cond_sym}[] = {{")
                for cc in conds:
                    c.append("    " + _emit_cond(cc, vt, pool) + ",")
                c.append("};")
            act_sym = f"{symbol_prefix}{safe}_r{r_i}_acts"
            c.append(f"static const UiLogicAction {act_sym}[] = {{")
            for aa in acts:
                c.append("    " + _emit_action(aa, scene_idx, vt, pool) + ",")
            c.append("};")

            name_ref = _str_ref(pool, str(rule.get("name", "") or ""))
            rules_out.append(
                f"    {{ .trig = {_TRIG_MAP[ttype]}, .trig_i0 = {trig_i0}, "
                f".trig_edge = {trig_edge}, .trig_s0 = {trig_s0}, "
                f".trig_wev = {trig_wev}, .name = {name_ref}, "
                f".conds = {cond_sym if cond_sym != 'NULL' else 'NULL'}, "
                f".cond_count = {len(conds)}, .actions = {act_sym}, "
                f".action_count = {len(acts)} }},"
            )

        if rules_out:
            rules_sym = f"{symbol_prefix}{safe}_rules"
            c.append(f"static const UiLogicRule {rules_sym}[] = {{")
            c.extend(rules_out)
            c.append("};")
            prog_inits.append(
                f'    {{ .scene_name = "{escape_c_string(key)}", '
                f".rules = {rules_sym}, "
                f".rule_count = (uint16_t)(sizeof({rules_sym}) / sizeof({rules_sym}[0])) }},"
            )
        else:
            prog_inits.append(
                f'    {{ .scene_name = "{escape_c_string(key)}", '
                ".rules = NULL, .rule_count = 0 },"
            )
        _ = s_i  # ordering only

    c.append("/* Per-scene logic programs (index-aligned with ui_scenes[]) */")
    c.append("const UiLogicProgram ui_logic_programs[] = {")
    c.extend(prog_inits)
    c.append("};")
    c.append("")

    h: list[str] = []
    h.append('#include "ui_logic.h"')
    h.append("extern const UiLogicProgram ui_logic_programs[];")
    h.append(f"#define UI_LOGIC_PROGRAM_COUNT {len(scene_keys)}")
    h.append(f"#define UI_LOGIC_VAR_COUNT {len(vt.order)}")
    return c, h, len(vt.order)


def generate_ui_design_pair(
    json_path: Path, *, scene_name: str, source_label: str
) -> tuple[str, str]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    selected_name, scene = select_scene(data, scene_name)
    widgets = scene.get("widgets", [])
    if not isinstance(widgets, list):
        widgets = []
    widgets = _widgets_in_paint_order(widgets)

    width = as_uint16(scene.get("width", data.get("width", 128)), 128)
    height = as_uint16(scene.get("height", data.get("height", 64)), 64)

    pool_values: list[str] = []
    for w in widgets:
        if isinstance(w, dict):
            pool_values.extend(collect_widget_strings(w))
    # Single-scene logic strings share the same pool.
    _single = {selected_name: scene}
    pool_values.extend(_logic_collect_strings(_single))

    pool = build_string_pool(pool_values, symbol_prefix="str_")

    # Visual-backend logic tables for this single scene.
    logic_c, logic_h, _vc = build_logic_tables(
        _single, [selected_name], pool, symbol_prefix="lg_"
    )

    # Header
    h_lines: list[str] = []
    h_lines.append("/* Auto-generated: UI design for ESP32OS */")
    h_lines.append(
        f"/* Source: {escape_c_comment(source_label)} (scene: {escape_c_comment(selected_name)}) */"
    )
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
    h_lines.append("/* Visual-backend logic program registry */")
    h_lines.extend(logic_h)
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
    c_lines.append(
        f"/* Source: {escape_c_comment(source_label)} (scene: {escape_c_comment(selected_name)}) */"
    )
    c_lines.append('#include "ui_design.h"')
    c_lines.append("")
    c_lines.append("/* String pool */")
    if pool.decls:
        c_lines.extend(pool.decls)
    else:
        c_lines.append("/* (empty) */")
    c_lines.append("")
    dp_decls, dp_by_id = build_data_point_arrays(widgets, symbol_prefix="dp_")
    if dp_decls:
        c_lines.append("/* Chart data series */")
        c_lines.extend(dp_decls)
        c_lines.append("")
    c_lines.append("/* Widget definitions */")
    if not widgets or not any(isinstance(w, dict) for w in widgets):
        c_lines.append("static const UiWidget widgets[] = {")
        c_lines.append("    {0}  /* empty sentinel */")
        c_lines.append("};")
        c_lines.append("")
        c_lines.append("/* Scene definition */")
        c_lines.append("const UiScene ui_design = {")
        c_lines.append(f'    .name = "{escape_c_string(selected_name)}",')
        c_lines.append(f"    .width = {width},")
        c_lines.append(f"    .height = {height},")
        c_lines.append("    .widget_count = 0,")
        c_lines.append("    .widgets = NULL,")
        c_lines.append("};")
        c_lines.append("")
        c_lines.append("/* Visual-backend logic (events / rules) */")
        c_lines.extend(logic_c)
        return "\n".join(c_lines), "\n".join(h_lines)

    c_lines.append("static const UiWidget widgets[] = {")

    for idx, w in enumerate(widgets):
        if not isinstance(w, dict):
            continue
        wtype = WIDGET_TYPE_MAP.get(str(w.get("type", "label")).lower(), "UIW_LABEL")
        x = as_uint16(w.get("x", 0), 0)
        y = as_uint16(w.get("y", 0), 0)
        ww = as_uint16(w.get("width", 8), 8)
        hh = as_uint16(w.get("height", 8), 8)
        border = 1 if as_bool(w.get("border", True), True) else 0
        checked = 1 if as_bool(w.get("checked", False), False) else 0
        value = as_int16(w.get("value", 0), 0)
        min_value = as_int16(w.get("min_value", 0), 0)
        max_value = as_int16(w.get("max_value", 100), 100)

        widget_id = str(w.get("_widget_id") or w.get("id") or "")
        text = str(w.get("text", "") or "")
        # For list widgets: join items into newline-separated text
        raw_items = w.get("items") or w.get("list_items")
        if isinstance(raw_items, list) and raw_items and not text:
            text = "\n".join(str(s) for s in raw_items)
        constraints = str(w.get("constraints_json", "") or w.get("runtime", "") or "")
        anim_csv = str(w.get("animations_csv", "") or "")
        if not anim_csv:
            anims = w.get("animations")
            if isinstance(anims, list) and anims:
                anim_csv = ";".join([str(x) for x in anims])

        icon_char = str(w.get("icon_char", "") or "")

        id_ref = pool.mapping.get(widget_id, "") if widget_id else ""
        text_ref = pool.mapping.get(text, "") if text else ""
        c_ref = pool.mapping.get(constraints, "") if constraints else ""
        a_ref = pool.mapping.get(anim_csv, "") if anim_csv else ""
        ic_ref = pool.mapping.get(icon_char, "") if icon_char else ""
        dp_ref = dp_by_id.get(id(w), "")
        dp_count = len(chart_data_points(w)) if dp_ref else 0

        fg = parse_gray4(w.get("color_fg", ""), default=15)
        bg = parse_gray4(w.get("color_bg", ""), default=0)
        border_style = border_style_for(w, border=border)
        align = align_for(w)
        valign = valign_for(w)
        overflow = overflow_for(w)
        max_lines = as_uint8(w.get("max_lines", 0), 0)
        style = style_expr(w.get("style", ""))
        visible = 1 if as_bool(w.get("visible", True), True) else 0
        enabled = 1 if as_bool(w.get("enabled", True), True) else 0

        preview = text or widget_id or ""
        c_lines.append(f'    {{ /* [{idx}] {wtype} "{escape_c_comment(preview)}" */')
        c_lines.append(f"        .type = {wtype},")
        c_lines.append(f"        .x = {x}, .y = {y}, .width = {ww}, .height = {hh},")
        c_lines.append(f"        .border = {border}, .checked = {checked},")
        c_lines.append(
            f"        .value = {value}, .min_value = {min_value}, .max_value = {max_value},"
        )
        c_lines.append(f"        .id = {id_ref if id_ref else 'NULL'},")
        c_lines.append(f"        .text = {text_ref if text_ref else 'NULL'},")
        c_lines.append(f"        .constraints_json = {c_ref if c_ref else 'NULL'},")
        c_lines.append(f"        .animations_csv = {a_ref if a_ref else 'NULL'},")
        c_lines.append(f"        .icon_char = {ic_ref if ic_ref else 'NULL'},")
        c_lines.append(f"        .data_points = {dp_ref if dp_ref else 'NULL'},")
        c_lines.append(f"        .data_count = {dp_count},")
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
    c_lines.append("/* Visual-backend logic (events / rules) */")
    c_lines.extend(logic_c)

    return "\n".join(c_lines), "\n".join(h_lines)


def load_scenes(json_path: Path) -> dict[str, Any]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    scenes_raw = data.get("scenes", {})
    if isinstance(scenes_raw, list):
        return {
            str(scene.get("id") or scene.get("name") or f"scene_{i}"): scene
            for i, scene in enumerate(scenes_raw)
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
        width = as_uint16(scene_data.get("width", 128), 128)
        height = as_uint16(scene_data.get("height", 64), 64)
        widgets = list(scene_data.get("widgets", []) or [])
        try:
            widgets.sort(key=lambda ww: (as_int(ww.get("z_index", 0), 0),))
        except (TypeError, ValueError, AttributeError):
            pass

        lines.append(f"/* Scene: {scene_name} ({width}x{height}) */")
        dp_decls, dp_by_id = build_data_point_arrays(
            widgets, symbol_prefix=f"{safe}_dp_"
        )
        if dp_decls:
            lines.extend(dp_decls)
        lines.append(f"static const UiWidget {safe}_widgets[] = {{")
        if not widgets or not any(isinstance(w, dict) for w in widgets):
            lines.append("    {0}  /* empty sentinel */")
            lines.append("};")
            lines.append("")
            lines.append(f"static const UiScene {safe}_scene = {{")
            lines.append(f'    .name = "{escape_c_string(scene_name)}",')
            lines.append(f"    .width = {width}, .height = {height},")
            lines.append("    .widget_count = 0,")
            lines.append("    .widgets = NULL,")
            lines.append("};")
            lines.append("")
            scene_names.append(safe)
            continue

        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            wtype = WIDGET_TYPE_MAP.get(str(w.get("type", "label")).lower(), "UIW_LABEL")
            x = as_uint16(w.get("x", 0), 0)
            y = as_uint16(w.get("y", 0), 0)
            ww = as_uint16(w.get("width", 8), 8)
            hh = as_uint16(w.get("height", 8), 8)
            border = 1 if as_bool(w.get("border", True), True) else 0
            checked = 1 if as_bool(w.get("checked", False), False) else 0
            value = as_int16(w.get("value", 0), 0)
            min_value = as_int16(w.get("min_value", 0), 0)
            max_value = as_int16(w.get("max_value", 100), 100)

            widget_id = str(w.get("_widget_id") or w.get("id") or "")
            text = str(w.get("text", "") or "")
            constraints = str(w.get("constraints_json", "") or w.get("runtime", "") or "")
            anim_csv = str(w.get("animations_csv", "") or "")
            if not anim_csv:
                anims = w.get("animations")
                if isinstance(anims, list) and anims:
                    anim_csv = ";".join([str(x) for x in anims])
            icon_char = str(w.get("icon_char", "") or "")

            id_ref = pool.mapping.get(widget_id, "") if widget_id else ""
            text_ref = pool.mapping.get(text, "") if text else ""
            c_ref = pool.mapping.get(constraints, "") if constraints else ""
            a_ref = pool.mapping.get(anim_csv, "") if anim_csv else ""
            ic_ref = pool.mapping.get(icon_char, "") if icon_char else ""
            dp_ref = dp_by_id.get(id(w), "")
            dp_count = len(chart_data_points(w)) if dp_ref else 0

            fg = parse_gray4(w.get("color_fg", ""), default=15)
            bg = parse_gray4(w.get("color_bg", ""), default=0)

            border_style = border_style_for(w, border=border)
            align = align_for(w)
            valign = valign_for(w)
            overflow = overflow_for(w)
            max_lines = as_uint8(w.get("max_lines", 0), 0)
            style = style_expr(w.get("style", ""))
            visible = 1 if as_bool(w.get("visible", True), True) else 0
            enabled = 1 if as_bool(w.get("enabled", True), True) else 0

            lines.append(f"    {{ /* [{idx}] {wtype} */")
            lines.append(f"        .type = {wtype},")
            lines.append(f"        .x = {x}, .y = {y}, .width = {ww}, .height = {hh},")
            lines.append(f"        .border = {border}, .checked = {checked},")
            lines.append(
                f"        .value = {value}, .min_value = {min_value}, .max_value = {max_value},"
            )
            lines.append(f"        .id = {id_ref if id_ref else 'NULL'},")
            lines.append(f"        .text = {text_ref if text_ref else 'NULL'},")
            lines.append(f"        .constraints_json = {c_ref if c_ref else 'NULL'},")
            lines.append(f"        .animations_csv = {a_ref if a_ref else 'NULL'},")
            lines.append(f"        .icon_char = {ic_ref if ic_ref else 'NULL'},")
            lines.append(f"        .data_points = {dp_ref if dp_ref else 'NULL'},")
            lines.append(f"        .data_count = {dp_count},")
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
        lines.append(
            f"    .widget_count = (uint16_t)(sizeof({safe}_widgets) / sizeof({safe}_widgets[0])),"
        )
        lines.append(f"    .widgets = {safe}_widgets,")
        lines.append("};")
        lines.append("")
        scene_names.append(safe)

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


def _emit_widget(
    w: dict[str, Any],
    idx: int,
    pool: StringPool,
    dp_by_id: dict[int, str] | None = None,
) -> list[str]:
    """Return C initializer lines for a single UiWidget."""
    lines: list[str] = []
    wtype = WIDGET_TYPE_MAP.get(str(w.get("type", "label")).lower(), "UIW_LABEL")
    x = as_uint16(w.get("x", 0), 0)
    y = as_uint16(w.get("y", 0), 0)
    ww = as_uint16(w.get("width", 8), 8)
    hh = as_uint16(w.get("height", 8), 8)
    border = 1 if as_bool(w.get("border", True), True) else 0
    checked = 1 if as_bool(w.get("checked", False), False) else 0
    value = as_int16(w.get("value", 0), 0)
    min_value = as_int16(w.get("min_value", 0), 0)
    max_value = as_int16(w.get("max_value", 100), 100)

    widget_id = str(w.get("_widget_id") or w.get("id") or "")
    text = str(w.get("text", "") or "")
    constraints = str(w.get("constraints_json", "") or w.get("runtime", "") or "")
    anim_csv = str(w.get("animations_csv", "") or "")
    if not anim_csv:
        anims = w.get("animations")
        if isinstance(anims, list) and anims:
            anim_csv = ";".join([str(a) for a in anims])

    icon_char = str(w.get("icon_char", "") or "")

    id_ref = pool.mapping.get(widget_id, "") if widget_id else ""
    text_ref = pool.mapping.get(text, "") if text else ""
    c_ref = pool.mapping.get(constraints, "") if constraints else ""
    a_ref = pool.mapping.get(anim_csv, "") if anim_csv else ""
    ic_ref = pool.mapping.get(icon_char, "") if icon_char else ""
    dp_ref = (dp_by_id or {}).get(id(w), "")
    dp_count = len(chart_data_points(w)) if dp_ref else 0

    fg = parse_gray4(w.get("color_fg", ""), default=15)
    bg = parse_gray4(w.get("color_bg", ""), default=0)
    bs = border_style_for(w, border=border)
    al = align_for(w)
    va = valign_for(w)
    ov = overflow_for(w)
    ml = as_uint8(w.get("max_lines", 0), 0)
    st = style_expr(w.get("style", ""))
    vis = 1 if as_bool(w.get("visible", True), True) else 0
    ena = 1 if as_bool(w.get("enabled", True), True) else 0

    preview = text or widget_id or ""
    lines.append(f'    {{ /* [{idx}] {wtype} "{escape_c_comment(preview)}" */')
    lines.append(f"        .type = {wtype},")
    lines.append(f"        .x = {x}, .y = {y}, .width = {ww}, .height = {hh},")
    lines.append(f"        .border = {border}, .checked = {checked},")
    lines.append(f"        .value = {value}, .min_value = {min_value}, .max_value = {max_value},")
    lines.append(f"        .id = {id_ref if id_ref else 'NULL'},")
    lines.append(f"        .text = {text_ref if text_ref else 'NULL'},")
    lines.append(f"        .constraints_json = {c_ref if c_ref else 'NULL'},")
    lines.append(f"        .animations_csv = {a_ref if a_ref else 'NULL'},")
    lines.append(f"        .icon_char = {ic_ref if ic_ref else 'NULL'},")
    lines.append(f"        .data_points = {dp_ref if dp_ref else 'NULL'},")
    lines.append(f"        .data_count = {dp_count},")
    lines.append(f"        .fg = {fg}, .bg = {bg},")
    lines.append(f"        .border_style = {bs},")
    lines.append(f"        .align = {al}, .valign = {va},")
    lines.append(f"        .text_overflow = {ov}, .max_lines = {ml},")
    lines.append(f"        .style = {st},")
    lines.append(f"        .visible = {vis}, .enabled = {ena},")
    lines.append("    },")
    return lines


def generate_ui_design_multi_pair(json_path: Path, *, source_label: str) -> tuple[str, str]:
    """Generate ui_design.c + ui_design.h with ALL scenes from the JSON file.

    Exports:
      - ``const UiScene ui_scenes[]`` (one entry per scene)
      - ``#define UI_SCENE_COUNT N``
      - per-scene index macros ``#define UI_SCENE_IDX_<NAME> <i>``
      - backward-compat ``#define UI_SCENE_DEMO ui_scenes[0]``
    """
    scenes = load_scenes(json_path)
    if not scenes:
        raise ValueError("No scenes found in JSON.")

    pool = build_string_pool(
        collect_scenes_strings(scenes) + _logic_collect_strings(scenes),
        symbol_prefix="str_",
    )

    scene_names: list[str] = []  # sanitised C identifiers
    scene_keys: list[str] = []  # original names

    # === Header (.h) ===
    h: list[str] = []
    h.append("/* Auto-generated: UI design for ESP32OS (multi-scene) */")
    h.append(f"/* Source: {escape_c_comment(source_label)} */")
    h.append("#ifndef UI_DESIGN_H")
    h.append("#define UI_DESIGN_H")
    h.append("")
    h.append("#include <stdint.h>")
    h.append('#include "ui_scene.h"')
    h.append("")
    h.append("#define UI_ENABLE_CONSTRAINTS 1")
    h.append("#define UI_ENABLE_ANIMATIONS  1")
    h.append("")
    h.append("#ifdef __cplusplus")
    h.append('extern "C" {')
    h.append("#endif")
    h.append("")

    # === Source (.c) ===
    c: list[str] = []
    c.append("/* Auto-generated: UI design for ESP32OS (multi-scene) */")
    c.append(f"/* Source: {escape_c_comment(source_label)} */")
    c.append('#include "ui_design.h"')
    c.append("")
    c.append("/* String pool */")
    if pool.decls:
        c.extend(pool.decls)
    else:
        c.append("/* (empty) */")
    c.append("")

    for scene_name, scene_data in scenes.items():
        safe = sanitize_ident(scene_name)
        scene_names.append(safe)
        scene_keys.append(scene_name)

        widgets = scene_data.get("widgets", [])
        if not isinstance(widgets, list):
            widgets = []
        widgets = _widgets_in_paint_order(widgets)
        width = as_uint16(scene_data.get("width", 128), 128)
        height = as_uint16(scene_data.get("height", 64), 64)

        c.append(f"/* Scene: {escape_c_comment(scene_name)} ({len(widgets)} widgets) */")
        dp_decls, dp_by_id = build_data_point_arrays(
            widgets, symbol_prefix=f"{safe}_dp_"
        )
        if dp_decls:
            c.extend(dp_decls)
        c.append(f"static const UiWidget {safe}_widgets[] = {{")
        has_widgets = any(isinstance(w, dict) for w in widgets)
        if not has_widgets:
            c.append("    {0}  /* empty sentinel */")
        for idx, w in enumerate(widgets):
            if isinstance(w, dict):
                c.extend(_emit_widget(w, idx, pool, dp_by_id))
        c.append("};")
        c.append("")

    # Scene array
    c.append("/* Scene registry */")
    c.append("const UiScene ui_scenes[] = {")
    for safe, key in zip(scene_names, scene_keys):
        scene_data = scenes[key]
        widgets = scene_data.get("widgets", [])
        if not isinstance(widgets, list):
            widgets = []
        width = as_uint16(scene_data.get("width", 128), 128)
        height = as_uint16(scene_data.get("height", 64), 64)
        has_widgets = any(isinstance(w, dict) for w in widgets) if widgets else False
        c.append(f"    {{ /* {escape_c_comment(key)} */")
        c.append(f'        .name = "{escape_c_string(key)}",')
        c.append(f"        .width = {width}, .height = {height},")
        if has_widgets:
            c.append(
                f"        .widget_count = (uint16_t)(sizeof({safe}_widgets) / sizeof({safe}_widgets[0])),"
            )
            c.append(f"        .widgets = {safe}_widgets,")
        else:
            c.append("        .widget_count = 0,")
            c.append("        .widgets = NULL,")
        c.append("    },")
    c.append("};")
    c.append("")

    # Visual-backend logic tables (events + rules) -> deterministic C.
    logic_c, logic_h, _var_count = build_logic_tables(
        scenes, scene_keys, pool, symbol_prefix="lg_"
    )
    c.append("/* ─────────── Visual-backend logic (events / rules) ─────────── */")
    c.extend(logic_c)

    # Header: extern + defines
    h.append(f"#define UI_SCENE_COUNT {len(scene_names)}")
    h.append("")
    h.append("/* Scene index macros */")
    for i, safe in enumerate(scene_names):
        h.append(f"#define UI_SCENE_IDX_{safe.upper()} {i}")
    h.append("")
    h.append("/* Scene array */")
    h.append("extern const UiScene ui_scenes[];")
    h.append("")
    h.append("/* Backward-compatible alias (first scene) */")
    h.append("#define UI_SCENE_DEMO ui_scenes[0]")
    h.append("")
    h.append("/* Visual-backend logic program registry */")
    h.extend(logic_h)
    h.append("")
    h.append("#ifdef __cplusplus")
    h.append("}")
    h.append("#endif")
    h.append("")
    h.append("#endif /* UI_DESIGN_H */")
    h.append("")

    return "\n".join(c), "\n".join(h)
