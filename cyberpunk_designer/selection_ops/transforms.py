from __future__ import annotations

from ..constants import GRID, snap
from .core import selection_bounds


def move_selection(app, dx: int, dy: int) -> None:
    if not app.state.selected:
        return
    sc = app.state.current_scene()
    if any(
        bool(getattr(sc.widgets[i], "locked", False))
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    ):
        app._set_status("Selection contains locked widget(s).", ttl_sec=2.0)
        return
    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return
    new_x = int(bounds.x) + int(dx)
    new_y = int(bounds.y) + int(dy)
    if app.snap_enabled:
        new_x = snap(new_x)
        new_y = snap(new_y)
    max_x = max(0, int(sc.width) - int(bounds.width))
    max_y = max(0, int(sc.height) - int(bounds.height))
    new_x = max(0, min(max_x, new_x))
    new_y = max(0, min(max_y, new_y))
    if app.snap_enabled:
        new_x = snap(new_x)
        new_y = snap(new_y)
        new_x = max(0, min(max_x, new_x))
        new_y = max(0, min(max_y, new_y))
    ddx = int(new_x - int(bounds.x))
    ddy = int(new_y - int(bounds.y))
    if ddx == 0 and ddy == 0:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.x = int(getattr(w, "x", 0) or 0) + ddx
        w.y = int(getattr(w, "y", 0) or 0) + ddy
    app._mark_dirty()


def resize_selection_to(app, new_w: int, new_h: int) -> bool:
    """Resize the current selection bounding box, scaling children proportionally."""
    if not app.state.selected:
        return False
    sc = app.state.current_scene()
    if any(
        bool(getattr(sc.widgets[i], "locked", False))
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    ):
        app._set_status("Selection contains locked widget(s).", ttl_sec=2.0)
        return False

    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return False

    new_w = int(new_w)
    new_h = int(new_h)
    if app.snap_enabled:
        new_w = max(GRID, snap(new_w))
        new_h = max(GRID, snap(new_h))
    else:
        new_w = max(GRID, new_w)
        new_h = max(GRID, new_h)

    max_w = max(GRID, int(sc.width) - int(bounds.x))
    max_h = max(GRID, int(sc.height) - int(bounds.y))
    new_w = max(GRID, min(max_w, new_w))
    new_h = max(GRID, min(max_h, new_h))

    if int(bounds.width) <= 0 or int(bounds.height) <= 0:
        return False

    sx = float(new_w) / float(int(bounds.width))
    sy = float(new_h) / float(int(bounds.height))

    try:
        app.designer._save_state()
    except Exception:
        pass

    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ox = int(getattr(w, "x", 0) or 0)
        oy = int(getattr(w, "y", 0) or 0)
        ow = max(GRID, int(getattr(w, "width", GRID) or GRID))
        oh = max(GRID, int(getattr(w, "height", GRID) or GRID))

        rel_x = float(ox - int(bounds.x))
        rel_y = float(oy - int(bounds.y))
        nx = float(int(bounds.x)) + rel_x * sx
        ny = float(int(bounds.y)) + rel_y * sy
        nw = float(ow) * sx
        nh = float(oh) * sy

        ix = int(round(nx))
        iy = int(round(ny))
        iw = max(GRID, int(round(nw)))
        ih = max(GRID, int(round(nh)))
        if app.snap_enabled:
            ix = snap(ix)
            iy = snap(iy)
            iw = max(GRID, snap(iw))
            ih = max(GRID, snap(ih))

        max_ix = max(0, int(sc.width) - iw)
        max_iy = max(0, int(sc.height) - ih)
        ix = max(0, min(max_ix, ix))
        iy = max(0, min(max_iy, iy))

        w.x = ix
        w.y = iy
        w.width = iw
        w.height = ih

    app._mark_dirty()
    return True


