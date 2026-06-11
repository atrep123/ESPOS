"""Interactive local studio for the DinMeter receiver UI renderer."""

from __future__ import annotations

import io
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import preview_din_rx_render as P


HOST = "127.0.0.1"
PORT = int(os.environ.get("DINMETER_STUDIO_PORT", "8077"))


def _int(params: dict[str, str], name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(params.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _bool(params: dict[str, str], name: str, default: bool) -> bool:
    if name not in params:
        return default
    return params[name].lower() in ("1", "true")


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


def _parse_palette(params: dict[str, str], default: tuple) -> tuple:
    # 1..8 colour cells. pal_count picks how many of pal0..pal7 are used; each is "#rrggbb".
    count = _int(params, "pal_count", len(default), 1, 8)
    cells = []
    for i in range(count):
        rgb = _hex_to_rgb(params.get(f"pal{i}", ""))
        if rgb is None:
            rgb = default[i] if i < len(default) else (255, 255, 255)
        cells.append(rgb)
    return tuple(cells)


def build_view(params: dict[str, str]) -> tuple[P.View, str]:
    default_config = P.EffectConfig()
    default_view = P.View()

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

    config = P.EffectConfig(
        pre_trigger=_bool(params, "pre_trigger", default_config.pre_trigger),
        shape=_int(params, "shape", default_config.shape, P.EFFECT_SHAPE_SINE2, P.EFFECT_SHAPE_EXP),
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
        P.View(
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


DEFAULTS = {
    "state": "KLID",
    "shape": P.EFFECT_SHAPE_SINE2,
    "period_ms": P.DEFAULT_PERIOD_MS,
    "intensity": 100,
    "shape_param": 50,
    "repeat": P.DEFAULT_REPEAT,
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

# Palette defaults derived from the renderer's default View, so the colour pickers load
# with the real default palette (1..8 cells, each "#rrggbb").
_DEFAULT_PALETTE = P.View().palette
DEFAULTS["pal_count"] = len(_DEFAULT_PALETTE)
for _i in range(8):
    _c = _DEFAULT_PALETTE[_i] if _i < len(_DEFAULT_PALETTE) else (255, 255, 255)
    DEFAULTS[f"pal{_i}"] = "#%02x%02x%02x" % _c


def _view_to_params(view: P.View, page: str) -> dict:
    # Inverse of build_view: turn a renderer View into the studio's control values, so the
    # preset buttons stay in lock-step with scenes() (no hand-kept duplicate list).
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
        params[f"pal{i}"] = "#%02x%02x%02x" % col
    return params


# Quick-load presets derived straight from the renderer's scenes() (KLID/NABITO/PALI/STOP/edit).
PRESETS = {name: _view_to_params(view, page) for name, (view, page) in P.scenes().items()}


HTML = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DinMeter Studio</title>
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
      grid-template-columns: minmax(320px, 420px) 1fr;
      gap: 28px;
      align-items: start;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 18px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    form {{
      display: grid;
      gap: 12px;
    }}
    label {{
      display: grid;
      grid-template-columns: 132px 1fr 54px;
      gap: 10px;
      align-items: center;
      min-height: 32px;
      color: #d7dde4;
      font-size: 14px;
    }}
    select,
    input[type="range"] {{
      width: 100%;
    }}
    select {{
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
      margin-bottom: 14px;
    }}
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
      gap: 12px;
      margin-bottom: 14px;
    }}
    .animbar button {{
      padding: 7px 16px;
      border: 1px solid #3c4652;
      border-radius: 7px;
      background: #2e9e72;
      color: #07120b;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      min-width: 84px;
    }}
    .animbar.playing button {{ background: #ff8c00; color: #1a1206; }}
    .anim-speed {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #9fc2c8;
    }}
    .anim-speed input[type="range"] {{ width: 120px; accent-color: #4fd1c5; }}
    .value {{
      justify-self: end;
      min-width: 42px;
      color: #9fc2c8;
      font-variant-numeric: tabular-nums;
      text-align: right;
    }}
    .check-label {{
      grid-template-columns: 132px 18px 54px;
    }}
    .preview {{
      min-width: 0;
      overflow-x: auto;
    }}
    #screen {{
      width: 720px;
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
        max-width: 720px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>DinMeter Studio</h1>
      <div class="presets">
        <button type="button" data-preset="main_idle">KLID</button>
        <button type="button" data-preset="main_armed">NABITO</button>
        <button type="button" data-preset="main_firing">PÁLÍ</button>
        <button type="button" data-preset="main_stop">STOP</button>
        <button type="button" data-preset="main_editing">EDIT</button>
      </div>
      <div class="animbar">
        <button type="button" id="playbtn">Play</button>
        <label class="anim-speed">Rychlost
          <input id="anim_speed" type="range" min="1" max="20" step="1" value="6">
        </label>
        <button type="button" id="onetoonebtn">1:1</button>
        <button type="button" id="exportbtn">Export PNG</button>
        <button type="button" id="sharebtn">Odkaz</button>
        <button type="button" id="allbtn">Vše</button>
        <button type="button" id="resetbtn">Reset</button>
        <a id="dl" style="display:none"></a>
      </div>
      <form id="controls">
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
            <option value="{P.EFFECT_SHAPE_SINE2}">SIN2</option>
            <option value="{P.EFFECT_SHAPE_SQUARE}">HRANA</option>
            <option value="{P.EFFECT_SHAPE_SAWTOOTH}">PILA</option>
            <option value="{P.EFFECT_SHAPE_TRIANGLE}">TROJÚH</option>
            <option value="{P.EFFECT_SHAPE_EXP}">EXP</option>
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
        <label>Selected row
          <input name="selected_row" type="range" min="0" max="7" step="1">
          <span class="value" data-value-for="selected_row"></span>
        </label>
        <label>Elapsed
          <input name="elapsed_ms" type="range" min="0" max="3000" step="1">
          <span class="value" data-value-for="elapsed_ms"></span>
        </label>
        <label>Delay LED
          <input name="selected_delay_led" type="range" min="0" max="3" step="1">
          <span class="value" data-value-for="selected_delay_led"></span>
        </label>
        <label>LED 0
          <input name="led0" type="range" min="0" max="500" step="1">
          <span class="value" data-value-for="led0"></span>
        </label>
        <label>LED 1
          <input name="led1" type="range" min="0" max="500" step="1">
          <span class="value" data-value-for="led1"></span>
        </label>
        <label>LED 2
          <input name="led2" type="range" min="0" max="500" step="1">
          <span class="value" data-value-for="led2"></span>
        </label>
        <label>LED 3
          <input name="led3" type="range" min="0" max="500" step="1">
          <span class="value" data-value-for="led3"></span>
        </label>
        <label class="check-label">Pre trigger
          <input name="pre_trigger" type="checkbox">
          <span class="value" data-value-for="pre_trigger"></span>
        </label>
        <label class="check-label">Palette fade
          <input name="palette_fade" type="checkbox">
          <span class="value" data-value-for="palette_fade"></span>
        </label>
        <label class="check-label">Rows visible
          <input name="rows_visible" type="checkbox">
          <span class="value" data-value-for="rows_visible"></span>
        </label>
        <label class="check-label">Editing
          <input name="editing" type="checkbox">
          <span class="value" data-value-for="editing"></span>
        </label>
        <label>Palette N
          <input name="pal_count" type="range" min="1" max="8" step="1">
          <span class="value" data-value-for="pal_count"></span>
        </label>
        <div class="swatches">
          <input name="pal0" type="color" title="cell 1">
          <input name="pal1" type="color" title="cell 2">
          <input name="pal2" type="color" title="cell 3">
          <input name="pal3" type="color" title="cell 4">
          <input name="pal4" type="color" title="cell 5">
          <input name="pal5" type="color" title="cell 6">
          <input name="pal6" type="color" title="cell 7">
          <input name="pal7" type="color" title="cell 8">
        </div>
      </form>
    </section>
    <section class="preview">
      <img id="screen" alt="DinMeter render">
    </section>
  </main>
  <script>
    const defaults = {json.dumps(DEFAULTS)};
    const form = document.getElementById('controls');
    const screen = document.getElementById('screen');

    for (const control of form.elements) {{
      if (!control.name) continue;
      if (control.type === 'checkbox') {{
        control.checked = Boolean(defaults[control.name]);
      }} else if (Object.prototype.hasOwnProperty.call(defaults, control.name)) {{
        control.value = defaults[control.name];
      }}
    }}

    // Restore state from the URL hash so a bookmarked / shared link reopens the same config.
    function applyHash() {{
      if (!location.hash || location.hash.length < 2) return;
      const p = new URLSearchParams(location.hash.slice(1));
      for (const control of form.elements) {{
        if (!control.name || !p.has(control.name)) continue;
        if (control.type === 'checkbox') control.checked = (p.get(control.name) === '1');
        else control.value = p.get(control.name);
      }}
    }}
    applyHash();

    function controlValue(control) {{
      return control.type === 'checkbox' ? (control.checked ? '1' : '0') : control.value;
    }}

    function updateLabels() {{
      for (const control of form.elements) {{
        if (!control.name) continue;
        const label = document.querySelector(`[data-value-for="${{control.name}}"]`);
        if (label) label.textContent = controlValue(control);
      }}
    }}

    function refresh() {{
      const qs = new URLSearchParams();
      for (const control of form.elements) {{
        if (!control.name) continue;
        qs.set(control.name, controlValue(control));
      }}
      updateLabels();
      const query = qs.toString();
      history.replaceState(null, '', '#' + query);   // persist state in the URL (bookmark / share)
      screen.src = '/render?' + query + '&_t=' + Date.now();
    }}

    for (const control of form.elements) {{
      if (!control.name) continue;
      control.addEventListener('input', refresh);
    }}

    const presets = {json.dumps(PRESETS)};
    function applyPreset(name) {{
      const p = presets[name];
      if (!p) return;
      for (const control of form.elements) {{
        if (!control.name || !(control.name in p)) continue;
        if (control.type === 'checkbox') control.checked = (String(p[control.name]) === '1');
        else control.value = p[control.name];
      }}
      refresh();
    }}
    for (const btn of document.querySelectorAll('[data-preset]')) {{
      btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
    }}

    // Live playhead animation: auto-advance the elapsed_ms slider so the effect runs.
    // The playhead is only drawn in preview/fire, so this animates those states.
    let animTimer = null;
    const animBar = document.querySelector('.animbar');
    const playBtn = document.getElementById('playbtn');
    const animSpeed = document.getElementById('anim_speed');
    const elapsedCtrl = form.elements['elapsed_ms'];
    function animTick() {{
      const step = parseInt(animSpeed.value, 10) * 10;
      const max = parseInt(elapsedCtrl.max, 10);
      const min = parseInt(elapsedCtrl.min, 10);
      let v = parseInt(elapsedCtrl.value, 10) + step;
      if (v > max) v = min;
      elapsedCtrl.value = v;
      refresh();
    }}
    function togglePlay() {{
      if (animTimer) {{
        clearInterval(animTimer); animTimer = null;
        playBtn.textContent = 'Play'; animBar.classList.remove('playing');
      }} else {{
        animTimer = setInterval(animTick, 150);
        playBtn.textContent = 'Pauza'; animBar.classList.add('playing');
      }}
    }}
    playBtn.addEventListener('click', togglePlay);

    document.getElementById('exportbtn').addEventListener('click', () => {{
      const a = document.getElementById('dl');
      const st = form.elements['state'] ? form.elements['state'].value : 'render';
      a.href = screen.src;
      a.download = 'dinmeter_' + st + '.png';
      a.click();
    }});
    document.getElementById('sharebtn').addEventListener('click', async () => {{
      const btn = document.getElementById('sharebtn');
      try {{ await navigator.clipboard.writeText(location.href); btn.textContent = 'Zkopírováno'; }}
      catch (e) {{ btn.textContent = 'Odkaz v URL'; }}
      setTimeout(() => {{ btn.textContent = 'Odkaz'; }}, 1300);
    }});
    // Show all states at once (transient -- any control change returns to the single render).
    document.getElementById('allbtn').addEventListener('click', () => {{
      screen.src = '/contact?_t=' + Date.now();
    }});
    // 1:1 toggle: view the render at the device's real 240x135 size (judge on-device legibility).
    let actualSize = false;
    document.getElementById('onetoonebtn').addEventListener('click', () => {{
      actualSize = !actualSize;
      screen.style.width = actualSize ? '240px' : '720px';
      document.getElementById('onetoonebtn').textContent = actualSize ? '3x' : '1:1';
    }});
    // Reset every control back to its default.
    document.getElementById('resetbtn').addEventListener('click', () => {{
      for (const control of form.elements) {{
        if (!control.name) continue;
        if (control.type === 'checkbox') control.checked = Boolean(defaults[control.name]);
        else if (Object.prototype.hasOwnProperty.call(defaults, control.name)) control.value = defaults[control.name];
      }}
      refresh();
    }});

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
                params = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
                view, page = build_view(params)
                image = P.render(view, page, hires=True)
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

        if parsed.path == "/contact":
            try:
                scenes = P.scenes()
                names = ["main_idle", "main_armed", "main_firing", "main_stop", "main_editing", "led_delays"]
                imgs = [(n, P.render(scenes[n][0], scenes[n][1])) for n in names if n in scenes]
                sheet = P.contact_sheet(imgs)
                out = io.BytesIO()
                sheet.save(out, format="PNG")
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
    print(f"DinMeter Studio: http://{HOST}:{PORT}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
