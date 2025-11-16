#!/usr/bin/env python3
"""
Responsive Layout System for UI Designer
Multi-display support with breakpoints and auto-scaling
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import copy


class DisplaySize(Enum):
    """Common ESP32 display sizes"""
    TINY = (64, 48)        # Ultra small OLED
    SMALL = (128, 64)      # Standard OLED
    MEDIUM = (240, 240)    # Round/square display
    LARGE = (320, 240)     # TFT display
    XLARGE = (480, 320)    # Large TFT
    HD = (800, 480)        # HD display


class LayoutMode(Enum):
    """Layout calculation modes"""
    ABSOLUTE = "absolute"     # Fixed pixel positions
    RELATIVE = "relative"     # Percentage-based
    FLEX = "flex"            # Flexbox-like
    GRID = "grid"            # Grid-based
    ADAPTIVE = "adaptive"    # Auto-adjust to display


class AlignmentMode(Enum):
    """Alignment modes for responsive layout"""
    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"
    SPACE_BETWEEN = "space_between"
    SPACE_AROUND = "space_around"


@dataclass
class Breakpoint:
    """Responsive breakpoint definition"""
    name: str
    min_width: int
    min_height: int
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    
    def matches(self, width: int, height: int) -> bool:
        """Check if display size matches this breakpoint"""
        width_match = self.min_width <= width
        height_match = self.min_height <= height
        
        if self.max_width:
            width_match = width_match and width <= self.max_width
        if self.max_height:
            height_match = height_match and height <= self.max_height
        
        return width_match and height_match


@dataclass
class ResponsiveRule:
    """Responsive layout rule"""
    breakpoint: str
    properties: Dict[str, Any]


@dataclass
class LayoutConstraints:
    """Layout constraints for widget"""
    # Position constraints (percentage or absolute)
    x: Optional[str] = None  # "50%" or "10px"
    y: Optional[str] = None
    
    # Size constraints
    width: Optional[str] = None
    height: Optional[str] = None
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    
    # Aspect ratio
    aspect_ratio: Optional[float] = None
    
    # Alignment
    align_x: str = "start"
    align_y: str = "start"
    
    # Flex properties
    flex_grow: float = 0.0
    flex_shrink: float = 1.0
    flex_basis: Optional[str] = None
    
    # Grid properties
    grid_column: Optional[int] = None
    grid_row: Optional[int] = None
    grid_column_span: int = 1
    grid_row_span: int = 1


@dataclass
class MediaQuery:
    """Media query for responsive design"""
    name: str
    condition: str  # e.g., "width >= 240 and height >= 240"
    styles: Dict[str, Any]


class ResponsiveLayoutSystem:
    """Responsive layout manager"""
    
    def __init__(self):
        self.breakpoints: Dict[str, Breakpoint] = {}
        self.media_queries: List[MediaQuery] = []
        self.current_breakpoint: Optional[str] = None
        
        # Register standard breakpoints
        self._register_standard_breakpoints()
    
    def _register_standard_breakpoints(self):
        """Register standard display breakpoints"""
        breakpoints = [
            Breakpoint("tiny", 0, 0, 80, 60),
            Breakpoint("small", 81, 61, 160, 128),
            Breakpoint("medium", 161, 129, 280, 280),
            Breakpoint("large", 281, 129, 400, 320),
            Breakpoint("xlarge", 401, 321, 640, 480),
            Breakpoint("hd", 641, 481, None, None),
        ]
        
        for bp in breakpoints:
            self.register_breakpoint(bp)
    
    def register_breakpoint(self, breakpoint: Breakpoint):
        """Register a breakpoint"""
        self.breakpoints[breakpoint.name] = breakpoint
    
    def find_breakpoint(self, width: int, height: int) -> Optional[str]:
        """Find matching breakpoint for display size"""
        # Check in order from largest to smallest
        for name in ["hd", "xlarge", "large", "medium", "small", "tiny"]:
            bp = self.breakpoints.get(name)
            if bp and bp.matches(width, height):
                return name
        return None
    
    def parse_value(self, value: str, reference: int) -> int:
        """Parse percentage or absolute value"""
        if isinstance(value, int):
            return value
        
        value = str(value).strip()
        
        if value.endswith('%'):
            percentage = float(value[:-1])
            return int(reference * percentage / 100)
        elif value.endswith("px"):
            return int(value[:-2])
        else:
            return int(value)
    
    def calculate_layout(self, widget_config: Dict[str, Any], 
                        display_width: int, display_height: int,
                        constraints: Optional[LayoutConstraints] = None) -> Dict[str, Any]:
        """Calculate widget layout for display size"""
        result = widget_config.copy()
        
        if not constraints:
            return result
        
        # Calculate position
        if constraints.x:
            result["x"] = self.parse_value(constraints.x, display_width)
        if constraints.y:
            result["y"] = self.parse_value(constraints.y, display_height)
        
        # Calculate size
        if constraints.width:
            result["width"] = self.parse_value(constraints.width, display_width)
        if constraints.height:
            result["height"] = self.parse_value(constraints.height, display_height)
        
        # Apply size constraints
        if constraints.min_width:
            result["width"] = max(result.get("width", 0), constraints.min_width)
        if constraints.max_width:
            result["width"] = min(result.get("width", display_width), constraints.max_width)
        if constraints.min_height:
            result["height"] = max(result.get("height", 0), constraints.min_height)
        if constraints.max_height:
            result["height"] = min(result.get("height", display_height), constraints.max_height)
        
        # Apply aspect ratio
        if constraints.aspect_ratio:
            if constraints.width and not constraints.height:
                result["height"] = int(result["width"] / constraints.aspect_ratio)
            elif constraints.height and not constraints.width:
                result["width"] = int(result["height"] * constraints.aspect_ratio)
        
        # Apply alignment
        if constraints.align_x == "center":
            result["x"] = (display_width - result.get("width", 0)) // 2
        elif constraints.align_x == "end":
            result["x"] = display_width - result.get("width", 0)
        
        if constraints.align_y == "center":
            result["y"] = (display_height - result.get("height", 0)) // 2
        elif constraints.align_y == "end":
            result["y"] = display_height - result.get("height", 0)
        
        return result
    
    def scale_layout(self, widget_config: Dict[str, Any],
                    from_width: int, from_height: int,
                    to_width: int, to_height: int,
                    mode: str = "proportional") -> Dict[str, Any]:
        """Scale widget layout from one display size to another"""
        result = widget_config.copy()
        
        if mode == "proportional":
            # Scale proportionally
            scale_x = to_width / from_width
            scale_y = to_height / from_height
            
            result["x"] = int(widget_config.get("x", 0) * scale_x)
            result["y"] = int(widget_config.get("y", 0) * scale_y)
            result["width"] = int(widget_config.get("width", 10) * scale_x)
            result["height"] = int(widget_config.get("height", 10) * scale_y)
        
        elif mode == "fit":
            # Maintain aspect ratio, fit to display
            scale = min(to_width / from_width, to_height / from_height)
            
            result["x"] = int(widget_config.get("x", 0) * scale)
            result["y"] = int(widget_config.get("y", 0) * scale)
            result["width"] = int(widget_config.get("width", 10) * scale)
            result["height"] = int(widget_config.get("height", 10) * scale)
        
        elif mode == "fill":
            # Fill display, may distort
            scale_x = to_width / from_width
            scale_y = to_height / from_height
            
            result["x"] = int(widget_config.get("x", 0) * scale_x)
            result["y"] = int(widget_config.get("y", 0) * scale_y)
            result["width"] = int(widget_config.get("width", 10) * scale_x)
            result["height"] = int(widget_config.get("height", 10) * scale_y)
        
        elif mode == "center":
            # Center without scaling
            offset_x = (to_width - from_width) // 2
            offset_y = (to_height - from_height) // 2
            
            result["x"] = widget_config.get("x", 0) + offset_x
            result["y"] = widget_config.get("y", 0) + offset_y
        
        return result
    
    def apply_responsive_rules(self, widget_config: Dict[str, Any],
                              rules: List[ResponsiveRule],
                              display_width: int, display_height: int) -> Dict[str, Any]:
        """Apply responsive rules based on current breakpoint"""
        result = widget_config.copy()
        
        current_bp = self.find_breakpoint(display_width, display_height)
        if not current_bp:
            return result
        
        # Apply matching rules
        for rule in rules:
            if rule.breakpoint == current_bp or rule.breakpoint == "all":
                result.update(rule.properties)
        
        return result
    
    def create_flex_layout(self, widgets: List[Dict[str, Any]],
                          container_width: int, container_height: int,
                          direction: str = "row",
                          justify: str = "start",
                          align: str = "start",
                          gap: int = 4) -> List[Dict[str, Any]]:
        """Create flexbox-like layout"""
        result = []
        
        if direction == "row":
            # Horizontal layout
            current_x = 0
            
            # Calculate total flex
            total_flex = sum(w.get("flex_grow", 0) for w in widgets)
            available_width = container_width - (len(widgets) - 1) * gap
            
            # Calculate fixed widths
            fixed_width = sum(w.get("width", 0) for w in widgets if "width" in w)
            flex_width = available_width - fixed_width
            
            for widget in widgets:
                w_config = widget.copy()
                
                # Calculate width
                if "width" not in w_config:
                    flex = w_config.get("flex_grow", 1)
                    if total_flex > 0:
                        w_config["width"] = int(flex_width * flex / total_flex)
                    else:
                        w_config["width"] = flex_width // len(widgets)
                
                # Position
                w_config["x"] = current_x
                
                # Vertical alignment
                if align == "center":
                    w_config["y"] = (container_height - w_config.get("height", 10)) // 2
                elif align == "end":
                    w_config["y"] = container_height - w_config.get("height", 10)
                else:
                    w_config["y"] = 0
                
                current_x += w_config["width"] + gap
                result.append(w_config)
        
        else:  # column
            # Vertical layout
            current_y = 0
            
            total_flex = sum(w.get("flex_grow", 0) for w in widgets)
            available_height = container_height - (len(widgets) - 1) * gap
            
            fixed_height = sum(w.get("height", 0) for w in widgets if "height" in w)
            flex_height = available_height - fixed_height
            
            for widget in widgets:
                w_config = widget.copy()
                
                # Calculate height
                if "height" not in w_config:
                    flex = w_config.get("flex_grow", 1)
                    if total_flex > 0:
                        w_config["height"] = int(flex_height * flex / total_flex)
                    else:
                        w_config["height"] = flex_height // len(widgets)
                
                # Position
                w_config["y"] = current_y
                
                # Horizontal alignment
                if align == "center":
                    w_config["x"] = (container_width - w_config.get("width", 10)) // 2
                elif align == "end":
                    w_config["x"] = container_width - w_config.get("width", 10)
                else:
                    w_config["x"] = 0
                
                current_y += w_config["height"] + gap
                result.append(w_config)
        
        return result
    
    def create_grid_layout(self, widgets: List[Dict[str, Any]],
                          container_width: int, container_height: int,
                          columns: int = 2, rows: int = 2,
                          gap: int = 4) -> List[Dict[str, Any]]:
        """Create grid layout"""
        result = []
        
        cell_width = (container_width - (columns - 1) * gap) // columns
        cell_height = (container_height - (rows - 1) * gap) // rows
        
        for idx, widget in enumerate(widgets):
            w_config = widget.copy()
            
            # Get grid position
            col = w_config.get("grid_column", idx % columns)
            row = w_config.get("grid_row", idx // columns)
            col_span = w_config.get("grid_column_span", 1)
            row_span = w_config.get("grid_row_span", 1)
            
            # Calculate position and size
            w_config["x"] = col * (cell_width + gap)
            w_config["y"] = row * (cell_height + gap)
            w_config["width"] = cell_width * col_span + gap * (col_span - 1)
            w_config["height"] = cell_height * row_span + gap * (row_span - 1)
            
            result.append(w_config)
        
        return result
    
    def add_media_query(self, name: str, condition: str, styles: Dict[str, Any]):
        """Add media query"""
        query = MediaQuery(name=name, condition=condition, styles=styles)
        self.media_queries.append(query)
    
    def evaluate_media_queries(self, width: int, height: int) -> Dict[str, Any]:
        """Evaluate all media queries and return matching styles"""
        styles = {}
        
        for query in self.media_queries:
            # Simple condition evaluation
            # Replace width/height in condition and eval
            condition = query.condition.replace("width", str(width))
            condition = condition.replace("height", str(height))
            
            try:
                if eval(condition):
                    styles.update(query.styles)
            except:
                pass
        
        return styles
    
    def export_layout_config(self, filename: str, 
                           breakpoints: Dict[str, List[Dict[str, Any]]]):
        """Export responsive layout configuration"""
        config = {
            "breakpoints": {name: asdict(bp) for name, bp in self.breakpoints.items()},
            "layouts": breakpoints
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
    
    def import_layout_config(self, filename: str) -> Dict[str, Any]:
        """Import responsive layout configuration"""
        with open(filename, 'r') as f:
            return json.load(f)


def main():
    """Demo responsive layout system"""
    print("📱 UI DESIGNER RESPONSIVE LAYOUT SYSTEM\n")
    
    system = ResponsiveLayoutSystem()
    
    print("Registered Breakpoints:")
    for name, bp in system.breakpoints.items():
        max_w = bp.max_width if bp.max_width else "∞"
        max_h = bp.max_height if bp.max_height else "∞"
        print(f"  • {name:8} {bp.min_width}×{bp.min_height} to {max_w}×{max_h}")
    
    print("\n" + "="*60)
    
    # Test breakpoint detection
    print("\nBreakpoint Detection:")
    test_sizes = [
        (64, 48, "tiny"),
        (128, 64, "small"),
        (240, 240, "medium"),
        (320, 240, "large"),
    ]
    
    for width, height, expected in test_sizes:
        detected = system.find_breakpoint(width, height)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {width}×{height} → {detected}")
    
    print("\n" + "="*60)
    
    # Test scaling
    print("\nLayout Scaling Demo:")
    original = {
        "type": "label",
        "x": 10,
        "y": 10,
        "width": 50,
        "height": 20,
        "text": "Hello"
    }
    
    print(f"  Original (128×64): {original}")
    
    scaled_large = system.scale_layout(original, 128, 64, 320, 240, "proportional")
    print(f"  Scaled (320×240):  x={scaled_large['x']}, y={scaled_large['y']}, "
          f"w={scaled_large['width']}, h={scaled_large['height']}")
    
    print("\n" + "="*60)
    
    # Test percentage layout
    print("\nPercentage-based Layout:")
    constraints = LayoutConstraints(
        x="25%",
        y="50%",
        width="50%",
        height="20%",
        align_x="center",
        align_y="center"
    )
    
    widget = {"type": "button", "text": "Click"}
    result = system.calculate_layout(widget, 320, 240, constraints)
    print(f"  Input: x=25%, y=50%, w=50%, h=20%")
    print(f"  Output (320×240): x={result['x']}, y={result['y']}, "
          f"w={result['width']}, h={result['height']}")
    
    print("\n" + "="*60)
    
    # Test flex layout
    print("\nFlex Layout Demo:")
    widgets = [
        {"type": "button", "text": "A", "flex_grow": 1},
        {"type": "button", "text": "B", "flex_grow": 2},
        {"type": "button", "text": "C", "flex_grow": 1},
    ]
    
    flex_result = system.create_flex_layout(widgets, 320, 60, direction="row", gap=4)
    print("  Horizontal flex layout (320×60, gap=4):")
    for i, w in enumerate(flex_result):
        print(f"    Widget {i}: x={w['x']}, width={w['width']}")
    
    print("\n" + "="*60)
    
    # Test grid layout
    print("\nGrid Layout Demo:")
    grid_widgets = [
        {"type": "label", "text": "1"},
        {"type": "label", "text": "2"},
        {"type": "label", "text": "3"},
        {"type": "label", "text": "4"},
    ]
    
    grid_result = system.create_grid_layout(grid_widgets, 320, 240, 
                                           columns=2, rows=2, gap=8)
    print("  2×2 grid (320×240, gap=8):")
    for i, w in enumerate(grid_result):
        print(f"    Cell {i}: x={w['x']}, y={w['y']}, "
              f"w={w['width']}, h={w['height']}")
    
    print("\n✅ Responsive layout system ready!")


if __name__ == "__main__":
    main()
