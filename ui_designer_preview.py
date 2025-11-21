#!/usr/bin/env python3
"""
Visual Preview Window for UI Designer
Real-time graphical preview with mouse interaction and export
"""
from __future__ import annotations

import argparse
import os
import time

try:
    import tkinter as tk  # type: ignore
    from tkinter import colorchooser, filedialog, messagebox, ttk  # type: ignore
except Exception:
    tk = None  # type: ignore
    colorchooser = filedialog = messagebox = ttk = None  # type: ignore

TK_AVAILABLE = tk is not None
from PIL import Image, ImageDraw

if TK_AVAILABLE:
    from PIL import ImageTk  # type: ignore
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from performance_profiler import PerformanceProfiler
from svg_export_enhanced import EnhancedSVGExporter, ExportOptions, ExportPreset
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

DATA_DISPLAY = "Data Display"
COMBO_SELECTED = "<<ComboboxSelected>>"
REFRESH_LABEL = "🔄 Refresh"
PROFILER_DISABLED_MSG = "Profiler not enabled"
FILETYPE_ALL = "All files"
FILETYPE_ALL_PAIR = (FILETYPE_ALL, "*.*")
EXPORT_ERROR_TITLE = "Export Error"
JSON_EXT = ".json"
JSON_PATTERN = "*.json"

if TK_AVAILABLE:
    from ui_template_manager import TemplateManagerWindow
else:
    TemplateManagerWindow = None  # type: ignore

# Public headless indicator for tests
HEADLESS: bool = (os.environ.get("ESP32OS_HEADLESS") == "1" or os.environ.get("PYTEST_CURRENT_TEST") is not None or not TK_AVAILABLE)


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
    nudge_distance: int = 1  # Normal arrow nudge distance (px)
    nudge_shift_distance: int = 8  # Shift+arrow nudge distance (px)
    # Alignment guides
    snap_to_widgets: bool = True  # Snap to other widget edges
    snap_distance: int = 4  # Snap tolerance in pixels
    show_alignment_guides: bool = True  # Show alignment guide lines
    # Debug overlay
    show_debug_overlay: bool = False
    # Auto JSON hot-reload of last loaded design file
    auto_reload_json: bool = False
    # Performance budgeting
    performance_budget_enabled: bool = True
    performance_budget_ms: float = 16.7  # Target frame time (~60 FPS)
    performance_warn_ms: float = 25.0    # Soft warning threshold


