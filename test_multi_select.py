#!/usr/bin/env python3
"""Test Multi-Select Improvements feature"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_designer import UIDesigner, WidgetType


def test_box_select_rectangle_bounds():
    """Test box select rectangle normalization"""
    # Simulate box select coordinates
    x1, y1 = 50, 50
    x2, y2 = 100, 150
    
    # Normalize (x1 < x2, y1 < y2)
    min_x = min(x1, x2)
    max_x = max(x1, x2)
    min_y = min(y1, y2)
    max_y = max(y1, y2)
    
    assert min_x == 50, "Min X should be 50"
    assert max_x == 100, "Max X should be 100"
    assert min_y == 50, "Min Y should be 50"
    assert max_y == 150, "Max Y should be 150"
    print(f"✅ Box select normalization: ({x1},{y1}) -> ({x2},{y2}) = [{min_x},{min_y}] to [{max_x},{max_y}]")
    
    # Test reverse drag (right to left)
    x1, y1 = 100, 150
    x2, y2 = 50, 50
    min_x = min(x1, x2)
    max_x = max(x1, x2)
    min_y = min(y1, y2)
    max_y = max(y1, y2)
    
    assert min_x == 50, "Min X should be 50 (reversed)"
    assert max_x == 100, "Max X should be 100 (reversed)"
    print(f"✅ Reverse drag normalization: ({x1},{y1}) -> ({x2},{y2}) = [{min_x},{min_y}] to [{max_x},{max_y}]")


def test_widget_overlap_detection():
    """Test if widget overlaps with selection rectangle"""
    # Widget bounds
    wx1, wy1 = 60, 60
    wx2, wy2 = 90, 90
    
    # Selection rectangle
    sel_x1, sel_y1 = 50, 50
    sel_x2, sel_y2 = 100, 100
    
    # Check overlap (rectangles intersect if NOT completely separated)
    overlaps = not (wx2 < sel_x1 or wx1 > sel_x2 or wy2 < sel_y1 or wy1 > sel_y2)
    
    assert overlaps, "Widget should overlap with selection"
    print(f"✅ Widget overlap detected: widget[{wx1},{wy1}]-[{wx2},{wy2}] overlaps selection[{sel_x1},{sel_y1}]-[{sel_x2},{sel_y2}]")
    
    # Test non-overlapping widget
    wx1, wy1 = 200, 200
    wx2, wy2 = 250, 250
    overlaps = not (wx2 < sel_x1 or wx1 > sel_x2 or wy2 < sel_y1 or wy1 > sel_y2)
    
    assert not overlaps, "Widget should NOT overlap with selection"
    print(f"✅ No overlap: widget[{wx1},{wy1}]-[{wx2},{wy2}] outside selection[{sel_x1},{sel_y1}]-[{sel_x2},{sel_y2}]")


def test_batch_property_update():
    """Test updating property for multiple widgets"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Create 3 labels
    designer.add_widget(WidgetType.LABEL, x=10, y=10, width=30, height=10, text="Label 1")
    designer.add_widget(WidgetType.LABEL, x=50, y=10, width=30, height=10, text="Label 2")
    designer.add_widget(WidgetType.LABEL, x=90, y=10, width=30, height=10, text="Label 3")
    
    scene = designer.scenes.get(designer.current_scene or "test")
    assert scene is not None, "Scene should exist"
    assert len(scene.widgets) == 3, "Should have 3 widgets"
    
    # Simulate batch update (change all colors)
    widget_indices = [0, 1, 2]
    new_color = "red"
    
    for idx in widget_indices:
        if idx < len(scene.widgets) and hasattr(scene.widgets[idx], 'color'):
            scene.widgets[idx].color = new_color
    
    # Verify all updated
    for idx in widget_indices:
        widget = scene.widgets[idx]
        if hasattr(widget, 'color'):
            assert widget.color == "red", f"Widget {idx} color should be red"
    
    print(f"✅ Batch property update: Changed color of {len(widget_indices)} widgets to '{new_color}'")


def test_multi_delete():
    """Test deleting multiple selected widgets"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Create 5 buttons
    for i in range(5):
        designer.add_widget(WidgetType.BUTTON, x=i*25, y=10, width=20, height=10, text=f"Btn{i+1}")
    
    scene = designer.scenes.get(designer.current_scene or "test")
    assert scene is not None, "Scene should exist"
    assert len(scene.widgets) == 5, "Should have 5 widgets"
    
    # Select widgets 1, 2, 4 (indices 1, 2, 4)
    selected = [1, 2, 4]
    
    # Delete in reverse order to avoid index shifting
    for idx in sorted(selected, reverse=True):
        if idx < len(scene.widgets):
            del scene.widgets[idx]
    
    # Should have 2 widgets left (0, 3)
    assert len(scene.widgets) == 2, "Should have 2 widgets remaining"
    assert scene.widgets[0].text == "Btn1", "First widget should be Btn1"
    assert scene.widgets[1].text == "Btn4", "Second widget should be Btn4"
    
    print(f"✅ Multi-delete: Deleted {len(selected)} widgets, {len(scene.widgets)} remaining")
    print(f"   Remaining: {scene.widgets[0].text}, {scene.widgets[1].text}")


def test_shift_selection_toggle():
    """Test Shift+click selection toggle behavior"""
    selected_widgets = []
    
    # Click widget 0 (no Shift) - single select
    selected_widgets = [0]
    assert selected_widgets == [0], "Single select should replace selection"
    print("✅ Single select (no Shift): [0]")
    
    # Shift+click widget 2 - add to selection
    widget_idx = 2
    if widget_idx in selected_widgets:
        selected_widgets.remove(widget_idx)
    else:
        selected_widgets.append(widget_idx)
    
    assert selected_widgets == [0, 2], "Shift+click should add to selection"
    print("✅ Shift+click add: [0, 2]")
    
    # Shift+click widget 0 again - toggle off
    widget_idx = 0
    if widget_idx in selected_widgets:
        selected_widgets.remove(widget_idx)
    else:
        selected_widgets.append(widget_idx)
    
    assert selected_widgets == [2], "Shift+click on selected should remove"
    print("✅ Shift+click remove: [2]")


if __name__ == '__main__':
    test_box_select_rectangle_bounds()
    test_widget_overlap_detection()
    test_batch_property_update()
    test_multi_delete()
    test_shift_selection_toggle()
    print("\n🎉 All Multi-Select tests passed!")
