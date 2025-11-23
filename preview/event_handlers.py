"""Mouse and keyboard event handlers for preview window."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import tkinter as tk

    from ui_models import WidgetConfig


class EventHandlers:
    """Mixin class for mouse and keyboard event handling."""

    # These will be provided by VisualPreviewWindow
    canvas: tk.Canvas
    designer: any
    settings: any
    selected_widget_idx: Optional[int]
    selected_widgets: list
    dragging: bool
    drag_start_x: int
    drag_start_y: int
    resize_handle: Optional[str]
    hovered_handle: Optional[str]
    alignment_guides: list

    def _canvas_to_widget_coords(self, canvas_x: int, canvas_y: int) -> tuple[int, int]:
        """Convert canvas event coords to logical widget coords."""
        try:
            abs_x = int(self.canvas.canvasx(canvas_x))
            abs_y = int(self.canvas.canvasy(canvas_y))
        except Exception:
            abs_x, abs_y = canvas_x, canvas_y
        widget_x = int(abs_x / self.settings.zoom)
        widget_y = int(abs_y / self.settings.zoom)

        if self.settings.snap_enabled:
            snap = self._get_scaled_snap_size()
            widget_x = round(widget_x / snap) * snap
            widget_y = round(widget_y / snap) * snap

        return widget_x, widget_y

    def _find_widget_at(self, x: int, y: int) -> Optional[int]:
        """Find widget at canvas coordinates."""
        if not self.designer.current_scene:
            return None

        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return None

        wx, wy = self._canvas_to_widget_coords(x, y)

        for idx in reversed(range(len(scene.widgets))):
            widget = scene.widgets[idx]
            if not widget.visible:
                continue

            if (
                widget.x <= wx < widget.x + widget.width
                and widget.y <= wy < widget.y + widget.height
            ):
                return idx

        return None

    def _find_resize_handle(self, x: int, y: int) -> Optional[str]:
        """Find which resize handle is at position."""
        if self.selected_widget_idx is None:
            return None

        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return None

        widget = scene.widgets[self.selected_widget_idx]
        wx, wy = self._canvas_to_widget_coords(x, y)

        try:
            spacing_scale, _ = self._get_responsive_scales()
            tolerance = max(6, int(6 * spacing_scale))
        except Exception:
            tolerance = 6

        handles = [
            (widget.x, widget.y, "nw"),
            (widget.x + widget.width, widget.y, "ne"),
            (widget.x + widget.width, widget.y + widget.height, "se"),
            (widget.x, widget.y + widget.height, "sw"),
            (widget.x + widget.width // 2, widget.y, "n"),
            (widget.x + widget.width // 2, widget.y + widget.height, "s"),
            (widget.x, widget.y + widget.height // 2, "w"),
            (widget.x + widget.width, widget.y + widget.height // 2, "e"),
        ]

        for hx, hy, handle_type in handles:
            if abs(wx - hx) <= tolerance and abs(wy - hy) <= tolerance:
                return handle_type

        return None

    def _get_scaled_snap_size(self) -> int:
        """Get snap size scaled for current zoom/responsive tier."""
        try:
            spacing_scale, _ = self._get_responsive_scales()
            return max(1, int(self.settings.snap_size * spacing_scale))
        except Exception:
            return self.settings.snap_size

    def _apply_widget_snapping(
        self, widget: "WidgetConfig", new_x: int, new_y: int
    ) -> tuple[int, int]:
        """Apply magnetic snapping to widget edges."""
        old_x, old_y = widget.x, widget.y
        widget.x = new_x
        widget.y = new_y

        guides = self._find_alignment_guides(widget)

        widget.x = old_x
        widget.y = old_y

        snapped_x, snapped_y = new_x, new_y

        for direction, position, label in guides:
            if direction == "v":
                if "left" in label:
                    snapped_x = position
                elif "right" in label:
                    snapped_x = position - widget.width
                elif "center" in label:
                    snapped_x = position - widget.width // 2
            elif direction == "h":
                if "top" in label:
                    snapped_y = position
                elif "bottom" in label:
                    snapped_y = position - widget.height
                elif "center" in label:
                    snapped_y = position - widget.height // 2

        widget.x = snapped_x
        widget.y = snapped_y
        self.alignment_guides = self._find_alignment_guides(widget)
        widget.x = old_x
        widget.y = old_y

        return snapped_x, snapped_y