class VisualPreviewWindow:
    """Graphical preview window with mouse interaction"""
    
    def __init__(self, designer: UIDesigner):
        self.designer = designer
        self.settings = PreviewSettings()
        self.anim = AnimationDesigner()
        # UX helpers
        self._show_hints: bool = True
        self._show_guides: bool = True
        # Perf metrics
        self._last_render_ms: float = 0.0
        # Animation playback speed multiplier (1.0 = normal)
        self._anim_speed_multiplier: float = 1.0
        # JSON auto-reload watcher state
        self._json_watch_job = None
        self._json_watch_interval_ms = 1200  # ms between checks
        # Perf budget state
        self._perf_over_budget: bool = False
        self._perf_soft_warn: bool = False
        # Performance profiler
        self._profiler: Optional[PerformanceProfiler] = None
        self._profiler_enabled: bool = False
        self._last_fps: float = 0.0
        # Pan/zoom runtime state
        self._pan_enabled: bool = False  # Space held
        self._pan_dragging: bool = False
        self._zoom_min: float = 0.5
        self._zoom_max: float = 10.0
        
        # Box select state
        self.box_select_start = None  # (canvas_x, canvas_y) or None
        self.box_select_rect = None   # Canvas rectangle ID or None
        
        # Quick insert components (for Ctrl+1-9 shortcuts)
        self.quick_insert_components = [
            {"type": "label", "name": "Label", "defaults": {"text": "Label", "width": 40, "height": 10}},
            {"type": "button", "name": "Button", "defaults": {"text": "Button", "width": 40, "height": 12}},
            {"type": "box", "name": "Box", "defaults": {"width": 50, "height": 30}},
            {"type": "panel", "name": "Panel", "defaults": {"width": 60, "height": 40}},
            {"type": "progressbar", "name": "Progress Bar", "defaults": {"value": 50, "width": 60, "height": 8}},
            {"type": "gauge", "name": "Gauge", "defaults": {"value": 75, "width": 30, "height": 30}},
            {"type": "checkbox", "name": "Checkbox", "defaults": {"text": "Check", "checked": False, "width": 50, "height": 10}},
            {"type": "slider", "name": "Slider", "defaults": {"value": 50, "width": 60, "height": 8}},
            {"type": "icon", "name": "Icon", "defaults": {"width": 16, "height": 16}},
        ]
        
        # ASCII component palette definitions
        self.ascii_components = [
            {"name": "AlertDialog", "category": "Dialogs", "description": "Alert dialog with OK button", "factory": lambda: create_alert_dialog_ascii()},
            {"name": "ConfirmDialog", "category": "Dialogs", "description": "Confirmation dialog with Yes/No buttons", "factory": lambda: create_confirm_dialog_ascii()},
            {"name": "InputDialog", "category": "Dialogs", "description": "Input dialog with text field", "factory": lambda: create_input_dialog_ascii()},
            {"name": "TabBar", "category": "Navigation", "description": "Tab bar with 3 tabs", "factory": lambda: create_tab_bar_ascii()},
            {"name": "VerticalMenu", "category": "Navigation", "description": "Vertical menu list", "factory": lambda: create_vertical_menu_ascii()},
            {"name": "Breadcrumb", "category": "Navigation", "description": "Breadcrumb navigation", "factory": lambda: create_breadcrumb_ascii()},
            {"name": "StatCard", "category": DATA_DISPLAY, "description": "Statistics card with value and label", "factory": lambda: create_stat_card_ascii()},
            {"name": "ProgressCard", "category": DATA_DISPLAY, "description": "Progress card with percentage", "factory": lambda: create_progress_card_ascii()},
            {"name": "StatusIndicator", "category": DATA_DISPLAY, "description": "Status indicator with colored dot", "factory": lambda: create_status_indicator_ascii()},
            {"name": "ButtonGroup", "category": "Controls", "description": "Button group with 3 buttons", "factory": lambda: create_button_group_ascii()},
            {"name": "ToggleSwitch", "category": "Controls", "description": "Toggle switch control", "factory": lambda: create_toggle_switch_ascii()},
            {"name": "RadioGroup", "category": "Controls", "description": "Radio button group", "factory": lambda: create_radio_group_ascii()},
            {"name": "HeaderFooterLayout", "category": "Layouts", "description": "Layout with header, content, and footer", "factory": lambda: create_header_footer_layout_ascii()},
            {"name": "SidebarLayout", "category": "Layouts", "description": "Layout with sidebar and main content", "factory": lambda: create_sidebar_layout_ascii()},
            {"name": "GridLayout", "category": "Layouts", "description": "Grid layout", "factory": lambda: create_grid_layout_ascii()},
            {"name": "Slider", "category": "Controls", "description": "Value slider with visual bar", "factory": lambda: create_slider_ascii()},
            {"name": "Checkbox", "category": "Controls", "description": "Checkbox with label", "factory": lambda: create_checkbox_ascii()},
            {"name": "Notification", "category": DATA_DISPLAY, "description": "Notification banner (info/success/error/warning)", "factory": lambda: create_notification_ascii()},
            {"name": "Chart", "category": DATA_DISPLAY, "description": "Simple bar chart", "factory": lambda: create_chart_ascii()},
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
        
        # Handle hover state for visual feedback
        self.hovered_handle: Optional[str] = None
        
        # Alignment guides state
        self.alignment_guides: List[Tuple[str, int]] = []  # [(type, position), ...] type: 'v'|'h'
        
        # Clipboard for copy/paste
        self.clipboard: List[WidgetConfig] = []
        
        # Performance optimization: caching
        self._render_cache: Optional[Image.Image] = None
        self._cache_valid = False
        self._ascii_cache: Optional[List[str]] = None
        self._ascii_cache_valid = False
        self._last_widget_count = 0
        # Content-change signatures to avoid stale caches when count is unchanged
        self._last_signature: Optional[int] = None
        self._last_ascii_signature: Optional[int] = None
        # Pending placement preview
        self._pending_component: Optional[Dict[str, Any]] = None
        self._last_mouse: Optional[Tuple[int, int]] = None
        self._pending_fill = (0, 200, 255, 80)
        
        # Headless mode: allow construction without Tk for tests/CI
        headless_env = os.environ.get("ESP32OS_HEADLESS") == "1" or os.environ.get("PYTEST_CURRENT_TEST") is not None
        if not TK_AVAILABLE or headless_env:
            class _HeadlessRoot:
                def after(self, *args, **kwargs):
                    return None
                def bind(self, *args, **kwargs):
                    return None
                def mainloop(self, *args, **kwargs):
                    return None
                def configure(self, *args, **kwargs):
                    return None
            self.root = _HeadlessRoot()
            # Skip UI setup in headless mode; ASCII rendering APIs remain usable
            self._headless = True
            return
        # GUI mode below
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
        self._zoom_var = tk.StringVar(value=f"{self.settings.zoom:.1f}x")
        self._zoom_combo = ttk.Combobox(toolbar, textvariable=self._zoom_var, width=6,
                      values=["0.5x", "1.0x", "2.0x", "4.0x", "6.0x", "8.0x", "10.0x"])
        self._zoom_combo.pack(side=tk.LEFT, padx=5)
        self._zoom_combo.bind(COMBO_SELECTED, self._on_zoom_change)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Grid toggle
        self.grid_var = tk.BooleanVar(value=self.settings.grid_enabled)
        ttk.Checkbutton(toolbar, text="Grid", variable=self.grid_var,
                       command=self._on_grid_toggle).pack(side=tk.LEFT, padx=5)
        
        # Snap toggle
        self.snap_var = tk.BooleanVar(value=self.settings.snap_enabled)
        ttk.Checkbutton(toolbar, text="Snap", variable=self.snap_var,
                       command=self._on_snap_toggle).pack(side=tk.LEFT, padx=5)

        # Hints toggle
        self.hints_var = tk.BooleanVar(value=self._show_hints)
        ttk.Checkbutton(toolbar, text="Hints", variable=self.hints_var,
                   command=self._on_hints_toggle).pack(side=tk.LEFT, padx=5)

        # Guides toggle
        self.guides_var = tk.BooleanVar(value=self._show_guides)
        ttk.Checkbutton(toolbar, text="Guides", variable=self.guides_var,
               command=self._on_guides_toggle).pack(side=tk.LEFT, padx=5)
        
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
        ttk.Button(toolbar, text="🖼️ Export SVG", command=self._export_svg).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="💾 Export JSON", command=self._export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📝 Export C", command=self._export_c).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📄 Export WidgetConfig", command=self._export_widgetconfig).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="👁️ Live ASCII Preview", command=self._show_ascii_tab).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="❓ Help", command=self._show_quick_help).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="⚡ Profiler", command=self._toggle_profiler).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text=REFRESH_LABEL, 
                  command=self.refresh).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Animation controls
        ttk.Label(toolbar, text="Animation:").pack(side=tk.LEFT, padx=5)
        self.anim_combo = ttk.Combobox(toolbar, values=self.anim.list_animations(), width=14)
        if self.anim.list_animations():
            self.anim_combo.set(self.anim.list_animations()[0])
            self.selected_anim = self.anim.list_animations()[0]
        self.anim_combo.pack(side=tk.LEFT)
        self.anim_combo.bind(COMBO_SELECTED, self._on_anim_change)
        ttk.Button(toolbar, text="▶", width=3, command=self._on_anim_play).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⏸", width=3, command=self._on_anim_pause).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⏹", width=3, command=self._on_anim_stop).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="✏", width=3, command=self._open_animation_editor).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="⤴", width=3, command=self._on_anim_step).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="½x", width=3, command=self._on_anim_speed_down).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="2x", width=3, command=self._on_anim_speed_up).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="1x", width=3, command=self._on_anim_speed_reset).pack(side=tk.LEFT, padx=1)
        
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

        # Canvas frame with scrollbars (center area)
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
        # Context menu bindings (Right-click / Ctrl+Click)
        self.canvas.bind("<Button-3>", self._on_context_menu)
        self.canvas.bind("<Control-Button-1>", self._on_context_menu)
        
        # Right-side panel with tabs (Properties, ASCII)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.right_tabs = ttk.Notebook(right_panel)
        self.right_tabs.pack(fill=tk.BOTH, expand=True)

        # Properties tab
        props_container = ttk.Frame(self.right_tabs)
        self.right_tabs.add(props_container, text="Properties")

        # Settings section at top (nudge distances, grid, snap)
        settings_frame = ttk.LabelFrame(props_container, text="Editor Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Nudge distance settings
        ttk.Label(settings_frame, text="Nudge Distance:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.nudge_distance_var = tk.IntVar(value=self.settings.nudge_distance)
        nudge_spin = ttk.Spinbox(settings_frame, from_=1, to=16, width=8, 
                                 textvariable=self.nudge_distance_var,
                                 command=self._on_nudge_distance_change)
        nudge_spin.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(settings_frame, text="px", foreground="#888").grid(row=0, column=2, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Shift+Nudge:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.nudge_shift_distance_var = tk.IntVar(value=self.settings.nudge_shift_distance)
        nudge_shift_spin = ttk.Spinbox(settings_frame, from_=1, to=32, width=8,
                                       textvariable=self.nudge_shift_distance_var,
                                       command=self._on_nudge_shift_distance_change)
        nudge_shift_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(settings_frame, text="px", foreground="#888").grid(row=1, column=2, sticky=tk.W)
        
        ttk.Separator(settings_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=3, sticky="ew", pady=8)
        
        # Grid/Snap settings
        ttk.Label(settings_frame, text="Grid Size:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.grid_size_var = tk.IntVar(value=self.settings.grid_size)
        grid_spin = ttk.Spinbox(settings_frame, from_=1, to=32, width=8,
                               textvariable=self.grid_size_var,
                               command=lambda: setattr(self.settings, 'grid_size', self.grid_size_var.get()) or self.refresh())
        grid_spin.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(settings_frame, text="px", foreground="#888").grid(row=3, column=2, sticky=tk.W)

        self.props_frame = ttk.Frame(props_container, padding=10)
        self.props_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self.props_frame, text="No widget selected").pack()

        # ASCII Preview tab
        ascii_container = ttk.Frame(self.right_tabs)
        self.right_tabs.add(ascii_container, text="ASCII Preview")

        ascii_toolbar = ttk.Frame(ascii_container)
        ascii_toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Label(ascii_toolbar, text="ASCII Renderer v2.0", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        # Placeholders; actual actions wired in _show_ascii_tab
        self._ascii_refresh_btn = ttk.Button(ascii_toolbar, text=REFRESH_LABEL)
        self._ascii_refresh_btn.pack(side=tk.LEFT, padx=5)
        self._ascii_copy_btn = ttk.Button(ascii_toolbar, text="💾 Copy to Clipboard")
        self._ascii_copy_btn.pack(side=tk.LEFT, padx=5)

        ascii_frame = ttk.Frame(ascii_container)
        ascii_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ascii_scrollbar = ttk.Scrollbar(ascii_frame)
        ascii_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ascii_text_widget = tk.Text(
            ascii_frame,
            font=("Consolas", 9),
            bg="#1a1a1a",
            fg="#d4d4d4",
            insertbackground="#ffffff",
            yscrollcommand=ascii_scrollbar.set,
            wrap=tk.NONE,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.ascii_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ascii_scrollbar.config(command=self.ascii_text_widget.yview)
        # Syntax highlighting tags
        self.ascii_text_widget.tag_config("border", foreground="#569cd6")
        self.ascii_text_widget.tag_config("fill_button", foreground="#4ec9b0")
        self.ascii_text_widget.tag_config("fill_box", foreground="#808080")
        self.ascii_text_widget.tag_config("fill_icon", foreground="#dcdcaa")
        self.ascii_text_widget.tag_config("text_label", foreground="#ce9178")

        # Wire toolbar actions now that widgets exist
        self._ascii_refresh_btn.configure(command=lambda: self._refresh_ascii_preview(self.ascii_text_widget, self.designer.scenes.get(self.designer.current_scene)))
        self._ascii_copy_btn.configure(command=lambda: self._copy_ascii_to_clipboard(self.ascii_text_widget))

        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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
        
        # Show Quick Tips on first run
        self.root.after(500, self._check_and_show_quick_tips)
    
    def _check_and_show_quick_tips(self):
        """Check if Quick Tips should be shown (first run)"""
        import json
        import tempfile
        
        # Settings file in temp directory
        settings_dir = os.path.join(tempfile.gettempdir(), "esp32os_designer")
        os.makedirs(settings_dir, exist_ok=True)
        settings_file = os.path.join(settings_dir, "settings.json")
        
        # Load settings
        settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            except Exception:
                pass
    
        
        # Check if tips should be shown
        if settings.get("hide_quick_tips", False):
            return
        
        # Show Quick Tips dialog
        self._show_quick_tips_dialog(settings_file)
    
    def _toggle_profiler(self):
        """Toggle performance profiler on/off."""
        try:
            if not self._profiler_enabled:
                self._profiler = PerformanceProfiler(history_size=1000)
                self._profiler_enabled = True
                self._show_profiler_panel()
                print("⚡ Performance profiler enabled")
            else:
                self._profiler_enabled = False
                if hasattr(self, '_profiler_window') and self._profiler_window:
                    self._profiler_window.destroy()
                    self._profiler_window = None
                print("⚡ Performance profiler disabled")
        except Exception as e:
            print(f"⚠ Profiler toggle error: {e}")

    def _show_profiler_panel(self):
        """Show profiler panel with live metrics and controls."""
        if not TK_AVAILABLE or HEADLESS:
            return

        try:
            if hasattr(self, '_profiler_window') and self._profiler_window:
                self._profiler_window.lift()
                return

            window = tk.Toplevel(self.root)
            window.title("⚡ Performance Profiler")
            window.geometry("500x600")
            window.configure(bg="#2b2b2b")
            self._profiler_window = window

            header = ttk.Frame(window)
            header.pack(fill=tk.X, padx=10, pady=10)
            ttk.Label(header, text="⚡ Performance Profiler", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

            btn_frame = ttk.Frame(header)
            btn_frame.pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="📊 Export HTML", command=self._export_profiler_html).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="💾 Export CSV", command=self._export_profiler_csv).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="📄 Export JSON", command=self._export_profiler_json).pack(side=tk.LEFT, padx=2)

            stats_frame = ttk.LabelFrame(window, text="Live Metrics", padding=10)
            stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            self._profiler_labels = {}
            metrics = [
                ("fps", "FPS:"),
                ("render_ms", "Render Time:"),
                ("frame_ms", "Frame Time:"),
                ("memory_mb", "Memory:"),
                ("cpu_percent", "CPU:"),
                ("samples", "Samples:"),
            ]

            for key, label_text in metrics:
                row = ttk.Frame(stats_frame)
                row.pack(fill=tk.X, pady=2)
                ttk.Label(row, text=label_text, width=15).pack(side=tk.LEFT)
                value_label = ttk.Label(row, text="--", font=("Courier", 10))
                value_label.pack(side=tk.LEFT)
                self._profiler_labels[key] = value_label

            rec_frame = ttk.LabelFrame(window, text="Recommendations", padding=10)
            rec_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            rec_scroll = ttk.Scrollbar(rec_frame)
            rec_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            self._profiler_rec_text = tk.Text(
                rec_frame,
                height=10,
                wrap=tk.WORD,
                yscrollcommand=rec_scroll.set,
                font=("Arial", 9),
            )
            self._profiler_rec_text.pack(fill=tk.BOTH, expand=True)
            rec_scroll.config(command=self._profiler_rec_text.yview)

            self._update_profiler_panel()

        except Exception as e:
            print(f"⚠ Profiler panel error: {e}")

    def _update_profiler_panel(self):
        """Update profiler panel with latest metrics."""
        if not self._profiler_enabled or not self._profiler:
            return

        try:
            if not hasattr(self, '_profiler_window') or not self._profiler_window:
                return

            stats = self._profiler.calculate_stats()

            if hasattr(self, '_profiler_labels'):
                self._profiler_labels['fps'].config(text=f"{stats.fps_avg:.1f} (min: {stats.fps_min:.1f}, max: {stats.fps_max:.1f})")
                self._profiler_labels['render_ms'].config(text=f"{stats.render_avg_ms:.2f} ms (min: {stats.render_min_ms:.2f}, max: {stats.render_max_ms:.2f})")
                self._profiler_labels['frame_ms'].config(text=f"{stats.frame_avg_ms:.2f} ms")
                self._profiler_labels['memory_mb'].config(text=f"{stats.memory_avg_mb:.1f} MB (peak: {stats.memory_peak_mb:.1f})")
                self._profiler_labels['cpu_percent'].config(text=f"{stats.cpu_avg_percent:.1f}% (peak: {stats.cpu_peak_percent:.1f}%)")
                self._profiler_labels['samples'].config(text=f"{stats.samples}")

            if not hasattr(self, '_last_rec_update') or time.time() - self._last_rec_update > 2.0:
                self._last_rec_update = time.time()
                recommendations = self._profiler.analyze_performance()

                if hasattr(self, '_profiler_rec_text'):
                    self._profiler_rec_text.config(state=tk.NORMAL)
                    self._profiler_rec_text.delete("1.0", tk.END)
                    for rec in recommendations:
                        self._profiler_rec_text.insert(tk.END, f"• {rec}\n")
                    self._profiler_rec_text.config(state=tk.DISABLED)

            if self._profiler_window:
                self._profiler_window.after(100, self._update_profiler_panel)

        except Exception as e:
            print(f"⚠ Profiler update error: {e}")

    def _export_profiler_html(self):
        """Export profiler report to HTML."""
        if not self._profiler:
            messagebox.showwarning("Profiler", PROFILER_DISABLED_MSG)
            return

        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML", "*.html"), FILETYPE_ALL_PAIR],
                initialfile="profiler_report.html",
            )
            if filename:
                self._profiler.export_to_html(filename)
                messagebox.showinfo("Profiler", f"Report exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror(EXPORT_ERROR_TITLE, str(e))

    def _export_profiler_csv(self):
        """Export profiler metrics to CSV."""
        if not self._profiler:
            messagebox.showwarning("Profiler", PROFILER_DISABLED_MSG)
            return

        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv"), FILETYPE_ALL_PAIR],
                initialfile="profiler_metrics.csv",
            )
            if filename:
                self._profiler.export_to_csv(filename)
                messagebox.showinfo("Profiler", f"Metrics exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror(EXPORT_ERROR_TITLE, str(e))

    def _export_profiler_json(self):
        """Export profiler data to JSON."""
        if not self._profiler:
            messagebox.showwarning("Profiler", PROFILER_DISABLED_MSG)
            return

        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=JSON_EXT,
                filetypes=[("JSON", JSON_PATTERN), FILETYPE_ALL_PAIR],
                initialfile="profiler_data.json",
            )
            if filename:
                self._profiler.export_to_json(filename)
                messagebox.showinfo("Profiler", f"Data exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror(EXPORT_ERROR_TITLE, str(e))
    
    def _show_quick_tips_dialog(self, settings_file):
        """Display Quick Tips dialog for first-time users"""
        import json
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Quick Tips - UI Designer")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header = ttk.Frame(dialog)
        header.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(header, text="🎨 UI Designer Quick Tips", 
                 font=("Arial", 14, "bold")).pack()
        
        # Tips content
        tips_frame = ttk.Frame(dialog)
        tips_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tips_text = tk.Text(tips_frame, wrap=tk.WORD, font=("Arial", 10), 
                           height=15, width=50, bg="#f9f9f9")
        tips_text.pack(fill=tk.BOTH, expand=True)
        
        tips_content = """Základní ovládání:

🖱️ Myš:
• Kliknutím vyberte widget
• Shift+klik přidá do výběru
• Tažení na prázdném plátně = box select
• Tažení handlu = změna velikosti
• Dvojklik = editace vlastností

⌨️ Klávesnice:
• Ctrl+Shift+A = Rychlé přidání komponenty
• Šipky = posun o 1px (Shift = 8px)
• Delete = smazání vybraných widgetů
• Ctrl+C/V = kopírovat/vložit
• Ctrl+Z/Y = zpět/vpřed
• Space+tažení = posun plátna

🔍 Zoom:
• Ctrl+kolečko myši = zoom
• Dropdown v toolbaru

📤 Export:
• PNG export s @1x-@4x scalováním
• Možnost Scene-only nebo With-guides
• Nastavení se pamatuje

💡 Tip: Všechny funkce najdete v menu Help > Keyboard Shortcuts"""
        
        tips_text.insert("1.0", tips_content)
        tips_text.configure(state="disabled")
        
        # Checkbox and buttons
        bottom_frame = ttk.Frame(dialog)
        bottom_frame.pack(fill=tk.X, padx=20, pady=10)
        
        dont_show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom_frame, text="Nezobrazovat znovu", 
                       variable=dont_show_var).pack(anchor=tk.W, pady=5)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X)
        
        def close_dialog():
            # Save preference
            if dont_show_var.get():
                try:
                    with open(settings_file, 'w') as f:
                        json.dump({"hide_quick_tips": True}, f)
                except Exception:
                    pass
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Zavřít", command=close_dialog, 
                  width=15).pack(side=tk.RIGHT, padx=5)
    
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
        self.canvas.bind("<Button-3>", self._on_right_click)
        # Zoom with Ctrl+Wheel (Windows/Mac) and Button4/5 fallback (Linux)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel_zoom)
        self.canvas.bind("<Control-Button-4>", lambda e: self._on_ctrl_wheel_zoom(self._mk_wheel_event(e, +120)))
        self.canvas.bind("<Control-Button-5>", lambda e: self._on_ctrl_wheel_zoom(self._mk_wheel_event(e, -120)))
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
        # Toggle Debug Overlay
        self.root.bind("<F12>", self._toggle_debug_overlay)
        self.root.bind("<Escape>", lambda e: self._cancel_pending_overlay())
        self.root.bind("<g>", lambda e: self._toggle_snap_key())
        self.root.bind("<G>", lambda e: self._toggle_snap_key())
        
        # Quick Add Search dialog (Ctrl+Shift+A)
        self.root.bind("<Control-Shift-A>", self._open_quick_add_search)
        self.root.bind("<Control-Shift-a>", self._open_quick_add_search)
        
        # Keyboard shortcuts for quick component insertion (Ctrl+1-9)
        for i in range(1, 10):
            self.root.bind(f"<Control-Key-{i}>", lambda e, idx=i-1: self._on_quick_insert(idx))
            self.root.bind(f"<Control-KP_{i}>", lambda e, idx=i-1: self._on_quick_insert(idx))  # Numpad support
        # Space = hand pan
        self.root.bind("<KeyPress-space>", self._on_space_down)
        self.root.bind("<KeyRelease-space>", self._on_space_up)
        # Space = hand pan
        self.root.bind("<KeyPress-space>", self._on_space_down)
        self.root.bind("<KeyRelease-space>", self._on_space_up)
    
    def refresh(self, force=False):
        """Refresh the preview with caching"""
        if self._refresh_headless():
            return

        scene = self._get_active_scene()
        if not scene:
            return

        t0 = time.perf_counter()
        img = self._render_or_cache_scene(scene, force)
        self._draw_canvas(img)
        self._finalize_refresh(t0)

    def _refresh_headless(self) -> bool:
        """Handle headless refresh, returns True if handled."""
        if not getattr(self, '_headless', False):
            return False
        if not self.designer.current_scene:
            return True
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return True
        t0 = time.perf_counter()
        try:
            _ = self._render_scene_image(
                scene,
                background_color=self.settings.background_color,
                include_grid=self.settings.grid_enabled,
                use_overlays=False,
                highlight_selection=False,
            )
        except Exception:
            pass
        self._last_render_ms = (time.perf_counter() - t0) * 1000.0
        self._last_fps = 1000.0 / self._last_render_ms if self._last_render_ms > 0 else 60.0
        if self.settings.performance_budget_enabled:
            self._perf_over_budget = self._last_render_ms > self.settings.performance_budget_ms
            self._perf_soft_warn = self._last_render_ms > self.settings.performance_warn_ms
        if self._profiler_enabled and self._profiler:
            self._profiler.record_frame(self._last_fps, self._last_render_ms, 0.0)
        return True

    def _fill_component_results(self, query, filtered_components, results_list):
        results_list.delete(0, tk.END)
        filtered_components.clear()
        for comp in self.ascii_components:
            name_match = query in comp["name"].lower()
            cat_match = query in comp["category"].lower()
            desc_match = query in comp["description"].lower()
            if not query or name_match or cat_match or desc_match:
                filtered_components.append(comp)
                display_text = f"{comp['name']} [{comp['category']}] - {comp['description']}"
                results_list.insert(tk.END, display_text)

    def _auto_select_first(self, listbox):
        if listbox.size() > 0:
            listbox.selection_set(0)
            listbox.activate(0)

    def _add_component_to_scene(self, component, dialog=None):
        try:
            widgets = component["factory"]()
            scene = self.designer.scenes.get(self.designer.current_scene)
            if not scene:
                messagebox.showerror("Error", "No active scene")
                return
            start_idx = len(scene.widgets)
            for w in widgets:
                scene.widgets.append(w)
            self.refresh()
            new_indices = list(range(start_idx, start_idx + len(widgets)))
            self.selected_widgets = new_indices
            if new_indices:
                self.selected_widget_idx = new_indices[0]
            if dialog:
                dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add component: {e}")

    def _move_list_selection(self, listbox: tk.Listbox, delta: int):
        current = listbox.curselection()
        if not current:
            return
        new_idx = current[0] + delta
        if new_idx < 0 or new_idx >= listbox.size():
            return
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(new_idx)
        listbox.activate(new_idx)
        listbox.see(new_idx)

    def _add_text_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Text:", width=10).pack(side=tk.LEFT)
        text_value = widgets[0].text if len(widgets) == 1 else ""
        text_var = tk.StringVar(value=text_value)
        entry = ttk.Entry(frame, textvariable=text_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, 'text', text_var.get()))

    def _add_label_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Label:", width=10).pack(side=tk.LEFT)
        label_value = widgets[0].label if len(widgets) == 1 else ""
        label_var = tk.StringVar(value=label_value)
        entry = ttk.Entry(frame, textvariable=label_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, 'label', label_var.get()))

    def _add_value_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Value:", width=10).pack(side=tk.LEFT)
        value_value = str(widgets[0].value) if len(widgets) == 1 else ""
        value_var = tk.StringVar(value=value_value)
        entry = ttk.Entry(frame, textvariable=value_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, 'value', value_var.get()))

    def _add_color_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Color:", width=10).pack(side=tk.LEFT)
        color_value = widgets[0].color if len(widgets) == 1 else ""
        color_var = tk.StringVar(value=color_value)
        entry = ttk.Entry(frame, textvariable=color_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, 'color', color_var.get()))

    def _render_position_size_fields(self, widget_indices, widgets):
        ttk.Label(self.props_frame, text="Position & Size:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        for prop in ['x', 'y', 'width', 'height']:
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{prop.capitalize()}:", width=10).pack(side=tk.LEFT)
            prop_value = getattr(widgets[0], prop) if len(widgets) == 1 else 0
            var = tk.IntVar(value=prop_value)
            spinbox = ttk.Spinbox(frame, from_=0, to=200, textvariable=var, width=10)
            spinbox.pack(side=tk.LEFT)
            spinbox.bind(RETURN_KEY, lambda e, p=prop, v=var: self._update_batch_prop(widget_indices, p, v.get()))

    def _get_active_scene(self):
        if not self.designer.current_scene:
            return None
        return self.designer.scenes.get(self.designer.current_scene)

    def _render_or_cache_scene(self, scene, force: bool):
        widget_count = len(scene.widgets)
        current_sig = self._compute_scene_signature(scene)
        need_render = (
            force
            or not self._cache_valid
            or self._render_cache is None
            or widget_count != self._last_widget_count
            or self._last_signature != current_sig
        )
        if need_render:
            img = self._render_scene_image(
                scene,
                background_color=self.settings.background_color,
                include_grid=self.settings.grid_enabled,
                use_overlays=True,
                highlight_selection=True,
            )
            self._render_cache = img.copy()
            self._cache_valid = True
            self._last_widget_count = widget_count
            self._last_signature = current_sig
        else:
            img = self._render_cache
        return img

    def _draw_canvas(self, img):
        scaled_width = int(self.designer.width * self.settings.zoom)
        scaled_height = int(self.designer.height * self.settings.zoom)
        img_scaled = img.resize((scaled_width, scaled_height), Image.NEAREST)
        self.photo = ImageTk.PhotoImage(img_scaled)
        if not hasattr(self, 'canvas'):
            return
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, scaled_width, scaled_height))
        if self.selected_widget_idx is not None and self.settings.show_handles:
            self._draw_selection_handles()
        if self._show_hints:
            self._draw_hints_overlay()
        if self.settings.show_alignment_guides and self.dragging and self.selected_widget_idx is not None:
            self._draw_guides_overlay()
        if getattr(self.settings, 'show_debug_overlay', False):
            self._draw_bounds_selected_overlay()
        if getattr(self.settings, 'show_debug_overlay', False):
            self._draw_debug_overlay()

    def _finalize_refresh(self, start_time: float):
        self._last_render_ms = (time.perf_counter() - start_time) * 1000.0
        self._last_fps = 1000.0 / self._last_render_ms if self._last_render_ms > 0 else 60.0
        if self._profiler_enabled and self._profiler:
            self._profiler.record_frame(self._last_fps, self._last_render_ms, 0.0)
        if self.settings.performance_budget_enabled:
            self._perf_over_budget = self._last_render_ms > self.settings.performance_budget_ms
            self._perf_soft_warn = self._last_render_ms > self.settings.performance_warn_ms
        self._update_status_bar()
        if hasattr(self, "_zoom_var"):
            try:
                self._zoom_var.set(f"{self.settings.zoom:.1f}x")
            except Exception:
                pass
        if self.settings.auto_reload_json:
            self._schedule_json_watch()
    
    def _draw_grid(self, draw: ImageDraw.ImageDraw, width: int, height: int):
        """Draw grid on canvas"""
        grid_color = (40, 40, 40)
        for x in range(0, width, self.settings.grid_size):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, self.settings.grid_size):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    
    def _update_status_bar(self):
        """Update status bar with current state and contextual hints."""
        if not hasattr(self, 'status_bar'):
            return
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            self.status_bar.configure(text="No active scene")
            return
        
        widget_count = len(scene.widgets)
        parts = [f"Widgets: {widget_count}", f"Zoom: {self.settings.zoom:.1f}x"]
        if hasattr(self, '_anim_speed_multiplier'):
            state = '▶' if self.playing else '⏸'
            parts.append(f"Anim {state} {self._anim_speed_multiplier:.2f}x")
        
        # Selection info
        if self.selected_widget_idx is not None and self.selected_widget_idx < len(scene.widgets):
            w = scene.widgets[self.selected_widget_idx]
            parts.append(f"Selected: {w.type} ({w.x},{w.y}) {w.width}×{w.height}")
        
        # Multi-selection count
        if len(self.selected_widgets) > 1:
            parts.append(f"{len(self.selected_widgets)} selected")
        if self._pending_component:
            parts.append(f"Placing: {self._pending_component.get('name', 'widget')} (click to place)")
        
        # Live hints based on mode
        hint = self._get_context_hint()
        if hint:
            parts.append(f"💡 {hint}")
        if self._pending_component:
            parts.append("Hint: click to place, Esc/right-click to cancel, Enter to confirm at cursor")
        
        # Performance budget indicators
        if getattr(self.settings, 'performance_budget_enabled', False):
            if getattr(self, '_perf_soft_warn', False):
                parts.append(f"Perf WARN {self._last_render_ms:.1f}ms")
            elif getattr(self, '_perf_over_budget', False):
                parts.append(f"Perf {self._last_render_ms:.1f}>{self.settings.performance_budget_ms:.1f}ms")

        # Profiler live snippet
        if getattr(self, '_profiler_enabled', False):
            parts.append(f"⚡ {self._last_fps:.1f} FPS {self._last_render_ms:.1f}ms")
        self.status_bar.configure(text=" | ".join(parts))

    # ---------------- JSON Hot-Reload Watcher -----------------
    def _schedule_json_watch(self):
        """Schedule polling for JSON design file changes (if enabled)."""
        if HEADLESS or not hasattr(self, 'root'):
            return
        if not self.settings.auto_reload_json:
            return
        if self._json_watch_job is None:
            self._json_watch_job = self.root.after(self._json_watch_interval_ms, self._poll_json_watch)

    def _poll_json_watch(self):
        """Poll last loaded JSON file for external modifications."""
        self._json_watch_job = None
        if not self.settings.auto_reload_json or HEADLESS or not hasattr(self, 'root'):
            return
        path = getattr(self.designer, '_last_loaded_json', None)
        if path and os.path.isfile(path):
            try:
                mtime = os.path.getmtime(path)
                last = getattr(self.designer, '_json_watch_mtime', None)
                if last is not None and mtime > last:
                    # Update mtime first to avoid repeat reloads
                    self.designer._json_watch_mtime = mtime
                    print(f"🔄 JSON file changed, reloading: {os.path.basename(path)}")
                    try:
                        self.designer.load_from_json(path)
                        self._cache_valid = False
                        self.refresh(force=True)
                    except Exception as e:
                        print(f"⚠️ Auto-reload failed: {e}")
            except Exception:
                pass
        # Reschedule if still enabled
        if self.settings.auto_reload_json:
            self._json_watch_job = self.root.after(self._json_watch_interval_ms, self._poll_json_watch)
    
    def _get_context_hint(self) -> str:
        """Get contextual hint based on current state."""
        # Panning mode
        if self._pan_enabled:
            return "Drag to pan • Release Space to exit"
        
        # Dragging/resizing
        if self.dragging:
            if self.resize_handle:
                return "Drag to resize • Shift=constrain"
            else:
                return "Drag to move • Shift=axis lock"
        
        # Multi-selection
        if len(self.selected_widgets) > 1:
            return "Multi-select active • Use Align/Distribute tools"
        
        # Single selection with handles visible
        if self.selected_widget_idx is not None and self.settings.show_handles:
            return "Click handles to resize • Drag to move • Arrows to nudge"
        
        # No selection
        if self.selected_widget_idx is None:
            return "Click widget to select • Right-click for menu • Ctrl+1-9 quick add"
        
        return ""
    
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
        
        # Larger handles for better UX (8px visual, 12px hitbox)
        handle_visual_size = 8
        handle_color = "#00AAFF"
        handle_hover_color = "#00DDFF"  # Brighter on hover
        
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
            # Use hover color if mouse is over this handle
            color = handle_hover_color if handle_type == self.hovered_handle else handle_color
            # Draw larger, more visible handles with border
            self.canvas.create_rectangle(
                hx - handle_visual_size // 2, hy - handle_visual_size // 2,
                hx + handle_visual_size // 2, hy + handle_visual_size // 2,
                fill=color, outline="white", width=2,
                tags=f"handle_{handle_type}"
            )
    
    def _find_alignment_guides(self, widget: WidgetConfig) -> List[Tuple[str, int, str]]:
        """
        Find nearby alignment opportunities with other widgets.
        Returns list of (direction, position, label) where direction is 'h' or 'v'.
        """
        if not self.settings.snap_to_widgets:
            return []
        
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return []
        
        guides = []
        threshold = self.settings.snap_distance
        
        # Widget edges to check
        w_left = widget.x
        w_right = widget.x + widget.width
        w_top = widget.y
        w_bottom = widget.y + widget.height
        w_center_x = widget.x + widget.width // 2
        w_center_y = widget.y + widget.height // 2
        
        # Check against all other widgets
        for idx, other in enumerate(scene.widgets):
            if idx == self.selected_widget_idx:
                continue  # Skip self
            
            o_left = other.x
            o_right = other.x + other.width
            o_top = other.y
            o_bottom = other.y + other.height
            o_center_x = other.x + other.width // 2
            o_center_y = other.y + other.height // 2
            
            # Vertical guides (aligned horizontally)
            if abs(w_left - o_left) <= threshold:
                guides.append(('v', o_left, 'left'))
            if abs(w_left - o_right) <= threshold:
                guides.append(('v', o_right, 'left-to-right'))
            if abs(w_right - o_right) <= threshold:
                guides.append(('v', o_right, 'right'))
            if abs(w_right - o_left) <= threshold:
                guides.append(('v', o_left, 'right-to-left'))
            if abs(w_center_x - o_center_x) <= threshold:
                guides.append(('v', o_center_x, 'center-x'))
            
            # Horizontal guides (aligned vertically)
            if abs(w_top - o_top) <= threshold:
                guides.append(('h', o_top, 'top'))
            if abs(w_top - o_bottom) <= threshold:
                guides.append(('h', o_bottom, 'top-to-bottom'))
            if abs(w_bottom - o_bottom) <= threshold:
                guides.append(('h', o_bottom, 'bottom'))
            if abs(w_bottom - o_top) <= threshold:
                guides.append(('h', o_top, 'bottom-to-top'))
            if abs(w_center_y - o_center_y) <= threshold:
                guides.append(('h', o_center_y, 'center-y'))
        
        return guides
    
    def _apply_widget_snapping(self, widget: WidgetConfig, new_x: int, new_y: int) -> Tuple[int, int]:
        """
        Apply magnetic snapping to widget edges.
        Returns adjusted (x, y) coordinates.
        """
        # Temporarily set position to detect guides
        old_x, old_y = widget.x, widget.y
        widget.x = new_x
        widget.y = new_y
        
        guides = self._find_alignment_guides(widget)
        
        # Restore original position
        widget.x = old_x
        widget.y = old_y
        
        # Apply snapping
        snapped_x, snapped_y = new_x, new_y
        
        for direction, position, label in guides:
            if direction == 'v':  # Vertical guide, snap X
                if 'left' in label:
                    snapped_x = position
                elif 'right' in label:
                    snapped_x = position - widget.width
                elif 'center' in label:
                    snapped_x = position - widget.width // 2
            elif direction == 'h':  # Horizontal guide, snap Y
                if 'top' in label:
                    snapped_y = position
                elif 'bottom' in label:
                    snapped_y = position - widget.height
                elif 'center' in label:
                    snapped_y = position - widget.height // 2
        
        # Update alignment guides for rendering
        widget.x = snapped_x
        widget.y = snapped_y
        self.alignment_guides = self._find_alignment_guides(widget)
        widget.x = old_x
        widget.y = old_y
        
        return snapped_x, snapped_y
    
    

    def _toggle_debug_overlay(self, event=None):
        """Toggle the on-canvas debug overlay (F12)."""
        try:
            self.settings.show_debug_overlay = not getattr(self.settings, 'show_debug_overlay', False)
            self.refresh(force=False)
        except Exception:
            pass

    def _draw_debug_overlay(self):
        """Draw a compact debug overlay with selection and scene info."""
        try:
            z = self.settings.zoom
            x0, y0 = 8, int(self.designer.height * z) - 90
            x1, y1 = x0 + 360, y0 + 82
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#000", outline="#555", stipple="gray25")
            lines = []
            # Scene info
            sc = self.designer.scenes.get(self.designer.current_scene) if self.designer.current_scene else None
            widget_count = len(sc.widgets) if sc else 0
            lines.append(f"Scene: {self.designer.current_scene or '-'}  Size: {self.designer.width}x{self.designer.height}  Zoom: {z:.1f}x  Widgets: {widget_count}")
            # Selection info
            if self.selected_widget_idx is not None and sc and 0 <= self.selected_widget_idx < len(sc.widgets):
                w = sc.widgets[self.selected_widget_idx]
                lines.append(f"Selected[{self.selected_widget_idx}]: {w.type}  pos=({w.x},{w.y}) size={w.width}x{w.height} z={w.z_index} vis={'1' if w.visible else '0'} en={'1' if w.enabled else '0'}")
            else:
                lines.append("Selected: none")
            # Guides hint
            lines.append(f"Guides: {'on' if self.settings.show_alignment_guides else 'off'}  Grid: {'on' if self.settings.grid_enabled else 'off'} Snap: {'on' if self.settings.snap_enabled else 'off'}  Render: {self._last_render_ms:.1f} ms")
            # Paint
            ty = y0 + 10
            for ln in lines:
                self.canvas.create_text(x0 + 10, ty, anchor=tk.NW, text=ln, fill="#fff")
                ty += 14
        except Exception:
            pass

    def _draw_alignment_guides(self):
        """Backwards-compatible shim for tests; delegates to _draw_guides_overlay."""
        try:
            self._draw_guides_overlay()
        except Exception:
            pass

    def _draw_bounds_selected_overlay(self):
        """Draw thin outlines for selected widgets (debug-only overlay)."""
        try:
            if self.selected_widget_idx is None and not self.selected_widgets:
                return
            scene = self.designer.scenes.get(self.designer.current_scene) if self.designer.current_scene else None
            if not scene:
                return
            z = self.settings.zoom
            indices = self.selected_widgets or ([self.selected_widget_idx] if self.selected_widget_idx is not None else [])
            for idx in indices:
                if 0 <= idx < len(scene.widgets):
                    w = scene.widgets[idx]
                    x = int(w.x * z)
                    y = int(w.y * z)
                    rw = int(w.width * z)
                    rh = int(w.height * z)
                    self.canvas.create_rectangle(x, y, x + rw, y + rh, outline="#66FF66", width=1, dash=(2,2))
                    self.canvas.create_text(x + 2, y + 2, anchor=tk.NW, text=f"#{idx} z={getattr(w,'z_index',0)}", fill="#66FF66")
        except Exception:
            pass
    
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
        """Convert canvas event coords to logical widget coords (accounts for scroll + zoom)."""
        # Translate event-local coords through canvas scroll offset
        try:
            abs_x = int(self.canvas.canvasx(canvas_x))
            abs_y = int(self.canvas.canvasy(canvas_y))
        except Exception:
            abs_x, abs_y = canvas_x, canvas_y
        widget_x = int(abs_x / self.settings.zoom)
        widget_y = int(abs_y / self.settings.zoom)
        
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
        
        # Larger hitbox tolerance for easier handle grabbing (12px total area)
        tolerance = 6
        
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
        if self._pending_component:
            self._place_pending_component(event.x, event.y)
            return
        if event.keysym == "Return" and self._last_mouse:
            self._place_pending_component(*self._last_mouse)
            return
        # Pan mode (space held)
        if self._pan_enabled:
            try:
                self.canvas.scan_mark(event.x, event.y)
                self._pan_dragging = True
            except Exception:
                pass
            # Do not start widget interaction while panning
            self.dragging = False
            return
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
            # Clicked on empty canvas - start box select (unless Shift is held to keep selection)
            if not (event.state & 0x0001):  # Clear selection if Shift not pressed
                self.selected_widget_idx = None
                self.selected_widgets = []
            
            # Start box select
            self.box_select_start = (event.x, event.y)
            self.refresh()

    def _on_right_click(self, event):
        """Right click cancels pending placement."""
        if self._pending_component:
            self._cancel_pending_overlay()
            try:
                self.canvas.configure(cursor="arrow")
            except Exception:
                pass
    
    def _place_pending_component(self, canvas_x: int, canvas_y: int) -> None:
        if not self._pending_component:
            return
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            self.designer.create_scene("scene")
            scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        try:
            from ui_designer import WidgetType
            type_map = {
                "label": WidgetType.LABEL,
                "button": WidgetType.BUTTON,
                "box": WidgetType.BOX if hasattr(WidgetType, 'BOX') else WidgetType.PANEL,
                "panel": WidgetType.PANEL,
                "progressbar": WidgetType.PROGRESSBAR,
                "gauge": WidgetType.GAUGE,
                "checkbox": WidgetType.CHECKBOX,
                "slider": WidgetType.SLIDER,
                "icon": WidgetType.LABEL,
            }
            widget_type = type_map.get(self._pending_component["type"], WidgetType.LABEL)
            defaults = self._pending_component.get("defaults", {})
            wx, wy = self._canvas_to_widget_coords(canvas_x, canvas_y)
            self.designer.add_widget(
                widget_type,
                x=wx,
                y=wy,
                width=defaults.get("width", 40),
                height=defaults.get("height", 12),
                text=defaults.get("text", ""),
                value=defaults.get("value", 0),
                checked=defaults.get("checked", False)
            )
            self.selected_widget_idx = len(scene.widgets) - 1
            try:
                if hasattr(self, 'props_frame'):
                    self._edit_widget_properties(self.selected_widget_idx)
            except Exception:
                pass
        finally:
            self._pending_component = None
            self._invalidate_cache()
            self.refresh()
            self._update_status_bar()
            self.designer._save_state()

    def _cancel_pending_overlay(self) -> None:
        if self._pending_component:
            self._pending_component = None
            self._invalidate_cache()
            self.refresh()
            self._update_status_bar()
            try:
                self.canvas.configure(cursor="arrow")
            except Exception:
                pass

    def _toggle_snap_key(self) -> None:
        """Toggle snap via keyboard shortcut."""
        self.settings.snap_enabled = not self.settings.snap_enabled
        if hasattr(self, "snap_var"):
            try:
                self.snap_var.set(self.settings.snap_enabled)
            except Exception:
                pass
        self.refresh()
        self._update_status_bar()
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag"""
        if self._pan_dragging:
            self._drag_pan(event)
            return
        if self._try_box_select_drag(event):
            return
        if not self.dragging or self.selected_widget_idx is None:
            return
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        widget = scene.widgets[self.selected_widget_idx]
        if self.resize_handle:
            self._resize_active_widget(widget, event)
        else:
            self._move_active_widget(widget, event)
        self.refresh()

    def _drag_pan(self, event):
        try:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
        except Exception:
            pass

    def _try_box_select_drag(self, event) -> bool:
        if self.box_select_start is None:
            return False
        x1, y1 = self.box_select_start
        x2, y2 = event.x, event.y
        if self.box_select_rect is not None:
            self.canvas.delete(self.box_select_rect)
        self.box_select_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#00AAFF", width=2, dash=(4, 4),
            tags="box_select"
        )
        return True

    def _resize_active_widget(self, widget, event):
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

    def _move_active_widget(self, widget, event):
        wx, wy = self._canvas_to_widget_coords(event.x, event.y)
        if self.drag_offset is None:
            return
        dx, dy = self.drag_offset
        new_x = wx - dx
        new_y = wy - dy
        if event.state & 0x0001 and self.drag_origin is not None and self.drag_start is not None:
            sx, sy = self.drag_start
            if abs(event.x - sx) >= abs(event.y - sy):
                new_y = self.drag_origin[1]
            else:
                new_x = self.drag_origin[0]
        if self.settings.snap_enabled:
            new_x = round(new_x / self.settings.snap_size) * self.settings.snap_size
            new_y = round(new_y / self.settings.snap_size) * self.settings.snap_size
        if self.settings.snap_to_widgets:
            new_x, new_y = self._apply_widget_snapping(widget, new_x, new_y)
        widget.x = max(0, min(new_x, self.designer.width - widget.width))
        widget.y = max(0, min(new_y, self.designer.height - widget.height))
    
    def _on_mouse_up(self, event):
        """Handle mouse up"""
        if self._pan_dragging:
            self._pan_dragging = False
            return
        
        if self._finish_box_select(event):
            return
        if self.dragging:
            # Save state for undo
            self.designer._save_state()
        
        self.dragging = False
        self.drag_start = None
        self.drag_offset = None
        self.resize_handle = None
        self.drag_origin = None

    def _finish_box_select(self, event) -> bool:
        if self.box_select_start is None:
            return False
        x1, y1 = self.box_select_start
        x2, y2 = event.x, event.y
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene:
            selected_indices = []
            for idx, widget in enumerate(scene.widgets):
                if not widget.visible:
                    continue
                wx1 = int(widget.x * self.settings.zoom)
                wy1 = int(widget.y * self.settings.zoom)
                wx2 = int((widget.x + widget.width) * self.settings.zoom)
                wy2 = int((widget.y + widget.height) * self.settings.zoom)
                if not (wx2 < x1 or wx1 > x2 or wy2 < y1 or wy1 > y2):
                    selected_indices.append(idx)
            if event.state & 0x0001:
                for idx in selected_indices:
                    if idx not in self.selected_widgets:
                        self.selected_widgets.append(idx)
            else:
                self.selected_widgets = selected_indices
            self.selected_widget_idx = self.selected_widgets[0] if self.selected_widgets else None
        if self.box_select_rect is not None:
            self.canvas.delete(self.box_select_rect)
            self.box_select_rect = None
        self.box_select_start = None
        self.refresh()
        return True
    def _on_mouse_move(self, event):
        """Handle mouse move (for cursor changes)"""
        self._last_mouse = (event.x, event.y)
        if self._pending_component:
            self.refresh()
            try:
                self.canvas.configure(cursor="crosshair")
            except Exception:
                pass
        if self.dragging:
            return
        # Hand cursor when panning active
        if self._pan_enabled:
            try:
                self.canvas.configure(cursor="fleur")
            except Exception:
                pass
            return
        
        # Check for resize handle hover
        handle = self._find_resize_handle(event.x, event.y)
        if handle:
            # Update hovered handle state for visual feedback
            if self.hovered_handle != handle:
                self.hovered_handle = handle
                self.refresh()  # Redraw with hover highlight
            
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
            # Clear hover state when not over handle
            if self.hovered_handle is not None:
                self.hovered_handle = None
                self.refresh()  # Redraw without hover
            self.canvas.configure(cursor="arrow")

    def _on_nudge(self, event, dx: int, dy: int):
        """Nudge selected widget with arrow keys.

        Holds Shift to nudge by configurable distance (default: 1px normal, 8px shift).
        """
        if self.selected_widget_idx is None or not self.designer.current_scene:
            return

        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene or not (0 <= self.selected_widget_idx < len(scene.widgets)):
            return

        widget = scene.widgets[self.selected_widget_idx]

        # Use configurable nudge distances
        step = self.settings.nudge_distance
        if event.state & 0x0001:  # Shift key
            step = self.settings.nudge_shift_distance

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
    
    # Advanced animation playback controls
    def _on_anim_step(self):
        """Advance animations by one frame (16ms * speed)."""
        if not self.selected_anim:
            return
        delta = 0.016 * self._anim_speed_multiplier
        vals = self.anim.update_animations(delta)
        self._anim_values = vals
        self._widget_overlays.clear()
        for anim_name, v in vals.items():
            anim = self.anim.animations.get(anim_name)
            if anim and anim.widget_id is not None:
                cur = self._widget_overlays.get(anim.widget_id, {})
                cur.update(v)
                self._widget_overlays[anim.widget_id] = cur
        self.refresh(force=True)

    def _on_anim_speed_down(self):
        self._anim_speed_multiplier = max(0.1, self._anim_speed_multiplier / 2.0)
        self._update_status_bar()

    def _on_anim_speed_up(self):
        self._anim_speed_multiplier = min(4.0, self._anim_speed_multiplier * 2.0)
        self._update_status_bar()

    def _on_anim_speed_reset(self):
        self._anim_speed_multiplier = 1.0
        self._update_status_bar()
    
    def _on_nudge_distance_change(self):
        """Update nudge distance setting"""
        self.settings.nudge_distance = self.nudge_distance_var.get()
    
    def _on_nudge_shift_distance_change(self):
        """Update shift+nudge distance setting"""
        self.settings.nudge_shift_distance = self.nudge_shift_distance_var.get()
    
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
    
    def _open_quick_add_search(self, event=None):
        """Open quick add search dialog for fast component insertion"""
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Quick Add Component")
        dialog.geometry("500x400")
        dialog.configure(bg="#2b2b2b")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Search entry at top
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text=SEARCH_LABEL_TEXT, foreground="#aaa").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 12))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.focus_set()
        
        # Listbox for results
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        results_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                   font=("Arial", 10), bg="#1e1e1e", fg="#ffffff",
                                   selectbackground="#4CAF50", selectforeground="#000000",
                                   height=15)
        results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=results_list.yview)
        
        # Filtered components list
        filtered_components = []
        
        def update_results(*args):
            """Update filtered results based on search text"""
            query = search_var.get().lower().strip()
            self._fill_component_results(query, filtered_components, results_list)
            self._auto_select_first(results_list)
        
        def add_selected_component():
            """Add the selected component to canvas"""
            selection = results_list.curselection()
            if not selection:
                return
            idx = selection[0]
            if idx >= len(filtered_components):
                return
            self._add_component_to_scene(filtered_components[idx], dialog)

        # Bind events
        search_var.trace("w", update_results)
        results_list.bind("<Double-Button-1>", lambda e: add_selected_component())
        results_list.bind(RETURN_KEY, lambda e: add_selected_component())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        # Arrow key navigation
        def on_arrow(event):
            if event.keysym == "Down":
                self._move_list_selection(results_list, +1)
            elif event.keysym == "Up":
                self._move_list_selection(results_list, -1)
        
        search_entry.bind("<Down>", on_arrow)
        search_entry.bind("<Up>", on_arrow)
        search_entry.bind(RETURN_KEY, lambda e: add_selected_component())
        # Bind events
        search_var.trace("w", update_results)
        results_list.bind("<Double-Button-1>", lambda e: add_selected_component())
        results_list.bind(RETURN_KEY, lambda e: add_selected_component())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        # Arrow key navigation
        def on_arrow(event):
            if event.keysym == "Down":
                self._move_list_selection(results_list, +1)
            elif event.keysym == "Up":
                self._move_list_selection(results_list, -1)
        
        search_entry.bind("<Down>", on_arrow)
        search_entry.bind("<Up>", on_arrow)
        search_entry.bind(RETURN_KEY, lambda e: add_selected_component())
        
        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Add Component", 
                  command=add_selected_component).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Initialize with all components
        update_results()
    
    def _edit_widget_properties(self, widget_idx: int):
        """Open widget properties editor (supports multi-selection)"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        # Determine which widgets to edit
        widget_indices = self.selected_widgets if len(self.selected_widgets) > 1 else [widget_idx]
        widgets = [scene.widgets[i] for i in widget_indices if i < len(scene.widgets)]
        
        if not widgets:
            return
        
        # Clear properties panel
        for child in self.props_frame.winfo_children():
            child.destroy()
        
        # Show multi-selection header
        if len(widgets) > 1:
            ttk.Label(self.props_frame, text=f"{len(widgets)} widgets selected", 
                     font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=5)
            ttk.Label(self.props_frame, text="(changes apply to all)", 
                     font=("Arial", 9, "italic")).pack(anchor=tk.W, pady=2)
        else:
            widget = widgets[0]
            ttk.Label(self.props_frame, text=f"Widget: {widget.type}", 
                     font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=5)
        
        # Find common properties
        common_props = set(dir(widgets[0]))
        for w in widgets[1:]:
            common_props &= set(dir(w))
        
        # Text property (if common)
        if 'text' in common_props:
            self._add_text_field(widget_indices, widgets)

        # Label property (if common)
        if 'label' in common_props:
            self._add_label_field(widget_indices, widgets)

        # Value property (if common)
        if 'value' in common_props:
            self._add_value_field(widget_indices, widgets)

        # Color property (if common)
        if 'color' in common_props:
            self._add_color_field(widget_indices, widgets)

        # Position and size (always available for all widgets)
        self._render_position_size_fields(widget_indices, widgets)
    
    def _update_batch_prop(self, widget_indices: list, prop: str, value: Any):
        """Update property for multiple widgets"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        for idx in widget_indices:
            if idx < len(scene.widgets) and hasattr(scene.widgets[idx], prop):
                setattr(scene.widgets[idx], prop, value)
        
        self.designer._save_state()
        self.refresh()
    
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
        """Delete selected widget(s)"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        # Delete all selected widgets
        if self.selected_widgets:
            # Sort indices in reverse order to avoid index shifting issues
            for idx in sorted(self.selected_widgets, reverse=True):
                if idx < len(scene.widgets):
                    del scene.widgets[idx]
            
            self.selected_widget_idx = None
            self.selected_widgets = []
            self.designer._save_state()
            self.refresh()
        elif self.selected_widget_idx is not None:
            # Fallback: delete single selected widget
            if self.selected_widget_idx < len(scene.widgets):
                del scene.widgets[self.selected_widget_idx]
                self.selected_widget_idx = None
                self.designer._save_state()
                self.refresh()
    
    def _on_zoom_change(self, event):
        """Handle zoom change"""
        zoom_str = event.widget.get()
        try:
            new_zoom = float(zoom_str.rstrip('x'))
            # Zoom around canvas center by default for combobox changes
            cx = getattr(self.canvas, 'winfo_width', lambda: 0)() // 2
            cy = getattr(self.canvas, 'winfo_height', lambda: 0)() // 2
            self._apply_zoom_at(cx, cy, new_zoom)
        except ValueError:
            pass

    def _mk_wheel_event(self, e, delta):
        """Create a proxy object carrying delta like MouseWheel events."""
        class _E:
            pass
        ne = _E()
        ne.widget = getattr(e, 'widget', None)
        ne.x = getattr(e, 'x', 0)
        ne.y = getattr(e, 'y', 0)
        ne.delta = delta
        return ne

    def _on_ctrl_wheel_zoom(self, event):
        """Zoom in/out centered at cursor when Ctrl+Wheel is used."""
        # Determine zoom step
        step = 1.1 if event.delta > 0 else (1/1.1)
        new_zoom = max(self._zoom_min, min(self._zoom_max, self.settings.zoom * step))
        self._apply_zoom_at(event.x, event.y, new_zoom)

    def _apply_zoom_at(self, win_x: int, win_y: int, new_zoom: float):
        """Apply zoom keeping the world point under (win_x, win_y) fixed on screen."""
        try:
            # Current absolute canvas coordinates under cursor
            abs_x = self.canvas.canvasx(win_x)
            abs_y = self.canvas.canvasy(win_y)
        except Exception:
            abs_x, abs_y = win_x, win_y
        # World coords before zoom
        old_z = max(self._zoom_min, min(self._zoom_max, self.settings.zoom))
        world_x = abs_x / max(1e-6, old_z)
        world_y = abs_y / max(1e-6, old_z)
        # Apply new zoom
        self.settings.zoom = max(self._zoom_min, min(self._zoom_max, float(new_zoom)))
        self.refresh()
        # Compute new absolute position of that world point
        scaled_w = int(self.designer.width * self.settings.zoom)
        scaled_h = int(self.designer.height * self.settings.zoom)
        new_abs_x = world_x * self.settings.zoom
        new_abs_y = world_y * self.settings.zoom
        # Desired left/top so that cursor stays over same world point
        view_w = getattr(self.canvas, 'winfo_width', lambda: 1)()
        view_h = getattr(self.canvas, 'winfo_height', lambda: 1)()
        left = max(0, min(scaled_w - view_w, int(new_abs_x - win_x)))
        top = max(0, min(scaled_h - view_h, int(new_abs_y - win_y)))
        # Move view
        try:
            self.canvas.xview_moveto(0 if scaled_w <= 0 else left / scaled_w)
            self.canvas.yview_moveto(0 if scaled_h <= 0 else top / scaled_h)
        except Exception:
            pass
        # Sync combobox text
        if hasattr(self, "_zoom_var"):
            try:
                self._zoom_var.set(f"{self.settings.zoom:.1f}x")
            except Exception:
                pass

    def _on_space_down(self, event):
        self._pan_enabled = True
        try:
            self.canvas.configure(cursor="fleur")
        except Exception:
            pass

    def _on_space_up(self, event):
        self._pan_enabled = False
        if not self._pan_dragging:
            try:
                self.canvas.configure(cursor="arrow")
            except Exception:
                pass
    
    def _on_grid_toggle(self):
        """Toggle grid"""
        self.settings.grid_enabled = self.grid_var.get()
        self.refresh()
    
    def _on_snap_toggle(self):
        """Toggle snap"""
        self.settings.snap_enabled = self.snap_var.get()
        self.refresh()
    
    def _on_hints_toggle(self):
        """Toggle on-canvas usage hints"""
        self._show_hints = bool(self.hints_var.get())
        self.refresh()

    def _on_guides_toggle(self):
        """Toggle magnetic guides overlay"""
        self._show_guides = bool(self.guides_var.get())
        self.refresh()
    
    def _choose_bg_color(self):
        """Choose background color"""
        color = colorchooser.askcolor(initialcolor=self.settings.background_color)
        if color[1]:
            self.settings.background_color = color[1]
            self.refresh()
    
    def _export_png(self):
        """Export preview as PNG with preset options"""
        # Show export options dialog
        export_dialog = tk.Toplevel(self.root)
        export_dialog.title("PNG Export Options")
        export_dialog.geometry("350x250")
        export_dialog.transient(self.root)
        export_dialog.grab_set()
        
        # Load last used settings (or defaults)
        last_scale = getattr(self, '_last_export_scale', 1)
        last_guides = getattr(self, '_last_export_guides', False)
        
        # Scale preset
        scale_frame = ttk.LabelFrame(export_dialog, text="Scale", padding=10)
        scale_frame.pack(fill=tk.X, padx=10, pady=5)
        
        scale_var = tk.IntVar(value=last_scale)
        ttk.Radiobutton(scale_frame, text="@1x (Original size)", variable=scale_var, value=1).pack(anchor=tk.W)
        ttk.Radiobutton(scale_frame, text="@2x (Double size)", variable=scale_var, value=2).pack(anchor=tk.W)
        ttk.Radiobutton(scale_frame, text="@3x (Triple size)", variable=scale_var, value=3).pack(anchor=tk.W)
        ttk.Radiobutton(scale_frame, text="@4x (Quadruple size)", variable=scale_var, value=4).pack(anchor=tk.W)
        
        # Content preset
        content_frame = ttk.LabelFrame(export_dialog, text="Content", padding=10)
        content_frame.pack(fill=tk.X, padx=10, pady=5)
        
        guides_var = tk.BooleanVar(value=last_guides)
        ttk.Radiobutton(content_frame, text="Scene only (clean export)", variable=guides_var, value=False).pack(anchor=tk.W)
        ttk.Radiobutton(content_frame, text="With guides (grid/bounds)", variable=guides_var, value=True).pack(anchor=tk.W)
        
        # Buttons
        btn_frame = ttk.Frame(export_dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        result = {"cancelled": True}
        
        def do_export():
            result["cancelled"] = False
            result["scale"] = scale_var.get()
            result["guides"] = guides_var.get()
            # Remember choices
            self._last_export_scale = result["scale"]
            self._last_export_guides = result["guides"]
            export_dialog.destroy()
        
        ttk.Button(btn_frame, text="Export", command=do_export, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=export_dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)
        
        # Wait for dialog
        export_dialog.wait_window()
        
        if result.get("cancelled"):
            return
        
        # Get export settings
        scale = result["scale"]
        include_guides = result["guides"]
        
        # Ask for filename
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), FILETYPE_ALL_PAIR],
            initialfile=f"ui_preview_{scale}x.png"
        )
        
        if not filename:
            return
        
        # Create export image
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene:
            # Temporarily adjust zoom for export scale
            original_zoom = self.settings.zoom
            self.settings.zoom = scale
            
            img = self._render_scene_image(
                scene,
                background_color=self.settings.background_color,
                include_grid=include_guides,
                use_overlays=include_guides,
                highlight_selection=False,
            )
            
            # Restore zoom
            self.settings.zoom = original_zoom
            
            # Save
            img.save(filename)
            messagebox.showinfo(EXPORT_COMPLETE_TITLE, f"Saved @{scale}x PNG to:\n{filename}")
        else:
            messagebox.showerror(EXPORT_ERROR_TITLE, "No scene to export")
    
    def _export_json(self):
        """Export design as JSON"""
        filename = filedialog.asksaveasfilename(
            defaultextension=JSON_EXT,
            filetypes=[("JSON files", JSON_PATTERN), FILETYPE_ALL_PAIR],
            initialfile=f"{self.designer.current_scene}{JSON_EXT}",
        )
        if filename:
            self.designer.save_to_json(filename)
            messagebox.showinfo(EXPORT_COMPLETE_TITLE, f"Saved JSON to: {filename}")

    def _export_c(self):
        """Export design as C code"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".c",
            filetypes=[("C files", "*.c"), FILETYPE_ALL_PAIR],
            initialfile=f"{self.designer.current_scene}.c"
        )
        if filename:
            # Use designer.export_code if available, else fallback
            if hasattr(self.designer, "export_code"):
                self.designer.export_code(filename, self.designer.current_scene)
                messagebox.showinfo(EXPORT_COMPLETE_TITLE, f"Saved C code to: {filename}")
            else:
                messagebox.showerror(EXPORT_ERROR_TITLE, "C code export not implemented.")

    def _export_widgetconfig(self):
        """Export design as WidgetConfig text"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), FILETYPE_ALL_PAIR],
            initialfile=f"{self.designer.current_scene}_widgetconfig.txt"
        )
        if not filename:
            return
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            messagebox.showerror(EXPORT_ERROR_TITLE, "No active scene.")
            return
        try:
            lines = []
            for w in scene.widgets:
                # Simple WidgetConfig ASCII export
                props = [f"{k}={getattr(w, k)}" for k in w.__dataclass_fields__]
                lines.append(f"[{w.type}] " + ", ".join(props))
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo(EXPORT_COMPLETE_TITLE, f"Saved WidgetConfig to: {filename}")
        except Exception as e:
            messagebox.showerror(EXPORT_ERROR_TITLE, f"Failed: {e}")

    def _export_svg(self):
        """Export current scene as enhanced SVG vector file with dialog."""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            messagebox.showerror(EXPORT_ERROR_TITLE, "No scene to export")
            return
        
        # Show enhanced export dialog
        self._show_svg_export_dialog(scene)
    
    def _show_svg_export_dialog(self, scene):
        """Show enhanced SVG export dialog with presets and options"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Enhanced SVG Export")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#2b2b2b")
        
        # Header
        header = ttk.Frame(dialog)
        header.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(header, text="🖼️ Enhanced SVG Export", 
                 font=("Arial", 14, "bold")).pack()
        ttk.Label(header, text="Professional-quality vector export with advanced features",
                 foreground="#888").pack()
        
        # Main content
        content = ttk.Frame(dialog)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Preset selection
        preset_frame = ttk.LabelFrame(content, text="Quality Preset", padding=10)
        preset_frame.pack(fill=tk.X, pady=(0, 10))
        
        preset_var = tk.StringVar(value="web")
        
        presets = [
            ("web", "🌐 Web Optimized", "Smaller file size, gradients enabled"),
            ("print", "🖨️ Print Quality", "Full features for printing"),
            ("hifi", "💎 High Fidelity", "Maximum quality, all features"),
        ]
        
        for value, label, desc in presets:
            frame = ttk.Frame(preset_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(frame, text=label, variable=preset_var, 
                           value=value).pack(side=tk.LEFT)
            ttk.Label(frame, text=desc, foreground="#888", 
                     font=("Arial", 8)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Advanced options
        options_frame = ttk.LabelFrame(content, text="Advanced Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        gradients_var = tk.BooleanVar(value=True)
        shadows_var = tk.BooleanVar(value=False)
        patterns_var = tk.BooleanVar(value=False)
        fonts_var = tk.BooleanVar(value=False)
        metadata_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Include Gradients (smoother colors)", 
                       variable=gradients_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Include Shadows (depth effects)", 
                       variable=shadows_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Include Patterns (textures)", 
                       variable=patterns_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Embed Fonts (requires font file)", 
                       variable=fonts_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Include Metadata", 
                       variable=metadata_var).pack(anchor=tk.W, pady=2)
        
        # Scale
        scale_frame = ttk.LabelFrame(content, text="Export Scale", padding=10)
        scale_frame.pack(fill=tk.X, pady=(0, 10))
        
        scale_var = tk.DoubleVar(value=1.0)
        scale_slider = ttk.Scale(scale_frame, from_=0.5, to=4.0, 
                                variable=scale_var, orient=tk.HORIZONTAL)
        scale_slider.pack(fill=tk.X, pady=2)
        
        scale_label = ttk.Label(scale_frame, text="1.0x")
        scale_label.pack()
        
        def update_scale_label(*args):
            scale_label.config(text=f"{scale_var.get():.1f}x")
        scale_var.trace_add("write", update_scale_label)
        
        # Font path (conditional)
        font_frame = ttk.LabelFrame(content, text="Font Embedding (Optional)", padding=10)
        font_frame.pack(fill=tk.X, pady=(0, 10))
        
        font_path_var = tk.StringVar(value="")
        font_entry = ttk.Entry(font_frame, textvariable=font_path_var, state="readonly")
        font_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        def browse_font():
            path = filedialog.askopenfilename(
                title="Select Font File",
                filetypes=[
                    ("Font files", "*.ttf *.otf *.woff *.woff2"),
                    FILETYPE_ALL_PAIR
                ]
            )
            if path:
                font_path_var.set(path)
        
        ttk.Button(font_frame, text="Browse...", command=browse_font).pack(side=tk.LEFT)
        
        # Update options based on preset
        def update_from_preset(*args):
            preset = preset_var.get()
            if preset == "web":
                gradients_var.set(True)
                shadows_var.set(False)
                patterns_var.set(False)
                fonts_var.set(False)
            elif preset == "print":
                gradients_var.set(True)
                shadows_var.set(True)
                patterns_var.set(True)
                fonts_var.set(False)
            elif preset == "hifi":
                gradients_var.set(True)
                shadows_var.set(True)
                patterns_var.set(True)
                fonts_var.set(True)
        
        preset_var.trace_add("write", update_from_preset)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        def do_export():
            filename = filedialog.asksaveasfilename(
                defaultextension=".svg",
                filetypes=[("SVG files", "*.svg"), FILETYPE_ALL_PAIR],
                initialfile=f"{self.designer.current_scene}_enhanced.svg"
            )
            if not filename:
                return
            
            try:
                # Build options
                options = ExportOptions(
                    preset=ExportPreset(preset_var.get()),
                    scale=scale_var.get(),
                    include_gradients=gradients_var.get(),
                    include_shadows=shadows_var.get(),
                    include_patterns=patterns_var.get(),
                    embed_fonts=fonts_var.get(),
                    font_path=font_path_var.get() or None,
                    include_metadata=metadata_var.get(),
                )
                
                exporter = EnhancedSVGExporter(options)
                exporter.export_scene(scene, filename)
                
                dialog.destroy()
                messagebox.showinfo(EXPORT_COMPLETE_TITLE, 
                                  f"Enhanced SVG exported to:\n{filename}\n\n"
                                  f"Preset: {preset_var.get().upper()}\n"
                                  f"Features: Gradients={gradients_var.get()}, "
                                  f"Shadows={shadows_var.get()}, "
                                  f"Patterns={patterns_var.get()}")
            except Exception as e:
                messagebox.showerror(EXPORT_ERROR_TITLE, f"Failed to export:\n{e}")
        
        ttk.Button(button_frame, text="Cancel", 
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Export SVG", 
                  command=do_export).pack(side=tk.RIGHT, padx=5)

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
        ttk.Button(toolbar, text=REFRESH_LABEL, command=lambda: self._refresh_ascii_preview(text_widget, scene)).pack(side=tk.LEFT, padx=5)
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

    def _show_ascii_tab(self):
        """Show the inline ASCII Preview tab and refresh its content."""
        if getattr(self, '_headless', False):
            return
        try:
            # Select ASCII tab
            for i in range(self.right_tabs.index('end')):
                if self.right_tabs.tab(i, 'text') == 'ASCII Preview':
                    self.right_tabs.select(i)
                    break
            # Refresh content
            scene = self.designer.scenes.get(self.designer.current_scene)
            if scene and hasattr(self, 'ascii_text_widget'):
                self._refresh_ascii_preview(self.ascii_text_widget, scene)
        except Exception:
            pass
    
    def _show_quick_help(self):
        """Show quick usage cheatsheet."""
        help_text = (
            "Drag: Move widget | Corners/Edges: Resize\n"
            "Shift+Drag: Axis lock | Shift+Click: Multi-select\n"
            "Arrows: Nudge | Shift+Arrows: Nudge by grid\n"
            "Ctrl+C/V: Copy/Paste | Ctrl+D: Duplicate | Delete: Remove\n"
            "Right-click: Context menu | Grid/Snap/Hints in toolbar"
        )
        try:
            messagebox.showinfo("Designer Help", help_text)
        except Exception:
            pass
        
    def _refresh_ascii_preview(self, text_widget, scene):
        """Refresh ASCII preview with syntax highlighting (robust resolution).

        Previously this assumed a valid scene object was always passed. Some
        test/code paths supply None or a scene key; handle those gracefully and
        show a fallback message if no scene can be resolved instead of raising.
        """
        # Resolve scene if a key or None was provided
        try:
            if scene is None:
                if getattr(self.designer, "current_scene", None):
                    scene = self.designer.scenes.get(self.designer.current_scene)
            elif isinstance(scene, str):  # scene name key
                scene = self.designer.scenes.get(scene)
        except Exception:
            scene = None

        text_widget.config(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)

        if not scene:
            # Fallback content when no scene available
            text_widget.insert(tk.END, "[no scene]")
            text_widget.config(state=tk.DISABLED)
            return

        try:
            ascii_lines = self._render_ascii_scene(scene)
        except Exception as e:
            ascii_lines = [f"[ascii render error: {e.__class__.__name__}]"]

        for line in ascii_lines:
            for char in line:
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

    def _draw_hints_overlay(self):
        """Draw a small on-canvas hint box with basic instructions."""
        try:
            # Background box
            x0, y0 = 8, 8
            x1, y1 = 8 + 360, 8 + 56
            # Simulated translucency via stipple
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#000", outline="#444", stipple="gray25")
            lines = [
                "Drag to move • Resize via corners/edges",
                "Shift+Drag=axis lock • Shift+Click=multi-select",
                "Arrows nudge (Shift=grid) • Right-click menu",
                "Toolbar: Grid • Snap • Hints • Export • Help",
            ]
            ty = y0 + 10
            for ln in lines:
                self.canvas.create_text(x0 + 10, ty, anchor=tk.NW, text=ln, fill="#fff")
                ty += 14
        except Exception:
            pass

    def _compute_alignment_guides(self) -> List[Tuple[str, int]]:
        """Compute alignment guide lines ('v', x) and ('h', y) for the selected widget.

        Guides indicate near alignment between the selected widget edges/centers
        and other visible widgets. Does not change positions; purely visual.
        """
        if self.selected_widget_idx is None or not self.designer.current_scene:
            return []
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene or not (0 <= self.selected_widget_idx < len(scene.widgets)):
            return []

        target = scene.widgets[self.selected_widget_idx]
        lx, rx = target.x, target.x + target.width
        cx = target.x + target.width // 2
        ty, by = target.y, target.y + target.height
        cy = target.y + target.height // 2

        # Tolerance: prefer snap size or a small default window
        tol = max(2, int(getattr(self.settings, 'snap_size', 4)))

        # Track nearest deltas for left/center/right and top/middle/bottom
        nearest_v = {"left": (10**9, None), "center": (10**9, None), "right": (10**9, None)}
        nearest_h = {"top": (10**9, None), "middle": (10**9, None), "bottom": (10**9, None)}

        for idx, w, _, _ in self._iter_visible_widgets(scene):
            if idx == self.selected_widget_idx:
                continue
            wl, wr = w.x, w.x + w.width
            wc = w.x + w.width // 2
            wt, wb = w.y, w.y + w.height
            wm = w.y + w.height // 2

            # Vertical alignment candidates (x positions)
            for key, target_x in (("left", lx), ("center", cx), ("right", rx)):
                for other_x in (wl, wc, wr):
                    d = abs(target_x - other_x)
                    if d < nearest_v[key][0]:
                        nearest_v[key] = (d, other_x)

            # Horizontal alignment candidates (y positions)
            for key, target_y in (("top", ty), ("middle", cy), ("bottom", by)):
                for other_y in (wt, wm, wb):
                    d = abs(target_y - other_y)
                    if d < nearest_h[key][0]:
                        nearest_h[key] = (d, other_y)

        guides: List[Tuple[str, int]] = []
        # Use nearest within tolerance per category to avoid clutter
        for key in ("left", "center", "right"):
            dist, x_pos = nearest_v[key]
            if x_pos is not None and dist <= tol:
                guides.append(("v", int(x_pos)))
        for key in ("top", "middle", "bottom"):
            dist, y_pos = nearest_h[key]
            if y_pos is not None and dist <= tol:
                guides.append(("h", int(y_pos)))
        return guides

    def _draw_guides_overlay(self):
        """Draw magnetic alignment guide lines on the canvas during drag/resize."""
        try:
            guides = self._compute_alignment_guides()
            if not guides:
                return
            z = self.settings.zoom
            # Canvas extents in pixels (zoomed)
            width_px = int(self.designer.width * z)
            height_px = int(self.designer.height * z)
            color = "#00FF88"
            for orient, pos in guides:
                if orient == "v":
                    x = int(pos * z)
                    self.canvas.create_line(x, 0, x, height_px, fill=color, dash=(4, 2), width=1)
                else:
                    y = int(pos * z)
                    self.canvas.create_line(0, y, width_px, y, fill=color, dash=(4, 2), width=1)
        except Exception:
            pass

    def _on_context_menu(self, event):
        """Show context menu with common actions."""
        try:
            # Detect widget under cursor and select it
            idx = self._find_widget_at(event.x, event.y)
            if idx is not None:
                self.selected_widget_idx = idx
                if idx not in self.selected_widgets:
                    self.selected_widgets = [idx]
                self.refresh()

            menu = tk.Menu(self.canvas, tearoff=0)
            if self.selected_widget_idx is not None:
                menu.add_command(label="Properties…", command=lambda: self._edit_widget_properties(self.selected_widget_idx))
                menu.add_command(label="Duplicate", command=lambda: self._on_duplicate(None))
                menu.add_command(label="Delete", command=lambda: self._on_delete_widget(None))
                menu.add_separator()
            # Quick add submenu
            add_menu = tk.Menu(menu, tearoff=0)
            for label, kind in (
                ("Label", "label"), ("Button", "button"), ("Box", "box"), ("Panel", "panel"),
                ("Progress", "progressbar"), ("Gauge", "gauge"), ("Checkbox", "checkbox"), ("Slider", "slider"),
            ):
                add_menu.add_command(label=f"{label}", command=lambda k=kind: self._palette_add(k))
            menu.add_cascade(label="Add", menu=add_menu)
            # Show
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    def _render_ascii_scene(self, scene, use_cache=True):
        """Render the scene as ASCII art with enhanced visuals and caching"""
        if self._can_return_cached_ascii(scene, use_cache):
            return self._ascii_cache  # type: ignore
        buf = self._init_ascii_buffer(scene)
        for _, w, _, _ in self._iter_visible_widgets(scene):
            self._draw_widget_ascii(scene, buf, w)
        lines = self._finalize_ascii_buffer(scene, buf)
        return lines

    def _can_return_cached_ascii(self, scene, use_cache: bool) -> bool:
        if not use_cache:
            return False
        if not (self._ascii_cache_valid and self._ascii_cache is not None):
            return False
        current_sig = self._compute_scene_signature(scene)
        return self._last_ascii_signature == current_sig

    def _init_ascii_buffer(self, scene) -> List[List[str]]:
        return [[" " for _ in range(scene.width)] for _ in range(scene.height)]

    def _draw_widget_ascii(self, scene, buf: List[List[str]], w: WidgetConfig) -> None:
        fill_char = self._get_widget_fill_char(w)
        max_y = min(w.y + w.height, scene.height)
        max_x = min(w.x + w.width, scene.width)
        large = (w.width >= 3 and w.height >= 3)
        for y in range(w.y, max_y):
            is_top = (y == w.y)
            is_bottom = (y == w.y + w.height - 1)
            for x in range(w.x, max_x):
                if large:
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
                    buf[y][x] = fill_char
        if hasattr(w, "text") and w.text and large and w.width >= len(w.text) + 2:
            text_x = w.x + 1
            text_y = w.y + w.height // 2
            if text_y < scene.height:
                for i, char in enumerate(w.text[: w.width - 2]):
                    if text_x + i < scene.width:
                        buf[text_y][text_x + i] = char

    def _finalize_ascii_buffer(self, scene, buf: List[List[str]]) -> List[str]:
        lines = ["".join(row) for row in buf]
        self._ascii_cache = lines
        self._ascii_cache_valid = True
        self._last_ascii_signature = self._compute_scene_signature(scene)
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
            defaultextension=JSON_EXT,
            filetypes=[("JSON files", JSON_PATTERN), FILETYPE_ALL_PAIR],
            initialfile=f"{self.designer.current_scene}{JSON_EXT}",
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
            for widget in widgets[1:-1]:
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
            for widget in widgets[1:-1]:
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
        self._update_status_bar()
    
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
        self._update_status_bar()
    
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
    
    def _on_quick_insert(self, index):
        """Handle number key press for quick insert."""
        try:
            if not (0 <= index < len(self.quick_insert_components)):
                return

            component = self.quick_insert_components[index]

            # Headless test path: add immediately
            if not hasattr(self, 'canvas'):
                scene = self.designer.scenes.get(self.designer.current_scene)
                if not scene:
                    self.designer.create_scene("test_scene")
                    scene = self.designer.scenes.get(self.designer.current_scene)
                from ui_designer import WidgetType
                type_map = {
                    "label": WidgetType.LABEL,
                    "button": WidgetType.BUTTON,
                    "box": WidgetType.BOX if hasattr(WidgetType, 'BOX') else WidgetType.PANEL,
                    "panel": WidgetType.PANEL,
                    "progressbar": WidgetType.PROGRESSBAR,
                    "gauge": WidgetType.GAUGE,
                    "checkbox": WidgetType.CHECKBOX,
                    "slider": WidgetType.SLIDER,
                    "icon": WidgetType.LABEL,
                }
                widget_type = type_map.get(component["type"], WidgetType.LABEL)
                defaults = component.get("defaults", {})
                self.designer.add_widget(
                    widget_type,
                    x=10,
                    y=10,
                    width=defaults.get("width", 40),
                    height=defaults.get("height", 12),
                    text=defaults.get("text", ""),
                    value=defaults.get("value", 0),
                    checked=defaults.get("checked", False)
                )
                self.selected_widget_idx = len(scene.widgets) - 1
                return

            # GUI placement: set pending component to show preview until click
            self._pending_component = component
            self._invalidate_cache()
            self.refresh()
            self._update_status_bar()

        except Exception as e:
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(text=f"Failed to insert: {e}")
            else:
                raise

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
            vals = self.anim.update_animations(0.016 * self._anim_speed_multiplier)
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

    def _iter_visible_widgets(self, scene):
        """Yield (idx, widget, overlay, is_selected) for visible widgets in draw order."""
        for idx, widget in enumerate(getattr(scene, 'widgets', [])):
            if not getattr(widget, 'visible', True):
                continue
            overlay = self._widget_overlays.get(idx, {})
            yield idx, widget, overlay, (idx == self.selected_widget_idx)

    def _render_scene_image(
        self,
        scene,
        background_color: Optional[str] = None,
        include_grid: bool = True,
        use_overlays: bool = True,
        highlight_selection: bool = True,
    ) -> Image.Image:
        """Render the given scene into a PIL Image using current settings.

        - Respects background color and optional grid.
        - Can draw with/without overlays and selection highlighting.
        """
        img_width = self.designer.width
        img_height = self.designer.height
        bg_hex = background_color or self.settings.background_color
        bg_color = self._hex_to_rgb(bg_hex)
        img = Image.new("RGB", (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(img)

        if include_grid:
            self._draw_grid(draw, img_width, img_height)

        for _idx, widget, overlay, is_sel in self._iter_visible_widgets(scene):
            ov = overlay if use_overlays else None
            sel = is_sel if highlight_selection else False
            self._draw_widget(draw, widget, sel, ov)

        if self._pending_component and self._last_mouse:
            defaults = self._pending_component.get("defaults", {})
            pw = int(defaults.get("width", 40))
            ph = int(defaults.get("height", 20))
            # Snap preview to snap/grid if enabled
            x = int(self._last_mouse[0])
            y = int(self._last_mouse[1])
            if self.settings.snap_enabled and self.settings.snap_size > 0:
                size = self.settings.snap_size
                x = round(x / size) * size
                y = round(y / size) * size
            elif self.settings.grid_enabled and self.settings.grid_size > 0:
                size = self.settings.grid_size
                x = (x // size) * size
                y = (y // size) * size
            x = max(0, min(self.designer.width - pw, x))
            y = max(0, min(self.designer.height - ph, y))
            if pw > 0 and ph > 0 and hasattr(draw, "rectangle"):
                try:
                    from PIL import ImageDraw as _ID  # type: ignore
                    overlay = Image.new("RGBA", (self.designer.width, self.designer.height), (0, 0, 0, 0))
                    o_draw = _ID.Draw(overlay)
                    o_draw.rectangle([(x, y), (x + pw, y + ph)], fill=self._pending_fill, outline=(0, 200, 255, 150), width=1)
                    img.paste(overlay, (0, 0), overlay)
                except Exception:
                    draw.rectangle([(x, y), (x + pw, y + ph)], outline=(0, 200, 255), width=1)
            name = self._pending_component.get("name", "widget")
            try:
                draw.text((x + 2, y + 2), f"Preview: {name}", fill=(0, 220, 255))
                draw.text((x + 2, y + 16), f"{pw}×{ph} @ {x},{y}", fill=(0, 220, 255))
            except Exception:
                pass

        return img

    def _compute_scene_signature(self, scene) -> int:
        """Compute a lightweight signature of scene content to validate caches.

        Only includes properties that affect visual output. This avoids stale caches
        when widget count stays the same but positions/text/values change.
        """
        try:
            items: List[Tuple[Any, ...]] = []
            # Include canvas/background parameters
            items.append((getattr(scene, 'width', self.designer.width),
                          getattr(scene, 'height', self.designer.height),
                          self.settings.background_color,
                          self.settings.grid_enabled,
                          self.settings.grid_size))
            for w in scene.widgets:
                # Collect common properties defensively
                items.append((
                    getattr(w, 'type', None),
                    getattr(w, 'x', None), getattr(w, 'y', None),
                    getattr(w, 'width', None), getattr(w, 'height', None),
                    getattr(w, 'text', None),
                    getattr(w, 'value', None), getattr(w, 'checked', None),
                    getattr(w, 'color_fg', None), getattr(w, 'color_bg', None),
                    getattr(w, 'border', None), getattr(w, 'border_style', None),
                    getattr(w, 'visible', True),
                ))
            return hash(tuple(items))
        except Exception:
            # Fallback to changing number to force re-render in error cases
            return object.__hash__(scene)


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
        except Exception:
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
        anim_combo.bind(COMBO_SELECTED, self._on_anim_selected)
        
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
        easing_combo.bind(COMBO_SELECTED, self._on_easing_changed)
        
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
        for pct in [0, 0.25, 0.5, 0.75, 1.0]:
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
            messagebox.showwarning(NO_ANIMATION_TITLE, NO_ANIMATION_MSG, parent=self.window)
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
            messagebox.showwarning(NO_ANIMATION_TITLE, NO_ANIMATION_MSG,
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
            messagebox.showwarning(NO_ANIMATION_TITLE, NO_ANIMATION_MSG,
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
            messagebox.showinfo(EXPORT_COMPLETE_TITLE, 
                              f"Animation exported to:\n{header_file}\n{impl_file}",
                              parent=self.window)
        
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {str(e)}",
                               parent=self.window)

if TK_AVAILABLE:
    # ---------------- Component / Template / Icon Palette Windows -----------------
    class ComponentPaletteWindow(tk.Toplevel):
        """Component library manager with search, preview, and insert."""

        def __init__(self, root, preview: 'VisualPreviewWindow'):
            super().__init__(root)
            self.title("Component Library")
            self.configure(bg="#2b2b2b")
            self.preview = preview
            self.geometry("640x520")
            self.recent = getattr(preview, 'recent_components', [])
            preview.recent_components = self.recent  # ensure attribute
            self._build_ui()

        def _build_ui(self):
            top = ttk.Frame(self)
            top.pack(fill=tk.X, padx=8, pady=6)
            ttk.Label(top, text=SEARCH_LABEL_TEXT).pack(side=tk.LEFT)
            self.search_var = tk.StringVar()
            entry = ttk.Entry(top, textvariable=self.search_var, width=32)
            entry.pack(side=tk.LEFT, padx=6)
            entry.bind(KEY_RELEASE, lambda e: self._refresh_list())
            # Category dropdown
            ttk.Label(top, text="Category:").pack(side=tk.LEFT)
            self.category_var = tk.StringVar(value="All")
            self.category_combo = ttk.Combobox(top, textvariable=self.category_var, width=14, state="readonly")
            self.category_combo.pack(side=tk.LEFT, padx=6)
            self.category_combo.bind(COMBO_SELECTED, lambda e: self._refresh_list())
            # Tags entry
            ttk.Label(top, text="Tags:").pack(side=tk.LEFT)
            self.tags_var = tk.StringVar()
            tags_entry = ttk.Entry(top, textvariable=self.tags_var, width=18)
            tags_entry.pack(side=tk.LEFT, padx=6)
            tags_entry.bind(KEY_RELEASE, lambda e: self._refresh_list())
            ttk.Button(top, text="Close", command=self.destroy).pack(side=tk.RIGHT)

            body = ttk.Frame(self)
            body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

            self.listbox = tk.Listbox(body, bg="#1e1e1e", fg="#eee", selectbackground="#4CAF50")
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_preview())
            self.listbox.bind(RETURN_KEY, lambda e: self._insert_selected())

            right = ttk.Frame(body)
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
            ttk.Label(right, text="Preview:").pack(anchor=tk.W)
            self.preview_text = tk.Text(right, height=20, bg="#111", fg="#ddd", state=tk.DISABLED)
            self.preview_text.pack(fill=tk.BOTH, expand=True)
            btn_row = ttk.Frame(right)
            btn_row.pack(fill=tk.X, pady=4)
            ttk.Button(btn_row, text="Insert", command=self._insert_selected).pack(side=tk.LEFT)
            ttk.Button(btn_row, text="Add ButtonGroup", command=lambda: self._insert_component("ButtonGroup")).pack(side=tk.LEFT, padx=4)

            self._build_library()
            self._refresh_list()

        def _build_library(self):
            self._entries = []
            seen = set()

            def make_tags(text: str):
                base = (text or '').lower().replace(',', ' ').split()
                return [t for t in base if len(t) > 2][:10]

            for comp in self.preview.ascii_components:
                name = comp.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                cat = comp.get("category", "Misc")
                desc = comp.get("description", "")
                self._entries.append({
                    'name': name,
                    'category': cat,
                    'desc': desc,
                    'factory': comp.get("factory"),
                    'tags': make_tags(name + ' ' + desc)
                })
            for qi in self.preview.quick_insert_components:
                name = qi.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                cat = 'Quick'
                desc = f"Quick insert {qi.get('type')}"
                self._entries.append({
                    'name': name,
                    'category': cat,
                    'desc': desc,
                    'defaults': qi.get('defaults'),
                    'type': qi.get('type'),
                    'tags': make_tags(name + ' ' + desc)
                })
            # Add recent pseudo entries
            for r in self.recent:
                if r not in seen:
                    self._entries.append({
                        'name': r,
                        'category': 'Recent',
                        'desc': 'Recently used component',
                        'tags': make_tags(r)
                    })
            self._entries.sort(key=lambda e: (e['category'], e['name']))
            cats = sorted({e['category'] for e in self._entries})
            if 'Recent' in cats:
                cats.remove('Recent')
                cats.insert(0, 'Recent')
            self.category_combo['values'] = ['All'] + cats

        def _refresh_list(self):
            term = self.search_var.get().lower().strip()
            cat = self.category_var.get()
            tags_filter = [t for t in self.tags_var.get().lower().split() if t]
            self.listbox.delete(0, tk.END)
            for e in self._entries:
                if cat != 'All' and e['category'] != cat:
                    continue
                if term and term not in e['name'].lower() and term not in e.get('desc', '').lower():
                    continue
                if tags_filter and not all(any(tf in tag for tag in e.get('tags', [])) for tf in tags_filter):
                    continue
                self.listbox.insert(tk.END, f"{e['name']}  [{e['category']}]")

        def _get_selected_entry(self):
            sel = self.listbox.curselection()
            if not sel:
                return None
            label = self.listbox.get(sel[0])
            name = label.split('  [', 1)[0]
            for e in self._entries:
                if e['name'] == name:
                    return e
            return None

        def _show_preview(self):
            e = self._get_selected_entry()
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete('1.0', tk.END)
            if not e:
                self.preview_text.insert(tk.END, 'No selection')
            else:
                self.preview_text.insert(tk.END, f"{e['name']}\n{e.get('desc', '')}\n\n")
                if e.get('factory'):
                    try:
                        ascii_art = e['factory']()
                        ascii_lines = ascii_art if isinstance(ascii_art, (list, tuple)) else str(ascii_art).splitlines()
                        for ln in ascii_lines:
                            self.preview_text.insert(tk.END, ln + '\n')
                    except Exception as ex:
                        self.preview_text.insert(tk.END, f"[preview error: {ex}]")
                elif e.get('defaults'):
                    self.preview_text.insert(tk.END, f"Widget defaults: {e['defaults']}")
            self.preview_text.config(state=tk.DISABLED)

        def _insert_selected(self):
            e = self._get_selected_entry()
            if e:
                self._insert_component(e['name'])

        def _insert_component(self, name: str):
            scene = self.preview.designer.scenes.get(self.preview.designer.current_scene) if self.preview.designer.current_scene else None
            if not scene:
                return
            cx = max(0, scene.width // 2 - 30)
            cy = max(0, scene.height // 2 - 10)
            entry = next((e for e in self._entries if e['name'] == name), None)
            if not entry:
                return
            wtype = entry.get('type') or 'label'
            defaults = entry.get('defaults', {})
            if wtype == 'label':
                widget_enum = WidgetType.LABEL
            elif wtype == 'button':
                widget_enum = WidgetType.BUTTON
            else:
                widget_enum = WidgetType.PANEL
            self.preview.designer.add_widget(
                widget_enum,
                x=cx,
                y=cy,
                width=defaults.get('width', 40),
                height=defaults.get('height', 12),
                text=defaults.get('text', name),
                value=defaults.get('value', 0),
                checked=defaults.get('checked', False)
            )
            self.preview.selected_widget_idx = len(scene.widgets) - 1
            self.preview._invalidate_cache()
            self.preview.refresh(force=True)
            # Track recent usage (MRU up to 12)
            if name not in self.recent:
                self.recent.insert(0, name)
            else:
                self.recent.remove(name)
                self.recent.insert(0, name)
            if len(self.recent) > 12:
                self.recent = self.recent[:12]
            self._build_library()
            self._refresh_list()

    class IconPaletteWindow(tk.Toplevel):
        """Icon palette with search, category filter and insertion.

        Keeps implementation lightweight: textual list + metadata preview
        (no raster glyph rendering). Designed to work within existing
        project style and without introducing new dependencies.
        """
        def __init__(self, root, preview: 'VisualPreviewWindow'):
            super().__init__(root)
            from ui_icons import (  # local import to avoid startup cost headless
                filter_icons,
                get_all_categories,
            )
            self.title("Icon Palette")
            self.configure(bg="#2b2b2b")
            self.preview = preview
            self.geometry("640x420")
            self.resizable(True, True)
            self._filter_fn = filter_icons
            self._all_categories = ["All"] + get_all_categories()
            self._icons: List[dict] = []
            self._build_ui()
            self._refresh_list()

        # ---------------- UI construction -----------------
        def _build_ui(self):
            top = ttk.Frame(self)
            top.pack(fill=tk.X, padx=8, pady=6)
            ttk.Label(top, text=SEARCH_LABEL_TEXT).pack(side=tk.LEFT)
            self.search_var = tk.StringVar()
            ent = ttk.Entry(top, textvariable=self.search_var, width=28)
            ent.pack(side=tk.LEFT, padx=6)
            ent.bind(KEY_RELEASE, lambda e: self._refresh_list())

            ttk.Label(top, text="Category:").pack(side=tk.LEFT)
            self.cat_var = tk.StringVar(value="All")
            cat_combo = ttk.Combobox(top, textvariable=self.cat_var, values=self._all_categories, width=16, state="readonly")
            cat_combo.pack(side=tk.LEFT, padx=6)
            cat_combo.bind(COMBO_SELECTED, lambda e: self._refresh_list())

            ttk.Button(top, text="Close", command=self.destroy).pack(side=tk.RIGHT)

            body = ttk.Frame(self)
            body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

            # Icon list
            self.listbox = tk.Listbox(body, bg="#1e1e1e", fg="#eee", selectbackground="#1976d2")
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_preview())
            self.listbox.bind(RETURN_KEY, lambda e: self._insert_selected())

            # Right panel
            right = ttk.Frame(body)
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
            ttk.Label(right, text="Preview:").pack(anchor=tk.W)
            self.preview_text = tk.Text(right, height=14, bg="#111", fg="#ddd", state=tk.DISABLED, wrap=tk.WORD)
            self.preview_text.pack(fill=tk.BOTH, expand=True)

            btn_row = ttk.Frame(right)
            btn_row.pack(fill=tk.X, pady=4)
            ttk.Button(btn_row, text="Insert", command=self._insert_selected).pack(side=tk.LEFT)
            ttk.Button(btn_row, text="Insert 16px", command=lambda: self._insert_selected(size_variant="size_16")).pack(side=tk.LEFT, padx=4)
            ttk.Button(btn_row, text="Insert 24px", command=lambda: self._insert_selected(size_variant="size_24")).pack(side=tk.LEFT, padx=4)
            ttk.Button(btn_row, text="Export C", command=self._export_c_header).pack(side=tk.LEFT, padx=4)

        # ---------------- Data / filtering -----------------
        def _refresh_list(self):
            from ui_icons import filter_icons  # reimport (hot-reload safe)
            term = self.search_var.get()
            cat = self.cat_var.get()
            category = None if cat == "All" else cat
            self._icons = filter_icons(term, category)
            self.listbox.delete(0, tk.END)
            for icon in self._icons:
                self.listbox.insert(tk.END, f"{icon['ascii']}  {icon['name']}  ({icon['symbol']})")
            self._show_preview()  # update preview if selection persists

        def _get_selected_icon(self):
            sel = self.listbox.curselection()
            if not sel or sel[0] >= len(self._icons):
                return None
            return self._icons[sel[0]]

        # ---------------- Preview / insertion -----------------
        def _show_preview(self):
            icon = self._get_selected_icon()
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            if not icon:
                self.preview_text.insert(tk.END, "No icon selected")
            else:
                self.preview_text.insert(tk.END, f"Name: {icon['name']}\n")
                self.preview_text.insert(tk.END, f"Category: {icon['category']}\n")
                self.preview_text.insert(tk.END, f"Symbol: {icon['symbol']}\n")
                self.preview_text.insert(tk.END, f"ASCII: {icon['ascii']}\n")
                self.preview_text.insert(tk.END, f"Usage: {icon['usage']}\n")
            self.preview_text.config(state=tk.DISABLED)

        def _insert_selected(self, size_variant: Optional[str] = None):
            icon = self._get_selected_icon()
            if not icon:
                return
            scene = self.preview.designer.scenes.get(self.preview.designer.current_scene)
            if not scene:
                return
            ascii_char = icon['ascii']
            # Basic sizing based on variant
            if size_variant == 'size_24':
                w = 24
            else:
                w = 16
            h = w
            x = max(0, (self.preview.designer.width - w) // 2)
            y = max(0, (self.preview.designer.height - h) // 2)
            from ui_designer import WidgetType
            self.preview.designer.add_widget(
                WidgetType.ICON,
                x=x,
                y=y,
                width=w,
                height=h,
                icon_char=ascii_char
            )
            self.preview.selected_widget_idx = len(scene.widgets) - 1
            self.preview.designer._save_state()
            self.preview._invalidate_cache()
            self.preview.refresh(force=True)

        # ---------------- Export helper -----------------
        def _export_c_header(self):
            """Export selected icon as a tiny C header snippet (ASCII fallback)."""
            icon = self._get_selected_icon()
            if not icon:
                return
            from tkinter import filedialog, messagebox
            path = filedialog.asksaveasfilename(defaultextension=".h", filetypes=[("Header", "*.h"), ("All", "*.*")], initialfile=f"icon_{icon['symbol']}.h")
            if not path:
                return
            guard = f"ICON_{icon['symbol'].upper()}_H".replace('-', '_')
            content = (
                f"#ifndef {guard}\n#define {guard}\n\n/* Auto-generated single-character icon fallback */\n#define ICON_{icon['symbol'].upper()} \"{icon['ascii']}\" /* {icon['name']} */\n\n#endif /* {guard} */\n"
            )
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Export", f"C header saved: {path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"{e}")
else:
    ComponentPaletteWindow = None  # type: ignore
    IconPaletteWindow = None  # type: ignore

if __name__ == "__main__":
    # Headless CLI for automated preview/export
    parser = argparse.ArgumentParser(description="UI Designer Preview (GUI/Headless)")
    parser.add_argument("--headless-preview", action="store_true", help="Run a headless PNG export without Tk (JSON-driven)")
    parser.add_argument("--headless", action="store_true", help="Run headless PNG export with a default scene if no JSON provided")
    parser.add_argument("--in-json", dest="in_json", help="Path to a UI Designer JSON file")
    parser.add_argument("--out-png", dest="out_png", help="Output PNG file path")
    parser.add_argument("--out-html", dest="out_html", help="Optional output HTML path (export from designer)")
    parser.add_argument("--scene", dest="scene", help="Optional scene name to render")
    parser.add_argument("--bg", dest="bg", default="#000000", help="Background color for PNG (default: #000000)")
    args, _unknown = parser.parse_known_args()

    run_headless = args.headless_preview or args.headless
    if run_headless and args.out_png:
        try:
            # Force headless
            os.environ["ESP32OS_HEADLESS"] = "1"
            from ui_designer import UIDesigner, WidgetConfig, WidgetType
            # Use a larger default canvas for meaningful PNG size when no JSON is provided
            designer = UIDesigner(320, 240) if not args.in_json else UIDesigner()
            if args.in_json:
                designer.load_from_json(args.in_json)
                if args.scene and args.scene in designer.scenes:
                    designer.current_scene = args.scene
                if not designer.current_scene:
                    raise SystemExit(1)
            else:
                # Create a minimal default scene for simple headless preview
                designer.create_scene("Preview")
                # Add a centered label and a panel background to ensure non-empty image
                sc = designer.scenes.get(designer.current_scene)
                if sc:
                    # Simple background panel
                    designer.add_widget(WidgetType.PANEL, x=4, y=4, width=max(8, sc.width-8), height=max(6, sc.height-8), text="", color_bg="#101010")
                    # Centered label
                    label_text = "ESP32OS Preview"
                    lw = max(40, len(label_text) + 12)
                    lh = 16
                    designer.add_widget(WidgetType.LABEL, x=(sc.width - lw)//2, y=(sc.height - lh)//2, width=lw, height=lh, text=label_text, border=False)
                    # Progress bar and gauge to add content
                    designer.add_widget(WidgetType.PROGRESSBAR, x=40, y=sc.height - 40, width=sc.width - 80, height=12, value=65, min_value=0, max_value=100)
                    designer.add_widget(WidgetType.GAUGE, x=sc.width - 60, y=20, width=40, height=40, value=75)

            vp = VisualPreviewWindow(designer)
            scene = designer.scenes.get(designer.current_scene)
            if scene is None:
                raise SystemExit(1)
            img = vp._render_scene_image(scene, background_color=args.bg, include_grid=False, use_overlays=False, highlight_selection=False)
            # Ensure output directory exists
            try:
                odir = os.path.dirname(os.path.abspath(args.out_png))
                if odir:
                    os.makedirs(odir, exist_ok=True)
            except Exception:
                pass
            img.save(args.out_png)
            # Optional HTML export
            if args.out_html:
                try:
                    designer.export_to_html(args.out_html)
                except Exception:
                    pass
            raise SystemExit(0)
        except SystemExit as se:
            raise se
        except Exception as e:
            try:
                print(f"[headless-preview] Failed: {e}")
            except Exception:
                pass
            raise SystemExit(1)
    else:
        # No CLI headless args; do nothing (GUI usage via import)
        raise SystemExit(0)

SEARCH_LABEL_TEXT = "Search:"
RETURN_KEY = "<Return>"
EXPORT_COMPLETE_TITLE = "Export Complete"
NO_ANIMATION_TITLE = "No Animation"
NO_ANIMATION_MSG = "Select an animation first"
KEY_RELEASE = "<KeyRelease>"
