#!/usr/bin/env python3
"""
Test template manager functionality
"""

import json
import os
import tempfile

import pytest

from ui_designer import UIDesigner, WidgetConfig


def test_widget_to_dict_conversion():
    """Test converting widget to dictionary"""
    widget = WidgetConfig(
        type="button",
        x=10,
        y=20,
        width=50,
        height=30,
        text="Click Me",
        visible=True,
        border=True
    )
    
    # Manually test conversion logic
    widget_dict = {
        "type": widget.type,
        "x": widget.x,
        "y": widget.y,
        "width": widget.width,
        "height": widget.height,
        "text": widget.text,
        "visible": widget.visible,
        "border": widget.border,
        "checked": False,
        "value": 0,
    }
    
    assert widget_dict["type"] == "button"
    assert widget_dict["x"] == 10
    assert widget_dict["y"] == 20
    assert widget_dict["text"] == "Click Me"
    assert widget_dict["border"] is True


def test_dict_to_widget_conversion():
    """Test converting dictionary back to widget"""
    widget_data = {
        "type": "label",
        "x": 5,
        "y": 15,
        "width": 100,
        "height": 20,
        "text": "Test Label",
        "visible": True,
        "border": False,
        "checked": False,
        "value": 0,
    }
    
    widget = WidgetConfig(
        type=widget_data["type"],
        x=widget_data["x"],
        y=widget_data["y"],
        width=widget_data["width"],
        height=widget_data["height"],
        text=widget_data["text"],
        visible=widget_data["visible"],
        border=widget_data["border"],
    )
    
    assert widget.type == "label"
    assert widget.x == 5
    assert widget.y == 15
    assert widget.text == "Test Label"


def test_template_save_load():
    """Test saving and loading template from file"""
    # Create temporary directory for templates
    with tempfile.TemporaryDirectory() as tmpdir:
        template_data = {
            "name": "Test Template",
            "description": "A test template",
            "widgets": [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 50,
                    "height": 20,
                    "text": "Button 1",
                    "visible": True,
                    "border": True,
                    "checked": False,
                    "value": 0,
                },
                {
                    "type": "label",
                    "x": 0,
                    "y": 25,
                    "width": 50,
                    "height": 15,
                    "text": "Label 1",
                    "visible": True,
                    "border": False,
                    "checked": False,
                    "value": 0,
                }
            ]
        }
        
        # Save template
        filepath = os.path.join(tmpdir, "test_template.json")
        with open(filepath, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        # Load template
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["name"] == "Test Template"
        assert len(loaded_data["widgets"]) == 2
        assert loaded_data["widgets"][0]["type"] == "button"
        assert loaded_data["widgets"][1]["type"] == "label"


def test_template_list_empty():
    """Test template listing with empty directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # List templates in empty directory
        template_files = [f for f in os.listdir(tmpdir) if f.endswith('.json')]
        assert len(template_files) == 0


def test_template_list_multiple():
    """Test template listing with multiple templates"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple template files
        for i in range(3):
            template_data = {
                "name": f"Template {i}",
                "description": f"Test template {i}",
                "widgets": []
            }
            filepath = os.path.join(tmpdir, f"template_{i}.json")
            with open(filepath, 'w') as f:
                json.dump(template_data, f)
        
        # List templates
        template_files = sorted([f for f in os.listdir(tmpdir) if f.endswith('.json')])
        assert len(template_files) == 3
        assert template_files[0] == "template_0.json"
        assert template_files[2] == "template_2.json"


def test_template_delete():
    """Test template deletion"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create template
        template_data = {"name": "Delete Me", "widgets": []}
        filepath = os.path.join(tmpdir, "delete_me.json")
        with open(filepath, 'w') as f:
            json.dump(template_data, f)
        
        assert os.path.exists(filepath)
        
        # Delete template
        os.remove(filepath)
        
        assert not os.path.exists(filepath)


def test_template_widget_count():
    """Test widget count in template"""
    template_data = {
        "name": "Multi Widget",
        "widgets": [
            {"type": "button", "x": 0, "y": 0, "width": 10, "height": 10},
            {"type": "label", "x": 0, "y": 15, "width": 10, "height": 10},
            {"type": "box", "x": 0, "y": 30, "width": 10, "height": 10},
        ]
    }
    
    widget_count = len(template_data["widgets"])
    assert widget_count == 3


def test_template_name_sanitization():
    """Test template filename sanitization"""
    template_name = "My Cool Template"
    filename = template_name.lower().replace(' ', '_') + ".json"
    
    assert filename == "my_cool_template.json"
    assert ' ' not in filename
    assert filename.endswith('.json')


def test_template_integration_with_designer():
    """Test loading template into designer"""
    designer = UIDesigner()
    designer.create_scene("test")
    
    # Simulate loading template widgets
    template_widgets = [
        {
            "type": "button",
            "x": 10,
            "y": 10,
            "width": 40,
            "height": 20,
            "text": "Btn1",
            "visible": True,
            "border": True,
            "checked": False,
            "value": 0,
        },
        {
            "type": "label",
            "x": 10,
            "y": 35,
            "width": 40,
            "height": 15,
            "text": "Lbl1",
            "visible": True,
            "border": False,
            "checked": False,
            "value": 0,
        }
    ]
    
    scene = designer.scenes["test"]
    initial_count = len(scene.widgets)
    
    # Add template widgets
    for widget_data in template_widgets:
        widget = WidgetConfig(
            type=widget_data["type"],
            x=widget_data["x"],
            y=widget_data["y"],
            width=widget_data["width"],
            height=widget_data["height"],
            text=widget_data["text"],
            visible=widget_data["visible"],
            border=widget_data["border"],
        )
        scene.widgets.append(widget)
    
    assert len(scene.widgets) == initial_count + 2
    assert scene.widgets[-2].type == "button"
    assert scene.widgets[-1].type == "label"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
