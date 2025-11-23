#!/usr/bin/env python3
"""
Integration tests for UI Designer palette workflow: add → edit → export
"""
import sys

sys.path.insert(0, '.')
from ui_components_library_ascii import (
    create_chart_ascii,
    create_checkbox_ascii,
    create_notification_ascii,
    create_slider_ascii,
)
from ui_designer import UIDesigner


def test_palette_workflow_add_components():
    """Test adding components from palette to canvas"""
    designer = UIDesigner()
    designer.create_scene("main")
    
    # Simulate adding components (as palette would)
    for w in create_slider_ascii():
        designer.add_widget(w)
    for w in create_checkbox_ascii():
        designer.add_widget(w)
    
    scene = designer.scenes[designer.current_scene]
    assert len(scene.widgets) >= 6  # Slider + Checkbox widgets

def test_palette_workflow_edit_properties():
    """Test editing widget properties after adding"""
    designer = UIDesigner()
    designer.create_scene("main")
    
    # Add component
    for w in create_slider_ascii(label="Volume", value=75):
        designer.add_widget(w)
    
    scene = designer.scenes[designer.current_scene]
    # Find label widget
    label_widget = next((w for w in scene.widgets if w.type == "label" and "Volume" in w.text), None)
    assert label_widget is not None
    
    # Edit property
    label_widget.text = "Master Volume"
    assert label_widget.text == "Master Volume"

def test_palette_workflow_export_json(tmp_path):
    """Test exporting scene with palette components as JSON"""
    designer = UIDesigner()
    designer.create_scene("main")
    
    # Add multiple components
    for w in create_chart_ascii():
        designer.add_widget(w)
    for w in create_notification_ascii(message="Test", type_="success"):
        designer.add_widget(w)
    
    # Export
    out_file = tmp_path / "palette_scene.json"
    designer.save_to_json(str(out_file))
    
    assert out_file.exists()
    # Verify content
    import json
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "scenes" in data
    assert "main" in data["scenes"]
    assert len(data["scenes"]["main"]["widgets"]) > 0

def test_palette_workflow_export_widgetconfig(tmp_path):
    """Test exporting palette components as WidgetConfig"""
    designer = UIDesigner()
    designer.create_scene("main")
    
    # Add components
    for w in create_checkbox_ascii(label="Enable Feature", checked=True):
        designer.add_widget(w)
    
    scene = designer.scenes[designer.current_scene]
    
    # Export WidgetConfig
    out_file = tmp_path / "widgets.txt"
    lines = []
    for w in scene.widgets:
        props = [f"{k}={getattr(w, k)}" for k in w.__dataclass_fields__]
        lines.append(f"[{w.type}] " + ", ".join(props))
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "[box]" in content or "[label]" in content

def test_palette_workflow_ascii_preview():
    """Test ASCII preview rendering of palette components"""
    designer = UIDesigner()
    designer.create_scene("main")
    
    # Add components
    for w in create_slider_ascii():
        designer.add_widget(w)
    
    # Generate ASCII preview
    preview = designer.preview_ascii()
    assert isinstance(preview, str)
    assert len(preview) > 0

def test_large_scene_performance():
    """Test performance with large number of widgets (100+)"""
    designer = UIDesigner()
    designer.create_scene("large")
    
    # Add 100+ widgets (checkbox has 3 widgets each)
    for i in range(40):
        for w in create_checkbox_ascii(label=f"Option {i}"):
            w.y += i * 2  # Offset vertically
            designer.add_widget(w)
    
    scene = designer.scenes[designer.current_scene]
    assert len(scene.widgets) >= 100
    
    # Test operations don't hang
    preview = designer.preview_ascii()
    assert len(preview) > 0

def test_palette_workflow_undo_redo():
    """Test undo/redo with palette component additions"""
    designer = UIDesigner()
    designer.create_scene("main")
    
    # Add component
    initial_count = len(designer.scenes["main"].widgets)
    for w in create_notification_ascii():
        designer.add_widget(w)
    
    new_count = len(designer.scenes["main"].widgets)
    assert new_count > initial_count
    
    # Undo (only undoes last widget added, not all)
    designer.undo()
    undo_count = len(designer.scenes["main"].widgets)
    assert undo_count < new_count  # Should have fewer widgets
    
    # Redo
    designer.redo()
    redo_count = len(designer.scenes["main"].widgets)
    assert redo_count > undo_count  # Should restore widget
