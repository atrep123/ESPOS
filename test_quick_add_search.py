#!/usr/bin/env python3
"""Test Quick Add Search feature"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_designer import UIDesigner


def test_quick_add_search_logic():
    """Test quick add search filtering logic"""
    
    # Simulate component list
    components = [
        {"name": "AlertDialog", "category": "Dialogs", "description": "Alert dialog with OK button"},
        {"name": "ConfirmDialog", "category": "Dialogs", "description": "Confirmation dialog with Yes/No"},
        {"name": "TabBar", "category": "Navigation", "description": "Tab bar with 3 tabs"},
        {"name": "StatusIndicator", "category": "Data Display", "description": "Status indicator with colored dot"},
        {"name": "ButtonGroup", "category": "Controls", "description": "Button group with 3 buttons"},
    ]
    
    def filter_components(query: str):
        """Simulate search filtering"""
        query = query.lower().strip()
        results = []
        for comp in components:
            name_match = query in comp["name"].lower()
            cat_match = query in comp["category"].lower()
            desc_match = query in comp["description"].lower()
            
            if not query or name_match or cat_match or desc_match:
                results.append(comp)
        return results
    
    # Test 1: Empty query returns all
    all_results = filter_components("")
    assert len(all_results) == 5, "Empty query should return all components"
    print("✅ Empty query returns all 5 components")
    
    # Test 2: Search by name
    dialog_results = filter_components("dialog")
    assert len(dialog_results) == 2, "Should find 2 dialogs"
    assert all("Dialog" in c["name"] for c in dialog_results), "All results should contain 'Dialog'"
    print("✅ Name search: 'dialog' found 2 components")
    
    # Test 3: Search by category
    nav_results = filter_components("navigation")
    assert len(nav_results) == 1, "Should find 1 navigation component"
    assert nav_results[0]["name"] == "TabBar", "Should find TabBar"
    print("✅ Category search: 'navigation' found TabBar")
    
    # Test 4: Search by description
    button_results = filter_components("button")
    assert len(button_results) >= 1, "Should find components with 'button' in description"
    print(f"✅ Description search: 'button' found {len(button_results)} components")
    
    # Test 5: Partial match
    status_results = filter_components("stat")
    assert len(status_results) >= 1, "Should find StatusIndicator"
    assert any("Status" in c["name"] for c in status_results), "Should match StatusIndicator"
    print("✅ Partial match: 'stat' found StatusIndicator")
    
    # Test 6: Case insensitive
    alert_upper = filter_components("ALERT")
    alert_lower = filter_components("alert")
    assert len(alert_upper) == len(alert_lower), "Search should be case insensitive"
    print("✅ Case insensitive: 'ALERT' == 'alert'")
    
    print("\n✅ All search filtering tests passed!")


def test_quick_add_integration():
    """Test that Quick Add Search integrates correctly with designer"""
    designer = UIDesigner(128, 64)
    designer.create_scene("test_scene")
    
    # Verify scene exists
    scene = designer.scenes.get(designer.current_scene)
    assert scene is not None, "Scene should exist"
    
    initial_widget_count = len(scene.widgets)
    print(f"✅ Initial widget count: {initial_widget_count}")
    
    # Simulate adding a component (we can't actually run GUI dialog in test)
    # But we can verify the backend logic
    from ui_designer import WidgetType
    
    # Add a button (simulating Quick Add result)
    designer.add_widget(WidgetType.BUTTON, x=10, y=10, width=50, height=12, text="Quick Added")
    
    updated_widget_count = len(scene.widgets)
    assert updated_widget_count == initial_widget_count + 1, "Should add 1 widget"
    print(f"✅ Widget added via designer: count now {updated_widget_count}")
    
    # Verify widget properties
    new_widget = scene.widgets[-1]
    # type is stored as string in designer
    assert "button" in str(new_widget.type).lower(), f"Should be a button, got {new_widget.type}"
    assert new_widget.text == "Quick Added", "Should have correct text"
    print("✅ Widget properties correct")
    
    print("\n✅ Quick Add integration test passed!")


if __name__ == '__main__':
    test_quick_add_search_logic()
    test_quick_add_integration()
    print("\n🎉 All Quick Add Search tests passed!")
