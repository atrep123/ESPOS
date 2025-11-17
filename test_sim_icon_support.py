#!/usr/bin/env python3
"""
Tests for simulator icon support
"""
import pytest

from sim_icon_support import ICON_ASCII_MAP, get_icon_ascii, icon_exists


def test_icon_ascii_map_exists():
    """Test that the icon ASCII map is populated"""
    assert len(ICON_ASCII_MAP) > 0
    assert len(ICON_ASCII_MAP) == 53  # Should have all 53 icons


def test_get_icon_ascii_navigation():
    """Test navigation icon lookups"""
    assert get_icon_ascii("mi_home_24px") == "⌂"
    assert get_icon_ascii("mi_arrow_back_24px") == "←"
    assert get_icon_ascii("mi_arrow_forward_24px") == "→"
    assert get_icon_ascii("mi_search_24px") == "🔍"
    assert get_icon_ascii("mi_settings_24px") == "⚙"
    assert get_icon_ascii("mi_menu_24px") == "☰"


def test_get_icon_ascii_files():
    """Test file operation icon lookups"""
    assert get_icon_ascii("mi_folder_24px") == "📁"
    assert get_icon_ascii("mi_folder_open_24px") == "📂"
    assert get_icon_ascii("mi_save_24px") == "💾"
    assert get_icon_ascii("mi_delete_24px") == "🗑"


def test_get_icon_ascii_types():
    """Test file type icon lookups"""
    assert get_icon_ascii("mi_code_24px") == "<>"
    assert get_icon_ascii("mi_image_24px") == "🖼"
    assert get_icon_ascii("mi_audio_file_24px") == "🎵"
    assert get_icon_ascii("mi_video_file_24px") == "🎬"


def test_get_icon_ascii_status():
    """Test device status icon lookups"""
    assert get_icon_ascii("mi_battery_full_24px") == "🔋"
    assert get_icon_ascii("mi_network_wifi_24px") == "📶"
    assert get_icon_ascii("mi_volume_up_24px") == "🔊"


def test_get_icon_ascii_media():
    """Test media control icon lookups"""
    assert get_icon_ascii("mi_play_arrow_24px") == "▶"
    assert get_icon_ascii("mi_pause_24px") == "⏸"
    assert get_icon_ascii("mi_stop_24px") == "⏹"


def test_get_icon_ascii_security():
    """Test security/alert icon lookups"""
    assert get_icon_ascii("mi_lock_24px") == "🔒"
    assert get_icon_ascii("mi_lock_open_24px") == "🔓"
    assert get_icon_ascii("mi_warning_24px") == "⚠"
    assert get_icon_ascii("mi_error_24px") == "⛔"
    assert get_icon_ascii("mi_info_24px") == "ℹ"


def test_get_icon_ascii_unknown():
    """Test fallback for unknown icons"""
    assert get_icon_ascii("mi_nonexistent") == "?"
    assert get_icon_ascii("mi_nonexistent", "X") == "X"
    assert get_icon_ascii("", "?") == "?"


def test_icon_exists():
    """Test icon_exists checker"""
    assert icon_exists("mi_home_24px") is True
    assert icon_exists("mi_folder_24px") is True
    assert icon_exists("mi_play_arrow_24px") is True
    assert icon_exists("mi_nonexistent") is False
    assert icon_exists("") is False


def test_all_icons_have_ascii():
    """Test that all mapped icons have non-empty ASCII"""
    for symbol, ascii_char in ICON_ASCII_MAP.items():
        assert len(ascii_char) > 0, f"Icon {symbol} has empty ASCII"
        assert len(ascii_char) <= 5, f"Icon {symbol} ASCII too long: {ascii_char}"


def test_common_icons_present():
    """Test that commonly used icons are present"""
    common_icons = [
        "mi_home_24px",
        "mi_settings_24px",
        "mi_folder_24px",
        "mi_save_24px",
        "mi_delete_24px",
        "mi_search_24px",
        "mi_close_24px",
        "mi_check_24px",
        "mi_play_arrow_24px",
        "mi_battery_full_24px",
    ]
    
    for icon in common_icons:
        assert icon in ICON_ASCII_MAP, f"Common icon {icon} missing from map"
        assert icon_exists(icon), f"icon_exists should return True for {icon}"


def test_icon_uniqueness():
    """Test that icon symbols are unique (no duplicates)"""
    symbols = list(ICON_ASCII_MAP.keys())
    assert len(symbols) == len(set(symbols)), "Icon symbols should be unique"


def test_ascii_characters_valid():
    """Test that ASCII characters are printable Unicode"""
    for symbol, ascii_char in ICON_ASCII_MAP.items():
        # Should not contain control characters
        assert not any(ord(c) < 32 for c in ascii_char), \
            f"Icon {symbol} has control character"
        
        # Should be valid Unicode
        try:
            ascii_char.encode('utf-8')
        except UnicodeEncodeError:
            pytest.fail(f"Icon {symbol} has invalid Unicode: {ascii_char}")


def test_category_coverage():
    """Test that all categories have icon coverage"""
    # Check navigation icons (should have most)
    nav_icons = [s for s in ICON_ASCII_MAP if "arrow" in s or "home" in s or 
                 "menu" in s or "search" in s or "settings" in s or "close" in s]
    assert len(nav_icons) >= 8, "Should have sufficient navigation icons"
    
    # Check file icons
    file_icons = [s for s in ICON_ASCII_MAP if "folder" in s or "save" in s or 
                  "delete" in s or "file" in s]
    assert len(file_icons) >= 10, "Should have sufficient file icons"
    
    # Check media icons
    media_icons = [s for s in ICON_ASCII_MAP if "play" in s or "pause" in s or 
                   "stop" in s or "audio" in s or "video" in s]
    assert len(media_icons) >= 5, "Should have sufficient media icons"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
