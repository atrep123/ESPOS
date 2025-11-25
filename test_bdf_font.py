#!/usr/bin/env python3
"""
Comprehensive BDF font test suite.

Tests:
- BDF parsing
- Text rendering to bitmap
- C code export
- Font subsetting
"""

from tools.bdf_font import create_simple_font
from tools.bdf_font_export import export_font_subset, export_font_to_c


def test_font_parsing():
    """Test BDF font parsing."""
    print("🔍 Testing BDF Font Parsing\n")
    
    font = create_simple_font()
    
    assert font.font_name == "Simple5x7"
    assert font.font_size == 7
    assert len(font.glyphs) == 4
    assert 65 in font.glyphs  # 'A'
    assert font.glyphs[65].bbox_width == 5
    
    print("✓ Font metadata parsed correctly")
    print(f"  Name: {font.font_name}")
    print(f"  Size: {font.font_size}pt")
    print(f"  Glyphs: {len(font.glyphs)}\n")


def test_text_rendering():
    """Test text rendering to bitmap."""
    print("📝 Testing Text Rendering\n")
    
    font = create_simple_font()
    
    # Render single character
    width, height, bitmap = font.render_text("A", spacing=0)
    assert width > 0
    assert height == font.bbox_height
    assert len(bitmap) > 0
    
    print(f"✓ Single char 'A': {width}x{height}, {len(bitmap)} bytes")
    
    # Render multiple characters
    width, height, bitmap = font.render_text("ABC", spacing=1)
    expected_width = font.get_text_width("ABC", spacing=1)
    assert width == expected_width
    
    print(f"✓ Multi char 'ABC': {width}x{height}, {len(bitmap)} bytes")
    
    # Render with spacing
    w1, _, _ = font.render_text("AB", spacing=0)
    w2, _, _ = font.render_text("AB", spacing=2)
    assert w2 > w1
    
    print(f"✓ Spacing: 0px={w1}w, 2px={w2}w\n")


def test_c_export():
    """Test C code export."""
    print("📦 Testing C Code Export\n")
    
    font = create_simple_font()
    
    # Full export
    c_code = export_font_to_c(font, "test_font")
    
    assert "BdfFont" in c_code
    assert "BdfGlyph" in c_code
    assert "test_font" in c_code
    assert "glyph_65_bitmap" in c_code  # 'A' glyph
    
    print(f"✓ Full export: {len(c_code)} chars")
    print(f"  Contains: BdfFont struct, {len(font.glyphs)} glyphs")
    
    # Subset export
    subset_code = export_font_subset(font, "AB", "subset_font")
    
    assert len(subset_code) < len(c_code)
    assert "glyph_65_bitmap" in subset_code  # 'A'
    assert "glyph_66_bitmap" in subset_code  # 'B'
    assert "glyph_67_bitmap" not in subset_code  # 'C' excluded
    
    savings = len(c_code) - len(subset_code)
    savings_pct = (savings / len(c_code)) * 100
    
    print(f"✓ Subset export 'AB': {len(subset_code)} chars")
    print(f"  Savings: {savings} chars ({savings_pct:.1f}%)\n")


def test_ascii_preview():
    """Test ASCII art preview of rendered text."""
    print("🎨 ASCII Art Preview\n")
    
    font = create_simple_font()
    width, height, bitmap = font.render_text("ABC", spacing=1)
    
    print(f"'ABC' rendered as {width}x{height} bitmap:\n")
    
    for y in range(height):
        line = "  "
        for x in range(width):
            byte_idx = y * ((width + 7) // 8) + (x // 8)
            bit_offset = x % 8
            if byte_idx < len(bitmap) and (bitmap[byte_idx] & (1 << bit_offset)):
                line += "█"
            else:
                line += "·"
        print(line)
    
    print()


def test_performance():
    """Test rendering performance."""
    print("⚡ Performance Test\n")
    
    import time
    
    font = create_simple_font()
    
    # Benchmark text rendering
    iterations = 1000
    text = "ABC"
    
    start = time.perf_counter()
    for _ in range(iterations):
        font.render_text(text, spacing=1)
    elapsed = time.perf_counter() - start
    
    per_render = (elapsed / iterations) * 1000  # ms
    renders_per_sec = iterations / elapsed
    
    print(f"✓ Rendered '{text}' {iterations}x in {elapsed:.3f}s")
    print(f"  {per_render:.3f}ms per render")
    print(f"  {renders_per_sec:.0f} renders/sec\n")


if __name__ == "__main__":
    print("=" * 60)
    print("BDF Font Test Suite")
    print("=" * 60)
    print()
    
    test_font_parsing()
    test_text_rendering()
    test_c_export()
    test_ascii_preview()
    test_performance()
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
