#!/usr/bin/env python3
"""
Visual UI Designer for ESP32 Simulator
Drag-and-drop widget editor with live preview and code generation
"""

import sys
import json
import copy
import shlex
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class WidgetType(Enum):
    """Available widget types"""
    LABEL = "label"
    BOX = "box"
    BUTTON = "button"
    GAUGE = "gauge"
    PROGRESSBAR = "progressbar"
    CHECKBOX = "checkbox"
    RADIOBUTTON = "radiobutton"
    SLIDER = "slider"
    TEXTBOX = "textbox"
    PANEL = "panel"
    ICON = "icon"
    CHART = "chart"


class BorderStyle(Enum):
    """Border styles"""
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"
    ROUNDED = "rounded"
    BOLD = "bold"
    DASHED = "dashed"


@dataclass
class WidgetConfig:
    """Widget configuration"""
    type: str  # label, box, button, gauge, progressbar, checkbox, etc.
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    style: str = "default"  # default, bold, inverse, highlight
    color_fg: str = "white"
    color_bg: str = "black"
    border: bool = True
    border_style: str = "single"  # single, double, rounded, bold, dashed
    align: str = "left"  # left, center, right
    valign: str = "middle"  # top, middle, bottom
    
    # Extended properties
    value: int = 0  # For gauge, slider, progressbar
    min_value: int = 0
    max_value: int = 100
    checked: bool = False  # For checkbox, radiobutton
    enabled: bool = True
    visible: bool = True
    icon_char: str = ""  # For icon widget
    data_points: List[int] = field(default_factory=list)  # For chart
    z_index: int = 0  # Layer order
    
    # Layout hints
    padding_x: int = 1
    padding_y: int = 0
    margin_x: int = 0
    margin_y: int = 0
    # Responsive/constraints metadata (stored as simple dicts for export)
    constraints: Dict[str, Any] = field(default_factory=dict)
    responsive_rules: List[Dict[str, Any]] = field(default_factory=list)
    animations: List[str] = field(default_factory=list)


@dataclass
class SceneConfig:
    """Scene configuration"""
    name: str
    width: int
    height: int
    widgets: List[WidgetConfig]
    bg_color: str = "black"


