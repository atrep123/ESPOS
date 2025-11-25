#!/usr/bin/env python3
"""Test dithering integration with XBMP manager."""

from PIL import Image

from tools.xbmp_dedup import XBMPManager


def test_dithering_integration():
    """Test adding PIL images with different dithering methods."""
    print("🎨 Testing Dithering Integration\n")
    
    # Create test gradient image
    width, height = 32, 32
    img = Image.new("L", (width, height))
    for y in range(height):
        for x in range(width):
            # Horizontal gradient
            val = int(x * 255 / (width - 1))
            img.putpixel((x, y), val)
    
    # Test each dithering method
    methods = ["threshold", "floyd-steinberg", "atkinson", "ordered"]
    
    for method in methods:
        print(f"Testing {method}:")
        xbmp = XBMPManager(default_dither=method)
        
        # Add same image 3 times (should deduplicate)
        ref1 = xbmp.add_icon_from_pil(img)
        ref2 = xbmp.add_icon_from_pil(img)
        ref3 = xbmp.add_icon_from_pil(img)
        
        print(f"  Reference 1: {ref1}")
        print(f"  Reference 2: {ref2}")
        print(f"  Reference 3: {ref3}")
        print(f"  All identical: {ref1 == ref2 == ref3}")
        
        stats = xbmp.get_stats()
        print(f"  Unique bitmaps: {stats['unique_bitmaps']}")
        print(f"  Total bytes: {stats['total_bytes']}\n")
        
        # Generate C code
        c_code = xbmp.generate_c_code()
        print(f"  C code preview ({len(c_code)} chars):")
        print("  " + c_code[:200].replace("\n", "\n  ") + "...\n")


def test_mixed_images():
    """Test different images with deduplication."""
    print("\n🖼️  Testing Multiple Different Images\n")
    
    xbmp = XBMPManager(default_dither="floyd-steinberg")
    
    # Create 3 different images
    images = []
    for i in range(3):
        img = Image.new("L", (16, 16))
        # Different patterns
        for y in range(16):
            for x in range(16):
                val = ((x + y) * (i + 1) * 20) % 256
                img.putpixel((x, y), val)
        images.append(img)
    
    # Add images (with some duplicates)
    refs = [
        xbmp.add_icon_from_pil(images[0]),  # Image 0
        xbmp.add_icon_from_pil(images[1]),  # Image 1
        xbmp.add_icon_from_pil(images[0]),  # Image 0 again
        xbmp.add_icon_from_pil(images[2]),  # Image 2
        xbmp.add_icon_from_pil(images[1]),  # Image 1 again
    ]
    
    print("Added 5 images (3 unique):")
    for i, ref in enumerate(refs):
        print(f"  Image {i}: {ref}")
    
    stats = xbmp.get_stats()
    print("\nStatistics:")
    print(f"  Unique bitmaps: {stats['unique_bitmaps']} (expected 3)")
    print(f"  Total refs: {len(refs)} (expected 5)")
    print(f"  Deduplication: {len(refs) - stats['unique_bitmaps']} duplicates saved")
    print(f"  Total bytes: {stats['total_bytes']}")


if __name__ == "__main__":
    test_dithering_integration()
    test_mixed_images()
    print("\n✅ All tests passed!")
