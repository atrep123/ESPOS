#!/usr/bin/env python3
"""
Visual Preview Window for UI Designer
Real-time graphical preview with mouse interaction and export
"""

import os
import time
import atexit
import statistics

HEADLESS = os.environ.get("ESP32OS_HEADLESS", "0") == "1"

try:
    import tkinter as tk  # type: ignore
    from tkinter import colorchooser, filedialog, messagebox, ttk  # type: ignore
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False
from PIL import Image, ImageDraw

if HEADLESS:
    TK_AVAILABLE = False

if not TK_AVAILABLE:
    # Minimal dummies to allow import in headless mode (GUI classes are not instantiated in tests).
    class _DummyTk:
        Toplevel = object
        Canvas = object
        Text = object
        StringVar = staticmethod(lambda *_, **__: None)
        BooleanVar = staticmethod(lambda *_, **__: None)
        NW = "nw"
    tk = _DummyTk()

    class _DummyTTK:
        Frame = object
        Label = object
        Button = object
        Combobox = object
        Scrollbar = object
        Separator = object
        Treeview = object
    ttk = _DummyTTK()

    class _DummyMsg:
        def __getattr__(self, _name):
            return lambda *_, **__: None
    colorchooser = filedialog = messagebox = _DummyMsg()

if TK_AVAILABLE and not HEADLESS:
    from PIL import ImageTk  # type: ignore
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ui_animations import AnimationDesigner
from ui_components_library_ascii import (
    create_alert_dialog_ascii,
    create_breadcrumb_ascii,
    create_button_group_ascii,
    create_chart_ascii,
    create_checkbox_ascii,
    create_confirm_dialog_ascii,
    create_grid_layout_ascii,
    create_header_footer_layout_ascii,
    create_input_dialog_ascii,
    create_notification_ascii,
    create_progress_card_ascii,
    create_radio_group_ascii,
    create_sidebar_layout_ascii,
    create_slider_ascii,
    create_stat_card_ascii,
    create_status_indicator_ascii,
    create_tab_bar_ascii,
    create_toggle_switch_ascii,
    create_vertical_menu_ascii,
)
from ui_designer import UIDesigner, WidgetConfig, WidgetType
from ui_icons import MATERIAL_ICONS, ICON_PALETTE, get_all_categories

_PROFILE_ENABLED = os.environ.get("ESP32OS_PREVIEW_PROFILE", "0") == "1"
_PROFILE_EVERY = max(1, int(os.environ.get("ESP32OS_PREVIEW_PROFILE_EVERY", "50")))


class _RenderProfile:
    def __init__(self):
        self.samples: List[float] = []
        self.count = 0

    def add(self, ms: float):
        self.samples.append(ms)
        self.count += 1
        if self.count % _PROFILE_EVERY == 0:
            self.report()

    def report(self):
        if not self.samples:
            return
        avg = sum(self.samples) / len(self.samples)
        if len(self.samples) >= 20:
            p95 = statistics.quantiles(self.samples, n=20, method="inclusive")[18]
        else:
            p95 = max(self.samples)
        print(f"[preview-prof] renders={len(self.samples)} avg={avg:.3f}ms p95={p95:.3f}ms")

    def report_final(self):
        self.report()


_render_profiler = _RenderProfile() if _PROFILE_ENABLED else None
if _render_profiler:
    atexit.register(_render_profiler.report_final)


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


class _DummyUI:
    def after(self, *_, **__): return None
    def bind(self, *_, **__): return None
    def mainloop(self, *_, **__): return None
    def configure(self, *_, **__): return None
    def delete(self, *_, **__): return None
    def create_image(self, *_, **__): return None


