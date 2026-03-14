"""Scene management, z-order, widget factory, and export — extracted from app.py."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple

import pygame

from ui_designer import HARDWARE_PROFILES, UIDesigner, WidgetConfig
from ui_models import SceneConfig

from . import text_metrics
from .constants import GRID, PROFILE_ORDER, safe_save_state, snap
from .state import EditorState

if TYPE_CHECKING:
    from .app import CyberpunkEditorApp


# ------------------------------------------------------------------ #
# Z-order
# ------------------------------------------------------------------ #

def z_order_step(app: CyberpunkEditorApp, delta: int) -> None:
    """Move selected widgets z_index by delta."""
    if not app.state.selected:
        return
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            w.z_index = int(getattr(w, "z_index", 0) or 0) + delta
    direction = "forward" if delta > 0 else "backward"
    app._set_status(f"z-order: {direction}", ttl_sec=1.5)
    app._mark_dirty()


def z_order_bring_to_front(app: CyberpunkEditorApp) -> None:
    """Set selected widgets z_index above all others."""
    if not app.state.selected:
        return
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    max_z = 0
    for w in sc.widgets:
        z = int(getattr(w, "z_index", 0) or 0)
        if z > max_z:
            max_z = z
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            max_z += 1
            sc.widgets[idx].z_index = max_z
    app._set_status("z-order: bring to front", ttl_sec=1.5)
    app._mark_dirty()


def z_order_send_to_back(app: CyberpunkEditorApp) -> None:
    """Set selected widgets z_index below all others."""
    if not app.state.selected:
        return
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    min_z = 0
    for w in sc.widgets:
        z = int(getattr(w, "z_index", 0) or 0)
        if z < min_z:
            min_z = z
    for idx in reversed(app.state.selected):
        if 0 <= idx < len(sc.widgets):
            min_z -= 1
            sc.widgets[idx].z_index = min_z
    app._set_status("z-order: send to back", ttl_sec=1.5)
    app._mark_dirty()


def toggle_lock_selection(app: CyberpunkEditorApp) -> None:
    """Toggle locked state on selected widgets."""
    if not app.state.selected:
        app._set_status("Lock: nothing selected.", ttl_sec=2.0)
        return
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    values = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            values.append(bool(getattr(sc.widgets[idx], "locked", False)))
    new_val = not all(values) if values else True
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].locked = new_val
    label = "locked" if new_val else "unlocked"
    app._set_status(f"Widget(s) {label}.", ttl_sec=1.5)
    app._mark_dirty()


# ------------------------------------------------------------------ #
# Scene navigation
# ------------------------------------------------------------------ #

def zoom_to_fit(app: CyberpunkEditorApp) -> None:
    """Auto-compute scale to fit the entire scene in the window."""
    try:
        sc = app.state.current_scene()
        scene_w = max(1, int(sc.width))
        scene_h = max(1, int(sc.height))
        canvas = app.layout.canvas_rect
        if canvas.width <= 0 or canvas.height <= 0:
            return
        win_w, win_h = app.window.get_size()
        avail_w = max(1, canvas.width)
        avail_h = max(1, canvas.height)
        fit_w = win_w // max(1, app.layout.width) * avail_w // scene_w
        fit_h = win_h // max(1, app.layout.height) * avail_h // scene_h
        new_scale = max(1, min(int(getattr(app, "max_auto_scale", 8) or 8), fit_w, fit_h))
        app._set_scale(new_scale)
        app._set_status(f"Zoom to fit: scale={new_scale}", ttl_sec=2.0)
    except (ValueError, TypeError, ZeroDivisionError, AttributeError):
        pass


def switch_scene(app: CyberpunkEditorApp, direction: int) -> None:
    """Switch to next/previous scene."""
    names = list(app.designer.scenes.keys())
    if len(names) <= 1:
        app._set_status("Only one scene.", ttl_sec=2.0)
        return
    current = app.designer.current_scene or ""
    try:
        idx = names.index(current)
    except ValueError:
        idx = 0
    idx = (idx + direction) % len(names)
    app.designer.current_scene = names[idx]
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Scene: {names[idx]}", ttl_sec=2.0)
    app._mark_dirty()


def handle_double_click(app: CyberpunkEditorApp, pos: Tuple[int, int]) -> None:
    """Double-click on a widget to start editing its text, or on a tab to rename."""
    lx, ly = pos
    if app.layout.scene_tabs_rect.collidepoint(lx, ly):
        for rect, tab_idx, _tab_name in getattr(app, "tab_hitboxes", []):
            if tab_idx >= 0 and rect.collidepoint(lx, ly):
                app._jump_to_scene(tab_idx)
                app._rename_current_scene()
                return
        return
    sr = getattr(app, "scene_rect", app.layout.canvas_rect)
    if not isinstance(sr, pygame.Rect):
        sr = app.layout.canvas_rect
    if not sr.collidepoint(pos[0], pos[1]):
        return
    hit = app.state.hit_test_at(pos, sr)
    if hit is None:
        return
    sc = app.state.current_scene()
    if not (0 <= hit < len(sc.widgets)):
        return
    app._set_selection([hit], anchor_idx=hit)
    app._inspector_start_edit("text")


def build_template_actions(app: CyberpunkEditorApp) -> list[tuple[str, Any]]:
    """Return a list of (label, callback) pairs for available templates."""
    actions = []
    if not app.template_library.templates:
        return actions
    actions.append(("-- Templates --", None))
    for tpl in app.template_library.templates[:6]:
        label = f"Template: {tpl.metadata.name}"
        actions.append((label, lambda tpl=tpl: app._apply_template(tpl)))
    return actions


def apply_template(app: CyberpunkEditorApp, template: Any) -> None:
    """Replace current scene with widgets from a template."""
    sc = app.state.current_scene()
    safe_save_state(app.designer)
    sc.widgets.clear()
    for wdict in template.scene._raw_data.get("widgets", []):  # pyright: ignore[reportPrivateUsage]
        try:
            sc.widgets.append(WidgetConfig(**wdict))
        except (TypeError, ValueError, KeyError):
            continue
    app.state.selected_idx = 0 if sc.widgets else None
    app.state.selected = [0] if sc.widgets else []
    app._mark_dirty()


def apply_first_template(app: CyberpunkEditorApp) -> None:
    """Quick apply first template to current scene."""
    if not app.template_library.templates:
        return
    app._apply_template(app.template_library.templates[0])


def set_profile(app: CyberpunkEditorApp, key: str) -> None:
    """Switch hardware profile (updates scene size + estimation)."""
    if key not in HARDWARE_PROFILES:
        return
    pinfo = HARDWARE_PROFILES[key]
    app.hardware_profile = key
    app.default_size = (pinfo["width"], pinfo["height"])
    app.designer.set_hardware_profile(key)
    win_size = app.window.get_size() if app.window else None
    app._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
    app._mark_dirty()
    print(f"[INFO] Hardware profile: {pinfo['label']}")


def cycle_profile(app: CyberpunkEditorApp) -> None:
    """Cycle through known hardware profiles (F6)."""
    if not PROFILE_ORDER:
        return
    if app.hardware_profile in PROFILE_ORDER:
        idx = PROFILE_ORDER.index(app.hardware_profile)
        next_key = PROFILE_ORDER[(idx + 1) % len(PROFILE_ORDER)]
    else:
        next_key = PROFILE_ORDER[0]
    app._set_profile(next_key)


# ------------------------------------------------------------------ #
# Scene CRUD
# ------------------------------------------------------------------ #

def new_scene(app: CyberpunkEditorApp) -> None:
    """Clear current design to a fresh scene."""
    app.designer = UIDesigner(*app.default_size)
    app.designer.create_scene("main")
    app.designer.set_responsive_base()
    sc = app.designer.scenes[app.designer.current_scene or ""]
    sc.width, sc.height = app.default_size
    app.designer.width, app.designer.height = sc.width, sc.height
    win_size = app.window.get_size() if app.window else None
    app._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
    app.state = EditorState(app.designer, app.layout)
    app._dirty = True


def jump_to_scene(app: CyberpunkEditorApp, index: int) -> None:
    """Jump to scene by 0-based index."""
    names = list(app.designer.scenes.keys())
    if index >= len(names):
        app._set_status(
            f"Scene #{index + 1} does not exist ({len(names)} scenes).", ttl_sec=2.0
        )
        return
    app.designer.current_scene = names[index]
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Scene {index + 1}: {names[index]}", ttl_sec=2.0)
    app._mark_dirty()


def save_selection_as_template(app: CyberpunkEditorApp) -> None:
    """Save selected widgets as a named template."""
    if not app.state.selected:
        app._set_status("Save template: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    widgets = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            from dataclasses import asdict

            widgets.append(asdict(sc.widgets[idx]))
    if not widgets:
        return
    app.state.inspector_selected_field = "_template_name"
    app.state.inspector_input_buffer = ""
    app._pending_template_widgets = widgets
    try:
        pygame.key.start_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status("Template name (Enter=save Esc=cancel)", ttl_sec=4.0)


def delete_current_scene(app: CyberpunkEditorApp) -> None:
    """Delete the current scene if more than one exists."""
    names = list(app.designer.scenes.keys())
    if len(names) <= 1:
        app._set_status("Cannot delete the only scene.", ttl_sec=2.0)
        return
    cur = app.designer.current_scene
    if not cur:
        return
    idx = names.index(cur) if cur in names else 0
    del app.designer.scenes[cur]
    app._dirty_scenes.discard(cur)
    remaining = list(app.designer.scenes.keys())
    new_idx = min(idx, len(remaining) - 1)
    app.designer.current_scene = remaining[new_idx]
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Deleted scene: {cur}", ttl_sec=2.0)
    app._mark_dirty()


def close_other_scenes(app: CyberpunkEditorApp) -> None:
    """Close all scenes except the current one."""
    cur = app.designer.current_scene
    names = [n for n in app.designer.scenes if n != cur]
    if not names:
        return
    for n in names:
        del app.designer.scenes[n]
        app._dirty_scenes.discard(n)
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Closed {len(names)} scene(s)", ttl_sec=2.0)
    app._mark_dirty()


def close_scenes_to_right(app: CyberpunkEditorApp) -> None:
    """Close all scenes to the right of the current one."""
    names = list(app.designer.scenes.keys())
    cur = app.designer.current_scene
    idx = names.index(cur) if cur in names else 0
    to_remove = names[idx + 1:]
    if not to_remove:
        return
    for n in to_remove:
        del app.designer.scenes[n]
        app._dirty_scenes.discard(n)
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Closed {len(to_remove)} scene(s) to the right", ttl_sec=2.0)
    app._mark_dirty()


def add_new_scene(app: CyberpunkEditorApp) -> None:
    """Add a new scene to the design."""
    names = list(app.designer.scenes.keys())
    base = "scene"
    idx = len(names) + 1
    while f"{base}_{idx}" in names:
        idx += 1
    name = f"{base}_{idx}"
    app.designer.create_scene(name)
    sc = app.designer.scenes[name]
    sc.width, sc.height = app.default_size
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"New scene: {name}", ttl_sec=2.0)
    app._mark_dirty()


def duplicate_current_scene(app: CyberpunkEditorApp) -> None:
    """Duplicate the current scene with all widgets."""
    from dataclasses import asdict

    cur = app.designer.current_scene
    if not cur:
        app._set_status("No scene to duplicate.", ttl_sec=2.0)
        return
    src = app.designer.scenes.get(cur)
    if src is None:
        app._set_status("No scene to duplicate.", ttl_sec=2.0)
        return
    names = list(app.designer.scenes.keys())
    base = f"{cur}_copy"
    idx = 1
    name = base
    while name in names:
        idx += 1
        name = f"{base}_{idx}"
    new_widgets = []
    for w in src.widgets:
        try:
            new_widgets.append(WidgetConfig(**asdict(w)))
        except (TypeError, ValueError, KeyError):
            continue
    new_sc = SceneConfig(
        name=name,
        width=src.width,
        height=src.height,
        widgets=new_widgets,
        bg_color=src.bg_color,
        theme=src.theme,
    )
    app.designer.scenes[name] = new_sc
    app.designer.current_scene = name
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Duplicated scene: {name}", ttl_sec=2.0)
    app._mark_dirty()


def rename_current_scene(app: CyberpunkEditorApp) -> None:
    """Start inline editing to rename the current scene."""
    app.state.inspector_selected_field = "_scene_name"
    app.state.inspector_input_buffer = str(app.designer.current_scene or "")
    try:
        pygame.key.start_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status("Rename scene (Enter=apply Esc=cancel)", ttl_sec=4.0)


# ------------------------------------------------------------------ #
# Export
# ------------------------------------------------------------------ #

def export_c_header(app: CyberpunkEditorApp) -> None:
    """Quick-export current JSON to a C header."""
    from pathlib import Path

    json_path = getattr(app, "json_path", None)
    if json_path is None:
        app._set_status("Export: no JSON file loaded.", ttl_sec=2.0)
        return
    json_path = Path(json_path)
    if not json_path.exists():
        app._set_status("Export: JSON file not found.", ttl_sec=2.0)
        return
    try:
        import sys

        repo_root = json_path.resolve().parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from tools.ui_codegen import generate_scenes_header
    except ImportError:
        app._set_status("Export: ui_codegen not found.", ttl_sec=3.0)
        return
    try:
        app.save_json()
    except OSError:
        pass
    out_dir = json_path.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ui_design_export.h"
    try:
        from datetime import datetime

        guard = "UI_DESIGN_EXPORT_H"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = generate_scenes_header(
            json_path,
            guard=guard,
            source_name=json_path.name,
            generated_ts=ts,
        )
        out_path.write_text(text, encoding="utf-8", newline="\n")
        app._set_status(f"Exported: {out_path.name}", ttl_sec=3.0)
    except (OSError, ValueError, TypeError) as exc:
        app._set_status(f"Export failed: {exc}", ttl_sec=4.0)


# ------------------------------------------------------------------ #
# Widget factory
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
    except (ValueError, TypeError, AttributeError):
        pass
    sc.widgets.append(w)
    idx = len(sc.widgets) - 1
    if not getattr(w, "_widget_id", None):
        w._widget_id = f"{kind}_{idx}"
    app.state.selected = [idx]
    app.state.selected_idx = app.state.selected[0]
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


def toggle_clean_preview(app: CyberpunkEditorApp) -> None:
    """Toggle clean preview mode — shows only the scene with no UI chrome."""
    app.clean_preview = not app.clean_preview
    if app.clean_preview:
        app._saved_show_grid = app.show_grid
        app._saved_panels_collapsed = app.panels_collapsed
        app.show_grid = False
        if not app.panels_collapsed:
            app._toggle_panels()
        app.state.selected = []
        app.state.selected_idx = None
        app._set_status("Preview ON (F9=exit)", ttl_sec=2.0)
    else:
        app.show_grid = getattr(app, "_saved_show_grid", True)
        if getattr(app, "_saved_panels_collapsed", False) != app.panels_collapsed:
            app._toggle_panels()
        app._set_status("Preview OFF", ttl_sec=1.5)
    app._mark_dirty()


def goto_widget_prompt(app: CyberpunkEditorApp) -> None:
    """Open inline input to jump to a widget by index."""
    app.state.inspector_selected_field = "_goto_widget"
    app.state.inspector_input_buffer = ""
    try:
        pygame.key.start_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status("Go to widget # (Enter=jump Esc=cancel)", ttl_sec=4.0)
