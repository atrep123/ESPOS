#!/usr/bin/env python3
"""Tests for icon palette helper logic (headless).

Focus on pure filtering and insertion mechanics without opening Tk windows.
"""
import os

import pytest

# Force headless mode for any preview imports
os.environ["ESP32OS_HEADLESS"] = "1"

from ui_designer import UIDesigner, WidgetType
from ui_icons import filter_icons, get_all_categories, get_icon_by_name


def test_filter_icons_basic():
    icons = filter_icons("home")
    assert len(icons) == 1
    assert icons[0]["name"] == "Home"


def test_filter_icons_category():
    nav = filter_icons("", "navigation")
    assert len(nav) == 12
    names = {i["name"] for i in nav}
    assert "Home" in names and "Search" in names


def test_filter_icons_term_case_insensitive():
    code = filter_icons("CODE")
    assert any(i["name"] == "Code" for i in code)


def test_filter_icons_symbol_match():
    match = filter_icons("mi_folder_24px")
    assert any(i["name"] == "Folder" for i in match)


def test_filter_icons_ascii_match():
    match = filter_icons("⚙")
    assert any(i["name"] == "Settings" for i in match)


def test_categories_sorted_unique():
    cats = get_all_categories()
    assert cats == sorted(cats)
    assert len(cats) == 7


def test_insert_icon_widget():
    designer = UIDesigner()
    designer.create_scene("scene")
    scene = designer.scenes["scene"]
    home = get_icon_by_name("Home")
    assert home is not None
    designer.add_widget(WidgetType.ICON, x=0, y=0, width=16, height=16, icon_char=home["ascii"])
    assert len(scene.widgets) == 1
    w = scene.widgets[0]
    assert w.icon_char == home["ascii"]
    assert w.width == 16 and w.height == 16


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
