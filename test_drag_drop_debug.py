#!/usr/bin/env python3
"""
Test drag and drop functionality in UI designer preview
"""

import os

os.environ["ESP32OS_HEADLESS"] = "1"

from ui_designer import UIDesigner
from ui_designer_preview import VisualPreviewWindow


def test_drag_drop_basic():
    """Test basic drag and drop functionality"""
    print("Testing drag and drop in headless mode...")
    
    # Create designer and preview
    designer = UIDesigner(128, 64)
    designer.create_scene("test")
    designer.current_scene = "test"
    
    # Add a test widget
    designer.add_widget(
        'label',
        x=20,
        y=20,
        width=50,
        height=20,
        text="Drag Me"
    )
    
    print(f"Initial widget position: ({designer.scenes['test'].widgets[0].x}, {designer.scenes['test'].widgets[0].y})")
    
    # Create preview window (headless)
    preview = VisualPreviewWindow(designer)
    preview.settings.zoom = 3.0
    preview.settings.snap_enabled = True
    preview.settings.snap_size = 10
    
    # Check if mouse handlers exist
    print(f"\nPreview has dragging attribute: {hasattr(preview, 'dragging')}")
    print(f"Preview has _on_mouse_down: {hasattr(preview, '_on_mouse_down')}")
    print(f"Preview has _on_mouse_drag: {hasattr(preview, '_on_mouse_drag')}")
    print(f"Preview has _on_mouse_up: {hasattr(preview, '_on_mouse_up')}")
    
    # Create mock event
    class MockEvent:
        def __init__(self, x: int, y: int, state: int = 0):
            self.x = x
            self.y = y
            self.state = state
    
    # Calculate canvas coordinates
    canvas_x = int((20 + 25) * preview.settings.zoom)  # center of widget
    canvas_y = int((20 + 10) * preview.settings.zoom)
    
    print(f"\nMouse down at canvas coords: ({canvas_x}, {canvas_y})")
    
    # Mouse down
    event_down = MockEvent(canvas_x, canvas_y)
    if hasattr(preview, '_on_mouse_down'):
        preview._on_mouse_down(event_down)
        
        print(f"Dragging: {preview.dragging}")
        print(f"Selected widget idx: {preview.selected_widget_idx}")
        print(f"Drag offset: {preview.drag_offset if hasattr(preview, 'drag_offset') else 'N/A'}")
        
        # Simulate drag
        new_canvas_x = canvas_x + 30
        new_canvas_y = canvas_y + 20
        
        event_drag = MockEvent(new_canvas_x, new_canvas_y)
        preview._on_mouse_drag(event_drag)
        
        print(f"\nAfter drag to canvas ({new_canvas_x}, {new_canvas_y}):")
        print(f"Widget position: ({designer.scenes['test'].widgets[0].x}, {designer.scenes['test'].widgets[0].y})")
        
        # Mouse up
        event_up = MockEvent(new_canvas_x, new_canvas_y)
        preview._on_mouse_up(event_up)
        
        print("\nAfter mouse up:")
        print(f"Dragging: {preview.dragging}")
        print(f"Final widget position: ({designer.scenes['test'].widgets[0].x}, {designer.scenes['test'].widgets[0].y})")
        
        # Check if position changed
        final_x = designer.scenes['test'].widgets[0].x
        final_y = designer.scenes['test'].widgets[0].y
        
        if final_x != 20 or final_y != 20:
            print("\n✓ Drag and drop WORKS! Widget moved.")
        else:
            print("\n✗ Drag and drop FAILED! Widget did not move.")
            print("\nDebugging info:")
            print(f"  - Initial dragging state: {preview.dragging}")
            print(f"  - Selected widget: {preview.selected_widget_idx}")
            if hasattr(preview, 'drag_offset'):
                print(f"  - Drag offset calculated: {preview.drag_offset}")
    else:
        print("\n✗ ERROR: Preview window missing mouse event handlers!")

if __name__ == "__main__":
    test_drag_drop_basic()
