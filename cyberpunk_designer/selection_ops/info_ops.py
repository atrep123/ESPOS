"""Widget info, statistics, and measurement operations."""

from __future__ import annotations

from collections import Counter


def widget_info(app) -> None:
    """Show a summary of the first selected widget's properties in status bar."""
    if not app.state.selected:
        app._set_status("Info: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    idx = app.state.selected[0]
    if not (0 <= idx < len(sc.widgets)):
        return
    w = sc.widgets[idx]
    ty = str(getattr(w, "type", "?") or "?")
    txt = str(getattr(w, "text", "") or "")
    if len(txt) > 12:
        txt = txt[:12] + "\u2026"
    pos = f"{int(w.x)},{int(w.y)}"
    size = f"{int(w.width)}x{int(w.height)}"
    style = str(getattr(w, "style", "default") or "default")
    fg = str(getattr(w, "color_fg", "") or "")
    bg = str(getattr(w, "color_bg", "") or "")
    z = int(getattr(w, "z_index", 0) or 0)
    flags = []
    if getattr(w, "locked", False):
        flags.append("L")
    if not getattr(w, "visible", True):
        flags.append("H")
    if not getattr(w, "enabled", True):
        flags.append("D")
    if getattr(w, "border", True):
        flags.append("B")
    flag_str = "".join(flags) if flags else "-"
    info = f"#{idx} {ty} '{txt}' @{pos} {size} z{z} {style} fg:{fg} bg:{bg} [{flag_str}]"
    app._set_status(info, ttl_sec=6.0)
    app._mark_dirty()


def scene_stats(app) -> None:
    """Show scene statistics in the status bar."""
    sc = app.state.current_scene()
    total = len(sc.widgets)
    if total == 0:
        app._set_status(f"Scene '{sc.name}' {sc.width}x{sc.height}: empty.", ttl_sec=4.0)
        return
    types: Counter[str] = Counter()
    hidden = locked = disabled = 0
    for w in sc.widgets:
        types[str(getattr(w, "type", "?") or "?").lower()] += 1
        if not getattr(w, "visible", True):
            hidden += 1
        if getattr(w, "locked", False):
            locked += 1
        if not getattr(w, "enabled", True):
            disabled += 1
    type_str = " ".join(f"{k}:{v}" for k, v in types.most_common())
    flags = []
    if hidden:
        flags.append(f"{hidden}H")
    if locked:
        flags.append(f"{locked}L")
    if disabled:
        flags.append(f"{disabled}D")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    app._set_status(
        f"Scene '{sc.name}' {sc.width}x{sc.height}: {total}w {type_str}{flag_str}",
        ttl_sec=6.0,
    )


def measure_selection(app) -> None:
    """Show distances/gaps between selected widgets in the status bar."""
    if not app.state.selected:
        app._set_status("Measure: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    widgets = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            widgets.append(sc.widgets[idx])
    if not widgets:
        return
    if len(widgets) == 1:
        w = widgets[0]
        app._set_status(
            f"{getattr(w, 'id', '?')}: pos=({w.x},{w.y}) size={w.width}×{w.height}",
            ttl_sec=4.0,
        )
        return
    # Bounding box of selection
    xs = [w.x for w in widgets]
    ys = [w.y for w in widgets]
    x2s = [w.x + int(getattr(w, "width", 0) or 0) for w in widgets]
    y2s = [w.y + int(getattr(w, "height", 0) or 0) for w in widgets]
    bx, by = min(xs), min(ys)
    bx2, by2 = max(x2s), max(y2s)
    bw, bh = bx2 - bx, by2 - by
    if len(widgets) == 2:
        a, b = widgets
        aw = int(getattr(a, "width", 0) or 0)
        ah = int(getattr(a, "height", 0) or 0)
        bw2 = int(getattr(b, "width", 0) or 0)
        bh2 = int(getattr(b, "height", 0) or 0)
        gap_h = max(b.x - (a.x + aw), a.x - (b.x + bw2))
        gap_v = max(b.y - (a.y + ah), a.y - (b.y + bh2))
        app._set_status(
            f"2 sel: bbox {bw}×{bh} | gap h={gap_h} v={gap_v}",
            ttl_sec=4.0,
        )
    else:
        app._set_status(
            f"{len(widgets)} sel: bbox {bw}×{bh} @ ({bx},{by})",
            ttl_sec=4.0,
        )


def scene_overview(app) -> None:
    """Show summary of all scenes in the status bar."""
    scenes = app.designer.scenes
    parts = []
    total = 0
    for name, sc in scenes.items():
        n = len(sc.widgets)
        total += n
        parts.append(f"{name}({n})")
    summary = " | ".join(parts)
    app._set_status(f"{len(scenes)} scene(s), {total} widgets: {summary}", ttl_sec=5.0)


def widget_type_summary(app) -> None:
    """Show count of each widget type in the current scene."""
    sc = app.state.current_scene()
    counts = Counter(w.type for w in sc.widgets)
    if not counts:
        app._set_status("Scene is empty.", ttl_sec=2.0)
        return
    parts = [f"{t}:{n}" for t, n in counts.most_common()]
    app._set_status(f"{len(sc.widgets)} widgets — {', '.join(parts)}", ttl_sec=5.0)


def list_templates(app) -> None:
    """Show available template names in the status bar."""
    lib = getattr(app, "template_library", None)
    if lib is None or not hasattr(lib, "templates"):
        app._set_status("No template library.", ttl_sec=2.0)
        return
    names = list(lib.templates.keys()) if lib.templates else []
    if not names:
        app._set_status("No saved templates.", ttl_sec=2.0)
        return
    summary = ", ".join(names[:10])
    extra = f" (+{len(names) - 10} more)" if len(names) > 10 else ""
    app._set_status(f"Templates: {summary}{extra}", ttl_sec=6.0)


def toggle_focus_order_overlay(app) -> None:
    """Toggle display of focus navigation order numbers on widgets."""
    current = bool(getattr(app, "show_focus_order", False))
    app.show_focus_order = not current
    state = "ON" if app.show_focus_order else "OFF"
    app._set_status(f"Focus order overlay: {state}", ttl_sec=2.0)
    app._mark_dirty()


def zoom_to_selection(app) -> None:
    """Zoom and pan so the current selection fills the canvas."""
    if not app.state.selected:
        app._set_status("Zoom to sel: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    widgets = [sc.widgets[i] for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not widgets:
        return
    xs = [w.x for w in widgets]
    ys = [w.y for w in widgets]
    x2s = [w.x + int(getattr(w, "width", 8) or 8) for w in widgets]
    y2s = [w.y + int(getattr(w, "height", 8) or 8) for w in widgets]
    bx, by = min(xs), min(ys)
    bx2, by2 = max(x2s), max(y2s)
    bw = max(8, bx2 - bx)
    bh = max(8, by2 - by)
    margin = 16
    canvas = getattr(app, "layout", None)
    if canvas is None:
        return
    cr = canvas.canvas_rect
    cw = max(1, cr.width)
    ch = max(1, cr.height)
    sx = cw / (bw + margin * 2)
    sy = ch / (bh + margin * 2)
    new_scale = max(1, min(8, int(min(sx, sy))))
    app._set_scale(new_scale)
    cx = bx + bw // 2
    cy = by + bh // 2
    app.pan_offset_x = cr.width // 2 - cx * new_scale
    app.pan_offset_y = cr.height // 2 - cy * new_scale
    app._set_status(f"Zoom to sel: {len(widgets)} widget(s), scale={new_scale}.", ttl_sec=2.0)
    app._mark_dirty()
