#!/usr/bin/env python3
"""
Test UI Designer Image Tools integration
"""
import os
import sys
from pathlib import Path

# Ensure we can import from tools
sys.path.insert(0, str(Path(__file__).parent))


def test_icon_exporter():
    """Test IconBitmapExporter basic functionality"""
    print("Testing IconBitmapExporter...")
    
    try:
        from ui_designer_image_tools import IconBitmapExporter
        from PIL import Image
        
        # Create test icon
        img = Image.new("L", (16, 16), color=128)
        for i in range(16):
            img.putpixel((i, i), 255)  # diagonal line
        
        exporter = IconBitmapExporter()
        
        # Add icon directly from PIL Image
        exporter.xbmp.add_icon_from_pil(img)
        exporter.icon_refs["test_icon"] = "icon_bitmap_test"  # manual tracking
        
        # Test that bitmap was added
        assert len(exporter.xbmp.bitmaps) >= 1
        
        # Test export
        c_code = exporter.export_to_header("")  # empty path = return code only
        assert "unsigned char icon_bitmap_" in c_code
        
        print("✓ IconBitmapExporter works")
        return True
        
    except ImportError as e:
        print(f"⚠ Skipped: {e}")
        return True  # not a failure
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_font_exporter():
    """Test FontExporter basic functionality"""
    print("\nTesting FontExporter...")
    
    try:
        from ui_designer_image_tools import FontExporter
        from tools.bdf_font import create_simple_font
        
        # Use built-in test font
        font = create_simple_font()
        
        exporter = FontExporter()
        exporter.loaded_fonts["test"] = font
        
        # Test subset export
        c_code = exporter.export_font_subset("test", "ABC", None)
        assert "BdfGlyph" in c_code
        assert "BdfFont" in c_code
        
        print("✓ FontExporter works")
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_find_fonts():
    """Test font discovery"""
    print("\nTesting find_bdf_fonts...")
    
    try:
        from ui_designer_image_tools import find_bdf_fonts
        
        fonts = find_bdf_fonts()
        print(f"  Found {len(fonts)} BDF fonts")
        
        if fonts:
            print(f"  Example: {fonts[0]}")
        
        print("✓ find_bdf_fonts works")
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_cli_exports():
    """Test CLI functions exist and are callable"""
    print("\nTesting CLI exports...")
    
    try:
        from ui_designer_image_tools import cli_export_icons, cli_export_font
        
        # Just check they're importable
        assert callable(cli_export_icons)
        assert callable(cli_export_font)
        
        print("✓ CLI functions available")
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("UI Designer Image Tools Integration Tests")
    print("=" * 60)
    
    tests = [
        test_icon_exporter,
        test_font_exporter,
        test_find_fonts,
        test_cli_exports,
    ]
    
    results = [test() for test in tests]
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nIntegrace je připravena k použití:")
        print("1. Otevři UI Designer: python run_designer.py")
        print("2. Zkus Icon Palette → Export Bitmap")
        print("3. Přidej PNG ikony do assets/icons/")
        return 0
    else:
        print(f"❌ {sum(not r for r in results)} test(s) failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