def mirror_selection(app, axis: str) -> None:
    """Mirror selected widgets along horizontal or vertical axis.

    axis: 'h' = flip horizontally (left-right), 'v' = flip vertically (top-bottom).
    """
    if not app.state.selected:
        app._set_status("Mirror: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wx = int(getattr(w, "x", 0) or 0)
        wy = int(getattr(w, "y", 0) or 0)
        ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
        wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
        if axis == "h":
            w.x = int(bounds.x) + (int(bounds.right) - (wx + ww))
        else:
            w.y = int(bounds.y) + (int(bounds.bottom) - (wy + wh))
    label = "horizontal" if axis == "h" else "vertical"
    app._set_status(f"Mirror: {label}", ttl_sec=1.5)
    app._mark_dirty()


def swap_fg_bg(app) -> None:
    """Swap foreground and background colors of selected widgets."""
    if not app.state.selected:
        app._set_status("Swap colors: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            w.color_fg, w.color_bg = w.color_bg, w.color_fg
    app._set_status("Swapped fg/bg colors.", ttl_sec=1.5)
    app._mark_dirty()


def make_full_width(app) -> None:
    """Set selected widgets to full scene width (x=0, width=scene_width)."""
    if not app.state.selected:
        app._set_status("Full width: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = [(i, sc.widgets[i]) for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not items:
        return
    if any(getattr(w, "locked", False) for _, w in items):
        app._set_status("Some widgets are locked.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    sw = int(getattr(sc, "width", 256) or 256)
    for _idx, w in items:
        w.x = 0
        w.width = sw
    app._set_status(f"Full width ({sw}px) on {len(items)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def make_full_height(app) -> None:
    """Set selected widgets to full scene height (y=0, height=scene_height)."""
    if not app.state.selected:
        app._set_status("Full height: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = [(i, sc.widgets[i]) for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not items:
        return
    if any(getattr(w, "locked", False) for _, w in items):
        app._set_status("Some widgets are locked.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    sh = int(getattr(sc, "height", 128) or 128)
    for _idx, w in items:
        w.y = 0
        w.height = sh
    app._set_status(f"Full height ({sh}px) on {len(items)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def swap_dimensions(app) -> None:
    """Swap width and height of selected widgets."""
    if not app.state.selected:
        app._set_status("Swap dims: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = [(i, sc.widgets[i]) for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not items:
        return
    if any(getattr(w, "locked", False) for _, w in items):
        app._set_status("Some widgets are locked.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    for _idx, w in items:
        w.width, w.height = w.height, w.width
    app._set_status(f"Swapped W/H on {len(items)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def move_selection_to_origin(app) -> None:
    """Move the selection's bounding box to the top-left corner (0,0)."""
    if not app.state.selected:
        app._set_status("Move to origin: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    min_x = min(int(sc.widgets[i].x) for i in valid)
    min_y = min(int(sc.widgets[i].y) for i in valid)
    for i in valid:
        w = sc.widgets[i]
        w.x = int(w.x) - min_x
        w.y = int(w.y) - min_y
    app._set_status(
        f"Moved {len(valid)} widget(s) to origin (offset {min_x},{min_y}).", ttl_sec=2.0
    )
    app._mark_dirty()


def swap_positions(app) -> None:
    """Swap x,y positions of exactly two selected widgets."""
    if len(app.state.selected) != 2:
        app._set_status("Swap: select exactly 2 widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    a, b = app.state.selected
    if not (0 <= a < len(sc.widgets) and 0 <= b < len(sc.widgets)):
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    wa, wb = sc.widgets[a], sc.widgets[b]
    wa.x, wb.x = int(wb.x), int(wa.x)
    wa.y, wb.y = int(wb.y), int(wa.y)
    app._set_status("Swapped positions.", ttl_sec=2.0)
    app._mark_dirty()


def flip_vertical(app) -> None:
    """Flip selected widgets vertically — mirror positions around group center Y."""
    if not app.state.selected:
        app._set_status("Flip V: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    min_y = min(int(sc.widgets[i].y) for i in valid)
    max_y = max(int(sc.widgets[i].y) + int(sc.widgets[i].height or 0) for i in valid)
    center_y = min_y + max_y
    for i in valid:
        w = sc.widgets[i]
        w.y = center_y - int(w.y) - int(w.height or 0)
    app._set_status(f"Flipped {len(valid)} widget(s) vertically.", ttl_sec=2.0)
    app._mark_dirty()


def swap_content(app) -> None:
    """Swap text, value, and checked between exactly 2 widgets."""
    if len(app.state.selected) != 2:
        app._set_status("Swap content: select exactly 2.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    a, b = app.state.selected
    if not (0 <= a < len(sc.widgets) and 0 <= b < len(sc.widgets)):
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    wa, wb = sc.widgets[a], sc.widgets[b]
    wa.text, wb.text = str(getattr(wb, "text", "") or ""), str(getattr(wa, "text", "") or "")
    wa.value, wb.value = int(getattr(wb, "value", 0) or 0), int(getattr(wa, "value", 0) or 0)
    wa.checked, wb.checked = (
        bool(getattr(wb, "checked", False)),
        bool(getattr(wa, "checked", False)),
    )
    wa.icon_char, wb.icon_char = (
        str(getattr(wb, "icon_char", "") or ""),
        str(getattr(wa, "icon_char", "") or ""),
    )
    app._set_status("Swapped content.", ttl_sec=2.0)
    app._mark_dirty()


def flip_horizontal(app) -> None:
    """Flip selected widgets horizontally — mirror X positions around group center."""
    if not app.state.selected:
        app._set_status("Flip H: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    min_x = min(int(sc.widgets[i].x) for i in valid)
    max_x = max(int(sc.widgets[i].x) + int(sc.widgets[i].width or 0) for i in valid)
    center_x = min_x + max_x
    for i in valid:
        w = sc.widgets[i]
        w.x = center_x - int(w.x) - int(w.width or 0)
    app._set_status(f"Flipped {len(valid)} widget(s) horizontally.", ttl_sec=2.0)
    app._mark_dirty()


def mirror_scene_horizontal(app) -> None:
    """Flip all widget X positions horizontally across the scene center."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    app._save_undo_state()
    sw = sc.width
    for w in sc.widgets:
        ww = int(getattr(w, "width", 0) or 0)
        w.x = sw - w.x - ww
    app._set_status(f"Mirrored {len(sc.widgets)} widget(s) horizontally.", ttl_sec=2.0)
    app._mark_dirty()


def mirror_scene_vertical(app) -> None:
    """Flip all widget Y positions vertically across the scene center."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    app._save_undo_state()
    sh = sc.height
    for w in sc.widgets:
        wh = int(getattr(w, "height", 0) or 0)
        w.y = sh - w.y - wh
    app._set_status(f"Mirrored {len(sc.widgets)} widget(s) vertically.", ttl_sec=2.0)
    app._mark_dirty()


def move_to_origin(app) -> None:
    """Move selected widgets so bounding box top-left is at (0, 0)."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    min_x = min(int(sc.widgets[i].x) for i in app.state.selected if 0 <= i < len(sc.widgets))
    min_y = min(int(sc.widgets[i].y) for i in app.state.selected if 0 <= i < len(sc.widgets))
    if min_x == 0 and min_y == 0:
        app._set_status("Already at origin.", ttl_sec=2.0)
        return
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].x -= min_x
            sc.widgets[idx].y -= min_y
    app._set_status(f"Moved {len(app.state.selected)} widget(s) to origin.", ttl_sec=2.0)
    app._mark_dirty()


def make_square(app) -> None:
    """Set width = height = max(width, height) on selected widgets."""
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
        ww = int(getattr(w, "width", GRID) or GRID)
        wh = int(getattr(w, "height", GRID) or GRID)
        side = max(ww, wh)
        if ww != side or wh != side:
            w.width = side
            w.height = side
            count += 1
    app._set_status(f"Squared {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def scale_up(app) -> None:
    """Double the width and height of selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.width = int(getattr(w, "width", GRID) or GRID) * 2
        w.height = int(getattr(w, "height", GRID) or GRID) * 2
    app._set_status(f"Scaled up {len(app.state.selected)} widget(s) 2×.", ttl_sec=2.0)
    app._mark_dirty()


def scale_down(app) -> None:
    """Halve the width and height of selected widgets (min GRID)."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.width = max(GRID, snap(int(getattr(w, "width", GRID) or GRID) // 2))
        w.height = max(GRID, snap(int(getattr(w, "height", GRID) or GRID) // 2))
    app._set_status(f"Scaled down {len(app.state.selected)} widget(s) ½.", ttl_sec=2.0)
    app._mark_dirty()
