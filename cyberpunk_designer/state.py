"""Editor state: selection, mode, scene, canvas tracking."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from ui_designer import UIDesigner, WidgetConfig

from .constants import DEFAULT_JSON
from .layout import Layout


class EditorState:
    """UI state layered on top of UIDesigner backend."""

    def __init__(self, designer: UIDesigner, layout: Layout):
        self.designer = designer
        self.layout = layout
        self.selected_idx: Optional[int] = None
        self.selected: List[int] = []
        self.dragging = False
        self.resizing = False
        self.drag_offset = (0, 0)
        self.resize_anchor: Optional[str] = None
        self.drag_start_positions: Dict[int, Tuple[int, int]] = {}
        self.drag_start_sizes: Dict[int, Tuple[int, int]] = {}
        self.drag_start_rect: Optional[pygame.Rect] = None
        self.resize_start_rect: Optional[pygame.Rect] = None
        self.json_path = DEFAULT_JSON
        self.input_mode = False
        self.input_buffer = ""
        self.saved_this_drag = False
        self.drag_lock_axis: Optional[str] = None
        self.drag_rect: Optional[pygame.Rect] = None
        self.palette_scroll = 0
        self.inspector_scroll = 0
        self.box_select_start: Optional[Tuple[int, int]] = None
        self.box_select_rect: Optional[pygame.Rect] = None
        self.inspector_selected_field: Optional[str] = None
        self.inspector_input_buffer: str = ""
        self.active_guides: List[Tuple[str, int]] = []

    def selection_list(self) -> List[int]:
        """Return a copy of the selected indices (always a list, never None)."""
        return list(self.selected or [])

    def current_scene(self):
        """Return the active SceneConfig from the designer."""
        key = self.designer.current_scene or ""
        return self.designer.scenes[key]

    def selected_widget(self) -> Optional[WidgetConfig]:
        """Return the currently selected widget, or None if nothing is selected."""
        sc = self.current_scene()
        if self.selected_idx is None:
            return None
        if 0 <= self.selected_idx < len(sc.widgets):
            return sc.widgets[self.selected_idx]
        return None

    def select_at(self, pos: Tuple[int, int], origin_rect: pygame.Rect) -> Optional[int]:
        """Select the widget under *pos* (if any) and return its index."""
        hit = self.hit_test_at(pos, origin_rect)
        if hit is not None:
            self.selected_idx = hit
            self.selected = [hit]
        else:
            self.selected_idx = None
            self.selected = []
        self.designer.selected_widget = hit if hit is not None else None
        return hit

    def hit_test_at(self, pos: Tuple[int, int], origin_rect: pygame.Rect) -> Optional[int]:
        """Return the index of the topmost visible widget at *pos*, or None."""
        lx, ly = pos
        sc = self.current_scene()
        for idx in reversed(range(len(sc.widgets))):
            w = sc.widgets[idx]
            if not getattr(w, "visible", True):
                continue
            rect = pygame.Rect(w.x + origin_rect.x, w.y + origin_rect.y, w.width, w.height)
            if rect.collidepoint(lx, ly):
                return idx
        return None
