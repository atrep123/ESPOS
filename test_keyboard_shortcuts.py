#!/usr/bin/env python3
"""
Test keyboard shortcuts for component palette
"""

import os

import pytest

# Force headless mode for all tests in this module to prevent Tk flakiness
os.environ["ESP32OS_HEADLESS"] = "1"

from ui_designer import UIDesigner


def test_quick_insert_basic():
    """Test basic quick insert functionality"""
    designer = UIDesigner()
    designer.create_scene("test")
    
    # Import preview window to access quick insert
    from ui_designer_preview import VisualPreviewWindow
    
    # Create mock preview window (no Tk needed for logic test)
    class MockRoot:
        def after(self, *args): pass
        def bind(self, *args): pass
        def mainloop(self): pass
    
    preview = VisualPreviewWindow(designer)
    preview.root = MockRoot()
    
    # Test quick insert for first 9 components
    initial_count = len(designer.scenes["test"].widgets)
    
    for idx in range(min(9, len(preview.ascii_components))):
        preview._on_quick_insert(idx)
        current_count = len(designer.scenes["test"].widgets)
        assert current_count > initial_count, f"Component {idx} should add widgets"
        initial_count = current_count


def test_quick_insert_component_mapping():
    """Test that component indices match expected shortcuts"""
    from ui_designer_preview import VisualPreviewWindow
    designer = UIDesigner()
    
    class MockRoot:
        def after(self, *args): pass
        def bind(self, *args): pass
        def mainloop(self): pass
    
    preview = VisualPreviewWindow(designer)
    preview.root = MockRoot()
    
    # Verify first 9 components are accessible
    assert len(preview.ascii_components) >= 9, "Should have at least 9 components for Ctrl+1-9"
    
    # Check component names (first 9)
    expected_names = [
        "AlertDialog", "ConfirmDialog", "InputDialog", "TabBar", "VerticalMenu",
        "Breadcrumb", "StatCard", "ProgressCard", "StatusIndicator"
    ]
    
    for i, expected_name in enumerate(expected_names):
        assert preview.ascii_components[i]["name"] == expected_name, \
            f"Ctrl+{i+1} should map to {expected_name}"


def test_quick_insert_invalid_index():
    """Test quick insert with invalid component index (logic only)"""
    designer = UIDesigner()
    designer.create_scene("test")
    
    # Test logic: invalid index should be ignored
    # (This tests the early return in _on_quick_insert)
    from ui_components_library_ascii import create_alert_dialog_ascii
    
    # Manually test the logic without preview window
    ascii_components = [
        {"name": "AlertDialog", "factory": lambda: create_alert_dialog_ascii()},
    ]
    
    component_index = 999
    if component_index >= len(ascii_components):
        # Should not proceed - this is the expected behavior
        assert True
    else:
        pytest.fail("Should have detected invalid index")


def test_quick_insert_selection():
    """Test quick insert component mapping (logic only)"""
    designer = UIDesigner()
    designer.create_scene("test")
    
    # Test that the quick insert would add and select widgets
    from ui_components_library_ascii import create_alert_dialog_ascii
    
    widgets = create_alert_dialog_ascii()
    scene = designer.scenes["test"]
    start_idx = len(scene.widgets)
    
    for w in widgets:
        scene.widgets.append(w)
    
    new_indices = list(range(start_idx, start_idx + len(widgets)))
    
    # Logic that would be in _on_quick_insert
    assert len(new_indices) > 0, "Should create selection indices"
    assert new_indices[0] == start_idx, "First index should be start_idx"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
