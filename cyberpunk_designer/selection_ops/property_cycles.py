from __future__ import annotations

_GRAY4 = [f"#{v:02x}{v:02x}{v:02x}" for v in range(0, 256, 17)]



def cycle_style(app) -> None:
    """Cycle style on selected widgets: default → bold → inverse → highlight."""
    if not app.state.selected:
        app._set_status("Style: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    styles = ["default", "bold", "inverse", "highlight"]
    try:
        app.designer._save_state()
    except Exception:
        pass
    # Use the first selected widget's current style to determine next
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur = str(getattr(sc.widgets[first_idx], "style", "default") or "default")
    else:
        cur = "default"
    try:
        next_style = styles[(styles.index(cur) + 1) % len(styles)]
    except ValueError:
        next_style = "default"
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].style = next_style
    app._set_status(f"Style: {next_style}", ttl_sec=1.5)
    app._mark_dirty()


def toggle_visibility(app) -> None:
    """Toggle visible on selected widgets."""
    if not app.state.selected:
        app._set_status("Visibility: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    values = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            values.append(bool(getattr(sc.widgets[idx], "visible", True)))
    new_val = not all(values) if values else True
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].visible = new_val
    label = "visible" if new_val else "hidden"
    app._set_status(f"Visibility: {label}", ttl_sec=1.5)
    app._mark_dirty()


def cycle_widget_type(app) -> None:
    """Cycle widget type on selected widgets."""
    types = ["label", "button", "panel", "progressbar", "gauge", "slider",
             "checkbox", "chart", "icon"]
    if not app.state.selected:
        app._set_status("Type: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur = str(getattr(sc.widgets[first_idx], "type", "label") or "label")
    else:
        cur = "label"
    try:
        next_type = types[(types.index(cur) + 1) % len(types)]
    except ValueError:
        next_type = "label"
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].type = next_type
    app._set_status(f"Type: {next_type}", ttl_sec=1.5)
    app._mark_dirty()


def cycle_border_style(app) -> None:
    """Cycle border style on selected widgets."""
    styles = ["none", "single", "double", "rounded", "bold", "dashed"]
    if not app.state.selected:
        app._set_status("Border: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur = str(getattr(sc.widgets[first_idx], "border_style", "single") or "single")
    else:
        cur = "single"
    try:
        next_bs = styles[(styles.index(cur) + 1) % len(styles)]
    except ValueError:
        next_bs = "single"
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].border_style = next_bs
    app._set_status(f"Border: {next_bs}", ttl_sec=1.5)
    app._mark_dirty()


def cycle_color_preset(app) -> None:
    """Cycle through predefined color presets on selected widgets."""
    presets = [
        ("#f5f5f5", "#000000"),
        ("#f5f5f5", "#101010"),
        ("#e0e0e0", "#080808"),
        ("#b0b0b0", "#080808"),
        ("#000000", "#f5f5f5"),
        ("#101010", "#e0e0e0"),
    ]
    if not app.state.selected:
        app._set_status("Color: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur_fg = str(getattr(sc.widgets[first_idx], "color_fg", "") or "").lower()
        cur_bg = str(getattr(sc.widgets[first_idx], "color_bg", "") or "").lower()
    else:
        cur_fg, cur_bg = "", ""
    # Find current preset index
    preset_idx = 0
    for i, (fg, bg) in enumerate(presets):
        if cur_fg == fg.lower() and cur_bg == bg.lower():
            preset_idx = (i + 1) % len(presets)
            break
    fg, bg = presets[preset_idx]
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].color_fg = fg
            sc.widgets[idx].color_bg = bg
    app._set_status(f"Color: fg={fg} bg={bg}", ttl_sec=1.5)
    app._mark_dirty()


def toggle_border(app) -> None:
    """Toggle border on/off for selected widgets."""
    if not app.state.selected:
        app._set_status("Border: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    values = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            values.append(bool(getattr(sc.widgets[idx], "border", True)))
    new_val = not all(values) if values else True
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].border = new_val
    label = "on" if new_val else "off"
    app._set_status(f"Border: {label}", ttl_sec=1.5)
    app._mark_dirty()


