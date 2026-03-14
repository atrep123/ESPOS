"""Widget visibility, locking, and enabling operations."""

from __future__ import annotations

from .core import save_undo


def hide_unselected(app) -> None:
    """Hide all widgets that are NOT in the current selection (isolation mode)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    save_undo(app)
    selected_set = set(app.state.selected)
    hidden = 0
    for i, w in enumerate(sc.widgets):
        if i not in selected_set:
            if getattr(w, "visible", True):
                w.visible = False
                hidden += 1
    app._set_status(f"Isolated: hid {hidden} unselected widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def show_all_widgets(app) -> None:
    """Unhide every hidden widget in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    save_undo(app)
    shown = 0
    for w in sc.widgets:
        if not getattr(w, "visible", True):
            w.visible = True
            shown += 1
    if shown:
        app._set_status(f"Showed {shown} hidden widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No hidden widgets to show.", ttl_sec=2.0)
    app._mark_dirty()


def unlock_all_widgets(app) -> None:
    """Unlock every locked widget in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    save_undo(app)
    unlocked = 0
    for w in sc.widgets:
        if getattr(w, "locked", False):
            w.locked = False
            unlocked += 1
    if unlocked:
        app._set_status(f"Unlocked {unlocked} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No locked widgets to unlock.", ttl_sec=2.0)
    app._mark_dirty()


def toggle_all_borders(app) -> None:
    """Toggle border on all widgets in scene (all on -> all off, or all on)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    save_undo(app)
    all_bordered = all(getattr(w, "border", True) for w in sc.widgets)
    new_val = not all_bordered
    for w in sc.widgets:
        w.border = new_val
    label = "ON" if new_val else "OFF"
    app._set_status(f"All borders {label} ({len(sc.widgets)} widgets).", ttl_sec=2.0)
    app._mark_dirty()


def enable_all_widgets(app) -> None:
    """Enable every disabled widget in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    save_undo(app)
    enabled = 0
    for w in sc.widgets:
        if not getattr(w, "enabled", True):
            w.enabled = True
            enabled += 1
    if enabled:
        app._set_status(f"Enabled {enabled} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No disabled widgets to enable.", ttl_sec=2.0)
    app._mark_dirty()


def toggle_all_checked(app) -> None:
    """Toggle the checked state of all selected checkbox/radiobutton widgets."""
    if not app.state.selected:
        app._set_status("Toggle checked: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wtype = str(getattr(w, "type", "") or "").lower()
        if wtype in ("checkbox", "radiobutton"):
            w.checked = not getattr(w, "checked", False)
            count += 1
    if count:
        app._set_status(f"Toggled checked on {count} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No checkbox/radiobutton in selection.", ttl_sec=2.0)
    app._mark_dirty()


def delete_hidden_widgets(app) -> None:
    """Delete all invisible (visible=False) widgets from the current scene."""
    sc = app.state.current_scene()
    hidden = [i for i, w in enumerate(sc.widgets) if not getattr(w, "visible", True)]
    if not hidden:
        app._set_status("No hidden widgets to delete.", ttl_sec=2.0)
        return
    app._save_undo_state()
    for idx in reversed(hidden):
        sc.widgets.pop(idx)
    app.state.selected = []
    app.state.selected_idx = None
    app._set_status(f"Deleted {len(hidden)} hidden widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def delete_offscreen_widgets(app) -> None:
    """Delete widgets that are completely outside the scene bounds."""
    sc = app.state.current_scene()
    sw, sh = int(sc.width), int(sc.height)
    offscreen = []
    for i, w in enumerate(sc.widgets):
        wx = int(getattr(w, "x", 0) or 0)
        wy = int(getattr(w, "y", 0) or 0)
        ww = int(getattr(w, "width", 0) or 0)
        wh = int(getattr(w, "height", 0) or 0)
        # Completely outside
        if wx + ww <= 0 or wy + wh <= 0 or wx >= sw or wy >= sh:
            offscreen.append(i)
    if not offscreen:
        app._set_status("No offscreen widgets to delete.", ttl_sec=2.0)
        return
    app._save_undo_state()
    for idx in reversed(offscreen):
        sc.widgets.pop(idx)
    app.state.selected = []
    app.state.selected_idx = None
    app._set_status(f"Deleted {len(offscreen)} offscreen widget(s).", ttl_sec=2.0)
    app._mark_dirty()
