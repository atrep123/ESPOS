from __future__ import annotations

from ui_designer import WidgetConfig

from ..constants import GRID
from .core import selection_bounds


def create_header_bar(app) -> None:
    """Create a header bar: full-width panel + centered label at top of scene."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    bar_h = 24
    panel = WidgetConfig(
        type="panel", x=0, y=0, width=sw, height=bar_h,
        text="", border=True, border_style="single",
        color_fg="white", color_bg="black",
    )
    label = WidgetConfig(
        type="label", x=2, y=4, width=sw - 4, height=16,
        text="Header", border=False,
        style="bold", align="center", valign="middle",
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(panel)
    sc.widgets.append(label)
    app.state.selected = [base, base + 1]
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status("Header bar created.", ttl_sec=2.0)
    app._mark_dirty()


def create_nav_row(app) -> None:
    """Create a navigation row: 3 buttons equally spaced at scene bottom."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    sh = int(sc.height)
    btn_count = 3
    btn_h = 24
    gap = GRID
    total_gap = gap * (btn_count + 1)
    btn_w = (sw - total_gap) // btn_count
    btn_w = max(btn_w, 32)
    y = sh - btn_h
    labels = ["Back", "OK", "Next"]
    base = len(sc.widgets)
    for i in range(btn_count):
        bx = gap + i * (btn_w + gap)
        btn = WidgetConfig(
            type="button", x=bx, y=y, width=btn_w, height=btn_h,
            text=labels[i], border=True, border_style="rounded",
            style="bold", align="center", valign="middle",
            color_fg="white", color_bg="black",
        )
        sc.widgets.append(btn)
    app.state.selected = list(range(base, base + btn_count))
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status(f"Nav row: {btn_count} buttons created.", ttl_sec=2.0)
    app._mark_dirty()