class UIDesigner:
    """Visual UI designer with layout editor"""
    
    def __init__(self, width: int = 128, height: int = 64):
        self.width = width
        self.height = height
        self.scenes: Dict[str, SceneConfig] = {}
        self.current_scene: Optional[str] = None
        self.selected_widget: Optional[int] = None
        
        # Undo/redo stacks
        self.undo_stack: List[str] = []  # JSON snapshots
        self.redo_stack: List[str] = []
        self.max_undo = 50
        
        # Templates
        self.templates: Dict[str, WidgetConfig] = self._create_default_templates()
        
        # Grid settings
        self.grid_enabled = True
        self.grid_size = 4
        self.snap_to_grid = True
    
    def _create_default_templates(self) -> Dict[str, WidgetConfig]:
        """Create default widget templates"""
        return {
            'title_label': WidgetConfig(
                type='label', x=0, y=0, width=128, height=10,
                text='Title', align='center', style='bold',
                border=False, color_fg='cyan'
            ),
            'button_primary': WidgetConfig(
                type='button', x=0, y=0, width=40, height=12,
                text='OK', align='center', border=True,
                border_style='rounded', color_fg='black', color_bg='green'
            ),
            'button_secondary': WidgetConfig(
                type='button', x=0, y=0, width=40, height=12,
                text='Cancel', align='center', border=True,
                border_style='rounded', color_fg='white', color_bg='red'
            ),
            'info_panel': WidgetConfig(
                type='panel', x=0, y=0, width=120, height=50,
                border=True, border_style='double', color_fg='white', color_bg='blue'
            ),
            'progress_bar': WidgetConfig(
                type='progressbar', x=0, y=0, width=100, height=8,
                value=50, min_value=0, max_value=100,
                border=True, color_fg='green', color_bg='black'
            ),
            'gauge_half': WidgetConfig(
                type='gauge', x=0, y=0, width=40, height=20,
                value=75, min_value=0, max_value=100,
                border=True, color_fg='yellow'
            ),
        }
    
    def _save_state(self):
        """Save current state for undo"""
        if self.current_scene and self.current_scene in self.scenes:
            state = json.dumps(asdict(self.scenes[self.current_scene]))
            self.undo_stack.append(state)
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
    
    def undo(self) -> bool:
        """Undo last operation"""
        if not self.undo_stack or not self.current_scene:
            return False
        
        # Save current state to redo
        current_state = json.dumps(asdict(self.scenes[self.current_scene]))
        self.redo_stack.append(current_state)
        
        # Restore previous state
        prev_state = json.loads(self.undo_stack.pop())
        widgets = [WidgetConfig(**w) for w in prev_state['widgets']]
        self.scenes[self.current_scene] = SceneConfig(
            name=prev_state['name'],
            width=prev_state['width'],
            height=prev_state['height'],
            widgets=widgets,
            bg_color=prev_state.get('bg_color', 'black')
        )
        return True
    
    def redo(self) -> bool:
        """Redo last undone operation"""
        if not self.redo_stack or not self.current_scene:
            return False
        
        # Save current state to undo
        current_state = json.dumps(asdict(self.scenes[self.current_scene]))
        self.undo_stack.append(current_state)
        
        # Restore next state
        next_state = json.loads(self.redo_stack.pop())
        widgets = [WidgetConfig(**w) for w in next_state['widgets']]
        self.scenes[self.current_scene] = SceneConfig(
            name=next_state['name'],
            width=next_state['width'],
            height=next_state['height'],
            widgets=widgets,
            bg_color=next_state.get('bg_color', 'black')
        )
        return True
    
    def snap_position(self, x: int, y: int) -> Tuple[int, int]:
        """Snap coordinates to grid"""
        if self.snap_to_grid and self.grid_enabled:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size
        return x, y
    
    def create_scene(self, name: str) -> SceneConfig:
        """Create new scene"""
        scene = SceneConfig(
            name=name,
            width=self.width,
            height=self.height,
            widgets=[]
        )
        self.scenes[name] = scene
        self.current_scene = name
        return scene
    
    def add_widget(self, widget, scene_name: Optional[str] = None, **kwargs):
        """Add widget to scene.

        Accepts either a WidgetConfig instance (existing behavior) or a widget type
        (WidgetType or str) with keyword args like x, y, width, height, text, etc.
        """
        # Normalize input to WidgetConfig
        if isinstance(widget, WidgetConfig):
            new_widget = widget
        else:
            # Determine widget type string
            if isinstance(widget, WidgetType):
                wtype = widget.value
            else:
                wtype = str(widget)

            # Required fields
            try:
                x = int(kwargs.get('x'))
                y = int(kwargs.get('y'))
                width = int(kwargs.get('width'))
                height = int(kwargs.get('height'))
            except Exception as e:
                raise TypeError("add_widget requires x, y, width, height when providing a type") from e

            # Build WidgetConfig with optional fields
            new_widget = WidgetConfig(
                type=wtype,
                x=x,
                y=y,
                width=width,
                height=height,
                text=kwargs.get('text', ''),
                style=kwargs.get('style', 'default'),
                color_fg=kwargs.get('color_fg', 'white'),
                color_bg=kwargs.get('color_bg', 'black'),
                border=bool(kwargs.get('border', True)),
                border_style=str(kwargs.get('border_style', 'single')),
                align=str(kwargs.get('align', 'left')),
                valign=str(kwargs.get('valign', 'middle')),
                value=int(kwargs.get('value', 0)) if kwargs.get('value') is not None else 0,
                min_value=int(kwargs.get('min_value', 0)),
                max_value=int(kwargs.get('max_value', 100)),
                checked=bool(kwargs.get('checked', False)),
                enabled=bool(kwargs.get('enabled', True)),
                visible=bool(kwargs.get('visible', True)),
                icon_char=str(kwargs.get('icon_char', '')),
                data_points=list(kwargs.get('data_points', [])),
                z_index=int(kwargs.get('z_index', 0)),
                padding_x=int(kwargs.get('padding_x', 1)),
                padding_y=int(kwargs.get('padding_y', 0)),
                margin_x=int(kwargs.get('margin_x', 0)),
                margin_y=int(kwargs.get('margin_y', 0)),
            )

        self._save_state()
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            # Snap to grid if enabled
            new_widget.x, new_widget.y = self.snap_position(new_widget.x, new_widget.y)
            self.scenes[scene_name].widgets.append(new_widget)
    
    def add_widget_from_template(self, template_name: str, widget_id: str,
                                 x: int, y: int, **kwargs):
        """Add widget from template with custom properties"""
        if template_name not in self.templates:
            print(f"❌ Template '{template_name}' not found")
            return
        
        # Deep copy template and update properties
        widget = copy.deepcopy(self.templates[template_name])
        widget.x = x
        widget.y = y
        
        # Update with any additional properties
        for key, value in kwargs.items():
            if hasattr(widget, key):
                setattr(widget, key, value)
        
        # Add to scene
        self.add_widget(widget)
    
    def clone_widget(self, widget_idx: int, offset_x: int = 10, offset_y: int = 10,
                     scene_name: Optional[str] = None):
        """Clone existing widget"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                self._save_state()
                cloned = copy.deepcopy(scene.widgets[widget_idx])
                cloned.x += offset_x
                cloned.y += offset_y
                scene.widgets.append(cloned)
    
    def move_widget(self, widget_idx: int, dx: int, dy: int, scene_name: Optional[str] = None):
        """Move widget by delta"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                widget = scene.widgets[widget_idx]
                widget.x = max(0, min(self.width - widget.width, widget.x + dx))
                widget.y = max(0, min(self.height - widget.height, widget.y + dy))
    
    def resize_widget(self, widget_idx: int, dw: int, dh: int, scene_name: Optional[str] = None):
        """Resize widget by delta"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                widget = scene.widgets[widget_idx]
                widget.width = max(1, widget.width + dw)
                widget.height = max(1, widget.height + dh)
    
    def delete_widget(self, widget_idx: int, scene_name: Optional[str] = None):
        """Delete widget"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                del scene.widgets[widget_idx]
    
    def save_to_json(self, filename: str):
        """Save design to JSON file"""
        data = {
            "width": self.width,
            "height": self.height,
            "scenes": {
                name: {
                    "name": scene.name,
                    "width": scene.width,
                    "height": scene.height,
                    "bg_color": scene.bg_color,
                    "widgets": [asdict(w) for w in scene.widgets]
                }
                for name, scene in self.scenes.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Design saved: {filename}")
    
    def load_from_json(self, filename: str):
        """Load design from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.width = data.get("width", 128)
        self.height = data.get("height", 64)
        self.scenes = {}
        
        for name, scene_data in data.get("scenes", {}).items():
            widgets = [WidgetConfig(**w) for w in scene_data.get("widgets", [])]
            scene = SceneConfig(
                name=scene_data["name"],
                width=scene_data["width"],
                height=scene_data["height"],
                widgets=widgets,
                bg_color=scene_data.get("bg_color", "black")
            )
            self.scenes[name] = scene
        
        if self.scenes:
            self.current_scene = list(self.scenes.keys())[0]
        
        print(f"📂 Design loaded: {filename}")
    
    def generate_python_code(self, scene_name: Optional[str] = None) -> str:
        """Generate Python code for scene"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return ""
        
        scene = self.scenes[scene_name]
        
        code_lines = [
            "# Auto-generated by UI Designer",
            f"# Scene: {scene.name}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "from dataclasses import dataclass",
            "from typing import List",
            "",
            "",
            "@dataclass",
            "class Widget:",
            "    type: str",
            "    x: int",
            "    y: int",
            "    width: int",
            "    height: int",
            "    text: str = ''",
            "    style: str = 'default'",
            "    color_fg: str = 'white'",
            "    color_bg: str = 'black'",
            "    border: bool = True",
            "    align: str = 'left'",
            "",
            "",
            f"def create_{scene.name.lower()}_scene() -> List[Widget]:",
            f'    """Create {scene.name} scene widgets"""',
            "    return [",
        ]
        
        for widget in scene.widgets:
            code_lines.append(f"        Widget(")
            code_lines.append(f"            type='{widget.type}',")
            code_lines.append(f"            x={widget.x},")
            code_lines.append(f"            y={widget.y},")
            code_lines.append(f"            width={widget.width},")
            code_lines.append(f"            height={widget.height},")
            if widget.text:
                code_lines.append(f"            text='{widget.text}',")
            if widget.style != 'default':
                code_lines.append(f"            style='{widget.style}',")
            if widget.color_fg != 'white':
                code_lines.append(f"            color_fg='{widget.color_fg}',")
            if widget.color_bg != 'black':
                code_lines.append(f"            color_bg='{widget.color_bg}',")
            if not widget.border:
                code_lines.append(f"            border={widget.border},")
            if widget.align != 'left':
                code_lines.append(f"            align='{widget.align}',")
            code_lines.append("        ),")
        
        code_lines.append("    ]")
        code_lines.append("")
        code_lines.append("")
        code_lines.append("if __name__ == '__main__':")
        code_lines.append(f"    widgets = create_{scene.name.lower()}_scene()")
        code_lines.append(f"    print(f'Created {{len(widgets)}} widgets for {scene.name} scene')")
        
        return '\n'.join(code_lines)
    
    def export_code(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as Python code file"""
        code = self.generate_python_code(scene_name)
        
        with open(filename, 'w') as f:
            f.write(code)
        
        print(f"🐍 Code exported: {filename}")
    
    def auto_layout(self, layout_type: str = 'vertical', spacing: int = 4,
                    scene_name: Optional[str] = None):
        """Auto-arrange widgets in scene"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        self._save_state()
        scene = self.scenes[scene_name]
        
        if layout_type == 'vertical':
            y_offset = spacing
            for widget in scene.widgets:
                widget.x = (scene.width - widget.width) // 2
                widget.y = y_offset
                y_offset += widget.height + spacing
        
        elif layout_type == 'horizontal':
            x_offset = spacing
            for widget in scene.widgets:
                widget.x = x_offset
                widget.y = (scene.height - widget.height) // 2
                x_offset += widget.width + spacing
        
        elif layout_type == 'grid':
            cols = int((scene.width + spacing) / (40 + spacing))  # Assume 40px avg width
            x_offset = spacing
            y_offset = spacing
            col = 0
            
            for widget in scene.widgets:
                widget.x = x_offset
                widget.y = y_offset
                
                col += 1
                x_offset += widget.width + spacing
                
                if col >= cols:
                    col = 0
                    x_offset = spacing
                    y_offset += 30 + spacing  # Assume 30px avg height
    
    def align_widgets(self, alignment: str, widget_indices: List[int],
                      scene_name: Optional[str] = None):
        """Align selected widgets"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        self._save_state()
        scene = self.scenes[scene_name]
        
        if not widget_indices:
            return
        
        widgets = [scene.widgets[i] for i in widget_indices if 0 <= i < len(scene.widgets)]
        
        if alignment == 'left':
            min_x = min(w.x for w in widgets)
            for w in widgets:
                w.x = min_x
        
        elif alignment == 'right':
            max_x = max(w.x + w.width for w in widgets)
            for w in widgets:
                w.x = max_x - w.width
        
        elif alignment == 'top':
            min_y = min(w.y for w in widgets)
            for w in widgets:
                w.y = min_y
        
        elif alignment == 'bottom':
            max_y = max(w.y + w.height for w in widgets)
            for w in widgets:
                w.y = max_y - w.height
        
        elif alignment == 'center_h':
            avg_x = sum(w.x + w.width // 2 for w in widgets) // len(widgets)
            for w in widgets:
                w.x = avg_x - w.width // 2
        
        elif alignment == 'center_v':
            avg_y = sum(w.y + w.height // 2 for w in widgets) // len(widgets)
            for w in widgets:
                w.y = avg_y - w.height // 2
    
    def distribute_widgets(self, direction: str, widget_indices: List[int],
                           scene_name: Optional[str] = None):
        """Distribute widgets evenly"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        self._save_state()
        scene = self.scenes[scene_name]
        
        if len(widget_indices) < 2:
            return
        
        widgets = [(i, scene.widgets[i]) for i in widget_indices if 0 <= i < len(scene.widgets)]
        
        if direction == 'horizontal':
            widgets.sort(key=lambda w: w[1].x)
            start_x = widgets[0][1].x
            end_x = widgets[-1][1].x + widgets[-1][1].width
            total_width = sum(w[1].width for w in widgets)
            spacing = (end_x - start_x - total_width) / (len(widgets) - 1)
            
            x_pos = start_x
            for _, widget in widgets:
                widget.x = int(x_pos)
                x_pos += widget.width + spacing
        
        elif direction == 'vertical':
            widgets.sort(key=lambda w: w[1].y)
            start_y = widgets[0][1].y
            end_y = widgets[-1][1].y + widgets[-1][1].height
            total_height = sum(w[1].height for w in widgets)
            spacing = (end_y - start_y - total_height) / (len(widgets) - 1)
            
            y_pos = start_y
            for _, widget in widgets:
                widget.y = int(y_pos)
                y_pos += widget.height + spacing
    
    def export_to_html(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as HTML preview"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        scene = self.scenes[scene_name]
        preview = self.preview_ascii(scene_name)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{scene.name} - UI Design Preview</title>
    <style>
        body {{
            background: #1a1a1a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            padding: 20px;
        }}
        .preview {{
            background: #000;
            border: 2px solid #00ff00;
            padding: 20px;
            display: inline-block;
            white-space: pre;
            line-height: 1.2;
        }}
        .info {{
            margin-top: 20px;
            color: #00ffff;
        }}
    </style>
</head>
<body>
    <h1>🎨 {scene.name}</h1>
    <div class="preview">{preview}</div>
    <div class="info">
        <p>Size: {scene.width} × {scene.height}</p>
        <p>Widgets: {len(scene.widgets)}</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"🌐 HTML preview exported: {filename}")
    
    def preview_ascii(self, scene_name: Optional[str] = None, show_grid: bool = False) -> str:
        """Generate ASCII preview of scene with enhanced rendering"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return ""
        
        scene = self.scenes[scene_name]
        
        # Create canvas
        canvas = [[' ' for _ in range(scene.width)] for _ in range(scene.height)]
        
        # Draw grid if enabled
        if show_grid and self.grid_enabled:
            for y in range(0, scene.height, self.grid_size):
                for x in range(0, scene.width, self.grid_size):
                    if x < scene.width and y < scene.height:
                        canvas[y][x] = '·'
        
        # Sort widgets by z_index
        sorted_widgets = sorted(enumerate(scene.widgets), key=lambda w: w[1].z_index)
        
        # Draw widgets
        for idx, widget in sorted_widgets:
            if not widget.visible:
                continue
            
            self._render_widget_to_canvas(canvas, widget, idx, scene.width, scene.height)
        
        # Convert to string
        lines = [''.join(row) for row in canvas]
        return '\n'.join(lines)
    
    def _render_widget_to_canvas(self, canvas: List[List[str]], widget: WidgetConfig, 
                                 idx: int, width: int, height: int):
        """Render single widget to canvas"""
        # Get border characters based on style
        border_chars = self._get_border_chars(widget.border_style)
        
        # Draw border
        if widget.border:
            # Top/bottom
            for x in range(widget.x, min(widget.x + widget.width, width)):
                if widget.y < height:
                    canvas[widget.y][x] = border_chars['h']
                if widget.y + widget.height - 1 < height:
                    canvas[widget.y + widget.height - 1][x] = border_chars['h']
            
            # Left/right
            for y in range(widget.y, min(widget.y + widget.height, height)):
                if widget.x < width:
                    canvas[y][widget.x] = border_chars['v']
                if widget.x + widget.width - 1 < width:
                    canvas[y][widget.x + widget.width - 1] = border_chars['v']
            
            # Corners
            if widget.y < height and widget.x < width:
                canvas[widget.y][widget.x] = border_chars['tl']
            if widget.y < height and widget.x + widget.width - 1 < width:
                canvas[widget.y][widget.x + widget.width - 1] = border_chars['tr']
            if widget.y + widget.height - 1 < height and widget.x < width:
                canvas[widget.y + widget.height - 1][widget.x] = border_chars['bl']
            if widget.y + widget.height - 1 < height and widget.x + widget.width - 1 < width:
                canvas[widget.y + widget.height - 1][widget.x + widget.width - 1] = border_chars['br']
        
        # Draw widget-specific content
        if widget.type == 'progressbar':
            self._draw_progressbar(canvas, widget, width, height)
        elif widget.type == 'gauge':
            self._draw_gauge(canvas, widget, width, height)
        elif widget.type == 'checkbox':
            self._draw_checkbox(canvas, widget, width, height)
        elif widget.type == 'slider':
            self._draw_slider(canvas, widget, width, height)
        elif widget.type == 'chart':
            self._draw_chart(canvas, widget, width, height)
        else:
            # Draw text for label, button, etc.
            if widget.text:
                self._draw_text(canvas, widget, width, height)
        
        # Draw widget index (top-left corner inside border)
        num_str = str(idx)
        num_y = widget.y if not widget.border else widget.y + 1
        num_x = widget.x + 1
        if 0 <= num_y < height:
            for i, ch in enumerate(num_str):
                x = num_x + i
                if 0 <= x < width:
                    canvas[num_y][x] = ch
    
    def _get_border_chars(self, style: str) -> Dict[str, str]:
        """Get border characters for style"""
        styles = {
            'single': {'h': '─', 'v': '│', 'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘'},
            'double': {'h': '═', 'v': '║', 'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝'},
            'rounded': {'h': '─', 'v': '│', 'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯'},
            'bold': {'h': '━', 'v': '┃', 'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛'},
            'dashed': {'h': '┄', 'v': '┆', 'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘'},
        }
        return styles.get(style, styles['single'])
    
    def _draw_text(self, canvas: List[List[str]], widget: WidgetConfig, 
                   width: int, height: int):
        """Draw text with alignment"""
        text_y = widget.y + widget.height // 2
        if widget.valign == 'top':
            text_y = widget.y + (1 if widget.border else 0) + widget.padding_y
        elif widget.valign == 'bottom':
            text_y = widget.y + widget.height - (1 if widget.border else 0) - widget.padding_y - 1
        
        text_x = widget.x + widget.padding_x + (1 if widget.border else 0)
        
        if widget.align == 'center':
            text_x = widget.x + (widget.width - len(widget.text)) // 2
        elif widget.align == 'right':
            text_x = widget.x + widget.width - len(widget.text) - widget.padding_x - (1 if widget.border else 0)
        
        if 0 <= text_y < height:
            for i, ch in enumerate(widget.text):
                x = text_x + i
                if 0 <= x < width:
                    canvas[text_y][x] = ch
    
    def _draw_progressbar(self, canvas: List[List[str]], widget: WidgetConfig,
                          width: int, height: int):
        """Draw progress bar"""
        inner_width = widget.width - (2 if widget.border else 0)
        progress = int((widget.value / max(widget.max_value, 1)) * inner_width)
        
        bar_y = widget.y + widget.height // 2
        bar_x_start = widget.x + (1 if widget.border else 0)
        
        if 0 <= bar_y < height:
            for i in range(inner_width):
                x = bar_x_start + i
                if 0 <= x < width:
                    canvas[bar_y][x] = '█' if i < progress else '░'
    
    def _draw_gauge(self, canvas: List[List[str]], widget: WidgetConfig,
                    width: int, height: int):
        """Draw gauge (simple bar)"""
        inner_height = widget.height - (2 if widget.border else 0)
        progress = int((widget.value / max(widget.max_value, 1)) * inner_height)
        
        gauge_x = widget.x + widget.width // 2
        gauge_y_start = widget.y + widget.height - (1 if widget.border else 0) - 1
        
        for i in range(inner_height):
            y = gauge_y_start - i
            if 0 <= y < height and 0 <= gauge_x < width:
                canvas[y][gauge_x] = '█' if i < progress else '░'
    
    def _draw_checkbox(self, canvas: List[List[str]], widget: WidgetConfig,
                       width: int, height: int):
        """Draw checkbox"""
        check_y = widget.y + widget.height // 2
        check_x = widget.x + (1 if widget.border else 0) + 1
        
        if 0 <= check_y < height and 0 <= check_x < width:
            canvas[check_y][check_x] = '☑' if widget.checked else '☐'
        
        # Draw label if text exists
        if widget.text and 0 <= check_y < height:
            text_x = check_x + 2
            for i, ch in enumerate(widget.text):
                x = text_x + i
                if 0 <= x < width:
                    canvas[check_y][x] = ch
    
    def _draw_slider(self, canvas: List[List[str]], widget: WidgetConfig,
                     width: int, height: int):
        """Draw slider"""
        inner_width = widget.width - (2 if widget.border else 0)
        slider_pos = int((widget.value / max(widget.max_value, 1)) * (inner_width - 1))
        
        slider_y = widget.y + widget.height // 2
        slider_x_start = widget.x + (1 if widget.border else 0)
        
        if 0 <= slider_y < height:
            for i in range(inner_width):
                x = slider_x_start + i
                if 0 <= x < width:
                    if i == slider_pos:
                        canvas[slider_y][x] = '▓'
                    else:
                        canvas[slider_y][x] = '─'
    
    def _draw_chart(self, canvas: List[List[str]], widget: WidgetConfig,
                    width: int, height: int):
        """Draw simple chart"""
        if not widget.data_points:
            return
        
        inner_width = widget.width - (2 if widget.border else 0)
        inner_height = widget.height - (2 if widget.border else 0)
        
        # Normalize data points
        max_val = max(widget.data_points) if widget.data_points else 1
        
        chart_x_start = widget.x + (1 if widget.border else 0)
        chart_y_start = widget.y + (1 if widget.border else 0)
        
        # Draw bars
        for i, val in enumerate(widget.data_points[:inner_width]):
            bar_height = int((val / max(max_val, 1)) * inner_height)
            x = chart_x_start + i
            
            for j in range(bar_height):
                y = chart_y_start + inner_height - 1 - j
                if 0 <= y < height and 0 <= x < width:
                    canvas[y][x] = '▌'


def create_cli_interface():
    """Advanced CLI interface for UI designer"""
    designer = UIDesigner(128, 64)
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   ESP32 UI Designer - Advanced CLI Mode                  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print("📐 Scene Management:")
    print("  new <name>              - Create new scene")
    print("  list                    - List widgets in current scene")
    print("  scenes                  - List all scenes")
    print("  switch <name>           - Switch to scene")
    print()
    print("🎨 Widget Operations:")
    print("  add <type> <x> <y> <w> <h> [text]    - Add widget")
    print("  template <name> <x> <y>              - Add from template")
    print("  clone <idx> [offset_x] [offset_y]    - Clone widget")
    print("  move <idx> <dx> <dy>                 - Move widget")
    print("  resize <idx> <dw> <dh>               - Resize widget")
    print("  delete <idx>                         - Delete widget")
    print("  edit <idx> <prop> <value>            - Edit property")
    print()
    print("🎯 Advanced Features:")
    print("  undo                    - Undo last operation")
    print("  redo                    - Redo operation")
    print("  grid <on|off>           - Toggle grid")
    print("  snap <on|off>           - Toggle snap to grid")
    print("  preview [grid]          - Show ASCII preview")
    print("  templates               - List available templates")
    print("  layout <type>           - Auto-layout (vertical/horizontal/grid)")
    print("  align <type> <ids...>   - Align widgets (left/right/top/bottom/center_h/center_v)")
    print("  distribute <dir> <ids...> - Distribute evenly (horizontal/vertical)")
    print()
    print("💾 File Operations:")
    print("  save <file>             - Save to JSON")
    print("  load <file>             - Load from JSON")
    print("  export <file>           - Export Python code")
    print()
    print("❓ Help & Info:")
    print("  help [command]          - Show help")
    print("  widgets                 - List available widget types")
    print("  quit                    - Exit")
    print()
    print("💡 Widget types: label, box, button, gauge, progressbar,")
    print("   checkbox, radiobutton, slider, textbox, panel, icon, chart")
    print()
    
    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            
            # Split command preserving quotes
            import shlex
            try:
                parts = shlex.split(cmd)
            except ValueError:
                parts = cmd.split()
            
            if not parts:
                continue
            
            action = parts[0].lower()
            
            # Scene Management
            if action == 'quit' or action == 'exit':
                break
            
            elif action == 'new':
                if len(parts) < 2:
                    print("Usage: new <scene_name>")
                    continue
                designer.create_scene(parts[1])
                print(f"✓ Created scene: {parts[1]}")
            
            elif action == 'scenes':
                if designer.scenes:
                    print("\n📋 Available scenes:")
                    for name in designer.scenes:
                        marker = " (current)" if name == designer.current_scene else ""
                        print(f"  - {name}{marker}")
                else:
                    print("No scenes created")
            
            elif action == 'switch':
                if len(parts) < 2:
                    print("Usage: switch <scene_name>")
                    continue
                if parts[1] in designer.scenes:
                    designer.current_scene = parts[1]
                    print(f"✓ Switched to scene: {parts[1]}")
                else:
                    print(f"❌ Scene '{parts[1]}' not found")
            
            # Widget Operations
            elif action == 'add':
                if len(parts) < 6:
                    print("Usage: add <type> <x> <y> <w> <h> [text]")
                    continue
                
                widget = WidgetConfig(
                    type=parts[1],
                    x=int(parts[2]),
                    y=int(parts[3]),
                    width=int(parts[4]),
                    height=int(parts[5]),
                    text=' '.join(parts[6:]) if len(parts) > 6 else ""
                )
                designer.add_widget(widget)
                print(f"✓ Added {widget.type} widget")
            
            elif action == 'template':
                if len(parts) < 5:
                    print("Usage: template <name> <id> <x> <y>")
                    continue
                designer.add_widget_from_template(parts[1], parts[2], int(parts[3]), int(parts[4]))
                print(f"✓ Added widget '{parts[2]}' from template: {parts[1]}")
            
            elif action == 'clone':
                if len(parts) < 2:
                    print("Usage: clone <idx> [offset_x] [offset_y]")
                    continue
                offset_x = int(parts[2]) if len(parts) > 2 else 10
                offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), offset_x, offset_y)
                print("✓ Widget cloned")
            
            elif action == 'move':
                if len(parts) < 4:
                    print("Usage: move <idx> <dx> <dy>")
                    continue
                designer.move_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("✓ Widget moved")
            
            elif action == 'resize':
                if len(parts) < 4:
                    print("Usage: resize <idx> <dw> <dh>")
                    continue
                designer.resize_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("✓ Widget resized")
            
            elif action == 'delete':
                if len(parts) < 2:
                    print("Usage: delete <idx>")
                    continue
                designer.delete_widget(int(parts[1]))
                print("✓ Widget deleted")
            
            elif action == 'edit':
                if len(parts) < 4:
                    print("Usage: edit <idx> <property> <value>")
                    continue
                idx = int(parts[1])
                prop = parts[2]
                value = ' '.join(parts[3:])
                
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= idx < len(scene.widgets):
                        # Save state before edit
                        state = json.dumps(asdict(scene))
                        designer.undo_stack.append(state)
                        designer.redo_stack.clear()
                        
                        widget = scene.widgets[idx]
                        
                        # Set property
                        if prop in ['x', 'y', 'width', 'height', 'value', 'min_value', 'max_value', 'z_index']:
                            setattr(widget, prop, int(value))
                        elif prop in ['checked', 'enabled', 'visible', 'border']:
                            setattr(widget, prop, value.lower() in ['true', '1', 'yes'])
                        else:
                            setattr(widget, prop, value)
                        
                        print(f"✓ Updated {prop} = {value}")
            
            # Advanced Features
            elif action == 'undo':
                if designer.undo():
                    print("✓ Undone")
                else:
                    print("❌ Nothing to undo")
            
            elif action == 'redo':
                if designer.redo():
                    print("✓ Redone")
                else:
                    print("❌ Nothing to redo")
            
            elif action == 'grid':
                if len(parts) < 2:
                    print(f"Grid is {'enabled' if designer.grid_enabled else 'disabled'}")
                elif parts[1].lower() in ['on', 'true', '1']:
                    designer.grid_enabled = True
                    print("✓ Grid enabled")
                else:
                    designer.grid_enabled = False
                    print("✓ Grid disabled")
            
            elif action == 'snap':
                if len(parts) < 2:
                    print(f"Snap to grid is {'enabled' if designer.snap_to_grid else 'disabled'}")
                elif parts[1].lower() in ['on', 'true', '1']:
                    designer.snap_to_grid = True
                    print("✓ Snap to grid enabled")
                else:
                    designer.snap_to_grid = False
                    print("✓ Snap to grid disabled")
            
            elif action == 'list':
                if designer.current_scene:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\n📋 Scene: {scene.name} ({scene.width}x{scene.height})")
                    print(f"Widgets: {len(scene.widgets)}\n")
                    for i, w in enumerate(scene.widgets):
                        border_info = f" border={w.border_style}" if w.border else ""
                        value_info = f" value={w.value}" if w.type in ['gauge', 'progressbar', 'slider'] else ""
                        print(f"  [{i}] {w.type:12s} pos=({w.x:3d},{w.y:3d}) size={w.width:3d}x{w.height:3d}{border_info}{value_info}")
                        if w.text:
                            print(f"       text='{w.text}'")
                else:
                    print("No scene loaded")
            
            elif action == 'preview':
                show_grid = len(parts) > 1 and parts[1].lower() == 'grid'
                print("\n" + designer.preview_ascii(show_grid=show_grid))
                print()
            
            elif action == 'templates':
                print("\n📦 Available templates:")
                for name, template in designer.templates.items():
                    print(f"  {name:20s} - {template.type} {template.width}x{template.height}")
                print()
            
            elif action == 'widgets':
                print("\n🎨 Available widget types:")
                for wtype in WidgetType:
                    print(f"  - {wtype.value}")
                print()
            
            # File Operations
            elif action == 'save':
                if len(parts) < 2:
                    print("Usage: save <file>")
                    continue
                designer.save_to_json(parts[1])
            
            elif action == 'load':
                if len(parts) < 2:
                    print("Usage: load <file>")
                    continue
                designer.load_from_json(parts[1])
            
            elif action == 'export':
                if len(parts) < 2:
                    print("Usage: export <file> [html]")
                    continue
                if len(parts) > 2 and parts[2].lower() == 'html':
                    designer.export_to_html(parts[1])
                else:
                    designer.export_code(parts[1])
            
            elif action == 'layout':
                if len(parts) < 2:
                    print("Usage: layout <vertical|horizontal|grid> [spacing]")
                    continue
                spacing = int(parts[2]) if len(parts) > 2 else 4
                designer.auto_layout(parts[1], spacing)
                print(f"✓ Applied {parts[1]} layout")
            
            elif action == 'align':
                if len(parts) < 3:
                    print("Usage: align <left|right|top|bottom|center_h|center_v> <idx1> [idx2...]")
                    continue
                indices = [int(x) for x in parts[2:]]
                designer.align_widgets(parts[1], indices)
                print(f"✓ Aligned {len(indices)} widgets ({parts[1]})")
            
            elif action == 'distribute':
                if len(parts) < 4:
                    print("Usage: distribute <horizontal|vertical> <idx1> <idx2> [idx3...]")
                    continue
                indices = [int(x) for x in parts[2:]]
                designer.distribute_widgets(parts[1], indices)
                print(f"✓ Distributed {len(indices)} widgets ({parts[1]})")
            
            elif action == 'help':
                if len(parts) > 1:
                    show_command_help(parts[1])
                else:
                    print("Type command name for help. Available: add, template, edit, grid, layout, etc.")
            
            else:
                print(f"❌ Unknown command: {action}. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def show_command_help(command: str):
    """Show detailed help for specific command"""
    helps = {
        'add': """
Add widget: add <type> <x> <y> <w> <h> [text]
  Examples:
    add label 10 10 100 10 "Hello World"
    add button 20 30 40 12 "Click Me"
    add progressbar 10 50 100 8
    add gauge 60 20 40 30
        """,
        'template': """
Add from template: template <name> <x> <y>
  Available templates: title_label, button_primary, button_secondary,
                       info_panel, progress_bar, gauge_half
  Example: template button_primary 20 30
        """,
        'edit': """
Edit widget property: edit <idx> <property> <value>
  Properties: text, value, checked, border_style, color_fg, color_bg,
             align, valign, z_index, enabled, visible
  Examples:
    edit 0 text "New Text"
    edit 1 value 75
    edit 2 border_style double
    edit 3 color_fg cyan
        """,
    }
    print(helps.get(command, f"No detailed help for '{command}'"))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        print("🌐 Web interface not yet implemented")
        print("   Use CLI mode for now")
    else:
        create_cli_interface()
