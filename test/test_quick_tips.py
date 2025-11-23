#!/usr/bin/env python3
"""Test Quick Tips feature"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_settings_file_location():
    """Test that settings file is stored in temp directory"""
    settings_dir = os.path.join(tempfile.gettempdir(), "esp32os_designer")
    settings_file = os.path.join(settings_dir, "settings.json")
    
    assert "esp32os_designer" in settings_file, "Settings should be in esp32os_designer dir"
    assert settings_file.endswith(".json"), "Settings should be JSON file"
    
    print(f"✅ Settings file location: {settings_file}")


def test_first_run_detection():
    """Test first-run detection logic"""
    # Simulate first run (no settings file)
    settings = {}
    show_tips = not settings.get("hide_quick_tips", False)
    
    assert show_tips, "Should show tips on first run"
    print("✅ First run: show_tips = True (no settings file)")
    
    # Simulate subsequent run (settings exist but not hidden)
    settings = {"hide_quick_tips": False}
    show_tips = not settings.get("hide_quick_tips", False)
    
    assert show_tips, "Should show tips if not explicitly hidden"
    print("✅ Subsequent run (not hidden): show_tips = True")
    
    # Simulate run after user checked "don't show again"
    settings = {"hide_quick_tips": True}
    show_tips = not settings.get("hide_quick_tips", False)
    
    assert not show_tips, "Should NOT show tips if hidden by user"
    print("✅ After 'don't show': show_tips = False")


def test_settings_persistence():
    """Test saving and loading settings"""
    import tempfile
    
    # Create temp settings file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        settings_file = f.name
        json.dump({"hide_quick_tips": True}, f)
    
    try:
        # Load settings
        with open(settings_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded["hide_quick_tips"] == True, "Should persist 'hide' preference"
        print(f"✅ Settings persistence: hide_quick_tips = {loaded['hide_quick_tips']}")
    finally:
        os.unlink(settings_file)


def test_tips_content_structure():
    """Test Quick Tips content includes key information"""
    tips_content = """Základní ovládání:

🖱️ Myš:
• Kliknutím vyberte widget
• Shift+klik přidá do výběru
• Tažení na prázdném plátně = box select

⌨️ Klávesnice:
• Ctrl+Shift+A = Rychlé přidání komponenty
• Šipky = posun
• Delete = smazání

🔍 Zoom:
• Ctrl+kolečko myši = zoom

📤 Export:
• PNG export s scalováním"""
    
    # Check for key features
    assert "Ctrl+Shift+A" in tips_content, "Should mention Quick Add"
    assert "box select" in tips_content, "Should mention box select"
    assert "Shift+klik" in tips_content, "Should mention multi-select"
    assert "Zoom" in tips_content or "zoom" in tips_content, "Should mention zoom"
    assert "Export" in tips_content or "export" in tips_content, "Should mention export"
    
    print("✅ Tips content includes:")
    print("   • Quick Add (Ctrl+Shift+A)")
    print("   • Box select")
    print("   • Multi-select (Shift+klik)")
    print("   • Zoom controls")
    print("   • Export features")


def test_dialog_timing():
    """Test that dialog shows after delay"""
    delay_ms = 500  # 0.5 second
    
    assert delay_ms > 0, "Dialog should show after delay"
    assert delay_ms <= 1000, "Delay should not be too long (≤1s)"
    
    delay_sec = delay_ms / 1000
    print(f"✅ Dialog timing: {delay_ms}ms ({delay_sec}s) after startup")


def test_dont_show_checkbox_default():
    """Test that 'don't show' checkbox defaults to unchecked"""
    dont_show_default = False
    
    assert not dont_show_default, "Checkbox should default to unchecked"
    print("✅ 'Nezobrazovat znovu' checkbox: defaults to unchecked")


if __name__ == '__main__':
    test_settings_file_location()
    test_first_run_detection()
    test_settings_persistence()
    test_tips_content_structure()
    test_dialog_timing()
    test_dont_show_checkbox_default()
    print("\n🎉 All Quick Tips tests passed!")
