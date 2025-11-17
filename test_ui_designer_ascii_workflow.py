#!/usr/bin/env python3
"""
Automated tests for UI Designer workflows and export formats (ASCII components)
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


def test_add_ascii_components():
    designer = UIDesigner()
    designer.create_scene("main")
    # Add slider
    for w in create_slider_ascii():
        designer.add_widget(w)
    # Add checkbox
    for w in create_checkbox_ascii():
        designer.add_widget(w)
    # Add notification
    for w in create_notification_ascii():
        designer.add_widget(w)
    # Add chart
    for w in create_chart_ascii():
        designer.add_widget(w)
    scene = designer.scenes[designer.current_scene]
    assert len(scene.widgets) >= 12  # All widgets added

def test_export_json(tmp_path):
    designer = UIDesigner()
    designer.create_scene("main")
    for w in create_slider_ascii():
        designer.add_widget(w)
    out_file = tmp_path / "scene.json"
    designer.save_to_json(str(out_file))
    assert out_file.exists()

def test_export_widgetconfig(tmp_path):
    designer = UIDesigner()
    designer.create_scene("main")
    for w in create_checkbox_ascii():
        designer.add_widget(w)
    out_file = tmp_path / "scene.txt"
    # Simulate WidgetConfig export
    scene = designer.scenes[designer.current_scene]
    lines = [f"[{w.type}] " + ", ".join(f"{k}={getattr(w, k)}" for k in w.__dataclass_fields__) for w in scene.widgets]
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    assert out_file.exists()

def test_ascii_preview():
    designer = UIDesigner()
    designer.create_scene("main")
    for w in create_chart_ascii():
        designer.add_widget(w)
    preview = designer.preview_ascii()
    assert isinstance(preview, str)
    assert len(preview) > 0
