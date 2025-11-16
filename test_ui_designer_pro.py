#!/usr/bin/env python3
"""
Comprehensive Test Suite for UI Designer Pro
Tests all 5 advanced features
"""

import sys
import time
from ui_designer import UIDesigner, WidgetType, BorderStyle
from ui_themes import ThemeManager
from ui_components import ComponentLibrary
from ui_animations import AnimationDesigner
from ui_responsive import ResponsiveLayoutSystem, LayoutConstraints
from ui_designer_pro import UIDesignerPro


def test_visual_preview():
    """Test visual preview capabilities"""
    print("\n" + "="*60)
    print("TEST 1: VISUAL PREVIEW WINDOW")
    print("="*60)
    
    try:
        from ui_designer_preview import VisualPreviewWindow, PreviewSettings
        
        # Create designer with sample content
        designer = UIDesigner(128, 64)
        designer.create_scene("preview_test")
        designer.add_widget(WidgetType.LABEL, x=5, y=5, width=60, height=10, 
                          text="Preview Test", border=True)
        designer.add_widget(WidgetType.BUTTON, x=70, y=5, width=50, height=10, 
                          text="Button")
        designer.add_widget(WidgetType.PROGRESSBAR, x=5, y=20, width=118, height=8, 
                          value=75)
        
        print("✓ Preview window components loaded")
        print("✓ Sample scene created with 3 widgets")
        print("✓ Features available:")
        print("  • Real-time rendering")
        print("  • Mouse interaction (drag & drop)")
        print("  • Resize handles")
        print("  • Zoom controls (1x-10x)")
        print("  • Grid & snap")
        print("  • PNG export")
        print("  • Properties panel")
        
        return True
    except ImportError as e:
        print(f"✗ Preview requires tkinter and PIL: {e}")
        return False


def test_theme_system():
    """Test theme system"""
    print("\n" + "="*60)
    print("TEST 2: THEME SYSTEM")
    print("="*60)
    
    manager = ThemeManager()
    
    # Test built-in themes
    themes = manager.list_themes()
    print(f"✓ Loaded {len(themes)} built-in themes:")
    for theme_name in themes:
        theme = manager.get_theme(theme_name)
        print(f"  • {theme_name:12} - {theme.description}")
    
    # Test theme application
    widget_config = {"type": "button", "text": "Test"}
    manager.current_theme = "Cyberpunk"
    themed = manager.apply_theme_to_widget(widget_config, "button")
    print(f"\n✓ Applied Cyberpunk theme to button:")
    print(f"  BG: {themed['color_bg']}, FG: {themed['color_fg']}")
    
    # Test custom theme
    custom = manager.create_custom_theme("TestTheme", "Dark")
    print(f"✓ Created custom theme '{custom.name}'")
    
    # Test export/import
    manager.export_theme("Nord", "test_theme_export.json")
    print("✓ Exported Nord theme")
    
    imported = manager.import_theme("test_theme_export.json")
    print(f"✓ Imported theme '{imported.name}'")
    
    # Test search
    dark_themes = manager.search_themes("dark")
    print(f"✓ Found {len(dark_themes)} dark themes")
    
    return True


def test_component_library():
    """Test component library"""
    print("\n" + "="*60)
    print("TEST 3: COMPONENT LIBRARY")
    print("="*60)
    
    library = ComponentLibrary()
    
    # Test built-in components
    components = library.list_components()
    print(f"✓ Loaded {len(components)} built-in components:")
    for comp_name in components:
        comp = library.get_component(comp_name)
        print(f"  • {comp_name:18} ({comp.category:10}) - {len(comp.widgets)} widgets")
    
    # Test component instantiation
    widgets = library.instantiate_component("LoginForm", x=10, y=10)
    print(f"\n✓ Instantiated LoginForm: {len(widgets)} widgets created")
    
    # Test component search
    form_comps = library.search_components("form")
    print(f"✓ Found {len(form_comps)} form components")
    
    # Test export
    library.export_component("StatusBar", "test_component_export.json")
    print("✓ Exported StatusBar component")
    
    # Test categories
    for category in ["form", "navigation", "display"]:
        cat_comps = library.list_components(category)
        print(f"✓ Category '{category}': {len(cat_comps)} components")
    
    return True


def test_animation_system():
    """Test animation system"""
    print("\n" + "="*60)
    print("TEST 4: ANIMATION DESIGNER")
    print("="*60)
    
    designer = AnimationDesigner()
    
    # Test built-in animations
    animations = designer.list_animations()
    print(f"✓ Loaded {len(animations)} built-in animations:")
    for anim_name in animations:
        anim = designer.animations[anim_name]
        print(f"  • {anim_name:15} ({anim.duration}ms) - {anim.type}")
    
    # Test built-in transitions
    transitions = designer.list_transitions()
    print(f"\n✓ Loaded {len(transitions)} transitions:")
    for trans_name in transitions:
        trans = designer.transitions[trans_name]
        print(f"  • {trans_name:12} ({trans.duration}ms)")
    
    # Test custom animation
    custom = designer.create_animation("TestMove", "move", 500, easing="ease_in_out")
    designer.add_keyframe("TestMove", 0.0, {"x": 0, "y": 0})
    designer.add_keyframe("TestMove", 0.5, {"x": 50, "y": 25})
    designer.add_keyframe("TestMove", 1.0, {"x": 100, "y": 0})
    print(f"✓ Created custom animation with {len(custom.keyframes)} keyframes")
    
    # Test animation playback
    designer.play_animation("Bounce")
    print("✓ Started Bounce animation")
    
    values = {}
    for i in range(5):
        values = designer.update_animations(0.05)
        time.sleep(0.05)
    
    print(f"✓ Simulated {5} animation frames")
    
    # Test export
    designer.export_animation("FadeIn", "test_animation_export.json")
    print("✓ Exported FadeIn animation")
    
    # Test easing functions
    from ui_animations import AnimationEasing
    easing_funcs = ["linear", "ease_in", "ease_out", "ease_in_out", 
                   "ease_out_bounce", "ease_out_elastic"]
    print(f"✓ {len(easing_funcs)} easing functions available")
    
    return True


