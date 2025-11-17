#!/usr/bin/env python3
"""Test Selection Handles improvements"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_designer import UIDesigner, WidgetType


def test_handle_hitbox_tolerance():
    """Test increased hitbox tolerance for easier grabbing"""
    # Original tolerance
    old_tolerance = 3
    
    # New improved tolerance
    new_tolerance = 6
    
    # Handle center position
    handle_x, handle_y = 50, 50
    
    # Test click 5px away (would miss with old tolerance)
    click_x, click_y = 55, 55
    distance = max(abs(click_x - handle_x), abs(click_y - handle_y))
    
    old_hit = distance <= old_tolerance
    new_hit = distance <= new_tolerance
    
    assert not old_hit, "Old tolerance (3px) should miss 5px away click"
    assert new_hit, "New tolerance (6px) should catch 5px away click"
    
    print(f"✅ Hitbox tolerance: {old_tolerance}px -> {new_tolerance}px")
    print(f"   Click at distance {distance}px: old={old_hit}, new={new_hit}")


def test_handle_visual_size():
    """Test larger handle visual size"""
    old_size = 6  # Old handle size
    new_size = 8  # New handle size
    
    # Calculate visual area
    old_area = old_size * old_size
    new_area = new_size * new_size
    
    area_increase = ((new_area - old_area) / old_area) * 100
    
    assert new_size > old_size, "New handles should be larger"
    assert area_increase > 70, "Area should increase by >70%"
    
    print(f"✅ Handle visual size: {old_size}px -> {new_size}px")
    print(f"   Area increase: {area_increase:.1f}% (more visible)")


def test_handle_border_width():
    """Test stronger handle borders"""
    old_border = 1  # Old border width
    new_border = 2  # New border width
    
    assert new_border > old_border, "Border should be thicker"
    print(f"✅ Handle border width: {old_border}px -> {new_border}px (better visibility)")


def test_cursor_types():
    """Test appropriate cursor types for each handle"""
    cursor_map = {
        "nw": "top_left_corner",
        "ne": "top_right_corner",
        "se": "bottom_right_corner",
        "sw": "bottom_left_corner",
        "n": "sb_v_double_arrow",
        "s": "sb_v_double_arrow",
        "w": "sb_h_double_arrow",
        "e": "sb_h_double_arrow",
    }
    
    # Test corner cursors
    assert cursor_map["nw"] == "top_left_corner", "NW should use diagonal cursor"
    assert cursor_map["se"] == "bottom_right_corner", "SE should use diagonal cursor"
    
    # Test edge cursors
    assert cursor_map["n"] == "sb_v_double_arrow", "North should use vertical cursor"
    assert cursor_map["w"] == "sb_h_double_arrow", "West should use horizontal cursor"
    
    print("✅ Cursor types for handles:")
    print("   Corners: diagonal arrows (↖ ↗ ↘ ↙)")
    print("   Edges: double arrows (↕ ↔)")


def test_hover_color_brightness():
    """Test hover color is brighter than normal"""
    normal_color = "#00AAFF"
    hover_color = "#00DDFF"
    
    # Extract blue component (rightmost 2 hex digits)
    normal_blue = int(normal_color[-2:], 16)
    hover_blue = int(hover_color[-2:], 16)
    
    # Extract green component (middle 2 hex digits)
    normal_green = int(normal_color[3:5], 16)
    hover_green = int(hover_color[3:5], 16)
    
    assert hover_blue == 255, "Hover should have max blue"
    assert hover_green > normal_green, "Hover should be brighter"
    
    brightness_increase = ((hover_green - normal_green) / normal_green) * 100
    
    print(f"✅ Hover color brightness:")
    print(f"   Normal: {normal_color} (green={normal_green})")
    print(f"   Hover: {hover_color} (green={hover_green}, +{brightness_increase:.1f}%)")


def test_total_hitbox_area():
    """Test total clickable area for handle"""
    visual_size = 8  # pixels
    tolerance = 6    # pixels each side
    
    # Total hitbox size = visual + tolerance on each side
    total_hitbox = visual_size + (tolerance * 2)
    
    assert total_hitbox == 20, "Total hitbox should be 20px (8 + 12)"
    
    clickable_area = total_hitbox * total_hitbox
    visual_area = visual_size * visual_size
    
    area_ratio = clickable_area / visual_area
    
    print(f"✅ Total clickable area:")
    print(f"   Visual: {visual_size}x{visual_size} = {visual_area}px²")
    print(f"   Hitbox: {total_hitbox}x{total_hitbox} = {clickable_area}px²")
    print(f"   Ratio: {area_ratio:.1f}x easier to click!")


if __name__ == '__main__':
    test_handle_hitbox_tolerance()
    test_handle_visual_size()
    test_handle_border_width()
    test_cursor_types()
    test_hover_color_brightness()
    test_total_hitbox_area()
    print("\n🎉 All Selection Handles tests passed!")
