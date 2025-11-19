# PDF Exporter for ESP32OS UI Designer
#
# Features:
# - Export scenes to PDF with vector graphics
# - Multi-page PDF support (one page per scene)
# - Embedded fonts and colors
# - Scalable vector output
# - Batch export functionality

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, A4, letter
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not available. Install with: pip install reportlab")


class PDFExporter:
    """Export UI designs to PDF format"""
    
    def __init__(self):
        self.page_sizes = {
            "letter": letter,
            "a4": A4,
            "a3": A3,
            "custom": None
        }
    
    def export_scene(self, 
                    scene_data: Dict[str, Any],
                    output_path: str,
                    page_size: str = "a4",
                    scale: float = 1.0,
                    show_grid: bool = False,
                    show_guides: bool = False) -> bool:
        """
        Export single scene to PDF
        
        Args:
            scene_data: Scene dictionary with widgets
            output_path: Output PDF file path
            page_size: Page size (letter/a4/a3/custom)
            scale: Scale factor for rendering
            show_grid: Show grid lines
            show_guides: Show alignment guides
            
        Returns:
            True if successful
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab required for PDF export")
        
        # Get page size
        if page_size == "custom":
            width = scene_data.get("width", 320) * scale
            height = scene_data.get("height", 240) * scale
            page_dims = (width, height)
        else:
            page_dims = self.page_sizes.get(page_size, A4)
        
        # Create PDF canvas
        c = canvas.Canvas(output_path, pagesize=page_dims)
        page_width, page_height = page_dims
        
        # Calculate centering offset
        scene_width = scene_data.get("width", 320) * scale
        scene_height = scene_data.get("height", 240) * scale
        offset_x = (page_width - scene_width) / 2
        offset_y = (page_height - scene_height) / 2
        
        # Draw background
        bg_color = scene_data.get("background_color", "#000000")
        c.setFillColor(self._parse_color(bg_color))
        c.rect(offset_x, offset_y, scene_width, scene_height, fill=1, stroke=0)
        
        # Draw grid if enabled
        if show_grid:
            self._draw_grid(c, offset_x, offset_y, scene_width, scene_height, 
                          scene_data.get("grid_size", 8) * scale)
        
        # Draw widgets
        widgets = scene_data.get("widgets", [])
        for widget in widgets:
            self._draw_widget_pdf(c, widget, offset_x, offset_y, scale)
        
        # Draw guides if enabled
        if show_guides:
            self._draw_guides(c, offset_x, offset_y, scene_width, scene_height)
        
        # Add metadata
        c.setTitle(scene_data.get("name", "UI Design"))
        c.setAuthor("ESP32OS UI Designer")
        c.setSubject("UI Design Export")
        
        # Save PDF
        c.save()
        return True
    
    def export_multiple_scenes(self,
                              scenes: List[Dict[str, Any]],
                              output_path: str,
                              page_size: str = "a4",
                              scale: float = 1.0) -> bool:
        """
        Export multiple scenes to multi-page PDF
        
        Args:
            scenes: List of scene dictionaries
            output_path: Output PDF file path
            page_size: Page size for all pages
            scale: Scale factor
            
        Returns:
            True if successful
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab required for PDF export")
        
        page_dims = self.page_sizes.get(page_size, A4)
        c = canvas.Canvas(output_path, pagesize=page_dims)
        
        for idx, scene in enumerate(scenes):
            if idx > 0:
                c.showPage()  # New page for each scene
            
            # Render scene on current page
            self._render_scene_page(c, scene, page_dims, scale)
        
        c.save()
        return True
    
    def _render_scene_page(self, c: canvas.Canvas, scene: Dict[str, Any], 
                          page_dims: Tuple[float, float], scale: float):
        """Render a single scene on current page"""
        page_width, page_height = page_dims
        
        scene_width = scene.get("width", 320) * scale
        scene_height = scene.get("height", 240) * scale
        offset_x = (page_width - scene_width) / 2
        offset_y = (page_height - scene_height) / 2
        
        # Background
        bg_color = scene.get("background_color", "#000000")
        c.setFillColor(self._parse_color(bg_color))
        c.rect(offset_x, offset_y, scene_width, scene_height, fill=1, stroke=0)
        
        # Widgets
        widgets = scene.get("widgets", [])
        for widget in widgets:
            self._draw_widget_pdf(c, widget, offset_x, offset_y, scale)
        
        # Add scene name as footer
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        scene_name = scene.get("name", f"Scene {id(scene)}")
        c.drawCentredString(page_width / 2, 20, scene_name)
    
    def _draw_widget_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                        offset_x: float, offset_y: float, scale: float):
        """Draw a widget in PDF using vector graphics"""
        x = widget.get("x", 0) * scale + offset_x
        y = widget.get("y", 0) * scale + offset_y
        w = widget.get("width", 40) * scale
        h = widget.get("height", 12) * scale
        
        # PDF coordinates are bottom-left, need to flip Y
        y_pdf = offset_y + (widget.get("height", 240) * scale) - y - h
        
        widget_type = widget.get("type", "label")
        
        # Get colors
        fg_color = self._parse_color(widget.get("color_fg", "#FFFFFF"))
        bg_color = self._parse_color(widget.get("color_bg", "#000000"))
        
        # Draw background
        c.setFillColor(bg_color)
        c.rect(x, y_pdf, w, h, fill=1, stroke=0)
        
        # Draw border
        if widget.get("border", True):
            c.setStrokeColor(fg_color)
            c.setLineWidth(1)
            c.rect(x, y_pdf, w, h, fill=0, stroke=1)
        
        # Widget-specific rendering
        if widget_type == "label":
            self._draw_label_pdf(c, widget, x, y_pdf, w, h, fg_color)
        elif widget_type == "button":
            self._draw_button_pdf(c, widget, x, y_pdf, w, h, fg_color)
        elif widget_type == "progressbar":
            self._draw_progressbar_pdf(c, widget, x, y_pdf, w, h, fg_color)
        elif widget_type == "checkbox":
            self._draw_checkbox_pdf(c, widget, x, y_pdf, w, h, fg_color)
        elif widget_type == "slider":
            self._draw_slider_pdf(c, widget, x, y_pdf, w, h, fg_color)
        elif widget_type == "gauge":
            self._draw_gauge_pdf(c, widget, x, y_pdf, w, h, fg_color)
    
    def _draw_label_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                       x: float, y: float, w: float, h: float, color):
        """Draw label widget"""
        text = widget.get("text", "Label")
        c.setFillColor(color)
        c.setFont("Helvetica", 8)
        
        # Center text
        text_width = c.stringWidth(text, "Helvetica", 8)
        text_x = x + (w - text_width) / 2
        text_y = y + h / 2 - 3
        
        c.drawString(text_x, text_y, text)
    
    def _draw_button_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                        x: float, y: float, w: float, h: float, color):
        """Draw button widget"""
        text = widget.get("text", "Button")
        
        # Button background (slightly lighter)
        c.setFillColor(colors.Color(0.2, 0.2, 0.2))
        c.rect(x + 1, y + 1, w - 2, h - 2, fill=1, stroke=0)
        
        # Text
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 8)
        text_width = c.stringWidth(text, "Helvetica-Bold", 8)
        text_x = x + (w - text_width) / 2
        text_y = y + h / 2 - 3
        c.drawString(text_x, text_y, text)
    
    def _draw_progressbar_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                             x: float, y: float, w: float, h: float, color):
        """Draw progress bar widget"""
        value = widget.get("value", 50)
        
        # Progress fill
        fill_width = (w - 4) * (value / 100.0)
        c.setFillColor(color)
        c.rect(x + 2, y + 2, fill_width, h - 4, fill=1, stroke=0)
        
        # Percentage text
        c.setFont("Helvetica", 6)
        text = f"{value}%"
        text_width = c.stringWidth(text, "Helvetica", 6)
        c.drawString(x + (w - text_width) / 2, y + h / 2 - 2, text)
    
    def _draw_checkbox_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                          x: float, y: float, w: float, h: float, color):
        """Draw checkbox widget"""
        box_size = min(h - 4, 10)
        box_x = x + 2
        box_y = y + (h - box_size) / 2
        
        # Checkbox box
        c.setStrokeColor(color)
        c.rect(box_x, box_y, box_size, box_size, fill=0, stroke=1)
        
        # Check mark if checked
        if widget.get("checked", False):
            c.setStrokeColor(color)
            c.setLineWidth(2)
            c.line(box_x + 2, box_y + box_size / 2, 
                  box_x + box_size / 2, box_y + 2)
            c.line(box_x + box_size / 2, box_y + 2, 
                  box_x + box_size - 2, box_y + box_size - 2)
        
        # Label
        text = widget.get("text", "")
        if text:
            c.setFillColor(color)
            c.setFont("Helvetica", 7)
            c.drawString(box_x + box_size + 4, box_y + 2, text)
    
    def _draw_slider_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                        x: float, y: float, w: float, h: float, color):
        """Draw slider widget"""
        value = widget.get("value", 50)
        
        # Slider track
        track_y = y + h / 2
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.line(x + 4, track_y, x + w - 4, track_y)
        
        # Slider thumb
        thumb_x = x + 4 + (w - 8) * (value / 100.0)
        thumb_size = 6
        c.setFillColor(color)
        c.circle(thumb_x, track_y, thumb_size / 2, fill=1, stroke=0)
    
    def _draw_gauge_pdf(self, c: canvas.Canvas, widget: Dict[str, Any],
                       x: float, y: float, w: float, h: float, color):
        """Draw gauge widget (arc-based)"""
        value = widget.get("value", 75)
        
        # Center point
        cx = x + w / 2
        cy = y + h / 2
        radius = min(w, h) / 2 - 4
        
        # Draw arc (simplified as circle for now)
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.circle(cx, cy, radius, fill=0, stroke=1)
        
        # Value indicator (line)
        import math
        angle = (value / 100.0) * 270 - 225  # -225 to 45 degrees
        angle_rad = math.radians(angle)
        end_x = cx + radius * math.cos(angle_rad)
        end_y = cy + radius * math.sin(angle_rad)
        c.line(cx, cy, end_x, end_y)
        
        # Value text
        c.setFillColor(color)
        c.setFont("Helvetica", 6)
        text = f"{value}%"
        text_width = c.stringWidth(text, "Helvetica", 6)
        c.drawString(cx - text_width / 2, cy - 3, text)
    
    def _draw_grid(self, c: canvas.Canvas, offset_x: float, offset_y: float,
                  width: float, height: float, grid_size: float):
        """Draw grid overlay"""
        c.setStrokeColor(colors.Color(0.2, 0.2, 0.2))
        c.setLineWidth(0.5)
        
        # Vertical lines
        x = offset_x
        while x <= offset_x + width:
            c.line(x, offset_y, x, offset_y + height)
            x += grid_size
        
        # Horizontal lines
        y = offset_y
        while y <= offset_y + height:
            c.line(offset_x, y, offset_x + width, y)
            y += grid_size
    
    def _draw_guides(self, c: canvas.Canvas, offset_x: float, offset_y: float,
                    width: float, height: float):
        """Draw alignment guides"""
        c.setStrokeColor(colors.blue)
        c.setLineWidth(0.5)
        c.setDash(3, 3)
        
        # Center lines
        cx = offset_x + width / 2
        cy = offset_y + height / 2
        
        c.line(cx, offset_y, cx, offset_y + height)
        c.line(offset_x, cy, offset_x + width, cy)
        
        c.setDash()  # Reset dash
    
    def _parse_color(self, color_str: str):
        """Parse color string to reportlab color"""
        if color_str.startswith("#"):
            # Hex color
            hex_color = color_str.lstrip("#")
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                return colors.Color(r, g, b)
        
        # Default to white
        return colors.white
    
    def batch_export(self, 
                    input_dir: str,
                    output_dir: str,
                    file_pattern: str = "*.json",
                    **kwargs) -> List[str]:
        """
        Batch export multiple JSON files to PDF
        
        Args:
            input_dir: Input directory with JSON files
            output_dir: Output directory for PDFs
            file_pattern: File pattern to match
            **kwargs: Additional export options
            
        Returns:
            List of exported PDF paths
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported = []
        for json_file in input_path.glob(file_pattern):
            try:
                # Load JSON
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Export to PDF
                pdf_file = output_path / f"{json_file.stem}.pdf"
                
                # Handle both single scene and multi-scene files
                if "scenes" in data:
                    scenes = list(data["scenes"].values())
                    self.export_multiple_scenes(scenes, str(pdf_file), **kwargs)
                else:
                    self.export_scene(data, str(pdf_file), **kwargs)
                
                exported.append(str(pdf_file))
            except Exception as e:
                print(f"Failed to export {json_file}: {e}")
        
        return exported


def main():
    """Example usage"""
    if not REPORTLAB_AVAILABLE:
        print("Install reportlab: pip install reportlab")
        return
    
    # Example scene data
    scene = {
        "name": "Example Scene",
        "width": 320,
        "height": 240,
        "background_color": "#000000",
        "widgets": [
            {
                "type": "label",
                "x": 10,
                "y": 10,
                "width": 100,
                "height": 20,
                "text": "Hello PDF!",
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
                "text": "Click Me",
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
            }
        ]
    }
    
    exporter = PDFExporter()
    exporter.export_scene(scene, "example_export.pdf", scale=2.0, show_grid=True)
    print("Exported to example_export.pdf")


if __name__ == "__main__":
    main()
