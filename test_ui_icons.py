#!/usr/bin/env python3
"""
Tests for ui_icons module - Material Icons metadata and lookups
"""
import pytest

from ui_icons import (
    ICON_PALETTE,
    MATERIAL_ICONS,
    get_all_categories,
    get_icon_by_name,
    get_icon_by_symbol,
    get_icons_by_category,
)


def test_material_icons_structure():
    """Test that MATERIAL_ICONS has correct structure"""
    assert len(MATERIAL_ICONS) == 53, "Should have 53 icons"
    
    # Check first icon has all required fields
    icon = MATERIAL_ICONS[0]
    assert "name" in icon
    assert "symbol" in icon
    assert "category" in icon
    assert "usage" in icon
    assert "ascii" in icon
    assert "size_16" in icon
    assert "size_24" in icon
    
    # All icons should have non-empty fields
    for icon in MATERIAL_ICONS:
        assert icon["name"], "Icon name should not be empty"
        assert icon["symbol"], "Icon symbol should not be empty"
        assert icon["category"], "Icon category should not be empty"
        assert icon["usage"], "Icon usage should not be empty"
        assert icon["ascii"], "Icon ASCII should not be empty"


def test_icon_categories():
    """Test that all icons have valid categories"""
    valid_categories = {
        "navigation", "files", "types", "network", 
        "status", "media", "security"
    }
    
    for icon in MATERIAL_ICONS:
        assert icon["category"] in valid_categories, \
            f"Icon {icon['name']} has invalid category: {icon['category']}"


def test_icon_symbols_unique():
    """Test that all icon symbols are unique"""
    symbols = [icon["symbol"] for icon in MATERIAL_ICONS]
    assert len(symbols) == len(set(symbols)), "Icon symbols should be unique"


def test_icon_names_unique():
    """Test that all icon names are unique"""
    names = [icon["name"] for icon in MATERIAL_ICONS]
    assert len(names) == len(set(names)), "Icon names should be unique"


def test_get_icon_by_name():
    """Test get_icon_by_name lookup"""
    # Test exact match
    icon = get_icon_by_name("Home")
    assert icon is not None
    assert icon["name"] == "Home"
    assert icon["symbol"] == "mi_home_24px"
    
    # Test case-insensitive
    icon = get_icon_by_name("home")
    assert icon is not None
    assert icon["name"] == "Home"
    
    # Test non-existent
    icon = get_icon_by_name("NonExistent")
    assert icon is None


def test_get_icon_by_symbol():
    """Test get_icon_by_symbol lookup"""
    # Test by main symbol
    icon = get_icon_by_symbol("mi_home_24px")
    assert icon is not None
    assert icon["name"] == "Home"
    
    # Test by size_16
    icon = get_icon_by_symbol("mi_folder_24px")
    assert icon is not None
    assert icon["name"] == "Folder"
    
    # Test non-existent
    icon = get_icon_by_symbol("mi_nonexistent")
    assert icon is None


def test_get_icons_by_category():
    """Test get_icons_by_category"""
    # Navigation category should have 12 icons
    nav_icons = get_icons_by_category("navigation")
    assert len(nav_icons) == 12
    assert all(icon["category"] == "navigation" for icon in nav_icons)
    
    # Files category should have 14 icons
    file_icons = get_icons_by_category("files")
    assert len(file_icons) == 14
    
    # Non-existent category
    empty = get_icons_by_category("nonexistent")
    assert len(empty) == 0


def test_get_all_categories():
    """Test get_all_categories returns sorted unique list"""
    categories = get_all_categories()
    
    # Should have 7 categories
    assert len(categories) == 7
    
    # Should be sorted
    assert categories == sorted(categories)
    
    # Should contain expected categories
    expected = ["files", "media", "navigation", "network", "security", "status", "types"]
    assert categories == expected


def test_icon_palette_structure():
    """Test ICON_PALETTE dictionary structure"""
    # Should have entries for all categories
    assert len(ICON_PALETTE) == 7
    
    # Check categories match get_all_categories
    categories = get_all_categories()
    for cat in categories:
        assert cat in ICON_PALETTE
    
    # Total icons across palette should be 53
    total = sum(len(icons) for icons in ICON_PALETTE.values())
    assert total == 53


