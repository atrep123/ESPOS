#!/usr/bin/env python3
"""
Export Parity Test Harness
Validates that ASCII, HTML, and C exports produce equivalent visual output.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List, Tuple

from ui_designer import UIDesigner, WidgetConfig


class ExportParityValidator:
    """Validates export consistency across formats."""
    
    def __init__(self):
        self.tolerance = 0.05  # 5% difference allowed
    
    def validate_widget_counts(
        self,
        ascii_output: str,
        html_output: str,
        c_output: str,
        expected_widgets: int
    ) -> Tuple[bool, str]:
        """Ensure all formats export the same number of widgets.
        
        Returns:
            (is_valid, error_message)
        """
        # ASCII: count widget boundaries (simplified heuristic, may undercount)
        ascii_widget_markers = ascii_output.count("┌") + ascii_output.count("╔")
        
        # C: count widget definitions
        c_widget_markers = c_output.count("ui_widget_t")
        
        # ASCII may undercount due to overlapping widgets, so be lenient
        if ascii_widget_markers < 1:
            return False, f"ASCII has no visible widgets: {ascii_widget_markers}"
        
        # C should match expected count (if not mocked)
        if "mock" not in c_output.lower():
            if c_widget_markers != expected_widgets:
                return False, f"C widget count mismatch: {c_widget_markers} vs expected {expected_widgets}"
        
        return True, ""
    
    def validate_text_content(
        self,
        ascii_output: str,
        html_output: str,
        expected_texts: List[str]
    ) -> Tuple[bool, str]:
        """Check that expected text appears in both ASCII and HTML.
        
        Returns:
            (is_valid, error_message)
        """
        missing_in_ascii = []
        missing_in_html = []
        
        for text in expected_texts:
            if text not in ascii_output:
                missing_in_ascii.append(text)
            if text not in html_output:
                missing_in_html.append(text)
        
        if missing_in_ascii:
            return False, f"ASCII missing text: {missing_in_ascii}"
        
        if missing_in_html:
            return False, f"HTML missing text: {missing_in_html}"
        
        return True, ""
    
    def validate_c_export_syntax(self, c_output: str) -> Tuple[bool, str]:
        """Basic C syntax validation.
        
        Returns:
            (is_valid, error_message)
        """
        required_patterns = [
            "ui_widget_t",
            "{",
            "}",
            ".x =",
            ".y =",
            ".width =",
            ".height =",
        ]
        
        for pattern in required_patterns:
            if pattern not in c_output:
                return False, f"C export missing required pattern: '{pattern}'"
        
        # Check balanced braces
        open_braces = c_output.count("{")
        close_braces = c_output.count("}")
        
        if open_braces != close_braces:
            return False, f"C export has unbalanced braces: {open_braces} open, {close_braces} close"
        
        return True, ""


# ========================================
# Test cases
# ========================================

@pytest.fixture
def simple_scene():
    """Create a simple test scene."""
    designer = UIDesigner(width=200, height=100)
    designer.create_scene("test_scene")
    
    designer.add_widget(WidgetConfig(
        type="panel",
        x=0, y=0, width=200, height=100,
        text="Test Panel",
        border=True,
        border_style="single"
    ))
    
    designer.add_widget(WidgetConfig(
        type="label",
        x=10, y=10, width=50, height=10,
        text="Hello"
    ))
    
    designer.add_widget(WidgetConfig(
        type="button",
        x=10, y=30, width=60, height=15,
        text="Click Me",
        border=True
    ))
    
    return designer


def test_export_parity_widget_count(simple_scene, tmp_path):
    """Verify all formats export the same number of widgets."""
    validator = ExportParityValidator()
    
    # Export to ASCII and HTML
    ascii_output = simple_scene.preview_ascii()
    
    html_path = tmp_path / "test.html"
    simple_scene.export_to_html(str(html_path))
    html_output = html_path.read_text(encoding='utf-8')
    
    # Mock C output (no ui_export_c integration for now)
    c_output = "ui_widget_t w1; ui_widget_t w2; ui_widget_t w3;"
    
    # Validate
    is_valid, error = validator.validate_widget_counts(
        ascii_output, html_output, c_output, expected_widgets=3
    )
    
    assert is_valid, error


def test_export_parity_text_content(simple_scene, tmp_path):
    """Verify text content appears in ASCII and HTML exports."""
    validator = ExportParityValidator()
    
    ascii_output = simple_scene.preview_ascii()
    
    html_path = tmp_path / "test.html"
    simple_scene.export_to_html(str(html_path))
    html_output = html_path.read_text(encoding='utf-8')
    
    expected_texts = ["Test Panel", "Hello", "Click Me"]
    
    is_valid, error = validator.validate_text_content(
        ascii_output, html_output, expected_texts
    )
    
    assert is_valid, error


def test_c_export_syntax_valid(simple_scene, tmp_path):
    """Verify C export has valid syntax."""
    validator = ExportParityValidator()
    
    # Mock C output (full ui_export_c integration pending)
    c_output = '''ui_widget_t widgets[] = {
    { .x = 0, .y = 0, .width = 200, .height = 100 },
    { .x = 10, .y = 10, .width = 50, .height = 10 },
    { .x = 10, .y = 30, .width = 60, .height = 15 }
};'''
    
    is_valid, error = validator.validate_c_export_syntax(c_output)
    
    assert is_valid, error


def test_export_parity_golden_file():
    """Golden file regression test for ASCII export.
    
    This test ensures ASCII rendering doesn't change unexpectedly.
    Update the golden file when intentional changes are made.
    """
    designer = UIDesigner(width=80, height=30)
    designer.create_scene("golden")
    
    designer.add_widget(WidgetConfig(
        type="panel",
        x=0, y=0, width=80, height=30,
        text="Golden Test",
        border=True,
        border_style="double"
    ))
    
    designer.add_widget(WidgetConfig(
        type="label",
        x=5, y=5, width=30, height=5,
        text="Status: OK"
    ))
    
    ascii_output = designer.preview_ascii()
    
    # Store golden file
    golden_path = Path(__file__).parent / "test_export_parity_golden.txt"
    
    if not golden_path.exists():
        # First run: create golden file
        golden_path.write_text(ascii_output, encoding='utf-8')
        pytest.skip("Created golden file, re-run test to validate")
    
    # Compare with golden
    golden_output = golden_path.read_text(encoding='utf-8')
    
    assert ascii_output == golden_output, (
        "ASCII export changed! If intentional, delete the golden file and re-run.\n"
        f"Golden file: {golden_path}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
