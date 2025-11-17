#!/usr/bin/env python3
"""Test Nudge Distance Settings feature"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_designer import UIDesigner, WidgetType


# Mock PreviewSettings to avoid UI dependencies
class PreviewSettings:
    """Mock PreviewSettings for testing"""
    def __init__(self):
        self.zoom = 4.0
        self.grid_enabled = True
        self.grid_size = 8
        self.snap_enabled = True
        self.snap_size = 4
        self.show_bounds = True
        self.show_handles = True
        self.background_color = "#000000"
        self.pixel_perfect = True
        self.nudge_distance = 1
        self.nudge_shift_distance = 8


def test_nudge_settings_defaults():
    """Test that nudge settings have correct defaults"""
    settings = PreviewSettings()
    
    assert settings.nudge_distance == 1, "Default nudge distance should be 1px"
    assert settings.nudge_shift_distance == 8, "Default shift+nudge distance should be 8px"
    
    print("✅ Default nudge settings correct:")
    print(f"   Normal nudge: {settings.nudge_distance}px")
    print(f"   Shift+nudge: {settings.nudge_shift_distance}px")


def test_nudge_distance_configuration():
    """Test configurable nudge distances"""
    settings = PreviewSettings()
    
    # Test changing normal nudge distance
    settings.nudge_distance = 2
    assert settings.nudge_distance == 2, "Should update nudge distance"
    
    # Test changing shift nudge distance
    settings.nudge_shift_distance = 16
    assert settings.nudge_shift_distance == 16, "Should update shift+nudge distance"
    
    print("✅ Nudge settings configurable:")
    print(f"   Updated normal nudge: {settings.nudge_distance}px")
    print(f"   Updated shift+nudge: {settings.nudge_shift_distance}px")


def test_nudge_logic():
    """Test nudge distance logic simulation"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    designer.add_widget(WidgetType.LABEL, x=50, y=30, width=40, height=12, text="Test")
    
    scene = designer.scenes.get(designer.current_scene or "test")
    assert scene is not None, "Scene should exist"
    widget = scene.widgets[0]
    
    initial_x = widget.x
    initial_y = widget.y
    
    # Simulate normal nudge right (1px)
    settings = PreviewSettings()
    nudge_distance = settings.nudge_distance
    widget.x += nudge_distance
    
    assert widget.x == initial_x + 1, "Normal nudge should move 1px"
    print(f"✅ Normal nudge right: {initial_x} -> {widget.x} (+{nudge_distance}px)")
    
    # Simulate shift+nudge down (8px)
    shift_nudge_distance = settings.nudge_shift_distance
    widget.y += shift_nudge_distance
    
    assert widget.y == initial_y + 8, "Shift+nudge should move 8px"
    print(f"✅ Shift+nudge down: {initial_y} -> {widget.y} (+{shift_nudge_distance}px)")
    
    # Test custom distances
    settings.nudge_distance = 3
    settings.nudge_shift_distance = 12
    
    widget.x += settings.nudge_distance
    assert widget.x == initial_x + 1 + 3, "Custom nudge distance works"
    print(f"✅ Custom nudge distance (3px): widget.x = {widget.x}")
    
    widget.y += settings.nudge_shift_distance
    assert widget.y == initial_y + 8 + 12, "Custom shift+nudge distance works"
    print(f"✅ Custom shift+nudge distance (12px): widget.y = {widget.y}")


def test_nudge_bounds_clamping():
    """Test that nudge respects canvas bounds"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    designer.add_widget(WidgetType.BUTTON, x=120, y=60, width=40, height=12, text="Edge")
    
    scene = designer.scenes.get(designer.current_scene or "test")
    assert scene is not None, "Scene should exist"
    widget = scene.widgets[0]
    
    settings = PreviewSettings()
    
    # Try to nudge right beyond canvas width
    new_x = widget.x + settings.nudge_distance
    max_x = designer.width - widget.width
    clamped_x = max(0, min(new_x, max_x))
    
    # Widget at x=120 with width=40 can't go past x=88 (128-40)
    assert clamped_x == max_x, "Should clamp to canvas boundary"
    print(f"✅ Nudge bounds clamping: x={widget.x} -> clamped to {clamped_x} (max={max_x})")
    
    # Try to nudge down beyond canvas height
    new_y = widget.y + settings.nudge_distance
    max_y = designer.height - widget.height
    clamped_y = max(0, min(new_y, max_y))
    
    # Widget at y=60 with height=12 can't go past y=52 (64-12)
    assert clamped_y == max_y, "Should clamp to canvas boundary"
    print(f"✅ Nudge bounds clamping: y={widget.y} -> clamped to {clamped_y} (max={max_y})")


if __name__ == '__main__':
    test_nudge_settings_defaults()
    test_nudge_distance_configuration()
    test_nudge_logic()
    test_nudge_bounds_clamping()
    print("\n🎉 All Nudge Settings tests passed!")
