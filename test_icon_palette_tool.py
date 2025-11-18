"""Tests for Icon Palette Tool"""

import pytest
from PIL import Image
import json
import os
import tempfile
from icon_palette_tool import Icon, IconLibrary


class TestIcon:
    def test_create_icon(self):
        # Create simple test image
        img = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        icon = Icon.from_pil(img, "test_icon")
        
        assert icon.name == "test_icon"
        assert icon.width == 16
        assert icon.height == 16
        assert icon.format == "RGBA"
    
    def test_resize_icon(self):
        img = Image.new("RGBA", (32, 32), (0, 255, 0, 255))
        icon = Icon.from_pil(img, "test")
        
        resized = icon.resize(16, 16)
        assert resized.width == 16
        assert resized.height == 16
    
    def test_to_c_array(self):
        img = Image.new("RGBA", (2, 2), (255, 255, 255, 255))
        icon = Icon.from_pil(img, "test")
        
        c_code = icon.to_c_array("test_icon")
        
        assert "const uint16_t test_icon[]" in c_code
        assert "0x" in c_code  # Should contain hex values
        assert "// Icon: test" in c_code
    
    def test_serialization(self):
        img = Image.new("RGBA", (8, 8), (100, 150, 200, 255))
        icon = Icon.from_pil(img, "test")
        icon.tags = ["ui", "button"]
        
        # Serialize
        data = icon.to_dict()
        assert data["name"] == "test"
        assert data["width"] == 8
        assert data["height"] == 8
        assert "ui" in data["tags"]
        
        # Deserialize
        icon2 = Icon.from_dict(data)
        assert icon2.name == icon.name
        assert icon2.width == icon.width
        assert icon2.height == icon.height
        assert icon2.tags == icon.tags


class TestIconLibrary:
    def test_add_remove(self):
        lib = IconLibrary()
        img = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        icon = Icon.from_pil(img, "test")
        
        lib.add(icon)
        assert lib.get("test") is not None
        
        lib.remove("test")
        assert lib.get("test") is None
    
    def test_search(self):
        lib = IconLibrary()
        
        img1 = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        icon1 = Icon.from_pil(img1, "home_icon")
        icon1.tags = ["navigation"]
        
        img2 = Image.new("RGBA", (16, 16), (0, 255, 0, 255))
        icon2 = Icon.from_pil(img2, "settings_icon")
        icon2.tags = ["config"]
        
        lib.add(icon1)
        lib.add(icon2)
        
        # Search by name
        results = lib.search("home")
        assert len(results) == 1
        assert results[0].name == "home_icon"
        
        # Search by tag
        results = lib.search("navigation")
        assert len(results) == 1
        assert results[0].name == "home_icon"
    
    def test_save_load(self):
        lib = IconLibrary()
        
        img = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        icon = Icon.from_pil(img, "test_icon")
        icon.tags = ["test"]
        lib.add(icon)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            lib.save(filepath)
            
            # Load into new library
            lib2 = IconLibrary()
            lib2.load(filepath)
            
            loaded_icon = lib2.get("test_icon")
            assert loaded_icon is not None
            assert loaded_icon.width == 16
            assert loaded_icon.height == 16
            assert "test" in loaded_icon.tags
        finally:
            os.unlink(filepath)
    
    def test_export_c(self):
        lib = IconLibrary()
        
        img = Image.new("RGBA", (4, 4), (255, 255, 255, 255))
        icon = Icon.from_pil(img, "test")
        lib.add(icon)
        
        # Export to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            lib.export_all_to_c(tmpdir)
            
            # Check files exist
            assert os.path.exists(os.path.join(tmpdir, "test.c"))
            assert os.path.exists(os.path.join(tmpdir, "icons.h"))
            
            # Check header content
            with open(os.path.join(tmpdir, "icons.h"), 'r') as f:
                header = f.read()
                assert "icon_test" in header
                assert "ICON_TEST_WIDTH" in header
                assert "ICON_TEST_HEIGHT" in header


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
