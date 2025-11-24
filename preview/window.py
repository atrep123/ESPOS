"""Visual Preview Window - Main GUI window class"""

from __future__ import annotations

import json
import os
import tempfile
import time
import tracemalloc
from typing import Any, Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, ttk
    from tkinter import font as tkfont
except Exception:
    tk = None
    colorchooser = filedialog = messagebox = ttk = tkfont = None

TK_AVAILABLE = tk is not None
HEADLESS = os.environ.get("ESP32OS_HEADLESS") == "1" or os.environ.get("PYTEST_CURRENT_TEST") is not None

from PIL import Image, ImageDraw

if TK_AVAILABLE:
    from PIL import ImageTk

from preview.rendering import (
    hex_to_rgb,
)
from preview.settings import PreviewSettings
from preview.diagnostics import layout_warnings
from ui_animations import AnimationDesigner

# Import all component creators
try:
    # Explicit imports to avoid lint ambiguity from wildcard
    from ui_components_library_ascii import (
        AnimationEditorWindow,
        ComponentPaletteWindow,
        IconPaletteWindow,
        TemplateManagerWindow,
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
except Exception:
    try:
        from tools.ui_components_library_ascii import (
            AnimationEditorWindow,
            ComponentPaletteWindow,
            IconPaletteWindow,
            TemplateManagerWindow,
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
    except Exception:
        # Fallback stubs to avoid NameError; minimal no-op implementations
        class _StubWin:  # type: ignore
            def __init__(self, *a, **kw):
                pass
        AnimationEditorWindow = ComponentPaletteWindow = TemplateManagerWindow = IconPaletteWindow = _StubWin  # type: ignore
        def _stub_list(): return []
        def create_alert_dialog_ascii(): return _stub_list()
        def create_confirm_dialog_ascii(): return _stub_list()
        def create_input_dialog_ascii(): return _stub_list()
        def create_tab_bar_ascii(): return _stub_list()
        def create_vertical_menu_ascii(): return _stub_list()
        def create_breadcrumb_ascii(): return _stub_list()
        def create_stat_card_ascii(): return _stub_list()
        def create_progress_card_ascii(): return _stub_list()
        def create_status_indicator_ascii(): return _stub_list()
        def create_button_group_ascii(): return _stub_list()
        def create_toggle_switch_ascii(): return _stub_list()
        def create_radio_group_ascii(): return _stub_list()
        def create_header_footer_layout_ascii(): return _stub_list()
        def create_sidebar_layout_ascii(): return _stub_list()
        def create_grid_layout_ascii(): return _stub_list()
        def create_slider_ascii(): return _stub_list()
        def create_checkbox_ascii(): return _stub_list()
        def create_notification_ascii(): return _stub_list()
        def create_chart_ascii(): return _stub_list()

# Import performance profiler
try:
    from performance_profiler import PerformanceProfiler
except Exception:
    try:
        from tools.performance_profiler import PerformanceProfiler
    except Exception:
        class PerformanceProfiler:
            def __init__(self, *args, **kwargs):
                self.history_size = kwargs.get("history_size", 0)
            def calculate_stats(self):
                class Stats:
                    fps_avg = fps_min = fps_max = 0.0
                    render_avg_ms = render_min_ms = render_max_ms = 0.0
                    frame_avg_ms = frame_min_ms = frame_max_ms = 0.0
                    memory_avg_mb = memory_peak_mb = 0.0
                    cpu_avg_percent = cpu_peak_percent = 0.0
                    samples = 0
                return Stats()
            def analyze_performance(self):
                return []
            def export_to_html(self, *args, **kwargs):
                return None
            def export_to_csv(self, *args, **kwargs):
                return None
            def export_to_json(self, *args, **kwargs):
                return None
            def record_frame(self, *args, **kwargs):
                return None

# Import designer
try:
    from ui_designer import UIDesigner, WidgetConfig, WidgetType, color_hex
except Exception:
    from tools.ui_designer import UIDesigner, WidgetConfig, WidgetType, color_hex

# Import SVG exporter
try:
    from svg_export_enhanced import EnhancedSVGExporter, ExportOptions, ExportPreset
except Exception:
    from tools.svg_export_enhanced import EnhancedSVGExporter, ExportOptions, ExportPreset

# Constants
DATA_DISPLAY = "Data Display"
COMBO_SELECTED = "<<ComboboxSelected>>"
REFRESH_LABEL = "🔄 Refresh"
FILETYPE_ALL_PAIR = ("All Files", "*.*")
PROFILER_DISABLED_MSG = "Profiler not enabled"
EXPORT_ERROR_TITLE = "Export Error"
JSON_EXT = ".json"
JSON_PATTERN = "*.json"
SEARCH_LABEL_TEXT = "Search:"
RETURN_KEY = "<Return>"
EXPORT_COMPLETE_TITLE = "Export Complete"
NO_ANIMATION_TITLE = "No Animation"
NO_ANIMATION_MSG = "Select an animation first"
KEY_RELEASE = "<KeyRelease>"

class VisualPreviewWindow:
    """Graphical preview window with mouse interaction"""

    # Centralized event string constants for maintainability and future tweaks
    EVT_MOUSE_LEFT = "<Button-1>"
    EVT_MOUSE_RIGHT = "<Button-3>"
    EVT_MOUSE_LEFT_DOUBLE = "<Double-Button-1>"
    EVT_MOUSE_DRAG_LEFT = "<B1-Motion>"
    EVT_MOUSE_LEFT_RELEASE = "<ButtonRelease-1>"
    EVT_MOUSE_MOVE = "<Motion>"
    EVT_MOUSE_CTRL_WHEEL = "<Control-MouseWheel>"
    EVT_CONTEXT_CTRL_LEFT = "<Control-Button-1>"
    EVT_KEY_DELETE = "<Delete>"
    EVT_KEY_UNDO = "<Control-z>"
    EVT_KEY_REDO = "<Control-y>"
    EVT_KEY_SAVE = "<Control-s>"
    EVT_KEY_COPY = "<Control-c>"
    EVT_KEY_PASTE = "<Control-v>"
    EVT_KEY_RETURN = "<Return>"

    def __init__(self, designer: UIDesigner):
        self.designer = designer
        self.settings = PreviewSettings()
        self.anim = AnimationDesigner()
        # UX helpers
        # On-canvas usage hints (disabled by default to keep canvas clear)
        self._show_hints: bool = False
        self._show_guides: bool = True
        self._responsive_tier: str = "medium"
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
        # Auto-fit/zoom state
        self._auto_fit_job = None
        # Performance profiler
        self._profiler: Optional[PerformanceProfiler] = None
        self._profiler_enabled: bool = False
        self._last_fps: float = 0.0
        # Responsive scaling helper (spacing/font) from design tokens
        try:
            from design_tokens import responsive_scalars  # type: ignore

            self._responsive_scalars = responsive_scalars
        except Exception:
            self._responsive_scalars = lambda width, height=None: {
                "tier": "medium",
                "spacing_scale": 1.0,
                "font_scale": 1.0,
            }
        # Auto-fit zoom is applied once after layout
        self._auto_fit_done: bool = False
        # Shared settings storage (temp dir, reused for quick tips/recents)
        settings_dir = os.path.join(tempfile.gettempdir(), "esp32os_designer")
        os.makedirs(settings_dir, exist_ok=True)
        self._settings_path = os.path.join(settings_dir, "settings.json")
        self._settings_cache: Dict[str, Any] = self._load_settings()
        self._recent_components: List[str] = list(self._settings_cache.get("recent_components", []))
        self._favorite_components: List[str] = list(
            self._settings_cache.get("favorite_components", [])
        )
        self._preview_theme: str = str(self._settings_cache.get("preview_theme", "default"))
        self._last_export_theme: str = str(self._settings_cache.get("last_export_theme", "current"))
        self._component_filter_default: str = str(
            self._settings_cache.get("component_filter_default", "all")
        )
        # Persisted grid padding preferences
        try:
            self.settings.grid_padding_pct = float(
                self._settings_cache.get("grid_padding_pct", self.settings.grid_padding_pct)
            )
            self.settings.grid_padding_min_px = int(
                self._settings_cache.get("grid_padding_min_px", self.settings.grid_padding_min_px)
            )
        except Exception:
            pass

        # Pan/zoom runtime state
        self._pan_enabled: bool = False  # Space held
        self._pan_dragging: bool = False
        self._zoom_min: float = 0.5
        self._zoom_max: float = 10.0

        # Box select state
        self.box_select_start = None  # (canvas_x, canvas_y) or None
        self.box_select_rect = None  # Canvas rectangle ID or None
        self._box_select_count: int = 0
        self._box_select_label = None  # Canvas text ID
        # Mini help overlay toggle
        self._show_mini_help: bool = False
        self._onboarding_toast_tag = "onboarding_toast"
        self._show_perf_overlay: bool = bool(self._settings_cache.get("perf_overlay", False))
        # Diagnostics state
        self._diagnostics_enabled: bool = False
        self._fps_history: List[float] = []
        self._fps_history_max: int = 60  # keep last 60 frames (~1s at 60fps)
        self._memory_peak: Optional[int] = None
        self._diagnostics_last_draw_ts: float = 0.0

        # Quick insert components (for Ctrl+1-9 shortcuts)
        self.quick_insert_components = [
            {
                "type": "label",
                "name": "Label",
                "defaults": {"text": "Label", "width": 40, "height": 10},
            },
            {
                "type": "button",
                "name": "Button",
                "defaults": {"text": "Button", "width": 40, "height": 12},
            },
            {"type": "box", "name": "Box", "defaults": {"width": 50, "height": 30}},
            {"type": "panel", "name": "Panel", "defaults": {"width": 60, "height": 40}},
            {
                "type": "progressbar",
                "name": "Progress Bar",
                "defaults": {"value": 50, "width": 60, "height": 8},
            },
            {
                "type": "gauge",
                "name": "Gauge",
                "defaults": {"value": 75, "width": 30, "height": 30},
            },
            {
                "type": "checkbox",
                "name": "Checkbox",
                "defaults": {"text": "Check", "checked": False, "width": 50, "height": 10},
            },
            {
                "type": "slider",
                "name": "Slider",
                "defaults": {"value": 50, "width": 60, "height": 8},
            },
            {"type": "icon", "name": "Icon", "defaults": {"width": 16, "height": 16}},
        ]
        self._load_quick_slots_from_settings()

        # ASCII component palette definitions
        self.ascii_components = [
            {
                "name": "AlertDialog",
                "category": "Dialogs",
                "description": "Alert dialog with OK button",
                "factory": lambda: create_alert_dialog_ascii(),
            },
            {
                "name": "ConfirmDialog",
                "category": "Dialogs",
                "description": "Confirmation dialog with Yes/No buttons",
                "factory": lambda: create_confirm_dialog_ascii(),
            },
            {
                "name": "InputDialog",
                "category": "Dialogs",
                "description": "Input dialog with text field",
                "factory": lambda: create_input_dialog_ascii(),
            },
            {
                "name": "TabBar",
                "category": "Navigation",
                "description": "Tab bar with 3 tabs",
                "factory": lambda: create_tab_bar_ascii(),
            },
            {
                "name": "VerticalMenu",
                "category": "Navigation",
                "description": "Vertical menu list",
                "factory": lambda: create_vertical_menu_ascii(),
            },
            {
                "name": "Breadcrumb",
                "category": "Navigation",
                "description": "Breadcrumb navigation",
                "factory": lambda: create_breadcrumb_ascii(),
            },
            {
                "name": "StatCard",
                "category": DATA_DISPLAY,
                "description": "Statistics card with value and label",
                "factory": lambda: create_stat_card_ascii(),
            },
            {
                "name": "ProgressCard",
                "category": DATA_DISPLAY,
                "description": "Progress card with percentage",
                "factory": lambda: create_progress_card_ascii(),
            },
            {
                "name": "StatusIndicator",
                "category": DATA_DISPLAY,
                "description": "Status indicator with colored dot",
                "factory": lambda: create_status_indicator_ascii(),
            },
            {
                "name": "ButtonGroup",
                "category": "Controls",
                "description": "Button group with 3 buttons",
                "factory": lambda: create_button_group_ascii(),
            },
            {
                "name": "ToggleSwitch",
                "category": "Controls",
                "description": "Toggle switch control",
                "factory": lambda: create_toggle_switch_ascii(),
            },
            {
                "name": "RadioGroup",
                "category": "Controls",
                "description": "Radio button group",
                "factory": lambda: create_radio_group_ascii(),
            },
            {
                "name": "HeaderFooterLayout",
                "category": "Layouts",
                "description": "Layout with header, content, and footer",
                "factory": lambda: create_header_footer_layout_ascii(),
            },
            {
                "name": "SidebarLayout",
                "category": "Layouts",
                "description": "Layout with sidebar and main content",
                "factory": lambda: create_sidebar_layout_ascii(),
            },
            {
                "name": "GridLayout",
                "category": "Layouts",
                "description": "Grid layout",
                "factory": lambda: create_grid_layout_ascii(),
            },
            {
                "name": "Slider",
                "category": "Controls",
                "description": "Value slider with visual bar",
                "factory": lambda: create_slider_ascii(),
            },
            {
                "name": "Checkbox",
                "category": "Controls",
                "description": "Checkbox with label",
                "factory": lambda: create_checkbox_ascii(),
            },
            {
                "name": "Notification",
                "category": DATA_DISPLAY,
                "description": "Notification banner (info/success/error/warning)",
                "factory": lambda: create_notification_ascii(),
            },
            {
                "name": "Chart",
                "category": DATA_DISPLAY,
                "description": "Simple bar chart",
                "factory": lambda: create_chart_ascii(),
            },
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
        # Slider interaction state (so dragging the thumb doesn't move the whole widget)
        self._slider_drag_idx: Optional[int] = None
        self._slider_value_changed: bool = False

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
        headless_env = (
            os.environ.get("ESP32OS_HEADLESS") == "1"
            or os.environ.get("PYTEST_CURRENT_TEST") is not None
        )
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
        self.root.configure(bg=color_hex("legacy_gray4"))

        # Setup UI with theme (theme will configure all ttk styles)
        self._apply_theme(self._preview_theme)
        self._setup_ui()
        self._setup_bindings()
        self._auto_size_window()

        # Initial render
        self.refresh()
        # Apply auto-fit zoom after layout settles (once)
        try:
            self.root.after(50, self._apply_auto_zoom_fit)
            self.root.after(800, self._show_onboarding_toast_if_needed)
        except Exception:
            pass

    def _draw_perf_overlay(self):
        """Draw a compact perf HUD with render time vs budget."""
        try:
            budget = getattr(self.settings, "performance_budget_ms", 16.7)
            warn = getattr(self.settings, "performance_warn_ms", 25.0)
            ms = self._last_render_ms
            w = self._scale_spacing(160, minimum=120)
            h = self._scale_spacing(48, minimum=36)
            pad = self._scale_spacing(8, minimum=6)
            x0 = self._scale_spacing(12, minimum=8)
            y0 = self._scale_spacing(12, minimum=8)
            x1 = x0 + w
            y1 = y0 + h
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray8"),
                stipple="gray25",
            )
            # Bar
            bar_width = w - 2 * pad
            bar_height = self._scale_spacing(12, minimum=10)
            bx0 = x0 + pad
            by0 = y0 + pad
            bx1 = bx0 + bar_width
            by1 = by0 + bar_height
            self.canvas.create_rectangle(bx0, by0, bx1, by1, outline=color_hex("legacy_gray8"))
            if bar_width > 0:
                frac = min(1.5, ms / max(1e-6, budget))
                fill_w = max(1, int(bar_width * frac / 1.5))
                if ms > warn:
                    fill_color = color_hex("legacy_dracula_red")
                elif ms > budget:
                    fill_color = color_hex("legacy_orange")
                else:
                    fill_color = color_hex("legacy_green")
                self.canvas.create_rectangle(
                    bx0, by0, bx0 + fill_w, by1, fill=fill_color, outline=""
                )
            # Text
            txt = f"{ms:.1f} ms (budget {budget:.1f} / warn {warn:.1f})"
            self.canvas.create_text(
                x0 + pad,
                by1 + pad,
                anchor=tk.NW,
                text=txt,
                fill=color_hex("text_primary"),
                font=("TkDefaultFont", self._scale_font_size(9, minimum=8)),
            )
        except Exception:
            pass
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

        # Main content area with resizable panes
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        panes = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)

        # Zoom controls
        ttk.Label(toolbar, text="Zoom:").pack(side=tk.LEFT, padx=5)
        self._zoom_var = tk.StringVar(value=f"{self.settings.zoom:.1f}x")
        self._zoom_combo = ttk.Combobox(
            toolbar,
            textvariable=self._zoom_var,
            width=6,
            values=["0.5x", "1.0x", "2.0x", "4.0x", "6.0x", "8.0x", "10.0x"],
        )
        self._zoom_combo.pack(side=tk.LEFT, padx=5)
        self._zoom_combo.bind(COMBO_SELECTED, self._on_zoom_change)
        ttk.Button(toolbar, text="Fit", command=lambda: self._on_zoom_fit()).pack(
            side=tk.LEFT, padx=(2, 8)
        )

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Grid toggle
        self.grid_var = tk.BooleanVar(value=self.settings.grid_enabled)
        ttk.Checkbutton(
            toolbar, text="Grid", variable=self.grid_var, command=self._on_grid_toggle
        ).pack(side=tk.LEFT, padx=5)

        # Grid padding controls
        ttk.Label(toolbar, text="Pad %:").pack(side=tk.LEFT, padx=(8, 2))
        self._grid_pad_var = tk.DoubleVar(value=self.settings.grid_padding_pct * 100.0)
        pad_spin = ttk.Spinbox(
            toolbar,
            from_=0.0,
            to=50.0,
            increment=1.0,
            width=5,
            textvariable=self._grid_pad_var,
            command=self._on_grid_padding_change,
        )
        pad_spin.pack(side=tk.LEFT, padx=2)
        pad_spin.bind(self.EVT_KEY_RETURN, lambda e: self._on_grid_padding_change())

        ttk.Label(toolbar, text="Min px:").pack(side=tk.LEFT, padx=(6, 2))
        self._grid_pad_min_var = tk.IntVar(value=self.settings.grid_padding_min_px)
        pad_min_spin = ttk.Spinbox(
            toolbar,
            from_=0,
            to=20,
            increment=1,
            width=4,
            textvariable=self._grid_pad_min_var,
            command=self._on_grid_padding_change,
        )
        pad_min_spin.pack(side=tk.LEFT, padx=2)
        pad_min_spin.bind(self.EVT_KEY_RETURN, lambda e: self._on_grid_padding_change())

        # Snap toggle
        self.snap_var = tk.BooleanVar(value=self.settings.snap_enabled)
        ttk.Checkbutton(
            toolbar, text="Snap", variable=self.snap_var, command=self._on_snap_toggle
        ).pack(side=tk.LEFT, padx=5)

        # Hints toggle
        self.hints_var = tk.BooleanVar(value=self._show_hints)
        ttk.Checkbutton(
            toolbar, text="Hints", variable=self.hints_var, command=self._on_hints_toggle
        ).pack(side=tk.LEFT, padx=5)

        # Guides toggle
        self.guides_var = tk.BooleanVar(value=self._show_guides)
        ttk.Checkbutton(
            toolbar, text="Guides", variable=self.guides_var, command=self._on_guides_toggle
        ).pack(side=tk.LEFT, padx=5)

        # High-contrast overlay toggle
        self.hc_var = tk.BooleanVar(value=self.settings.high_contrast_overlays)
        ttk.Checkbutton(
            toolbar, text="HC UI", variable=self.hc_var, command=self._on_hc_toggle
        ).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Alignment tools
        ttk.Label(toolbar, text="Align:").pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="⬅", width=3, command=lambda: self._align_widgets("left")).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⬆", width=3, command=lambda: self._align_widgets("top")).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⬇", width=3, command=lambda: self._align_widgets("bottom")).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="➡", width=3, command=lambda: self._align_widgets("right")).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(
            toolbar, text="↔", width=3, command=lambda: self._align_widgets("center_h")
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            toolbar, text="↕", width=3, command=lambda: self._align_widgets("center_v")
        ).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Distribute tools
        ttk.Label(toolbar, text="Distribute:").pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar, text="H", width=3, command=lambda: self._distribute_widgets("horizontal")
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            toolbar, text="V", width=3, command=lambda: self._distribute_widgets("vertical")
        ).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Export buttons
        ttk.Button(toolbar, text="📷 Export PNG", command=self._export_png).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="🖼️ Export SVG", command=self._export_svg).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="💾 Export JSON", command=self._export_json).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="📝 Export C", command=self._export_c).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📄 Export WidgetConfig", command=self._export_widgetconfig).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="👁️ Live ASCII Preview", command=self._show_ascii_tab).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="❓ Help", command=self._show_quick_help).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="⚡ Profiler", command=self._toggle_profiler).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(toolbar, text=REFRESH_LABEL, command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar,
            text="📸 Shot",
            command=self._screenshot_canvas
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🚀 Push", command=self._push_stub).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar,
            text="🔎 Layout",
            command=self._show_layout_warnings,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="🩺 Diag",
            command=self._toggle_diagnostics,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Animation controls
        ttk.Label(toolbar, text="Animation:").pack(side=tk.LEFT, padx=5)
        self.anim_combo = ttk.Combobox(toolbar, values=self.anim.list_animations(), width=14)
        if self.anim.list_animations():
            self.anim_combo.set(self.anim.list_animations()[0])
            self.selected_anim = self.anim.list_animations()[0]
        self.anim_combo.pack(side=tk.LEFT)
        self.anim_combo.bind(COMBO_SELECTED, self._on_anim_change)
        ttk.Button(toolbar, text="▶", width=3, command=self._on_anim_play).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⏸", width=3, command=self._on_anim_pause).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⏹", width=3, command=self._on_anim_stop).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="✏", width=3, command=self._open_animation_editor).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⤴", width=3, command=self._on_anim_step).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="½x", width=3, command=self._on_anim_speed_down).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="2x", width=3, command=self._on_anim_speed_up).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="1x", width=3, command=self._on_anim_speed_reset).pack(
            side=tk.LEFT, padx=1
        )

        # Background color
        ttk.Button(toolbar, text="🎨 BG Color", command=self._choose_bg_color).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(toolbar, text="Theme:").pack(side=tk.LEFT, padx=(8, 2))
        self._theme_var = tk.StringVar(value=self._preview_theme)
        theme_options = ["default", "light", "dark", "nord", "dracula", "hc", "cyber"]
        self._theme_combo = ttk.Combobox(
            toolbar, values=theme_options, width=10, textvariable=self._theme_var
        )
        self._theme_combo.pack(side=tk.LEFT, padx=2)
        self._theme_combo.bind(
            COMBO_SELECTED, lambda e: self._on_theme_change(self._theme_var.get())
        )

        # Left-side palette (widget add shortcuts)
        palette = ttk.Frame(panes)

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
        ttk.Button(palette, text="📦 Components", command=self._open_component_palette).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(palette, text="📑 Templates", command=self._open_template_manager).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(palette, text="🎨 Icons", command=self._open_icon_palette).pack(
            fill=tk.X, pady=2
        )

        # Canvas frame with scrollbars (center area)
        canvas_frame = ttk.Frame(panes)
        canvas_frame.pack_propagate(False)
        self._canvas_frame = canvas_frame

        # Canvas
        canvas_width = int(self.designer.width * self.settings.zoom)
        canvas_height = int(self.designer.height * self.settings.zoom)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=canvas_width,
            height=canvas_height,
            bg=color_hex("surface"),
            highlightthickness=1,
            highlightbackground=color_hex("legacy_gray8"),
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbars
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        # Context menu bindings (Right-click / Ctrl+Click)
        self.canvas.bind("<Button-3>", self._on_context_menu)
        self.canvas.bind("<Control-Button-1>", self._on_context_menu)
        # Re-fit canvas when the container resizes (panes drag/resize)
        canvas_frame.bind("<Configure>", lambda e: self._schedule_auto_zoom_fit(reset_override=True))

        # Right-side panel with tabs (Properties, ASCII)
        right_panel = ttk.Frame(panes)

        self.right_tabs = ttk.Notebook(right_panel)
        self.right_tabs.pack(fill=tk.BOTH, expand=True)

        # Properties tab
        props_container = ttk.Frame(self.right_tabs)
        self.right_tabs.add(props_container, text="Properties")

        # Settings section at top (nudge distances, grid, snap)
        settings_frame = ttk.LabelFrame(
            props_container, text="Editor Settings", padding=self._scale_spacing(10, minimum=6)
        )
        settings_frame.pack(fill=tk.X, padx=5, pady=5)

        # Nudge distance settings
        ttk.Label(settings_frame, text="Nudge Distance:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.nudge_distance_var = tk.IntVar(value=self.settings.nudge_distance)
        nudge_spin = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=16,
            width=8,
            textvariable=self.nudge_distance_var,
            command=self._on_nudge_distance_change,
        )
        nudge_spin.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(settings_frame, text="px", foreground=color_hex("legacy_gray1")).grid(
            row=0, column=2, sticky=tk.W
        )

        ttk.Label(settings_frame, text="Shift+Nudge:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.nudge_shift_distance_var = tk.IntVar(value=self.settings.nudge_shift_distance)
        nudge_shift_spin = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=32,
            width=8,
            textvariable=self.nudge_shift_distance_var,
            command=self._on_nudge_shift_distance_change,
        )
        nudge_shift_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(settings_frame, text="px", foreground=color_hex("legacy_gray1")).grid(
            row=1, column=2, sticky=tk.W
        )

        ttk.Separator(settings_frame, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=8
        )

        # Grid/Snap settings
        ttk.Label(settings_frame, text="Grid Size:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.grid_size_var = tk.IntVar(value=self.settings.grid_size)
        grid_spin = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=32,
            width=8,
            textvariable=self.grid_size_var,
            command=lambda: setattr(self.settings, "grid_size", self.grid_size_var.get())
            or self.refresh(),
        )
        grid_spin.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(settings_frame, text="px", foreground=color_hex("legacy_gray1")).grid(
            row=3, column=2, sticky=tk.W
        )

        # Batch edit panel (multi-select position/size deltas)
        batch_frame = ttk.LabelFrame(
            props_container,
            text="Batch Edit (Multi-Select)",
            padding=self._scale_spacing(10, minimum=6),
        )
        batch_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        self.batch_dx_var = tk.StringVar(value="0")
        self.batch_dy_var = tk.StringVar(value="0")
        self.batch_dw_var = tk.StringVar(value="0")
        self.batch_dh_var = tk.StringVar(value="0")

        ttk.Label(batch_frame, text="ΔX").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(batch_frame, width=6, textvariable=self.batch_dx_var).grid(
            row=0, column=1, sticky=tk.W, padx=4
        )
        ttk.Label(batch_frame, text="ΔY").grid(row=0, column=2, sticky=tk.W, pady=2)
        ttk.Entry(batch_frame, width=6, textvariable=self.batch_dy_var).grid(
            row=0, column=3, sticky=tk.W, padx=4
        )
        ttk.Label(batch_frame, text="ΔW").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(batch_frame, width=6, textvariable=self.batch_dw_var).grid(
            row=1, column=1, sticky=tk.W, padx=4
        )
        ttk.Label(batch_frame, text="ΔH").grid(row=1, column=2, sticky=tk.W, pady=2)
        ttk.Entry(batch_frame, width=6, textvariable=self.batch_dh_var).grid(
            row=1, column=3, sticky=tk.W, padx=4
        )
        ttk.Button(batch_frame, text="Apply to Selection", command=self._on_batch_apply).grid(
            row=0, column=4, rowspan=2, padx=8, pady=2
        )
        ttk.Button(batch_frame, text="Reset", command=self._on_batch_reset).grid(
            row=0, column=5, rowspan=2, padx=4, pady=2
        )

        self.props_frame = ttk.Frame(props_container, padding=self._scale_spacing(10, minimum=6))
        self.props_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self.props_frame, text="No widget selected").pack()

        # ASCII Preview tab
        ascii_container = ttk.Frame(self.right_tabs)
        self.right_tabs.add(ascii_container, text="ASCII Preview")

        ascii_toolbar = ttk.Frame(ascii_container)
        ascii_toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Label(ascii_toolbar, text="ASCII Renderer v2.0", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, padx=5
        )
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
            bg=color_hex("legacy_gray5"),
            fg=color_hex("legacy_gray9"),
            insertbackground=color_hex("text_primary"),
            yscrollcommand=ascii_scrollbar.set,
            wrap=tk.NONE,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.ascii_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ascii_scrollbar.config(command=self.ascii_text_widget.yview)
        # Syntax highlighting tags
        self.ascii_text_widget.tag_config("border", foreground=color_hex("legacy_blue_light"))
        self.ascii_text_widget.tag_config("fill_button", foreground=color_hex("legacy_teal"))
        self.ascii_text_widget.tag_config("fill_box", foreground=color_hex("legacy_gray10"))
        self.ascii_text_widget.tag_config("fill_icon", foreground=color_hex("legacy_gold"))
        self.ascii_text_widget.tag_config("text_label", foreground=color_hex("legacy_salmon"))

        # Wire toolbar actions now that widgets exist
        self._ascii_refresh_btn.configure(
            command=lambda: self._refresh_ascii_preview(
                self.ascii_text_widget, self.designer.scenes.get(self.designer.current_scene)
            )
        )
        self._ascii_copy_btn.configure(
            command=lambda: self._copy_ascii_to_clipboard(self.ascii_text_widget)
        )

        # Add panes to allow mouse-resizable layout: palette | canvas | properties
        added = False
        try:
            # Use conservative options for broader Tk compatibility
            panes.add(palette)
            panes.add(canvas_frame)
            panes.add(right_panel)
            try:
                panes.paneconfig(palette, weight=0)
                panes.paneconfig(canvas_frame, weight=3)
                panes.paneconfig(right_panel, weight=1)
            except Exception:
                pass
            added = True
        except Exception as e:
            # Fallback for Tk builds that don't support weight/minsize args
            print(f"[WARN] Paned layout failed: {e}; falling back to fixed layout")
        if not added:
            palette.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
            canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            right_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        # Ensure auto-fit runs after panes settle
        self._schedule_auto_zoom_fit()

        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._apply_status_font()

    def _center_coords(self, w: int, h: int) -> Tuple[int, int]:
        """Compute top-left coords to center a widget of size w×h."""
        cx = max(0, (self.designer.width - w) // 2)
        cy = max(0, (self.designer.height - h) // 2)
        return cx, cy

    def _get_responsive_scales(self) -> Tuple[float, float]:
        """Return (spacing_scale, font_scale) based on current canvas size."""
        try:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
        except Exception:
            width = self.designer.width
            height = self.designer.height
        try:
            scales = self._responsive_scalars(width, height)
            self._responsive_tier = str(scales.get("tier", "medium"))
            return float(scales.get("spacing_scale", 1.0)), float(scales.get("font_scale", 1.0))
        except Exception:
            self._responsive_tier = "medium"
            return 1.0, 1.0

    def _load_settings(self) -> Dict[str, Any]:
        """Load shared UI settings (safe fallback)."""
        try:
            if os.path.exists(self._settings_path):
                with open(self._settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_settings(self) -> None:
        """Persist shared UI settings."""
        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump(self._settings_cache, f, indent=2)
        except Exception:
            pass

    def _load_quick_slots_from_settings(self) -> None:
        """Load saved quick-insert slots if available."""
        slots = self._settings_cache.get("quick_insert_components")
        if isinstance(slots, list) and slots:
            valid = []
            for item in slots:
                if isinstance(item, dict) and "type" in item and "name" in item:
                    valid.append(item)
            if valid:
                self.quick_insert_components = valid[:9]

    def _save_quick_slots(self) -> None:
        """Persist current quick-insert slots."""
        self._settings_cache["quick_insert_components"] = self.quick_insert_components
        self._save_settings()

    def _record_recent_component(self, name: Optional[str]) -> None:
        """Track a component name in recent list (dedup, limited)."""
        if not name:
            return
        try:
            if name in self._recent_components:
                self._recent_components.remove(name)
            self._recent_components.insert(0, name)
            self._recent_components = self._recent_components[:12]
            self._settings_cache["recent_components"] = self._recent_components
            self._save_settings()
        except Exception:
            pass

    def _save_favorites_from_recent(self) -> None:
        """Persist favorites list sourced from current recents."""
        self._favorite_components = list(self._recent_components[:12])
        self._settings_cache["favorite_components"] = self._favorite_components
        self._save_settings()

    def _save_favorites_from_list(self, components: List[Dict[str, Any]]) -> None:
        """Persist favorites from a given component list."""
        names = [c.get("name") for c in components if isinstance(c, dict) and c.get("name")]
        self._favorite_components = names[:12]
        self._settings_cache["favorite_components"] = self._favorite_components
        self._save_settings()

    def _save_favorites_from_names(self, names: List[str]) -> None:
        """Persist favorites from a list of names."""
        self._favorite_components = [n for n in names if n][:12]
        self._settings_cache["favorite_components"] = self._favorite_components
        self._save_settings()

    def _component_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Build lookup of component name -> defaults/type for quick slots."""
        lookup: Dict[str, Dict[str, Any]] = {}
        for comp in self.ascii_components:
            nm = comp.get("name")
            if nm:
                lookup[nm] = {
                    "name": nm,
                    "type": comp.get("type", "label"),
                    "defaults": comp.get("defaults", {}),
                }
        for comp in self.quick_insert_components:
            nm = comp.get("name")
            if nm:
                lookup[nm] = {
                    "name": nm,
                    "type": comp.get("type", "label"),
                    "defaults": comp.get("defaults", {}),
                }
        return lookup

    def _apply_favorites_to_quick_slots(self) -> None:
        """Replace quick insert slots with favorites where possible."""
        lookup = self._component_lookup()
        new_slots = []
        for nm in self._favorite_components:
            entry = lookup.get(nm)
            if entry:
                new_slots.append(entry)
        if new_slots:
            self.quick_insert_components = new_slots[:9]
            self._save_quick_slots()

    def _scale_spacing(self, value: int, minimum: int = 0) -> int:
        """Scale a spacing value using responsive spacing scale."""
        spacing_scale, _ = self._get_responsive_scales()
        scaled = int(round(value * spacing_scale))
        return max(minimum, scaled)

    def _scale_font_size(self, value: int, minimum: int = 1) -> int:
        """Scale a font size using responsive font scale."""
        _, font_scale = self._get_responsive_scales()
        scaled = int(round(value * font_scale))
        return max(minimum, scaled)

    def _resolve_theme_bg(self, theme: str) -> Optional[str]:
        """Map theme name to background hex (None = current)."""
        t = (theme or "current").lower()
        palette = {
            "default": color_hex("theme_default_bg"),
            "light": color_hex("theme_light_bg"),
            "dark": color_hex("theme_dark_bg"),
            "hc": color_hex("theme_hc_bg"),
            "nord": color_hex("legacy_nord_base"),
            "dracula": color_hex("legacy_dracula_bg"),
            "cyber": color_hex("theme_cyber_bg"),
        }
        return palette.get(t)

    def _apply_theme(self, theme_name: str) -> None:
        """Apply preview theme by adjusting background color and caching selection."""
        theme = (theme_name or "default").lower()
        bg = self._resolve_theme_bg(theme)
        if bg:
            self.settings.background_color = bg
            self._preview_theme = theme
            self._settings_cache["preview_theme"] = theme
            self._save_settings()
            if hasattr(self, "_theme_var"):
                try:
                    self._theme_var.set(theme)
                except Exception:
                    pass

    def _on_theme_change(self, theme_name: str):
        """Handle theme dropdown change."""
        try:
            self._apply_theme(theme_name)
            self.refresh()
        except Exception:
            pass

    def _handle_colors(self) -> Tuple[str, str]:
        """Return (base, hover) colors for handles, respecting HC toggle."""
        if getattr(self.settings, "high_contrast_overlays", False):
            return color_hex("theme_hc_accent"), color_hex("theme_hc_primary")
        return color_hex("accent_handle_base"), color_hex("accent_handle_hover")

    def _selection_colors(self) -> Tuple[str, str]:
        """Return (outline, fill) colors for selection/box-select."""
        if getattr(self.settings, "high_contrast_overlays", False):
            return color_hex("theme_hc_primary"), color_hex("theme_hc_accent")
        return color_hex("selection_outline"), color_hex("selection_fill")

    def _default_cursor(self) -> str:
        """Default cursor respecting accessibility toggle."""
        return "crosshair" if getattr(self.settings, "high_contrast_overlays", False) else "arrow"

    def _get_scaled_grid_size(self) -> int:
        """Return grid size in device units (no responsive scaling)."""
        try:
            return max(1, int(getattr(self.settings, "grid_size", 1)))
        except Exception:
            return 1

    def _get_scaled_snap_size(self) -> int:
        """Return snap size adjusted by responsive spacing scale."""
        return self._scale_spacing(getattr(self.settings, "snap_size", 1), minimum=1)

    def _get_scaled_nudge(self, shift: bool) -> int:
        """Return nudge distance (normal or shift) adjusted by responsive spacing scale."""
        base = self.settings.nudge_shift_distance if shift else self.settings.nudge_distance
        return self._scale_spacing(base, minimum=1)

    def _count_box_select(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Return how many widgets intersect the current box select area (canvas coords)."""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return 0
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        count = 0
        for widget in scene.widgets:
            if not getattr(widget, "visible", True):
                continue
            wx1 = int(widget.x * self.settings.zoom)
            wy1 = int(widget.y * self.settings.zoom)
            wx2 = int((widget.x + widget.width) * self.settings.zoom)
            wy2 = int((widget.y + widget.height) * self.settings.zoom)
            if not (wx2 < x1 or wx1 > x2 or wy2 < y1 or wy1 > y2):
                count += 1
        return count

    def _apply_auto_zoom_fit(self, force: bool = False):
        """Auto-fit zoom to the available canvas area."""
        if (self._auto_fit_done and not force) or HEADLESS:
            return
        try:
            if hasattr(self, "root"):
                self.root.update_idletasks()
            container = getattr(self, "_canvas_frame", None)
            if container is None and hasattr(self, "canvas"):
                container = getattr(self.canvas, "master", None)
            if container is None:
                return
            # Leave a small gutter so grid/handles aren't pinned to the frame edges
            gutter = 8
            avail_w = max(1, getattr(container, "winfo_width", lambda: 0)() - gutter)
            avail_h = max(1, getattr(container, "winfo_height", lambda: 0)() - gutter)
            # If layout not ready yet, retry once
            if avail_w < 20 or avail_h < 20:
                if hasattr(self, "root"):
                    self.root.after(50, self._apply_auto_zoom_fit)
                return
            zoom_x = avail_w / max(1e-6, float(self.designer.width))
            zoom_y = avail_h / max(1e-6, float(self.designer.height))
            target_zoom = round(max(self._zoom_min, min(self._zoom_max, min(zoom_x, zoom_y))), 1)
            self._auto_fit_done = True
            if abs(target_zoom - self.settings.zoom) > 0.05:
                self.settings.zoom = target_zoom
                if hasattr(self, "_zoom_var"):
                    try:
                        self._zoom_var.set(f"{self.settings.zoom:.1f}x")
                    except Exception:
                        pass
                self.refresh()
        except Exception:
            self._auto_fit_done = True

    def _schedule_auto_zoom_fit(self, reset_override: bool = False):
        """Throttle auto-zoom fit so it runs after resize settles."""
        if reset_override:
            self._auto_fit_done = False
        if not hasattr(self, "root") or not getattr(self.root, "winfo_exists", lambda: False)():
            return
        try:
            if self._auto_fit_job and hasattr(self, "root"):
                self.root.after_cancel(self._auto_fit_job)
        except Exception:
            pass
        try:
            self._auto_fit_job = self.root.after(
                120, lambda: self._apply_auto_zoom_fit(force=True)
            )
        except Exception:
            pass

    def _auto_size_window(self) -> None:
        """Size the main window to fit canvas + sidebars and center on screen."""
        if HEADLESS or not hasattr(self, "root"):
            return
        try:
            self.root.update_idletasks()
            screen_w = max(800, self.root.winfo_screenwidth())
            screen_h = max(600, self.root.winfo_screenheight())
            canvas_w = int(self.designer.width * self.settings.zoom)
            canvas_h = int(self.designer.height * self.settings.zoom)
            desired_w = canvas_w + 540  # canvas + palette + props + padding
            desired_h = canvas_h + 260  # canvas + toolbars/status + padding
            width = min(screen_w - 40, max(900, desired_w))
            height = min(screen_h - 60, max(650, desired_h))
            # Center window on screen
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _apply_status_font(self) -> None:
        """Apply responsive font sizing to the status bar."""
        if not hasattr(self, "status_bar"):
            return
        try:
            size = self._scale_font_size(10, minimum=8)
            if tkfont:
                try:
                    base_font = tkfont.nametofont(self.status_bar.cget("font"))
                    derived = base_font.copy()
                    derived.configure(size=size)
                    self.status_bar.configure(font=derived)
                except Exception:
                    self.status_bar.configure(font=("TkDefaultFont", size))
            else:
                self.status_bar.configure(font=("TkDefaultFont", size))
        except Exception:
            pass

    def _palette_add(self, kind: str):
        """Add a widget of given kind near center and select it."""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            # Ensure at least one scene exists
            self.designer.create_scene("scene")
            scene = self.designer.scenes.get(self.designer.current_scene)
            if not scene:
                return

        spacing_scale, _font_scale = self._get_responsive_scales()

        def size(w: int, h: int) -> Tuple[int, int]:
            """Scale a base (w,h) by current responsive spacing scale."""
            return (int(w * spacing_scale), int(h * spacing_scale))

        # Defaults per widget type (scaled)
        defaults = {
            "label": (*size(60, 10), {"text": "Label", "border": False}),
            "button": (*size(50, 12), {"text": "Button"}),
            "box": (*size(60, 40), {}),
            "panel": (*size(60, 40), {}),
            "progressbar": (*size(80, 8), {"value": 50}),
            "gauge": (*size(20, 30), {"value": 70}),
            "checkbox": (*size(60, 10), {"text": "Check me", "checked": True}),
            "slider": (*size(80, 8), {"value": 50}),
        }

        w, h, props = defaults.get(kind, (40, 12, {}))
        x, y = self._center_coords(w, h)

        # Map to enum
        kind_map = {
            "label": WidgetType.LABEL,
            "button": WidgetType.BUTTON,
            "box": WidgetType.BOX if hasattr(WidgetType, "BOX") else WidgetType.PANEL,
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
        self._record_recent_component(kind.title())
        self.refresh()

        # Show Quick Tips on first run
        self.root.after(500, self._check_and_show_quick_tips)

    def _check_and_show_quick_tips(self):
        """Check if Quick Tips should be shown (first run)"""
        if self._settings_cache.get("hide_quick_tips", False):
            return

        # Show Quick Tips dialog
        self._show_quick_tips_dialog()

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
                if hasattr(self, "_profiler_window") and self._profiler_window:
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
            if hasattr(self, "_profiler_window") and self._profiler_window:
                self._profiler_window.lift()
                return

            window = tk.Toplevel(self.root)
            window.title("⚡ Performance Profiler")
            window.geometry("500x600")
            window.configure(bg=color_hex("legacy_gray4"))
            self._profiler_window = window

            header = ttk.Frame(window)
            header.pack(fill=tk.X, padx=10, pady=10)
            ttk.Label(header, text="⚡ Performance Profiler", font=("Arial", 14, "bold")).pack(
                side=tk.LEFT
            )

            btn_frame = ttk.Frame(header)
            btn_frame.pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="📊 Export HTML", command=self._export_profiler_html).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(btn_frame, text="💾 Export CSV", command=self._export_profiler_csv).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(btn_frame, text="📄 Export JSON", command=self._export_profiler_json).pack(
                side=tk.LEFT, padx=2
            )

            stats_frame = ttk.LabelFrame(
                window, text="Live Metrics", padding=self._scale_spacing(10, minimum=6)
            )
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

            rec_frame = ttk.LabelFrame(
                window, text="Recommendations", padding=self._scale_spacing(10, minimum=6)
            )
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
            if not hasattr(self, "_profiler_window") or not self._profiler_window:
                return

            stats = self._profiler.calculate_stats()

            if hasattr(self, "_profiler_labels"):
                self._profiler_labels["fps"].config(
                    text=f"{stats.fps_avg:.1f} (min: {stats.fps_min:.1f}, max: {stats.fps_max:.1f})"
                )
                self._profiler_labels["render_ms"].config(
                    text=(
                        f"{stats.render_avg_ms:.2f} ms "
                        f"(min: {stats.render_min_ms:.2f}, max: {stats.render_max_ms:.2f})"
                    )
                )
                self._profiler_labels["frame_ms"].config(text=f"{stats.frame_avg_ms:.2f} ms")
                self._profiler_labels["memory_mb"].config(
                    text=f"{stats.memory_avg_mb:.1f} MB (peak: {stats.memory_peak_mb:.1f})"
                )
                self._profiler_labels["cpu_percent"].config(
                    text=f"{stats.cpu_avg_percent:.1f}% (peak: {stats.cpu_peak_percent:.1f}%)"
                )
                self._profiler_labels["samples"].config(text=f"{stats.samples}")

            if not hasattr(self, "_last_rec_update") or time.time() - self._last_rec_update > 2.0:
                self._last_rec_update = time.time()
                recommendations = self._profiler.analyze_performance()

                if hasattr(self, "_profiler_rec_text"):
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

    def _show_quick_tips_dialog(self):
        """Display Quick Tips dialog for first-time users"""
        dialog = tk.Toplevel(self.root)
        dialog.title("UI Designer Quick Tips")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        header = ttk.Frame(dialog)
        header.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(header, text="Quick Tips", font=("Arial", 14, "bold")).pack()

        tips_frame = ttk.Frame(dialog)
        tips_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tips_text = tk.Text(
            tips_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            height=15,
            width=50,
            bg=color_hex("legacy_gray_faint"),
        )
        tips_text.pack(fill=tk.BOTH, expand=True)

        tips_content = """Mouse:
- Click selects, Shift+Click multi-selects
- Drag empty canvas = box select
- Drag handle = resize
- Double-click = edit properties

Keyboard:
- Ctrl+Shift+A = quick add search
- Arrows move (Shift = 8px)
- Delete removes selection
- Ctrl+C/V copy/paste, Ctrl+Z/Y undo/redo
- Space+drag = pan

Zoom:
- Ctrl+mouse wheel or toolbar dropdown

Export:
- PNG @1x-@4x, scene-only or with guides

Tip: Full shortcut list in Help > Keyboard Shortcuts"""

        tips_text.insert("1.0", tips_content)
        tips_text.configure(state="disabled")

        bottom_frame = ttk.Frame(dialog)
        bottom_frame.pack(fill=tk.X, padx=20, pady=10)

        dont_show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom_frame, text="Nezobrazovat znovu", variable=dont_show_var).pack(
            anchor=tk.W, pady=5
        )

        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X)

        def close_dialog():
            if dont_show_var.get():
                self._settings_cache["hide_quick_tips"] = True
                self._save_settings()
            dialog.destroy()

        ttk.Button(btn_frame, text="Zav??t", command=close_dialog, width=15).pack(
            side=tk.RIGHT, padx=5
        )

    def _invalidate_cache(self):
        """Invalidate render caches"""
        self._cache_valid = False
        self._ascii_cache_valid = False

    def _setup_properties_panel(self):
        """Setup widget properties panel"""
        props_window = tk.Toplevel(self.root)
        props_window.title("Widget Properties")
        props_window.geometry("300x500")
        props_window.configure(bg=color_hex("legacy_gray4"))

        # Make it stay on top but not modal
        props_window.attributes("-topmost", False)

        self.props_frame = ttk.Frame(props_window, padding=self._scale_spacing(10, minimum=6))
        self.props_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.props_frame, text="No widget selected").pack()

        self.props_window = props_window

    def _setup_bindings(self):
        """Setup mouse and keyboard bindings"""
        self.canvas.bind(self.EVT_MOUSE_LEFT, self._on_mouse_down)
        self.canvas.bind(self.EVT_MOUSE_DRAG_LEFT, self._on_mouse_drag)
        self.canvas.bind(self.EVT_MOUSE_LEFT_RELEASE, self._on_mouse_up)
        self.canvas.bind(self.EVT_MOUSE_MOVE, self._on_mouse_move)
        self.canvas.bind(self.EVT_MOUSE_RIGHT, self._on_right_click)
        # Zoom with Ctrl+Wheel (Windows/Mac) and Button4/5 fallback (Linux)
        self.canvas.bind(self.EVT_MOUSE_CTRL_WHEEL, self._on_ctrl_wheel_zoom)
        self.canvas.bind(
            "<Control-Button-4>", lambda e: self._on_ctrl_wheel_zoom(self._mk_wheel_event(e, +120))
        )
        self.canvas.bind(
            "<Control-Button-5>", lambda e: self._on_ctrl_wheel_zoom(self._mk_wheel_event(e, -120))
        )
        self.root.bind("<Control-0>", lambda e: self._on_zoom_fit())
        self.canvas.bind(self.EVT_MOUSE_LEFT_DOUBLE, self._on_double_click)

        # Keyboard shortcuts
        self.root.bind(self.EVT_KEY_DELETE, self._on_delete_widget)
        self.root.bind(self.EVT_KEY_UNDO, lambda e: self.designer.undo())
        self.root.bind(self.EVT_KEY_REDO, lambda e: self.designer.redo())
        self.root.bind(self.EVT_KEY_SAVE, self._on_save)
        self.root.bind(self.EVT_KEY_COPY, self._on_copy)
        self.root.bind(self.EVT_KEY_PASTE, self._on_paste)
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
            self.root.bind(f"<Control-Key-{i}>", lambda e, idx=i - 1: self._on_quick_insert(idx))
            self.root.bind(
                f"<Control-KP_{i}>", lambda e, idx=i - 1: self._on_quick_insert(idx)
            )  # Numpad support
        # Space = hand pan
        self.root.bind("<KeyPress-space>", self._on_space_down)
        self.root.bind("<KeyRelease-space>", self._on_space_up)
        # Align/Distribute shortcuts for multi-select
        self.root.bind("<Alt-Left>", lambda e: self._align_widgets("left"))
        self.root.bind("<Alt-Right>", lambda e: self._align_widgets("right"))
        self.root.bind("<Alt-Up>", lambda e: self._align_widgets("top"))
        self.root.bind("<Alt-Down>", lambda e: self._align_widgets("bottom"))
        self.root.bind("<Alt-h>", lambda e: self._distribute_widgets("horizontal"))
        self.root.bind("<Alt-H>", lambda e: self._distribute_widgets("horizontal"))
        self.root.bind("<Alt-v>", lambda e: self._distribute_widgets("vertical"))
        self.root.bind("<Alt-V>", lambda e: self._distribute_widgets("vertical"))
        # Mini help overlay
        self.root.bind("<F1>", lambda e: self._toggle_mini_help())
        self.root.bind("<F10>", lambda e: self._toggle_mini_help())
        # Perf overlay toggle
        self.root.bind("<F9>", lambda e: self._toggle_perf_overlay())
        # (Space hand pan bindings already registered earlier; avoid duplicates)

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
        # Keep last rendered PIL image for screenshot capture
        try:
            self._last_image = img
        except Exception:
            pass
        # Performance tracking
        self._finalize_refresh(t0)
        try:
            self._predicted_fps, self._complexity_score = self._estimate_scene_perf(scene)
        except Exception:
            self._predicted_fps, self._complexity_score = None, None
        # Update status bar with predicted performance if available
        # Diagnostics augmentation
        if self._diagnostics_enabled:
            # Record instantaneous FPS (based on render ms) for history
            try:
                if self._last_render_ms > 0:
                    inst_fps = 1000.0 / self._last_render_ms
                    self._fps_history.append(inst_fps)
                    if len(self._fps_history) > self._fps_history_max:
                        self._fps_history = self._fps_history[-self._fps_history_max:]
            except Exception:
                pass
            # Memory stats (tracemalloc started when enabling diagnostics)
            current_mem_mb, peak_mem_mb = self._get_memory_usage()
            self._memory_peak = peak_mem_mb
            # Throttle overlay redraw to reduce overhead
            now = time.time()
            if now - self._diagnostics_last_draw_ts > 0.25:  # 250ms
                try:
                    self._draw_diagnostics_overlay()
                except Exception:
                    pass
                self._diagnostics_last_draw_ts = now
            # Build segmented status text
            if hasattr(self, "status_bar"):
                try:
                    avg_fps = sum(self._fps_history) / len(self._fps_history) if self._fps_history else 0.0
                    scene_name = getattr(scene, "name", self.designer.current_scene)
                    status_txt = (
                        f"Scene: {scene_name} | Widgets: {len(scene.widgets)} | Complexity: {self._complexity_score} | "
                        f"est FPS: {int(self._predicted_fps) if self._predicted_fps else '--'} (avg {avg_fps:.1f}) | "
                        f"Mem: {current_mem_mb:.1f}MB (peak {peak_mem_mb:.1f})"
                    )
                    self.status_bar.config(text=status_txt)
                except Exception:
                    pass
        else:
            if hasattr(self, "status_bar") and self._predicted_fps is not None:
                try:
                    base = self.status_bar.cget("text")
                    perf_snippet = (
                        f" | est FPS: {int(self._predicted_fps)} "
                        f"(complexity {self._complexity_score})"
                    )
                    if "est FPS:" in base:
                        base = base.split(" | est FPS:")[0]
                    self.status_bar.config(text=base + perf_snippet)
                except Exception:
                    pass
        # Optional perf log export
        if os.environ.get("ESP32OS_PERF_LOG") == "1":
            try:
                log_dir = os.path.join(os.getcwd(), "output")
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, "perf_log.csv")
                new_file = not os.path.exists(log_path)
                with open(log_path, "a", encoding="utf-8") as f:
                    if new_file:
                        f.write("timestamp,scene,complexity,est_fps,render_ms\n")
                    ts_val = f"{time.time():.3f}"
                    scene_name = (
                        scene.name if hasattr(scene, "name") else self.designer.current_scene
                    )
                    line = \
                        f"{ts_val},{scene_name},{self._complexity_score},{self._predicted_fps:.1f},{self._last_render_ms:.2f}\n"
                    f.write(line)
            except Exception:
                pass
        # Auto screenshot on first render if env set
        if os.environ.get("ESP32OS_SCREENSHOT_ON_START") == "1" and not getattr(
            self, "_auto_shot_done", False
        ):
            self._auto_shot_done = True
            self._screenshot_canvas()

    def _estimate_scene_perf(self, scene) -> Tuple[float, int]:
        """Estimate rendering performance (rough heuristic).

        Returns (estimated_fps, complexity_score).
        Complexity is a simple weighted sum of widget features.
        This does not measure real device speed; it offers guidance before export.
        """
        complexity = 0
        for w in scene.widgets:
            # Base cost per widget
            complexity += 5
            wt = getattr(w, "type", "") or getattr(w, "widget_type", "")
            # Text length contributes
            txt = getattr(w, "text", "")
            if txt:
                complexity += min(len(str(txt)) * 0.8, 20)
            # Shapes / style extras
            if wt in ("gauge", "progressbar", "slider"):
                complexity += 12
            elif wt in ("panel", "box"):
                complexity += 4
            elif wt in ("icon", "image"):
                complexity += 10
            # Borders add a bit
            if getattr(w, "border", False):
                complexity += 3
            # Size scaling (larger widgets generally cost more)
            w_area = getattr(w, "width", 0) * getattr(w, "height", 0)
            complexity += min(w_area / 300.0, 20)
        # Convert complexity to FPS estimate (heuristic curve)
        if complexity <= 0:
            return 60.0, 0
        # Assume base 120 'cycles' budget → fps scales inversely
        fps = max(8.0, 120.0 / (complexity / 10.0))
        fps = min(60.0, fps)
        return fps, int(complexity)

    def _screenshot_canvas(self):
        """Capture current canvas render to PNG in output/screenshots."""
        if not getattr(self, "_last_image", None):
            try:
                messagebox.showwarning("Screenshot", "No rendered image yet")
            except Exception:
                pass
            return
        # Ensure output/screenshots directory exists
        out_dir = os.path.join(os.getcwd(), "output", "screenshots")
        os.makedirs(out_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        comp = getattr(self, "_complexity_score", None)
        fps = getattr(self, "_predicted_fps", None)
        parts = ["shot", ts]
        if comp is not None:
            parts.append(f"C{comp}")
        if fps is not None:
            parts.append(f"FPS{int(fps)}")
        fname = "_".join(parts) + ".png"
        path = os.path.join(out_dir, fname)
        try:
            self._last_image.save(path)
            try:
                messagebox.showinfo("Screenshot", f"Saved {path}")
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror("Screenshot Failed", f"Could not save: {e}")
            except Exception:
                pass

    # ---------------- Layout Analysis -----------------
    def _layout_warnings(self):
        scene = self._get_active_scene()
        return layout_warnings(scene, self.designer.width, self.designer.height)

    def _show_layout_warnings(self):
        """Display layout warnings in a popup dialog."""
        try:
            warnings = self._layout_warnings()
            msg = "\n".join(warnings)
            messagebox.showinfo("Layout Analysis", msg)
        except Exception as e:
            try:
                messagebox.showerror("Layout Analysis Failed", str(e))
            except Exception:
                pass

    # ---------------- Additional Diagnostics -----------------
    def _toggle_diagnostics(self):
        """Enable/disable diagnostics overlay and enhanced status bar info."""
        self._diagnostics_enabled = not self._diagnostics_enabled
        if self._diagnostics_enabled:
            # Start tracemalloc once
            if not tracemalloc.is_tracing():
                try:
                    tracemalloc.start()
                except Exception:
                    pass
            self._fps_history.clear()
            self._diagnostics_last_draw_ts = 0.0
        else:
            # Optional: stop tracing to reduce overhead
            if tracemalloc.is_tracing():
                try:
                    tracemalloc.stop()
                except Exception:
                    pass
        try:
            self.refresh(force=True)
        except Exception:
            pass

    def _draw_diagnostics_overlay(self):
        """Draw bounding boxes for all widgets and a simple FPS sparkline."""
        if HEADLESS or not hasattr(self, "canvas"):
            return
        scene = self._get_active_scene()
        if not scene:
            return
        zoom = getattr(self.settings, "zoom", 1.0)
        # Clear previous overlay shapes (use tagged items)
        try:
            self.canvas.delete("diag_overlay")
        except Exception:
            pass
        # Bounding boxes
        try:
            for idx, w in enumerate(scene.widgets):
                x1 = int(w.x * zoom)
                y1 = int(w.y * zoom)
                x2 = int((w.x + w.width) * zoom)
                y2 = int((w.y + w.height) * zoom)
                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    outline=color_hex("legacy_dracula_cyan"),
                    width=1,
                    tags=("diag_overlay",),
                )
                if idx == self.selected_widget_idx:
                    self.canvas.create_rectangle(
                        x1,
                        y1,
                        x2,
                        y2,
                        outline=color_hex("legacy_green"),
                        width=2,
                        tags=("diag_overlay",),
                    )
        except Exception:
            pass
        # FPS sparkline (bottom-left corner)
        try:
            if self._fps_history:
                spark_w = 100
                spark_h = 28
                pad = 4
                x0 = 10
                y0 = int(self.designer.height * zoom) - spark_h - 10
                self.canvas.create_rectangle(
                    x0,
                    y0,
                    x0 + spark_w,
                    y0 + spark_h,
                    fill=color_hex("shadow"),
                    outline=color_hex("legacy_gray8"),
                    tags=("diag_overlay",),
                )
                max_fps = max(self._fps_history) if self._fps_history else 60.0
                min_fps = min(self._fps_history) if self._fps_history else 0.0
                span = max(1.0, max_fps - min_fps)
                pts = []
                hist = self._fps_history[-spark_w:]
                for i, v in enumerate(hist):
                    norm = (v - min_fps) / span
                    px = x0 + pad + i
                    py = (y0 + spark_h - pad) - int(norm * (spark_h - 2 * pad))
                    pts.append((px, py))
                for a, b in zip(pts, pts[1:]):
                    self.canvas.create_line(
                        a[0],
                        a[1],
                        b[0],
                        b[1],
                        fill=color_hex("legacy_dracula_pink"),
                        tags=("diag_overlay",),
                    )
                # Current FPS label
                try:
                    inst = self._fps_history[-1]
                    self.canvas.create_text(
                        x0 + spark_w // 2,
                        y0 - 2,
                        text=f"FPS {inst:.1f}",
                        fill=color_hex("text_primary"),
                        font=("TkDefaultFont", self._scale_font_size(9, minimum=8)),
                        tags=("diag_overlay",),
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _get_memory_usage(self) -> Tuple[float, float]:
        """Return (current_mb, peak_mb) using tracemalloc (safe fallbacks)."""
        try:
            if not tracemalloc.is_tracing():
                return 0.0, 0.0
            current, peak = tracemalloc.get_traced_memory()
            return current / (1024 * 1024), peak / (1024 * 1024)
        except Exception:
            return 0.0, 0.0

    def _refresh_headless(self) -> bool:
        """Handle headless refresh, returns True if handled."""
        if not getattr(self, "_headless", False):
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

    def _fill_component_results(
        self, query, filtered_components, results_list, source_components=None
    ):
        results_list.delete(0, tk.END)
        filtered_components.clear()
        comps = source_components or self.ascii_components
        for comp in comps:
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
            self._record_recent_component(component.get("name"))
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
        entry.bind(
            RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, "text", text_var.get())
        )

    def _add_label_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Label:", width=10).pack(side=tk.LEFT)
        label_value = widgets[0].label if len(widgets) == 1 else ""
        label_var = tk.StringVar(value=label_value)
        entry = ttk.Entry(frame, textvariable=label_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(
            RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, "label", label_var.get())
        )

    def _add_value_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Value:", width=10).pack(side=tk.LEFT)
        value_value = str(widgets[0].value) if len(widgets) == 1 else ""
        value_var = tk.StringVar(value=value_value)
        entry = ttk.Entry(frame, textvariable=value_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(
            RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, "value", value_var.get())
        )

    def _add_color_field(self, widget_indices, widgets):
        frame = ttk.Frame(self.props_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Color:", width=10).pack(side=tk.LEFT)
        color_value = widgets[0].color if len(widgets) == 1 else ""
        color_var = tk.StringVar(value=color_value)
        entry = ttk.Entry(frame, textvariable=color_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind(
            RETURN_KEY, lambda e: self._update_batch_prop(widget_indices, "color", color_var.get())
        )

    def _render_position_size_fields(self, widget_indices, widgets):
        ttk.Label(self.props_frame, text="Position & Size:", font=("Arial", 10, "bold")).pack(
            anchor=tk.W, pady=(10, 5)
        )
        for prop in ["x", "y", "width", "height"]:
            frame = ttk.Frame(self.props_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{prop.capitalize()}:", width=10).pack(side=tk.LEFT)
            prop_value = getattr(widgets[0], prop) if len(widgets) == 1 else 0
            var = tk.IntVar(value=prop_value)
            spinbox = ttk.Spinbox(frame, from_=0, to=200, textvariable=var, width=10)
            spinbox.pack(side=tk.LEFT)
            spinbox.bind(
                RETURN_KEY,
                lambda e, p=prop, v=var: self._update_batch_prop(widget_indices, p, v.get()),
            )

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
                include_grid=False,  # grid will be drawn once after padding/zoom
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

        # If the canvas is larger than the rendered scene, pad the image so the
        # background fills the entire visible area (prevents gray strips).
        if hasattr(self, "canvas"):
            try:
                canvas_w = int(self.canvas.winfo_width())
                canvas_h = int(self.canvas.winfo_height())
                target_w = max(scaled_width, canvas_w)
                target_h = max(scaled_height, canvas_h)
                if target_w > scaled_width or target_h > scaled_height:
                    bg_hex = getattr(self.settings, "background_color", color_hex("shadow"))
                    try:
                        base_color = hex_to_rgb(bg_hex)
                    except Exception:
                        base_color = (0, 0, 0)
                    if img_scaled.mode == "RGBA":
                        base_color = tuple(list(base_color) + [255])[:4]
                    padded = Image.new(img_scaled.mode, (target_w, target_h), base_color)
                    padded.paste(img_scaled, (0, 0))
                    img_scaled = padded
                    scaled_width, scaled_height = target_w, target_h
            except Exception:
                pass

        # Draw a single grid over the final image, scaled to current zoom.
        if getattr(self.settings, "grid_enabled", False):
            try:
                draw = ImageDraw.Draw(img_scaled)
                base_step = max(1, int(getattr(self.settings, "grid_size", 1)))
                zoom = max(0.01, float(self.settings.zoom))
                step = max(1, int(round(base_step * zoom)))
                dynamic_pad_scene = int(min(self.designer.width, self.designer.height) * 0.02)
                padding_scene = max(
                    getattr(self.settings, "grid_padding_min_px", 0),
                    int(base_step * getattr(self.settings, "grid_padding_pct", 0)),
                    dynamic_pad_scene,
                )
                padding = int(round(padding_scene * zoom))
                grid_color = (
                    self.settings.grid_color_light
                    if getattr(self.settings, "high_contrast_overlays", False)
                    else self.settings.grid_color_dark
                )
                for x in range(padding, scaled_width - padding, step):
                    draw.line(
                        [(x, padding), (x, scaled_height - padding)],
                        fill=grid_color,
                        width=1,
                    )
                for y in range(padding, scaled_height - padding, step):
                    draw.line([(padding, y), (scaled_width - padding, y)], fill=grid_color, width=1)
            except Exception:
                pass

        self.photo = ImageTk.PhotoImage(img_scaled)
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, scaled_width, scaled_height))
        if self.selected_widget_idx is not None and self.settings.show_handles:
            self._draw_selection_handles()
        if self._show_hints:
            self._draw_hints_overlay()
        if getattr(self, "_show_mini_help", False):
            self._draw_mini_help_overlay()
        if getattr(self, "_show_perf_overlay", False):
            self._draw_perf_overlay()
        if (
            self.settings.show_alignment_guides
            and self.dragging
            and self.selected_widget_idx is not None
        ):
            self._draw_guides_overlay()
        if getattr(self.settings, "show_debug_overlay", False):
            self._draw_bounds_selected_overlay()
        if getattr(self.settings, "show_debug_overlay", False):
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
        step = self._get_scaled_grid_size()
        if step <= 0:
            return
        # Color selection based on contrast mode
        grid_color = (
            self.settings.grid_color_light
            if getattr(self.settings, "high_contrast_overlays", False)
            else self.settings.grid_color_dark
        )
        # Configurable padding
        # Make padding adapt to canvas size so the grid has breathing room on all sides.
        dynamic_pad = int(min(width, height) * 0.02)
        padding = max(
            self.settings.grid_padding_min_px,
            int(step * self.settings.grid_padding_pct),
            dynamic_pad,
        )
        # Draw vertical lines with padding
        for x in range(padding, width - padding, step):
            draw.line([(x, padding), (x, height - padding)], fill=grid_color, width=1)
        # Draw horizontal lines with padding
        for y in range(padding, height - padding, step):
            draw.line([(padding, y), (width - padding, y)], fill=grid_color, width=1)

    def _update_status_bar(self):
        """Update status bar with current state and contextual hints."""
        if not hasattr(self, "status_bar"):
            return
        self._apply_status_font()

        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            self.status_bar.configure(text="No active scene")
            return

        widget_count = len(scene.widgets)
        parts = [
            f"Widgets: {widget_count}",
            f"Zoom: {self.settings.zoom:.1f}x",
            f"Tier:{getattr(self, '_responsive_tier', 'medium')}",
        ]
        if hasattr(self, "_anim_speed_multiplier"):
            state = "▶" if self.playing else "⏸"
            parts.append(f"Anim {state} {self._anim_speed_multiplier:.2f}x")

        # Selection info
        if self.selected_widget_idx is not None and self.selected_widget_idx < len(scene.widgets):
            w = scene.widgets[self.selected_widget_idx]
            parts.append(f"Selected: {w.type} ({w.x},{w.y}) {w.width}×{w.height}")

        # Multi-selection count
        if len(self.selected_widgets) > 1:
            parts.append(
                f"{len(self.selected_widgets)} selected (Align Alt+Arrows • Distribute Alt+H/V)"
            )
        if (
            self.dragging
            and self.resize_handle
            and self.selected_widget_idx is not None
            and self.selected_widget_idx < len(scene.widgets)
        ):
            w = scene.widgets[self.selected_widget_idx]
            parts.append(f"Resizing {self.resize_handle.upper()} → {w.width}x{w.height}")
        if self._pending_component:
            parts.append(
                f"Placing: {self._pending_component.get('name', 'widget')} (click to place)"
            )
        if self.box_select_start and self.box_select_rect:
            parts.append(f"Box-select: {self._box_select_count} hit • Align/Distribute ready")

        # Editor toggles (compact)
        toggles = []

        def _toggle(label: str, enabled: bool) -> str:
            return f"{'●' if enabled else '○'}{label}"

        toggles.append(_toggle("Grid", self.settings.grid_enabled))
        toggles.append(_toggle("Snap", self.settings.snap_enabled))
        toggles.append(_toggle("Guides", self.settings.show_alignment_guides))
        toggles.append(_toggle("Handles", self.settings.show_handles))
        if getattr(self, "_show_mini_help", False):
            toggles.append("●Help")
        if self.settings.auto_reload_json:
            toggles.append("AutoReload:on")
        parts.append(" ".join(toggles))

        # Live hints based on mode
        hint = self._get_context_hint()
        if hint:
            parts.append(f"💡 {hint}")
        if self._pending_component:
            parts.append(
                "Hint: click to place, Esc/right-click to cancel, Enter to confirm at cursor"
            )

        # Performance budget indicators
        status_color = None
        if getattr(self.settings, "performance_budget_enabled", False):
            if getattr(self, "_perf_soft_warn", False):
                parts.append(f"⚠ Perf WARN {self._last_render_ms:.1f}ms")
                status_color = color_hex("legacy_orange")
            elif getattr(self, "_perf_over_budget", False):
                parts.append(
                    f"‼ Perf {self._last_render_ms:.1f}>{self.settings.performance_budget_ms:.1f}ms"
                )
                status_color = color_hex("legacy_dracula_red")

        # Always show current FPS/render time
        parts.append(f"FPS:{self._last_fps:.1f} {self._last_render_ms:.1f}ms")

        # Profiler live snippet
        if getattr(self, "_profiler_enabled", False):
            parts.append(f"⚡ {self._last_fps:.1f} FPS {self._last_render_ms:.1f}ms")
        if status_color is None:
            status_color = (
                color_hex("theme_hc_text")
                if getattr(self.settings, "high_contrast_overlays", False)
                else color_hex("text_primary")
            )
        self.status_bar.configure(text=" | ".join(parts), foreground=status_color)

    # ---------------- JSON Hot-Reload Watcher -----------------
    def _schedule_json_watch(self):
        """Schedule polling for JSON design file changes (if enabled)."""
        if HEADLESS or not hasattr(self, "root"):
            return
        if not self.settings.auto_reload_json:
            return
        if self._json_watch_job is None:
            self._json_watch_job = self.root.after(
                self._json_watch_interval_ms, self._poll_json_watch
            )

    def _poll_json_watch(self):
        """Poll last loaded JSON file for external modifications."""
        self._json_watch_job = None
        if not self.settings.auto_reload_json or HEADLESS or not hasattr(self, "root"):
            return
        path = getattr(self.designer, "_last_loaded_json", None)
        if path and os.path.isfile(path):
            try:
                mtime = os.path.getmtime(path)
                last = getattr(self.designer, "_json_watch_mtime", None)
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
            self._json_watch_job = self.root.after(
                self._json_watch_interval_ms, self._poll_json_watch
            )

    def _get_context_hint(self) -> str:
        """Get contextual hint based on current state."""
        # Panning mode
        if self._pan_enabled:
            return "Pan: Space+Drag to move • Ctrl+Wheel zoom • Release Space to exit"

        # Dragging/resizing
        if self.dragging:
            if self.resize_handle:
                return "Resize: Drag handle • Shift=constrain axis • Arrows nudge"
            else:
                return "Move: Drag to reposition • Shift=axis lock • Ctrl+D duplicate"

        # Multi-selection
        if len(self.selected_widgets) > 1:
            return (
                "Multi-select: Shift+Click add • Ctrl+A select all • "
                "Align Alt+Arrows • Distribute Alt+H/V"
            )

        # Single selection with handles visible
        if self.selected_widget_idx is not None and self.settings.show_handles:
            return "Edit: Drag handles to resize • Arrows nudge (Shift=grid) • Delete to remove"

        # No selection
        if self.selected_widget_idx is None:
            return (
                "Ready: Click to select • Right-click for menu • "
                "Ctrl+Shift+A search • Toolbar Export (PNG/SVG/JSON)"
            )

        return ""

    def _draw_widget(
        self,
        draw: ImageDraw.ImageDraw,
        widget: WidgetConfig,
        selected: bool,
        overlay: Optional[Dict[str, Any]] = None,
    ):
        """Draw a widget via helper stages (geometry, background, border, content)."""
        x, y, w, h = self._compute_widget_geometry(widget, overlay)
        fg_color, bg_color = self._resolve_widget_colors(widget, selected)
        self._paint_widget_background(draw, x, y, w, h, bg_color)
        if widget.border:
            self._paint_widget_border(draw, x, y, w, h, widget, selected, fg_color)
        self._paint_widget_content(draw, x, y, w, h, widget, fg_color)

    # --- Widget drawing helpers ---
    def _compute_widget_geometry(
        self, widget: WidgetConfig, overlay: Optional[Dict[str, Any]]
    ) -> Tuple[int, int, int, int]:
        x, y = widget.x, widget.y
        w, h = widget.width, widget.height
        if overlay:
            try:
                if "x" in overlay:
                    x = int(overlay["x"])
                if "y" in overlay:
                    y = int(overlay["y"])
                if "x_offset" in overlay:
                    x += int(overlay["x_offset"])
                if "y_offset" in overlay:
                    y += int(overlay["y_offset"])
                if "scale" in overlay:
                    s = float(overlay["scale"])
                    cx, cy = x + w // 2, y + h // 2
                    w = max(1, int(w * s))
                    h = max(1, int(h * s))
                    x = cx - w // 2
                    y = cy - h // 2
            except Exception:
                pass
        return int(x), int(y), int(w), int(h)

    def _resolve_widget_colors(
        self, widget: WidgetConfig, selected: bool
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        fg_color = self._get_color(widget.color_fg)
        bg_color = self._get_color(widget.color_bg)
        # Selection border highlight uses fg_color adjustments at border stage
        return fg_color, bg_color

    def _paint_widget_background(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        bg_color: Tuple[int, int, int],
    ) -> None:
        try:
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg_color)
        except Exception:
            pass

    def _paint_widget_border(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: WidgetConfig,
        selected: bool,
        base_color: Tuple[int, int, int],
    ) -> None:
        try:
            border_color = base_color
            if selected:
                if getattr(self.settings, "high_contrast_overlays", False):
                    border_color = self._hex_to_rgb(color_hex("theme_hc_primary"))
                else:
                    border_color = (0, 150, 255)
            style = getattr(widget, "border_style", "single")
            if style == "single":
                sel_width = (
                    2
                    if (selected and getattr(self.settings, "high_contrast_overlays", False))
                    else 1
                )
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=sel_width)
            elif style == "double":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
                draw.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], outline=border_color, width=1)
            elif style == "bold":
                sel_width = (
                    3
                    if (selected and getattr(self.settings, "high_contrast_overlays", False))
                    else 2
                )
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=sel_width)
            elif style == "dashed":
                draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
        except Exception:
            pass

    def _paint_widget_content(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        widget: WidgetConfig,
        fg_color: Tuple[int, int, int],
    ) -> None:
        try:
            wt = widget.type
            if wt == WidgetType.LABEL.value:
                self._draw_text(
                    draw,
                    widget.text,
                    x + widget.padding_x,
                    y + widget.padding_y,
                    w - 2 * widget.padding_x,
                    h - 2 * widget.padding_y,
                    fg_color,
                    widget.align,
                    widget.valign,
                )
            elif wt == WidgetType.BUTTON.value:
                self._draw_text(draw, widget.text, x, y, w, h, fg_color, "center", "middle")
            elif wt == WidgetType.CHECKBOX.value:
                box_size = max(0, min(h - 4, 6))
                box_x = x + 2
                box_y = y + (h - box_size) // 2
                y0, y1 = self._clamp_rect_y_order(box_y, box_y + box_size)
                draw.rectangle([box_x, y0, box_x + box_size, y1], outline=fg_color, width=1)
                if widget.checked:
                    draw.line(
                        [(box_x + 1, box_y + 1), (box_x + box_size - 1, box_y + box_size - 1)],
                        fill=fg_color,
                        width=1,
                    )
                    draw.line(
                        [(box_x + 1, box_y + box_size - 1), (box_x + box_size - 1, box_y + 1)],
                        fill=fg_color,
                        width=1,
                    )
                if widget.text:
                    self._draw_text(
                        draw,
                        widget.text,
                        box_x + box_size + 2,
                        y,
                        w - box_size - 4,
                        h,
                        fg_color,
                        "left",
                        "middle",
                    )
            elif wt == WidgetType.PROGRESSBAR.value:
                span = max(0, (w - 4))
                denom = max(1, (widget.max_value - widget.min_value))
                progress = int((widget.value - widget.min_value) / denom * span)
                if progress > 0:
                    x0 = x + 2
                    y_top = y + 2
                    y_bottom = y + h - 3
                    y0, y1 = self._clamp_rect_y_order(y_top, y_bottom)
                    x1 = x0 + progress
                    x1 = min(x + w - 2, max(x0, x1))
                    draw.rectangle([x0, y0, x1, y1], fill=fg_color)
            elif wt == WidgetType.GAUGE.value:
                center_x = x + w // 2
                center_y = y + h // 2
                radius = max(1, min(w, h) // 2 - 2)
                draw.ellipse(
                    [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                    outline=fg_color,
                    width=1,
                )
                self._draw_text(draw, str(widget.value), x, y, w, h, fg_color, "center", "middle")
            elif wt == WidgetType.SLIDER.value:
                track_y = y + h // 2
                draw.line([(x + 2, track_y), (x + w - 2, track_y)], fill=fg_color, width=1)
                span = max(0, (w - 4))
                denom = max(1, (widget.max_value - widget.min_value))
                handle_x = x + 2 + int((widget.value - widget.min_value) / denom * span)
                x0 = max(x + 2, min(handle_x - 2, x + w - 2))
                x1 = max(x + 2, min(handle_x + 2, x + w - 2))
                y_top = y + 2
                y_bottom = y + h - 2
                y0, y1 = self._clamp_rect_y_order(y_top, y_bottom)
                draw.rectangle([x0, y0, x1, y1], fill=fg_color, outline=fg_color)
            elif wt == WidgetType.BOX.value:
                pass  # Background & border already handled
            elif wt == WidgetType.PANEL.value:
                if widget.text:
                    self._draw_text(draw, widget.text, x + 2, y, w - 4, 8, fg_color, "left", "top")
        except Exception:
            pass

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        w: int,
        h: int,
        color: Tuple[int, int, int],
        align: str,
        valign: str,
    ):
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

        spacing_scale, _font_scale = self._get_responsive_scales()

        # Scale to canvas coordinates (render uses settings.zoom to keep parity)
        x = int(widget.x * self.settings.zoom)
        y = int(widget.y * self.settings.zoom)
        w = int(widget.width * self.settings.zoom)
        h = int(widget.height * self.settings.zoom)

        # Larger handles for better UX (8px visual, 12-14px with scaling)
        handle_visual_size = max(8, min(14, int(10 * spacing_scale)))
        handle_color, handle_hover_color = self._handle_colors()

        # Corner handles
        handles = [
            (x, y, "nw"),  # Top-left
            (x + w, y, "ne"),  # Top-right
            (x + w, y + h, "se"),  # Bottom-right
            (x, y + h, "sw"),  # Bottom-left
            (x + w // 2, y, "n"),  # Top-center
            (x + w // 2, y + h, "s"),  # Bottom-center
            (x, y + h // 2, "w"),  # Left-center
            (x + w, y + h // 2, "e"),  # Right-center
        ]

        outline_width = 3 if getattr(self.settings, "high_contrast_overlays", False) else 2
        for hx, hy, handle_type in handles:
            # Use hover color if mouse is over this handle
            color = handle_hover_color if handle_type == self.hovered_handle else handle_color
            # Draw larger, more visible handles with border
            self.canvas.create_rectangle(
                hx - handle_visual_size // 2,
                hy - handle_visual_size // 2,
                hx + handle_visual_size // 2,
                hy + handle_visual_size // 2,
                fill=color,
                outline="white",
                width=outline_width,
                tags=f"handle_{handle_type}",
            )
        # Tooltip with size/direction while resizing
        if self.dragging and self.resize_handle:
            try:
                tooltip_pad = self._scale_spacing(6, minimum=4)
                tooltip_offset = self._scale_spacing(12, minimum=8)
                text = f"{widget.width}x{widget.height} | {self.resize_handle.upper()}"
                bx = x + tooltip_offset
                by = y - self._scale_spacing(18, minimum=12)
                if by < 0:
                    by = y + tooltip_offset
                tx0, ty0 = bx, by
                # Simple dark pill background
                self.canvas.create_rectangle(
                    tx0 - tooltip_pad,
                    ty0 - tooltip_pad,
                    tx0 + self._scale_spacing(120, minimum=80),
                    ty0 + self._scale_spacing(18, minimum=14),
                    fill=color_hex("shadow"),
                    outline=color_hex("legacy_gray8"),
                    stipple="gray25",
                )
                self.canvas.create_text(
                    tx0,
                    ty0,
                    anchor=tk.NW,
                    text=text,
                    fill=color_hex("text_primary"),
                    font=("TkDefaultFont", self._scale_font_size(9, minimum=8)),
                )
            except Exception:
                pass

    def _widget_edges(self, w: WidgetConfig):
        """Return all relevant edge and center positions for a widget (helper)."""
        return {
            "left": w.x,
            "right": w.x + w.width,
            "top": w.y,
            "bottom": w.y + w.height,
            "center_x": w.x + w.width // 2,
            "center_y": w.y + w.height // 2,
        }

    def _add_vertical_guides(
        self,
        guides: List[Tuple[str, int, str]],
        w_edges,
        o_edges,
        threshold: int,
    ):
        """Add vertical (X-alignment) guides if widget edges within threshold."""
        if abs(w_edges["left"] - o_edges["left"]) <= threshold:
            guides.append(("v", o_edges["left"], "left"))
        if abs(w_edges["left"] - o_edges["right"]) <= threshold:
            guides.append(("v", o_edges["right"], "left-to-right"))
        if abs(w_edges["right"] - o_edges["right"]) <= threshold:
            guides.append(("v", o_edges["right"], "right"))
        if abs(w_edges["right"] - o_edges["left"]) <= threshold:
            guides.append(("v", o_edges["left"], "right-to-left"))
        if abs(w_edges["center_x"] - o_edges["center_x"]) <= threshold:
            guides.append(("v", o_edges["center_x"], "center-x"))

    def _add_horizontal_guides(
        self,
        guides: List[Tuple[str, int, str]],
        w_edges,
        o_edges,
        threshold: int,
    ):
        """Add horizontal (Y-alignment) guides if widget edges within threshold."""
        if abs(w_edges["top"] - o_edges["top"]) <= threshold:
            guides.append(("h", o_edges["top"], "top"))
        if abs(w_edges["top"] - o_edges["bottom"]) <= threshold:
            guides.append(("h", o_edges["bottom"], "top-to-bottom"))
        if abs(w_edges["bottom"] - o_edges["bottom"]) <= threshold:
            guides.append(("h", o_edges["bottom"], "bottom"))
        if abs(w_edges["bottom"] - o_edges["top"]) <= threshold:
            guides.append(("h", o_edges["top"], "bottom-to-top"))
        if abs(w_edges["center_y"] - o_edges["center_y"]) <= threshold:
            guides.append(("h", o_edges["center_y"], "center-y"))

    def _find_alignment_guides(self, widget: WidgetConfig) -> List[Tuple[str, int, str]]:
        """Find nearby alignment opportunities with other widgets.
        Returns list of (direction, position, label) where direction is 'h' or 'v'."""
        if not self.settings.snap_to_widgets:
            return []

        scene_name = self.designer.current_scene
        if not scene_name:
            return []
        scene = self.designer.scenes.get(scene_name)
        if not scene:
            return []

        threshold = max(self.settings.snap_distance, self._get_scaled_snap_size())
        w_edges = self._widget_edges(widget)
        guides: List[Tuple[str, int, str]] = []

        for idx, other in enumerate(scene.widgets):
            if idx == self.selected_widget_idx:
                continue  # Skip self
            o_edges = self._widget_edges(other)
            self._add_vertical_guides(guides, w_edges, o_edges, threshold)
            self._add_horizontal_guides(guides, w_edges, o_edges, threshold)

        return guides

    def _apply_widget_snapping(
        self, widget: WidgetConfig, new_x: int, new_y: int
    ) -> Tuple[int, int]:
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
            if direction == "v":  # Vertical guide, snap X
                if "left" in label:
                    snapped_x = position
                elif "right" in label:
                    snapped_x = position - widget.width
                elif "center" in label:
                    snapped_x = position - widget.width // 2
            elif direction == "h":  # Horizontal guide, snap Y
                if "top" in label:
                    snapped_y = position
                elif "bottom" in label:
                    snapped_y = position - widget.height
                elif "center" in label:
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
            self.settings.show_debug_overlay = not getattr(
                self.settings, "show_debug_overlay", False
            )
            self.refresh(force=False)
        except Exception:
            pass

    def _draw_debug_overlay(self):
        """Draw a compact debug overlay with selection and scene info."""
        try:
            z = self.settings.zoom
            x0, y0 = 8, int(self.designer.height * z) - 90
            x1, y1 = x0 + 360, y0 + 82
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray11"),
                stipple="gray25",
            )
            lines = []
            # Scene info
            sc = (
                self.designer.scenes.get(self.designer.current_scene)
                if self.designer.current_scene
                else None
            )
            widget_count = len(sc.widgets) if sc else 0
            lines.append(
                "Scene: {name}  Size: {w}x{h}  Zoom: {zoom}  Widgets: {count}".format(
                    name=self.designer.current_scene or "-",
                    w=self.designer.width,
                    h=self.designer.height,
                    zoom=f"{z:.1f}x",
                    count=widget_count,
                )
            )
            # Selection info
            if (
                self.selected_widget_idx is not None
                and sc
                and 0 <= self.selected_widget_idx < len(sc.widgets)
            ):
                w = sc.widgets[self.selected_widget_idx]
                lines.append(
                    (
                        "Selected[{idx}]: {type} pos=({x},{y}) size={ww}x{hh} "
                        "z={z} vis={vis} en={en}"
                    ).format(
                        idx=self.selected_widget_idx,
                        type=w.type,
                        x=w.x,
                        y=w.y,
                        ww=w.width,
                        hh=w.height,
                        z=w.z_index,
                        vis="1" if w.visible else "0",
                        en="1" if w.enabled else "0",
                    )
                )
            else:
                lines.append("Selected: none")
            # Guides hint
            lines.append(
                "Guides:{g} Grid:{gr} Snap:{s} Render:{r} ms".format(
                    g="on" if self.settings.show_alignment_guides else "off",
                    gr="on" if self.settings.grid_enabled else "off",
                    s="on" if self.settings.snap_enabled else "off",
                    r=f"{self._last_render_ms:.1f}",
                )
            )
            # Paint
            ty = y0 + 10
            for ln in lines:
                self.canvas.create_text(
                    x0 + 10, ty, anchor=tk.NW, text=ln, fill=color_hex("text_primary")
                )
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
            scene = (
                self.designer.scenes.get(self.designer.current_scene)
                if self.designer.current_scene
                else None
            )
            if not scene:
                return
            z = self.settings.zoom
            indices = self.selected_widgets or (
                [self.selected_widget_idx] if self.selected_widget_idx is not None else []
            )
            for idx in indices:
                if 0 <= idx < len(scene.widgets):
                    w = scene.widgets[idx]
                    x = int(w.x * z)
                    y = int(w.y * z)
                    rw = int(w.width * z)
                    rh = int(w.height * z)
                    if getattr(self.settings, "high_contrast_overlays", False):
                        outline_color = color_hex("theme_hc_primary")
                        dash = ()
                        width = 2
                    else:
                        outline_color = color_hex("legacy_green_lime")
                        dash = (2, 2)
                        width = 1
                    self.canvas.create_rectangle(
                        x, y, x + rw, y + rh, outline=outline_color, width=width, dash=dash
                    )
                    self.canvas.create_text(
                        x + 2,
                        y + 2,
                        anchor=tk.NW,
                        text=f"#{idx} z={getattr(w,'z_index',0)}",
                        fill=outline_color,
                        font=("TkDefaultFont", self._scale_font_size(9, minimum=8)),
                    )
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
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

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
            snap = self._get_scaled_snap_size()
            widget_x = round(widget_x / snap) * snap
            widget_y = round(widget_y / snap) * snap

        return widget_x, widget_y

    def _hit_slider_track(self, widget: WidgetConfig, wx: int, wy: int) -> bool:
        """Return True if point is on the slider track/thumb area (avoid hijacking border drags)."""
        if getattr(widget, "type", None) != WidgetType.SLIDER.value:
            return False
        track_y = widget.y + widget.height // 2
        band = max(2, widget.height // 3)
        if abs(wy - track_y) > band:
            return False
        return widget.x + 1 <= wx <= widget.x + widget.width - 2

    def _slider_value_from_x(self, widget: WidgetConfig, wx: int) -> int:
        """Convert an x coord on the slider track into a clamped value."""
        span = max(1, widget.width - 4)
        rel = max(0, min(span, wx - widget.x - 2))
        value_range = max(0, widget.max_value - widget.min_value)
        if value_range == 0:
            return int(widget.min_value)
        ratio = rel / span
        return int(round(widget.min_value + ratio * value_range))

    def _apply_slider_value(self, widget: WidgetConfig, wx: int) -> None:
        """Set slider value from x-pos, refreshing only when it changes."""
        new_value = self._slider_value_from_x(widget, wx)
        if new_value == getattr(widget, "value", None):
            return
        widget.value = new_value
        self._slider_value_changed = True
        self._invalidate_cache()
        self.refresh()

    def _start_slider_drag(self, widget_idx: int, widget: WidgetConfig, wx: int) -> None:
        """Begin slider value drag without moving the widget itself."""
        self._slider_drag_idx = widget_idx
        self._slider_value_changed = False
        self.dragging = False
        self.resize_handle = None
        self.drag_start = None
        self.drag_offset = None
        self.drag_origin = None
        self._apply_slider_value(widget, wx)

    def _update_slider_drag(self, event) -> None:
        """Update slider value while dragging its thumb."""
        if self._slider_drag_idx is None:
            return
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene or not (0 <= self._slider_drag_idx < len(scene.widgets)):
            return
        widget = scene.widgets[self._slider_drag_idx]
        wx, _ = self._canvas_to_widget_coords(event.x, event.y)
        self._apply_slider_value(widget, wx)

    def _end_slider_drag(self) -> None:
        """Finish slider drag, saving undo state if needed."""
        if self._slider_drag_idx is None:
            return
        if self._slider_value_changed:
            try:
                self.designer._save_state()
            except Exception:
                pass
        self._slider_drag_idx = None
        self._slider_value_changed = False

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

            if (
                widget.x <= wx < widget.x + widget.width
                and widget.y <= wy < widget.y + widget.height
            ):
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

        # Larger hitbox tolerance for easier handle grabbing (12-16px total area)
        try:
            spacing_scale, _ = self._get_responsive_scales()
            tolerance = max(6, int(6 * spacing_scale))
        except Exception:
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
        if getattr(event, "keysym", None) == "Return" and self._last_mouse:
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

            widget = scene.widgets[widget_idx]
            wx, wy = self._canvas_to_widget_coords(event.x, event.y)
            # If clicking the slider track, adjust value instead of moving the widget
            if widget.type == WidgetType.SLIDER.value and self._hit_slider_track(widget, wx, wy):
                self._start_slider_drag(widget_idx, widget, wx)
                self._update_status_bar()
                return

            self.dragging = True
            self.drag_start = (event.x, event.y)

            # Calculate offset for smooth dragging
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
            self._box_select_count = 0
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
                "box": WidgetType.BOX if hasattr(WidgetType, "BOX") else WidgetType.PANEL,
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
                checked=defaults.get("checked", False),
            )
            self._record_recent_component(self._pending_component.get("name"))
            self.selected_widget_idx = len(scene.widgets) - 1
            try:
                if hasattr(self, "props_frame"):
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
        if self._slider_drag_idx is not None:
            self._update_slider_drag(event)
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
        if self._box_select_label is not None:
            self.canvas.delete(self._box_select_label)
            self._box_select_label = None
        self.box_select_rect = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=self._selection_colors()[0],
            width=2,
            dash=(4, 4),
            fill=self._selection_colors()[1],
            stipple="gray50",
            tags="box_select",
        )
        try:
            self._box_select_count = self._count_box_select(x1, y1, x2, y2)
            label_text = f"{self._box_select_count} in box • Align/Distribute ready"
            label_x = min(x1, x2) + self._scale_spacing(8, minimum=4)
            label_y = min(y1, y2) - self._scale_spacing(18, minimum=10)
            if label_y < 0:
                label_y = min(y1, y2) + self._scale_spacing(6, minimum=4)
            self._box_select_label = self.canvas.create_text(
                label_x,
                label_y,
                anchor=tk.NW,
                text=label_text,
                fill=color_hex("text_primary"),
                font=("TkDefaultFont", self._scale_font_size(9, minimum=8)),
                tags="box_select",
            )
            self._update_status_bar()
        except Exception:
            self._box_select_count = 0
        return True

    def _resize_active_widget(self, widget, event):
        wx, wy = self._canvas_to_widget_coords(event.x, event.y)
        if "n" in self.resize_handle:
            new_height = widget.y + widget.height - wy
            if new_height > 4:
                widget.y = wy
                widget.height = new_height
        if "s" in self.resize_handle:
            widget.height = max(4, wy - widget.y)
        if "w" in self.resize_handle:
            new_width = widget.x + widget.width - wx
            if new_width > 4:
                widget.x = wx
                widget.width = new_width
        if "e" in self.resize_handle:
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
            snap = self._get_scaled_snap_size()
            new_x = round(new_x / snap) * snap
            new_y = round(new_y / snap) * snap
        if self.settings.snap_to_widgets:
            new_x, new_y = self._apply_widget_snapping(widget, new_x, new_y)
        widget.x = max(0, min(new_x, self.designer.width - widget.width))
        widget.y = max(0, min(new_y, self.designer.height - widget.height))

    def _on_mouse_up(self, event):
        """Handle mouse up"""
        if self._pan_dragging:
            self._pan_dragging = False
            return
        if self._slider_drag_idx is not None:
            self._end_slider_drag()

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
        if self._box_select_label is not None:
            self.canvas.delete(self._box_select_label)
            self._box_select_label = None
        self.box_select_start = None
        self._box_select_count = 0
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
            self.canvas.configure(cursor=self._default_cursor())

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
        step = self._get_scaled_nudge(shift=False)
        if event.state & 0x0001:  # Shift key
            step = self._get_scaled_nudge(shift=True)
            if self.settings.snap_enabled and self.settings.snap_size > 0:
                # Horizontal shift: allow larger stride for generic objects;
                # vertical stays nearer grid
                if dx != 0 and not isinstance(widget, WidgetConfig):
                    step = max(step, self.settings.snap_size * 2)
                else:
                    step = max(step, self.settings.snap_size)

        new_x = widget.x + dx * step
        new_y = widget.y + dy * step

        # Respect snap-to-grid if enabled
        snap = self._get_scaled_snap_size()
        if self.settings.snap_enabled and snap > 0:
            snapped_x = round(new_x / snap) * snap
            snapped_y = round(new_y / snap) * snap
            # If snapping collapses movement, step to next cell in the direction
            if snapped_x == widget.x and dx != 0:
                snapped_x = widget.x + (snap if dx > 0 else -snap)
            if snapped_y == widget.y and dy != 0:
                snapped_y = widget.y + (snap if dy > 0 else -snap)
            new_x, new_y = snapped_x, snapped_y

        new_x = max(0, min(new_x, self.designer.width - widget.width))
        new_y = max(0, min(new_y, self.designer.height - widget.height))

        if new_x == widget.x and new_y == widget.y:
            return

        widget.x = new_x
        widget.y = new_y
        try:
            self.designer._save_state()
        except Exception:
            pass
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

    def _on_batch_apply(self) -> None:
        """Apply batch position/size deltas to current selection."""

        def _parse(var: tk.StringVar) -> int:
            try:
                return int(var.get() or 0)
            except Exception:
                return 0

        dx = _parse(self.batch_dx_var)
        dy = _parse(self.batch_dy_var)
        dw = _parse(self.batch_dw_var)
        dh = _parse(self.batch_dh_var)
        self._batch_apply_deltas(dx, dy, dw, dh)

    def _on_batch_reset(self) -> None:
        """Reset batch edit deltas to zero."""
        for var in (self.batch_dx_var, self.batch_dy_var, self.batch_dw_var, self.batch_dh_var):
            var.set("0")

    def _batch_apply_deltas(self, dx: int, dy: int, dw: int, dh: int) -> None:
        """Core batch apply logic (separate for testing)."""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        indices = self.selected_widgets or (
            [self.selected_widget_idx] if self.selected_widget_idx is not None else []
        )
        if not indices:
            return
        for idx in indices:
            if idx >= len(scene.widgets):
                continue
            w = scene.widgets[idx]
            new_w = max(4, w.width + dw)
            new_h = max(4, w.height + dh)
            new_x = w.x + dx
            new_y = w.y + dy
            new_x = max(0, min(new_x, max(0, self.designer.width - new_w)))
            new_y = max(0, min(new_y, max(0, self.designer.height - new_h)))
            w.x = new_x
            w.y = new_y
            w.width = new_w
            w.height = new_h
        try:
            self.designer._save_state()
        except Exception:
            pass
        self.refresh()

    def _open_animation_editor(self):
        """Open animation timeline editor"""
        if not hasattr(self, "anim_editor_window") or not self.anim_editor_window.winfo_exists():
            self.anim_editor_window = AnimationEditorWindow(self.root, self)
        else:
            self.anim_editor_window.lift()

    def _open_component_palette(self):
        """Open component palette window"""
        if (
            not hasattr(self, "component_palette_window")
            or not self.component_palette_window.winfo_exists()
        ):
            self.component_palette_window = ComponentPaletteWindow(self.root, self)
        else:
            self.component_palette_window.lift()

    def _open_template_manager(self):
        """Open template manager window"""
        if (
            not hasattr(self, "template_manager_window")
            or not self.template_manager_window.winfo_exists()
        ):
            self.template_manager_window = TemplateManagerWindow(self.root, self)
        else:
            self.template_manager_window.lift()

    def _open_icon_palette(self):
        """Open icon palette window"""
        if not hasattr(self, "icon_palette_window") or not self.icon_palette_window.winfo_exists():
            self.icon_palette_window = IconPaletteWindow(self.root, self)
        else:
            self.icon_palette_window.lift()

    def _open_quick_add_search(self, event=None):
        """Open quick add search dialog for fast component insertion"""
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Quick Add Component")
        dialog.geometry("500x400")
        dialog.configure(bg=color_hex("legacy_gray4"))
        dialog.transient(self.root)
        dialog.grab_set()

        # Search entry at top
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(search_frame, text=SEARCH_LABEL_TEXT, foreground=color_hex("legacy_gray14")).pack(
            side=tk.LEFT, padx=5
        )
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 12))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.focus_set()

        # Filter toggles (All / Recent / Favorites)
        filter_frame = ttk.Frame(dialog)
        filter_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        filter_var = tk.StringVar(value="favorites" if self._favorite_components else "all")
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 6))
        for value, label in (("all", "All"), ("recent", "Recent"), ("favorites", "Favorites")):
            ttk.Radiobutton(
                filter_frame,
                text=label,
                variable=filter_var,
                value=value,
                command=lambda: update_results(),
            ).pack(side=tk.LEFT, padx=4)

        # Listbox for results
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        results_list = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            bg=color_hex("surface"),
            fg=color_hex("text_primary"),
            selectbackground=color_hex("legacy_green_material"),
            selectforeground=color_hex("shadow"),
            height=15,
        )
        results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=results_list.yview)

        # Filtered components list
        filtered_components = []
        name_lookup = {c["name"]: c for c in self.ascii_components}

        def _source_components():
            mode = filter_var.get()
            if mode == "recent" and self._recent_components:
                comps = [name_lookup[n] for n in self._recent_components if n in name_lookup]
                if comps:
                    return comps
            if mode == "favorites" and self._favorite_components:
                comps = [name_lookup[n] for n in self._favorite_components if n in name_lookup]
                if comps:
                    return comps
            return self.ascii_components

        def update_results(*args):
            """Update filtered results based on search text"""
            query = search_var.get().lower().strip()
            self._fill_component_results(
                query, filtered_components, results_list, source_components=_source_components()
            )
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

        ttk.Button(button_frame, text="Add Component", command=add_selected_component).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            button_frame,
            text="Save list as Favorites",
            command=lambda: self._save_favorites_from_list(filtered_components),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Quick Slots", command=self._save_quick_slots).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

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
            ttk.Label(
                self.props_frame,
                text=f"{len(widgets)} widgets selected",
                font=("Arial", 12, "bold"),
            ).pack(anchor=tk.W, pady=5)
            ttk.Label(
                self.props_frame, text="(changes apply to all)", font=("Arial", 9, "italic")
            ).pack(anchor=tk.W, pady=2)
        else:
            widget = widgets[0]
            ttk.Label(
                self.props_frame, text=f"Widget: {widget.type}", font=("Arial", 12, "bold")
            ).pack(anchor=tk.W, pady=5)

        # Find common properties
        common_props = set(dir(widgets[0]))
        for w in widgets[1:]:
            common_props &= set(dir(w))

        # Text property (if common)
        if "text" in common_props:
            self._add_text_field(widget_indices, widgets)

        # Label property (if common)
        if "label" in common_props:
            self._add_label_field(widget_indices, widgets)

        # Value property (if common)
        if "value" in common_props:
            self._add_value_field(widget_indices, widgets)

        # Color property (if common)
        if "color" in common_props:
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
            new_zoom = float(zoom_str.rstrip("x"))
            # Zoom around canvas center by default for combobox changes
            cx = getattr(self.canvas, "winfo_width", lambda: 0)() // 2
            cy = getattr(self.canvas, "winfo_height", lambda: 0)() // 2
            self._auto_fit_done = False
            self._apply_zoom_at(cx, cy, new_zoom, user_override=True)
        except ValueError:
            pass

    def _on_zoom_fit(self):
        """Force auto-fit zoom to fill available canvas area."""
        self._auto_fit_done = False
        self._apply_auto_zoom_fit(force=True)

    def _on_grid_padding_change(self):
        """Handle change to grid padding spinboxes (percentage & minimum px)."""
        try:
            raw_pct = float(getattr(self, "_grid_pad_var", tk.DoubleVar(value=0)).get())
            pct = max(0.0, min(0.5, raw_pct / 100.0))  # clamp 0–50% => 0.0–0.5
            min_px = int(getattr(self, "_grid_pad_min_var", tk.IntVar(value=0)).get())
            min_px = max(0, min_px)
            self.settings.grid_padding_pct = pct
            self.settings.grid_padding_min_px = min_px
            # Persist to shared settings cache
            if hasattr(self, "_settings_cache"):
                try:
                    self._settings_cache["grid_padding_pct"] = pct
                    self._settings_cache["grid_padding_min_px"] = min_px
                    self._save_settings()
                except Exception:
                    pass
            self.refresh(force=True)
        except Exception:
            pass

    def _mk_wheel_event(self, e, delta):
        """Create a proxy object carrying delta like MouseWheel events."""

        class _E:
            pass

        ne = _E()
        ne.widget = getattr(e, "widget", None)
        ne.x = getattr(e, "x", 0)
        ne.y = getattr(e, "y", 0)
        ne.delta = delta
        return ne

    def _on_ctrl_wheel_zoom(self, event):
        """Zoom in/out centered at cursor when Ctrl+Wheel is used."""
        # Determine zoom step
        step = 1.1 if event.delta > 0 else (1 / 1.1)
        new_zoom = max(self._zoom_min, min(self._zoom_max, self.settings.zoom * step))
        self._auto_fit_done = False
        self._apply_zoom_at(event.x, event.y, new_zoom, user_override=True)

    def _apply_zoom_at(self, win_x: int, win_y: int, new_zoom: float, user_override: bool = False):
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
        view_w = getattr(self.canvas, "winfo_width", lambda: 1)()
        view_h = getattr(self.canvas, "winfo_height", lambda: 1)()
        left = max(0, min(scaled_w - view_w, int(new_abs_x - win_x)))
        top = max(0, min(scaled_h - view_h, int(new_abs_y - win_y)))
        # Move view
        try:
            self.canvas.xview_moveto(0 if scaled_w <= 0 else left / scaled_w)
            self.canvas.yview_moveto(0 if scaled_h <= 0 else top / scaled_h)
            self.canvas.configure(scrollregion=(0, 0, scaled_w, scaled_h))
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
                self.canvas.configure(cursor=self._default_cursor())
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
            self._preview_theme = "custom"
            self._settings_cache["preview_theme"] = self._preview_theme
            self._save_settings()
            self.refresh()

    def _on_hc_toggle(self):
        """Toggle high-contrast overlay colors for handles/guides/status."""
        try:
            self.settings.high_contrast_overlays = bool(self.hc_var.get())
            self._apply_status_font()
            self.refresh()
        except Exception:
            pass

    def _toggle_mini_help(self):
        """Toggle mini help overlay (F1/F10)."""
        try:
            self._show_mini_help = not getattr(self, "_show_mini_help", False)
            self.refresh()
        except Exception:
            pass

    def _toggle_perf_overlay(self):
        """Toggle simple perf overlay (FPS/render time bar)."""
        try:
            self._show_perf_overlay = not getattr(self, "_show_perf_overlay", False)
            self._settings_cache["perf_overlay"] = self._show_perf_overlay
            self._save_settings()
            self.refresh()
        except Exception:
            pass

    def _hide_onboarding_toast(self, persist: bool = False) -> None:
        """Hide onboarding toast overlay."""
        if hasattr(self, "canvas"):
            try:
                self.canvas.delete(self._onboarding_toast_tag)
            except Exception:
                pass
        if persist:
            self._settings_cache["hide_onboarding_toast"] = True
            self._save_settings()

    def _show_onboarding_toast_if_needed(self):
        """Show first-run onboarding tip (grid/snap/quick-add)."""
        if HEADLESS or self._settings_cache.get("hide_onboarding_toast", False):
            return
        if not hasattr(self, "canvas"):
            return
        try:
            pad = self._scale_spacing(8, minimum=6)
            font_size = self._scale_font_size(10, minimum=9)
            lines = [
                "Tip: Zapni Grid/Snap v toolbaru pro přesné umístění.",
                "Ctrl+Shift+A otevře rychlé přidání komponenty.",
                "F1/F10 = mini help, HC UI = vysoký kontrast.",
                "Klikni na toast pro skrytí (už se nezobrazí).",
            ]
            width = max(len(ln) for ln in lines) * self._scale_spacing(6, minimum=5)
            x0 = self._scale_spacing(16, minimum=10)
            y0 = self._scale_spacing(40, minimum=28)
            x1 = x0 + width + pad * 2
            y1 = y0 + pad * 2 + len(lines) * self._scale_spacing(14, minimum=12)
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray8"),
                stipple="gray25",
                tags=self._onboarding_toast_tag,
            )
            ty = y0 + pad
            for ln in lines:
                self.canvas.create_text(
                    x0 + pad,
                    ty,
                    anchor=tk.NW,
                    text=ln,
                    fill=color_hex("text_primary"),
                    font=("TkDefaultFont", font_size),
                    tags=self._onboarding_toast_tag,
                )
                ty += self._scale_spacing(14, minimum=12)
            # Bind click to dismiss permanently
            self.canvas.tag_bind(
                self._onboarding_toast_tag,
                "<Button-1>",
                lambda e: self._hide_onboarding_toast(True),
            )
            # Auto-hide after 8 seconds (non-persist)
            self.root.after(8000, lambda: self._hide_onboarding_toast(persist=False))
        except Exception:
            pass

    def _export_png(self):
        """Export preview as PNG with preset options"""
        # Show export options dialog
        export_dialog = tk.Toplevel(self.root)
        export_dialog.title("PNG Export Options")
        export_dialog.geometry("350x250")
        export_dialog.transient(self.root)
        export_dialog.grab_set()

        # Load last used settings (or defaults)
        last_scale = getattr(self, "_last_export_scale", 1)
        last_guides = getattr(self, "_last_export_guides", False)
        last_responsive = getattr(self, "_last_export_responsive", False)
        last_theme = getattr(self, "_last_export_theme", "current")
        last_tokens = getattr(self, "_last_export_tokens", "default")

        # Scale preset
        scale_frame = ttk.LabelFrame(
            export_dialog, text="Scale", padding=self._scale_spacing(10, minimum=6)
        )
        scale_frame.pack(fill=tk.X, padx=10, pady=5)

        scale_var = tk.IntVar(value=last_scale)
        ttk.Radiobutton(scale_frame, text="@1x (Original size)", variable=scale_var, value=1).pack(
            anchor=tk.W
        )
        ttk.Radiobutton(scale_frame, text="@2x (Double size)", variable=scale_var, value=2).pack(
            anchor=tk.W
        )
        ttk.Radiobutton(scale_frame, text="@3x (Triple size)", variable=scale_var, value=3).pack(
            anchor=tk.W
        )
        ttk.Radiobutton(scale_frame, text="@4x (Quadruple size)", variable=scale_var, value=4).pack(
            anchor=tk.W
        )

        # Content preset
        content_frame = ttk.LabelFrame(
            export_dialog, text="Content", padding=self._scale_spacing(10, minimum=6)
        )
        content_frame.pack(fill=tk.X, padx=10, pady=5)

        guides_var = tk.BooleanVar(value=last_guides)
        ttk.Radiobutton(
            content_frame, text="Scene only (clean export)", variable=guides_var, value=False
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            content_frame, text="With guides (grid/bounds)", variable=guides_var, value=True
        ).pack(anchor=tk.W)

        resp_var = tk.BooleanVar(value=last_responsive)
        ttk.Checkbutton(
            content_frame, text="Respect responsive scale (spacing/font)", variable=resp_var
        ).pack(anchor=tk.W, pady=(6, 0))

        theme_frame = ttk.LabelFrame(
            export_dialog, text="Theme", padding=self._scale_spacing(10, minimum=6)
        )
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        theme_var = tk.StringVar(value=last_theme)
        ttk.Label(theme_frame, text="Background:").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Combobox(
            theme_frame,
            values=["current", "default", "light", "dark", "nord", "dracula", "hc", "cyber"],
            textvariable=theme_var,
            width=12,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)

        tokens_frame = ttk.LabelFrame(
            export_dialog, text="Tokens", padding=self._scale_spacing(10, minimum=6)
        )
        tokens_frame.pack(fill=tk.X, padx=10, pady=5)
        tokens_var = tk.StringVar(value=last_tokens)
        ttk.Radiobutton(tokens_frame, text="Default", variable=tokens_var, value="default").pack(
            anchor=tk.W
        )
        ttk.Radiobutton(tokens_frame, text="High-Contrast", variable=tokens_var, value="hc").pack(
            anchor=tk.W
        )
        ttk.Radiobutton(
            tokens_frame, text="Print (light, clean)", variable=tokens_var, value="print"
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            tokens_frame, text="Mono (grayscale)", variable=tokens_var, value="mono"
        ).pack(anchor=tk.W)

        # Buttons
        btn_frame = ttk.Frame(export_dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        result = {"cancelled": True}

        def do_export():
            result["cancelled"] = False
            result["scale"] = scale_var.get()
            result["guides"] = guides_var.get()
            result["responsive"] = resp_var.get()
            result["theme"] = theme_var.get()
            result["tokens"] = tokens_var.get()
            # Remember choices
            self._last_export_scale = result["scale"]
            self._last_export_guides = result["guides"]
            self._last_export_responsive = result["responsive"]
            self._last_export_theme = result["theme"]
            self._last_export_tokens = result["tokens"]
            self._settings_cache["last_export_theme"] = self._last_export_theme
            self._settings_cache["last_export_tokens"] = self._last_export_tokens
            self._save_settings()
            export_dialog.destroy()

        ttk.Button(btn_frame, text="Export", command=do_export, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=export_dialog.destroy, width=15).pack(
            side=tk.LEFT, padx=5
        )

        # Wait for dialog
        export_dialog.wait_window()

        if result.get("cancelled"):
            return

        # Get export settings
        scale = result["scale"]
        include_guides = result["guides"]
        respect_resp = result.get("responsive", False)
        export_theme = result.get("theme", "current")
        export_tokens = result.get("tokens", "default")

        # Ask for filename
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), FILETYPE_ALL_PAIR],
            initialfile=f"ui_preview_{scale}x.png",
        )

        if not filename:
            return

        # Create export image
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene:
            # Temporarily adjust zoom for export scale
            original_zoom = self.settings.zoom
            eff_scale = scale
            if respect_resp:
                spacing_scale, _ = self._get_responsive_scales()
                eff_scale = max(0.1, scale * spacing_scale)
            self.settings.zoom = eff_scale

            bg = self._resolve_theme_bg(export_theme) or self.settings.background_color
            # Token preset adjustments (temporary)
            original_hc = getattr(self.settings, "high_contrast_overlays", False)
            original_bg = bg
            try:
                if export_tokens == "hc":
                    self.settings.high_contrast_overlays = True
                elif export_tokens == "print":
                    self.settings.high_contrast_overlays = False
                    if export_theme == "current":
                        bg = color_hex("legacy_gray19")
                elif export_tokens == "mono":
                    self.settings.high_contrast_overlays = False
                img = self._render_scene_image(
                    scene,
                    background_color=bg,
                    include_grid=include_guides,
                    use_overlays=include_guides,
                    highlight_selection=False,
                )
                if export_tokens == "mono":
                    try:
                        img = img.convert("L").convert("RGB")
                    except Exception:
                        pass
            finally:
                self.settings.high_contrast_overlays = original_hc
                bg = original_bg

            # Restore zoom
            self.settings.zoom = original_zoom

            # Save
            img.save(filename)
            suffix = f"@{eff_scale:.1f}x" if respect_resp else f"@{scale}x"
            messagebox.showinfo(EXPORT_COMPLETE_TITLE, f"Saved {suffix} PNG to:\n{filename}")
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
            initialfile=f"{self.designer.current_scene}.c",
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
            initialfile=f"{self.designer.current_scene}_widgetconfig.txt",
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
        dialog.configure(bg=color_hex("legacy_gray4"))

        # Header
        header = ttk.Frame(dialog)
        header.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(header, text="🖼️ Enhanced SVG Export", font=("Arial", 14, "bold")).pack()
        ttk.Label(
            header,
            text="Professional-quality vector export with advanced features",
            foreground=color_hex("legacy_gray1"),
        ).pack()

        # Main content
        content = ttk.Frame(dialog)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Preset selection
        preset_frame = ttk.LabelFrame(
            content, text="Quality Preset", padding=self._scale_spacing(10, minimum=6)
        )
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
            ttk.Radiobutton(frame, text=label, variable=preset_var, value=value).pack(side=tk.LEFT)
            ttk.Label(
                frame, text=desc, foreground=color_hex("legacy_gray1"), font=("Arial", 8)
            ).pack(side=tk.LEFT, padx=(10, 0))

        # Advanced options
        options_frame = ttk.LabelFrame(
            content, text="Advanced Options", padding=self._scale_spacing(10, minimum=6)
        )
        options_frame.pack(fill=tk.X, pady=(0, 10))

        gradients_var = tk.BooleanVar(value=True)
        shadows_var = tk.BooleanVar(value=False)
        patterns_var = tk.BooleanVar(value=False)
        fonts_var = tk.BooleanVar(value=False)
        metadata_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            options_frame, text="Include Gradients (smoother colors)", variable=gradients_var
        ).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            options_frame, text="Include Shadows (depth effects)", variable=shadows_var
        ).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            options_frame, text="Include Patterns (textures)", variable=patterns_var
        ).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            options_frame, text="Embed Fonts (requires font file)", variable=fonts_var
        ).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Include Metadata", variable=metadata_var).pack(
            anchor=tk.W, pady=2
        )

        # Scale
        scale_frame = ttk.LabelFrame(
            content, text="Export Scale", padding=self._scale_spacing(10, minimum=6)
        )
        scale_frame.pack(fill=tk.X, pady=(0, 10))

        scale_var = tk.DoubleVar(value=1.0)
        scale_slider = ttk.Scale(
            scale_frame, from_=0.5, to=4.0, variable=scale_var, orient=tk.HORIZONTAL
        )
        scale_slider.pack(fill=tk.X, pady=2)

        scale_label = ttk.Label(scale_frame, text="1.0x")
        scale_label.pack()

        def update_scale_label(*args):
            scale_label.config(text=f"{scale_var.get():.1f}x")

        scale_var.trace_add("write", update_scale_label)

        # Font path (conditional)
        font_frame = ttk.LabelFrame(
            content, text="Font Embedding (Optional)", padding=self._scale_spacing(10, minimum=6)
        )
        font_frame.pack(fill=tk.X, pady=(0, 10))

        font_path_var = tk.StringVar(value="")
        font_entry = ttk.Entry(font_frame, textvariable=font_path_var, state="readonly")
        font_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        def browse_font():
            path = filedialog.askopenfilename(
                title="Select Font File",
                filetypes=[("Font files", "*.ttf *.otf *.woff *.woff2"), FILETYPE_ALL_PAIR],
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
                initialfile=f"{self.designer.current_scene}_enhanced.svg",
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
                messagebox.showinfo(
                    EXPORT_COMPLETE_TITLE,
                    f"Enhanced SVG exported to:\n{filename}\n\n"
                    f"Preset: {preset_var.get().upper()}\n"
                    f"Features: Gradients={gradients_var.get()}, "
                    f"Shadows={shadows_var.get()}, "
                    f"Patterns={patterns_var.get()}",
                )
            except Exception as e:
                messagebox.showerror(EXPORT_ERROR_TITLE, f"Failed to export:\n{e}")

        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Export SVG", command=do_export).pack(side=tk.RIGHT, padx=5)

    def _open_ascii_preview(self):
        """Open live ASCII preview window with enhanced styling"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            messagebox.showerror("Preview Error", "No active scene.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Live ASCII Preview - {self.designer.current_scene}")
        win.geometry("800x600")
        win.configure(bg=color_hex("surface"))

        # Create toolbar
        toolbar = ttk.Frame(win)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="ASCII Renderer v2.0", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            toolbar,
            text=REFRESH_LABEL,
            command=lambda: self._refresh_ascii_preview(text_widget, scene),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar,
            text="💾 Copy to Clipboard",
            command=lambda: self._copy_ascii_to_clipboard(text_widget),
        ).pack(side=tk.LEFT, padx=5)

        # Create text widget with scrollbar
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            frame,
            font=("Consolas", 9),
            bg=color_hex("legacy_gray5"),
            fg=color_hex("legacy_gray9"),
            insertbackground=color_hex("text_primary"),
            yscrollcommand=scrollbar.set,
            wrap=tk.NONE,
            relief=tk.FLAT,
            borderwidth=0,
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # Configure text tags for syntax highlighting
        text_widget.tag_config(
            "border", foreground=color_hex("legacy_blue_light")
        )  # Blue for borders
        text_widget.tag_config(
            "fill_button", foreground=color_hex("legacy_teal")
        )  # Teal for buttons
        text_widget.tag_config("fill_box", foreground=color_hex("legacy_gray10"))  # Gray for boxes
        text_widget.tag_config("fill_icon", foreground=color_hex("legacy_gold"))  # Yellow for icons
        text_widget.tag_config(
            "text_label", foreground=color_hex("legacy_salmon")
        )  # Orange for text

        # Render ASCII UI
        self._refresh_ascii_preview(text_widget, scene)

    def _show_ascii_tab(self):
        """Show the inline ASCII Preview tab and refresh its content."""
        if getattr(self, "_headless", False):
            return
        try:
            # Select ASCII tab
            for i in range(self.right_tabs.index("end")):
                if self.right_tabs.tab(i, "text") == "ASCII Preview":
                    self.right_tabs.select(i)
                    break
            # Refresh content
            scene = self.designer.scenes.get(self.designer.current_scene)
            if scene and hasattr(self, "ascii_text_widget"):
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
            font_size = self._scale_font_size(10, minimum=9)
            line_height = max(12, int(font_size * 1.4))
            box_width = self._scale_spacing(360, minimum=260)
            pad = self._scale_spacing(10, minimum=6)
            x0 = self._scale_spacing(8, minimum=6)
            y0 = self._scale_spacing(8, minimum=6)
            lines = [
                "Drag to move | Resize via corners/edges",
                "Shift+Drag=axis lock | Shift+Click=multi-select",
                "Arrows nudge (Shift=grid) | Right-click menu",
                "Toolbar: Grid | Snap | Hints | Export | Help",
            ]
            x1 = x0 + box_width
            y1 = y0 + pad * 2 + line_height * len(lines)
            # Simulated translucency via stipple
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray8"),
                stipple="gray25",
            )
            ty = y0 + pad
            for ln in lines:
                self.canvas.create_text(
                    x0 + pad,
                    ty,
                    anchor=tk.NW,
                    text=ln,
                    fill=color_hex("text_primary"),
                    font=("TkDefaultFont", font_size),
                )
                ty += line_height
        except Exception:
            pass

    def _draw_mini_help_overlay(self):
        """Draw a richer on-canvas mini help panel (F1/F10 toggle)."""
        try:
            font_size = self._scale_font_size(10, minimum=9)
            line_height = max(12, int(font_size * 1.35))
            pad = self._scale_spacing(10, minimum=6)
            x0 = self._scale_spacing(12, minimum=8)
            y0 = self._scale_spacing(80, minimum=50)
            lines = [
                "Pan/Zoom: Space+Drag | Ctrl+Wheel | 0.5-10x dropdown",
                "Edit: Handles resize | Shift=axis lock | Alt+Arrows align | Alt+H/V distribute",
                "Insert: Ctrl+Shift+A search | Ctrl+1-9 quick slots | Right-click menu",
                (
                    f"Responsive: tier {getattr(self, '_responsive_tier', 'medium')} | "
                    "Hints toggle | Mini Help F1/F10"
                ),
                "Themes: dropdown | HC UI toggle | Export respects responsive scale & theme",
            ]
            width = max(len(ln) for ln in lines) * self._scale_spacing(6, minimum=5)
            x1 = x0 + width + pad * 2
            y1 = y0 + pad * 2 + line_height * len(lines)
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray8"),
                stipple="gray25",
            )
            ty = y0 + pad
            for ln in lines:
                self.canvas.create_text(
                    x0 + pad,
                    ty,
                    anchor=tk.NW,
                    text=ln,
                    fill=color_hex("text_primary"),
                    font=("TkDefaultFont", font_size),
                )
                ty += line_height
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
        base_tol = max(2, int(getattr(self.settings, "snap_distance", 4)))
        tol = max(base_tol, self._get_scaled_snap_size())

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
            color = color_hex("legacy_green_mint")
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
                menu.add_command(
                    label="Properties…",
                    command=lambda: self._edit_widget_properties(self.selected_widget_idx),
                )
                menu.add_command(label="Duplicate", command=lambda: self._on_duplicate(None))
                menu.add_command(label="Delete", command=lambda: self._on_delete_widget(None))
                menu.add_separator()
            # Quick add submenu
            add_menu = tk.Menu(menu, tearoff=0)
            for label, kind in (
                ("Label", "label"),
                ("Button", "button"),
                ("Box", "box"),
                ("Panel", "panel"),
                ("Progress", "progressbar"),
                ("Gauge", "gauge"),
                ("Checkbox", "checkbox"),
                ("Slider", "slider"),
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
        large = w.width >= 3 and w.height >= 3
        for y in range(w.y, max_y):
            is_top = y == w.y
            is_bottom = y == w.y + w.height - 1
            for x in range(w.x, max_x):
                if large:
                    is_left = x == w.x
                    is_right = x == w.x + w.width - 1
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
            total_space = last.x - (first.x + first.width)
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
            total_space = last.y - (first.y + first.height)
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

        self.clipboard = [
            deepcopy(scene.widgets[i]) for i in self.selected_widgets if i < len(scene.widgets)
        ]
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
            if not hasattr(self, "canvas"):
                scene = self.designer.scenes.get(self.designer.current_scene)
                if not scene:
                    self.designer.create_scene("test_scene")
                    scene = self.designer.scenes.get(self.designer.current_scene)
                from ui_designer import WidgetType

                type_map = {
                    "label": WidgetType.LABEL,
                    "button": WidgetType.BUTTON,
                    "box": WidgetType.BOX if hasattr(WidgetType, "BOX") else WidgetType.PANEL,
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
                    checked=defaults.get("checked", False),
                )
                self.selected_widget_idx = len(scene.widgets) - 1
                self._record_recent_component(component.get("name"))
                return

            # GUI placement: set pending component to show preview until click
            self._pending_component = component
            try:
                cw = getattr(self.canvas, "winfo_width", lambda: 0)() or (
                    self.designer.width * self.settings.zoom
                )
                ch = getattr(self.canvas, "winfo_height", lambda: 0)() or (
                    self.designer.height * self.settings.zoom
                )
                self._last_mouse = (cw // 2, ch // 2)
            except Exception:
                self._last_mouse = None
            self._invalidate_cache()
            self.refresh()
            self._update_status_bar()

        except Exception as e:
            if hasattr(self, "status_bar"):
                self.status_bar.configure(text=f"Failed to insert: {e}")
            else:
                raise

    def run(self):
        """Run the preview window"""
        self.root.mainloop()

    def _push_stub(self):
        """Stub for pushing current scene to device (placeholder)."""
        scene = self._get_active_scene()
        if not scene:
            try:
                messagebox.showwarning("Push", "No active scene to push")
            except Exception:
                pass
            return
        try:
            payload = json.dumps(scene.to_dict()) if hasattr(scene, "to_dict") else json.dumps(
                {"widgets": [getattr(w, "__dict__", {}) for w in scene.widgets]}
            )
            path = os.path.join(
                tempfile.gettempdir(),
                "esp32os_push_payload.json",
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(payload)
            try:
                messagebox.showinfo(
                    "Push",
                    (
                        f"Payload written to {path}\n"
                        "(This is a stub – replace with network/WebSocket push)"
                    ),
                )
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror("Push Failed", f"Could not prepare payload: {e}")
            except Exception:
                pass

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
        for idx, widget in enumerate(getattr(scene, "widgets", [])):
            if not getattr(widget, "visible", True):
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
            # Draw grid before widgets so overlays/text remain legible
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
            snap = self._get_scaled_snap_size()
            grid = self._get_scaled_grid_size()
            if self.settings.snap_enabled and snap > 0:
                size = snap
                x = round(x / size) * size
                y = round(y / size) * size
            elif self.settings.grid_enabled and grid > 0:
                size = grid
                x = (x // size) * size
                y = (y // size) * size
            x = max(0, min(self.designer.width - pw, x))
            y = max(0, min(self.designer.height - ph, y))
            if pw > 0 and ph > 0 and hasattr(draw, "rectangle"):
                try:
                    from PIL import ImageDraw as _ID  # type: ignore

                    overlay = Image.new(
                        "RGBA", (self.designer.width, self.designer.height), (0, 0, 0, 0)
                    )
                    o_draw = _ID.Draw(overlay)
                    o_draw.rectangle(
                        [(x, y), (x + pw, y + ph)],
                        fill=self._pending_fill,
                        outline=(0, 200, 255, 150),
                        width=1,
                    )
                    img.paste(overlay, (0, 0), overlay)
                except Exception:
                    draw.rectangle([(x, y), (x + pw, y + ph)], outline=(0, 200, 255), width=1)
            name = self._pending_component.get("name", "widget")
            try:
                draw.text((x + 2, y + 2), f"Preview: {name}", fill=(0, 220, 255))
                draw.text((x + 2, y + 16), f"{pw}x{ph} @ {x},{y}", fill=(0, 220, 255))
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
            spacing_scale, font_scale = self._get_responsive_scales()
            # Include canvas/background parameters
            items.append(
                (
                    getattr(scene, "width", self.designer.width),
                    getattr(scene, "height", self.designer.height),
                    self.settings.background_color,
                    self.settings.grid_enabled,
                    self._get_scaled_grid_size(),
                )
            )
            items.append(("responsive_scales", round(spacing_scale, 3), round(font_scale, 3)))
            for w in scene.widgets:
                # Collect common properties defensively
                items.append(
                    (
                        getattr(w, "type", None),
                        getattr(w, "x", None),
                        getattr(w, "y", None),
                        getattr(w, "width", None),
                        getattr(w, "height", None),
                        getattr(w, "text", None),
                        getattr(w, "value", None),
                        getattr(w, "checked", None),
                        getattr(w, "color_fg", None),
                        getattr(w, "color_bg", None),
                        getattr(w, "border", None),
                        getattr(w, "border_style", None),
                        getattr(w, "visible", True),
                    )
                )
            return hash(tuple(items))
        except Exception:
            # Fallback to changing number to force re-render in error cases
            return object.__hash__(scene)


