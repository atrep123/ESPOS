"""Local M5 FE Studio for the real DinMeter and M5 Dial render harnesses."""

from __future__ import annotations

import io
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import preview_din_rx_render as DIN
import preview_prop_tx as DIAL


HOST = "127.0.0.1"
PORT = int(os.environ.get("M5_STUDIO_PORT", "8078"))
DEVICES = {"dinmeter", "dial"}


def _int(params: dict[str, str], name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(params.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _bool(params: dict[str, str], name: str, default: bool) -> bool:
    if name not in params:
        return default
    return params[name].lower() in ("1", "true", "on", "yes")


def _choice(params: dict[str, str], name: str, default: str, allowed: set[str]) -> str:
    value = params.get(name, default)
    return value if value in allowed else default


def _hex_to_rgb(text: str) -> tuple[int, int, int] | None:
    s = text.lstrip("#").strip()
    if len(s) != 6:
        return None
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None


def _rgb_to_hex(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % color


def _parse_palette(params: dict[str, str], default: tuple) -> tuple:
    count = _int(params, "pal_count", len(default), 1, 8)
    cells = []
    for i in range(count):
        rgb = _hex_to_rgb(params.get(f"pal{i}", ""))
        if rgb is None:
            rgb = default[i] if i < len(default) else (255, 255, 255)
        cells.append(rgb)
    return tuple(cells)


def build_dinmeter_view(params: dict[str, str]) -> tuple[DIN.View, str]:
    default_config = DIN.EffectConfig()
    default_view = DIN.View()

    state = _choice(params, "state", "KLID", {"KLID", "NABITO", "PALI", "STOP"})
    status = state
    mode = "idle"
    armed = False
    if state == "NABITO":
        armed = True
    elif state == "PALI":
        mode = "fire"
    elif state == "STOP":
        armed = False

    mode = _choice(params, "mode", mode, {"idle", "preview", "fire"})

    config = DIN.EffectConfig(
        pre_trigger=_bool(params, "pre_trigger", default_config.pre_trigger),
        shape=_int(params, "shape", default_config.shape, DIN.EFFECT_SHAPE_SINE2, DIN.EFFECT_SHAPE_EXP),
        shape_param=_int(params, "shape_param", default_config.shape_param, 0, 100),
        period_ms=_int(params, "period_ms", default_config.period_ms, 100, 3000),
        repeat=_int(params, "repeat", default_config.repeat, 0, 8),
        intensity=_int(params, "intensity", default_config.intensity, 0, 100),
        led_delay_ms=(
            _int(params, "led0", default_config.led_delay_ms[0], 0, 500),
            _int(params, "led1", default_config.led_delay_ms[1], 0, 500),
            _int(params, "led2", default_config.led_delay_ms[2], 0, 500),
            _int(params, "led3", default_config.led_delay_ms[3], 0, 500),
        ),
    )

    selected_row = _int(params, "selected_row", default_view.selected_row, 0, 7)
    row_scroll = max(0, min(selected_row, 6))
    page = _choice(params, "page", "main", {"main", "delays"})
    palette = _parse_palette(params, default_view.palette)

    return (
        DIN.View(
            status=status,
            mode=mode,
            armed=armed,
            config=config,
            battery_percent=_int(params, "battery_percent", default_view.battery_percent, 0, 100),
            rows_visible=_bool(params, "rows_visible", default_view.rows_visible),
            row_scroll=row_scroll,
            selected_row=selected_row,
            editing=_bool(params, "editing", default_view.editing),
            selected_delay_led=_int(params, "selected_delay_led", default_view.selected_delay_led, 0, 3),
            elapsed_ms=_int(params, "elapsed_ms", default_view.elapsed_ms, 0, 3000),
            has_palette=default_view.has_palette,
            palette_fade=_bool(params, "palette_fade", default_view.palette_fade),
            palette=palette,
            dial_colors=default_view.dial_colors,
        ),
        page,
    )


def build_dial_view(params: dict[str, str]) -> DIAL.View:
    default = DIAL.View()
    colors = []
    for i in range(4):
        rgb = _hex_to_rgb(params.get(f"col{i}", ""))
        colors.append(rgb if rgb is not None else tuple(default.colors[i]))

    return DIAL.View(
        status=params.get("status", default.status),
        armed=_bool(params, "armed", default.armed),
        awaiting_ack=_bool(params, "awaiting_ack", default.awaiting_ack),
        brightness_percent=_int(params, "brightness_percent", default.brightness_percent, 0, 100),
        selected_led=_int(params, "selected_led", default.selected_led, 0, 3),
        selected_hue_degrees=_int(params, "selected_hue_degrees", default.selected_hue_degrees, 0, 359),
        shot_count=_int(params, "shot_count", default.shot_count, 0, 99),
        action_label=params.get("action_label", default.action_label),
        field_label=params.get("field_label", default.field_label),
        field_value=params.get("field_value", default.field_value),
        colors=colors,
    )


_RENDER_LOCK = threading.Lock()

# DinMeter theme (colours) -- single source tools/m5_theme.json. The Studio edits these
# live (DIN.apply_theme per render) and can export them straight into the firmware header
# (tools/gen_firmware_theme.py -> firmware/din-rx/src/ui_theme_generated.h).
_THEME_PATH = os.path.join(TOOLS_DIR, "m5_theme.json")
with open(_THEME_PATH, encoding="utf-8") as _tf:
    THEME = json.load(_tf)
THEME_COLOR_KEYS = list(THEME["colors"])


def _theme_from_params(params: dict) -> dict:
    """Collect t_<KEY> colour overrides from the query into a DIN.apply_theme() dict.
    Missing keys fall back to the saved theme so every render sets the full theme."""
    colors = {}
    for key in THEME_COLOR_KEYS:
        rgb = _hex_to_rgb(params.get(f"t_{key}", ""))
        colors[key] = ("0x%02X%02X%02X" % rgb) if rgb is not None else THEME["colors"][key]
    return {"colors": colors}


def _theme_pickers_html() -> str:
    rows = []
    for key in THEME_COLOR_KEYS:
        nice = key.replace("COLOR_", "").replace("CHIP_KLID_", "CHIP ").replace("_", " ").title()
        rows.append(
            f'          <label>{nice}\n'
            f'            <input name="t_{key}" type="color">\n'
            f'            <span class="value" data-value-for="t_{key}"></span>\n'
            f"          </label>"
        )
    return "\n".join(rows)


DIN_THEME_PICKERS = _theme_pickers_html()

THEME_DIAL_KEYS = list(THEME.get("dial", {}))


def _dial_theme_from_params(params: dict) -> dict:
    """Collect td_<KEY> Dial colour overrides into a DIAL.apply_theme() dict.
    Missing keys fall back to the saved dial theme so every render sets it fully."""
    colors = {}
    for key in THEME_DIAL_KEYS:
        rgb = _hex_to_rgb(params.get(f"td_{key}", ""))
        colors[key] = ("0x%02X%02X%02X" % rgb) if rgb is not None else THEME["dial"][key]
    return colors


def _dial_theme_pickers_html() -> str:
    rows = []
    for key in THEME_DIAL_KEYS:
        nice = key.replace("P_", "").replace("_", " ").title()
        rows.append(
            f'          <label>{nice}\n'
            f'            <input name="td_{key}" type="color">\n'
            f'            <span class="value" data-value-for="td_{key}"></span>\n'
            f"          </label>"
        )
    return "\n".join(rows)


DIAL_THEME_PICKERS = _dial_theme_pickers_html()


DIN_DEFAULTS = {
    "state": "KLID",
    "shape": DIN.EFFECT_SHAPE_SINE2,
    "period_ms": DIN.DEFAULT_PERIOD_MS,
    "intensity": 100,
    "shape_param": 50,
    "repeat": DIN.DEFAULT_REPEAT,
    "pre_trigger": False,
    "palette_fade": True,
    "battery_percent": 72,
    "rows_visible": False,
    "editing": False,
    "selected_row": 0,
    "elapsed_ms": 0,
    "page": "main",
    "selected_delay_led": 0,
    "led0": 0,
    "led1": 80,
    "led2": 160,
    "led3": 240,
}

_DIN_PALETTE = DIN.View().palette
DIN_DEFAULTS["pal_count"] = len(_DIN_PALETTE)
for _i in range(8):
    _c = _DIN_PALETTE[_i] if _i < len(_DIN_PALETTE) else (255, 255, 255)
    DIN_DEFAULTS[f"pal{_i}"] = _rgb_to_hex(_c)

# Theme colour pickers default to the saved m5_theme.json values (0xRRGGBB -> #rrggbb).
for _k in THEME_COLOR_KEYS:
    DIN_DEFAULTS[f"t_{_k}"] = "#" + THEME["colors"][_k][2:].lower()

_DIAL_DEFAULT = DIAL.View()
DIAL_DEFAULTS = {
    "status": _DIAL_DEFAULT.status,
    "armed": _DIAL_DEFAULT.armed,
    "awaiting_ack": _DIAL_DEFAULT.awaiting_ack,
    "brightness_percent": _DIAL_DEFAULT.brightness_percent,
    "selected_led": _DIAL_DEFAULT.selected_led,
    "selected_hue_degrees": _DIAL_DEFAULT.selected_hue_degrees,
    "shot_count": _DIAL_DEFAULT.shot_count,
    "action_label": _DIAL_DEFAULT.action_label,
    "field_label": _DIAL_DEFAULT.field_label,
    "field_value": _DIAL_DEFAULT.field_value,
}
for _i in range(4):
    DIAL_DEFAULTS[f"col{_i}"] = _rgb_to_hex(tuple(_DIAL_DEFAULT.colors[_i]))

# Dial theme colour pickers default to the saved m5_theme.json "dial" values.
for _k in THEME_DIAL_KEYS:
    DIAL_DEFAULTS[f"td_{_k}"] = "#" + THEME["dial"][_k][2:].lower()

DEFAULTS = {
    "device": "dinmeter",
    "dinmeter": DIN_DEFAULTS,
    "dial": DIAL_DEFAULTS,
}


# ----------------------------------------------------------------------------
# Presets, all-states "Vše" contact sheet, status options, native sizes.
# Everything below is derived from each harness's scenes() so the studio stays
# in lock-step with the real device states (no hand-kept duplicate lists).
# ----------------------------------------------------------------------------


def _din_view_to_params(view: DIN.View, page: str) -> dict:
    """Inverse of build_dinmeter_view: a renderer View -> studio control values."""
    c = view.config
    params = {
        "state": "PALI" if view.mode == "fire" else view.status,
        "shape": c.shape,
        "period_ms": c.period_ms,
        "intensity": c.intensity,
        "shape_param": c.shape_param,
        "repeat": c.repeat,
        "battery_percent": view.battery_percent,
        "selected_row": max(0, view.selected_row),
        "elapsed_ms": view.elapsed_ms,
        "selected_delay_led": view.selected_delay_led,
        "page": page,
        "pre_trigger": 1 if c.pre_trigger else 0,
        "palette_fade": 1 if view.palette_fade else 0,
        "rows_visible": 1 if view.rows_visible else 0,
        "editing": 1 if view.editing else 0,
        "pal_count": len(view.palette),
    }
    for i, delay in enumerate(c.led_delay_ms):
        params[f"led{i}"] = delay
    for i in range(8):
        col = view.palette[i] if i < len(view.palette) else (255, 255, 255)
        params[f"pal{i}"] = _rgb_to_hex(col)
    return params


def _dial_view_to_params(view: DIAL.View) -> dict:
    """Inverse of build_dial_view: a Dial View -> studio control values."""
    params = {
        "status": view.status,
        "armed": 1 if view.armed else 0,
        "awaiting_ack": 1 if view.awaiting_ack else 0,
        "brightness_percent": view.brightness_percent,
        "selected_led": view.selected_led,
        "selected_hue_degrees": view.selected_hue_degrees,
        "shot_count": view.shot_count,
        "action_label": view.action_label,
        "field_label": view.field_label,
        "field_value": view.field_value,
    }
    for i in range(4):
        col = tuple(view.colors[i]) if i < len(view.colors) else (255, 255, 255)
        params[f"col{i}"] = _rgb_to_hex(col)
    return params


# All scenes as ready-to-apply control sets, keyed by device.
PRESETS = {
    "dinmeter": {name: _din_view_to_params(v, p) for name, (v, p) in DIN.scenes().items()},
    "dial": {name: _dial_view_to_params(v) for name, v in DIAL.scenes().items()},
}

# Curated preset buttons (scene key -> friendly label); emitted only if the scene exists.
_DIN_PRESET_BUTTONS = [
    ("main_idle", "KLID"), ("main_armed", "NABITO"), ("main_firing", "PÁLÍ"),
    ("main_stop", "STOP"), ("main_editing", "EDIT"),
]
_DIAL_PRESET_BUTTONS = [
    ("01_ready_action", "Ready"), ("02_action_fire", "ODPAL"), ("03_armed", "ARM"),
    ("04_wait_ack", "Wait"), ("05_ack", "ACK"), ("07_edit_jas", "Jas"),
    ("08_edit_led", "LED"), ("09_edit_hue", "Hue"),
]
PRESET_BUTTONS = {
    "dinmeter": [(k, lbl) for k, lbl in _DIN_PRESET_BUTTONS if k in PRESETS["dinmeter"]],
    "dial": [(k, lbl) for k, lbl in _DIAL_PRESET_BUTTONS if k in PRESETS["dial"]],
}

# Scenes shown in the "Vše" (all states) contact sheet, per device.
_DIN_CONTACT = ["main_idle", "main_armed", "main_firing", "main_stop", "main_editing", "led_delays"]
CONTACT_KEYS = {
    "dinmeter": [n for n in _DIN_CONTACT if n in PRESETS["dinmeter"]],
    "dial": list(PRESETS["dial"].keys()),
}

# Distinct Dial status strings (scene statuses first) so every preset's status is a
# valid <select> option; a few hand-edit extras are appended.
_DIAL_STATUS_LABELS = {
    "ready": "ready", "armed": "armed", "ARM ready": "armed",
    "sent FIRE wait": "wait", "ACK 42": "ack", "no ack": "no ack",
    "timeout": "timeout", "ERR radio": "error", "RX ignored": "rx ignored",
    "LED 3 BARVA": "led setup",
}


def _dial_status_options() -> list[str]:
    seen: list[str] = []
    for v in DIAL.scenes().values():
        if v.status not in seen:
            seen.append(v.status)
    for extra in (_DIAL_DEFAULT.status, "ready", "armed", "timeout", "ERR radio", "RX ignored"):
        if extra and extra not in seen:
            seen.append(extra)
    return seen


DIAL_STATUSES = _dial_status_options()
DIAL_STATUS_OPTIONS_HTML = "\n".join(
    f'              <option value="{s}">{_DIAL_STATUS_LABELS.get(s, s)}</option>'
    for s in DIAL_STATUSES
)


def _preset_row_html(device: str) -> str:
    return "\n".join(
        f'        <button type="button" data-preset="{k}" data-preset-device="{device}">{lbl}</button>'
        for k, lbl in PRESET_BUTTONS[device]
    )


DIN_PRESET_ROW = _preset_row_html("dinmeter")
DIAL_PRESET_ROW = _preset_row_html("dial")

# Device native render width (px) for the 1:1 toggle, and the default zoom width.
NATIVE_WIDTH = {"dinmeter": 240, "dial": 272}
ZOOM_WIDTH = 640


def _contact_sheet(imgs: list) -> "object":
    """Generic grid contact sheet for any device's renders (mixed sizes ok)."""
    from PIL import Image, ImageDraw, ImageFont  # harness already pulls PIL in

    if not imgs:
        return Image.new("RGB", (240, 135), (20, 22, 26))
    cell_w = max(im.width for _, im in imgs)
    cell_h = max(im.height for _, im in imgs)
    label_h = 16
    cols = 3 if len(imgs) > 4 else 2
    rows = (len(imgs) + cols - 1) // cols
    pad = 12
    sheet = Image.new(
        "RGB",
        (cols * cell_w + (cols + 1) * pad, rows * (cell_h + label_h) + (rows + 1) * pad),
        (20, 22, 26),
    )
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    for idx, (name, im) in enumerate(imgs):
        row, col = divmod(idx, cols)
        x = pad + col * (cell_w + pad)
        y = pad + row * (cell_h + label_h + pad)
        sheet.paste(im, (x + (cell_w - im.width) // 2, y))
        if font is not None:
            draw.text((x, y + cell_h + 2), name, font=font, fill=(150, 170, 175))
    return sheet


HTML = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>M5 FE Studio</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #15191f;
      color: #e7e9ed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: #15191f;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(340px, 430px) 1fr;
      gap: 28px;
      align-items: start;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .tabs {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .tabs button {{
      min-height: 34px;
      border: 1px solid #3c4652;
      border-radius: 7px;
      background: #202730;
      color: #d7dde4;
      font-weight: 700;
      cursor: pointer;
    }}
    .tabs button.active {{
      background: #4fd1c5;
      border-color: #4fd1c5;
      color: #07120b;
    }}
    form, .controls {{
      display: grid;
      gap: 12px;
    }}
    .controls[hidden] {{
      display: none;
    }}
    label {{
      display: grid;
      grid-template-columns: 136px 1fr 54px;
      gap: 10px;
      align-items: center;
      min-height: 32px;
      color: #d7dde4;
      font-size: 14px;
    }}
    select,
    input[type="range"],
    input[type="text"] {{
      width: 100%;
    }}
    select,
    input[type="text"] {{
      min-height: 30px;
      border: 1px solid #3c4652;
      border-radius: 6px;
      background: #202730;
      color: #f2f4f6;
      padding: 4px 8px;
    }}
    input[type="range"] {{
      accent-color: #4fd1c5;
    }}
    input[type="checkbox"] {{
      width: 18px;
      height: 18px;
      accent-color: #ff8c00;
    }}
    .check-label {{
      grid-template-columns: 136px 18px 54px;
    }}
    .value {{
      justify-self: end;
      min-width: 42px;
      color: #9fc2c8;
      font-variant-numeric: tabular-nums;
      overflow: hidden;
      text-align: right;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .swatches {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      padding: 2px 0 6px;
    }}
    .swatches input[type="color"] {{
      width: 38px;
      height: 30px;
      border: 1px solid #3c4652;
      border-radius: 6px;
      background: #202730;
      padding: 2px;
      cursor: pointer;
    }}
    .presets {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .presets[hidden] {{ display: none; }}
    .presets button {{
      padding: 7px 12px;
      border: 1px solid #3c4652;
      border-radius: 7px;
      background: #202730;
      color: #e7e9ed;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }}
    .presets button:hover {{ background: #2a333d; }}
    .animbar {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }}
    .animbar button {{
      padding: 7px 14px;
      border: 1px solid #3c4652;
      border-radius: 7px;
      background: #202730;
      color: #e7e9ed;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }}
    .animbar button:hover {{ background: #2a333d; }}
    .animbar button#playbtn {{ background: #2e9e72; color: #07120b; font-weight: 700; }}
    .animbar.playing button#playbtn {{ background: #ff8c00; color: #1a1206; }}
    .theme {{
      border: 1px solid #2c3440;
      border-radius: 7px;
      padding: 6px 10px;
      background: #1b2129;
    }}
    .theme summary {{
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      color: #9fc2c8;
      padding: 2px 0;
    }}
    .theme label {{ grid-template-columns: 136px 1fr 72px; }}
    label input[type="color"] {{
      width: 100%;
      height: 28px;
      border: 1px solid #3c4652;
      border-radius: 6px;
      background: #202730;
      padding: 2px;
      cursor: pointer;
    }}
    .preview {{
      min-width: 0;
      overflow-x: auto;
    }}
    #screen {{
      width: 640px;
      height: auto;
      max-width: none;
      border: 1px solid #303a45;
      background: #121820;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
    }}
    @media (max-width: 920px) {{
      main {{
        grid-template-columns: 1fr;
      }}
      #screen {{
        width: 100%;
        max-width: 640px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>M5 FE Studio</h1>
      <div class="tabs">
        <button type="button" data-device-tab="dinmeter">DinMeter</button>
        <button type="button" data-device-tab="dial">Dial</button>
      </div>
      <div class="presets" data-preset-row="dinmeter">
{DIN_PRESET_ROW}
      </div>
      <div class="presets" data-preset-row="dial" hidden>
{DIAL_PRESET_ROW}
      </div>
      <div class="animbar">
        <button type="button" id="playbtn">Play</button>
        <button type="button" id="onetoonebtn">1:1</button>
        <button type="button" id="exportbtn">Export PNG</button>
        <button type="button" id="sharebtn">Odkaz</button>
        <button type="button" id="allbtn">Vše</button>
        <button type="button" id="resetbtn">Reset</button>
        <button type="button" id="savethemebtn">Uložit téma → firmware</button>
        <a id="dl" style="display:none"></a>
      </div>
      <form id="controls">
        <input type="hidden" name="device" value="dinmeter">

        <section class="controls" data-device="dinmeter">
          <label>State
            <select name="state">
              <option value="KLID">KLID</option>
              <option value="NABITO">NABITO</option>
              <option value="PALI">PALI</option>
              <option value="STOP">STOP</option>
            </select>
            <span class="value" data-value-for="state"></span>
          </label>
          <label>Shape
            <select name="shape">
              <option value="{DIN.EFFECT_SHAPE_SINE2}">SIN2</option>
              <option value="{DIN.EFFECT_SHAPE_SQUARE}">SQUARE</option>
              <option value="{DIN.EFFECT_SHAPE_SAWTOOTH}">SAW</option>
              <option value="{DIN.EFFECT_SHAPE_TRIANGLE}">TRIANGLE</option>
              <option value="{DIN.EFFECT_SHAPE_EXP}">EXP</option>
            </select>
            <span class="value" data-value-for="shape"></span>
          </label>
          <label>Page
            <select name="page">
              <option value="main">main</option>
              <option value="delays">delays</option>
            </select>
            <span class="value" data-value-for="page"></span>
          </label>
          <label>Period
            <input name="period_ms" type="range" min="100" max="3000" step="1">
            <span class="value" data-value-for="period_ms"></span>
          </label>
          <label>Intensity
            <input name="intensity" type="range" min="0" max="100" step="1">
            <span class="value" data-value-for="intensity"></span>
          </label>
          <label>Shape param
            <input name="shape_param" type="range" min="0" max="100" step="1">
            <span class="value" data-value-for="shape_param"></span>
          </label>
          <label>Repeat
            <input name="repeat" type="range" min="0" max="8" step="1">
            <span class="value" data-value-for="repeat"></span>
          </label>
          <label>Battery
            <input name="battery_percent" type="range" min="0" max="100" step="1">
            <span class="value" data-value-for="battery_percent"></span>
          </label>
          <label>Rows visible
            <input name="rows_visible" type="checkbox">
            <span class="value" data-value-for="rows_visible"></span>
          </label>
          <label>Editing
            <input name="editing" type="checkbox">
            <span class="value" data-value-for="editing"></span>
          </label>
          <label>Selected row
            <input name="selected_row" type="range" min="0" max="7" step="1">
            <span class="value" data-value-for="selected_row"></span>
          </label>
          <label>Elapsed
            <input name="elapsed_ms" type="range" min="0" max="3000" step="1">
            <span class="value" data-value-for="elapsed_ms"></span>
          </label>
          <label>Palette N
            <input name="pal_count" type="range" min="1" max="8" step="1">
            <span class="value" data-value-for="pal_count"></span>
          </label>
          <div class="swatches">
            <input name="pal0" type="color" title="palette 1">
            <input name="pal1" type="color" title="palette 2">
            <input name="pal2" type="color" title="palette 3">
            <input name="pal3" type="color" title="palette 4">
            <input name="pal4" type="color" title="palette 5">
            <input name="pal5" type="color" title="palette 6">
            <input name="pal6" type="color" title="palette 7">
            <input name="pal7" type="color" title="palette 8">
          </div>
          <label>Delay page LED
            <input name="selected_delay_led" type="range" min="0" max="3" step="1">
            <span class="value" data-value-for="selected_delay_led"></span>
          </label>
          <label>LED 0 delay
            <input name="led0" type="range" min="0" max="500" step="1">
            <span class="value" data-value-for="led0"></span>
          </label>
          <label>LED 1 delay
            <input name="led1" type="range" min="0" max="500" step="1">
            <span class="value" data-value-for="led1"></span>
          </label>
          <label>LED 2 delay
            <input name="led2" type="range" min="0" max="500" step="1">
            <span class="value" data-value-for="led2"></span>
          </label>
          <label>LED 3 delay
            <input name="led3" type="range" min="0" max="500" step="1">
            <span class="value" data-value-for="led3"></span>
          </label>
          <label>Pre trigger
            <input name="pre_trigger" type="checkbox">
            <span class="value" data-value-for="pre_trigger"></span>
          </label>
          <label>Palette fade
            <input name="palette_fade" type="checkbox">
            <span class="value" data-value-for="palette_fade"></span>
          </label>
          <details class="theme">
            <summary>Téma (barvy) → firmware</summary>
{DIN_THEME_PICKERS}
          </details>
        </section>

        <section class="controls" data-device="dial" hidden>
          <label>Status
            <select name="status">
{DIAL_STATUS_OPTIONS_HTML}
            </select>
            <span class="value" data-value-for="status"></span>
          </label>
          <label>Armed
            <input name="armed" type="checkbox">
            <span class="value" data-value-for="armed"></span>
          </label>
          <label>Awaiting ack
            <input name="awaiting_ack" type="checkbox">
            <span class="value" data-value-for="awaiting_ack"></span>
          </label>
          <label>Brightness
            <input name="brightness_percent" type="range" min="0" max="100" step="1">
            <span class="value" data-value-for="brightness_percent"></span>
          </label>
          <label>Selected LED
            <input name="selected_led" type="range" min="0" max="3" step="1">
            <span class="value" data-value-for="selected_led"></span>
          </label>
          <label>Hue
            <input name="selected_hue_degrees" type="range" min="0" max="359" step="1">
            <span class="value" data-value-for="selected_hue_degrees"></span>
          </label>
          <label>Shot count
            <input name="shot_count" type="range" min="0" max="99" step="1">
            <span class="value" data-value-for="shot_count"></span>
          </label>
          <label>Action label
            <input name="action_label" type="text" maxlength="16">
            <span class="value" data-value-for="action_label"></span>
          </label>
          <label>Field label
            <input name="field_label" type="text" maxlength="16">
            <span class="value" data-value-for="field_label"></span>
          </label>
          <label>Field value
            <input name="field_value" type="text" maxlength="16">
            <span class="value" data-value-for="field_value"></span>
          </label>
          <div class="swatches">
            <input name="col0" type="color" title="LED 1">
            <input name="col1" type="color" title="LED 2">
            <input name="col2" type="color" title="LED 3">
            <input name="col3" type="color" title="LED 4">
          </div>
          <details class="theme">
            <summary>Téma (barvy) → firmware</summary>
{DIAL_THEME_PICKERS}
          </details>
        </section>
      </form>
    </section>
    <section class="preview">
      <img id="screen" alt="M5 render">
    </section>
  </main>
  <script>
    const defaults = {json.dumps(DEFAULTS)};
    const form = document.getElementById('controls');
    const screen = document.getElementById('screen');
    const deviceInput = form.elements['device'];
    let animTimer = null;

    function sections() {{
      return Array.from(document.querySelectorAll('.controls'));
    }}

    function controlsFor(device) {{
      const section = document.querySelector('.controls[data-device="' + device + '"]');
      return section ? Array.from(section.querySelectorAll('[name]')) : [];
    }}

    function controlValue(control) {{
      return control.type === 'checkbox' ? (control.checked ? '1' : '0') : control.value;
    }}

    function setControl(control, value) {{
      if (control.type === 'checkbox') control.checked = Boolean(value);
      else control.value = value;
    }}

    function setDefaults() {{
      for (const device of ['dinmeter', 'dial']) {{
        const d = defaults[device];
        for (const control of controlsFor(device)) {{
          if (Object.prototype.hasOwnProperty.call(d, control.name)) {{
            setControl(control, d[control.name]);
          }}
        }}
      }}
      deviceInput.value = defaults.device;
    }}

    function applyHash() {{
      if (!location.hash || location.hash.length < 2) return;
      const p = new URLSearchParams(location.hash.slice(1));
      const device = p.get('device');
      if (device === 'dinmeter' || device === 'dial') deviceInput.value = device;
      for (const control of controlsFor(deviceInput.value)) {{
        if (!p.has(control.name)) continue;
        if (control.type === 'checkbox') control.checked = p.get(control.name) === '1';
        else control.value = p.get(control.name);
      }}
    }}

    function showDevice(device) {{
      if (device !== 'dinmeter' && device !== 'dial') device = 'dinmeter';
      deviceInput.value = device;
      for (const section of sections()) {{
        section.hidden = section.dataset.device !== device;
      }}
      for (const row of document.querySelectorAll('[data-preset-row]')) {{
        row.hidden = row.dataset.presetRow !== device;
      }}
      for (const tab of document.querySelectorAll('[data-device-tab]')) {{
        tab.classList.toggle('active', tab.dataset.deviceTab === device);
      }}
      const playBtn = document.getElementById('playbtn');
      playBtn.style.display = (device === 'dinmeter') ? '' : 'none';
      document.getElementById('savethemebtn').style.display = '';  // saves both devices' theme
      if (device !== 'dinmeter' && animTimer) {{
        clearInterval(animTimer); animTimer = null;
        playBtn.textContent = 'Play';
        document.querySelector('.animbar').classList.remove('playing');
      }}
    }}

    function updateLabels(device) {{
      for (const control of controlsFor(device)) {{
        const label = document.querySelector('.controls[data-device="' + device + '"] [data-value-for="' + control.name + '"]');
        if (label) label.textContent = controlValue(control);
      }}
    }}

    function refresh() {{
      const device = deviceInput.value;
      const qs = new URLSearchParams();
      qs.set('device', device);
      for (const control of controlsFor(device)) {{
        qs.set(control.name, controlValue(control));
      }}
      updateLabels(device);
      const query = qs.toString();
      history.replaceState(null, '', '#' + query);
      screen.src = '/render?' + query + '&_t=' + Date.now();
    }}

    for (const tab of document.querySelectorAll('[data-device-tab]')) {{
      tab.addEventListener('click', () => {{
        showDevice(tab.dataset.deviceTab);
        refresh();
      }});
    }}

    for (const section of sections()) {{
      for (const control of section.querySelectorAll('[name]')) {{
        control.addEventListener('input', refresh);
      }}
    }}

    const PRESETS = {json.dumps(PRESETS)};
    const NATIVE = {json.dumps(NATIVE_WIDTH)};
    const ZOOM = {ZOOM_WIDTH};

    function applyPreset(device, name) {{
      const p = PRESETS[device] && PRESETS[device][name];
      if (!p) return;
      showDevice(device);
      for (const control of controlsFor(device)) {{
        if (!(control.name in p)) continue;
        if (control.type === 'checkbox') control.checked = (String(p[control.name]) === '1');
        else control.value = p[control.name];
      }}
      refresh();
    }}
    for (const btn of document.querySelectorAll('[data-preset]')) {{
      btn.addEventListener('click', () => applyPreset(btn.dataset.presetDevice, btn.dataset.preset));
    }}

    document.getElementById('exportbtn').addEventListener('click', () => {{
      const device = deviceInput.value;
      const a = document.getElementById('dl');
      const tag = device === 'dial'
        ? (form.elements['status'] ? form.elements['status'].value : 'render')
        : (form.elements['state'] ? form.elements['state'].value : 'render');
      a.href = screen.src;
      a.download = 'm5_' + device + '_' + String(tag).replace(/[^a-z0-9]+/gi, '_') + '.png';
      a.click();
    }});

    document.getElementById('sharebtn').addEventListener('click', async () => {{
      const btn = document.getElementById('sharebtn');
      try {{ await navigator.clipboard.writeText(location.href); btn.textContent = 'Zkopírováno'; }}
      catch (e) {{ btn.textContent = 'Odkaz v URL'; }}
      setTimeout(() => {{ btn.textContent = 'Odkaz'; }}, 1300);
    }});

    document.getElementById('allbtn').addEventListener('click', () => {{
      screen.src = '/contact?device=' + deviceInput.value + '&_t=' + Date.now();
    }});

    let actualSize = false;
    document.getElementById('onetoonebtn').addEventListener('click', () => {{
      actualSize = !actualSize;
      const device = deviceInput.value;
      screen.style.width = (actualSize ? NATIVE[device] : ZOOM) + 'px';
      document.getElementById('onetoonebtn').textContent = actualSize ? 'Zoom' : '1:1';
    }});

    document.getElementById('resetbtn').addEventListener('click', () => {{
      const device = deviceInput.value;
      const d = defaults[device];
      for (const control of controlsFor(device)) {{
        if (!Object.prototype.hasOwnProperty.call(d, control.name)) continue;
        if (control.type === 'checkbox') control.checked = Boolean(d[control.name]);
        else control.value = d[control.name];
      }}
      refresh();
    }});

    function animTick() {{
      const c = form.elements['elapsed_ms'];
      if (!c) return;
      const max = parseInt(c.max, 10), min = parseInt(c.min, 10);
      let v = parseInt(c.value, 10) + 60;
      if (v > max) v = min;
      c.value = v;
      refresh();
    }}
    document.getElementById('playbtn').addEventListener('click', () => {{
      const playBtn = document.getElementById('playbtn');
      const animBar = document.querySelector('.animbar');
      if (animTimer) {{
        clearInterval(animTimer); animTimer = null;
        playBtn.textContent = 'Play'; animBar.classList.remove('playing');
      }} else {{
        animTimer = setInterval(animTick, 150);
        playBtn.textContent = 'Pauza'; animBar.classList.add('playing');
      }}
    }});

    document.getElementById('savethemebtn').addEventListener('click', async () => {{
      const btn = document.getElementById('savethemebtn');
      const qs = new URLSearchParams();
      for (const c of form.querySelectorAll('[name^="t_"], [name^="td_"]')) {{
        qs.set(c.name, c.value);
      }}
      try {{
        const r = await fetch('/save_theme?' + qs.toString());
        btn.textContent = r.ok ? 'Uloženo ✓' : 'Chyba';
      }} catch (e) {{ btn.textContent = 'Chyba'; }}
      setTimeout(() => {{ btn.textContent = 'Uložit téma → firmware'; }}, 1600);
    }});

    setDefaults();
    applyHash();
    showDevice(deviceInput.value);
    refresh();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/render":
            try:
                params = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
                device = params.get("device", "dinmeter")
                with _RENDER_LOCK:
                    if device == "dial":
                        DIAL.apply_theme(_dial_theme_from_params(params))
                        image = DIAL.render(build_dial_view(params))
                    else:
                        view, page = build_dinmeter_view(params)
                        DIN.apply_theme(_theme_from_params(params))
                        image = DIN.render(view, page, hires=True)
                out = io.BytesIO()
                image.save(out, format="PNG")
                body = out.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                body = traceback.format_exc().encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        if parsed.path == "/save_theme":
            try:
                params = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
                raw_prev = open(_THEME_PATH, encoding="utf-8").read()
                data = json.loads(raw_prev)
                for key in THEME_COLOR_KEYS:
                    rgb = _hex_to_rgb(params.get(f"t_{key}", ""))
                    if rgb is not None:
                        data["colors"][key] = "0x%02X%02X%02X" % rgb
                for key in THEME_DIAL_KEYS:
                    rgb = _hex_to_rgb(params.get(f"td_{key}", ""))
                    if rgb is not None:
                        data.setdefault("dial", {})[key] = "0x%02X%02X%02X" % rgb
                with open(_THEME_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                import gen_firmware_theme
                try:
                    gen_firmware_theme.main()  # validates + regenerates both headers
                except Exception:
                    with open(_THEME_PATH, "w", encoding="utf-8") as f:  # roll back -> JSON + headers stay in sync
                        f.write(raw_prev)
                    raise
                with _RENDER_LOCK:
                    THEME["colors"] = data["colors"]
                    THEME["dial"] = data.get("dial", THEME.get("dial", {}))
                    DIN.apply_theme(THEME)
                    DIAL.apply_theme(THEME["dial"])
                body = b"saved tools/m5_theme.json + regenerated firmware headers (din-rx + dial-tx)"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                body = traceback.format_exc().encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        if parsed.path == "/contact":
            try:
                params = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
                device = params.get("device", "dinmeter")
                with _RENDER_LOCK:
                    if device == "dial":
                        DIAL.apply_theme(THEME.get("dial", {}))  # show the saved theme, not last /render
                        scenes = DIAL.scenes()
                        imgs = [(n, DIAL.render(scenes[n])) for n in CONTACT_KEYS["dial"] if n in scenes]
                    else:
                        DIN.apply_theme(THEME)
                        scenes = DIN.scenes()
                        imgs = [
                            (n, DIN.render(scenes[n][0], scenes[n][1]))
                            for n in CONTACT_KEYS["dinmeter"]
                            if n in scenes
                        ]
                out = io.BytesIO()
                _contact_sheet(imgs).save(out, format="PNG")
                body = out.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                body = traceback.format_exc().encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"M5 FE Studio: http://{HOST}:{PORT}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
