"""Lightweight enhanced SVG exporter used by tests and UI preview."""

from __future__ import annotations

import base64
import os
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

from design_tokens import color_hex
from ui_models import SceneConfig, WidgetConfig


class ExportPreset(Enum):
    WEB_OPTIMIZED = "web_optimized"
    PRINT_QUALITY = "print_quality"
    HIGH_FIDELITY = "high_fidelity"


@dataclass
class ExportOptions:
    scale: float = 1.0
    include_gradients: bool = True
    include_shadows: bool = False
    include_patterns: bool = False
    include_metadata: bool = True
    embed_fonts: bool = False
    optimize_size: bool = False
    preset: ExportPreset = ExportPreset.WEB_OPTIMIZED

    @classmethod
    def from_preset(cls, preset: ExportPreset) -> "ExportOptions":
        if preset == ExportPreset.PRINT_QUALITY:
            return cls(
                include_gradients=True,
                include_shadows=True,
                include_patterns=True,
                embed_fonts=False,
                optimize_size=False,
                preset=preset,
            )
        if preset == ExportPreset.HIGH_FIDELITY:
            return cls(
                include_gradients=True,
                include_shadows=True,
                include_patterns=True,
                embed_fonts=True,
                optimize_size=False,
                preset=preset,
            )
        # Default web-optimized
        return cls(
            include_gradients=True,
            include_shadows=False,
            include_patterns=False,
            embed_fonts=False,
            optimize_size=True,
            preset=preset,
        )