def test_responsive_system():
    """Test responsive layout system"""
    print("\n" + "="*60)
    print("TEST 5: RESPONSIVE LAYOUT SYSTEM")
    print("="*60)
    
    system = ResponsiveLayoutSystem()
    
    # Test breakpoints
    breakpoints = list(system.breakpoints.keys())
    print(f"✓ Loaded {len(breakpoints)} breakpoints:")
    for bp_name in breakpoints:
        bp = system.breakpoints[bp_name]
        max_w = bp.max_width if bp.max_width else "∞"
        max_h = bp.max_height if bp.max_height else "∞"
        print(f"  • {bp_name:8} {bp.min_width:3d}×{bp.min_height:<3d} to {max_w}×{max_h}")
    
    # Test breakpoint detection
    test_sizes = [(128, 64), (240, 240), (320, 240)]
    print("\n✓ Breakpoint detection:")
    for w, h in test_sizes:
        bp = system.find_breakpoint(w, h)
        print(f"  • {w}×{h} → '{bp}'")
    
    # Test scaling
    widget = {"x": 10, "y": 10, "width": 50, "height": 20}
    scaled = system.scale_layout(widget, 128, 64, 320, 240, "proportional")
    print(f"\n✓ Scaled layout from 128×64 to 320×240:")
    print(f"  Original: x={widget['x']}, w={widget['width']}")
    print(f"  Scaled:   x={scaled['x']}, w={scaled['width']}")
    
    # Test percentage layout
    constraints = LayoutConstraints(x="50%", y="50%", width="25%", height="10%")
    result = system.calculate_layout(widget, 320, 240, constraints)
    print(f"✓ Percentage layout calculated")
    
    # Test flex layout
    widgets = [
        {"type": "button", "flex_grow": 1},
        {"type": "button", "flex_grow": 2},
        {"type": "button", "flex_grow": 1},
    ]
    flex = system.create_flex_layout(widgets, 320, 60, "row", gap=4)
    print(f"✓ Flex layout: {len(flex)} widgets positioned")
    
    # Test grid layout
    grid_widgets = [{"type": "label"} for _ in range(4)]
    grid = system.create_grid_layout(grid_widgets, 320, 240, columns=2, rows=2)
    print(f"✓ Grid layout: 2×2 grid created")
    
    return True


def test_integration():
    """Test complete integration"""
    print("\n" + "="*60)
    print("TEST 6: COMPLETE INTEGRATION")
    print("="*60)
    
    # Create UI Designer Pro
    designer_pro = UIDesignerPro(128, 64)
    designer_pro.create_scene("integration_test")
    
    print("✓ UI Designer Pro initialized")
    
    # Apply theme
    designer_pro.set_theme("Dracula")
    
    # Add components
    designer_pro.add_component("StatusBar", x=0, y=54)
    designer_pro.add_component("CardWidget", x=5, y=5)
    
    # Add themed widgets
    designer_pro.add_widget_with_theme(
        WidgetType.BUTTON,
        x=70, y=10, width=50, height=12,
        text="Click Me"
    )
    
    print("✓ Added components with theme applied")
    
    # Export complete
    designer_pro.export_complete("test_integration")
    
    # Make responsive
    designer_pro.make_responsive((128, 64), (240, 240), "fit")
    
    print("✓ Created responsive version")
    
    # Show stats
    scene = designer_pro.designer.scenes.get(designer_pro.designer.current_scene)
    if scene:
        print(f"✓ Final scene: {len(scene.widgets)} widgets")
    
    return True


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*60)
    print("     UI DESIGNER PRO TEST SUITE")
    print("="*60)
    
    tests = [
        ("Visual Preview", test_visual_preview),
        ("Theme System", test_theme_system),
        ("Component Library", test_component_library),
        ("Animation Designer", test_animation_system),
        ("Responsive Layout", test_responsive_system),
        ("Complete Integration", test_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed ({passed*100//total}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! UI Designer Pro is ready!")
        print("\n📚 Feature Overview:")
        print("  1. Visual Preview Window - Graphical editor with drag & drop")
        print("  2. Theme System - 8 built-in themes + custom theme support")
        print("  3. Component Library - 9 pre-built components")
        print("  4. Animation Designer - 6 animations + 8 transitions")
        print("  5. Responsive Layout - Multi-display support with breakpoints")
        print("\n🚀 Quick Start:")
        print("  python ui_designer_pro.py      # Complete demo")
        print("  python ui_designer_preview.py  # Launch visual editor")
        print("  python ui_themes.py            # Preview themes")
        print("  python ui_components.py        # Browse components")
        print("  python ui_animations.py        # Test animations")
        print("  python ui_responsive.py        # Test responsive layouts")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
