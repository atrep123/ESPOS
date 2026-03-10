from __future__ import annotations

from typing import Optional

from ui_designer import WidgetConfig

from .constants import GRID, snap
from .text_metrics import DEVICE_CHAR_H, DEVICE_CHAR_W, is_device_profile, wrap_text_chars


def fit_selection_to_text(app) -> None:
    """Grow selected widgets so their text fits without clipping/ellipsis (best-effort)."""
    if not getattr(app.state, "selected", None):
        app._set_status("Fit Text: no selection.", ttl_sec=2.0)
        return

    sc = app.state.current_scene()
    pad = max(2, int(getattr(app, "pixel_padding", 0)) // 2)
    line_h = max(1, int(app.pixel_font.get_height()))
    use_device = is_device_profile(getattr(app, "hardware_profile", None))
    if use_device:
        line_h = DEVICE_CHAR_H

    def _snap_up(v: int, g: int = GRID) -> int:
        v = int(v)
        g = int(g)
        return g * ((v + g - 1) // g)

    def _parse_max_lines(w: WidgetConfig) -> Optional[int]:
        try:
            raw = getattr(w, "max_lines", None)
            if raw is None or str(raw).strip() == "":
                return None
            v = int(raw)
            return v if v > 0 else None
        except Exception:
            return None

    saved = False
    changed = 0
    skipped_locked = 0

    for idx in list(app.state.selected):
        if not (0 <= int(idx) < len(sc.widgets)):
            continue
        w = sc.widgets[int(idx)]
        if bool(getattr(w, "locked", False)):
            skipped_locked += 1
            continue

        kind = str(getattr(w, "type", "") or "").lower()
        if kind == "icon":
            text = str(getattr(w, "icon_char", "") or getattr(w, "text", "") or "@")
        else:
            text = str(getattr(w, "text", "") or "")
        if not text.strip():
            continue

        overflow = str(getattr(w, "text_overflow", "ellipsis") or "ellipsis").strip().lower()
        if overflow not in {"ellipsis", "wrap", "clip", "auto"}:
            overflow = "ellipsis"

        cur_w = max(GRID, int(getattr(w, "width", GRID) or GRID))
        cur_h = max(GRID, int(getattr(w, "height", GRID) or GRID))

        needed_w = cur_w
        needed_h = cur_h

        if kind == "checkbox":
            flat = text.replace("\t", " ").replace("\n", " ").strip()
            if use_device:
                txt_w = len(flat) * DEVICE_CHAR_W
                needed_w = max(cur_w, int(txt_w + 10))
                needed_h = max(cur_h, int(max(line_h, 6) + 2))
            else:
                txt_w = app._text_width_px(flat)
                needed_w = max(cur_w, int(txt_w + GRID + pad * 2))
                needed_h = max(cur_h, int(max(line_h, GRID + pad * 2)))
        else:
            wrap_mode = overflow in {"wrap", "auto"}
            if wrap_mode:
                if use_device:
                    avail_w = max(1, int(cur_w - 2 * (1 + (1 if bool(getattr(w, "border", True)) else 0))))
                    max_chars = avail_w // DEVICE_CHAR_W
                else:
                    avail_w = max(1, int(cur_w - pad * 2))
                max_lines = _parse_max_lines(w) or 9999
                if use_device:
                    lines, _trunc = wrap_text_chars(text, max_chars=max(1, max_chars), max_lines=max_lines, ellipsis="...")
                    line_count = max(1, len(lines))
                else:
                    lines = app._wrap_text_px(text, max_width_px=avail_w, max_lines=max_lines)
                    line_count = max(1, len(lines))
                if use_device:
                    needed_h = max(cur_h, int(line_count * DEVICE_CHAR_H + 2 * (1 + (1 if bool(getattr(w, "border", True)) else 0))))
                else:
                    needed_h = max(cur_h, int(line_count * line_h + pad * 2))
            else:
                flat = text.replace("\t", " ").replace("\n", " ").strip()
                if use_device:
                    txt_w = len(flat) * DEVICE_CHAR_W
                    inset = 1 if bool(getattr(w, "border", True)) else 0
                    needed_w = max(cur_w, int(txt_w + (inset + 1) * 2))
                    needed_h = max(cur_h, int(DEVICE_CHAR_H + (inset + 1) * 2))
                else:
                    txt_w = app._text_width_px(flat)
                    needed_w = max(cur_w, int(txt_w + pad * 2))
                    needed_h = max(cur_h, int(line_h + pad * 2))

        sc_w = max(GRID, int(getattr(sc, "width", GRID) or GRID))
        sc_h = max(GRID, int(getattr(sc, "height", GRID) or GRID))

        new_w = max(GRID, min(sc_w, int(needed_w)))
        new_h = max(GRID, min(sc_h, int(needed_h)))

        if app.snap_enabled:
            max_w_grid = max(GRID, (sc_w // GRID) * GRID)
            max_h_grid = max(GRID, (sc_h // GRID) * GRID)
            new_w = min(max_w_grid, max(GRID, _snap_up(new_w)))
            new_h = min(max_h_grid, max(GRID, _snap_up(new_h)))

        new_w = max(GRID, min(sc_w, int(new_w)))
        new_h = max(GRID, min(sc_h, int(new_h)))

        x = int(getattr(w, "x", 0) or 0)
        y = int(getattr(w, "y", 0) or 0)
        if app.snap_enabled:
            x = snap(x)
            y = snap(y)

        max_x = max(0, sc_w - new_w)
        max_y = max(0, sc_h - new_h)
        x = max(0, min(max_x, x))
        y = max(0, min(max_y, y))

        if (int(getattr(w, "x", 0) or 0), int(getattr(w, "y", 0) or 0), cur_w, cur_h) == (x, y, new_w, new_h):
            continue

        if not saved:
            try:
                app.designer._save_state()
            except Exception:
                pass
            saved = True

        w.x = x
        w.y = y
        w.width = new_w
        w.height = new_h
        changed += 1

    if changed:
        msg = f"Fit Text: updated {changed} widget(s)."
        if skipped_locked:
            msg += f" Skipped locked: {skipped_locked}."
        app._set_status(msg, ttl_sec=3.0)
        app._mark_dirty()
    else:
        if skipped_locked:
            app._set_status(f"Fit Text: nothing to change (locked: {skipped_locked}).", ttl_sec=2.5)
        else:
            app._set_status("Fit Text: nothing to change.", ttl_sec=2.0)
