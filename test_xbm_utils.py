#!/usr/bin/env python3
"""Test XBM utilities with various patterns."""

from tools.xbm_utils import (
    _set_pixel,
    xbm_invert,
    xbm_pixelate,
    xbm_resize_canvas,
    xbm_rotate_90,
    xbm_scale,
    xbm_to_ascii,
)


def create_gradient(width: int, height: int) -> bytes:
    """Create horizontal gradient pattern."""
    bitmap = bytearray((width + 7) // 8 * height)
    
    for y in range(height):
        for x in range(width):
            # Horizontal gradient: more pixels on right
            if x * 100 // width > 50:
                _set_pixel(bitmap, x, y, width)
    
    return bytes(bitmap)


def create_circle(width: int, height: int) -> bytes:
    """Create circle pattern."""
    bitmap = bytearray((width + 7) // 8 * height)
    
    cx, cy = width // 2, height // 2
    radius = min(width, height) // 3
    
    for y in range(height):
        for x in range(width):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist < radius:
                _set_pixel(bitmap, x, y, width)
    
    return bytes(bitmap)


def test_pixelate():
    """Test pixelate effect on different patterns."""
    print("🎨 Pixelate Effect Tests\n")
    
    width, height = 32, 16
    
    # Test on gradient
    print("Gradient pattern (32x16):")
    gradient = create_gradient(width, height)
    print(xbm_to_ascii(gradient, width, height))
    
    print("\nPixelated (4px blocks):")
    pixelated = xbm_pixelate(gradient, width, height, 4)
    print(xbm_to_ascii(pixelated, width, height))
    
    # Test on circle
    print("\n\nCircle pattern (32x16):")
    circle = create_circle(width, height)
    print(xbm_to_ascii(circle, width, height))
    
    print("\nPixelated (2px blocks):")
    pixelated = xbm_pixelate(circle, width, height, 2)
    print(xbm_to_ascii(pixelated, width, height))
    
    print("\nPixelated (4px blocks):")
    pixelated = xbm_pixelate(circle, width, height, 4)
    print(xbm_to_ascii(pixelated, width, height))


def test_transformations():
    """Test various transformations."""
    print("\n\n🔄 Transformation Tests\n")
    
    # Create L-shape
    width, height = 12, 12
    bitmap = bytearray((width + 7) // 8 * height)
    
    # Draw L
    for y in range(8):
        _set_pixel(bitmap, 2, y, width)
    for x in range(2, 8):
        _set_pixel(bitmap, x, 7, width)
    
    bitmap = bytes(bitmap)
    
    print("Original L-shape (12x12):")
    print(xbm_to_ascii(bitmap, width, height))
    
    # Rotate
    print("\nRotated 90° clockwise:")
    rotated, rw, rh = xbm_rotate_90(bitmap, width, height)
    print(xbm_to_ascii(rotated, rw, rh))
    
    # Scale
    print("\nScaled 2x:")
    scaled, sw, sh = xbm_scale(bitmap, width, height, 2, 2)
    print(xbm_to_ascii(scaled, sw, sh))
    
    # Invert
    print("\nInverted:")
    inverted = xbm_invert(bitmap, width, height)
    print(xbm_to_ascii(inverted, width, height))


def test_canvas_resize():
    """Test canvas resizing."""
    print("\n\n📐 Canvas Resize Tests\n")
    
    # Create small icon
    width, height = 8, 8
    bitmap = bytearray((width + 7) // 8 * height)
    
    # Draw small square
    for y in range(2, 6):
        for x in range(2, 6):
            _set_pixel(bitmap, x, y, width)
    
    bitmap = bytes(bitmap)
    
    print("Original 8x8:")
    print(xbm_to_ascii(bitmap, width, height))
    
    # Expand canvas
    print("\nExpanded to 16x12 with offset (4, 2):")
    expanded = xbm_resize_canvas(bitmap, width, height, 16, 12, 4, 2)
    print(xbm_to_ascii(expanded, 16, 12))
    
    # Crop
    print("\nCropped to 4x4:")
    cropped = xbm_resize_canvas(bitmap, width, height, 4, 4, -2, -2)
    print(xbm_to_ascii(cropped, 4, 4))


if __name__ == "__main__":
    test_pixelate()
    test_transformations()
    test_canvas_resize()
    
    print("\n\n✅ All XBM utility tests completed!")
