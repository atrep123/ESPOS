"""Scene management, z-order, templates, and export — extracted from app.py."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

import pygame

from ui_designer import HARDWARE_PROFILES, UIDesigner, WidgetConfig
from ui_models import SceneConfig

from .constants import PROFILE_ORDER, safe_save_state
from .state import EditorState

# Re-export widget factory functions for backward compatibility
from .widget_factory import (  # noqa: F401
    add_widget,
    auto_arrange_grid,
    auto_complete_widget,
    find_best_position,
    intelligent_auto_arrange,
)

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
        app._set_status(f"Scene #{index + 1} does not exist ({len(names)} scenes).", ttl_sec=2.0)
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
    to_remove = names[idx + 1 :]
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
