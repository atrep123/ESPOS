#!/usr/bin/env python3
"""
XBM Bitmap Utilities

Utilities for manipulating XBM format bitmaps used in embedded displays.
Provides rotate, scale, invert, and pixelate operations.

Inspired by Lopaka's bitmap manipulation capabilities.
"""

from typing import Tuple, List
import math


def xbm_invert(bitmap: bytes, width: int, height: int) -> bytes:
    """
    Invert all pixels in XBM bitmap (black↔white).
    
    Args:
        bitmap: XBM bitmap data
        width: Bitmap width
        height: Bitmap height
        
    Returns:
        Inverted bitmap
    """
    return bytes(~b & 0xFF for b in bitmap)


def xbm_rotate_90(bitmap: bytes, width: int, height: int) -> Tuple[bytes, int, int]:
    """
    Rotate XBM bitmap 90° clockwise.
    
    Args:
        bitmap: XBM bitmap data
        width: Original width
        height: Original height
        
    Returns:
        Tuple of (rotated_bitmap, new_width, new_height)
    """
    # New dimensions (swap width/height)
    new_width = height
    new_height = width
    
    # Create new bitmap
    new_bytes_per_row = (new_width + 7) // 8
    new_bitmap = bytearray(new_bytes_per_row * new_height)
    
    # Rotate pixels
    for y in range(height):
        for x in range(width):
            # Get pixel from source
            if _get_pixel(bitmap, x, y, width):
                # Set in rotated position
                new_x = height - 1 - y
                new_y = x
                _set_pixel(new_bitmap, new_x, new_y, new_width)
    
    return (bytes(new_bitmap), new_width, new_height)


def xbm_scale(
    bitmap: bytes, width: int, height: int, scale_x: int, scale_y: int
) -> Tuple[bytes, int, int]:
    """
    Scale XBM bitmap by integer factors (nearest neighbor).
    
    Args:
        bitmap: XBM bitmap data
        width: Original width
        height: Original height
        scale_x: Horizontal scale factor
        scale_y: Vertical scale factor
        
    Returns:
        Tuple of (scaled_bitmap, new_width, new_height)
    """
    new_width = width * scale_x
    new_height = height * scale_y
    
    new_bytes_per_row = (new_width + 7) // 8
    new_bitmap = bytearray(new_bytes_per_row * new_height)
    
    for y in range(height):
        for x in range(width):
            if _get_pixel(bitmap, x, y, width):
                # Replicate pixel
                for dy in range(scale_y):
                    for dx in range(scale_x):
                        new_x = x * scale_x + dx
                        new_y = y * scale_y + dy
                        _set_pixel(new_bitmap, new_x, new_y, new_width)
    
    return (bytes(new_bitmap), new_width, new_height)


def xbm_pixelate(
    bitmap: bytes, width: int, height: int, pixel_size: int
) -> bytes:
    """
    Apply pixelate/mosaic effect to XBM bitmap.
    
    Creates blocky appearance by averaging pixels in blocks.
    Inspired by Lopaka's drawPixelate() function.
    
    Args:
        bitmap: XBM bitmap data
        width: Bitmap width
        height: Bitmap height
        pixel_size: Size of pixelated blocks (e.g., 2, 4, 8)
        
    Returns:
        Pixelated bitmap (same dimensions)
    """
    if pixel_size <= 1:
        return bitmap
    
    bytes_per_row = (width + 7) // 8
    new_bitmap = bytearray(bytes_per_row * height)
    
    # Process in blocks
    for block_y in range(0, height, pixel_size):
        for block_x in range(0, width, pixel_size):
            # Count set pixels in block
            count = 0
            total = 0
            
            for dy in range(pixel_size):
                y = block_y + dy
                if y >= height:
                    break
                for dx in range(pixel_size):
                    x = block_x + dx
                    if x >= width:
                        break
                    if _get_pixel(bitmap, x, y, width):
                        count += 1
                    total += 1
            
            # Set entire block based on majority
            fill = count > total // 2
            
            if fill:
                for dy in range(pixel_size):
                    y = block_y + dy
                    if y >= height:
                        break
                    for dx in range(pixel_size):
                        x = block_x + dx
                        if x >= width:
                            break
                        _set_pixel(new_bitmap, x, y, width)
    
    return bytes(new_bitmap)


