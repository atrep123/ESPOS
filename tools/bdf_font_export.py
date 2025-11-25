#!/usr/bin/env python3
"""
BDF Font to C Code Exporter

Exports BDF fonts as embeddable C arrays for use in embedded systems.
Supports full font export or subset of characters.

Usage:
    from tools.bdf_font_export import export_font_to_c
    
    c_code = export_font_to_c("font.bdf", charset="ASCII")
"""

from tools.bdf_font import BDFFont, BDFGlyph
from typing import List, Optional, Set


def export_font_to_c(
    font: BDFFont,
    font_name: str = "default_font",
    charset: Optional[Set[int]] = None
) -> str:
    """
    Export BDF font to C code.
    
    Args:
        font: BDFFont instance
        font_name: C identifier for font
        charset: Set of character codes to export (None = all)
        
    Returns:
        C source code string
    """
    if charset is None:
        glyphs_to_export = list(font.glyphs.values())
    else:
        glyphs_to_export = [g for g in font.glyphs.values() if g.encoding in charset]
    
    glyphs_to_export.sort(key=lambda g: g.encoding)
    
    c_code = f"""/* Auto-generated font: {font.font_name} */
/* Size: {font.font_size}pt, Glyphs: {len(glyphs_to_export)} */

#include <stdint.h>

/* Font metadata */
typedef struct {{
    uint16_t encoding;    /* Unicode code point */
    uint8_t width;        /* Glyph width in pixels */
    uint8_t height;       /* Glyph height in pixels */
    int8_t x_offset;      /* X offset from origin */
    int8_t y_offset;      /* Y offset from baseline */
    uint8_t advance;      /* Horizontal advance */
    const uint8_t *bitmap; /* Pointer to bitmap data */
}} BdfGlyph;

typedef struct {{
    const char *name;
    uint8_t size;
    uint8_t bbox_w;
    uint8_t bbox_h;
    int8_t bbox_x;
    int8_t bbox_y;
    uint16_t glyph_count;
    const BdfGlyph *glyphs;
}} BdfFont;

"""
    
    # Export bitmap data for each glyph
    for glyph in glyphs_to_export:
        c_code += f"/* '{chr(glyph.encoding) if 32 <= glyph.encoding < 127 else '?'}' (U+{glyph.encoding:04X}) */\n"
        c_code += f"static const uint8_t glyph_{glyph.encoding}_bitmap[] = {{\n"
        c_code += "    "
        for i, byte_val in enumerate(glyph.bitmap):
            c_code += f"0x{byte_val:02X}"
            if i < len(glyph.bitmap) - 1:
                c_code += ", "
            if (i + 1) % 12 == 0 and i < len(glyph.bitmap) - 1:
                c_code += "\n    "
        c_code += "\n};\n\n"
    
    # Export glyph table
    c_code += f"static const BdfGlyph {font_name}_glyphs[] = {{\n"
    for glyph in glyphs_to_export:
        c_code += f"    {{ {glyph.encoding}, {glyph.bbox_width}, {glyph.bbox_height}, "
        c_code += f"{glyph.bbox_x_offset}, {glyph.bbox_y_offset}, {glyph.dwidth_x}, "
        c_code += f"glyph_{glyph.encoding}_bitmap }},\n"
    c_code += "};\n\n"
    
    # Export font structure
    c_code += f"const BdfFont {font_name} = {{\n"
    c_code += f'    .name = "{font.font_name}",\n'
    c_code += f"    .size = {font.font_size},\n"
    c_code += f"    .bbox_w = {font.bbox_width},\n"
    c_code += f"    .bbox_h = {font.bbox_height},\n"
    c_code += f"    .bbox_x = {font.bbox_x_offset},\n"
    c_code += f"    .bbox_y = {font.bbox_y_offset},\n"
    c_code += f"    .glyph_count = {len(glyphs_to_export)},\n"
    c_code += f"    .glyphs = {font_name}_glyphs\n"
    c_code += "};\n"
    
    return c_code


def export_font_subset(
    font: BDFFont,
    text: str,
    font_name: str = "subset_font"
) -> str:
    """
    Export only glyphs needed for specific text.
    
    Args:
        font: BDFFont instance
        text: Text string to support
        font_name: C identifier
        
    Returns:
        C source code
    """
    charset = {ord(c) for c in text}
    return export_font_to_c(font, font_name, charset)


if __name__ == "__main__":
    from tools.bdf_font import create_simple_font
    
    print("📦 BDF Font C Export Demo\n")
    
    # Create test font
    font = create_simple_font()
    
    # Export full font
    c_code = export_font_to_c(font, "simple_font")
    
    print("Generated C code:")
    print("=" * 60)
    print(c_code[:500] + "...")
    print("=" * 60)
    
    # Export subset
    subset_code = export_font_subset(font, "ABC", "abc_font")
    
    print(f"\nFull export: {len(c_code)} chars")
    print(f"Subset export: {len(subset_code)} chars")
    print(f"Savings: {len(c_code) - len(subset_code)} chars")
    
    # Write to file
    with open("font_export_demo.c", "w") as f:
        f.write(c_code)
    
    print("\n✅ Exported to font_export_demo.c")
