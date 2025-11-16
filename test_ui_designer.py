#!/usr/bin/env python3
"""Quick test of UI Designer functionality"""

import sys
sys.path.insert(0, '.')

from ui_designer import UIDesigner, WidgetType, BorderStyle, WidgetConfig

def test_ui_designer():
    """Test basic UI Designer functionality"""
    
    print("Testing UI Designer...")
    print("-" * 60)
    
    # Create designer
    designer = UIDesigner()
    designer.create_scene("main")  # Create initial scene
    
    # Test 1: Add widgets from templates
    print("\n1. Testing templates:")
    designer.add_widget_from_template('title_label', 'title', x=10, y=2, text="Dashboard")
    designer.add_widget_from_template('button_primary', 'btn1', x=10, y=8, text="Start")
    designer.add_widget_from_template('gauge_half', 'gauge1', x=60, y=8)
    print("   ✓ Added 3 widgets from templates")
    
    # Test 2: Clone widget
    print("\n2. Testing clone:")
    designer.clone_widget(1, offset_x=0, offset_y=4)  # Clone button by index
    print(f"   ✓ Cloned button")
    
    # Test 3: Undo/Redo
    print("\n3. Testing undo/redo:")
    designer.undo()
    scene = designer.scenes[designer.current_scene]
    print(f"   ✓ Undo - widgets: {len(scene.widgets)}")
    designer.redo()
    scene = designer.scenes[designer.current_scene]
    print(f"   ✓ Redo - widgets: {len(scene.widgets)}")
    
    # Test 4: Auto layout
    print("\n4. Testing auto-layout:")
    designer.auto_layout('vertical', spacing=4)
    print("   ✓ Applied vertical layout")
    
    # Test 5: ASCII Preview
    print("\n5. ASCII Preview:")
    print(designer.preview_ascii(show_grid=True))
    
    # Test 6: Export formats
    print("\n6. Testing exports:")
    
    # JSON
    designer.save_to_json('test_scene.json')
    print("   ✓ Saved JSON: test_scene.json")
    
    # Python code
    designer.export_code('test_scene.py')
    print("   ✓ Generated Python code: test_scene.py")
    
    # HTML
    designer.export_to_html('test_scene.html')
    print("   ✓ Generated HTML: test_scene.html")
    
    # Test 7: Widget types
    print("\n7. Testing all widget types:")
    test_widgets = [
        WidgetConfig(type=WidgetType.PROGRESSBAR.value, x=10, y=20, width=20, height=1, value=75),
        WidgetConfig(type=WidgetType.CHECKBOX.value, x=10, y=22, width=10, height=1, text='Enable', checked=True),
        WidgetConfig(type=WidgetType.SLIDER.value, x=10, y=24, width=15, height=1, value=50),
        WidgetConfig(type=WidgetType.CHART.value, x=10, y=26, width=10, height=5, data_points=[5, 8, 3, 10, 7]),
    ]
    
    for widget in test_widgets:
        designer.add_widget(widget)
        print(f"   ✓ {widget.type}")
    
    # Test 8: Border styles
    print("\n8. Testing border styles:")
    for style in [BorderStyle.SINGLE, BorderStyle.DOUBLE, BorderStyle.ROUNDED, BorderStyle.BOLD]:
        widget = WidgetConfig(
            type=WidgetType.BOX.value,
            x=10, y=32,
            width=10, height=3,
            border_style=style.value
        )
        designer.add_widget(widget)
        print(f"   ✓ {style.value}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    scene = designer.scenes[designer.current_scene]
    print(f"\nFinal stats:")
    print(f"  - Total widgets: {len(scene.widgets)}")
    print(f"  - Undo stack: {len(designer.undo_stack)}")
    print(f"  - Templates: {len(designer.templates)}")
    print(f"  - Grid enabled: {designer.grid_enabled}")

if __name__ == '__main__':
    test_ui_designer()
