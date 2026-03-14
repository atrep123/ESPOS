"""Selection queries: search, select-by-type, select-all."""

from __future__ import annotations

from typing import Optional


def select_all(app) -> None:
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("Select all: empty scene.", ttl_sec=2.0)
        return
    app.state.selected = list(range(len(sc.widgets)))
    app.state.selected_idx = app.state.selected[0] if app.state.selected else None
    app.designer.selected_widget = app.state.selected_idx
    app._set_status(f"Selected {len(app.state.selected)} widget(s).", ttl_sec=2.0)


def search_widgets(app, query: str) -> None:
    """Select all widgets matching the query string (text, type, or icon_char)."""
    sc = app.state.current_scene()
    q = query.strip().lower()
    if not q:
        app._set_status("Search: empty query.", ttl_sec=2.0)
        return
    matches = []
    for i, w in enumerate(sc.widgets):
        text_val = str(getattr(w, "text", "") or "").lower()
        type_val = str(getattr(w, "type", "") or "").lower()
        icon_val = str(getattr(w, "icon_char", "") or "").lower()
        runtime_val = str(getattr(w, "runtime", "") or "").lower()
        if q in text_val or q in type_val or q in icon_val or q in runtime_val:
            matches.append(i)
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Found {len(matches)} widget(s) matching '{query.strip()}'.", ttl_sec=2.0)
    else:
        app._set_status(f"No widgets match '{query.strip()}'.", ttl_sec=2.0)
    app._mark_dirty()


def select_same_z(app) -> None:
    """Select all widgets on the same z-index as the first selected widget."""
    if not app.state.selected:
        app._set_status("Select z-layer: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    target_z = int(getattr(sc.widgets[first_idx], "z_index", 0) or 0)
    matches = [
        i for i, w in enumerate(sc.widgets) if int(getattr(w, "z_index", 0) or 0) == target_z
    ]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} widget(s) on z={target_z}.", ttl_sec=2.0)
    app._mark_dirty()


def select_same_style(app) -> None:
    """Select all widgets with the same style as the first selected widget."""
    if not app.state.selected:
        app._set_status("Select same style: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    target = str(getattr(sc.widgets[first_idx], "style", "default") or "default").lower()
    matches = [
        i
        for i, w in enumerate(sc.widgets)
        if str(getattr(w, "style", "default") or "default").lower() == target
    ]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} '{target}' style widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def select_hidden(app) -> None:
    """Select all hidden (invisible) widgets."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    matches = [i for i, w in enumerate(sc.widgets) if not getattr(w, "visible", True)]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} hidden widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No hidden widgets found.", ttl_sec=2.0)
    app._mark_dirty()


def select_same_type(app) -> None:
    """Select all widgets of the same type as the currently selected widget."""
    if not app.state.selected:
        app._set_status("Select same type: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    target_type = str(getattr(sc.widgets[first_idx], "type", "") or "").lower()
    matches = [
        i
        for i, w in enumerate(sc.widgets)
        if str(getattr(w, "type", "") or "").lower() == target_type
    ]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} '{target_type}' widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def select_locked(app) -> None:
    """Select all locked widgets, or all unlocked if current selection is all locked."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    # If current selection is all locked, select unlocked instead
    current_all_locked = app.state.selected and all(
        getattr(sc.widgets[i], "locked", False)
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    )
    if current_all_locked:
        matches = [i for i, w in enumerate(sc.widgets) if not getattr(w, "locked", False)]
        label = "unlocked"
    else:
        matches = [i for i, w in enumerate(sc.widgets) if getattr(w, "locked", False)]
        label = "locked"
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} {label} widget(s).", ttl_sec=2.0)
    else:
        app._set_status(f"No {label} widgets found.", ttl_sec=2.0)
    app._mark_dirty()


def select_overflow(app) -> None:
    """Select all widgets with text overflow issues."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    try:
        from .. import text_metrics
    except ImportError:  # pragma: no cover — module always available
        app._set_status("Overflow detection unavailable.", ttl_sec=2.0)
        return
    matches = []
    for i, w in enumerate(sc.widgets):
        txt = str(getattr(w, "text", "") or "")
        kind = str(getattr(w, "type", "") or "").lower()
        if kind == "icon":
            txt = str(getattr(w, "icon_char", "") or txt or "@")
        if txt.strip() and text_metrics.text_truncates_in_widget(w, txt):
            matches.append(i)
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} overflow widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No overflow issues found.", ttl_sec=2.0)
    app._mark_dirty()


def invert_selection(app) -> None:
    """Invert the current selection (select all not-selected widgets)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    current = set(app.state.selected)
    inverted = [i for i in range(len(sc.widgets)) if i not in current]
    if inverted:
        app._set_selection(inverted, anchor_idx=inverted[0])
        app._set_status(f"Inverted: {len(inverted)} widget(s) selected.", ttl_sec=2.0)
    else:
        app._set_selection([], anchor_idx=None)
        app._set_status("Inverted: nothing selected.", ttl_sec=2.0)
    app._mark_dirty()


