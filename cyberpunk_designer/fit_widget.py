"""Auto-fit widget size to its text content."""

from __future__ import annotations

from typing import Optional

from ui_designer import WidgetConfig

from .constants import GRID, safe_save_state, snap
from .text_metrics import DEVICE_CHAR_H, DEVICE_CHAR_W, is_device_profile, wrap_text_chars


def fit_selection_to_widget(app) -> None:
    """Resize selected widgets to tightly fit their content (best-effort).

    Unlike Fit Text (grow-only), this may shrink or grow.
    """
    if not getattr(app.state, "selected", None):
        app._set_status("Fit Widget: no selection.", ttl_sec=2.0)
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
        except (ValueError, TypeError):
            return None

    saved = False
    changed = 0
    skipped_locked = 0
    skipped_no_text = 0

    sc_w = max(GRID, int(getattr(sc, "width", GRID) or GRID))
    sc_h = max(GRID, int(getattr(sc, "height", GRID) or GRID))

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
            skipped_no_text += 1
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
                needed_w = int(txt_w + 10)
                needed_h = int(max(line_h, 6) + 2)
            else:
                txt_w = app._text_width_px(flat)
                needed_w = int(txt_w + GRID + pad * 2)
                needed_h = int(max(line_h, GRID) + pad * 2)
        elif kind == "list":
            items = list(getattr(w, "items", None) or [])
            if not items:
                items = text.split("\n") if "\n" in text else [text]
            items = [it for it in items if it.strip()]
            n = max(1, len(items))
            border_inset = 1 if bool(getattr(w, "border", True)) else 0
            if use_device:
                max_item_w = max((len(it) * DEVICE_CHAR_W for it in items), default=DEVICE_CHAR_W)
                needed_w = int(max_item_w + (border_inset + 1) * 2)
                needed_h = int(n * DEVICE_CHAR_H + (border_inset + 1) * 2)
            else:
                max_item_w = max(
                    (app._text_width_px(it) for it in items), default=line_h
                )
                needed_w = int(max_item_w + pad * 2)
                needed_h = int(n * line_h + pad * 2)
        elif kind == "toggle":
            flat = text.replace("\t", " ").replace("\n", " ").strip()
            track_h = max(line_h, DEVICE_CHAR_H if use_device else GRID)
            track_w = track_h * 2
            if use_device:
                txt_w = len(flat) * DEVICE_CHAR_W if flat else 0
                needed_w = int(track_w + (txt_w + 4 if txt_w else 0) + 4)
                needed_h = int(track_h + 4)
            else:
                txt_w = app._text_width_px(flat) if flat else 0
                needed_w = int(track_w + (txt_w + pad if txt_w else 0) + pad * 2)
                needed_h = int(track_h + pad * 2)
        else:
            wrap_mode = overflow in {"wrap", "auto"}
            max_chars = 1
            if wrap_mode:
                if use_device:
                    avail_w = max(
                        1, int(cur_w - 2 * (1 + (1 if bool(getattr(w, "border", True)) else 0)))
                    )
                    max_chars = avail_w // DEVICE_CHAR_W
                else:
                    avail_w = max(1, int(cur_w - pad * 2))
                max_lines = _parse_max_lines(w) or 9999
                if use_device:
                    lines, _trunc = wrap_text_chars(
                        text, max_chars=max(1, max_chars), max_lines=max_lines, ellipsis="..."
                    )
                    line_count = max(1, len(lines))
                    needed_h = int(
                        line_count * DEVICE_CHAR_H
                        + 2 * (1 + (1 if bool(getattr(w, "border", True)) else 0))
                    )
                else:
                    lines = app._wrap_text_px(text, max_width_px=avail_w, max_lines=max_lines)
                    line_count = max(1, len(lines))
                    needed_h = int(line_count * line_h + pad * 2)
            else:
                flat = text.replace("\t", " ").replace("\n", " ").strip()
                if use_device:
                    txt_w = len(flat) * DEVICE_CHAR_W
                    inset = 1 if bool(getattr(w, "border", True)) else 0
                    needed_w = int(txt_w + (inset + 1) * 2)
                    needed_h = int(DEVICE_CHAR_H + (inset + 1) * 2)
                else:
                    txt_w = app._text_width_px(flat)
                    needed_w = int(txt_w + pad * 2)
                    needed_h = int(line_h + pad * 2)

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

        if (int(getattr(w, "x", 0) or 0), int(getattr(w, "y", 0) or 0), cur_w, cur_h) == (
            x,
            y,
            new_w,
            new_h,
        ):
            continue

        if not saved:
            safe_save_state(app.designer)
            saved = True

        w.x = x
        w.y = y
        w.width = new_w
        w.height = new_h
        changed += 1

    if changed:
        msg = f"Fit Widget: updated {changed} widget(s)."
        if skipped_locked:
            msg += f" Skipped locked: {skipped_locked}."
        if skipped_no_text:
            msg += f" Skipped empty text: {skipped_no_text}."
        app._set_status(msg, ttl_sec=3.0)
        app._mark_dirty()
    else:
        if skipped_locked or skipped_no_text:
            app._set_status(
                f"Fit Widget: nothing to change (locked: {skipped_locked}, empty: {skipped_no_text}).",
                ttl_sec=2.5,
            )
        else:
            app._set_status("Fit Widget: nothing to change.", ttl_sec=2.0)
