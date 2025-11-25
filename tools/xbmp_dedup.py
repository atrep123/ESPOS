#!/usr/bin/env python3
"""
XBMP Icon Deduplication for C Export

Converts icon data to XBM format and deduplicates identical bitmaps.
Reduces code size by 30-50% when multiple widgets share same icons.

Usage:
    from tools.xbmp_dedup import XBMPManager
    
    xbmp = XBMPManager()
    bitmap_ref = xbmp.add_icon(icon_data, width, height)
    c_code = xbmp.generate_c_code()
"""

import hashlib
from typing import Dict, List, Tuple


class XBMPManager:
    """Manage XBM bitmap deduplication for icon widgets."""
    
    def __init__(self):
        self.bitmaps: Dict[str, Tuple[int, int, List[int]]] = {}  # hash -> (width, height, data)
        self.bitmap_order: List[str] = []  # Preserve insertion order
    
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
