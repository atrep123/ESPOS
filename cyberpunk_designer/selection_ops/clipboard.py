from __future__ import annotations

import json
from dataclasses import asdict
from typing import List

import pygame

from ui_designer import SceneConfig, WidgetConfig

from ..constants import GRID, snap
from .core import delete_selected


def copy_selection(app) -> None:
    sc = app.state.current_scene()
    if not app.state.selected:
        app._set_status("Copy: nothing selected.", ttl_sec=2.0)
        return
    copied: List[WidgetConfig] = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            try:
                copied.append(WidgetConfig(**asdict(sc.widgets[idx])))
            except Exception:
                continue
    app.clipboard = copied
    app._set_status(f"Copied {len(copied)} widget(s).", ttl_sec=2.0)


def paste_clipboard(app) -> None:
    if not app.clipboard:
        app._set_status("Paste: clipboard empty.", ttl_sec=2.0)
        return

    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass

    if not app.clipboard:
        return
    min_x = min(int(w.x) for w in app.clipboard)
    min_y = min(int(w.y) for w in app.clipboard)

    dx = GRID * 2
    dy = GRID * 2
    sr = getattr(app, "scene_rect", None)
    if sr is None or not hasattr(sr, "collidepoint"):
        sr = app.layout.canvas_rect
    if sr.collidepoint(app.pointer_pos):
        try:
            dx = int(app.pointer_pos[0] - sr.x) - min_x
            dy = int(app.pointer_pos[1] - sr.y) - min_y
        except Exception:
            dx, dy = GRID * 2, GRID * 2

    new_indices: List[int] = []
    for w in app.clipboard:
        try:
            nw = WidgetConfig(**asdict(w))
        except Exception:
            continue
        nw.x = int(nw.x + dx)
        nw.y = int(nw.y + dy)
        if app.snap_enabled:
            nw.x = snap(int(nw.x))
            nw.y = snap(int(nw.y))
        max_x = max(0, int(sc.width) - int(nw.width))
        max_y = max(0, int(sc.height) - int(nw.height))
        nw.x = max(0, min(max_x, int(nw.x)))
        nw.y = max(0, min(max_y, int(nw.y)))
        sc.widgets.append(nw)
        new_indices.append(len(sc.widgets) - 1)

    app.state.selected = new_indices
    app.state.selected_idx = new_indices[0] if new_indices else None
    app.designer.selected_widget = app.state.selected_idx
    app._set_status(f"Pasted {len(new_indices)} widget(s).", ttl_sec=2.0)


def cut_selection(app) -> None:
    if not app.state.selected:
        app._set_status("Cut: nothing selected.", ttl_sec=2.0)
        return
    copy_selection(app)
    delete_selected(app)
    app._set_status("Cut.", ttl_sec=2.0)


