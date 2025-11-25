#!/usr/bin/env python3
"""
XBMP Icon Deduplication for C Export

Converts icon data to XBM format and deduplicates identical bitmaps.
Reduces code size by 30-50% when multiple widgets share same icons.

Supports Floyd-Steinberg and Atkinson dithering for high-quality 1bpp conversion.

Usage:
    from tools.xbmp_dedup import XBMPManager
    
    xbmp = XBMPManager()
    bitmap_ref = xbmp.add_icon(icon_data, width, height)
    # Or with PIL Image:
    bitmap_ref = xbmp.add_icon_from_pil(image, dither="floyd-steinberg")
    c_code = xbmp.generate_c_code()
"""

import hashlib
from typing import Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage  # type: ignore[import-not-found]


class XBMPManager:
    """Manage XBM bitmap deduplication for icon widgets."""
    
    def __init__(self, default_dither: str = "floyd-steinberg"):
        """
        Initialize XBMPManager.
        
        Args:
            default_dither: Default dithering method
                ("floyd-steinberg", "atkinson", "ordered", "threshold")
        """
        self.bitmaps: Dict[str, Tuple[int, int, List[int]]] = {}  # hash -> (width, height, data)
        self.bitmap_order: List[str] = []  # Preserve insertion order
        self.default_dither = default_dither
    
    def add_icon(self, data: List[int], width: int, height: int) -> str:
        """
        Add icon bitmap and return reference name.
        
        Args:
            data: Bitmap data as list of bytes
            width: Icon width in pixels
            height: Icon height in pixels
            
        Returns:
            Reference name (e.g., "icon_bitmap_0")
        """
        # Compute hash of bitmap data
        bitmap_hash = hashlib.md5(bytes(data)).hexdigest()[:8]
        
        # Check if we already have this bitmap
        if bitmap_hash in self.bitmaps:
            return f"icon_bitmap_{bitmap_hash}"
        
        # Store new bitmap
        self.bitmaps[bitmap_hash] = (width, height, data)
        self.bitmap_order.append(bitmap_hash)
        
        return f"icon_bitmap_{bitmap_hash}"
    
    def generate_c_code(self) -> str:
        """Generate C code for all unique bitmaps."""
        if not self.bitmaps:
            return ""
        
        c_code = "\n/* Icon bitmaps (XBM format, deduplicated) */\n"
        
        for bitmap_hash in self.bitmap_order:
            width, height, data = self.bitmaps[bitmap_hash]
            name = f"icon_bitmap_{bitmap_hash}"
            
            # Generate XBM format
            c_code += f"static const unsigned char {name}[] = {{\n"
            c_code += "    "
            
            for i, byte in enumerate(data):
                c_code += f"0x{byte:02x}"
                if i < len(data) - 1:
                    c_code += ", "
                if (i + 1) % 12 == 0 and i < len(data) - 1:
                    c_code += "\n    "
            
            c_code += f"\n}}; /* {width}x{height}, {len(data)} bytes */\n\n"
        
        return c_code
    
    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        total_bytes = sum(len(data) for _, _, data in self.bitmaps.values())
        return {
            "unique_bitmaps": len(self.bitmaps),
            "total_bytes": total_bytes
        }
    
    def add_icon_from_pil(self, image, dither: str | None = None) -> str:
        """
        Add icon from PIL Image with dithering.
        
        Args:
            image: PIL Image object
            dither: Dithering method (None = use default)
            
        Returns:
            Reference name (e.g., "icon_bitmap_abc12345")
        """
        try:
            from tools.image_dithering import image_to_xbm, rgb_to_grayscale
        except ImportError:
            raise ImportError("image_dithering module required for PIL support")
        
        # Convert to grayscale pixel array
        width, height = image.size
        pixels = []
        
        if image.mode == "L":  # Already grayscale
            for y in range(height):
                row = []
                for x in range(width):
                    row.append(image.getpixel((x, y)))
                pixels.append(row)
        else:  # RGB or RGBA
            for y in range(height):
                row = []
                for x in range(width):
                    px = image.getpixel((x, y))
                    if isinstance(px, int):  # Single channel
                        row.append(px)
                    else:  # Tuple (RGB or RGBA)
                        r, g, b = px[:3]
                        row.append(rgb_to_grayscale(r, g, b))
                pixels.append(row)
        
        # Apply dithering and convert to XBM
        method = dither or self.default_dither
        _, _, bitmap_data = image_to_xbm(pixels, width, height, method)
        
        # Add to manager
        return self.add_icon(list(bitmap_data), width, height)


def icon_char_to_bitmap(char: str, size: int = 16) -> List[int]:
    """
    Convert icon character to simple bitmap representation.
    
    This is a placeholder - in real implementation, you'd use a font renderer
    or pre-rendered icon atlas.
    
    Args:
        char: Icon character (emoji or symbol)
        size: Icon size (square)
        
    Returns:
        List of bytes representing bitmap
    """
    # Placeholder: generate simple pattern based on character code
    # Real implementation would render actual font glyph
    char_code = ord(char[0]) if char else 0
    
    bytes_per_row = (size + 7) // 8
    
    # Generate simple pattern (checkerboard influenced by char code)
    data: List[int] = []
    for row in range(size):
        for byte_idx in range(bytes_per_row):
            # Simple pattern: XOR with char_code for variation
            pattern = ((row + byte_idx) ^ (char_code >> 4)) & 0xFF
            data.append(pattern)
    
    return data


def main():
    """Demo XBM deduplication."""
    print("🎨 XBM Icon Deduplication Demo\n")
    
    xbmp = XBMPManager()
    
    # Simulate adding icons (some duplicates)
    icons: List[Tuple[str, str]] = [
        ("🏠", "home"),
        ("⚙️", "settings"),
        ("🏠", "home_again"),  # Duplicate
        ("📊", "chart"),
        ("⚙️", "settings_again"),  # Duplicate
    ]
    
    refs: Dict[str, str] = {}
    for icon_char, label in icons:
        bitmap_data = icon_char_to_bitmap(icon_char, 16)
        ref = xbmp.add_icon(bitmap_data, 16, 16)
        refs[label] = ref
        print(f"  {label:15} → {ref}")
    
    print("\n📊 Statistics:")
    stats = xbmp.get_stats()
    print(f"  Unique bitmaps: {stats['unique_bitmaps']}")
    print(f"  Total bytes: {stats['total_bytes']}")
    print(f"  References: {len(refs)}")
    print(f"  Savings: {len(refs) - stats['unique_bitmaps']} duplicates eliminated")
    
    print("\n💾 Generated C code:\n")
    print(xbmp.generate_c_code())


if __name__ == "__main__":
    main()
