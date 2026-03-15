"""Widget creation, auto-completion, and layout — extracted from scene_ops.py."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple

import pygame

from ui_designer import WidgetConfig

from . import text_metrics
from .constants import GRID, safe_save_state, snap

if TYPE_CHECKING:
    from .app import CyberpunkEditorApp


# ------------------------------------------------------------------ #
# Widget auto-completion
# ------------------------------------------------------------------ #


def auto_complete_widget(app: CyberpunkEditorApp, w: WidgetConfig) -> None:
    """Automatically complete widget configuration with smart defaults."""
    if not w.text and w.type == "button":
        w.text = "Button"
    if not w.color_fg:
        w.color_fg = "#f5f5f5"
    if not w.color_bg:
        w.color_bg = "#000000"

    if w.type == "label" and w.text:
        if text_metrics.is_device_profile(app.hardware_profile):
            text_w = len(str(w.text)) * text_metrics.DEVICE_CHAR_W
            text_h = text_metrics.DEVICE_CHAR_H
            w.width = max(w.width, int(text_w + 4))
            w.height = max(w.height, int(text_h + 4))
        else:
            text_size = app.font.size(w.text)
            w.width = max(w.width, text_size[0] + GRID)
            w.height = max(w.height, text_size[1] + GRID // 2)

    w.x = snap(w.x)
    w.y = snap(w.y)
    w.width = snap(w.width)
    w.height = snap(w.height)


# ------------------------------------------------------------------ #
# Position finding
# ------------------------------------------------------------------ #


def find_best_position(
    app: CyberpunkEditorApp, widget: WidgetConfig, scene: object
) -> Tuple[int, int]:
    """Find a good position: next to selection, at mouse cursor, or first free slot."""
    ww = max(GRID, int(widget.width))
    wh = max(GRID, int(widget.height))
    max_x = max(0, int(scene.width) - ww)  # type: ignore[attr-defined]
    max_y = max(0, int(scene.height) - wh)  # type: ignore[attr-defined]

    def _overlaps(x: int, y: int) -> bool:
        r = pygame.Rect(x, y, ww, wh)
        for other in scene.widgets:  # type: ignore[attr-defined]
            if other is widget:
                continue
            o = pygame.Rect(int(other.x), int(other.y), int(other.width), int(other.height))
            if r.colliderect(o):
                return True
        return False

    def _clamp_snap(x: int, y: int) -> Tuple[int, int]:
        x = max(0, min(max_x, snap(x) if app.snap_enabled else x))
        y = max(0, min(max_y, snap(y) if app.snap_enabled else y))
        return x, y

    if app.state.selected:
        bounds = app._selection_bounds(app.state.selected)
        if bounds is not None:
            cx, cy = _clamp_snap(bounds.right + GRID, bounds.y)
            if not _overlaps(cx, cy):
                return cx, cy
            cx, cy = _clamp_snap(bounds.x, bounds.bottom + GRID)
            if not _overlaps(cx, cy):
                return cx, cy

    sr = getattr(app, "scene_rect", None)
    if sr and isinstance(sr, pygame.Rect) and sr.collidepoint(app.pointer_pos):
        cx = int(app.pointer_pos[0] - sr.x) - ww // 2
        cy = int(app.pointer_pos[1] - sr.y) - wh // 2
        cx, cy = _clamp_snap(cx, cy)
        if not _overlaps(cx, cy):
            return cx, cy

    for y in range(0, max_y + 1, GRID):
        for x in range(0, max_x + 1, GRID):
            if not _overlaps(x, y):
                return x, y

    return _clamp_snap(GRID, GRID)


# ------------------------------------------------------------------ #
# Widget creation
# ------------------------------------------------------------------ #


def add_widget(app: CyberpunkEditorApp, kind: str) -> None:
    """Add widget to scene."""
    sc = app.state.current_scene()
    safe_save_state(app.designer)
    kind = str(kind or "").lower()
    defaults: Dict[str, Dict[str, Any]] = {
        "label": {
            "width": 90,
            "height": 16,
            "border": False,
            "align": "left",
            "valign": "middle",
        },
        "button": {
            "width": 88,
            "height": 24,
            "border_style": "rounded",
            "style": "bold",
            "align": "center",
            "valign": "middle",
        },
        "panel": {"width": 160, "height": 96, "text": "", "border_style": "single"},
        "progressbar": {"width": 140, "height": 16, "text": "Progress", "value": 65},
        "gauge": {
            "width": 64,
            "height": 64,
            "text": "Gauge",
            "value": 70,
            "align": "center",
            "valign": "bottom",
        },
        "slider": {"width": 160, "height": 24, "text": "Slider", "value": 40},
        "checkbox": {"width": 140, "height": 16, "text": "Checkbox"},
        "textbox": {
            "width": 160,
            "height": 24,
            "text": "Text",
            "align": "left",
            "valign": "middle",
        },
        "chart": {
            "width": 200,
            "height": 120,
            "text": "Line chart",
            "border_style": "rounded",
        },
        "list": {
            "width": 100,
            "height": 48,
            "text": "Item 1\nItem 2\nItem 3\nItem 4\nItem 5",
            "value": 0,
            "border": True,
            "border_style": "single",
        },
        "toggle": {
            "width": 60,
            "height": 10,
            "text": "Toggle",
            "checked": False,
            "border": False,
        },
        "icon": {
            "width": 24,
            "height": 24,
            "text": "",
            "icon_char": "@",
            "border": False,
            "align": "center",
            "valign": "middle",
        },
    }
    cfg = defaults.get(kind, {})
    try:
        w = WidgetConfig(
            type=kind,
            x=GRID,
            y=GRID,
            width=int(cfg.get("width", 60)),
            height=int(cfg.get("height", 16)),
            text=str(cfg.get("text", kind.capitalize()) or ""),
            style=str(cfg.get("style", "default") or "default"),
            color_fg=str(cfg.get("color_fg", "white") or "white"),
            color_bg=str(cfg.get("color_bg", "black") or "black"),
            border=bool(cfg.get("border", True)),
            border_style=str(cfg.get("border_style", "single") or "single"),
            align=str(cfg.get("align", "left") or "left"),
            valign=str(cfg.get("valign", "middle") or "middle"),
            value=int(cfg.get("value", 0) or 0),
            min_value=int(cfg.get("min_value", 0) or 0),
            max_value=int(cfg.get("max_value", 100) or 100),
            checked=bool(cfg.get("checked", False)),
            icon_char=str(cfg.get("icon_char", "") or ""),
        )
    except ValueError:
        app._set_status(f"Unknown widget type: {kind}", ttl_sec=4.0)
        return
    try:
        auto_complete_widget(app, w)
        bx, by = find_best_position(app, w, sc)
        w.x, w.y = int(bx), int(by)
    except (ValueError, TypeError, AttributeError):  # pragma: no cover
        pass
    sc.widgets.append(w)
    idx = len(sc.widgets) - 1
    if not getattr(w, "_widget_id", None):
        w._widget_id = f"{kind}_{idx}"
    app.state.selected = [idx]
    app.state.selected_idx = app.state.selected[0]
    app._mark_dirty()


# ------------------------------------------------------------------ #
# Auto-arrange
# ------------------------------------------------------------------ #


def intelligent_auto_arrange(app: CyberpunkEditorApp) -> None:
    """Smart auto-arrangement using AI-like heuristics."""
    sc = app.state.current_scene()
    if not sc.widgets:
        return

    safe_save_state(app.designer)

    groups: dict[str, list[WidgetConfig]] = {}
    for w in sc.widgets:
        if w.type not in groups:
            groups[w.type] = []
        groups[w.type].append(w)

    for _widget_type, widgets in groups.items():
        widgets.sort(key=lambda w: w.width * w.height, reverse=True)
        for w in widgets:
            best_x, best_y = find_best_position(app, w, sc)
            w.x = best_x
            w.y = best_y

    app._mark_dirty()


def auto_arrange_grid(app: CyberpunkEditorApp) -> None:
    """Auto-arrange widgets in grid."""
    sc = app.state.current_scene()
    x, y = GRID, GRID
    row_h = 0
    for w in sc.widgets:
        if x + w.width > sc.width - GRID:
            x, y = GRID, y + row_h + GRID
            row_h = 0
        w.x, w.y = x, y
        x += w.width + GRID
        row_h = max(row_h, w.height)
    app._mark_dirty()
