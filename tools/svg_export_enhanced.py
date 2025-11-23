"""Enhanced SVG export with gradients, shadows, patterns, and font embedding.

Professional-quality vector exports for ESP32 UI designs.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import Enum
from html import escape
from pathlib import Path
from typing import List, Optional, Tuple

__all__ = ["EnhancedSVGExporter", "ExportPreset", "ExportOptions"]


class ExportPreset(str, Enum):
    """Pre-configured export quality presets"""
    WEB_OPTIMIZED = "web"      # Smaller file size, basic features
    PRINT_QUALITY = "print"    # Full features, optimized for print
    HIGH_FIDELITY = "hifi"     # Maximum quality, all features enabled


@dataclass
class ExportOptions:
    """Configuration for SVG export"""
    preset: ExportPreset = ExportPreset.WEB_OPTIMIZED
    scale: float = 1.0
    include_gradients: bool = True
    include_shadows: bool = True
    include_patterns: bool = False
    embed_fonts: bool = False
    font_path: Optional[str] = None
    optimize_size: bool = True
    include_metadata: bool = True
    
    @classmethod
    def from_preset(cls, preset: ExportPreset) -> "ExportOptions":
        """Create options from preset"""
        if preset == ExportPreset.WEB_OPTIMIZED:
            return cls(
                preset=preset,
                include_gradients=True,
                include_shadows=False,
                include_patterns=False,
                embed_fonts=False,
                optimize_size=True,
            )
        elif preset == ExportPreset.PRINT_QUALITY:
            return cls(
                preset=preset,
                include_gradients=True,
                include_shadows=True,
                include_patterns=True,
                embed_fonts=False,
                optimize_size=False,
            )
        elif preset == ExportPreset.HIGH_FIDELITY:
            return cls(
                preset=preset,
                include_gradients=True,
                include_shadows=True,
                include_patterns=True,
                embed_fonts=True,
                optimize_size=False,
            )
        return cls()


class EnhancedSVGExporter:
    """Professional SVG exporter with advanced features"""
    
    COLOR_MAP = {
        "black": "#000000",
        "white": "#ffffff",
        "red": "#d32f2f",
        "green": "#388e3c",
        "blue": "#1976d2",
        "yellow": "#fbc02d",
        "magenta": "#c2185b",
        "cyan": "#0097a7",
        "gray": "#666666",
    }
    
    def __init__(self, options: Optional[ExportOptions] = None):
        self.options = options or ExportOptions()
        self._gradient_defs: List[str] = []
        self._shadow_defs: List[str] = []
        self._pattern_defs: List[str] = []
        self._font_defs: List[str] = []
        self._next_id = 0
    
    def _get_id(self, prefix: str = "elem") -> str:
        """Generate unique ID for SVG elements"""
        uid = f"{prefix}_{self._next_id}"
        self._next_id += 1
        return uid
    
    def _color(self, c: str, default: str = "#333333") -> str:
        """Convert color name to hex"""
        if not c:
            return default
        c_low = c.lower()
        if c_low in self.COLOR_MAP:
            return self.COLOR_MAP[c_low]
        # Assume hex if starts with #
        if c_low.startswith("#"):
            return c_low
        return default
    
    def _create_linear_gradient(
        self, 
        color_start: str, 
        color_end: str, 
        angle: float = 0
    ) -> Tuple[str, str]:
        """Create linear gradient definition, return (id, def_xml)"""
        gid = self._get_id("grad_linear")
        # Convert angle to x1,y1,x2,y2 (0° = top to bottom)
        import math
        rad = math.radians(angle)
        x1, y1 = 0.5 - 0.5 * math.sin(rad), 0.5 - 0.5 * math.cos(rad)
        x2, y2 = 0.5 + 0.5 * math.sin(rad), 0.5 + 0.5 * math.cos(rad)
        
        grad_def = (
            f'  <linearGradient id="{gid}" x1="{x1:.2%}" y1="{y1:.2%}" '
            f'x2="{x2:.2%}" y2="{y2:.2%}">\n'
            f'    <stop offset="0%" stop-color="{color_start}" />\n'
            f'    <stop offset="100%" stop-color="{color_end}" />\n'
            f'  </linearGradient>\n'
        )
        return gid, grad_def
    
    def _create_radial_gradient(
        self,
        color_center: str,
        color_edge: str,
        cx: float = 0.5,
        cy: float = 0.5,
    ) -> Tuple[str, str]:
        """Create radial gradient definition"""
        gid = self._get_id("grad_radial")
        grad_def = (
            f'  <radialGradient id="{gid}" cx="{cx:.2%}" cy="{cy:.2%}">\n'
            f'    <stop offset="0%" stop-color="{color_center}" />\n'
            f'    <stop offset="100%" stop-color="{color_edge}" />\n'
            f'  </radialGradient>\n'
        )
        return gid, grad_def
    
    def _create_drop_shadow(
        self,
        blur: float = 2.0,
        offset_x: float = 2.0,
        offset_y: float = 2.0,
        opacity: float = 0.5,
    ) -> Tuple[str, str]:
        """Create drop shadow filter definition"""
        fid = self._get_id("shadow_drop")
        filter_def = (
            f'  <filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">\n'
            f'    <feGaussianBlur in="SourceAlpha" stdDeviation="{blur}" />\n'
            f'    <feOffset dx="{offset_x}" dy="{offset_y}" result="offsetblur" />\n'
            f'    <feComponentTransfer>\n'
            f'      <feFuncA type="linear" slope="{opacity}" />\n'
            f'    </feComponentTransfer>\n'
            f'    <feMerge>\n'
            f'      <feMergeNode />\n'
            f'      <feMergeNode in="SourceGraphic" />\n'
            f'    </feMerge>\n'
            f'  </filter>\n'
        )
        return fid, filter_def
    
    def _create_inner_shadow(
        self,
        blur: float = 2.0,
        offset_x: float = 2.0,
        offset_y: float = 2.0,
        opacity: float = 0.5,
    ) -> Tuple[str, str]:
        """Create inner shadow filter definition"""
        fid = self._get_id("shadow_inner")
        filter_def = (
            f'  <filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">\n'
            f'    <feFlood flood-color="black" flood-opacity="{opacity}" result="flood" />\n'
            f'    <feComposite in="flood" in2="SourceGraphic" operator="out" result="inverse" />\n'
            f'    <feGaussianBlur in="inverse" stdDeviation="{blur}" result="blurred" />\n'
            f'    <feOffset in="blurred" dx="{offset_x}" dy="{offset_y}" result="offsetblur" />\n'
            f'    <feComposite in="offsetblur" in2="SourceGraphic" operator="in" result="inner" />\n'
            f'    <feMerge>\n'
            f'      <feMergeNode in="SourceGraphic" />\n'
            f'      <feMergeNode in="inner" />\n'
            f'    </feMerge>\n'
            f'  </filter>\n'
        )
        return fid, filter_def
    
    def _create_pattern(
        self,
        pattern_type: str = "dots",
        color: str = "#ffffff",
        spacing: int = 10,
    ) -> Tuple[str, str]:
        """Create pattern fill definition"""
        pid = self._get_id("pattern")
        
        if pattern_type == "dots":
            content = f'    <circle cx="5" cy="5" r="2" fill="{color}" opacity="0.3" />\n'
        elif pattern_type == "lines":
            content = f'    <line x1="0" y1="0" x2="0" y2="{spacing}" stroke="{color}" stroke-width="1" opacity="0.3" />\n'
        elif pattern_type == "grid":
            content = (
                f'    <line x1="0" y1="0" x2="{spacing}" y2="0" stroke="{color}" stroke-width="1" opacity="0.2" />\n'
                f'    <line x1="0" y1="0" x2="0" y2="{spacing}" stroke="{color}" stroke-width="1" opacity="0.2" />\n'
            )
        else:
            content = f'    <rect width="{spacing//2}" height="{spacing//2}" fill="{color}" opacity="0.1" />\n'
        
        pattern_def = (
            f'  <pattern id="{pid}" x="0" y="0" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse">\n'
            f'{content}'
            f'  </pattern>\n'
        )
        return pid, pattern_def
    
    def _embed_font(self, font_path: str) -> Optional[str]:
        """Embed font file as base64 data URI"""
        if not os.path.exists(font_path):
            return None
        
        try:
            with open(font_path, "rb") as f:
                font_data = f.read()
            
            b64_data = base64.b64encode(font_data).decode("utf-8")
            font_ext = Path(font_path).suffix.lower()
            
            # Detect font format
            if font_ext == ".ttf":
                font_format = "truetype"
            elif font_ext == ".otf":
                font_format = "opentype"
            elif font_ext == ".woff":
                font_format = "woff"
            elif font_ext == ".woff2":
                font_format = "woff2"
            else:
                return None
            
            font_def = (
                f'  <style>\n'
                f'    @font-face {{\n'
                f'      font-family: "EmbeddedFont";\n'
                f'      src: url("data:font/{font_format};base64,{b64_data}");\n'
                f'    }}\n'
                f'  </style>\n'
            )
            return font_def
        except Exception:
            return None
    
    def _widget_to_svg(self, widget, scale: float = 1.0) -> List[str]:
        """Convert widget to SVG elements with enhanced features"""
        if not getattr(widget, "visible", True):
            return []
        
        x = int(widget.x * scale)
        y = int(widget.y * scale)
        w = int(widget.width * scale)
        h = int(widget.height * scale)
        fg = self._color(getattr(widget, "color_fg", "white"))
        bg = self._color(getattr(widget, "color_bg", "black"))
        
        lines: List[str] = []
        tag = escape(getattr(widget, "type", "widget"))
        
        # Determine if widget should have gradient background
        use_gradient = self.options.include_gradients and tag in ("button", "panel", "gauge")
        use_shadow = self.options.include_shadows and tag in ("button", "panel")
        use_pattern = self.options.include_patterns and tag == "panel"
        
        # Build style
        style_parts = []
        fill_value = bg
        filter_value = None
        
        if use_gradient:
            # Create subtle gradient
            lighter_bg = self._lighten_color(bg, 0.2)
            gid, gdef = self._create_linear_gradient(lighter_bg, bg, angle=135)
            self._gradient_defs.append(gdef)
            fill_value = f"url(#{gid})"
        
        if use_pattern:
            pid, pdef = self._create_pattern("dots", fg, spacing=8)
            self._pattern_defs.append(pdef)
            # Layer pattern over gradient/solid
            lines.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                f'fill="url(#{pid})" opacity="0.1" rx="3" ry="3" />'
            )
        
        if use_shadow:
            sid, sdef = self._create_drop_shadow(blur=2, offset_x=2, offset_y=2, opacity=0.3)
            self._shadow_defs.append(sdef)
            filter_value = f"url(#{sid})"
        
        style_parts.append(f"fill:{fill_value}")
        style_parts.append(f"stroke:{fg}")
        style_parts.append("stroke-width:1")
        style = ";".join(style_parts)
        
        # Main rectangle
        filter_attr = f' filter="{filter_value}"' if filter_value else ''
        lines.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'style="{style}" rx="3" ry="3"{filter_attr} />'
        )
        
        # Text overlay
        text = escape(getattr(widget, "text", ""))
        if text:
            tx = x + w / 2
            ty = y + h / 2 + 4
            font_family = 'EmbeddedFont, monospace' if self.options.embed_fonts else 'monospace'
            lines.append(
                f'<text x="{tx}" y="{ty}" text-anchor="middle" '
                f'font-family="{font_family}" font-size="12" fill="{fg}">{text}</text>'
            )
        
        # Progress indicator for gauges/sliders
        if tag in ("gauge", "progressbar", "slider"):
            try:
                val = getattr(widget, "value", 0)
                min_val = getattr(widget, "min_value", 0)
                max_val = getattr(widget, "max_value", 100)
                
                if max_val > min_val:
                    pct = (val - min_val) / (max_val - min_val)
                    pct = max(0.0, min(1.0, pct))
                    bar_w = int((w - 4) * pct)
                    
                    # Gradient for progress bar
                    if self.options.include_gradients:
                        bright_fg = self._lighten_color(fg, 0.3)
                        gid, gdef = self._create_linear_gradient(bright_fg, fg, angle=90)
                        self._gradient_defs.append(gdef)
                        bar_fill = f"url(#{gid})"
                    else:
                        bar_fill = fg
                    
                    lines.append(
                        f'<rect x="{x+2}" y="{y + h//2}" width="{bar_w}" height="4" '
                        f'fill="{bar_fill}" rx="2" ry="2" />'
                    )
            except Exception:
                pass
        
        return lines
    
    def _lighten_color(self, hex_color: str, amount: float = 0.2) -> str:
        """Lighten a hex color by amount (0.0-1.0)"""
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = min(255, int(r + (255 - r) * amount))
            g = min(255, int(g + (255 - g) * amount))
            b = min(255, int(b + (255 - b) * amount))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color
    
    def _svg_header(self, width: int, height: int) -> str:
        """Generate SVG header with metadata"""
        header = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" stroke-linejoin="round">',
        ]
        
        if self.options.include_metadata:
            header.append('  <metadata>')
            header.append('    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">')
            header.append('      <rdf:Description>')
            header.append('        <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">ESP32 UI Design</dc:title>')
            header.append(f'        <dc:description xmlns:dc="http://purl.org/dc/elements/1.1/">Exported with preset: {self.options.preset}</dc:description>')
            header.append('      </rdf:Description>')
            header.append('    </rdf:RDF>')
            header.append('  </metadata>')
        
        return "\n".join(header) + "\n"
    
    def _svg_defs(self) -> str:
        """Generate <defs> section with gradients, filters, patterns"""
        if not any([self._gradient_defs, self._shadow_defs, self._pattern_defs, self._font_defs]):
            return ""
        
        parts = ["  <defs>"]
        parts.extend(self._font_defs)
        parts.extend(self._gradient_defs)
        parts.extend(self._shadow_defs)
        parts.extend(self._pattern_defs)
        parts.append("  </defs>")
        return "\n".join(parts) + "\n"
    
    def export_scene(self, scene, filename: str) -> str:
        """Export scene to enhanced SVG file"""
        # Reset definitions
        self._gradient_defs = []
        self._shadow_defs = []
        self._pattern_defs = []
        self._font_defs = []
        self._next_id = 0
        
        # Embed font if requested
        if self.options.embed_fonts and self.options.font_path:
            font_def = self._embed_font(self.options.font_path)
            if font_def:
                self._font_defs.append(font_def)
        
        width = int(scene.width * self.options.scale)
        height = int(scene.height * self.options.scale)
        
        # First pass: render widgets to collect defs
        widget_lines: List[str] = []
        for widget in getattr(scene, 'widgets', []):
            for line in self._widget_to_svg(widget, self.options.scale):
                widget_lines.append(f'  {line}')
        
        # Now build SVG with collected defs
        parts: List[str] = [self._svg_header(width, height)]
        parts.append(self._svg_defs())  # Defs now populated from widget rendering
        
        # Background
        bg_color = self._color(getattr(scene, 'bg_color', 'black'))
        parts.append(f'  <rect x="0" y="0" width="{width}" height="{height}" fill="{bg_color}" />')
        
        # Add pre-rendered widgets
        parts.extend(widget_lines)
        
        parts.append("</svg>")
        
        svg_content = "\n".join(parts)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        return filename
    
    def export_scene_to_string(self, scene) -> str:
        """Export scene to SVG string (non-persistent)"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as tmp:
            tmp_path = tmp.name
        
        try:
            self.export_scene(scene, tmp_path)
            with open(tmp_path, 'r', encoding='utf-8') as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
