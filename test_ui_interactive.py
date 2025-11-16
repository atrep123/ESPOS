#!/usr/bin/env python3
"""Interactive UI Designer demo - creates a dashboard"""

import sys
sys.path.insert(0, '.')

from ui_designer import UIDesigner

def create_dashboard_demo():
    """Create a sample dashboard with various widgets"""
    
    print("=" * 70)
    print("🎨 UI DESIGNER - INTERACTIVE DASHBOARD DEMO")
    print("=" * 70)
    
    designer = UIDesigner()
    designer.create_scene("dashboard")
    
    # Enable grid for precise placement
    designer.grid_enabled = True
    print("\n✓ Grid enabled (4px)")
    
    # 1. Add title from template
    print("\n1️⃣  Adding title label...")
    designer.add_widget_from_template('title_label', 'title', x=0, y=0, text="ESP32 Dashboard")
    
    # 2. Add status panel
    print("2️⃣  Adding status panel...")
    designer.add_widget_from_template('info_panel', 'status', x=8, y=12, text="Status: ONLINE")
    
    # 3. Add control buttons
    print("3️⃣  Adding control buttons...")
    designer.add_widget_from_template('button_primary', 'btn_start', x=8, y=24, text="START")
    designer.clone_widget(2, offset_x=44, offset_y=0)  # Clone button to the right
    
    # 4. Add progress bar
    print("4️⃣  Adding progress bar...")
    designer.add_widget_from_template('progress_bar', 'progress1', x=8, y=40)
    
    # 5. Add gauges
    print("5️⃣  Adding temperature gauge...")
    designer.add_widget_from_template('gauge_half', 'temp_gauge', x=80, y=12)
    
    print("6️⃣  Adding CPU usage gauge...")
    designer.clone_widget(5, offset_x=0, offset_y=28)
    
    # Display current state
    print("\n" + "=" * 70)
    print("📊 CURRENT DESIGN:")
    print("=" * 70)
    scene = designer.scenes[designer.current_scene]
    print(f"Widgets: {len(scene.widgets)}")
    print(f"Undo levels: {len(designer.undo_stack)}")
    
    # Show ASCII preview
    print("\n" + "=" * 70)
    print("🖼️  ASCII PREVIEW:")
    print("=" * 70)
    print(designer.preview_ascii(show_grid=False))
    
    # Save outputs
    print("\n" + "=" * 70)
    print("💾 EXPORTING:")
    print("=" * 70)
    
    designer.save_to_json('dashboard_demo.json')
    print("✓ JSON saved: dashboard_demo.json")
    
    designer.export_code('dashboard_demo.py')
    print("✓ Python code: dashboard_demo.py")
    
    designer.export_to_html('dashboard_demo.html')
    print("✓ HTML preview: dashboard_demo.html")
    
    # Widget summary
    print("\n" + "=" * 70)
    print("📋 WIDGET SUMMARY:")
    print("=" * 70)
    for i, widget in enumerate(scene.widgets):
        print(f"  [{i}] {widget.type:12s} @ ({widget.x:3d}, {widget.y:3d}) "
              f"{widget.width}x{widget.height} '{widget.text[:20]}'")
    
    # Test undo/redo
    print("\n" + "=" * 70)
    print("↩️  TESTING UNDO/REDO:")
    print("=" * 70)
    
    print(f"Before undo: {len(scene.widgets)} widgets")
    designer.undo()
    scene = designer.scenes[designer.current_scene]
    print(f"After undo:  {len(scene.widgets)} widgets")
    
    designer.undo()
    scene = designer.scenes[designer.current_scene]
    print(f"After undo:  {len(scene.widgets)} widgets")
    
    designer.redo()
    scene = designer.scenes[designer.current_scene]
    print(f"After redo:  {len(scene.widgets)} widgets")
    
    designer.redo()
    scene = designer.scenes[designer.current_scene]
    print(f"After redo:  {len(scene.widgets)} widgets")
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETED!")
    print("=" * 70)
    print("\nNext steps:")
    print("  • Open dashboard_demo.html in browser for preview")
    print("  • Use python ui_designer.py for interactive CLI")
    print("  • Import dashboard_demo.py into simulator")

if __name__ == '__main__':
    create_dashboard_demo()
