"""Tests for enhanced SVG export with gradients, shadows, and patterns."""
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from svg_export_enhanced import EnhancedSVGExporter, ExportOptions, ExportPreset
from ui_designer import UIDesigner, WidgetType


@pytest.fixture
def designer():
    """Create basic UI designer for testing"""
    d = UIDesigner(width=320, height=240)
    d.create_scene("test_scene")
    return d


@pytest.fixture
def scene_with_widgets(designer):
    """Create scene with various widgets"""
    designer.add_widget(WidgetType.BUTTON, x=10, y=10, width=80, height=30, text="Click Me")
    designer.add_widget(WidgetType.PANEL, x=100, y=10, width=100, height=80, border=True)
    designer.add_widget(WidgetType.GAUGE, x=10, y=50, width=80, height=30, value=75)
    designer.add_widget(WidgetType.LABEL, x=10, y=90, width=200, height=20, text="Test Label")
    return designer.scenes[designer.current_scene]


def test_exporter_creation():
    """Test exporter can be created with default options"""
    exporter = EnhancedSVGExporter()
    assert exporter.options.preset == ExportPreset.WEB_OPTIMIZED
    assert exporter.options.include_gradients is True


def test_preset_web_optimized():
    """Test web optimized preset configuration"""
    options = ExportOptions.from_preset(ExportPreset.WEB_OPTIMIZED)
    assert options.include_gradients is True
    assert options.include_shadows is False
    assert options.include_patterns is False
    assert options.embed_fonts is False
    assert options.optimize_size is True


def test_preset_print_quality():
    """Test print quality preset configuration"""
    options = ExportOptions.from_preset(ExportPreset.PRINT_QUALITY)
    assert options.include_gradients is True
    assert options.include_shadows is True
    assert options.include_patterns is True
    assert options.embed_fonts is False


def test_preset_high_fidelity():
    """Test high fidelity preset configuration"""
    options = ExportOptions.from_preset(ExportPreset.HIGH_FIDELITY)
    assert options.include_gradients is True
    assert options.include_shadows is True
    assert options.include_patterns is True
    assert options.embed_fonts is True


def test_color_conversion():
    """Test color name to hex conversion"""
    exporter = EnhancedSVGExporter()
    assert exporter._color("red") == "#d32f2f"
    assert exporter._color("white") == "#ffffff"
    assert exporter._color("black") == "#000000"
    assert exporter._color("#abc123") == "#abc123"
    assert exporter._color("") == "#333333"  # default


def test_lighten_color():
    """Test color lightening function"""
    exporter = EnhancedSVGExporter()
    lighter = exporter._lighten_color("#000000", 0.5)
    assert lighter == "#7f7f7f"  # 50% lighter black
    
    lighter = exporter._lighten_color("#ff0000", 0.5)
    assert lighter == "#ff7f7f"  # 50% lighter red


def test_linear_gradient_creation():
    """Test linear gradient definition creation"""
    exporter = EnhancedSVGExporter()
    gid, gdef = exporter._create_linear_gradient("#ffffff", "#000000", angle=90)
    
    assert "linearGradient" in gdef
    assert gid.startswith("grad_linear_")
    assert "#ffffff" in gdef
    assert "#000000" in gdef
    assert 'stop offset="0%"' in gdef
    assert 'stop offset="100%"' in gdef


def test_radial_gradient_creation():
    """Test radial gradient definition creation"""
    exporter = EnhancedSVGExporter()
    gid, gdef = exporter._create_radial_gradient("#ffffff", "#000000")
    
    assert "radialGradient" in gdef
    assert gid.startswith("grad_radial_")
    assert "#ffffff" in gdef
    assert "#000000" in gdef


def test_drop_shadow_creation():
    """Test drop shadow filter definition"""
    exporter = EnhancedSVGExporter()
    sid, sdef = exporter._create_drop_shadow(blur=2.0, offset_x=2.0, offset_y=2.0)
    
    assert "<filter" in sdef
    assert sid.startswith("shadow_drop_")
    assert "feGaussianBlur" in sdef
    assert "feOffset" in sdef
    assert 'dx="2.0"' in sdef
    assert 'dy="2.0"' in sdef


def test_inner_shadow_creation():
    """Test inner shadow filter definition"""
    exporter = EnhancedSVGExporter()
    sid, sdef = exporter._create_inner_shadow(blur=2.0, offset_x=1.0, offset_y=1.0)
    
    assert "<filter" in sdef
    assert sid.startswith("shadow_inner_")
    assert "feGaussianBlur" in sdef
    assert "feComposite" in sdef


def test_pattern_creation_dots():
    """Test dot pattern creation"""
    exporter = EnhancedSVGExporter()
    pid, pdef = exporter._create_pattern("dots", "#ffffff", spacing=10)
    
    assert "<pattern" in pdef
    assert pid.startswith("pattern_")
    assert "<circle" in pdef
    assert "#ffffff" in pdef


def test_pattern_creation_lines():
    """Test line pattern creation"""
    exporter = EnhancedSVGExporter()
    pid, pdef = exporter._create_pattern("lines", "#000000", spacing=8)
    
    assert "<pattern" in pdef
    assert "<line" in pdef
    assert "#000000" in pdef


def test_pattern_creation_grid():
    """Test grid pattern creation"""
    exporter = EnhancedSVGExporter()
    pid, pdef = exporter._create_pattern("grid", "#888888", spacing=12)
    
    assert "<pattern" in pdef
    assert pdef.count("<line") == 2  # 2 lines for grid
    assert "#888888" in pdef


