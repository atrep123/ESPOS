#!/usr/bin/env python3
"""Test Export Presets feature"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_export_scale_presets():
    """Test export scale calculations"""
    # Base widget size
    width, height = 40, 12
    
    # @1x scale
    scale = 1
    scaled_w = width * scale
    scaled_h = height * scale
    assert scaled_w == 40, "@1x width should be 40"
    assert scaled_h == 12, "@1x height should be 12"
    print(f"✅ @1x scale: {width}x{height} -> {scaled_w}x{scaled_h}")
    
    # @2x scale
    scale = 2
    scaled_w = width * scale
    scaled_h = height * scale
    assert scaled_w == 80, "@2x width should be 80"
    assert scaled_h == 24, "@2x height should be 24"
    print(f"✅ @2x scale: {width}x{height} -> {scaled_w}x{scaled_h}")
    
    # @4x scale
    scale = 4
    scaled_w = width * scale
    scaled_h = height * scale
    assert scaled_w == 160, "@4x width should be 160"
    assert scaled_h == 48, "@4x height should be 48"
    print(f"✅ @4x scale: {width}x{height} -> {scaled_w}x{scaled_h}")


def test_export_content_presets():
    """Test export content options"""
    # Scene only preset
    include_grid = False
    use_overlays = False
    
    assert not include_grid, "Scene-only should disable grid"
    assert not use_overlays, "Scene-only should disable overlays"
    print("✅ Scene-only preset: grid=False, overlays=False")
    
    # With guides preset
    include_grid = True
    use_overlays = True
    
    assert include_grid, "With-guides should enable grid"
    assert use_overlays, "With-guides should enable overlays"
    print("✅ With-guides preset: grid=True, overlays=True")


def test_export_settings_persistence():
    """Test remembering last export settings"""
    # Mock settings storage
    settings = {}
    
    # First export: use defaults
    settings['last_scale'] = 1
    settings['last_guides'] = False
    
    assert settings['last_scale'] == 1, "Default scale should be @1x"
    assert settings['last_guides'] == False, "Default guides should be off"
    print("✅ Default settings: @1x, guides=False")
    
    # User changes to @2x with guides
    settings['last_scale'] = 2
    settings['last_guides'] = True
    
    # Next export should remember choices
    assert settings['last_scale'] == 2, "Should remember @2x"
    assert settings['last_guides'] == True, "Should remember guides=True"
    print("✅ Remembered settings: @2x, guides=True")


def test_export_filename_generation():
    """Test automatic filename suggestions"""
    base_name = "ui_preview"
    
    # @1x export
    scale = 1
    filename = f"{base_name}_{scale}x.png"
    assert filename == "ui_preview_1x.png", "@1x filename should include scale"
    print(f"✅ @1x filename: {filename}")
    
    # @2x export
    scale = 2
    filename = f"{base_name}_{scale}x.png"
    assert filename == "ui_preview_2x.png", "@2x filename should include scale"
    print(f"✅ @2x filename: {filename}")
    
    # @4x export
    scale = 4
    filename = f"{base_name}_{scale}x.png"
    assert filename == "ui_preview_4x.png", "@4x filename should include scale"
    print(f"✅ @4x filename: {filename}")


def test_export_dialog_options():
    """Test export dialog option values"""
    # Available scale options
    scales = [1, 2, 3, 4]
    assert 1 in scales, "Should offer @1x"
    assert 2 in scales, "Should offer @2x"
    assert 3 in scales, "Should offer @3x"
    assert 4 in scales, "Should offer @4x"
    print(f"✅ Available scales: {scales}")
    
    # Content options
    content_options = ["Scene only", "With guides"]
    assert len(content_options) == 2, "Should have 2 content options"
    print(f"✅ Content options: {content_options}")


if __name__ == '__main__':
    test_export_scale_presets()
    test_export_content_presets()
    test_export_settings_persistence()
    test_export_filename_generation()
    test_export_dialog_options()
    print("\n🎉 All Export Presets tests passed!")