def select_same_color(app) -> None:
    """Select all widgets matching fg+bg color of the first selected widget."""
    if not app.state.selected:
        app._set_status("Select same color: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    fg = str(getattr(ref, "color_fg", "") or "").lower()
    bg = str(getattr(ref, "color_bg", "") or "").lower()
    matches = [
        i
        for i, w in enumerate(sc.widgets)
        if str(getattr(w, "color_fg", "") or "").lower() == fg
        and str(getattr(w, "color_bg", "") or "").lower() == bg
    ]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} widget(s) with fg:{fg} bg:{bg}.", ttl_sec=2.0)
    app._mark_dirty()


def select_parent_panel(app) -> None:
    """Select the panel that geometrically contains the first selected widget."""
    if not app.state.selected:
        app._set_status("Select parent: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    idx = app.state.selected[0]
    if not (0 <= idx < len(sc.widgets)):
        return
    child = sc.widgets[idx]
    cx, cy = int(child.x), int(child.y)
    cw, ch = int(child.width), int(child.height)
    best_idx: Optional[int] = None
    best_area = float("inf")
    for i, w in enumerate(sc.widgets):
        if i == idx:
            continue
        if str(getattr(w, "type", "") or "").lower() != "panel":
            continue
        px, py = int(w.x), int(w.y)
        pw, ph = int(w.width), int(w.height)
        if px <= cx and py <= cy and px + pw >= cx + cw and py + ph >= cy + ch:
            area = pw * ph
            if area < best_area:
                best_area = area
                best_idx = i
    if best_idx is not None:
        app._set_selection([best_idx], anchor_idx=best_idx)
        name = str(getattr(sc.widgets[best_idx], "id", "") or f"#{best_idx}")
        app._set_status(f"Parent panel: {name}", ttl_sec=2.0)
    else:
        app._set_status("No enclosing panel found.", ttl_sec=2.0)
    app._mark_dirty()


def select_children(app) -> None:
    """Select all widgets inside the first selected panel."""
    if not app.state.selected:
        app._set_status("Select children: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    idx = app.state.selected[0]
    if not (0 <= idx < len(sc.widgets)):
        return
    panel = sc.widgets[idx]
    if str(getattr(panel, "type", "") or "").lower() != "panel":
        app._set_status("Select children: first selected is not a panel.", ttl_sec=2.0)
        return
    px, py = int(panel.x), int(panel.y)
    pw, ph = int(panel.width), int(panel.height)
    children = []
    for i, w in enumerate(sc.widgets):
        if i == idx:
            continue
        wx, wy = int(w.x), int(w.y)
        ww, wh = int(w.width), int(w.height)
        if wx >= px and wy >= py and wx + ww <= px + pw and wy + wh <= py + ph:
            children.append(i)
    if children:
        app._set_selection(children, anchor_idx=children[0])
        app._set_status(f"Selected {len(children)} child widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No children inside this panel.", ttl_sec=2.0)
    app._mark_dirty()


def select_same_size(app) -> None:
    """Select all widgets with the same width+height as the first selected."""
    if not app.state.selected:
        app._set_status("Select same size: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    tw, th = int(ref.width), int(ref.height)
    matches = [i for i, w in enumerate(sc.widgets) if int(w.width) == tw and int(w.height) == th]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} widget(s) sized {tw}x{th}.", ttl_sec=2.0)
    app._mark_dirty()


def select_bordered(app) -> None:
    """Select all widgets with border enabled, or without border if all selected have borders."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    current_all_bordered = app.state.selected and all(
        getattr(sc.widgets[i], "border", True)
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    )
    if current_all_bordered:
        matches = [i for i, w in enumerate(sc.widgets) if not getattr(w, "border", True)]
        label = "unbordered"
    else:
        matches = [i for i, w in enumerate(sc.widgets) if getattr(w, "border", True)]
        label = "bordered"
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} {label} widget(s).", ttl_sec=2.0)
    else:
        app._set_status(f"No {label} widgets found.", ttl_sec=2.0)
    app._mark_dirty()


def select_overlapping(app) -> None:
    """Select all widgets that overlap the bounding box of the current selection."""
    if not app.state.selected:
        app._set_status("Select overlapping: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    # Compute bounding box of current selection
    bx1 = min(int(sc.widgets[i].x) for i in valid)
    by1 = min(int(sc.widgets[i].y) for i in valid)
    bx2 = max(int(sc.widgets[i].x) + int(sc.widgets[i].width) for i in valid)
    by2 = max(int(sc.widgets[i].y) + int(sc.widgets[i].height) for i in valid)
    selected_set = set(valid)
    matches = list(valid)  # keep original selection
    for i, w in enumerate(sc.widgets):
        if i in selected_set:
            continue
        wx1, wy1 = int(w.x), int(w.y)
        wx2, wy2 = wx1 + int(w.width), wy1 + int(w.height)
        # Check rectangle overlap
        if wx1 < bx2 and wx2 > bx1 and wy1 < by2 and wy2 > by1:
            matches.append(i)
    new_count = len(matches) - len(valid)
    if new_count > 0:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Added {new_count} overlapping widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No overlapping widgets found.", ttl_sec=2.0)
    app._mark_dirty()


def select_all_panels(app) -> None:
    """Select all panel-type widgets in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    matches = [
        i for i, w in enumerate(sc.widgets) if str(getattr(w, "type", "") or "").lower() == "panel"
    ]
    if matches:
        app._set_selection(matches, anchor_idx=matches[0])
        app._set_status(f"Selected {len(matches)} panel(s).", ttl_sec=2.0)
    else:
        app._set_status("No panels found.", ttl_sec=2.0)
    app._mark_dirty()


def select_same_type_as_current(app) -> None:
    """Select all widgets of the same type as the first selected widget."""
    sc = app.state.current_scene()
    if not app.state.selected:
        app._set_status("Select by type: select a widget first.", ttl_sec=2.0)
        return
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    wtype = sc.widgets[first_idx].type
    matches = [i for i, w in enumerate(sc.widgets) if w.type == wtype]
    app._set_selection(matches, anchor_idx=first_idx)
    app._set_status(f"Selected {len(matches)} '{wtype}' widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def select_unlocked(app) -> None:
    """Select all non-locked widgets in the scene."""
    sc = app.state.current_scene()
    indices = [i for i, w in enumerate(sc.widgets) if not getattr(w, "locked", False)]
    if not indices:
        app._set_status("No unlocked widgets.", ttl_sec=2.0)
        return
    app.state.selected = indices
    app._set_status(f"Selected {len(indices)} unlocked widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def select_disabled(app) -> None:
    """Select all widgets with enabled=False."""
    sc = app.state.current_scene()
    indices = [i for i, w in enumerate(sc.widgets) if not getattr(w, "enabled", True)]
    if not indices:
        app._set_status("No disabled widgets.", ttl_sec=2.0)
        return
    app.state.selected = indices
    app._set_status(f"Selected {len(indices)} disabled widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def select_largest(app) -> None:
    """Select the single largest widget by area in the scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    best_i = 0
    best_area = 0
    for i, w in enumerate(sc.widgets):
        area = int(getattr(w, "width", 0) or 0) * int(getattr(w, "height", 0) or 0)
        if area > best_area:
            best_area = area
            best_i = i
    app.state.selected = [best_i]
    wtype = str(getattr(sc.widgets[best_i], "type", "") or "?")
    app._set_status(f"Largest: #{best_i} ({wtype}, {best_area}px²).", ttl_sec=2.0)
    app._mark_dirty()


def select_smallest(app) -> None:
    """Select the single smallest widget by area in the scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    best_i = 0
    best_area = float("inf")
    for i, w in enumerate(sc.widgets):
        area = int(getattr(w, "width", 1) or 1) * int(getattr(w, "height", 1) or 1)
        if area < best_area:
            best_area = area
            best_i = i
    app.state.selected = [best_i]
    wtype = str(getattr(sc.widgets[best_i], "type", "") or "?")
    app._set_status(f"Smallest: #{best_i} ({wtype}, {int(best_area)}px²).", ttl_sec=2.0)
    app._mark_dirty()
