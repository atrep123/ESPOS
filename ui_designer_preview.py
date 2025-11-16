#!/usr/bin/env python3
"""
Visual Preview Window for UI Designer
Real-time graphical preview with mouse interaction and export
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk
import json
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from ui_designer import UIDesigner, WidgetConfig, WidgetType, BorderStyle
from ui_animations import AnimationDesigner


@dataclass
class PreviewSettings:
    """Preview window settings"""
    zoom: float = 4.0  # 4x zoom by default
    grid_enabled: bool = True
    grid_size: int = 8
    snap_enabled: bool = True
    snap_size: int = 4
    show_bounds: bool = True
    show_handles: bool = True
    background_color: str = "#000000"
    pixel_perfect: bool = True


class VisualPreviewWindow:
    """Graphical preview window with mouse interaction"""
    
    def __init__(self, designer: UIDesigner):
        self.designer = designer
        self.settings = PreviewSettings()
        self.anim = AnimationDesigner()
        self.playing = False
        self.selected_anim: Optional[str] = None
        # Per-animation current values and per-widget overlay transform cache
        self._anim_values: Dict[str, Dict[str, Any]] = {}
        self._widget_overlays: Dict[int, Dict[str, Any]] = {}
        
        # Selection and drag state
        self.selected_widget_idx: Optional[int] = None
        self.dragging = False
        self.drag_start: Optional[Tuple[int, int]] = None
        self.drag_offset: Optional[Tuple[int, int]] = None
        self.resize_handle: Optional[str] = None  # ne, nw, se, sw, n, s, e, w
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"UI Designer Preview - {designer.width}×{designer.height}")
        self.root.configure(bg="#2b2b2b")
        
        # Setup UI
        self._setup_ui()
        self._setup_bindings()
        
        # Initial render
        self.refresh()
        # Kick animation timer
        self._schedule_tick()
    
    def _setup_ui(self):
        """Setup UI components"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Zoom controls
        ttk.Label(toolbar, text="Zoom:").pack(side=tk.LEFT, padx=5)
        zoom_var = tk.StringVar(value=f"{self.settings.zoom:.1f}x")
        zoom_combo = ttk.Combobox(toolbar, textvariable=zoom_var, width=6,
                                  values=["1.0x", "2.0x", "4.0x", "6.0x", "8.0x", "10.0x"])
        zoom_combo.pack(side=tk.LEFT, padx=5)
        zoom_combo.bind("<<ComboboxSelected>>", self._on_zoom_change)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Grid toggle
        self.grid_var = tk.BooleanVar(value=self.settings.grid_enabled)
        ttk.Checkbutton(toolbar, text="Grid", variable=self.grid_var,
                       command=self._on_grid_toggle).pack(side=tk.LEFT, padx=5)
        
        # Snap toggle
        self.snap_var = tk.BooleanVar(value=self.settings.snap_enabled)
        ttk.Checkbutton(toolbar, text="Snap", variable=self.snap_var,
                       command=self._on_snap_toggle).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Export button
        ttk.Button(toolbar, text="📷 Export PNG", 
                  command=self._export_png).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", 
                  command=self.refresh).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Animation controls
        ttk.Label(toolbar, text="Animation:").pack(side=tk.LEFT, padx=5)
        self.anim_combo = ttk.Combobox(toolbar, values=self.anim.list_animations(), width=14)
        if self.anim.list_animations():
            self.anim_combo.set(self.anim.list_animations()[0])
            self.selected_anim = self.anim.list_animations()[0]
        self.anim_combo.pack(side=tk.LEFT)
        self.anim_combo.bind("<<ComboboxSelected>>", self._on_anim_change)
        ttk.Button(toolbar, text="▶ Play", command=self._on_anim_play).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⏸ Pause", command=self._on_anim_pause).pack(side=tk.LEFT, padx=2)
        
        # Background color
        ttk.Button(toolbar, text="🎨 BG Color", 
                  command=self._choose_bg_color).pack(side=tk.LEFT, padx=5)
        
        # Canvas frame with scrollbars
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas
        canvas_width = int(self.designer.width * self.settings.zoom)
        canvas_height = int(self.designer.height * self.settings.zoom)
        
        self.canvas = tk.Canvas(canvas_frame, 
                               width=canvas_width, 
                               height=canvas_height,
                               bg="#1e1e1e",
                               highlightthickness=1,
                               highlightbackground="#444")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X, padx=5)
        
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Properties panel
        self._setup_properties_panel()
    
    def _setup_properties_panel(self):
        """Setup widget properties panel"""
        props_window = tk.Toplevel(self.root)
        props_window.title("Widget Properties")
        props_window.geometry("300x500")
        props_window.configure(bg="#2b2b2b")
        
        # Make it stay on top but not modal
        props_window.attributes("-topmost", False)
        
        self.props_frame = ttk.Frame(props_window, padding=10)
        self.props_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.props_frame, text="No widget selected").pack()
        
        self.props_window = props_window
    
    def _setup_bindings(self):
        """Setup mouse and keyboard bindings"""
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        
        # Keyboard shortcuts
        self.root.bind("<Delete>", self._on_delete_widget)
        self.root.bind("<Control-z>", lambda e: self.designer.undo())
        self.root.bind("<Control-y>", lambda e: self.designer.redo())
        self.root.bind("<Control-s>", self._on_save)
    
    def refresh(self):
        """Refresh the preview"""
        self.canvas.delete("all")
        
        if not self.designer.current_scene:
            return
        
        # Get current scene
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        # Create image for pixel-perfect rendering
        img_width = self.designer.width
        img_height = self.designer.height
        
        # Create PIL image
        bg_color = self._hex_to_rgb(self.settings.background_color)
        img = Image.new("RGB", (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw grid if enabled
        if self.settings.grid_enabled:
            self._draw_grid(draw, img_width, img_height)
        
        # Draw widgets
        for idx, widget in enumerate(scene.widgets):
            if not widget.visible:
                continue
            overlay = self._widget_overlays.get(idx, {})
            self._draw_widget(draw, widget, idx == self.selected_widget_idx, overlay)
        
        # Scale image
        scaled_width = int(img_width * self.settings.zoom)
        scaled_height = int(img_height * self.settings.zoom)
        img_scaled = img.resize((scaled_width, scaled_height), Image.NEAREST)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(img_scaled)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Update canvas scroll region
        self.canvas.configure(scrollregion=(0, 0, scaled_width, scaled_height))
        
        # Draw selection handles
        if self.selected_widget_idx is not None and self.settings.show_handles:
            self._draw_selection_handles()
        
        # Update status
        widget_count = len(scene.widgets)
        selected_info = ""
        if self.selected_widget_idx is not None:
            w = scene.widgets[self.selected_widget_idx]
            selected_info = f" | Selected: {w.type} at ({w.x},{w.y}) {w.width}×{w.height}"
        self.status_bar.configure(text=f"Widgets: {widget_count} | Zoom: {self.settings.zoom:.1f}x{selected_info}")
    
    def _draw_grid(self, draw: ImageDraw.ImageDraw, width: int, height: int):
        """Draw grid on canvas"""
        grid_color = (40, 40, 40)
        for x in range(0, width, self.settings.grid_size):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, self.settings.grid_size):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    
    def _draw_widget(self, draw: ImageDraw.ImageDraw, widget: WidgetConfig, selected: bool, overlay: Optional[Dict[str, Any]] = None):
        """Draw a widget on the image"""
        x, y = widget.x, widget.y
        w, h = widget.width, widget.height
        if overlay:
            # Position offsets or absolute move
            if 'x' in overlay:
                x = int(overlay['x'])
            if 'y' in overlay:
                y = int(overlay['y'])
            if 'x_offset' in overlay:
                x += int(overlay['x_offset'])
            if 'y_offset' in overlay:
                y += int(overlay['y_offset'])
            # Scale around center
            if 'scale' in overlay:
                s = float(overlay['scale'])
                cx, cy = x + w // 2, y + h // 2
                w = max(1, int(w * s))
                h = max(1, int(h * s))
                x = cx - w // 2
                y = cy - h // 2
        
        # Widget colors
        fg_color = self._get_color(widget.color_fg)
        bg_color = self._get_color(widget.color_bg)
        
        # Draw background
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg_color)
        
        # Draw border
        if widget.border:
            border_color = fg_color
            if selected:
                border_color = (0, 150, 255)  # Blue for selection
            
            if widget.border_style == "single":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
            elif widget.border_style == "double":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
                draw.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], outline=border_color, width=1)
            elif widget.border_style == "bold":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=2)
            elif widget.border_style == "dashed":
                # Simplified dashed border
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
        
        # Draw widget-specific content
        if widget.type == WidgetType.LABEL.value:
            self._draw_text(draw, widget.text, x + widget.padding_x, y + widget.padding_y, 
                          w - 2 * widget.padding_x, h - 2 * widget.padding_y, 
                          fg_color, widget.align, widget.valign)
        
        elif widget.type == WidgetType.BUTTON.value:
            # Button with text centered
            self._draw_text(draw, widget.text, x, y, w, h, fg_color, "center", "middle")
        
        elif widget.type == WidgetType.CHECKBOX.value:
            # Draw checkbox
            box_size = min(h - 4, 6)
            box_x = x + 2
            box_y = y + (h - box_size) // 2
            draw.rectangle([box_x, box_y, box_x + box_size, box_y + box_size], 
                         outline=fg_color, width=1)
            if widget.checked:
                draw.line([(box_x + 1, box_y + 1), (box_x + box_size - 1, box_y + box_size - 1)], 
                         fill=fg_color, width=1)
                draw.line([(box_x + 1, box_y + box_size - 1), (box_x + box_size - 1, box_y + 1)], 
                         fill=fg_color, width=1)
            # Label
            if widget.text:
                self._draw_text(draw, widget.text, box_x + box_size + 2, y, 
                              w - box_size - 4, h, fg_color, "left", "middle")
        
        elif widget.type == WidgetType.PROGRESSBAR.value:
            # Draw progress bar
            progress = int((widget.value - widget.min_value) / 
                          (widget.max_value - widget.min_value) * (w - 4))
            if progress > 0:
                draw.rectangle([x + 2, y + 2, x + 2 + progress, y + h - 3], fill=fg_color)
        
        elif widget.type == WidgetType.GAUGE.value:
            # Draw gauge as arc (simplified)
            center_x = x + w // 2
            center_y = y + h // 2
            radius = min(w, h) // 2 - 2
            # Draw circle
            draw.ellipse([center_x - radius, center_y - radius, 
                         center_x + radius, center_y + radius], 
                        outline=fg_color, width=1)
            # Draw value text
            value_text = str(widget.value)
            self._draw_text(draw, value_text, x, y, w, h, fg_color, "center", "middle")
        
        elif widget.type == WidgetType.SLIDER.value:
            # Draw slider track
            track_y = y + h // 2
            draw.line([(x + 2, track_y), (x + w - 2, track_y)], fill=fg_color, width=1)
            # Draw handle
            handle_x = x + 2 + int((widget.value - widget.min_value) / 
                                  (widget.max_value - widget.min_value) * (w - 4))
            draw.rectangle([handle_x - 2, y + 2, handle_x + 2, y + h - 2], 
                          fill=fg_color, outline=fg_color)
        
        elif widget.type == WidgetType.BOX.value:
            # Just the border and background, already drawn
            pass
        
        elif widget.type == WidgetType.PANEL.value:
            # Panel with optional title
            if widget.text:
                self._draw_text(draw, widget.text, x + 2, y, w - 4, 8, fg_color, "left", "top")
    
    def _draw_text(self, draw: ImageDraw.ImageDraw, text: str, 
                   x: int, y: int, w: int, h: int, 
                   color: Tuple[int, int, int], 
                   align: str, valign: str):
        """Draw text with alignment"""
        if not text:
            return
        
        # Use default font (PIL's built-in)
        # Calculate text position based on alignment
        # Note: Simplified - real implementation would need proper font metrics
        char_width = 4  # Approximate monospace width
        char_height = 6  # Approximate height
        
        text_width = len(text) * char_width
        text_height = char_height
        
        # Horizontal alignment
        if align == "center":
            text_x = x + (w - text_width) // 2
        elif align == "right":
            text_x = x + w - text_width
        else:  # left
            text_x = x
        
        # Vertical alignment
        if valign == "middle":
            text_y = y + (h - text_height) // 2
        elif valign == "bottom":
            text_y = y + h - text_height
        else:  # top
            text_y = y
        
        # Draw text (simplified - PIL text is limited at small sizes)
        draw.text((text_x, text_y), text, fill=color)
    
    def _draw_selection_handles(self):
        """Draw resize handles for selected widget"""
        if self.selected_widget_idx is None:
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        widget = scene.widgets[self.selected_widget_idx]
        
        # Scale to canvas coordinates
        x = int(widget.x * self.settings.zoom)
        y = int(widget.y * self.settings.zoom)
        w = int(widget.width * self.settings.zoom)
        h = int(widget.height * self.settings.zoom)
        
        handle_size = 6
        handle_color = "#00AAFF"
        
        # Corner handles
        handles = [
            (x, y, "nw"),                    # Top-left
            (x + w, y, "ne"),                # Top-right
            (x + w, y + h, "se"),            # Bottom-right
            (x, y + h, "sw"),                # Bottom-left
            (x + w // 2, y, "n"),            # Top-center
            (x + w // 2, y + h, "s"),        # Bottom-center
            (x, y + h // 2, "w"),            # Left-center
            (x + w, y + h // 2, "e"),        # Right-center
        ]
        
        for hx, hy, handle_type in handles:
            self.canvas.create_rectangle(
                hx - handle_size // 2, hy - handle_size // 2,
                hx + handle_size // 2, hy + handle_size // 2,
                fill=handle_color, outline="white", width=1,
                tags=f"handle_{handle_type}"
            )
    
    def _get_color(self, color_name: str) -> Tuple[int, int, int]:
        """Convert color name to RGB tuple"""
        colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
            "gray": (128, 128, 128),
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
        }
        return colors.get(color_name.lower(), (255, 255, 255))
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _canvas_to_widget_coords(self, canvas_x: int, canvas_y: int) -> Tuple[int, int]:
        """Convert canvas coordinates to widget coordinates"""
        widget_x = int(canvas_x / self.settings.zoom)
        widget_y = int(canvas_y / self.settings.zoom)
        
        # Apply snapping
        if self.settings.snap_enabled:
            widget_x = round(widget_x / self.settings.snap_size) * self.settings.snap_size
            widget_y = round(widget_y / self.settings.snap_size) * self.settings.snap_size
        
        return widget_x, widget_y
    
    def _find_widget_at(self, x: int, y: int) -> Optional[int]:
        """Find widget at canvas coordinates"""
        if not self.designer.current_scene:
            return None
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return None
        
        # Convert to widget coordinates
        wx, wy = self._canvas_to_widget_coords(x, y)
        
        # Check widgets in reverse order (top to bottom)
        for idx in reversed(range(len(scene.widgets))):
            widget = scene.widgets[idx]
            if not widget.visible:
                continue
            
            if (widget.x <= wx < widget.x + widget.width and
                widget.y <= wy < widget.y + widget.height):
                return idx
        
        return None
    
    def _find_resize_handle(self, x: int, y: int) -> Optional[str]:
        """Find which resize handle is at position"""
        if self.selected_widget_idx is None:
            return None
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return None
        
        widget = scene.widgets[self.selected_widget_idx]
        
        # Convert to widget coordinates
        wx, wy = self._canvas_to_widget_coords(x, y)
        
        # Check handle positions (with some tolerance)
        tolerance = 3
        
        handles = [
            (widget.x, widget.y, "nw"),
            (widget.x + widget.width, widget.y, "ne"),
            (widget.x + widget.width, widget.y + widget.height, "se"),
            (widget.x, widget.y + widget.height, "sw"),
            (widget.x + widget.width // 2, widget.y, "n"),
            (widget.x + widget.width // 2, widget.y + widget.height, "s"),
            (widget.x, widget.y + widget.height // 2, "w"),
            (widget.x + widget.width, widget.y + widget.height // 2, "e"),
        ]
        
        for hx, hy, handle_type in handles:
            if abs(wx - hx) <= tolerance and abs(wy - hy) <= tolerance:
                return handle_type
        
        return None
    
    def _on_mouse_down(self, event):
        """Handle mouse down"""
        # Check for resize handle first
        handle = self._find_resize_handle(event.x, event.y)
        if handle:
            self.resize_handle = handle
            self.dragging = True
            self.drag_start = (event.x, event.y)
            return
        
        # Check for widget selection
        widget_idx = self._find_widget_at(event.x, event.y)
        if widget_idx is not None:
            self.selected_widget_idx = widget_idx
            self.dragging = True
            self.drag_start = (event.x, event.y)
            
            # Calculate offset for smooth dragging
            scene = self.designer.scenes.get(self.designer.current_scene)
            widget = scene.widgets[widget_idx]
            wx, wy = self._canvas_to_widget_coords(event.x, event.y)
            self.drag_offset = (wx - widget.x, wy - widget.y)
            
            self.refresh()
        else:
            self.selected_widget_idx = None
            self.refresh()
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag"""
        if not self.dragging or self.selected_widget_idx is None:
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        widget = scene.widgets[self.selected_widget_idx]
        
        if self.resize_handle:
            # Resize widget
            wx, wy = self._canvas_to_widget_coords(event.x, event.y)
            
            if 'n' in self.resize_handle:
                new_height = widget.y + widget.height - wy
                if new_height > 4:
                    widget.y = wy
                    widget.height = new_height
            if 's' in self.resize_handle:
                widget.height = max(4, wy - widget.y)
            if 'w' in self.resize_handle:
                new_width = widget.x + widget.width - wx
                if new_width > 4:
                    widget.x = wx
                    widget.width = new_width
            if 'e' in self.resize_handle:
                widget.width = max(4, wx - widget.x)
        else:
            # Move widget
            wx, wy = self._canvas_to_widget_coords(event.x, event.y)
            widget.x = wx - self.drag_offset[0]
            widget.y = wy - self.drag_offset[1]
            
            # Clamp to canvas
            widget.x = max(0, min(widget.x, self.designer.width - widget.width))
            widget.y = max(0, min(widget.y, self.designer.height - widget.height))
        
        self.refresh()
    
    def _on_mouse_up(self, event):
        """Handle mouse up"""
        if self.dragging:
            # Save state for undo
            self.designer._save_state()
        
        self.dragging = False
        self.drag_start = None
        self.drag_offset = None
        self.resize_handle = None
    
    def _on_mouse_move(self, event):
        """Handle mouse move (for cursor changes)"""
        if self.dragging:
            return
        
        # Check for resize handle hover
        handle = self._find_resize_handle(event.x, event.y)
        if handle:
            cursors = {
                "nw": "top_left_corner",
                "ne": "top_right_corner",
                "se": "bottom_right_corner",
                "sw": "bottom_left_corner",
                "n": "sb_v_double_arrow",
                "s": "sb_v_double_arrow",
                "w": "sb_h_double_arrow",
                "e": "sb_h_double_arrow",
            }
            self.canvas.configure(cursor=cursors.get(handle, "arrow"))
        else:
            self.canvas.configure(cursor="arrow")
    
    def _on_double_click(self, event):
        """Handle double click to edit widget properties"""
        widget_idx = self._find_widget_at(event.x, event.y)
        if widget_idx is not None:
            self._edit_widget_properties(widget_idx)

    def _on_anim_change(self, event):
        sel = self.anim_combo.get()
        self.selected_anim = sel or None

    def _on_anim_play(self):
        if self.selected_widget_idx is None or not self.selected_anim:
            return
        name = self.selected_anim
        # Ensure unique active animation name instance per widget by suffixing index
        inst_name = f"{name}__w{self.selected_widget_idx}"
        # Clone the template animation under a unique name if not exists
        if inst_name not in self.anim.animations:
            base = self.anim.animations[name]
            from dataclasses import asdict
            from copy import deepcopy
            cloned = deepcopy(base)
            cloned.name = inst_name
            self.anim.register_animation(cloned)
        self.anim.play_animation(inst_name, widget_id=self.selected_widget_idx)
        self.playing = True

    def _on_anim_pause(self):
        self.playing = False
    
    def _edit_widget_properties(self, widget_idx: int):
        """Open widget properties editor"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        widget = scene.widgets[widget_idx]
        
        # Clear properties panel
        for child in self.props_frame.winfo_children():
            child.destroy()
        
        # Add property editors
        ttk.Label(self.props_frame, text=f"Widget: {widget.type}", 
                 font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=5)
        
        # Text property
        if hasattr(widget, 'text'):
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text="Text:", width=10).pack(side=tk.LEFT)
            text_var = tk.StringVar(value=widget.text)
            entry = ttk.Entry(frame, textvariable=text_var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<Return>", lambda e: self._update_widget_text(widget_idx, text_var.get()))
        
        # Position and size
        ttk.Label(self.props_frame, text="Position & Size:", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        for prop in ['x', 'y', 'width', 'height']:
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{prop.capitalize()}:", width=10).pack(side=tk.LEFT)
            var = tk.IntVar(value=getattr(widget, prop))
            spinbox = ttk.Spinbox(frame, from_=0, to=200, textvariable=var, width=10)
            spinbox.pack(side=tk.LEFT)
            spinbox.bind("<Return>", 
                        lambda e, p=prop, v=var: self._update_widget_prop(widget_idx, p, v.get()))
    
    def _update_widget_text(self, widget_idx: int, text: str):
        """Update widget text"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene and widget_idx < len(scene.widgets):
            scene.widgets[widget_idx].text = text
            self.designer._save_state()
            self.refresh()
    
    def _update_widget_prop(self, widget_idx: int, prop: str, value: Any):
        """Update widget property"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene and widget_idx < len(scene.widgets):
            setattr(scene.widgets[widget_idx], prop, value)
            self.designer._save_state()
            self.refresh()
    
    def _on_delete_widget(self, event):
        """Delete selected widget"""
        if self.selected_widget_idx is not None:
            scene = self.designer.scenes.get(self.designer.current_scene)
            if scene:
                del scene.widgets[self.selected_widget_idx]
                self.selected_widget_idx = None
                self.designer._save_state()
                self.refresh()
    
    def _on_zoom_change(self, event):
        """Handle zoom change"""
        zoom_str = event.widget.get()
        try:
            self.settings.zoom = float(zoom_str.rstrip('x'))
            self.refresh()
        except ValueError:
            pass
    
    def _on_grid_toggle(self):
        """Toggle grid"""
        self.settings.grid_enabled = self.grid_var.get()
        self.refresh()
    
    def _on_snap_toggle(self):
        """Toggle snap"""
        self.settings.snap_enabled = self.snap_var.get()
    
    def _choose_bg_color(self):
        """Choose background color"""
        color = colorchooser.askcolor(initialcolor=self.settings.background_color)
        if color[1]:
            self.settings.background_color = color[1]
            self.refresh()
    
    def _export_png(self):
        """Export preview as PNG"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            initialfile="ui_preview.png"
        )
        
        if not filename:
            return
        
        # Create export image
        img_width = self.designer.width
        img_height = self.designer.height
        
        bg_color = self._hex_to_rgb(self.settings.background_color)
        img = Image.new("RGB", (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw all widgets
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene:
            for widget in scene.widgets:
                if widget.visible:
                    self._draw_widget(draw, widget, False)
        
        # Save
        img.save(filename)
        messagebox.showinfo("Export Complete", f"Saved to: {filename}")
    
    def _on_save(self, event):
        """Save design"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.designer.current_scene}.json"
        )
        
        if filename:
            self.designer.save_to_json(filename)
            messagebox.showinfo("Saved", f"Design saved to: {filename}")
    
    def run(self):
        """Run the preview window"""
        self.root.mainloop()

    def _schedule_tick(self):
        # ~60 FPS
        self.root.after(16, self._tick)

    def _tick(self):
        # Update animations and apply overlays
        self._widget_overlays.clear()
        if self.playing:
            vals = self.anim.update_animations(0.016)
            self._anim_values = vals
            # Assign per-widget overlays from any active animations
            for anim_name, v in vals.items():
                anim = self.anim.animations.get(anim_name)
                if anim and anim.widget_id is not None:
                    # Merge overlays per widget
                    cur = self._widget_overlays.get(anim.widget_id, {})
                    cur.update(v)
                    self._widget_overlays[anim.widget_id] = cur
            self.refresh()
        self._schedule_tick()


def main():
    """Main entry point"""
    # Create designer with sample scene
    designer = UIDesigner(128, 64)
    designer.create_scene("preview_test")
    
    # Add sample widgets
    designer.add_widget(WidgetType.LABEL, x=5, y=5, width=50, height=10, 
                        text="Visual Preview", border=True)
    designer.add_widget(WidgetType.BUTTON, x=60, y=5, width=30, height=10, 
                        text="Click Me")
    designer.add_widget(WidgetType.PROGRESSBAR, x=5, y=20, width=60, height=8, 
                        value=75)
    designer.add_widget(WidgetType.CHECKBOX, x=5, y=35, width=50, height=8, 
                        text="Enable Feature", checked=True)
    
    # Launch preview window
    preview = VisualPreviewWindow(designer)
    preview.run()


if __name__ == "__main__":
    main()
