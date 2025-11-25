#!/usr/bin/env python3
"""
BDF (Bitmap Distribution Format) Font Parser and Renderer

Supports reading BDF font files and rendering text to 1bpp bitmaps.
Inspired by Lopaka's BDF font support for embedded displays.

BDF format is widely used for bitmap fonts, especially in embedded systems.
Popular sources: X11 fonts, GNU Unifont, Spleen fonts.

Usage:
    font = BDFFont.load("font.bdf")
    bitmap = font.render_text("Hello", spacing=1)
    width, height, data = bitmap
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import re


@dataclass
class BDFGlyph:
    """Single character glyph from BDF font."""
    
    encoding: int  # Unicode code point
    name: str  # Glyph name (e.g., "A", "space")
    bbox_width: int  # Bounding box width
    bbox_height: int  # Bounding box height
    bbox_x_offset: int  # X offset from origin
    bbox_y_offset: int  # Y offset from baseline
    dwidth_x: int  # Device width (advance width)
    dwidth_y: int  # Device height (usually 0)
    bitmap: List[int]  # Bitmap data as list of row values


class BDFFont:
    """BDF bitmap font parser and renderer."""
    
    def __init__(self):
        self.font_name = ""
        self.font_size = 0
        self.bbox_width = 0  # Font bounding box
        self.bbox_height = 0
        self.bbox_x_offset = 0
        self.bbox_y_offset = 0
        self.glyphs: Dict[int, BDFGlyph] = {}  # encoding -> glyph
        self.default_char = 0  # Fallback character (usually space)
    
    @classmethod
    def load(cls, filepath: str) -> "BDFFont":
        """
        Load BDF font from file.
        
        Args:
            filepath: Path to .bdf file
            
        Returns:
            BDFFont instance
        """
        font = cls()
        
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.rstrip() for line in f]
        
        font._parse_bdf(lines)
        return font
    
    def _parse_bdf(self, lines: List[str]) -> None:
        """Parse BDF file content."""
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("FONT "):
                self.font_name = line[5:].strip()
            
            elif line.startswith("SIZE "):
                parts = line.split()
                if len(parts) >= 2:
                    self.font_size = int(parts[1])
            
            elif line.startswith("FONTBOUNDINGBOX "):
                parts = line.split()
                if len(parts) >= 5:
                    self.bbox_width = int(parts[1])
                    self.bbox_height = int(parts[2])
                    self.bbox_x_offset = int(parts[3])
                    self.bbox_y_offset = int(parts[4])
            
            elif line.startswith("DEFAULT_CHAR "):
                self.default_char = int(line.split()[1])
            
            elif line.startswith("STARTCHAR "):
                # Parse glyph
                glyph = self._parse_glyph(lines, i)
                if glyph:
                    self.glyphs[glyph.encoding] = glyph
                    # Skip to end of glyph
                    while i < len(lines) and not lines[i].startswith("ENDCHAR"):
                        i += 1
            
            i += 1
    
    def _parse_glyph(self, lines: List[str], start_idx: int) -> Optional[BDFGlyph]:
        """Parse single glyph from BDF."""
        name = ""
        encoding = -1
        dwidth_x = 0
        dwidth_y = 0
        bbox_w = 0
        bbox_h = 0
        bbox_x = 0
        bbox_y = 0
        bitmap: List[int] = []
        
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("STARTCHAR "):
                name = line[10:].strip()
            
            elif line.startswith("ENCODING "):
                encoding = int(line.split()[1])
            
            elif line.startswith("DWIDTH "):
                parts = line.split()
                dwidth_x = int(parts[1])
                dwidth_y = int(parts[2]) if len(parts) > 2 else 0
            
            elif line.startswith("BBX "):
                parts = line.split()
                bbox_w = int(parts[1])
                bbox_h = int(parts[2])
                bbox_x = int(parts[3])
                bbox_y = int(parts[4])
            
            elif line.startswith("BITMAP"):
                # Read bitmap data
                i += 1
                while i < len(lines) and not lines[i].startswith("ENDCHAR"):
                    hex_line = lines[i].strip()
                    if hex_line:
                        bitmap.append(int(hex_line, 16))
                    i += 1
                break
            
            i += 1
        
        if encoding >= 0 and bitmap:
            return BDFGlyph(
                encoding=encoding,
                name=name,
                bbox_width=bbox_w,
                bbox_height=bbox_h,
                bbox_x_offset=bbox_x,
                bbox_y_offset=bbox_y,
                dwidth_x=dwidth_x,
                dwidth_y=dwidth_y,
                bitmap=bitmap
            )
        
        return None
    
    def get_glyph(self, char: str) -> Optional[BDFGlyph]:
        """Get glyph for character (or fallback to default)."""
        code = ord(char)
        if code in self.glyphs:
            return self.glyphs[code]
        elif self.default_char in self.glyphs:
            return self.glyphs[self.default_char]
        return None
    
    def render_text(
        self, text: str, spacing: int = 1, max_width: Optional[int] = None
    ) -> Tuple[int, int, bytes]:
        """
        Render text to 1bpp bitmap.
        
        Args:
            text: Text to render
            spacing: Extra pixels between characters
            max_width: Maximum width (None = unlimited)
            
        Returns:
            Tuple of (width, height, bitmap_data)
        """
        if not text:
            return (0, self.bbox_height, b"")
        
        # Calculate total width
        total_width = 0
        glyphs_to_render: List[BDFGlyph] = []
        
        for char in text:
            glyph = self.get_glyph(char)
            if glyph:
                glyphs_to_render.append(glyph)
                total_width += glyph.dwidth_x + spacing
        
        if glyphs_to_render:
            total_width -= spacing  # Remove trailing spacing
        
        if max_width and total_width > max_width:
            total_width = max_width
        
        height = self.bbox_height
        
        # Create bitmap buffer
        bytes_per_row = (total_width + 7) // 8
        bitmap = bytearray(bytes_per_row * height)
        
        # Render each glyph
        x_pos = 0
        for glyph in glyphs_to_render:
            if max_width and x_pos >= max_width:
                break
            
            self._render_glyph(bitmap, glyph, x_pos, total_width, height)
            x_pos += glyph.dwidth_x + spacing
        
        return (total_width, height, bytes(bitmap))
    
    def _render_glyph(
        self,
        bitmap: bytearray,
        glyph: BDFGlyph,
        x_pos: int,
        total_width: int,
        total_height: int
    ) -> None:
        """Render single glyph into bitmap buffer."""
        # Calculate glyph position
        glyph_x = x_pos + glyph.bbox_x_offset
        glyph_y = total_height - self.bbox_height + glyph.bbox_y_offset
        
        bytes_per_row = (total_width + 7) // 8
        
        # Render glyph bitmap
        for row_idx, row_data in enumerate(glyph.bitmap):
            y = glyph_y + row_idx
            if y < 0 or y >= total_height:
                continue
            
            # Extract bits from glyph row
            for bit_idx in range(glyph.bbox_width):
                x = glyph_x + bit_idx
                if x < 0 or x >= total_width:
                    continue
                
                # Check if bit is set in glyph
                bit_pos = glyph.bbox_width - 1 - bit_idx
                if row_data & (1 << bit_pos):
                    # Set bit in output bitmap (LSB first for XBM)
                    byte_idx = y * bytes_per_row + (x // 8)
                    bit_offset = x % 8
                    bitmap[byte_idx] |= 1 << bit_offset
    
    def get_text_width(self, text: str, spacing: int = 1) -> int:
        """Calculate width of rendered text."""
        if not text:
            return 0
        
        width = 0
        for char in text:
            glyph = self.get_glyph(char)
            if glyph:
                width += glyph.dwidth_x + spacing
        
        return width - spacing if width > 0 else 0
    
    def get_info(self) -> Dict[str, any]:
        """Get font information."""
        return {
            "name": self.font_name,
            "size": self.font_size,
            "bbox": (self.bbox_width, self.bbox_height),
            "glyphs": len(self.glyphs),
            "has_ascii": all(i in self.glyphs for i in range(32, 127))
        }


def create_simple_font() -> BDFFont:
    """Create a minimal 5x7 ASCII font for testing."""
    font = BDFFont()
    font.font_name = "Simple5x7"
    font.font_size = 7
    font.bbox_width = 5
    font.bbox_height = 7
    font.bbox_x_offset = 0
    font.bbox_y_offset = -1
    font.default_char = 32  # Space
    
    # Simple glyphs (space, A, B, C for demo)
    simple_glyphs = {
        32: ("space", 3, [0x00] * 7),  # Space
        65: ("A", 5, [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x00]),  # A
        66: ("B", 5, [0x1E, 0x11, 0x1E, 0x11, 0x11, 0x1E, 0x00]),  # B
        67: ("C", 5, [0x0E, 0x11, 0x10, 0x10, 0x11, 0x0E, 0x00]),  # C
    }
    
    for code, (name, width, bitmap) in simple_glyphs.items():
        glyph = BDFGlyph(
            encoding=code,
            name=name,
            bbox_width=width,
            bbox_height=7,
            bbox_x_offset=0,
            bbox_y_offset=-1,
            dwidth_x=width + 1,
            dwidth_y=0,
            bitmap=bitmap
        )
        font.glyphs[code] = glyph
    
    return font


if __name__ == "__main__":
    print("📝 BDF Font Parser Demo\n")
    
    # Create simple test font
    font = create_simple_font()
    
    print(f"Font: {font.font_name}")
    print(f"Size: {font.font_size}pt")
    print(f"Bounding box: {font.bbox_width}x{font.bbox_height}")
    print(f"Glyphs: {len(font.glyphs)}\n")
    
    # Render text
    test_text = "ABC"
    width, height, bitmap = font.render_text(test_text, spacing=1)
    
    print(f"Rendered '{test_text}':")
    print(f"  Size: {width}x{height}")
    print(f"  Bytes: {len(bitmap)}\n")
    
    # Display as ASCII art
    print("ASCII preview:")
    for y in range(height):
        line = ""
        for x in range(width):
            byte_idx = y * ((width + 7) // 8) + (x // 8)
            bit_offset = x % 8
            if byte_idx < len(bitmap) and (bitmap[byte_idx] & (1 << bit_offset)):
                line += "█"
            else:
                line += "·"
        print(f"  {line}")
    
    print("\n✅ BDF font parser ready!")
