"""Grid and overlay rendering for preview canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Tuple

    from PIL import ImageDraw


class OverlayRenderer:
    """Mixin class for drawing grid, guides, and debug overlays."""

    # These will be provided by VisualPreviewWindow
    settings: any
    designer: any
    alignment_guides: List[Tuple[str, int, str]]
    selected_widget_idx: int | None

    def _draw_grid(self, draw: "ImageDraw.ImageDraw", width: int, height: int) -> None:
        """Draw grid overlay with configurable padding and color."""
        if not self.settings.grid_enabled:
            return

        try:
            step = self.settings.grid_size
            if step < 1:
                return

            # Calculate padding (percentage of step + minimum px)
            pad_pct = getattr(self.settings, "grid_padding_pct", 0.10)
            pad_min = getattr(self.settings, "grid_padding_min_px", 2)
            padding = max(pad_min, int(step * pad_pct))

            # Choose grid color based on high-contrast mode
            hc_mode = getattr(self.settings, "high_contrast_overlays", False)
            if hc_mode:
                grid_rgb = getattr(self.settings, "grid_color_light", (50, 50, 50))
            else:
                grid_rgb = getattr(self.settings, "grid_color_dark", (36, 36, 36))

            # Vertical lines (with padding at left/right)
            x = padding
            while x < width - padding:
                draw.line([(x, 0), (x, height)], fill=grid_rgb, width=1)
                x += step

            # Horizontal lines (with padding at top/bottom)
            y = padding
            while y < height - padding:
                draw.line([(0, y), (width, y)], fill=grid_rgb, width=1)
                y += step

        except Exception:
            pass

    def _draw_guides_overlay(self) -> None:
        """Draw alignment guide lines on canvas."""
        if not self.settings.show_alignment_guides or not self.alignment_guides:
            return

        try:
            from design_tokens import color_hex

            zoom = self.settings.zoom
            guide_color = (
                color_hex("theme_hc_primary")
                if getattr(self.settings, "high_contrast_overlays", False)
                else color_hex("legacy_green_lime")
            )

            for direction, position, _label in self.alignment_guides:
                if direction == "v":  # Vertical guide
                    x = int(position * zoom)
                    self.canvas.create_line(
                        x,
                        0,
                        x,
                        int(self.designer.height * zoom),
                        fill=guide_color,
                        width=1,
                        dash=(4, 4),
                    )
                elif direction == "h":  # Horizontal guide
                    y = int(position * zoom)
                    self.canvas.create_line(
                        0,
                        y,
                        int(self.designer.width * zoom),
                        y,
                        fill=guide_color,
                        width=1,
                        dash=(4, 4),
                    )
        except Exception:
            pass

    def _draw_debug_overlay(self) -> None:
        """Draw a compact debug overlay with selection and scene info."""
        try:
            import tkinter as tk

            from design_tokens import color_hex

            z = self.settings.zoom
            x0, y0 = 8, int(self.designer.height * z) - 90
            x1, y1 = x0 + 360, y0 + 82
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray11"),
                stipple="gray25",
            )

            lines = []
            sc = (
                self.designer.scenes.get(self.designer.current_scene)
                if self.designer.current_scene
                else None
            )
            widget_count = len(sc.widgets) if sc else 0
            lines.append(
                f"Scene: {self.designer.current_scene or '-'}  "
                f"Size: {self.designer.width}x{self.designer.height}  "
                f"Zoom: {z:.1f}x  Widgets: {widget_count}"
            )

            if (
                self.selected_widget_idx is not None
                and sc
                and 0 <= self.selected_widget_idx < len(sc.widgets)
            ):
                w = sc.widgets[self.selected_widget_idx]
                lines.append(
                    f"Selected[{self.selected_widget_idx}]: {w.type} "
                    f"pos=({w.x},{w.y}) size={w.width}x{w.height} "
                    f"z={w.z_index} vis={1 if w.visible else 0} "
                    f"en={1 if w.enabled else 0}"
                )
            else:
                lines.append("Selected: none")

            lines.append(
                f"Guides:{'on' if self.settings.show_alignment_guides else 'off'} "
                f"Grid:{'on' if self.settings.grid_enabled else 'off'} "
                f"Snap:{'on' if self.settings.snap_enabled else 'off'} "
                f"Render:{self._last_render_ms:.1f} ms"
            )

            ty = y0 + 10
            for ln in lines:
                self.canvas.create_text(
                    x0 + 10, ty, anchor=tk.NW, text=ln, fill=color_hex("text_primary")
                )
                ty += 14
        except Exception:
            pass