class VisualPreviewWindow:
    """Graphical preview window with mouse interaction"""
    
    def __init__(self, designer: UIDesigner):
        self.designer = designer
        self.settings = PreviewSettings()
        self.anim = AnimationDesigner()
        # ASCII component palette definitions
        self.ascii_components = [
            {"name": "AlertDialog", "category": "Dialogs", "description": "Alert dialog with OK button", "factory": lambda: create_alert_dialog_ascii()},
            {"name": "ConfirmDialog", "category": "Dialogs", "description": "Confirmation dialog with Yes/No buttons", "factory": lambda: create_confirm_dialog_ascii()},
            {"name": "InputDialog", "category": "Dialogs", "description": "Input dialog with text field", "factory": lambda: create_input_dialog_ascii()},
            {"name": "TabBar", "category": "Navigation", "description": "Tab bar with 3 tabs", "factory": lambda: create_tab_bar_ascii()},
            {"name": "VerticalMenu", "category": "Navigation", "description": "Vertical menu list", "factory": lambda: create_vertical_menu_ascii()},
            {"name": "Breadcrumb", "category": "Navigation", "description": "Breadcrumb navigation", "factory": lambda: create_breadcrumb_ascii()},
            {"name": "StatCard", "category": "Data Display", "description": "Statistics card with value and label", "factory": lambda: create_stat_card_ascii()},
            {"name": "ProgressCard", "category": "Data Display", "description": "Progress card with percentage", "factory": lambda: create_progress_card_ascii()},
            {"name": "StatusIndicator", "category": "Data Display", "description": "Status indicator with colored dot", "factory": lambda: create_status_indicator_ascii()},
            {"name": "ButtonGroup", "category": "Controls", "description": "Button group with 3 buttons", "factory": lambda: create_button_group_ascii()},
            {"name": "ToggleSwitch", "category": "Controls", "description": "Toggle switch control", "factory": lambda: create_toggle_switch_ascii()},
            {"name": "RadioGroup", "category": "Controls", "description": "Radio button group", "factory": lambda: create_radio_group_ascii()},
            {"name": "HeaderFooterLayout", "category": "Layouts", "description": "Layout with header, content, and footer", "factory": lambda: create_header_footer_layout_ascii()},
            {"name": "SidebarLayout", "category": "Layouts", "description": "Layout with sidebar and main content", "factory": lambda: create_sidebar_layout_ascii()},
            {"name": "GridLayout", "category": "Layouts", "description": "Grid layout", "factory": lambda: create_grid_layout_ascii()},
            {"name": "Slider", "category": "Controls", "description": "Value slider with visual bar", "factory": lambda: create_slider_ascii()},
            {"name": "Checkbox", "category": "Controls", "description": "Checkbox with label", "factory": lambda: create_checkbox_ascii()},
            {"name": "Notification", "category": "Data Display", "description": "Notification banner (info/success/error/warning)", "factory": lambda: create_notification_ascii()},
            {"name": "Chart", "category": "Data Display", "description": "Simple bar chart", "factory": lambda: create_chart_ascii()},
        ]
        self.playing = False
        self.selected_anim: Optional[str] = None
        # Per-animation current values and per-widget overlay transform cache
        self._anim_values: Dict[str, Dict[str, Any]] = {}
        self._widget_overlays: Dict[int, Dict[str, Any]] = {}

        # Selection and drag state
        self.selected_widget_idx: Optional[int] = None
        self.selected_widgets: List[int] = []  # Multi-selection support
        self.dragging = False
        self.drag_start: Optional[Tuple[int, int]] = None
        self.drag_offset: Optional[Tuple[int, int]] = None
        self.drag_origin: Optional[Tuple[int, int]] = None
        self.resize_handle: Optional[str] = None  # ne, nw, se, sw, n, s, e, w
        
        # Clipboard for copy/paste
        self.clipboard: List[WidgetConfig] = []
        
        # Performance optimization: caching
        self._render_cache: Optional[Image.Image] = None
        self._cache_valid = False
        self._ascii_cache: Optional[List[str]] = None
        self._ascii_cache_valid = False
        self._last_widget_count = 0

        if HEADLESS or not TK_AVAILABLE:
            # Headless mode: stub minimal UI surfaces for logic-only tests.
            self.root = _DummyUI()
            self.canvas = _DummyUI()
            self.status_bar = _DummyUI()
            return

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
        
        # Alignment tools
        ttk.Label(toolbar, text="Align:").pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="⬅", width=3,
                  command=lambda: self._align_widgets("left")).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⬆", width=3,
                  command=lambda: self._align_widgets("top")).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⬇", width=3,
                  command=lambda: self._align_widgets("bottom")).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="➡", width=3,
                  command=lambda: self._align_widgets("right")).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="↔", width=3,
                  command=lambda: self._align_widgets("center_h")).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="↕", width=3,
                  command=lambda: self._align_widgets("center_v")).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Distribute tools
        ttk.Label(toolbar, text="Distribute:").pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="H", width=3,
                  command=lambda: self._distribute_widgets("horizontal")).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="V", width=3,
                  command=lambda: self._distribute_widgets("vertical")).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Export buttons
        ttk.Button(toolbar, text="📷 Export PNG", command=self._export_png).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="💾 Export JSON", command=self._export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📝 Export C", command=self._export_c).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📄 Export WidgetConfig", command=self._export_widgetconfig).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="👁️ Live ASCII Preview", command=self._open_ascii_preview).pack(side=tk.LEFT, padx=5)
        
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
        ttk.Button(toolbar, text="▶", width=3, command=self._on_anim_play).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⏸", width=3, command=self._on_anim_pause).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⏹", width=3, command=self._on_anim_stop).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="✏", width=3, command=self._open_animation_editor).pack(side=tk.LEFT, padx=1)
        
        # Background color
        ttk.Button(toolbar, text="🎨 BG Color", 
                  command=self._choose_bg_color).pack(side=tk.LEFT, padx=5)
        
        # Left-side palette (widget add shortcuts)
        palette = ttk.Frame(main_frame)
        palette.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        ttk.Label(palette, text="Add Widgets").pack(anchor=tk.W)
        ttk.Separator(palette, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)

        def add_btn(text, cb):
            ttk.Button(palette, text=text, command=cb).pack(fill=tk.X, pady=2)

        add_btn("➕ Label", lambda: self._palette_add("label"))
        add_btn("➕ Button", lambda: self._palette_add("button"))
        add_btn("➕ Box", lambda: self._palette_add("box"))
        add_btn("➕ Panel", lambda: self._palette_add("panel"))
        add_btn("➕ Progress", lambda: self._palette_add("progressbar"))
        add_btn("➕ Gauge", lambda: self._palette_add("gauge"))
        add_btn("➕ Checkbox", lambda: self._palette_add("checkbox"))
        add_btn("➕ Slider", lambda: self._palette_add("slider"))
        
        ttk.Separator(palette, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Button(palette, text="📦 Components", 
                  command=self._open_component_palette).pack(fill=tk.X, pady=2)
        ttk.Button(palette, text="📑 Templates", 
                  command=self._open_template_manager).pack(fill=tk.X, pady=2)
        ttk.Button(palette, text="🎨 Icons", 
                  command=self._open_icon_palette).pack(fill=tk.X, pady=2)

        # Canvas frame with scrollbars (to the right of palette)
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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

    def _center_coords(self, w: int, h: int) -> Tuple[int, int]:
        """Compute top-left coords to center a widget of size w×h."""
        cx = max(0, (self.designer.width - w) // 2)
        cy = max(0, (self.designer.height - h) // 2)
        return cx, cy

    def _palette_add(self, kind: str):
        """Add a widget of given kind near center and select it."""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            # Ensure at least one scene exists
            self.designer.create_scene("scene")
            scene = self.designer.scenes.get(self.designer.current_scene)
            if not scene:
                return

        # Defaults per widget type
        defaults = {
            "label":      (60, 10, {"text": "Label", "border": False}),
            "button":     (50, 12, {"text": "Button"}),
            "box":        (60, 40, {}),
            "panel":      (60, 40, {}),
            "progressbar":(80, 8,  {"value": 50}),
            "gauge":      (20, 30, {"value": 70}),
            "checkbox":   (60, 10, {"text": "Check me", "checked": True}),
            "slider":     (80, 8,  {"value": 50}),
        }

        w, h, props = defaults.get(kind, (40, 12, {}))
        x, y = self._center_coords(w, h)

        # Map to enum
        kind_map = {
            "label": WidgetType.LABEL,
            "button": WidgetType.BUTTON,
            "box": WidgetType.BOX if hasattr(WidgetType, 'BOX') else WidgetType.PANEL,
            "panel": WidgetType.PANEL,
            "progressbar": WidgetType.PROGRESSBAR,
            "gauge": WidgetType.GAUGE,
            "checkbox": WidgetType.CHECKBOX,
            "slider": WidgetType.SLIDER,
        }
        wtype = kind_map.get(kind, WidgetType.LABEL)

        # Create widget via designer API
        self.designer.add_widget(wtype, x=x, y=y, width=w, height=h, **props)
        # Select the new widget
        self.selected_widget_idx = len(scene.widgets) - 1
        # Save state and refresh
        self.designer._save_state()
        self._invalidate_cache()
        self.refresh()
    
    def _invalidate_cache(self):
        """Invalidate render caches"""
        self._cache_valid = False
        self._ascii_cache_valid = False
    
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
        self.root.bind("<Control-c>", self._on_copy)
        self.root.bind("<Control-v>", self._on_paste)
        self.root.bind("<Control-d>", self._on_duplicate)
        self.root.bind("<Control-a>", self._on_select_all)
        self.root.bind("<Left>", lambda e: self._on_nudge(e, -1, 0))
        self.root.bind("<Right>", lambda e: self._on_nudge(e, 1, 0))
        self.root.bind("<Up>", lambda e: self._on_nudge(e, 0, -1))
        self.root.bind("<Down>", lambda e: self._on_nudge(e, 0, 1))
        
        # Keyboard shortcuts for quick component insertion (Ctrl+1-9)
        for i in range(1, 10):
            self.root.bind(f"<Control-Key-{i}>", lambda e, idx=i-1: self._on_quick_insert(idx))
            self.root.bind(f"<Control-KP_{i}>", lambda e, idx=i-1: self._on_quick_insert(idx))  # Numpad support
    
    def refresh(self, force=False):
        """Refresh the preview with caching"""
        if HEADLESS or not TK_AVAILABLE or isinstance(self.canvas, _DummyUI):
            return
        self.canvas.delete("all")
        
        if not self.designer.current_scene:
            return
        
        # Get current scene
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        # Check if cache is valid
        widget_count = len(scene.widgets)
        if not force and self._cache_valid and self._render_cache is not None and widget_count == self._last_widget_count:
            # Use cached image
            img = self._render_cache
        else:
            img = self._render_scene_image(
                scene,
                include_grid=self.settings.grid_enabled,
                use_overlays=True,
                highlight_selection=True,
            )
            # Cache the rendered image
            self._render_cache = img.copy()
            self._cache_valid = True
            self._last_widget_count = widget_count
        
        # Scale image
        img_width = self.designer.width
        img_height = self.designer.height
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

    def _render_scene_image(self, scene, include_grid=True, use_overlays=True, highlight_selection=True):
        """Render scene into a PIL image (no Tk required)."""
        img_width = self.designer.width
        img_height = self.designer.height

        bg_color = self._hex_to_rgb(self.settings.background_color)
        img = Image.new("RGB", (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(img)

        if include_grid:
            self._draw_grid(draw, img_width, img_height)

        t0 = time.perf_counter() if _render_profiler else 0.0

        for idx, widget in enumerate(scene.widgets):
            if not widget.visible:
                continue
            overlay = self._widget_overlays.get(idx, {}) if use_overlays else {}
            self._draw_widget(draw, widget, highlight_selection and idx == self.selected_widget_idx, overlay)

        if _render_profiler:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            _render_profiler.add(dt_ms)

        return img
    
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
            # Draw checkbox (clamped for very small heights)
            box_size = max(0, min(h - 4, 6))
            box_x = x + 2
            box_y = y + (h - box_size) // 2
            y0, y1 = self._clamp_rect_y_order(box_y, box_y + box_size)
            draw.rectangle([box_x, y0, box_x + box_size, y1], outline=fg_color, width=1)
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
            # Draw progress bar with safe clamping for very small heights
            span = max(0, (w - 4))
            denom = max(1, (widget.max_value - widget.min_value))
            progress = int((widget.value - widget.min_value) / denom * span)
            if progress > 0:
                x0 = x + 2
                y_top = y + 2
                y_bottom = y + h - 3
                # Ensure correct ordering for PIL rectangle (y1 >= y0)
                y0, y1 = self._clamp_rect_y_order(y_top, y_bottom)
                x1 = x0 + progress
                # Clamp within the inner bar area
                x1 = min(x + w - 2, max(x0, x1))
                draw.rectangle([x0, y0, x1, y1], fill=fg_color)
        
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
            # Draw handle with safe clamping
            span = max(0, (w - 4))
            denom = max(1, (widget.max_value - widget.min_value))
            handle_x = x + 2 + int((widget.value - widget.min_value) / denom * span)
            x0 = max(x + 2, min(handle_x - 2, x + w - 2))
            x1 = max(x + 2, min(handle_x + 2, x + w - 2))
            y_top = y + 2
            y_bottom = y + h - 2
            y0, y1 = self._clamp_rect_y_order(y_top, y_bottom)
            draw.rectangle([x0, y0, x1, y1], fill=fg_color, outline=fg_color)
        
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
            self.drag_origin = None
            return
        
        # Check for widget selection
        widget_idx = self._find_widget_at(event.x, event.y)
        if widget_idx is not None:
            scene = self.designer.scenes.get(self.designer.current_scene)
            if not scene or not (0 <= widget_idx < len(scene.widgets)):
                return
            
            # Multi-selection with Shift key
            if event.state & 0x0001:  # Shift pressed
                if widget_idx in self.selected_widgets:
                    self.selected_widgets.remove(widget_idx)
                else:
                    self.selected_widgets.append(widget_idx)
                self.selected_widget_idx = widget_idx
            else:
                # Single selection
                if widget_idx not in self.selected_widgets:
                    self.selected_widgets = [widget_idx]
                self.selected_widget_idx = widget_idx
            
            self.dragging = True
            self.drag_start = (event.x, event.y)

            # Calculate offset for smooth dragging
            widget = scene.widgets[widget_idx]
            wx, wy = self._canvas_to_widget_coords(event.x, event.y)
            self.drag_offset = (wx - widget.x, wy - widget.y)
            self.drag_origin = (widget.x, widget.y)

            self.refresh()
        else:
            if not (event.state & 0x0001):  # Clear selection if Shift not pressed
                self.selected_widget_idx = None
                self.selected_widgets = []
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
            if self.drag_offset is None:
                return
            dx, dy = self.drag_offset
            new_x = wx - dx
            new_y = wy - dy

            # Optional axis-lock when Shift is held:
            # move převážně v jedné ose podle směru tahu
            if event.state & 0x0001 and self.drag_origin is not None and self.drag_start is not None:
                sx, sy = self.drag_start
                if abs(event.x - sx) >= abs(event.y - sy):
                    new_y = self.drag_origin[1]
                else:
                    new_x = self.drag_origin[0]

            widget.x = new_x
            widget.y = new_y
            
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
        self.drag_origin = None
    
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

    def _on_nudge(self, event, dx: int, dy: int):
        """Nudge selected widget with arrow keys.

        Holds Shift to nudge by grid size instead of 1 pixel.
        """
        if self.selected_widget_idx is None or not self.designer.current_scene:
            return

        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene or not (0 <= self.selected_widget_idx < len(scene.widgets)):
            return

        widget = scene.widgets[self.selected_widget_idx]

        step = 1
        if event.state & 0x0001:
            step = max(1, self.settings.snap_size)

        new_x = widget.x + dx * step
        new_y = widget.y + dy * step

        new_x = max(0, min(new_x, self.designer.width - widget.width))
        new_y = max(0, min(new_y, self.designer.height - widget.height))

        if new_x == widget.x and new_y == widget.y:
            return

        widget.x = new_x
        widget.y = new_y
        self.designer._save_state()
        self.refresh()
    
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
            from copy import deepcopy
            cloned = deepcopy(base)
            cloned.name = inst_name
            self.anim.register_animation(cloned)
        self.anim.play_animation(inst_name, widget_id=self.selected_widget_idx)
        self.playing = True

    def _on_anim_pause(self):
        self.playing = False
    
    def _on_anim_stop(self):
        """Stop and reset animations"""
        self.playing = False
        self.anim.stop_all_animations()
        self._widget_overlays.clear()
        self._anim_values.clear()
        self.refresh()
    
    def _open_animation_editor(self):
        """Open animation timeline editor"""
        if not hasattr(self, 'anim_editor_window') or not self.anim_editor_window.winfo_exists():
            self.anim_editor_window = AnimationEditorWindow(self.root, self)
        else:
            self.anim_editor_window.lift()
    
    def _open_component_palette(self):
        """Open component palette window"""
        if not hasattr(self, 'component_palette_window') or not self.component_palette_window.winfo_exists():
            self.component_palette_window = ComponentPaletteWindow(self.root, self)
        else:
            self.component_palette_window.lift()
    
    def _open_template_manager(self):
        """Open template manager window"""
        if not hasattr(self, 'template_manager_window') or not self.template_manager_window.winfo_exists():
            self.template_manager_window = TemplateManagerWindow(self.root, self)
        else:
            self.template_manager_window.lift()
    
    def _open_icon_palette(self):
        """Open icon palette window"""
        if not hasattr(self, 'icon_palette_window') or not self.icon_palette_window.winfo_exists():
            self.icon_palette_window = IconPaletteWindow(self.root, self)
        else:
            self.icon_palette_window.lift()
    
    def _open_icon_palette(self):
        """Open icon palette window"""
        if not hasattr(self, 'icon_palette_window') or not self.icon_palette_window.winfo_exists():
            self.icon_palette_window = IconPaletteWindow(self.root, self)
        else:
            self.icon_palette_window.lift()
    
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

        # Label property
        if hasattr(widget, 'label'):
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text="Label:", width=10).pack(side=tk.LEFT)
            label_var = tk.StringVar(value=widget.label)
            entry = ttk.Entry(frame, textvariable=label_var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<Return>", lambda e: self._update_widget_prop(widget_idx, 'label', label_var.get()))

        # Value property
        if hasattr(widget, 'value'):
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text="Value:", width=10).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=str(widget.value))
            entry = ttk.Entry(frame, textvariable=value_var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<Return>", lambda e: self._update_widget_prop(widget_idx, 'value', value_var.get()))

        # Color property
        if hasattr(widget, 'color'):
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text="Color:", width=10).pack(side=tk.LEFT)
            color_var = tk.StringVar(value=widget.color)
            entry = ttk.Entry(frame, textvariable=color_var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<Return>", lambda e: self._update_widget_prop(widget_idx, 'color', color_var.get()))

        # Position and size
        ttk.Label(self.props_frame, text="Position & Size:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        for prop in ['x', 'y', 'width', 'height']:
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{prop.capitalize()}:", width=10).pack(side=tk.LEFT)
            var = tk.IntVar(value=getattr(widget, prop))
            spinbox = ttk.Spinbox(frame, from_=0, to=200, textvariable=var, width=10)
            spinbox.pack(side=tk.LEFT)
            spinbox.bind("<Return>", lambda e, p=prop, v=var: self._update_widget_prop(widget_idx, p, v.get()))
    
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
    
    def _export_json(self):
        """Export design as JSON"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.designer.current_scene}.json"
        )
        if filename:
            self.designer.save_to_json(filename)
            messagebox.showinfo("Export Complete", f"Saved JSON to: {filename}")

    def _export_c(self):
        """Export design as C code"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".c",
            filetypes=[("C files", "*.c"), ("All files", "*.*")],
            initialfile=f"{self.designer.current_scene}.c"
        )
        if filename:
            # Use designer.export_code if available, else fallback
            if hasattr(self.designer, "export_code"):
                self.designer.export_code(filename, self.designer.current_scene)
                messagebox.showinfo("Export Complete", f"Saved C code to: {filename}")
            else:
                messagebox.showerror("Export Error", "C code export not implemented.")

    def _export_widgetconfig(self):
        """Export design as WidgetConfig text"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"{self.designer.current_scene}_widgetconfig.txt"
        )
        if not filename:
            return
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            messagebox.showerror("Export Error", "No active scene.")
            return
        try:
            lines = []
            for w in scene.widgets:
                # Simple WidgetConfig ASCII export
                props = [f"{k}={getattr(w, k)}" for k in w.__dataclass_fields__]
                lines.append(f"[{w.type}] " + ", ".join(props))
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Export Complete", f"Saved WidgetConfig to: {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed: {e}")

    def _open_ascii_preview(self):
        """Open live ASCII preview window with enhanced styling"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            messagebox.showerror("Preview Error", "No active scene.")
            return
        
        win = tk.Toplevel(self.root)
        win.title(f"Live ASCII Preview - {self.designer.current_scene}")
        win.geometry("800x600")
        win.configure(bg="#1e1e1e")
        
        # Create toolbar
        toolbar = ttk.Frame(win)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="ASCII Renderer v2.0", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 Refresh", command=lambda: self._refresh_ascii_preview(text_widget, scene)).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="💾 Copy to Clipboard", command=lambda: self._copy_ascii_to_clipboard(text_widget)).pack(side=tk.LEFT, padx=5)
        
        # Create text widget with scrollbar
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(frame, font=("Consolas", 9), bg="#1a1a1a", fg="#d4d4d4",
                             insertbackground="#ffffff", yscrollcommand=scrollbar.set,
                             wrap=tk.NONE, relief=tk.FLAT, borderwidth=0)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Configure text tags for syntax highlighting
        text_widget.tag_config("border", foreground="#569cd6")  # Blue for borders
        text_widget.tag_config("fill_button", foreground="#4ec9b0")  # Teal for buttons
        text_widget.tag_config("fill_box", foreground="#808080")  # Gray for boxes
        text_widget.tag_config("fill_icon", foreground="#dcdcaa")  # Yellow for icons
        text_widget.tag_config("text_label", foreground="#ce9178")  # Orange for text
        
        # Render ASCII UI
        self._refresh_ascii_preview(text_widget, scene)
        
    def _refresh_ascii_preview(self, text_widget, scene):
        """Refresh ASCII preview with syntax highlighting"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        
        # Render ASCII lines
        ascii_lines = self._render_ascii_scene(scene)
        
        # Insert with highlighting
        for line_num, line in enumerate(ascii_lines, 1):
            for char_num, char in enumerate(line):
                # Determine tag based on character
                tag = None
                if char in "┌┐└┘─│":
                    tag = "border"
                elif char == "▓":
                    tag = "fill_button"
                elif char == "░":
                    tag = "fill_box"
                elif char == "◆":
                    tag = "fill_icon"
                elif char.isalnum():
                    tag = "text_label"
                
                if tag:
                    text_widget.insert(tk.END, char, tag)
                else:
                    text_widget.insert(tk.END, char)
            
            text_widget.insert(tk.END, "\n")
        
        text_widget.config(state=tk.DISABLED)
    
    def _copy_ascii_to_clipboard(self, text_widget):
        """Copy ASCII preview to clipboard"""
        content = text_widget.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Copied", "ASCII preview copied to clipboard!")

    def _render_ascii_scene(self, scene, use_cache=True):
        """Render the scene as ASCII art with enhanced visuals and caching"""
        # Use cache if valid
        if use_cache and self._ascii_cache_valid and self._ascii_cache is not None:
            widget_count = len(scene.widgets)
            if widget_count == self._last_widget_count:
                return self._ascii_cache
        
        # Create a 2D buffer
        buf = [[" " for _ in range(scene.width)] for _ in range(scene.height)]
        
        # Draw each widget with borders and enhanced styling
        for w in scene.widgets:
            if not w.visible:
                continue
            
            # Determine widget character/style based on type
            fill_char = self._get_widget_fill_char(w)
            
            # Draw widget area with clamping to buffer bounds
            start_y = max(0, w.y)
            end_y = min(w.y + w.height, scene.height)
            start_x = max(0, w.x)
            end_x = min(w.x + w.width, scene.width)
            if start_x >= end_x or start_y >= end_y:
                continue

            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    # Draw borders for widgets >= 3x3
                    if w.width >= 3 and w.height >= 3:
                        is_top = (y == w.y)
                        is_bottom = (y == w.y + w.height - 1)
                        is_left = (x == w.x)
                        is_right = (x == w.x + w.width - 1)
                        
                        if is_top and is_left:
                            buf[y][x] = "┌"
                        elif is_top and is_right:
                            buf[y][x] = "┐"
                        elif is_bottom and is_left:
                            buf[y][x] = "└"
                        elif is_bottom and is_right:
                            buf[y][x] = "┘"
                        elif is_top or is_bottom:
                            buf[y][x] = "─"
                        elif is_left or is_right:
                            buf[y][x] = "│"
                        else:
                            buf[y][x] = fill_char
                    else:
                        # Small widgets: just fill
                        buf[y][x] = fill_char
            
            # Draw text label if widget has text and is large enough
            if hasattr(w, "text") and w.text and w.width >= len(w.text) + 2 and w.height >= 3:
                text_x = w.x + 1
                text_y = w.y + w.height // 2
                if text_y < scene.height:
                    for i, char in enumerate(w.text[:w.width - 2]):
                        if text_x + i < scene.width:
                            buf[text_y][text_x + i] = char
        
        # Convert buffer to lines
        lines = ["".join(row) for row in buf]
        
        # Cache the result
        self._ascii_cache = lines
        self._ascii_cache_valid = True
        
        return lines
    
    def _get_widget_fill_char(self, widget):
        """Get fill character based on widget type"""
        type_chars = {
            "button": "▓",
            "label": " ",
            "box": "░",
            "icon": "◆",
            "checkbox": "☐",
            "slider": "═",
            "progress": "▬",
        }
        return type_chars.get(widget.type, "█")
    
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
    
    def _align_widgets(self, alignment: str):
        """Align selected widgets"""
        if len(self.selected_widgets) < 2:
            messagebox.showwarning("Alignment", "Select at least 2 widgets to align")
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        widgets = [scene.widgets[i] for i in self.selected_widgets if i < len(scene.widgets)]
        if not widgets:
            return
        
        # Use first widget as reference
        ref = widgets[0]
        
        for widget in widgets[1:]:
            if alignment == "left":
                widget.x = ref.x
            elif alignment == "right":
                widget.x = ref.x + ref.width - widget.width
            elif alignment == "top":
                widget.y = ref.y
            elif alignment == "bottom":
                widget.y = ref.y + ref.height - widget.height
            elif alignment == "center_h":
                widget.x = ref.x + (ref.width - widget.width) // 2
            elif alignment == "center_v":
                widget.y = ref.y + (ref.height - widget.height) // 2
        
        self.designer._save_state()
        self.refresh()
    
    def _distribute_widgets(self, direction: str):
        """Distribute selected widgets evenly"""
        if len(self.selected_widgets) < 3:
            messagebox.showwarning("Distribution", "Select at least 3 widgets to distribute")
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        widgets = [(i, scene.widgets[i]) for i in self.selected_widgets if i < len(scene.widgets)]
        if len(widgets) < 3:
            return
        
        if direction == "horizontal":
            # Sort by x position
            widgets.sort(key=lambda w: w[1].x)
            first = widgets[0][1]
            last = widgets[-1][1]
            total_space = (last.x - (first.x + first.width))
            total_widget_width = sum(w[1].width for w in widgets[1:-1])
            gap = (total_space - total_widget_width) / (len(widgets) - 1)
            
            current_x = first.x + first.width + gap
            for idx, widget in widgets[1:-1]:
                widget.x = int(current_x)
                current_x += widget.width + gap
        
        elif direction == "vertical":
            # Sort by y position
            widgets.sort(key=lambda w: w[1].y)
            first = widgets[0][1]
            last = widgets[-1][1]
            total_space = (last.y - (first.y + first.height))
            total_widget_height = sum(w[1].height for w in widgets[1:-1])
            gap = (total_space - total_widget_height) / (len(widgets) - 1)
            
            current_y = first.y + first.height + gap
            for idx, widget in widgets[1:-1]:
                widget.y = int(current_y)
                current_y += widget.height + gap
        
        self.designer._save_state()
        self.refresh()
    
    def _on_copy(self, event):
        """Copy selected widgets to clipboard"""
        if not self.selected_widgets:
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        from copy import deepcopy
        self.clipboard = [deepcopy(scene.widgets[i]) for i in self.selected_widgets 
                         if i < len(scene.widgets)]
        self.status_bar.configure(text=f"Copied {len(self.clipboard)} widget(s)")
    
    def _on_paste(self, event):
        """Paste widgets from clipboard"""
        if not self.clipboard:
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        from copy import deepcopy
        self.selected_widgets = []
        
        # Paste with offset to make it visible
        for widget in self.clipboard:
            new_widget = deepcopy(widget)
            new_widget.x += 10
            new_widget.y += 10
            scene.widgets.append(new_widget)
            self.selected_widgets.append(len(scene.widgets) - 1)
        
        if self.selected_widgets:
            self.selected_widget_idx = self.selected_widgets[0]
        
        self.designer._save_state()
        self.refresh()
        self.status_bar.configure(text=f"Pasted {len(self.clipboard)} widget(s)")
    
    def _on_duplicate(self, event):
        """Duplicate selected widgets (Ctrl+D)"""
        self._on_copy(event)
        self._on_paste(event)
    
    def _on_select_all(self, event):
        """Select all widgets"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        self.selected_widgets = list(range(len(scene.widgets)))
        if self.selected_widgets:
            self.selected_widget_idx = 0
        self.refresh()
        self.status_bar.configure(text=f"Selected {len(self.selected_widgets)} widget(s)")
    
    def _on_quick_insert(self, component_index: int):
        """Quick insert component from palette using keyboard shortcut (Ctrl+1-9)"""
        if component_index >= len(self.ascii_components):
            # No component at this index
            return
        
        component = self.ascii_components[component_index]
        try:
            widgets = component["factory"]()
            scene = self.designer.scenes.get(self.designer.current_scene)
            if not scene:
                return
            
            # Add widgets at center of view or last mouse position
            start_idx = len(scene.widgets)
            offset_x = 10 + (component_index * 5)  # Slight offset to avoid overlap
            offset_y = 10 + (component_index * 5)
            
            for w in widgets:
                w.x += offset_x
                w.y += offset_y
                scene.widgets.append(w)
            
            self.refresh()
            
            # Select newly added widgets
            new_indices = list(range(start_idx, start_idx + len(widgets)))
            self.selected_widgets = new_indices
            if new_indices:
                self.selected_widget_idx = new_indices[0]
            
            self.status_bar.configure(
                text=f"Quick inserted: {component['name']} ({len(widgets)} widgets) - Use Ctrl+{component_index+1} again"
            )
        except Exception as e:
            self.status_bar.configure(text=f"Failed to insert {component['name']}: {e}")
    
    def run(self):
        """Run the preview window"""
        if HEADLESS or not TK_AVAILABLE:
            return
        self.root.mainloop()

    def _schedule_tick(self):
        # ~60 FPS
        if HEADLESS or not TK_AVAILABLE:
            return
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

    def _clamp_rect_y_order(self, y0: int, y1: int) -> Tuple[int, int]:
        """Ensure y0 <= y1 for PIL rectangle operations."""
        return (y0, y1) if y0 <= y1 else (y1, y0)


class AnimationEditorWindow:
    """Timeline editor for creating and editing animations"""
    
    def __init__(self, parent, preview_window: VisualPreviewWindow):
        self.preview = preview_window
        self.anim_designer = preview_window.anim
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Animation Timeline Editor")
        self.window.geometry("800x600")
        self.window.configure(bg="#2b2b2b")
        
        self._setup_ui()
    
    def winfo_exists(self):
        """Check if window exists"""
        try:
            return self.window.winfo_exists()
        except:
            return False
    
    def lift(self):
        """Bring window to front"""
        self.window.lift()
        self.window.focus_force()
    
    def _setup_ui(self):
        """Setup animation editor UI"""
        # Top toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Animation:").pack(side=tk.LEFT, padx=5)
        
        # Animation list
        self.anim_var = tk.StringVar()
        animations = self.anim_designer.list_animations()
        if animations:
            self.anim_var.set(animations[0])
        
        anim_combo = ttk.Combobox(toolbar, textvariable=self.anim_var, 
                                  values=animations, width=20)
        anim_combo.pack(side=tk.LEFT, padx=5)
        anim_combo.bind("<<ComboboxSelected>>", self._on_anim_selected)
        
        ttk.Button(toolbar, text="➕ New", command=self._create_new_animation).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ Delete", command=self._delete_animation).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Playback controls
        ttk.Button(toolbar, text="▶", width=3, command=self._play_preview).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⏸", width=3, command=self._pause_preview).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⏹", width=3, command=self._stop_preview).pack(side=tk.LEFT, padx=1)
        
        # Main content area
        content = ttk.Frame(self.window)
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Properties panel (left)
        props_frame = ttk.LabelFrame(content, text="Animation Properties", padding=10)
        props_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Type
        ttk.Label(props_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.type_var = tk.StringVar(value="fade")
        type_combo = ttk.Combobox(props_frame, textvariable=self.type_var, width=15,
                                  values=["fade", "slide_left", "slide_right", "move", 
                                         "scale", "pulse", "bounce"])
        type_combo.grid(row=0, column=1, pady=2)
        
        # Duration
        ttk.Label(props_frame, text="Duration (ms):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.duration_var = tk.IntVar(value=500)
        ttk.Spinbox(props_frame, from_=100, to=5000, textvariable=self.duration_var, 
                   width=13, increment=100).grid(row=1, column=1, pady=2)
        
        # Easing
        ttk.Label(props_frame, text="Easing:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.easing_var = tk.StringVar(value="ease_in_out")
        easing_combo = ttk.Combobox(props_frame, textvariable=self.easing_var, width=15,
                                    values=["linear", "ease_in", "ease_out", "ease_in_out",
                                           "ease_in_quad", "ease_out_quad"])
        easing_combo.grid(row=2, column=1, pady=2)
        easing_combo.bind("<<ComboboxSelected>>", self._on_easing_changed)
        
        # Easing curve preview
        self.easing_canvas = tk.Canvas(props_frame, width=120, height=80, bg="#1e1e1e")
        self.easing_canvas.grid(row=3, column=0, columnspan=2, pady=5)
        self._draw_easing_curve()
        
        # Loop
        self.loop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(props_frame, text="Loop", variable=self.loop_var).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Apply button
        ttk.Button(props_frame, text="Apply Changes", 
                  command=self._apply_changes).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Export button
        ttk.Button(props_frame, text="📤 Export to C", 
                  command=self._export_to_c).grid(row=6, column=0, columnspan=2, pady=5)
        
        # Timeline canvas (right)
        timeline_frame = ttk.LabelFrame(content, text="Timeline", padding=5)
        timeline_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Timeline controls
        timeline_ctrl = ttk.Frame(timeline_frame)
        timeline_ctrl.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        ttk.Label(timeline_ctrl, text="Keyframes:").pack(side=tk.LEFT, padx=5)
        ttk.Button(timeline_ctrl, text="➕ Add", command=self._add_keyframe).pack(side=tk.LEFT, padx=2)
        ttk.Button(timeline_ctrl, text="🗑️ Delete", command=self._delete_keyframe).pack(side=tk.LEFT, padx=2)
        
        # Timeline canvas with scrollbar
        canvas_container = ttk.Frame(timeline_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        self.timeline_canvas = tk.Canvas(canvas_container, bg="#2b2b2b", height=200)
        scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.timeline_canvas.yview)
        self.timeline_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Timeline click events
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.selected_keyframe_idx = None
        
        # Keyframe properties panel
        keyframe_frame = ttk.LabelFrame(timeline_frame, text="Keyframe Properties", padding=5)
        keyframe_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        ttk.Label(keyframe_frame, text="Time (0-1):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.keyframe_time_var = tk.DoubleVar(value=0.0)
        ttk.Spinbox(keyframe_frame, from_=0.0, to=1.0, textvariable=self.keyframe_time_var,
                   width=10, increment=0.1, format="%.2f").grid(row=0, column=1, padx=5)
        
        ttk.Label(keyframe_frame, text="Property:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.keyframe_prop_var = tk.StringVar(value="opacity")
        prop_combo = ttk.Combobox(keyframe_frame, textvariable=self.keyframe_prop_var, width=10,
                                  values=["opacity", "x", "y", "width", "height", "scale", "rotation"])
        prop_combo.grid(row=1, column=1, padx=5)
        
        ttk.Label(keyframe_frame, text="Value:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.keyframe_value_var = tk.StringVar(value="1.0")
        ttk.Entry(keyframe_frame, textvariable=self.keyframe_value_var, width=12).grid(row=2, column=1, padx=5)
        
        ttk.Button(keyframe_frame, text="Update Keyframe", 
                  command=self._update_keyframe).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Status bar
        self.status = ttk.Label(self.window, text="Ready", relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _on_anim_selected(self, event=None):
        """Load selected animation properties"""
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            return
        
        anim = self.anim_designer.animations[anim_name]
        self.type_var.set(anim.type)
        self.duration_var.set(anim.duration)
        self.easing_var.set(anim.easing)
        self.loop_var.set(anim.iterations == -1)
        self.status.configure(text=f"Loaded: {anim_name}")
        
        # Update timeline display
        self._draw_timeline()
    
    def _draw_timeline(self):
        """Draw timeline with keyframes"""
        self.timeline_canvas.delete("all")
        
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            return
        
        anim = self.anim_designer.animations[anim_name]
        
        # Draw timeline bar
        canvas_width = self.timeline_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 600
        
        timeline_y = 50
        timeline_height = 20
        
        # Background bar
        self.timeline_canvas.create_rectangle(
            50, timeline_y, canvas_width - 50, timeline_y + timeline_height,
            fill="#1e1e1e", outline="white", width=2, tags="timeline_bar"
        )
        
        # Time markers (0%, 25%, 50%, 75%, 100%)
        bar_width = canvas_width - 100
        for i, pct in enumerate([0, 0.25, 0.5, 0.75, 1.0]):
            x = 50 + int(bar_width * pct)
            self.timeline_canvas.create_line(x, timeline_y + timeline_height, x, timeline_y + timeline_height + 10,
                                            fill="white", width=1)
            self.timeline_canvas.create_text(x, timeline_y + timeline_height + 20,
                                            text=f"{int(pct*100)}%", fill="white", font=("Arial", 8))
        
        # Draw keyframes
        if not anim.keyframes:
            self.timeline_canvas.create_text(
                canvas_width // 2, timeline_y + 80,
                text="No keyframes yet. Click '➕ Add' to create one.",
                fill="gray", font=("Arial", 10)
            )
            return
        
        for idx, kf in enumerate(anim.keyframes):
            x = 50 + int(bar_width * kf.time)
            
            # Keyframe marker
            color = "#00ff00" if idx == self.selected_keyframe_idx else "#ffaa00"
            self.timeline_canvas.create_oval(
                x - 8, timeline_y + 6, x + 8, timeline_y + 34,
                fill=color, outline="white", width=2, tags=f"keyframe_{idx}"
            )
            
            # Keyframe label
            props_text = ", ".join([f"{k}={v}" for k, v in list(kf.properties.items())[:2]])
            if len(kf.properties) > 2:
                props_text += "..."
            
            self.timeline_canvas.create_text(
                x, timeline_y + 50,
                text=f"KF{idx}\n{props_text}",
                fill="white", font=("Arial", 8), tags=f"keyframe_{idx}"
            )
    
    def _on_timeline_click(self, event):
        """Handle timeline click to select keyframe"""
        # Find clicked keyframe
        items = self.timeline_canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
        
        for item in items:
            tags = self.timeline_canvas.gettags(item)
            for tag in tags:
                if tag.startswith("keyframe_"):
                    idx = int(tag.split("_")[1])
                    self.selected_keyframe_idx = idx
                    self._load_keyframe(idx)
                    self._draw_timeline()
                    return
        
        # Click on empty area - deselect
        self.selected_keyframe_idx = None
        self._draw_timeline()
    
    def _load_keyframe(self, idx: int):
        """Load keyframe properties into UI"""
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            return
        
        anim = self.anim_designer.animations[anim_name]
        if idx < 0 or idx >= len(anim.keyframes):
            return
        
        kf = anim.keyframes[idx]
        self.keyframe_time_var.set(kf.time)
        
        # Load first property
        if kf.properties:
            prop_name, prop_value = list(kf.properties.items())[0]
            self.keyframe_prop_var.set(prop_name)
            self.keyframe_value_var.set(str(prop_value))
    
    def _add_keyframe(self):
        """Add new keyframe"""
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            messagebox.showwarning("No Animation", "Select an animation first", parent=self.window)
            return
        
        from ui_animations import Keyframe
        
        # Get property and value
        prop = self.keyframe_prop_var.get()
        try:
            value = float(self.keyframe_value_var.get())
        except ValueError:
            value = self.keyframe_value_var.get()
        
        # Create keyframe
        kf = Keyframe(
            time=self.keyframe_time_var.get(),
            properties={prop: value},
            easing="linear"
        )
        
        anim = self.anim_designer.animations[anim_name]
        anim.keyframes.append(kf)
        anim.keyframes.sort(key=lambda k: k.time)
        
        self._draw_timeline()
        self.status.configure(text=f"Added keyframe at {kf.time:.2f}")
    
    def _delete_keyframe(self):
        """Delete selected keyframe"""
        if self.selected_keyframe_idx is None:
            messagebox.showwarning("No Selection", "Select a keyframe first", parent=self.window)
            return
        
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            return
        
        anim = self.anim_designer.animations[anim_name]
        if self.selected_keyframe_idx < 0 or self.selected_keyframe_idx >= len(anim.keyframes):
            return
        
        anim.keyframes.pop(self.selected_keyframe_idx)
        self.selected_keyframe_idx = None
        self._draw_timeline()
        self.status.configure(text="Keyframe deleted")
    
    def _update_keyframe(self):
        """Update selected keyframe properties"""
        if self.selected_keyframe_idx is None:
            messagebox.showwarning("No Selection", "Select a keyframe first", parent=self.window)
            return
        
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            return
        
        anim = self.anim_designer.animations[anim_name]
        if self.selected_keyframe_idx < 0 or self.selected_keyframe_idx >= len(anim.keyframes):
            return
        
        kf = anim.keyframes[self.selected_keyframe_idx]
        
        # Update properties
        kf.time = self.keyframe_time_var.get()
        
        prop = self.keyframe_prop_var.get()
        try:
            value = float(self.keyframe_value_var.get())
        except ValueError:
            value = self.keyframe_value_var.get()
        
        kf.properties[prop] = value
        
        # Re-sort by time
        anim.keyframes.sort(key=lambda k: k.time)
        
        self._draw_timeline()
        self.status.configure(text=f"Updated keyframe at {kf.time:.2f}")
    
    def _draw_easing_curve(self):
        """Draw easing function curve preview"""
        from ui_animations import AnimationEasing
        
        self.easing_canvas.delete("all")
        
        # Get easing function
        easing_name = self.easing_var.get()
        easing_func = getattr(AnimationEasing, easing_name, AnimationEasing.linear)
        
        # Canvas dimensions
        width = 120
        height = 80
        padding = 10
        
        # Draw axes
        self.easing_canvas.create_line(padding, height - padding, width - padding, height - padding,
                                       fill="gray", width=1)  # X axis
        self.easing_canvas.create_line(padding, height - padding, padding, padding,
                                       fill="gray", width=1)  # Y axis
        
        # Draw curve
        points = []
        steps = 50
        for i in range(steps + 1):
            t = i / steps
            value = easing_func(t)
            
            x = padding + (width - 2 * padding) * t
            y = height - padding - (height - 2 * padding) * value
            points.extend([x, y])
        
        if len(points) >= 4:
            self.easing_canvas.create_line(points, fill="#00ff00", width=2, smooth=True)
        
        # Labels
        self.easing_canvas.create_text(width // 2, height - 3,
                                       text="Time", fill="gray", font=("Arial", 7))
        self.easing_canvas.create_text(3, height // 2,
                                       text="Value", fill="gray", font=("Arial", 7), angle=90)
    
    def _on_easing_changed(self, event=None):
        """Handle easing function change"""
        self._draw_easing_curve()
    
    def _create_new_animation(self):
        """Create new animation"""
        from ui_animations import Animation, AnimationType, EasingFunction
        
        # Simple dialog
        name = tk.simpledialog.askstring("New Animation", "Animation name:",
                                        parent=self.window)
        if not name:
            return
        
        # Create animation
        anim = Animation(
            name=name,
            type=AnimationType.FADE.value,
            duration=500,  # milliseconds
            easing=EasingFunction.EASE_IN_OUT.value,
            iterations=1,
            keyframes=[]
        )
        
        self.anim_designer.register_animation(anim)
        
        # Update combo
        animations = self.anim_designer.list_animations()
        self.anim_var.set(name)
        
        # Update main window combo too
        self.preview.anim_combo.configure(values=animations)
        self.preview.anim_combo.set(name)
        self.preview.selected_anim = name
        
        self.status.configure(text=f"Created: {name}")
    
    def _delete_animation(self):
        """Delete selected animation"""
        anim_name = self.anim_var.get()
        if not anim_name:
            return
        
        if messagebox.askyesno("Delete Animation", 
                              f"Delete animation '{anim_name}'?",
                              parent=self.window):
            if anim_name in self.anim_designer.animations:
                del self.anim_designer.animations[anim_name]
            
            # Update combos
            animations = self.anim_designer.list_animations()
            if animations:
                self.anim_var.set(animations[0])
            else:
                self.anim_var.set("")
            
            self.preview.anim_combo.configure(values=animations)
            self.status.configure(text=f"Deleted: {anim_name}")
    
    def _apply_changes(self):
        """Apply property changes to selected animation"""
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            messagebox.showwarning("No Animation", "Select an animation first",
                                  parent=self.window)
            return
        
        anim = self.anim_designer.animations[anim_name]
        anim.type = self.type_var.get()
        anim.duration = self.duration_var.get()
        anim.easing = self.easing_var.get()
        anim.iterations = -1 if self.loop_var.get() else 1
        
        self.status.configure(text=f"Updated: {anim_name}")
        messagebox.showinfo("Applied", f"Changes applied to '{anim_name}'",
                           parent=self.window)
    
    def _play_preview(self):
        """Play animation in main preview"""
        if self.preview.selected_widget_idx is not None:
            self.preview._on_anim_play()
    
    def _pause_preview(self):
        """Pause animation"""
        self.preview._on_anim_pause()
    
    def _stop_preview(self):
        """Stop animation"""
        self.preview._on_anim_stop()
    
    def _export_to_c(self):
        """Export selected animation to C code"""
        from pathlib import Path
        from tkinter import filedialog

        from animation_export_c import AnimationExporter
        
        anim_name = self.anim_var.get()
        if not anim_name or anim_name not in self.anim_designer.animations:
            messagebox.showwarning("No Animation", "Select an animation first",
                                  parent=self.window)
            return
        
        # Ask for output directory
        output_dir = filedialog.askdirectory(
            title="Select Export Directory",
            parent=self.window
        )
        
        if not output_dir:
            return
        
        try:
            # Export selected animation
            exporter = AnimationExporter()
            anim = self.anim_designer.animations[anim_name]
            exporter.add_animation(anim)
            
            # Generate files
            output_path = Path(output_dir)
            header_file, impl_file = exporter.export_to_files(output_path)
            
            self.status.configure(text=f"Exported: {anim_name}")
            messagebox.showinfo("Export Complete", 
                              f"Animation exported to:\n{header_file}\n{impl_file}",
                              parent=self.window)
        
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {str(e)}",
                               parent=self.window)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="UI Designer Preview")
    parser.add_argument("--headless", action="store_true", help="Run without GUI and export image (deprecated, use --headless-preview)")
    parser.add_argument("--headless-preview", action="store_true", help="Run without GUI and export PNG/HTML")
    parser.add_argument("--in-json", default="", help="Design JSON to load (optional)")
    parser.add_argument("--out-png", default="examples/preview_ci.png", help="Output PNG path in headless mode")
    parser.add_argument("--out-html", default="", help="Optional HTML preview output path in headless mode")
    parser.add_argument("--bg", default="#000000", help="Background color (hex)")
    args = parser.parse_args()

    # Create designer with sample scene
    designer = UIDesigner(128, 64)
    if args.in_json:
        try:
            designer.load_from_json(args.in_json)
        except Exception as e:
            print(f"[headless] Failed to load design {args.in_json}: {e}")
            designer.create_scene("preview_test")
    else:
        designer.create_scene("preview_test")
        # Add sample widgets
        designer.add_widget(WidgetType.LABEL, x=5, y=5, width=50, height=10, text="Visual Preview", border=True)
        designer.add_widget(WidgetType.BUTTON, x=60, y=5, width=30, height=10, text="Click Me")
        designer.add_widget(WidgetType.PROGRESSBAR, x=5, y=20, width=60, height=8, value=75)
        designer.add_widget(WidgetType.CHECKBOX, x=5, y=35, width=50, height=8, text="Enable Feature", checked=True)

    if args.headless or args.headless_preview or not TK_AVAILABLE:
        # Headless render to PNG
        from pathlib import Path
        Path("examples").mkdir(exist_ok=True)
        def _hx(col: str):
            c = col.lstrip("#")
            return tuple(int(c[i:i+2], 16) for i in (0,2,4))
        img = Image.new("RGB", (designer.width, designer.height), _hx(args.bg))
        draw = ImageDraw.Draw(img)
        scene = designer.scenes.get(designer.current_scene)
        if scene:
            for w in scene.widgets:
                if w.visible:
                    # Minimal draw: reuse class method via instance
                    vp = object.__new__(VisualPreviewWindow)
                    vp.settings = PreviewSettings()
                    vp._draw_widget(draw, w, False)
        img = img.resize((designer.width * 4, designer.height * 4), Image.NEAREST)
        img.save(args.out_png)
        print(f"[headless] PNG exported: {args.out_png}")
        # Optional HTML
        if args.out_html:
            try:
                # Use ASCII HTML export from designer
                designer.export_to_html(args.out_html)
                print(f"[headless] HTML exported: {args.out_html}")
            except Exception as e:
                print(f"[headless] HTML export failed: {e}")
        return 0

    # GUI mode
    preview = VisualPreviewWindow(designer)
    preview.run()


# ========== TEMPLATE MANAGER WINDOW ==========

class TemplateManagerWindow(tk.Toplevel):
    """Template manager for saving and loading custom widget combinations"""
    
    def __init__(self, parent, preview_window: VisualPreviewWindow):
        super().__init__(parent)
        self.preview_window = preview_window
        self.designer = preview_window.designer
        self.templates_dir = "templates"
        
        # Create templates directory if it doesn't exist
        import os
        os.makedirs(self.templates_dir, exist_ok=True)
        
        self.title("Template Manager")
        self.geometry("500x600")
        self.configure(bg="#2b2b2b")
        
        self._setup_ui()
        self._load_templates()
    
    def _setup_ui(self):
        """Setup template manager UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header, text="📑 Template Manager", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Button(toolbar, text="💾 Save Selection as Template", 
                  command=self._save_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 Refresh", 
                  command=self._load_templates).pack(side=tk.LEFT, padx=5)
        
        # Template list (scrollable)
        list_frame = ttk.Frame(self)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas with scrollbar
        canvas = tk.Canvas(list_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        self.templates_frame = ttk.Frame(canvas)
        self.templates_frame.bind("<Configure>", 
                                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.templates_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = canvas
    
    def _load_templates(self):
        """Load and display all saved templates"""
        import json
        import os
        
        # Clear existing
        for widget in self.templates_frame.winfo_children():
            widget.destroy()
        
        # Get all template files
        template_files = []
        if os.path.exists(self.templates_dir):
            template_files = [f for f in os.listdir(self.templates_dir) if f.endswith('.json')]
        
        if not template_files:
            ttk.Label(self.templates_frame, text="No templates found. Save a selection to create one.", 
                     font=("Arial", 10), foreground="#888").pack(padx=20, pady=20)
            return
        
        # Display templates
        for template_file in sorted(template_files):
            template_path = os.path.join(self.templates_dir, template_file)
            try:
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                self._create_template_card(template_file, template_data)
            except Exception as e:
                print(f"Failed to load template {template_file}: {e}")
    
    def _create_template_card(self, filename: str, template_data: dict):
        """Create a template card in the list"""
        card = ttk.Frame(self.templates_frame, relief=tk.RAISED, borderwidth=1)
        card.pack(fill=tk.X, padx=5, pady=5)
        
        # Header with name
        header = ttk.Frame(card)
        header.pack(fill=tk.X, padx=10, pady=5)
        
        name = template_data.get("name", filename.replace(".json", ""))
        ttk.Label(header, text=name, font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        
        # Info
        widget_count = len(template_data.get("widgets", []))
        ttk.Label(header, text=f"{widget_count} widgets", 
                 font=("Arial", 9), foreground="#888").pack(side=tk.RIGHT)
        
        # Description
        desc = template_data.get("description", "No description")
        ttk.Label(card, text=desc, font=("Arial", 9), foreground="#aaa").pack(anchor=tk.W, padx=10)
        
        # Buttons
        button_frame = ttk.Frame(card)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="➕ Add to Canvas", 
                  command=lambda: self._load_template(filename)).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="👁️ Preview", 
                  command=lambda: self._preview_template(template_data)).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑️ Delete", 
                  command=lambda: self._delete_template(filename)).pack(side=tk.LEFT, padx=2)
    
    def _save_template(self):
        """Save currently selected widgets as a template"""
        import json
        from tkinter import simpledialog
        
        if not self.preview_window.selected_widgets:
            messagebox.showwarning("No Selection", "Select widgets to save as template")
            return
        
        # Ask for template name and description
        name = simpledialog.askstring("Template Name", "Enter template name:")
        if not name:
            return
        
        description = simpledialog.askstring("Template Description", 
                                            "Enter template description (optional):", 
                                            initialvalue="Custom component template")
        
        # Get selected widgets
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        selected_widgets = [scene.widgets[i] for i in self.preview_window.selected_widgets 
                          if i < len(scene.widgets)]
        
        # Create template data
        template_data = {
            "name": name,
            "description": description or "Custom component template",
            "widgets": [self._widget_to_dict(w) for w in selected_widgets]
        }
        
        # Save to file
        import os
        filename = f"{name.lower().replace(' ', '_')}.json"
        filepath = os.path.join(self.templates_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(template_data, f, indent=2)
            messagebox.showinfo("Template Saved", f"Template '{name}' saved successfully!")
            self._load_templates()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save template: {e}")
    
    def _widget_to_dict(self, widget) -> dict:
        """Convert widget to dictionary"""
        return {
            "type": widget.type,
            "x": widget.x,
            "y": widget.y,
            "width": widget.width,
            "height": widget.height,
            "text": getattr(widget, "text", ""),
            "visible": widget.visible,
            "border": getattr(widget, "border", False),
            "checked": getattr(widget, "checked", False),
            "value": getattr(widget, "value", 0),
        }
    
    def _load_template(self, filename: str):
        """Load template and add widgets to canvas"""
        import json
        import os
        
        filepath = os.path.join(self.templates_dir, filename)
        try:
            with open(filepath, 'r') as f:
                template_data = json.load(f)
            
            scene = self.designer.scenes.get(self.designer.current_scene)
            if not scene:
                messagebox.showerror("Error", "No active scene")
                return
            
            # Add widgets from template
            start_idx = len(scene.widgets)
            for widget_data in template_data.get("widgets", []):
                widget = self._dict_to_widget(widget_data)
                scene.widgets.append(widget)
            
            # Select newly added widgets
            new_indices = list(range(start_idx, len(scene.widgets)))
            self.preview_window.selected_widgets = new_indices
            if new_indices:
                self.preview_window.selected_widget_idx = new_indices[0]
            
            self.preview_window.refresh()
            messagebox.showinfo("Template Loaded", 
                              f"Added {len(template_data.get('widgets', []))} widgets from template")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load template: {e}")
    
    def _dict_to_widget(self, data: dict):
        """Convert dictionary to widget"""
        from ui_designer import WidgetConfig
        return WidgetConfig(
            type=data.get("type", "label"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 10),
            height=data.get("height", 10),
            text=data.get("text", ""),
            visible=data.get("visible", True),
            border=data.get("border", False),
            checked=data.get("checked", False),
            value=data.get("value", 0),
        )
    
    def _preview_template(self, template_data: dict):
        """Show template preview"""
        preview_text = f"Template: {template_data.get('name', 'Unknown')}\n\n"
        preview_text += f"Description: {template_data.get('description', 'None')}\n\n"
        preview_text += f"Widgets ({len(template_data.get('widgets', []))}):\n"
        
        for i, widget in enumerate(template_data.get("widgets", []), 1):
            preview_text += f"  {i}. {widget.get('type', 'unknown')} at ({widget.get('x')},{widget.get('y')})\n"
        
        messagebox.showinfo("Template Preview", preview_text)
    
    def _delete_template(self, filename: str):
        """Delete a template"""
        import os
        
        if messagebox.askyesno("Delete Template", f"Delete template '{filename}'?"):
            filepath = os.path.join(self.templates_dir, filename)
            try:
                os.remove(filepath)
                messagebox.showinfo("Deleted", "Template deleted successfully")
                self._load_templates()
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete template: {e}")


# ========== COMPONENT PALETTE WINDOW ==========

class ComponentPaletteWindow(tk.Toplevel):
    """Component palette window for drag-and-drop component templates"""
    
    def __init__(self, parent, preview_window: VisualPreviewWindow):
        super().__init__(parent)
        self.preview_window = preview_window
        self.library = preview_window.component_library
        
        self.title("Component Palette")
        self.geometry("400x600")
        self.configure(bg="#2b2b2b")
        
        # Setup UI
        self._setup_ui()
        self._load_components()
    
    def _setup_ui(self):
        """Setup palette UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header, text="📦 Component Library", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Category filter
        filter_frame = ttk.Frame(self)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=5)
        
        categories = ["All"] + sorted(set(c["category"] for c in self.preview_window.ascii_components))
        self.category_var = tk.StringVar(value="All")
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var,
                          values=categories, width=20, state="readonly")
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind("<<ComboboxSelected>>", lambda e: self._load_components())
        
        # Search box
        search_frame = ttk.Frame(self)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._load_components())
        
        # Component list (scrollable)
        list_frame = ttk.Frame(self)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas with scrollbar
        canvas = tk.Canvas(list_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        self.components_frame = ttk.Frame(canvas)
        self.components_frame.bind("<Configure>", 
                                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.components_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = canvas
    
    def _load_components(self):
        """Load and display components based on filters"""
        # Clear existing
        for widget in self.components_frame.winfo_children():
            widget.destroy()
        
        # Get filtered components
        category = self.category_var.get()
        search = self.search_var.get().lower()
        components = self.preview_window.ascii_components
        if category != "All":
            components = [c for c in components if c["category"] == category]
        if search:
            components = [c for c in components if search in c["name"].lower() or search in c["description"].lower()]
        # Display components
        for i, component in enumerate(components):
            self._create_component_card(component, i)
    
    def _create_component_card(self, component, index):
        """Create a component card in the palette"""
        card = ttk.Frame(self.components_frame, relief=tk.RAISED, borderwidth=1)
        card.pack(fill=tk.X, padx=5, pady=5)
        # Header with name and category
        header = ttk.Frame(card)
        header.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(header, text=component["name"], font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        
        # Show keyboard shortcut if available (Ctrl+1-9)
        component_idx = self.preview_window.ascii_components.index(component)
        if component_idx < 9:
            ttk.Label(header, text=f"Ctrl+{component_idx+1}", 
                     font=("Courier", 9), foreground="#4CAF50", 
                     background="#263238", relief=tk.RAISED, padding=2).pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(header, text=f"[{component["category"]}]", font=("Arial", 9), foreground="#888").pack(side=tk.RIGHT)
        # Description
        ttk.Label(card, text=component["description"], font=("Arial", 9), foreground="#aaa").pack(anchor=tk.W, padx=10)
        # Add button
        button_frame = ttk.Frame(card)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(button_frame, text="➕ Add to Canvas", command=lambda: self._add_component_to_canvas(component)).pack(fill=tk.X)
    
    def _add_component_to_canvas(self, component):
        """Add ASCII component widgets to designer canvas"""
        try:
            widgets = component["factory"]()
            scene = self.preview_window.designer.scenes.get(self.preview_window.designer.current_scene)
            if not scene:
                raise RuntimeError("No active scene")
            start_idx = len(scene.widgets)
            for w in widgets:
                scene.widgets.append(w)
            self.preview_window.refresh()
            # Select added widgets
            new_indices = list(range(start_idx, start_idx + len(widgets)))
            self.preview_window.selected_widgets = new_indices
            if new_indices:
                self.preview_window.selected_widget_idx = new_indices[0]
            messagebox.showinfo("Component Added", f"Added {component['name']} with {len(widgets)} widgets")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add component: {e}")


if __name__ == "__main__":
    import sys
    sys.exit(0)
# Icon Palette Window Implementation
# This file extends ui_designer_preview.py with the IconPaletteWindow class
# Append this to the end of ui_designer_preview.py

class IconPaletteWindow(tk.Toplevel):
    """Icon palette window for browsing and selecting Material Icons"""
    
    def __init__(self, parent, preview_window: VisualPreviewWindow):
        super().__init__(parent)
        self.preview_window = preview_window
        
        self.title("Icon Palette - Material Icons")
        self.geometry("500x700")
        self.configure(bg="#2b2b2b")
        
        # Setup UI
        self._setup_ui()
        self._load_icons()
    
    def _setup_ui(self):
        """Setup palette UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header, text="đźŽ¨ Material Icons (53)", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Size selector
        size_frame = ttk.Frame(self)
        size_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(size_frame, text="Size:").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.StringVar(value="16px")
        ttk.Radiobutton(size_frame, text="16Ă—16", variable=self.size_var, value="16px").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(size_frame, text="24Ă—24", variable=self.size_var, value="24px").pack(side=tk.LEFT, padx=5)
        
        # Category filter
        filter_frame = ttk.Frame(self)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=5)
        
        categories = ["All"] + get_all_categories()
        self.category_var = tk.StringVar(value="All")
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var,
                          values=categories, width=20, state="readonly")
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind("<<ComboboxSelected>>", lambda e: self._load_icons())
        
        # Search box
        search_frame = ttk.Frame(self)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._load_icons())
        
        # Icon list (scrollable)
        list_frame = ttk.Frame(self)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas with scrollbar
        canvas = tk.Canvas(list_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        self.icons_frame = ttk.Frame(canvas)
        self.icons_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.icons_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = canvas
        
        # Info footer
        info = ttk.Label(self, text="Click icon to copy symbol name â€˘ Drag to add to canvas (future)", 
                        font=("Arial", 9), foreground="#8b949e", background="#2b2b2b")
        info.pack(side=tk.BOTTOM, pady=10)
    
    def _load_icons(self):
        """Load and display icons based on filters"""
        # Clear existing
        for widget in self.icons_frame.winfo_children():
            widget.destroy()
        
        # Get filtered icons
        category = self.category_var.get()
        search = self.search_var.get().lower()
        icons = MATERIAL_ICONS
        
        if category != "All":
            icons = [i for i in icons if i["category"] == category]
        if search:
            icons = [i for i in icons if search in i["name"].lower() or 
                    search in i["usage"].lower() or 
                    search in i["symbol"].lower()]
        
        # Display icons
        for i, icon in enumerate(icons):
            self._create_icon_card(icon, i)
    
    def _create_icon_card(self, icon, index):
        """Create an icon card in the palette"""
        card = ttk.Frame(self.icons_frame, relief=tk.RAISED, borderwidth=1)
        card.pack(fill=tk.X, padx=5, pady=5)
        
        # Header with icon symbol and name
        header = ttk.Frame(card)
        header.pack(fill=tk.X, padx=10, pady=8)
        
        # ASCII preview
        ascii_label = ttk.Label(header, text=icon["ascii"], font=("Segoe UI Emoji", 20))
        ascii_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Name and category
        info_frame = ttk.Frame(header)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(info_frame, text=icon["name"], font=("Arial", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"{icon['category'].title()} â€˘ {icon['symbol']}", 
                 font=("Courier", 9), foreground="#58a6ff").pack(anchor=tk.W)
        
        # Usage description
        ttk.Label(card, text=icon["usage"], font=("Arial", 9), 
                 foreground="#8b949e", wraplength=450).pack(anchor=tk.W, padx=10, pady=(0, 8))
        
        # Action buttons
        button_frame = ttk.Frame(card)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="đź“‹ Copy Symbol", 
                  command=lambda: self._copy_symbol(icon["symbol"])).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="â„ą Info", 
                  command=lambda: self._show_icon_info(icon)).pack(side=tk.LEFT, padx=2)
    
    def _copy_symbol(self, symbol: str):
        """Copy icon symbol to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(symbol)
        # Show toast notification
        messagebox.showinfo("Copied", f"Symbol '{symbol}' copied to clipboard!")
    
    def _show_icon_info(self, icon):
        """Show detailed icon information"""
        size = self.size_var.get()
        size_field = "size_16" if size == "16px" else "size_24"
        
        info_text = f"""Icon: {icon['name']}
Category: {icon['category'].title()}
Usage: {icon['usage']}

C Symbol ({size}): {icon[size_field]}
ASCII Fallback: {icon['ascii']}

Example (C):
  #include "icons.h"
  display_draw_icon(&{icon[size_field]}, x, y);

Example (JSON/Python):
  {{"type": "icon", "icon": "{icon['symbol']}", "x": 10, "y": 20}}
"""
        
        # Create info dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Icon Info - {icon['name']}")
        dialog.geometry("500x400")
        dialog.configure(bg="#1e1e1e")
        
        # ASCII preview (large)
        preview = ttk.Label(dialog, text=icon["ascii"], font=("Segoe UI Emoji", 48), 
                           background="#1e1e1e", foreground="#58a6ff")
        preview.pack(pady=20)
        
        # Info text
        text = tk.Text(dialog, width=60, height=15, bg="#2b2b2b", fg="#c9d1d9", 
                      font=("Courier", 10), wrap=tk.WORD)
        text.insert("1.0", info_text)
        text.config(state=tk.DISABLED)
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)


# Add this class to the end of ui_designer_preview.py
