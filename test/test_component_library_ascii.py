#!/usr/bin/env python3
"""
Tests for ASCII-Compatible Component Library
"""

import pytest

from ui_components_library_ascii import (
    create_alert_dialog_ascii,
    create_breadcrumb_ascii,
    create_button_group_ascii,
    create_confirm_dialog_ascii,
    create_grid_layout_ascii,
    create_header_footer_layout_ascii,
    create_input_dialog_ascii,
    create_progress_card_ascii,
    create_radio_group_ascii,
    create_sidebar_layout_ascii,
    create_stat_card_ascii,
    create_status_indicator_ascii,
    create_tab_bar_ascii,
    create_toggle_switch_ascii,
    create_vertical_menu_ascii,
)

# ========== DIALOGS ==========

def test_alert_dialog_ascii():
    widgets = create_alert_dialog_ascii("Warning", "Alert!", "Close")
    assert len(widgets) == 4
    assert any(w.type == "button" and w.text == "Close" for w in widgets)
    assert any(w.type == "label" and w.text == "Warning" for w in widgets)
    assert any(w.type == "label" and w.text == "Alert!" for w in widgets)

def test_confirm_dialog_ascii():
    widgets = create_confirm_dialog_ascii("Confirm", "Sure?", "Yes", "No")
    assert len(widgets) == 5
    assert any(w.type == "button" and w.text == "Yes" for w in widgets)
    assert any(w.type == "button" and w.text == "No" for w in widgets)

def test_input_dialog_ascii():
    widgets = create_input_dialog_ascii("Input", "Enter:", "abc")
    assert len(widgets) == 6
    assert any(w.type == "label" and w.text == "abc" for w in widgets)
    assert any(w.type == "button" and w.text == "OK" for w in widgets)

# ========== NAVIGATION ==========

def test_tab_bar_ascii():
    widgets = create_tab_bar_ascii(["A", "B", "C"])
    assert len(widgets) == 3
    assert all(w.type == "button" for w in widgets)
    assert widgets[0].text == "A"

def test_vertical_menu_ascii():
    widgets = create_vertical_menu_ascii(["One", "Two"])
    assert len(widgets) == 3  # 1 box + 2 items
    assert widgets[1].text == "One"
    assert widgets[2].text == "Two"

def test_breadcrumb_ascii():
    widgets = create_breadcrumb_ascii(["Home", "Docs", "API"])
    assert any(w.type == "label" and w.text == "Home" for w in widgets)
    assert any(w.type == "label" and w.text == ">" for w in widgets)
    assert any(w.type == "label" and w.text == "API" for w in widgets)

# ========== DATA DISPLAY ==========

def test_stat_card_ascii():
    widgets = create_stat_card_ascii("Users", "1234", "*")
    assert len(widgets) == 4
    assert any(w.type == "label" and w.text == "*" for w in widgets)
    assert any(w.type == "label" and w.text == "1234" for w in widgets)

def test_progress_card_ascii():
    widgets = create_progress_card_ascii("Loading", 75)
    assert any(w.type == "label" and "%" in w.text for w in widgets)
    assert any(w.type == "box" and w.color_bg == "green" for w in widgets)

def test_status_indicator_ascii():
    widgets = create_status_indicator_ascii("online", "Server")
    assert any(w.type == "label" and w.text == "●" for w in widgets)
    assert any(w.type == "label" and w.text == "Server" for w in widgets)

# ========== CONTROLS ==========

def test_button_group_ascii():
    widgets = create_button_group_ascii(["A", "B"])
    assert len(widgets) == 2
    assert widgets[0].text == "A"
    assert widgets[1].text == "B"

def test_toggle_switch_ascii():
    widgets = create_toggle_switch_ascii("Enable", True)
    assert any(w.type == "box" and w.color_bg == "green" for w in widgets)
    assert any(w.type == "label" and w.text == "●" for w in widgets)

def test_radio_group_ascii():
    widgets = create_radio_group_ascii(["A", "B"], selected=1)
    assert any(w.type == "label" and w.text == "◉" for w in widgets)
    assert any(w.type == "label" and w.text == "A" for w in widgets)
    assert any(w.type == "label" and w.text == "B" for w in widgets)

# ========== LAYOUTS ==========

def test_header_footer_layout_ascii():
    widgets = create_header_footer_layout_ascii("App", "Footer")
    assert any(w.type == "label" and w.text == "App" for w in widgets)
    assert any(w.type == "label" and w.text == "Footer" for w in widgets)
    assert any(w.type == "box" for w in widgets)

def test_sidebar_layout_ascii():
    widgets = create_sidebar_layout_ascii(8)
    assert len(widgets) == 2
    assert widgets[0].width == 8
    assert widgets[1].width == 16

def test_grid_layout_ascii():
    widgets = create_grid_layout_ascii(2, 3)
    assert len(widgets) == 6
    assert all(w.type == "box" for w in widgets)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
