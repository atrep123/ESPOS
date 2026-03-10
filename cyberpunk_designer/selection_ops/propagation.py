from __future__ import annotations


def copy_style(app) -> None:
    """Copy visual style from selected widget to style clipboard."""
    w = app.state.selected_widget()
    if w is None:
        app._set_status("Copy style: nothing selected.", ttl_sec=2.0)
        return
    app._style_clipboard = {
        "style": str(getattr(w, "style", "default") or "default"),
        "color_fg": str(getattr(w, "color_fg", "white") or "white"),
        "color_bg": str(getattr(w, "color_bg", "black") or "black"),
        "border": bool(getattr(w, "border", True)),
        "border_style": str(getattr(w, "border_style", "single") or "single"),
        "align": str(getattr(w, "align", "left") or "left"),
        "valign": str(getattr(w, "valign", "middle") or "middle"),
    }
    app._set_status("Style copied.", ttl_sec=1.5)


def paste_style(app) -> None:
    """Paste visual style from style clipboard onto selected widgets."""
    sc_data = getattr(app, "_style_clipboard", None)
    if not sc_data:
        app._set_status("Paste style: nothing copied.", ttl_sec=2.0)
        return
    if not app.state.selected:
        app._set_status("Paste style: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            for key, val in sc_data.items():
                setattr(w, key, val)
    app._set_status(f"Style applied to {len(app.state.selected)} widget(s).", ttl_sec=1.5)
    app._mark_dirty()


def propagate_border(app) -> None:
    """Copy border/border_style/border_width from first selected to rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate border: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    b = getattr(ref, "border", True)
    bs = str(getattr(ref, "border_style", "single") or "single")
    bw = getattr(ref, "border_width", None)
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            w.border = b
            w.border_style = bs
            if bw is not None:
                w.border_width = bw
            changed += 1
    app._set_status(f"Border propagated to {changed} widget(s). ({bs})", ttl_sec=2.0)
    app._mark_dirty()


def propagate_style(app) -> None:
    """Copy the style field from the first selected widget to the rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate style: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref_style = str(getattr(sc.widgets[first_idx], "style", "default") or "default")
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].style = ref_style
            changed += 1
    app._set_status(f"Style '{ref_style}' → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def clone_text(app) -> None:
    """Set all selected widgets' text to match the first selected."""
    if len(app.state.selected) < 2:
        app._set_status("Clone text: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref_text = str(getattr(sc.widgets[first_idx], "text", "") or "")
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].text = ref_text
            changed += 1
    app._set_status(f"Text '{ref_text[:20]}' → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_align(app) -> None:
    """Copy align+valign from first selected widget to the rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate align: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    al = str(getattr(ref, "align", "left") or "left")
    va = str(getattr(ref, "valign", "middle") or "middle")
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].align = al
            sc.widgets[idx].valign = va
            changed += 1
    app._set_status(f"Align {al}/{va} → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_colors(app) -> None:
    """Copy fg+bg colors from first selected widget to the rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate colors: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    fg = str(getattr(ref, "color_fg", "white") or "white")
    bg = str(getattr(ref, "color_bg", "black") or "black")
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].color_fg = fg
            sc.widgets[idx].color_bg = bg
            changed += 1
    app._set_status(f"Colors fg={fg} bg={bg} → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_value(app) -> None:
    """Copy value/min_value/max_value from first selected to the rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate value: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    val = int(getattr(ref, "value", 0) or 0)
    mn = int(getattr(ref, "min_value", 0) or 0)
    mx = int(getattr(ref, "max_value", 100) or 100)
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].value = val
            sc.widgets[idx].min_value = mn
            sc.widgets[idx].max_value = mx
            changed += 1
    app._set_status(f"Value {val} ({mn}..{mx}) → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_padding(app) -> None:
    """Copy padding_x/padding_y from first selected widget to the rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate padding: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    px = int(getattr(ref, "padding_x", 1) or 0)
    py = int(getattr(ref, "padding_y", 0) or 0)
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].padding_x = px
            sc.widgets[idx].padding_y = py
            changed += 1
    app._set_status(f"Padding ({px},{py}) → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_margin(app) -> None:
    """Copy margin_x/margin_y from first selected widget to the rest."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate margin: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    mx = int(getattr(ref, "margin_x", 0) or 0)
    my = int(getattr(ref, "margin_y", 0) or 0)
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].margin_x = mx
            sc.widgets[idx].margin_y = my
            changed += 1
    app._set_status(f"Margin ({mx},{my}) → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_appearance(app) -> None:
    """Copy all visual appearance from first selected to the rest.

    Copies: style, color_fg, color_bg, border, border_style, border_width,
    align, valign, padding_x/y, margin_x/y.
    """
    if len(app.state.selected) < 2:
        app._set_status("Propagate look: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    props = {
        "style": str(getattr(ref, "style", "default") or "default"),
        "color_fg": str(getattr(ref, "color_fg", "white") or "white"),
        "color_bg": str(getattr(ref, "color_bg", "black") or "black"),
        "border": bool(getattr(ref, "border", True)),
        "border_style": str(getattr(ref, "border_style", "single") or "single"),
        "border_width": getattr(ref, "border_width", None),
        "align": str(getattr(ref, "align", "left") or "left"),
        "valign": str(getattr(ref, "valign", "middle") or "middle"),
        "padding_x": int(getattr(ref, "padding_x", 1) or 0),
        "padding_y": int(getattr(ref, "padding_y", 0) or 0),
        "margin_x": int(getattr(ref, "margin_x", 0) or 0),
        "margin_y": int(getattr(ref, "margin_y", 0) or 0),
    }
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            for k, v in props.items():
                setattr(w, k, v)
            changed += 1
    app._set_status(f"Appearance → {changed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def propagate_text(app) -> None:
    """Set text of all selected widgets to the text of the first selected."""
    if len(app.state.selected) < 2:
        app._set_status("Propagate text: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    text = str(getattr(sc.widgets[first_idx], "text", "") or "")
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].text = text
            count += 1
    app._set_status(f'Set text "{text}" on {count} widget(s).', ttl_sec=2.0)
    app._mark_dirty()