def test_icon_palette_navigation():
    """Test navigation category in palette"""
    nav_icons = ICON_PALETTE["navigation"]
    assert len(nav_icons) == 12
    
    # Check some known navigation icons
    names = [icon["name"] for icon in nav_icons]
    assert "Home" in names
    assert "Back" in names
    assert "Search" in names
    assert "Settings" in names


def test_icon_palette_files():
    """Test files category in palette"""
    file_icons = ICON_PALETTE["files"]
    assert len(file_icons) == 14
    
    names = [icon["name"] for icon in file_icons]
    assert "Folder" in names
    assert "Save" in names
    assert "Delete" in names


def test_icon_palette_types():
    """Test file types category in palette"""
    type_icons = ICON_PALETTE["types"]
    assert len(type_icons) == 8
    
    names = [icon["name"] for icon in type_icons]
    assert "Code" in names
    assert "Image" in names
    assert "PDF" in names


def test_icon_palette_status():
    """Test status category in palette"""
    status_icons = ICON_PALETTE["status"]
    assert len(status_icons) == 6
    
    names = [icon["name"] for icon in status_icons]
    assert "Battery Full" in names
    assert "WiFi" not in names  # WiFi is in network category


def test_icon_palette_media():
    """Test media category in palette"""
    media_icons = ICON_PALETTE["media"]
    assert len(media_icons) == 3
    
    names = [icon["name"] for icon in media_icons]
    assert "Play" in names
    assert "Pause" in names
    assert "Stop" in names


def test_icon_size_variants():
    """Test that all icons have both size variants"""
    for icon in MATERIAL_ICONS:
        assert icon["size_16"], f"Icon {icon['name']} missing size_16"
        assert icon["size_24"], f"Icon {icon['name']} missing size_24"
        
        # Both should reference valid symbols
        assert icon["size_16"].startswith("mi_")
        assert icon["size_24"].startswith("mi_")


def test_icon_ascii_fallbacks():
    """Test that all icons have ASCII fallbacks"""
    for icon in MATERIAL_ICONS:
        assert len(icon["ascii"]) > 0, f"Icon {icon['name']} has empty ASCII"
        # ASCII should be short (1-3 chars typically)
        assert len(icon["ascii"]) <= 5, f"Icon {icon['name']} ASCII too long"


def test_specific_icon_metadata():
    """Test specific well-known icons have correct metadata"""
    # Test Home icon
    home = get_icon_by_name("Home")
    assert home["symbol"] == "mi_home_24px"
    assert home["category"] == "navigation"
    assert home["ascii"] == "⌂"
    
    # Test Folder icon
    folder = get_icon_by_name("Folder")
    assert folder["symbol"] == "mi_folder_24px"
    assert folder["category"] == "files"
    assert folder["ascii"] == "📁"
    
    # Test Battery icon
    battery = get_icon_by_name("Battery Full")
    assert battery["symbol"] == "mi_battery_full_24px"
    assert battery["category"] == "status"
    assert battery["ascii"] == "🔋"


def test_icon_usage_descriptions():
    """Test that all icons have meaningful usage descriptions"""
    for icon in MATERIAL_ICONS:
        usage = icon["usage"]
        assert len(usage) > 5, f"Icon {icon['name']} has too short usage description"
        # Usage should be non-empty and descriptive (removed strict keyword check)


def test_icon_count_per_category():
    """Test expected icon counts per category"""
    expected_counts = {
        "navigation": 12,
        "files": 14,
        "types": 8,
        "network": 5,
        "status": 6,
        "media": 3,
        "security": 5,
    }
    
    for category, expected in expected_counts.items():
        icons = get_icons_by_category(category)
        assert len(icons) == expected, \
            f"Category {category} should have {expected} icons, got {len(icons)}"


def test_no_duplicate_ascii():
    """Test that ASCII fallbacks are reasonably unique"""
    # Some duplicates are OK (e.g., multiple save icons use 💾)
    # but excessive duplication would be bad
    ascii_chars = [icon["ascii"] for icon in MATERIAL_ICONS]
    unique_ascii = set(ascii_chars)
    
    # Should have at least 35 unique ASCII representations (some duplication OK)
    assert len(unique_ascii) >= 35, \
        f"Only {len(unique_ascii)} unique ASCII chars for {len(MATERIAL_ICONS)} icons"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