def duplicate_selection(app) -> None:
    if not app.state.selected:
        app._set_status("Duplicate: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass

    new_indices: List[int] = []
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        try:
            nw = WidgetConfig(**asdict(sc.widgets[idx]))
        except Exception:
            continue
        # Offset: one GRID step right + down
        nw.x = max(0, min(int(sc.width) - int(nw.width), int(nw.x) + GRID))
        nw.y = max(0, min(int(sc.height) - int(nw.height), int(nw.y) + GRID))
        sc.widgets.append(nw)
        new_indices.append(len(sc.widgets) - 1)

    if new_indices:
        app.state.selected = new_indices
        app.state.selected_idx = new_indices[0]
        app.designer.selected_widget = app.state.selected_idx
    app._set_status(f"Duplicated {len(new_indices)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def copy_to_next_scene(app) -> None:
    """Copy selected widgets to the next scene."""
    if not app.state.selected:
        app._set_status("Copy to scene: nothing selected.", ttl_sec=2.0)
        return
    names = list(app.designer.scenes.keys())
    if len(names) <= 1:
        app._set_status("Only one scene — nowhere to copy.", ttl_sec=2.0)
        return
    current = app.designer.current_scene
    try:
        ci = names.index(current)
    except ValueError:
        ci = 0
    next_name = names[(ci + 1) % len(names)]
    target_sc = app.designer.scenes.get(next_name)
    if target_sc is None:
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    copied = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        nw = WidgetConfig(**asdict(sc.widgets[idx]))
        target_sc.widgets.append(nw)
        copied += 1
    app._set_status(f"Copied {copied} widget(s) to '{next_name}'.", ttl_sec=2.0)
    app._mark_dirty()


def paste_in_place(app) -> None:
    """Paste clipboard widgets at their original positions (no offset)."""
    if not app.clipboard:
        app._set_status("Paste in place: clipboard empty.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    new_indices: List[int] = []
    for w in app.clipboard:
        try:
            nw = WidgetConfig(**asdict(w))
        except Exception:
            continue
        max_x = max(0, int(sc.width) - max(1, int(nw.width)))
        max_y = max(0, int(sc.height) - max(1, int(nw.height)))
        nw.x = max(0, min(max_x, int(nw.x)))
        nw.y = max(0, min(max_y, int(nw.y)))
        sc.widgets.append(nw)
        new_indices.append(len(sc.widgets) - 1)
    if new_indices:
        app._set_selection(new_indices, anchor_idx=new_indices[0])
    app._set_status(f"Pasted {len(new_indices)} widget(s) in place.", ttl_sec=2.0)
    app._mark_dirty()


def broadcast_to_all_scenes(app) -> None:
    """Copy selected widgets into every other scene."""
    if not app.state.selected:
        app._set_status("Broadcast: nothing selected.", ttl_sec=2.0)
        return
    names = list(app.designer.scenes.keys())
    if len(names) <= 1:
        app._set_status("Only one scene — nowhere to broadcast.", ttl_sec=2.0)
        return
    current = app.designer.current_scene
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    total_copied = 0
    scenes_touched = 0
    for name in names:
        if name == current:
            continue
        target = app.designer.scenes.get(name)
        if target is None:
            continue
        for idx in app.state.selected:
            if not (0 <= idx < len(sc.widgets)):
                continue
            nw = WidgetConfig(**asdict(sc.widgets[idx]))
            target.widgets.append(nw)
            total_copied += 1
        scenes_touched += 1
    app._set_status(
        f"Broadcast {total_copied} widget(s) to {scenes_touched} scene(s).", ttl_sec=2.0
    )
    app._mark_dirty()


def quick_clone(app) -> None:
    """Duplicate selected widgets with a GRID offset to the right and down."""
    if not app.state.selected:
        app._set_status("Quick clone: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    new_indices: List[int] = []
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        nw = WidgetConfig(**asdict(sc.widgets[idx]))
        nw.x = min(int(sc.width) - max(1, int(nw.width)), int(nw.x) + GRID)
        nw.y = min(int(sc.height) - max(1, int(nw.height)), int(nw.y) + GRID)
        sc.widgets.append(nw)
        new_indices.append(len(sc.widgets) - 1)
    if new_indices:
        app._set_selection(new_indices, anchor_idx=new_indices[0])
    app._set_status(f"Cloned {len(new_indices)} widget(s) +{GRID}px.", ttl_sec=2.0)
    app._mark_dirty()


def extract_to_new_scene(app) -> None:
    """Move selected widgets to a new scene (removes from current)."""
    if not app.state.selected:
        app._set_status("Extract: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    # Collect widgets
    widgets_to_move = []
    for idx in sorted(app.state.selected):
        if 0 <= idx < len(sc.widgets):
            widgets_to_move.append(sc.widgets[idx])
    if not widgets_to_move:
        return
    # Create new scene
    names = list(app.designer.scenes.keys())
    base = f"{app.designer.current_scene}_extract"
    num = 1
    name = base
    while name in names:
        num += 1
        name = f"{base}_{num}"
    new_sc = SceneConfig(
        name=name,
        width=sc.width,
        height=sc.height,
        widgets=list(widgets_to_move),
        bg_color=sc.bg_color,
        theme=sc.theme,
    )
    app.designer.scenes[name] = new_sc
    # Remove from current scene (reverse order to keep indices valid)
    for idx in sorted(app.state.selected, reverse=True):
        if 0 <= idx < len(sc.widgets):
            sc.widgets.pop(idx)
    count = len(widgets_to_move)
    app.designer.current_scene = name
    app.state.selected = list(range(count))
    app.state.selected_idx = 0 if count else None
    app.designer.selected_widget = app.state.selected_idx
    app._set_status(f"Extracted {count} widget(s) to '{name}'.", ttl_sec=2.0)
    app._mark_dirty()


def duplicate_below(app) -> None:
    """Duplicate selected widgets and place them directly below."""
    if not app.state.selected:
        app._set_status("Dup below: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    max_y = max(int(sc.widgets[i].y) + int(sc.widgets[i].height or 0) for i in valid)
    min_y = min(int(sc.widgets[i].y) for i in valid)
    offset_y = max_y - min_y + GRID
    new_indices = []
    for i in valid:
        orig = sc.widgets[i]
        d = asdict(orig)
        d["y"] = int(orig.y) + offset_y
        new_w = WidgetConfig(
            **{k: v for k, v in d.items() if k in WidgetConfig.__dataclass_fields__}
        )
        sc.widgets.append(new_w)
        new_indices.append(len(sc.widgets) - 1)
    app.state.selected = new_indices
    app._set_status(f"Duplicated {len(new_indices)} below.", ttl_sec=2.0)
    app._mark_dirty()


def duplicate_right(app) -> None:
    """Duplicate selected widgets and place them to the right."""
    if not app.state.selected:
        app._set_status("Dup right: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    max_x = max(int(sc.widgets[i].x) + int(sc.widgets[i].width or 0) for i in valid)
    min_x = min(int(sc.widgets[i].x) for i in valid)
    offset_x = max_x - min_x + GRID
    new_indices = []
    for i in valid:
        orig = sc.widgets[i]
        d = asdict(orig)
        d["x"] = int(orig.x) + offset_x
        new_w = WidgetConfig(
            **{k: v for k, v in d.items() if k in WidgetConfig.__dataclass_fields__}
        )
        sc.widgets.append(new_w)
        new_indices.append(len(sc.widgets) - 1)
    app.state.selected = new_indices
    app._set_status(f"Duplicated {len(new_indices)} to the right.", ttl_sec=2.0)
    app._mark_dirty()


def export_selection_json(app) -> None:
    """Copy selected widgets as a JSON snippet to the system clipboard."""
    if not app.state.selected:
        app._set_status("Export JSON: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    widgets = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            widgets.append(asdict(sc.widgets[idx]))
    if not widgets:
        return
    text = json.dumps(widgets, indent=2, ensure_ascii=False)
    try:
        pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
    except Exception:
        pass
