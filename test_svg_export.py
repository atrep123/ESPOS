#!/usr/bin/env python3
"""Tests for SVG export utility.

Validates basic structure and widget mapping in generated SVG.
"""
import os
import re

import pytest

# Force headless to avoid Tk usage in preview related imports
os.environ["ESP32OS_HEADLESS"] = "1"

from svg_export import scene_to_svg_string
from ui_designer import UIDesigner, WidgetConfig


def _make_basic_scene():
    designer = UIDesigner()
    designer.create_scene("test")
    scene = designer.scenes["test"]
    # Add representative widgets
    scene.widgets.append(WidgetConfig(type="label", x=2, y=3, width=40, height=12, text="Title"))
    scene.widgets.append(WidgetConfig(type="button", x=10, y=20, width=50, height=18, text="OK"))
    scene.widgets.append(WidgetConfig(type="gauge", x=70, y=20, width=60, height=18, value=50, min_value=0, max_value=100))
    scene.widgets.append(WidgetConfig(type="progressbar", x=10, y=50, width=80, height=12, value=30, min_value=0, max_value=100))
    return scene


def test_svg_basic_structure():
    scene = _make_basic_scene()
    svg = scene_to_svg_string(scene)
    assert svg.startswith("<?xml"), "SVG should start with XML header"
    assert "<svg" in svg and "</svg>" in svg, "SVG root element should exist"
    # Count rects (widgets + background)
    rects = len(re.findall(r"<rect ", svg))
    assert rects >= 5, f"Expected at least 5 <rect> elements, found {rects}"


def test_svg_scaled_export():
    scene = _make_basic_scene()
    # Scale by factor 2 via manual width/height doubling for expectation
    svg_scaled = scene_to_svg_string(scene, scale=2.0)
    # Root viewBox should reflect scaled dimensions
    assert f'viewBox="0 0 {scene.width*2} {scene.height*2}"' in svg_scaled, "Scaled viewBox should match scene*scale"
    # Ensure label rect is fully scaled (position and size)
    assert re.search(rf'<rect x="{2*2}" y="{3*2}" width="{40*2}" height="{12*2}"', svg_scaled), "Label widget should be scaled with coordinates"
    # Inner bars should scale positions; check any inner progress bar rectangle exists
    inner_bars = re.findall(r'<rect[^>]*height="4"', svg_scaled)
    assert inner_bars, "Scaled export should include progress/gauge inner bars"


def test_svg_text_present():
    scene = _make_basic_scene()
    svg = scene_to_svg_string(scene)
    assert "Title" in svg and "OK" in svg, "Widget text should be embedded"
    assert re.search(r"<text .*?>OK</text>", svg), "Button text should render as <text>"


def test_svg_progress_gauge_bar():
    scene = _make_basic_scene()
    svg = scene_to_svg_string(scene)
    # Look for inner progress rectangles (height=4 as defined)
    small_bars = re.findall(r"<rect[^>]*height=\"4\"", svg)
    assert len(small_bars) >= 2, "Gauge and progressbar should render inner bar rectangles"


def test_svg_color_mapping():
    scene = _make_basic_scene()
    # Change colors to known palette entries
    scene.widgets[0].color_bg = "red"
    scene.widgets[1].color_bg = "green"
    svg = scene_to_svg_string(scene)
    assert "#d32f2f" in svg, "Mapped red color hex should appear"
    assert "#388e3c" in svg, "Mapped green color hex should appear"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