class EnhancedSVGExporter:
    """Generate SVG markup from SceneConfig data with optional styling effects."""

    def __init__(self, options: ExportOptions | None = None):
        self.options = options or ExportOptions.from_preset(ExportPreset.WEB_OPTIMIZED)
        self._id_counts: Dict[str, int] = {}

    # --- ID and color helpers -------------------------------------------------
    def _get_id(self, prefix: str) -> str:
        count = self._id_counts.get(prefix, 0) + 1
        self._id_counts[prefix] = count
        return f"{prefix}_{count}"

    def _color(self, value: str) -> str:
        palette = {
            "red": "#d32f2f",
            "white": "#ffffff",
            "black": "#000000",
            "gray": "#888888",
            "blue": color_hex("theme_default_primary"),
        }
        if not value:
            return "#333333"
        lower = value.lower()
        if lower in palette:
            return palette[lower]
        if value.startswith("#") and len(value) in (4, 7):
            return value.lower()
        return "#333333"

    def _lighten_color(self, value: str, factor: float) -> str:
        base = self._color(value).lstrip("#")
        try:
            r = int(base[0:2], 16)
            g = int(base[2:4], 16)
            b = int(base[4:6], 16)
        except ValueError:
            r = g = b = 51
        mix = lambda c: min(255, int(c + (255 - c) * factor))
        return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"

    # --- Def generators -------------------------------------------------------
    def _create_linear_gradient(self, start: str, end: str, angle: int = 0) -> Tuple[str, str]:
        gid = self._get_id("grad_linear")
        gradient = (
            f'<linearGradient id="{gid}" gradientTransform="rotate({angle})">'
            f'<stop offset="0%" stop-color="{self._color(start)}" />'
            f'<stop offset="100%" stop-color="{self._color(end)}" />'
            "</linearGradient>"
        )
        return gid, gradient

    def _create_radial_gradient(self, inner: str, outer: str) -> Tuple[str, str]:
        gid = self._get_id("grad_radial")
        gradient = (
            f'<radialGradient id="{gid}">'
            f'<stop offset="0%" stop-color="{self._color(inner)}" />'
            f'<stop offset="100%" stop-color="{self._color(outer)}" />'
            "</radialGradient>"
        )
        return gid, gradient

    def _create_drop_shadow(self, blur: float = 2.0, offset_x: float = 1.0, offset_y: float = 1.0) -> Tuple[str, str]:
        sid = self._get_id("shadow_drop")
        shadow = (
            f'<filter id="{sid}">'
            f'<feGaussianBlur in="SourceAlpha" stdDeviation="{blur}"/>'
            f'<feOffset dx="{offset_x}" dy="{offset_y}" result="offsetblur"/>'
            '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
            "</filter>"
        )
        return sid, shadow

    def _create_inner_shadow(self, blur: float = 2.0, offset_x: float = 1.0, offset_y: float = 1.0) -> Tuple[str, str]:
        sid = self._get_id("shadow_inner")
        shadow = (
            f'<filter id="{sid}" filterUnits="objectBoundingBox" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur in="SourceAlpha" stdDeviation="{blur}" result="blur"/>'
            f'<feOffset dx="{offset_x}" dy="{offset_y}" result="offsetBlur"/>'
            '<feComposite in="offsetBlur" in2="SourceGraphic" operator="atop"/>'
            "</filter>"
        )
        return sid, shadow

    def _create_pattern(self, pattern_type: str, color: str, spacing: int = 8) -> Tuple[str, str]:
        pid = self._get_id("pattern")
        color_hex_value = self._color(color)
        if pattern_type == "lines":
            pattern = (
                f'<pattern id="{pid}" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse">'
                f'<line x1="0" y1="0" x2="{spacing}" y2="{spacing}" stroke="{color_hex_value}" stroke-width="1"/>'
                "</pattern>"
            )
        elif pattern_type == "grid":
            pattern = (
                f'<pattern id="{pid}" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse">'
                f'<line x1="0" y1="0" x2="{spacing}" y2="0" stroke="{color_hex_value}" stroke-width="1"/>'
                f'<line x1="0" y1="0" x2="0" y2="{spacing}" stroke="{color_hex_value}" stroke-width="1"/>'
                "</pattern>"
            )
        else:  # dots
            radius = max(1, spacing // 4)
            cx = cy = spacing // 2
            pattern = (
                f'<pattern id="{pid}" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse">'
                f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color_hex_value}" />'
                "</pattern>"
            )
        return pid, pattern

    # --- Export helpers -------------------------------------------------------
    def _embed_font(self, path: str) -> str | None:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:font/ttf;base64,{encoded}"
        except Exception:
            return None

    def _build_defs(self) -> str:
        defs: List[str] = []
        if self.options.include_gradients:
            gid, gdef = self._create_linear_gradient("#4caf50", "#1b5e20", angle=90)
            defs.append(gdef)
            # include radial for variety
            _, rdef = self._create_radial_gradient("#ffffff", "#cccccc")
            defs.append(rdef)
            self._default_gradient_id = gid
        if self.options.include_shadows:
            sid, sdef = self._create_drop_shadow()
            defs.append(sdef)
            _, inner = self._create_inner_shadow()
            defs.append(inner)
            self._default_shadow_id = sid
        if self.options.include_patterns:
            _, pdef = self._create_pattern("dots", "#cccccc", spacing=8)
            defs.append(pdef)
        if not defs:
            return ""
        return "<defs>" + "".join(defs) + "</defs>"

    def _widget_rect(self, widget: WidgetConfig) -> str:
        if not getattr(widget, "visible", True):
            return ""
        x = int(widget.x * self.options.scale)
        y = int(widget.y * self.options.scale)
        w = int(widget.width * self.options.scale)
        h = int(widget.height * self.options.scale)
        fill = self._color(getattr(widget, "color_bg", "#000000"))
        stroke = self._color(getattr(widget, "color_fg", "#ffffff"))
        attrs = [f'x="{x}"', f'y="{y}"', f'width="{w}"', f'height="{h}"', f'fill="{fill}"', f'stroke="{stroke}"']
        if self.options.include_shadows and hasattr(self, "_default_shadow_id"):
            attrs.append(f'filter="url(#{self._default_shadow_id})"')
        if widget.type == "progressbar" and self.options.include_gradients and hasattr(self, "_default_gradient_id"):
            attrs.append(f'fill="url(#{self._default_gradient_id})"')
        return f"<rect {' '.join(attrs)} />"

    # --- Public API ----------------------------------------------------------
    def export_scene(self, scene: SceneConfig, path: str) -> str:
        svg = self.export_scene_to_string(scene)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        return path

    def export_scene_to_string(self, scene: SceneConfig) -> str:
        width = int(scene.width * self.options.scale)
        height = int(scene.height * self.options.scale)
        defs = self._build_defs()
        content: List[str] = []
        if defs:
            content.append(defs)

        # Render widgets
        for widget in scene.widgets:
            rect = self._widget_rect(widget)
            if rect:
                content.append(rect)
                if getattr(widget, "text", ""):
                    tx = int(widget.x * self.options.scale + 2)
                    ty = int(widget.y * self.options.scale + 12)
                    content.append(f'<text x="{tx}" y="{ty}" fill="{self._color(widget.color_fg)}">{widget.text}</text>')

        metadata = ""
        if self.options.include_metadata:
            metadata = "<metadata>ESP32 UI Design - Enhanced SVG Export</metadata>"

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f"{metadata}"
            f"{''.join(content)}"
            "</svg>"
        )
        return svg

