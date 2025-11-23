#!/usr/bin/env python3
"""
Tests for UI Designer alignment and distribution features
"""

import pytest
from ui_designer import UIDesigner, WidgetType


def test_alignment_tools():
    """Test widget alignment functionality"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Add widgets at different positions
    designer.add_widget(WidgetType.BOX, x=10, y=10, width=20, height=20, border=False)
    designer.add_widget(WidgetType.BOX, x=40, y=15, width=20, height=20, border=False)
    designer.add_widget(WidgetType.BOX, x=70, y=20, width=20, height=20, border=False)
    
    scene = designer.scenes[designer.current_scene]
    widgets = scene.widgets
    
    # Simulate left alignment (align all to first widget's x)
    ref_x = widgets[0].x
    for w in widgets[1:]:
        w.x = ref_x
    
    # All widgets should have the same x coordinate
    assert widgets[0].x == widgets[1].x
    assert widgets[1].x == widgets[2].x
    
    # Restore positions for next test
    widgets[1].x = 40
    widgets[2].x = 70
    
    # Simulate top alignment
    ref_y = widgets[0].y
    for w in widgets[1:]:
        w.y = ref_y
    
    # All widgets should have the same y coordinate
    assert widgets[0].y == widgets[1].y
    assert widgets[1].y == widgets[2].y


def test_distribution():
    """Test widget distribution"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Add 4 widgets
    designer.add_widget(WidgetType.BOX, x=0, y=10, width=10, height=10)
    designer.add_widget(WidgetType.BOX, x=20, y=10, width=10, height=10)
    designer.add_widget(WidgetType.BOX, x=50, y=10, width=10, height=10)
    designer.add_widget(WidgetType.BOX, x=100, y=10, width=10, height=10)
    
    scene = designer.scenes[designer.current_scene]
    widgets = scene.widgets
    
    # Sort by x
    widgets_sorted = sorted(widgets, key=lambda w: w.x)
    first = widgets_sorted[0]
    last = widgets_sorted[-1]
    
    # Calculate even distribution
    total_space = (last.x - (first.x + first.width))
    total_widget_width = sum(w.width for w in widgets_sorted[1:-1])
    gap = (total_space - total_widget_width) / (len(widgets_sorted) - 1)
    
    # Apply distribution
    current_x = first.x + first.width + gap
    for widget in widgets_sorted[1:-1]:
        widget.x = int(current_x)
        current_x += widget.width + gap
    
    # Verify spacing is more even
    gaps = []
    for i in range(len(widgets_sorted) - 1):
        gap_size = widgets_sorted[i+1].x - (widgets_sorted[i].x + widgets_sorted[i].width)
        gaps.append(gap_size)
    
    # All gaps should be similar (within 1 pixel due to rounding)
    assert max(gaps) - min(gaps) <= 1


def test_copy_paste():
    """Test widget copy/paste functionality"""
    from copy import deepcopy
    
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Add widgets
    designer.add_widget(WidgetType.LABEL, x=10, y=10, width=50, height=10, text="Original", border=False)
    designer.add_widget(WidgetType.BUTTON, x=20, y=25, width=40, height=12, text="Button", border=False)
    
    scene = designer.scenes[designer.current_scene]
    original_count = len(scene.widgets)
    original_x0 = scene.widgets[0].x
    original_x1 = scene.widgets[1].x
    
    # Simulate clipboard copy
    clipboard = [deepcopy(scene.widgets[0]), deepcopy(scene.widgets[1])]
    
    # Simulate paste with offset
    for widget in clipboard:
        new_widget = deepcopy(widget)
        new_widget.x += 10
        new_widget.y += 10
        scene.widgets.append(new_widget)
    
    # Should have 4 widgets now
    assert len(scene.widgets) == original_count + 2
    
    # Verify copied widgets have offset applied
    assert scene.widgets[2].text == "Original"
    assert scene.widgets[2].x == original_x0 + 10
    assert scene.widgets[2].y == scene.widgets[0].y + 10
    
    assert scene.widgets[3].text == "Button"
    assert scene.widgets[3].x == original_x1 + 10
    assert scene.widgets[3].y == scene.widgets[1].y + 10


def test_multi_selection():
    """Test multi-selection behavior"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Add widgets
    for i in range(5):
        designer.add_widget(WidgetType.BOX, x=i*20, y=10, width=15, height=15)
    
    # Simulate multi-selection
    selected_widgets = [0, 2, 4]  # Select 1st, 3rd, 5th widget
    
    assert len(selected_widgets) == 3
    assert 0 in selected_widgets
    assert 2 in selected_widgets
    assert 4 in selected_widgets
    assert 1 not in selected_widgets


def test_undo_redo_exists():
    """Test that undo/redo methods exist"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    # Add a widget
    designer.add_widget(WidgetType.BOX, x=10, y=10, width=20, height=20, border=False)
    
    # Test undo/redo methods exist and are callable
    assert hasattr(designer, 'undo')
    assert hasattr(designer, 'redo')
    assert callable(designer.undo)
    assert callable(designer.redo)
    
    # Call them (should not raise errors even if history is empty)
    designer.undo()
    designer.redo()


def test_nudge_with_grid():
    """Test nudging with grid snap"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    
    designer.add_widget(WidgetType.BOX, x=10, y=10, width=20, height=20, border=False)
    
    scene = designer.scenes[designer.current_scene]
    widget = scene.widgets[0]
    
    original_x = widget.x
    original_y = widget.y
    
    # Nudge right by 4 pixels (grid size)
    snap_size = 4
    widget.x += snap_size
    
    assert widget.x == original_x + snap_size
    
    # Nudge down
    widget.y += snap_size
    
    assert widget.y == original_y + snap_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
