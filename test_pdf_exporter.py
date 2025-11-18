"""Tests for PDF Exporter"""

import pytest
import os
import tempfile
import json
from pathlib import Path

# Skip tests if reportlab not available
pytest.importorskip("reportlab")

from pdf_exporter import PDFExporter


@pytest.fixture
def sample_scene():
    """Sample scene data for testing"""
    return {
        "name": "Test Scene",
        "width": 320,
        "height": 240,
        "background_color": "#000000",
        "grid_size": 8,
        "widgets": [
            {
                "type": "label",
                "x": 10,
                "y": 10,
                "width": 100,
                "height": 20,
                "text": "Test Label",
                "color_fg": "#FFFFFF",
                "color_bg": "#000000",
                "border": True
            },
            {
                "type": "button",
                "x": 10,
                "y": 40,
                "width": 80,
                "height": 24,
                "text": "Button",
                "color_fg": "#FFFFFF",
                "color_bg": "#333333",
                "border": True
            },
            {
                "type": "progressbar",
                "x": 10,
                "y": 80,
                "width": 120,
                "height": 16,
                "value": 75,
                "color_fg": "#00FF00",
                "color_bg": "#333333",
                "border": True
            },
            {
                "type": "checkbox",
                "x": 10,
                "y": 110,
                "width": 80,
                "height": 16,
                "text": "Check",
                "checked": True,
                "color_fg": "#FFFFFF",
                "color_bg": "#000000",
                "border": True
            },
            {
                "type": "slider",
                "x": 10,
                "y": 140,
                "width": 100,
                "height": 16,
                "value": 60,
                "color_fg": "#FFFFFF",
                "color_bg": "#000000",
                "border": True
            },
            {
                "type": "gauge",
                "x": 10,
                "y": 170,
                "width": 50,
                "height": 50,
                "value": 80,
                "color_fg": "#FFFFFF",
                "color_bg": "#000000",
                "border": True
            }
        ]
    }


class TestPDFExporter:
    def test_create_exporter(self):
        exporter = PDFExporter()
        assert exporter is not None
        assert "a4" in exporter.page_sizes
    
    def test_export_single_scene(self, sample_scene):
        exporter = PDFExporter()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = f.name
        
        try:
            result = exporter.export_scene(sample_scene, output_path)
            assert result is True
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_with_grid(self, sample_scene):
        exporter = PDFExporter()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = f.name
        
        try:
            result = exporter.export_scene(sample_scene, output_path, 
                                          show_grid=True, show_guides=True)
            assert result is True
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_different_page_sizes(self, sample_scene):
        exporter = PDFExporter()
        
        for page_size in ["letter", "a4", "a3"]:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                output_path = f.name
            
            try:
                result = exporter.export_scene(sample_scene, output_path, 
                                              page_size=page_size)
                assert result is True
                assert os.path.exists(output_path)
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)
    
    def test_export_with_scale(self, sample_scene):
        exporter = PDFExporter()
        
        for scale in [0.5, 1.0, 2.0]:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                output_path = f.name
            
            try:
                result = exporter.export_scene(sample_scene, output_path, scale=scale)
                assert result is True
                assert os.path.exists(output_path)
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)
    
    def test_export_multiple_scenes(self, sample_scene):
        exporter = PDFExporter()
        
        # Create multiple scenes
        scenes = []
        for i in range(3):
            scene = sample_scene.copy()
            scene["name"] = f"Scene {i+1}"
            scenes.append(scene)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = f.name
        
        try:
            result = exporter.export_multiple_scenes(scenes, output_path)
            assert result is True
            assert os.path.exists(output_path)
            # Multi-page PDF should be larger
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_batch_export(self, sample_scene):
        exporter = PDFExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            
            # Create test JSON files
            for i in range(3):
                json_path = input_dir / f"scene_{i}.json"
                with open(json_path, 'w') as f:
                    json.dump(sample_scene, f)
            
            # Batch export
            exported = exporter.batch_export(str(input_dir), str(output_dir))
            
            assert len(exported) == 3
            for pdf_path in exported:
                assert os.path.exists(pdf_path)
                assert pdf_path.endswith('.pdf')
    
    def test_parse_color(self):
        exporter = PDFExporter()
        
        # Test hex color
        color = exporter._parse_color("#FF0000")
        assert color.red == 1.0
        assert color.green == 0.0
        assert color.blue == 0.0
        
        # Test another hex
        color = exporter._parse_color("#00FF00")
        assert color.green == 1.0
        
        # Test invalid color (should default to white)
        color = exporter._parse_color("invalid")
        assert color.red == 1.0
        assert color.green == 1.0
        assert color.blue == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