def xbm_resize_canvas(
    bitmap: bytes,
    width: int,
    height: int,
    new_width: int,
    new_height: int,
    offset_x: int = 0,
    offset_y: int = 0
) -> bytes:
    """
    Resize canvas (crop or extend) without scaling content.
    
    Args:
        bitmap: XBM bitmap data
        width: Original width
        height: Original height
        new_width: New canvas width
        new_height: New canvas height
        offset_x: X offset for original content
        offset_y: Y offset for original content
        
    Returns:
        Resized canvas bitmap
    """
    new_bytes_per_row = (new_width + 7) // 8
    new_bitmap = bytearray(new_bytes_per_row * new_height)
    
    # Copy pixels
    for y in range(min(height, new_height - offset_y)):
        for x in range(min(width, new_width - offset_x)):
            if _get_pixel(bitmap, x, y, width):
                new_x = x + offset_x
                new_y = y + offset_y
                if 0 <= new_x < new_width and 0 <= new_y < new_height:
                    _set_pixel(new_bitmap, new_x, new_y, new_width)
    
    return bytes(new_bitmap)


def xbm_to_ascii(bitmap: bytes, width: int, height: int) -> str:
    """
    Convert XBM bitmap to ASCII art for debugging.
    
    Args:
        bitmap: XBM bitmap data
        width: Bitmap width
        height: Bitmap height
        
    Returns:
        ASCII art string
    """
    lines = []
    for y in range(height):
        line = ""
        for x in range(width):
            if _get_pixel(bitmap, x, y, width):
                line += "█"
            else:
                line += "·"
        lines.append(line)
    return "\n".join(lines)


# Helper functions

def _get_pixel(bitmap: bytes, x: int, y: int, width: int) -> bool:
    """Get pixel value from XBM bitmap."""
    bytes_per_row = (width + 7) // 8
    byte_idx = y * bytes_per_row + (x // 8)
    bit_offset = x % 8
    if byte_idx < len(bitmap):
        return bool(bitmap[byte_idx] & (1 << bit_offset))
    return False


def _set_pixel(bitmap: bytearray, x: int, y: int, width: int) -> None:
    """Set pixel in XBM bitmap."""
    bytes_per_row = (width + 7) // 8
    byte_idx = y * bytes_per_row + (x // 8)
    bit_offset = x % 8
    if byte_idx < len(bitmap):
        bitmap[byte_idx] |= 1 << bit_offset


# Demo
if __name__ == "__main__":
    print("🎨 XBM Bitmap Utilities Demo\n")
    
    # Create test pattern
    width, height = 16, 16
    bitmap = bytearray((width + 7) // 8 * height)
    
    # Draw checkerboard
    for y in range(height):
        for x in range(width):
            if (x // 2 + y // 2) % 2 == 0:
                _set_pixel(bitmap, x, y, width)
    
    bitmap = bytes(bitmap)
    
    print("Original 16x16 checkerboard:")
    print(xbm_to_ascii(bitmap, width, height))
    
    # Test invert
    print("\n🔄 Inverted:")
    inverted = xbm_invert(bitmap, width, height)
    print(xbm_to_ascii(inverted, width, height)[:100] + "...")
    
    # Test scale
    print("\n🔍 Scaled 2x:")
    scaled, sw, sh = xbm_scale(bitmap, width, height, 2, 2)
    print(f"New size: {sw}x{sh}")
    print(xbm_to_ascii(scaled, sw, sh)[:100] + "...")
    
    # Test pixelate
    print("\n🟦 Pixelated (4px blocks):")
    pixelated = xbm_pixelate(bitmap, width, height, 4)
    print(xbm_to_ascii(pixelated, width, height))
    
    # Test rotate
    print("\n↻ Rotated 90°:")
    rotated, rw, rh = xbm_rotate_90(bitmap, width, height)
    print(f"New size: {rw}x{rh}")
    print(xbm_to_ascii(rotated, rw, rh))
    
    print("\n✅ XBM utilities ready!")