def cycle_text_overflow(app) -> None:
    """Cycle text_overflow on selected widgets."""
    modes = ["ellipsis", "wrap", "clip", "auto"]
    if not app.state.selected:
        app._set_status("Overflow: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur = str(getattr(sc.widgets[first_idx], "text_overflow", "ellipsis") or "ellipsis")
    else:
        cur = "ellipsis"
    try:
        nxt = modes[(modes.index(cur) + 1) % len(modes)]
    except ValueError:
        nxt = "ellipsis"
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].text_overflow = nxt
    app._set_status(f"Overflow: {nxt}", ttl_sec=1.5)
    app._mark_dirty()


def cycle_align(app) -> None:
    """Cycle horizontal align on selected widgets."""
    aligns = ["left", "center", "right"]
    if not app.state.selected:
        app._set_status("Align: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur = str(getattr(sc.widgets[first_idx], "align", "left") or "left")
    else:
        cur = "left"
    try:
        nxt = aligns[(aligns.index(cur) + 1) % len(aligns)]
    except ValueError:
        nxt = "left"
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].align = nxt
    app._set_status(f"Align: {nxt}", ttl_sec=1.5)
    app._mark_dirty()


def cycle_valign(app) -> None:
    """Cycle vertical align on selected widgets."""
    valigns = ["top", "middle", "bottom"]
    if not app.state.selected:
        app._set_status("VAlign: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_idx = app.state.selected[0]
    if 0 <= first_idx < len(sc.widgets):
        cur = str(getattr(sc.widgets[first_idx], "valign", "middle") or "middle")
    else:
        cur = "middle"
    try:
        nxt = valigns[(valigns.index(cur) + 1) % len(valigns)]
    except ValueError:
        nxt = "middle"
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].valign = nxt
    app._set_status(f"VAlign: {nxt}", ttl_sec=1.5)
    app._mark_dirty()


