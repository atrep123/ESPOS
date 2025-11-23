#!/usr/bin/env python3
"""
Extended tests for UI Designer ASCII workflows: edge cases, error handling, and export validation
"""
import sys

sys.path.insert(0, '.')
from ui_components_library_ascii import (
    create_chart_ascii,
    create_checkbox_ascii,
    create_notification_ascii,
    create_slider_ascii,
)
from ui_designer import UIDesigner, WidgetConfig


def test_empty_scene_export(tmp_path):
    designer = UIDesigner()
    designer.create_scene("empty")
    out_file = tmp_path / "empty.json"
    designer.save_to_json(str(out_file))
    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        data = f.read()
    assert 'widgets' in data

def test_invalid_widget_properties():
    designer = UIDesigner()
    designer.create_scene("main")
    # Add widget with negative coordinates (will be snapped to 0)
    widget = WidgetConfig(type="label", x=-5, y=-5, width=0, height=0, text="Invalid")
    designer.add_widget(widget)
    scene = designer.scenes[designer.current_scene]
    # snap_position clamps negative coords to 0
    assert scene.widgets[-1].x == 0
    assert scene.widgets[-1].y == 0
    assert scene.widgets[-1].width == 0

def test_large_chart_export(tmp_path):
    designer = UIDesigner()
    designer.create_scene("main")
    data = [i for i in range(20)]
    for w in create_chart_ascii(data=data):
        designer.add_widget(w)
    out_file = tmp_path / "large_chart.txt"
    scene = designer.scenes[designer.current_scene]
    lines = [f"[{w.type}] " + ", ".join(f"{k}={getattr(w, k)}" for k in w.__dataclass_fields__) for w in scene.widgets]
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Chart" in content

def test_multiple_scenes():
    designer = UIDesigner()
    designer.create_scene("scene1")
    # Add widgets to scene1
    for w in create_slider_ascii():
        designer.add_widget(w)
    # Create scene2 and add different widgets
    designer.create_scene("scene2")
    for w in create_checkbox_ascii():
        designer.add_widget(w)
    # Verify both scenes have widgets
    assert len(designer.scenes["scene1"].widgets) > 0
    assert len(designer.scenes["scene2"].widgets) > 0

def test_notification_types():
    designer = UIDesigner()
    designer.create_scene("main")
    for t in ["info", "success", "error", "warning"]:
        for w in create_notification_ascii(type_=t):
            designer.add_widget(w)
    scene = designer.scenes[designer.current_scene]
    types = [w.color_bg for w in scene.widgets if hasattr(w, "color_bg")]
    assert "blue" in types
    assert "green" in types
    assert "red" in types
    assert "yellow" in types