def test_basic_export_web_preset(scene_with_widgets):
    """Test basic SVG export with web preset"""
    options = ExportOptions.from_preset(ExportPreset.WEB_OPTIMIZED)
    exporter = EnhancedSVGExporter(options)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        result = exporter.export_scene(scene_with_widgets, tmp_path)
        assert result == tmp_path
        assert os.path.exists(tmp_path)
        
        # Parse and validate SVG
        tree = ET.parse(tmp_path)
        root = tree.getroot()
        
        # Check basic structure
        assert root.tag.endswith('svg')
        assert 'width' in root.attrib
        assert 'height' in root.attrib
        
        # Check for defs section (gradients should be present)
        defs = root.find('.//{http://www.w3.org/2000/svg}defs')
        if options.include_gradients:
            assert defs is not None
            gradients = defs.findall('.//{http://www.w3.org/2000/svg}linearGradient')
            assert len(gradients) > 0
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_export_with_gradients(scene_with_widgets):
    """Test export includes gradients when enabled"""
    options = ExportOptions(include_gradients=True)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene_with_widgets)
    
    assert "linearGradient" in svg_string
    assert "grad_linear_" in svg_string


def test_export_with_shadows(scene_with_widgets):
    """Test export includes shadows when enabled"""
    options = ExportOptions(include_shadows=True, include_gradients=False)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene_with_widgets)
    
    assert "filter" in svg_string
    assert "feGaussianBlur" in svg_string


def test_export_with_patterns(scene_with_widgets):
    """Test export includes patterns when enabled"""
    options = ExportOptions(include_patterns=True, include_gradients=False)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene_with_widgets)
    
    assert "<pattern" in svg_string


def test_export_with_metadata(scene_with_widgets):
    """Test export includes metadata when enabled"""
    options = ExportOptions(include_metadata=True)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene_with_widgets)
    
    assert "<metadata>" in svg_string
    assert "ESP32 UI Design" in svg_string


def test_export_without_metadata(scene_with_widgets):
    """Test export excludes metadata when disabled"""
    options = ExportOptions(include_metadata=False)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene_with_widgets)
    
    assert "<metadata>" not in svg_string


def test_export_scaling(scene_with_widgets):
    """Test export respects scale factor"""
    options = ExportOptions(scale=2.0)
    exporter = EnhancedSVGExporter(options)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        exporter.export_scene(scene_with_widgets, tmp_path)
        
        tree = ET.parse(tmp_path)
        root = tree.getroot()
        
        # Width should be doubled
        assert root.attrib['width'] == str(int(scene_with_widgets.width * 2.0))
        assert root.attrib['height'] == str(int(scene_with_widgets.height * 2.0))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_widget_with_progress_bar(designer):
    """Test progress bar widget exports with gradient fill"""
    designer.add_widget(WidgetType.PROGRESSBAR, x=10, y=10, width=100, height=20, value=50)
    scene = designer.scenes[designer.current_scene]
    
    options = ExportOptions(include_gradients=True)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene)
    
    # Should have progress bar representation
    assert "<rect" in svg_string
    # May have gradient for the bar fill
    if options.include_gradients:
        assert "linearGradient" in svg_string


def test_unique_id_generation():
    """Test that unique IDs are generated for SVG elements"""
    exporter = EnhancedSVGExporter()
    
    id1 = exporter._get_id("test")
    id2 = exporter._get_id("test")
    id3 = exporter._get_id("other")
    
    assert id1 != id2
    assert id1 != id3
    assert id2 != id3
    assert id1.startswith("test_")
    assert id3.startswith("other_")


def test_invisible_widget_skipped(designer):
    """Test that invisible widgets are not exported"""
    designer.add_widget(WidgetType.LABEL, x=10, y=10, width=100, height=20, text="Hidden")
    scene = designer.scenes[designer.current_scene]
    widget = scene.widgets[-1]
    widget.visible = False
    
    exporter = EnhancedSVGExporter()
    
    svg_string = exporter.export_scene_to_string(scene)
    
    # Should not contain the hidden widget's text
    assert "Hidden" not in svg_string


def test_all_presets_export(scene_with_widgets):
    """Test that all presets can successfully export"""
    for preset in [ExportPreset.WEB_OPTIMIZED, ExportPreset.PRINT_QUALITY, ExportPreset.HIGH_FIDELITY]:
        options = ExportOptions.from_preset(preset)
        exporter = EnhancedSVGExporter(options)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = exporter.export_scene(scene_with_widgets, tmp_path)
            assert os.path.exists(result)
            
            # Verify valid SVG
            tree = ET.parse(result)
            assert tree.getroot().tag.endswith('svg')
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def test_font_embedding_missing_file():
    """Test font embedding gracefully handles missing font file"""
    exporter = EnhancedSVGExporter()
    result = exporter._embed_font("/nonexistent/font.ttf")
    assert result is None


def test_high_fidelity_export_comprehensive(scene_with_widgets):
    """Comprehensive test of high fidelity export with all features"""
    options = ExportOptions.from_preset(ExportPreset.HIGH_FIDELITY)
    exporter = EnhancedSVGExporter(options)
    
    svg_string = exporter.export_scene_to_string(scene_with_widgets)
    
    # Should contain all advanced features
    assert "<defs>" in svg_string
    assert "linearGradient" in svg_string or "radialGradient" in svg_string
    assert "filter" in svg_string
    assert "<pattern" in svg_string
    assert "<metadata>" in svg_string


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