def smart_edit(app) -> None:
    """Start editing the most relevant field based on selected widget type.

    label/button/textbox/panel/box → text, gauge/slider/progressbar → value,
    chart → data_points, icon → icon_char, checkbox/radiobutton → toggle checked.
    """
    if not app.state.selected:
        app._set_status("Smart edit: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    idx = app.state.selected[0]
    if not (0 <= idx < len(sc.widgets)):
        return
    w = sc.widgets[idx]
    wtype = str(getattr(w, "type", "") or "").lower()
    if wtype in ("gauge", "slider", "progressbar"):
        app._inspector_start_edit("value")
    elif wtype == "chart":
        app._inspector_start_edit("data_points")
    elif wtype == "icon":
        app._inspector_start_edit("icon_char")
    elif wtype in ("checkbox", "radiobutton"):
        # Toggle checked directly instead of opening editor
        try:
            app.designer._save_state()
        except Exception:
            pass
        for i in app.state.selected:
            if 0 <= i < len(sc.widgets):
                sc.widgets[i].checked = not sc.widgets[i].checked
        state = "checked" if w.checked else "unchecked"
        app._set_status(f"Toggled: {state}", ttl_sec=1.5)
        app._mark_dirty()
    else:
        # label, button, textbox, panel, box — edit text
        app._inspector_start_edit("text")


def adjust_value(app, delta: int) -> None:
    """Adjust the value property of selected widgets by delta, clamped to min/max."""
    if not app.state.selected:
        app._set_status("No selection.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    value_types = {"gauge", "slider", "progressbar"}
    applied = 0
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wtype = str(getattr(w, "type", "") or "").lower()
        if wtype not in value_types:
            continue
        mn = int(getattr(w, "min_value", 0) or 0)
        mx = int(getattr(w, "max_value", 100) or 100)
        cur = int(getattr(w, "value", 0) or 0)
        w.value = max(mn, min(mx, cur + delta))
        applied += 1
    if applied:
        sample = sc.widgets[app.state.selected[0]]
        app._set_status(f"Value: {sample.value}", ttl_sec=1.5)
        app._mark_dirty()
    else:
        app._set_status("No gauge/slider/progressbar selected.", ttl_sec=2.0)


def toggle_enabled(app) -> None:
    """Toggle the enabled property of selected widgets."""
    if not app.state.selected:
        app._set_status("Toggle enabled: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    new_val = not sc.widgets[first_idx].enabled
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].enabled = new_val
    label = "enabled" if new_val else "disabled"
    app._set_status(f"Widget: {label}", ttl_sec=1.5)
    app._mark_dirty()


def toggle_checked(app) -> None:
    """Toggle checked state for checkbox/radiobutton widgets."""
    if not app.state.selected:
        app._set_status("Toggle checked: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = [(i, sc.widgets[i]) for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not items:
        return
    applicable = [
        (i, w) for i, w in items
        if str(getattr(w, "type", "") or "").lower() in ("checkbox", "radiobutton")
    ]
    if not applicable:
        app._set_status("Toggle checked: select a checkbox or radio.", ttl_sec=2.0)
        return
    if any(getattr(w, "locked", False) for _, w in applicable):
        app._set_status("Some widgets are locked.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    count = 0
    for _idx, w in applicable:
        w.checked = not w.checked
        count += 1
    app._set_status(f"Toggled checked on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def cycle_gray_fg(app) -> None:
    """Cycle foreground color through 16-level grayscale palette."""
    if not app.state.selected:
        app._set_status("Gray FG: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    cur = str(getattr(sc.widgets[first_idx], "color_fg", "") or "").lower()
    idx = 0
    for i, g in enumerate(_GRAY4):
        if cur == g:
            idx = (i + 1) % len(_GRAY4)
            break
    new_c = _GRAY4[idx]
    try:
        app.designer._save_state()
    except Exception:
        pass
    for i in app.state.selected:
        if 0 <= i < len(sc.widgets):
            sc.widgets[i].color_fg = new_c
    app._set_status(f"FG={new_c} (gray {idx}/15)", ttl_sec=1.5)
    app._mark_dirty()


def cycle_gray_bg(app) -> None:
    """Cycle background color through 16-level grayscale palette."""
    if not app.state.selected:
        app._set_status("Gray BG: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    cur = str(getattr(sc.widgets[first_idx], "color_bg", "") or "").lower()
    idx = 0
    for i, g in enumerate(_GRAY4):
        if cur == g:
            idx = (i + 1) % len(_GRAY4)
            break
    new_c = _GRAY4[idx]
    try:
        app.designer._save_state()
    except Exception:
        pass
    for i in app.state.selected:
        if 0 <= i < len(sc.widgets):
            sc.widgets[i].color_bg = new_c
    app._set_status(f"BG={new_c} (gray {idx}/15)", ttl_sec=1.5)
    app._mark_dirty()


def outline_mode(app) -> None:
    """Set selected widgets to wireframe: border on, bg=#000000."""
    if not app.state.selected:
        app._set_status("Outline: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    for i in valid:
        w = sc.widgets[i]
        w.border = True
        w.color_bg = "#000000"
    app._set_status(f"Outline mode on {len(valid)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def outline_only(app) -> None:
    """Set border=True, color_bg='black' to make outline-style widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.border = True
        w.color_bg = "black"
        count += 1
    app._set_status(f"Outline-only on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def set_inverse_style(app) -> None:
    """Set style='inverse' on selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        if str(getattr(w, "style", "") or "") != "inverse":
            w.style = "inverse"
            count += 1
    app._set_status(f"Set inverse style on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def set_bold_style(app) -> None:
    """Set style='bold' on selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        if str(getattr(w, "style", "") or "") != "bold":
            w.style = "bold"
            count += 1
    app._set_status(f"Set bold style on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def set_default_style(app) -> None:
    """Reset style='default' on selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        if str(getattr(w, "style", "") or "") != "default":
            w.style = "default"
            count += 1
    app._set_status(f"Reset style on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()
