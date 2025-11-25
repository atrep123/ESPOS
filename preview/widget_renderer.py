"""Widget rendering pipeline - geometry, colors, painting stages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict, Optional, Tuple

    from PIL import ImageDraw

    from ui_models import WidgetConfig

# Import at runtime for actual use
from design_tokens import color_hex  # noqa: F401
from ui_models import WidgetType  # noqa: F401


class WidgetRenderer:
    """Mixin class for widget rendering methods."""

    # These will be provided by VisualPreviewWindow
    settings: Any

    def _get_color(self, color_name: str) -> Tuple[int, int, int]:
        """Convert color name to RGB tuple."""
        colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
            "gray": (128, 128, 128),
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
        }
        return colors.get(color_name.lower(), (255, 255, 255))

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)

    def _clamp_rect_y_order(self, y0: int, y1: int) -> Tuple[int, int]:
        """Ensure y0 <= y1 for PIL rectangle drawing."""
        return (min(y0, y1), max(y0, y1))

    def _draw_widget(
        self,
        draw: ImageDraw.ImageDraw,
        widget: "WidgetConfig",
        selected: bool,
        overlay: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Draw a widget via helper stages (geometry, background, border, content)."""
        x, y, w, h = self._compute_widget_geometry(widget, overlay)
        fg_color, bg_color = self._resolve_widget_colors(widget)
        self._paint_widget_background(draw, x, y, w, h, bg_color)
        if widget.border:
            self._paint_widget_border(draw, x, y, w, h, widget, selected, fg_color)
        self._paint_widget_content(draw, x, y, w, h, widget, fg_color)

    def _compute_widget_geometry(
        self, widget: "WidgetConfig", overlay: Optional[Dict[str, Any]]
    ) -> Tuple[int, int, int, int]:
        """Compute final widget position and size with optional overlay transforms."""
        x, y = widget.x, widget.y
        w, h = widget.width or 1, widget.height or 1
        if overlay:
            try:
                if "x" in overlay:
                    x = int(overlay["x"])
                if "y" in overlay:
                    y = int(overlay["y"])
                if "x_offset" in overlay:
                    x += int(overlay["x_offset"])
                if "y_offset" in overlay:
                    y += int(overlay["y_offset"])
                if "scale" in overlay:
                    s = float(overlay["scale"])
                    cx, cy = x + w // 2, y + h // 2
                    w = max(1, int(w * s))
                    h = max(1, int(h * s))
                    x = cx - w // 2
                    y = cy - h // 2
            except Exception:
                pass
        return x, y, w, h

    def _resolve_widget_colors(
        self,
        widget: "WidgetConfig",
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Determine foreground and background colors for widget."""
        fg_color = self._get_color(widget.color_fg)
        bg_color = self._get_color(widget.color_bg)
        return fg_color, bg_color

    def _paint_widget_background(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        bg_color: Tuple[int, int, int],
    ) -> None:
        """Fill widget background."""
        try:
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg_color)
        except Exception:
            pass

    def _paint_widget_border(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: "WidgetConfig",
        selected: bool,
        base_color: Tuple[int, int, int],
    ) -> None:
        """Draw widget border with style."""
        try:
            border_color = base_color
            if selected:
                if getattr(self.settings, "high_contrast_overlays", False):
                    border_color = self._hex_to_rgb(color_hex("theme_hc_primary"))
                else:
                    border_color = (0, 150, 255)

            style = getattr(widget, "border_style", "single")
            sel_width = (
                2 if (selected and getattr(self.settings, "high_contrast_overlays", False)) else 1
            )

            if style == "single":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=sel_width)
            elif style == "double":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
                draw.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], outline=border_color, width=1)
            elif style == "bold":
                bold_width = (
                    3
                    if (selected and getattr(self.settings, "high_contrast_overlays", False))
                    else 2
                )
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=bold_width)
            elif style == "dashed":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
        except Exception:
            pass

    def _paint_widget_content(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: "WidgetConfig",
        fg_color: Tuple[int, int, int],
    ) -> None:
        """Draw widget-specific content (text, gauge arc, slider thumb, etc.)."""
        try:
            wt = widget.type

            if wt == WidgetType.LABEL.value:
                self._draw_text(
                    draw,
                    widget.text,
                    x + widget.padding_x,
                    y + widget.padding_y,
                    w - 2 * widget.padding_x,
                    h - 2 * widget.padding_y,
                    fg_color,
                    widget.align,
                    widget.valign,
                )
            elif wt == WidgetType.BUTTON.value:
                self._draw_text(draw, widget.text, x, y, w, h, fg_color, "center", "middle")
            elif wt == WidgetType.CHECKBOX.value:
                self._paint_checkbox(draw, x, y, w, h, widget, fg_color)
            elif wt == WidgetType.PROGRESSBAR.value:
                self._paint_progressbar(draw, x, y, w, h, widget, fg_color)
            elif wt == WidgetType.GAUGE.value:
                self._paint_gauge(draw, x, y, w, h, widget, fg_color)
            elif wt == WidgetType.SLIDER.value:
                self._paint_slider(draw, x, y, w, h, widget, fg_color)
        except Exception:
            pass

    def _paint_checkbox(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: "WidgetConfig",
        fg_color: Tuple[int, int, int],
    ) -> None:
        """Paint checkbox widget."""
        box_size = max(0, min(h - 4, 6))
        box_x = x + 2
        box_y = y + (h - box_size) // 2
        y0, y1 = self._clamp_rect_y_order(box_y, box_y + box_size)
        draw.rectangle([box_x, y0, box_x + box_size, y1], outline=fg_color, width=1)

        if widget.checked:
            draw.line(
                [(box_x + 1, box_y + 1), (box_x + box_size - 1, box_y + box_size - 1)],
                fill=fg_color,
                width=1,
            )
            draw.line(
                [(box_x + 1, box_y + box_size - 1), (box_x + box_size - 1, box_y + 1)],
                fill=fg_color,
                width=1,
            )

        if widget.text:
            self._draw_text(
                draw,
                widget.text,
                box_x + box_size + 2,
                y,
                w - box_size - 4,
                h,
                fg_color,
                "left",
                "middle",
            )

    def _paint_progressbar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: "WidgetConfig",
        fg_color: Tuple[int, int, int],
    ) -> None:
        """Paint progress bar widget."""
        span = max(0, (w - 4))
        denom = max(1, (widget.max_value - widget.min_value))
        progress = int((widget.value - widget.min_value) / denom * span)

        if progress > 0:
            x0 = x + 2
            y_top = y + 2
            y_bottom = y + h - 3
            y0, y1 = self._clamp_rect_y_order(y_top, y_bottom)
            x1 = x0 + progress
            x1 = min(x + w - 2, max(x0, x1))
            draw.rectangle([x0, y0, x1, y1], fill=fg_color)

    def _paint_gauge(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: "WidgetConfig",
        fg_color: Tuple[int, int, int],
    ) -> None:
        """Paint gauge widget."""
        center_x = x + w // 2
        center_y = y + h // 2
        radius = max(1, min(w, h) // 2 - 2)
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            outline=fg_color,
            width=1,
        )
        self._draw_text(draw, str(widget.value), x, y, w, h, fg_color, "center", "middle")

    def _paint_slider(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: "WidgetConfig",
        fg_color: Tuple[int, int, int],
    ) -> None:
        """Paint slider widget."""
        track_y = y + h // 2
        draw.line([(x + 2, track_y), (x + w - 2, track_y)], fill=fg_color, width=1)

        span = max(0, (w - 4))
        denom = max(1, (widget.max_value - widget.min_value))
        handle_x = x + 2 + int((widget.value - widget.min_value) / denom * span)

        x0 = max(x + 2, min(handle_x - 2, x + w - 2))
        x1 = max(x + 2, min(handle_x + 2, x + w - 2))
        y_top = y + 2
        y_bottom = y + h - 2
        y0, y1 = self._clamp_rect_y_order(y_top, y_bottom)
        draw.rectangle([x0, y0, x1, y1], fill=fg_color, outline=fg_color)

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        w: int,
        h: int,
        color: Tuple[int, int, int],
        align: str = "left",
        valign: str = "top",
    ) -> None:
        """Draw text with alignment (simple placeholder - no font rendering)."""
        # Simple 1px horizontal line as text placeholder
        # Actual text rendering requires font metrics from Pillow
        try:
            cy = y + h // 2
            if align == "center":
                x_start = x + 2
                x_end = x + w - 2
            elif align == "right":
                x_start = x + w - min(20, w - 4)
                x_end = x + w - 2
            else:  # left
                x_start = x + 2
                x_end = x + min(20, w - 4)

            if valign == "middle":
                y_line = cy
            elif valign == "bottom":
                y_line = y + h - 4
            else:  # top
                y_line = y + 4

            draw.line([(x_start, y_line), (x_end, y_line)], fill=color, width=1)
        except Exception:
            pass