def create_form_pair(app) -> None:
    """Create a form pair: label on left + textbox on right, placed below selection or at top."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    row_h = 24
    label_w = 64
    gap = GRID
    input_w = sw - label_w - gap * 3

    # Place below current selection bounds, or at y=GRID
    y = GRID
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    lbl = WidgetConfig(
        type="label", x=gap, y=y + 4, width=label_w, height=16,
        text="Label:", border=False,
        align="right", valign="middle",
        color_fg="white", color_bg="black",
    )
    txt = WidgetConfig(
        type="textbox", x=gap + label_w + gap, y=y, width=input_w, height=row_h,
        text="value", border=True, border_style="single",
        align="left", valign="middle",
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(lbl)
    sc.widgets.append(txt)
    app.state.selected = [base, base + 1]
    app.state.selected_idx = base + 1
    app._save_undo_state()
    app._set_status("Form pair created (label + textbox).", ttl_sec=2.0)
    app._mark_dirty()


def create_status_bar(app) -> None:
    """Create a status bar: full-width panel + label at scene bottom."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    sh = int(sc.height)
    bar_h = 16
    panel = WidgetConfig(
        type="panel", x=0, y=sh - bar_h, width=sw, height=bar_h,
        text="", border=True, border_style="single",
        color_fg="white", color_bg="black",
    )
    label = WidgetConfig(
        type="label", x=2, y=sh - bar_h + 2, width=sw - 4, height=12,
        text="Status: ready", border=False,
        style="default", align="left", valign="middle",
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(panel)
    sc.widgets.append(label)
    app.state.selected = [base, base + 1]
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status("Status bar created.", ttl_sec=2.0)
    app._mark_dirty()


def create_toggle_group(app) -> None:
    """Create a row of 3 checkboxes with sequential labels."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    cb_count = 3
    cb_w = 72
    cb_h = 16
    gap = GRID
    total_w = cb_count * cb_w + (cb_count - 1) * gap
    start_x = max(gap, (sw - total_w) // 2)

    # Place below current selection bounds, or at y=GRID*4
    y = GRID * 4
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    labels = ["Option A", "Option B", "Option C"]
    base = len(sc.widgets)
    for i in range(cb_count):
        cx = start_x + i * (cb_w + gap)
        cb = WidgetConfig(
            type="checkbox", x=cx, y=y, width=cb_w, height=cb_h,
            text=labels[i], border=False,
            align="left", valign="middle",
            color_fg="white", color_bg="black",
            checked=(i == 0),
        )
        sc.widgets.append(cb)
    app.state.selected = list(range(base, base + cb_count))
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status(f"Toggle group: {cb_count} checkboxes created.", ttl_sec=2.0)
    app._mark_dirty()


def create_slider_with_label(app) -> None:
    """Create a labeled slider: label + slider + value label in one row."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    gap = GRID
    label_w = 56
    value_w = 32
    slider_w = sw - label_w - value_w - gap * 4
    slider_w = max(slider_w, 48)
    row_h = 24

    # Place below current selection bounds, or at y=GRID*4
    y = GRID * 4
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    lbl = WidgetConfig(
        type="label", x=gap, y=y + 4, width=label_w, height=16,
        text="Volume:", border=False,
        align="right", valign="middle",
        color_fg="white", color_bg="black",
    )
    slider = WidgetConfig(
        type="slider", x=gap + label_w + gap, y=y, width=slider_w, height=row_h,
        text="", border=True, border_style="single",
        value=50, min_value=0, max_value=100,
        color_fg="white", color_bg="black",
    )
    val_lbl = WidgetConfig(
        type="label", x=gap + label_w + gap + slider_w + gap, y=y + 4,
        width=value_w, height=16,
        text="50", border=False,
        align="left", valign="middle",
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(lbl)
    sc.widgets.append(slider)
    sc.widgets.append(val_lbl)
    app.state.selected = [base, base + 1, base + 2]
    app.state.selected_idx = base + 1
    app._save_undo_state()
    app._set_status("Slider with label created.", ttl_sec=2.0)
    app._mark_dirty()


def create_gauge_panel(app) -> None:
    """Create a gauge with title label inside a panel."""
    sc = app.state.current_scene()
    gap = GRID
    panel_w = 80
    panel_h = 88
    gauge_sz = 64

    # Place below current selection or at GRID*2
    y = GRID * 2
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    panel = WidgetConfig(
        type="panel", x=gap, y=y, width=panel_w, height=panel_h,
        text="", border=True, border_style="rounded",
        color_fg="white", color_bg="black",
    )
    title = WidgetConfig(
        type="label", x=gap + 2, y=y + 2, width=panel_w - 4, height=12,
        text="Speed", border=False,
        style="bold", align="center", valign="middle",
        color_fg="white", color_bg="black",
    )
    gauge = WidgetConfig(
        type="gauge", x=gap + (panel_w - gauge_sz) // 2, y=y + 16,
        width=gauge_sz, height=gauge_sz,
        text="", border=False,
        value=70, min_value=0, max_value=100,
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(panel)
    sc.widgets.append(title)
    sc.widgets.append(gauge)
    app.state.selected = [base, base + 1, base + 2]
    app.state.selected_idx = base + 2
    app._save_undo_state()
    app._set_status("Gauge panel created.", ttl_sec=2.0)
    app._mark_dirty()


def create_progress_section(app) -> None:
    """Create a label + progressbar row."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    gap = GRID
    label_w = 64
    bar_w = sw - label_w - gap * 3
    bar_w = max(bar_w, 48)
    row_h = 16

    y = GRID * 4
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    lbl = WidgetConfig(
        type="label", x=gap, y=y, width=label_w, height=row_h,
        text="Loading:", border=False,
        align="right", valign="middle",
        color_fg="white", color_bg="black",
    )
    bar = WidgetConfig(
        type="progressbar", x=gap + label_w + gap, y=y,
        width=bar_w, height=row_h,
        text="", border=True, border_style="single",
        value=65, min_value=0, max_value=100,
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(lbl)
    sc.widgets.append(bar)
    app.state.selected = [base, base + 1]
    app.state.selected_idx = base + 1
    app._save_undo_state()
    app._set_status("Progress section created.", ttl_sec=2.0)
    app._mark_dirty()


def create_icon_button_row(app) -> None:
    """Create a row of 4 icon-sized buttons for a mini toolbar."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    btn_count = 4
    btn_sz = 24
    gap = GRID
    total_w = btn_count * btn_sz + (btn_count - 1) * gap
    start_x = max(gap, (sw - total_w) // 2)

    y = GRID * 2
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    icons = ["\u2190", "\u2191", "\u2193", "\u2192"]  # arrow chars
    base = len(sc.widgets)
    for i in range(btn_count):
        bx = start_x + i * (btn_sz + gap)
        btn = WidgetConfig(
            type="button", x=bx, y=y, width=btn_sz, height=btn_sz,
            text=icons[i], border=True, border_style="rounded",
            style="bold", align="center", valign="middle",
            color_fg="white", color_bg="black",
        )
        sc.widgets.append(btn)
    app.state.selected = list(range(base, base + btn_count))
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status(f"Icon button row: {btn_count} buttons created.", ttl_sec=2.0)
    app._mark_dirty()


def create_card_layout(app) -> None:
    """Create a card: panel + bold title + thin separator + body label."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    gap = GRID
    card_w = min(sw - gap * 2, 200)
    card_h = 80
    sep_h = 1

    y = GRID * 2
    if app.state.selected:
        bounds = selection_bounds(app, app.state.selected)
        if bounds is not None:
            y = bounds.bottom + GRID

    cx = max(gap, (sw - card_w) // 2)

    panel = WidgetConfig(
        type="panel", x=cx, y=y, width=card_w, height=card_h,
        text="", border=True, border_style="rounded",
        color_fg="white", color_bg="black",
    )
    title = WidgetConfig(
        type="label", x=cx + 4, y=y + 4, width=card_w - 8, height=14,
        text="Card Title", border=False,
        style="bold", align="left", valign="middle",
        color_fg="white", color_bg="black",
    )
    separator = WidgetConfig(
        type="panel", x=cx + 2, y=y + 20, width=card_w - 4, height=sep_h,
        text="", border=False,
        color_fg="white", color_bg="white",
    )
    body = WidgetConfig(
        type="label", x=cx + 4, y=y + 24, width=card_w - 8, height=card_h - 28,
        text="Body content goes here.", border=False,
        style="default", align="left", valign="top",
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(panel)
    sc.widgets.append(title)
    sc.widgets.append(separator)
    sc.widgets.append(body)
    app.state.selected = list(range(base, base + 4))
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status("Card layout created.", ttl_sec=2.0)
    app._mark_dirty()


def create_dashboard_grid(app) -> None:
    """Create a 2x2 grid of gauge mini-panels filling the scene."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    sh = int(sc.height)
    gap = GRID
    cols, rows = 2, 2
    cell_w = (sw - gap * (cols + 1)) // cols
    cell_h = (sh - gap * (rows + 1)) // rows
    gauge_sz = min(cell_w - 8, cell_h - 20, 48)
    gauge_sz = max(gauge_sz, 24)

    titles = ["Speed", "Temp", "RPM", "Batt"]
    values = [70, 45, 85, 60]

    base = len(sc.widgets)
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            px = gap + c * (cell_w + gap)
            py = gap + r * (cell_h + gap)
            # Panel
            sc.widgets.append(WidgetConfig(
                type="panel", x=px, y=py, width=cell_w, height=cell_h,
                text="", border=True, border_style="single",
                color_fg="white", color_bg="black",
            ))
            # Title
            sc.widgets.append(WidgetConfig(
                type="label", x=px + 2, y=py + 2, width=cell_w - 4, height=12,
                text=titles[idx], border=False,
                style="bold", align="center", valign="middle",
                color_fg="white", color_bg="black",
            ))
            # Gauge
            gx = px + (cell_w - gauge_sz) // 2
            gy = py + 16
            sc.widgets.append(WidgetConfig(
                type="gauge", x=gx, y=gy, width=gauge_sz, height=gauge_sz,
                text="", border=False,
                value=values[idx], min_value=0, max_value=100,
                color_fg="white", color_bg="black",
            ))
    total = cols * rows * 3  # 3 widgets per cell
    app.state.selected = list(range(base, base + total))
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status("Dashboard grid (2×2) created.", ttl_sec=2.0)
    app._mark_dirty()


def create_split_layout(app) -> None:
    """Create a 2-pane horizontal split: left panel + right panel with labels."""
    sc = app.state.current_scene()
    sw = int(sc.width)
    sh = int(sc.height)
    gap = GRID
    split = sw // 2
    left_w = split - gap
    right_w = sw - split - gap
    pane_h = sh - gap * 2

    left_panel = WidgetConfig(
        type="panel", x=gap, y=gap, width=left_w, height=pane_h,
        text="", border=True, border_style="single",
        color_fg="white", color_bg="black",
    )
    left_label = WidgetConfig(
        type="label", x=gap + 4, y=gap + 4, width=left_w - 8, height=14,
        text="Left Pane", border=False,
        style="bold", align="center", valign="middle",
        color_fg="white", color_bg="black",
    )
    right_panel = WidgetConfig(
        type="panel", x=split, y=gap, width=right_w, height=pane_h,
        text="", border=True, border_style="single",
        color_fg="white", color_bg="black",
    )
    right_label = WidgetConfig(
        type="label", x=split + 4, y=gap + 4, width=right_w - 8, height=14,
        text="Right Pane", border=False,
        style="bold", align="center", valign="middle",
        color_fg="white", color_bg="black",
    )
    base = len(sc.widgets)
    sc.widgets.append(left_panel)
    sc.widgets.append(left_label)
    sc.widgets.append(right_panel)
    sc.widgets.append(right_label)
    app.state.selected = list(range(base, base + 4))
    app.state.selected_idx = base
    app._save_undo_state()
    app._set_status("Split layout created (2 panes).", ttl_sec=2.0)
    app._mark_dirty()


def wrap_in_panel(app) -> None:
    """Wrap selected widgets in a new panel that encloses them with padding."""
    if not app.state.selected:
        app._set_status("Wrap: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return
    pad = GRID
    panel = WidgetConfig(
        type="panel",
        x=bounds.x - pad, y=bounds.y - pad,
        width=bounds.width + pad * 2, height=bounds.height + pad * 2,
        text="", border=True, border_style="single",
        color_fg="white", color_bg="black",
    )
    # Insert panel just before the first selected widget so it's behind them
    insert_at = min(app.state.selected)
    sc.widgets.insert(insert_at, panel)
    # Shift selection indices up by 1 (everything after insert shifted)
    new_sel = [i + 1 for i in app.state.selected]
    new_sel.insert(0, insert_at)
    app.state.selected = sorted(set(new_sel))
    app.state.selected_idx = insert_at
    app._save_undo_state()
    app._set_status(f"Wrapped {len(new_sel) - 1} widget(s) in panel.", ttl_sec=2.0)
    app._mark_dirty()
