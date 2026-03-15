#!/usr/bin/env python3
"""
cyberpunk_designer.app

Pixel-art UI Designer front-end (pygame) backed by existing UIDesigner/SceneConfig/WidgetConfig.
Step 2: load JSON (UIDesigner schema), render widgets, select/drag/resize with grid snap,
basic inspector and status bar. No full palette/inspector editing yet, but core interactions work.

Run (from repo root with venv active):
    .\\.venv\\Scripts\\python cyberpunk_editor.py [json_path]
"""

from __future__ import annotations

import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from event_manager import EventManager
from ui_designer import HARDWARE_PROFILES, UIDesigner, WidgetConfig
from ui_template_manager import Template, TemplateLibrary

from . import (
    component_insert,
    context_menu,
    drawing,
    fit_text,
    fit_widget,
    focus_nav,
    groups,
    input_handlers,
    io_ops,
    layout_tools,
    live_preview,
    reporting,
    scene_ops,
    selection_ops,
    text_metrics,
    windowing,
)
from . import constants as _constants
from .component_fields import component_field_specs
from .components import component_blueprints
from .constants import (
    AUTOSAVE_SEC,
    BAUD_DEFAULT,
    DBLCLICK_PX,
    DBLCLICK_SEC,
    DEFAULT_INSPECTOR_W,
    DEFAULT_JSON,
    DEFAULT_PALETTE_W,
    FPS,
    GRID,
    MAX_AUTO_SCALE_DEFAULT,
    MIN_FPS,
    NAMED_COLORS,
    SCALE,
    SCENE_TABS_H,
    STATUS_H,
    TOOLBAR_H,
    WIN_MARGIN_H,
    WIN_MARGIN_W,
    hex_to_rgb,
    safe_save_state,
    snap,
)
from .inspector_logic import compute_inspector_rows, inspector_commit_edit, inspector_field_to_str
from .layout import Layout
from .perf import RenderCache
from .state import EditorState

# Backward-compatible module symbol used by tests and legacy monkeypatches.
PROFILE_ORDER = _constants.PROFILE_ORDER


def _build_delegate_registry():
    """Build {method_name: (module, target_fn_name)} for simple self->module delegates."""
    reg: dict[str, tuple[object, str]] = {}

    # selection_ops: _name(self) -> selection_ops.name(self)
    _SEL_OPS = {
        "delete_selected",
        "copy_selection",
        "paste_clipboard",
        "cut_selection",
        "duplicate_selection",
        "select_all",
        "cycle_style",
        "toggle_visibility",
        "cycle_widget_type",
        "cycle_border_style",
        "copy_style",
        "paste_style",
        "arrange_in_row",
        "arrange_in_column",
        "cycle_color_preset",
        "toggle_border",
        "cycle_text_overflow",
        "cycle_align",
        "cycle_valign",
        "smart_edit",
        "toggle_enabled",
        "swap_fg_bg",
        "select_same_type",
        "toggle_checked",
        "reset_to_defaults",
        "select_locked",
        "select_overflow",
        "make_full_width",
        "make_full_height",
        "swap_dimensions",
        "select_same_z",
        "select_same_style",
        "select_hidden",
        "widget_info",
        "invert_selection",
        "auto_rename",
        "select_same_color",
        "scene_stats",
        "select_parent_panel",
        "select_children",
        "copy_to_next_scene",
        "snap_selection_to_grid",
        "paste_in_place",
        "broadcast_to_all_scenes",
        "select_same_size",
        "clear_margins",
        "hide_unselected",
        "select_bordered",
        "move_selection_to_origin",
        "fit_scene_to_content",
        "show_all_widgets",
        "unlock_all_widgets",
        "select_overlapping",
        "toggle_all_borders",
        "remove_degenerate_widgets",
        "enable_all_widgets",
        "sort_widgets_by_position",
        "compact_widgets",
        "snap_sizes_to_grid",
        "select_all_panels",
        "quick_clone",
        "list_templates",
        "extract_to_new_scene",
        "clear_padding",
        "flatten_z_indices",
        "stack_vertical",
        "stack_horizontal",
        "equalize_widths",
        "equalize_heights",
        "swap_positions",
        "center_in_scene",
        "duplicate_below",
        "duplicate_right",
        "cycle_gray_fg",
        "cycle_gray_bg",
        "grid_arrange",
        "reverse_widget_order",
        "flip_vertical",
        "normalize_sizes",
        "auto_name_scene",
        "propagate_border",
        "remove_duplicates",
        "increment_text",
        "propagate_style",
        "swap_content",
        "outline_mode",
        "clone_text",
        "propagate_align",
        "propagate_colors",
        "flip_horizontal",
        "propagate_value",
        "propagate_padding",
        "propagate_margin",
        "propagate_appearance",
        "auto_flow_layout",
        "measure_selection",
        "space_evenly_h",
        "space_evenly_v",
        "replace_text_in_scene",
        "select_same_type_as_current",
        "zoom_to_selection",
        "scene_overview",
        "widget_type_summary",
        "toggle_focus_order_overlay",
        "export_selection_json",
        "create_header_bar",
        "create_nav_row",
        "create_form_pair",
        "create_status_bar",
        "create_toggle_group",
        "create_slider_with_label",
        "create_gauge_panel",
        "create_progress_section",
        "create_icon_button_row",
        "create_card_layout",
        "create_dashboard_grid",
        "create_split_layout",
        "wrap_in_panel",
        "fill_scene",
        "shrink_to_content",
        "auto_label_widgets",
        "inset_widgets",
        "outset_widgets",
        "align_to_scene_top",
        "align_to_scene_bottom",
        "align_to_scene_left",
        "align_to_scene_right",
        "center_horizontal",
        "center_vertical",
        "delete_hidden_widgets",
        "delete_offscreen_widgets",
        "tile_fill_scene",
        "match_first_height",
        "scatter_random",
        "toggle_all_checked",
        "reset_all_values",
        "propagate_text",
        "flatten_z_index",
        "number_widget_ids",
        "z_by_position",
        "clone_to_grid",
        "distribute_rows",
        "mirror_scene_horizontal",
        "sort_widgets_by_z",
        "clamp_to_scene",
        "mirror_scene_vertical",
        "select_unlocked",
        "snap_all_to_grid",
        "select_disabled",
        "center_in_parent",
        "size_to_text",
        "pack_left",
        "pack_top",
        "fill_parent",
        "clear_all_text",
        "move_to_origin",
        "make_square",
        "scale_up",
        "scale_down",
        "number_text",
        "spread_values",
        "reset_padding",
        "reset_colors",
        "outline_only",
        "select_largest",
        "select_smallest",
        "cascade_arrange",
        "set_inverse_style",
        "set_bold_style",
        "set_default_style",
        "align_h_centers",
        "align_v_centers",
        "align_left_edges",
        "align_top_edges",
        "align_right_edges",
        "align_bottom_edges",
        "distribute_columns_3",
    }
    for name in _SEL_OPS:
        reg[f"_{name}"] = (selection_ops, name)

    # scene_ops: _name(self) -> scene_ops.name(self)
    _SCENE_OPS = {
        "build_template_actions",
        "apply_first_template",
        "cycle_profile",
        "new_scene",
        "intelligent_auto_arrange",
        "z_order_bring_to_front",
        "z_order_send_to_back",
        "toggle_lock_selection",
        "zoom_to_fit",
        "save_selection_as_template",
        "delete_current_scene",
        "close_other_scenes",
        "close_scenes_to_right",
        "add_new_scene",
        "duplicate_current_scene",
        "rename_current_scene",
        "export_c_header",
        "auto_arrange_grid",
        "toggle_clean_preview",
        "goto_widget_prompt",
    }
    for name in _SCENE_OPS:
        reg[f"_{name}"] = (scene_ops, name)

    # drawing: _name(self) -> drawing.name(self)
    _DRAWING_OPS = {
        "smart_dirty_tracking",
        "auto_adjust_quality",
        "draw_frame",
        "optimized_draw_frame",
        "draw_toolbar",
        "draw_scene_tabs",
        "draw_palette",
        "draw_canvas",
        "draw_inspector",
        "draw_status",
    }
    for name in _DRAWING_OPS:
        reg[f"_{name}"] = (drawing, name)

    # io_ops: _name(self) -> io_ops.name(self)  (+ two public names)
    _IO_OPS = {
        "load_or_default",
        "load_widget_presets",
        "save_widget_presets",
        "load_prefs",
        "save_prefs",
        "write_audit_report",
        "maybe_autosave",
    }
    for name in _IO_OPS:
        reg[f"_{name}"] = (io_ops, name)
    reg["save_json"] = (io_ops, "save_json")
    reg["load_json"] = (io_ops, "load_json")

    # groups: _name(self) -> groups.name(self)
    _GROUP_OPS = {
        "selected_group_exact",
        "selected_component_group",
        "group_selection",
        "ungroup_selection",
    }
    for name in _GROUP_OPS:
        reg[f"_{name}"] = (groups, name)

    # focus_nav: _name(self) -> focus_nav.name(self)
    for name in ("ensure_focus", "activate_focused"):
        reg[f"_{name}"] = (focus_nav, name)

    # context_menu
    reg["_ctx_view_items"] = (context_menu, "ctx_view_items")

    # windowing
    reg["_hardware_accelerated_scale"] = (windowing, "hardware_accelerated_scale")
    reg["_toggle_fullscreen"] = (windowing, "toggle_fullscreen")

    return reg


_DELEGATE_REGISTRY: dict[str, tuple[object, str]] = _build_delegate_registry()


class CyberpunkEditorApp:
    """Main app: integrates UIDesigner backend with pixel-art pygame front-end."""

    def __init__(
        self,
        json_path: Path,
        default_size: Tuple[int, int] = (480, 320),
        profile: Optional[str] = None,
    ):
        """Initialize the pygame editor app.

        Args:
            json_path: Path to the scene JSON to load or create.
            default_size: Logical canvas size when no profile is set.
            profile: Optional hardware profile key to preconfigure dimensions.
        """
        self._init_pygame()
        self._init_config(json_path, default_size, profile)
        self._init_window()
        self._init_fonts_and_metrics()
        self._init_state_and_perf()
        self._build_palette()
        self._build_toolbar()
        if self._restored_from_autosave:
            print(f"[INFO] Autosave restored from {self.autosave_path}")

    def _init_pygame(self) -> None:
        """Phase 1: Initialize pygame subsystems and event filtering."""
        pygame.init()
        pygame.font.init()

    def _init_config(
        self,
        json_path: Path,
        default_size: Tuple[int, int],
        profile: Optional[str],
    ) -> None:
        """Phase 2: Designer, hardware profile, env settings, paths."""
        self.json_path = json_path
        self.hardware_profile = profile
        if self.hardware_profile and self.hardware_profile in HARDWARE_PROFILES:
            pinfo = HARDWARE_PROFILES[self.hardware_profile]
            default_size = (pinfo["width"], pinfo["height"])
        self.default_size = default_size
        self.designer = UIDesigner()
        if self.hardware_profile:
            self.designer.set_hardware_profile(self.hardware_profile)
        self.live_preview_port = os.getenv("ESP32OS_LIVE_PORT")
        try:
            self.live_preview_baud = int(os.getenv("ESP32OS_LIVE_BAUD", str(BAUD_DEFAULT)))
        except (ValueError, TypeError):
            self.live_preview_baud = BAUD_DEFAULT
        self.toolbar_h = TOOLBAR_H
        self.scene_tabs_h = SCENE_TABS_H
        self.status_h = STATUS_H
        self.tab_hitboxes = []
        self.scale = SCALE
        self._scale_locked = False
        self.template_library = TemplateLibrary()
        env_autosave = os.getenv("ESP32OS_AUTOSAVE", "0")
        self.autosave_enabled = env_autosave not in ("0", "false", "False", "")
        try:
            self.autosave_interval = float(os.getenv("ESP32OS_AUTOSAVE_SECS", str(AUTOSAVE_SEC)))
        except (ValueError, TypeError):
            self.autosave_interval = AUTOSAVE_SEC
        self._last_autosave_ts: float = time.time()
        self.autosave_path = self.json_path.with_suffix(".autosave.json")
        self._dirty = False
        self._dirty_scenes: set[str] = set()
        self._quit_confirm_ts: float = 0.0
        self._force_full_redraw: bool = False
        self.clean_preview = False
        self._pending_template_widgets: Optional[list] = None
        self._saved_show_grid: bool = True
        self._saved_panels_collapsed: bool = False
        self._restored_from_autosave = False
        self.snap_enabled = True
        self.show_grid = True
        self.show_center_guides = False
        self.show_widget_ids = False
        self.show_z_labels = False
        self.show_rulers = True
        self.prefs: Dict[str, str] = {}
        self.favorite_ports: List[str] = []
        self.available_ports: List[str] = []
        self.available_ports_idx: int = -1
        self.dialog_message: str = ""
        self._load_prefs()
        self.preset_path = Path("user_widget_presets.json")
        self.widget_presets: List[dict] = self._load_widget_presets()
        self.inspector_hitboxes: List[Tuple[pygame.Rect, str]] = []
        self.show_help_overlay: bool = True
        self._help_shown_once: bool = False
        self._help_pinned: bool = False
        self.show_shortcuts_panel: bool = False
        self._default_palette_w = DEFAULT_PALETTE_W
        self._default_inspector_w = DEFAULT_INSPECTOR_W
        self.panels_collapsed = False
        self.fullscreen = False
        self._help_timer_start: float = time.time()
        self._help_timeout_sec: float = 5.0
        self._status_until_ts: float = 0.0
        self.clipboard: List[WidgetConfig] = []
        self.window: Optional[pygame.Surface] = None
        try:
            self.fps_limit = max(0, int(os.getenv("ESP32OS_FPS", str(FPS))))
        except (ValueError, TypeError):
            self.fps_limit = FPS
        try:
            self.max_auto_scale = max(
                1, int(os.getenv("ESP32OS_MAX_SCALE", str(MAX_AUTO_SCALE_DEFAULT)))
            )
        except (ValueError, TypeError):
            self.max_auto_scale = MAX_AUTO_SCALE_DEFAULT
        self.lock_profile_scale = os.getenv("ESP32OS_LOCK_PROFILE_SCALE", "1") not in (
            "0",
            "false",
            "False",
        )
        if not self.hardware_profile and self.prefs.get("profile"):
            self.hardware_profile = self.prefs["profile"]
        else:
            self.prefs["profile"] = self.hardware_profile or ""
        if self.prefs.get("live_port"):
            self.live_preview_port = self.prefs["live_port"]
        if self.prefs.get("live_baud"):
            try:
                self.live_preview_baud = int(self.prefs["live_baud"])
            except (ValueError, TypeError):
                self.live_preview_baud = BAUD_DEFAULT
        if self.live_preview_port and self.live_preview_port not in self.favorite_ports:
            self.favorite_ports.append(self.live_preview_port)
        self._load_or_default()

    def _init_window(self) -> None:
        """Phase 3: Window creation, display config, event queue setup."""
        start_max = os.getenv("ESP32OS_START_MAXIMIZED", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "",
        )
        is_dummy = os.getenv("SDL_VIDEODRIVER", "").strip().lower() == "dummy"
        win_size = None
        if start_max and not is_dummy:  # pragma: no cover — requires real display
            try:
                info = pygame.display.Info()
                scr_w = int(getattr(info, "current_w", 0) or 0)
                scr_h = int(getattr(info, "current_h", 0) or 0)
                if scr_w > 0 and scr_h > 0:
                    margin_w, margin_h = WIN_MARGIN_W, WIN_MARGIN_H
                    win_size = (max(1, scr_w - margin_w), max(1, scr_h - margin_h))
            except (pygame.error, AttributeError, ValueError, TypeError):
                win_size = None
        self.layout: Layout = Layout(1, 1)  # placeholder; overwritten by _rebuild_layout
        self.logical_surface: pygame.Surface = pygame.Surface((1, 1))
        self._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
        pygame.display.set_caption("ESP32OS UI Designer (pygame)")
        pygame.event.set_blocked(None)
        pygame.event.set_allowed(
            [
                pygame.QUIT,
                pygame.VIDEORESIZE,
                pygame.KEYDOWN,
                pygame.KEYUP,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
                pygame.MOUSEWHEEL,
                pygame.TEXTINPUT,
            ]
        )
        self.event_manager = EventManager(monotonic=time.monotonic)
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.fps = 0.0

    def _init_fonts_and_metrics(self) -> None:
        """Phase 4: Pixel-art font loading and row-height calculations."""
        self.pixel_font_size, self.pixel_scale = self._font_settings()
        self.pixel_font = self._load_pixel_font(self.pixel_font_size)
        base_height = self.pixel_font.get_height() * self.pixel_scale
        row_target = max(GRID * 2, base_height + GRID // 2)
        self.pixel_row_height = GRID * max(2, (row_target + GRID - 1) // GRID)
        self.pixel_padding = GRID // 2
        self.pointer_pos: Tuple[int, int] = (-9999, -9999)
        self.pointer_down: bool = False
        self.sim_input_mode: bool = False
        self.focus_idx: Optional[int] = None
        self.focus_edit_value: bool = False
        self.font = self.pixel_font
        self.font_small = self.pixel_font
        self._render_scale_x: float = 1.0
        self._render_scale_y: float = 1.0
        self._render_offset_x: int = 0
        self._render_offset_y: int = 0

    def _init_state_and_perf(self) -> None:
        """Phase 5: Editor state, render cache, FPS tracking."""
        self.state = EditorState(self.designer, self.layout)
        self.running = True
        self.render_cache = RenderCache()
        self.dirty_rects: List[pygame.Rect] = []
        self.target_fps = 60
        self.vsync_enabled = True
        self.auto_optimize = False
        self.fps_history = deque(maxlen=60)
        self.auto_scale_adjust = False
        self.min_acceptable_fps = MIN_FPS

    def __getattr__(self, name: str):
        """Auto-dispatch simple delegates via _DELEGATE_REGISTRY."""
        entry = _DELEGATE_REGISTRY.get(name)
        if entry is not None:
            mod, fn_name = entry
            fn = getattr(mod, fn_name)
            bound = lambda: fn(self)  # noqa: E731
            object.__setattr__(self, name, bound)
            return bound
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    # ------------------------------------------------------------------ #
    # Palette and toolbar builders (called from __init__)
    # ------------------------------------------------------------------ #
    def _build_palette(self) -> None:
        """Construct collapsible palette sections for the left panel."""
        self.palette_sections = [
            (
                "Add Widget",
                [
                    ("Label", lambda: self._add_widget("label")),
                    ("Button", lambda: self._add_widget("button")),
                    ("Panel", lambda: self._add_widget("panel")),
                    ("Progress", lambda: self._add_widget("progressbar")),
                    ("Gauge", lambda: self._add_widget("gauge")),
                    ("Slider", lambda: self._add_widget("slider")),
                    ("Checkbox", lambda: self._add_widget("checkbox")),
                    ("Textbox", lambda: self._add_widget("textbox")),
                    ("Chart", lambda: self._add_widget("chart")),
                    ("List", lambda: self._add_widget("list")),
                    ("Toggle", lambda: self._add_widget("toggle")),
                    ("Icon", lambda: self._add_widget("icon")),
                ],
            ),
            ("Templates", self._build_template_actions()),
            (
                "Colors",
                [
                    ("White / Black", lambda: self._apply_color_preset("#f5f5f5", "#000000")),
                    ("White / Panel", lambda: self._apply_color_preset("#f5f5f5", "#101010")),
                    ("LightGray / Dark", lambda: self._apply_color_preset("#e0e0e0", "#080808")),
                    ("Gray / Dark", lambda: self._apply_color_preset("#b0b0b0", "#080808")),
                ],
            ),
            (
                "Components",
                [
                    ("Dashboard 256x128", lambda: self._add_component("dashboard_256x128")),
                    ("Status Bar", lambda: self._add_component("status_bar")),
                    ("Tabs", lambda: self._add_component("tabs")),
                    ("Menu", lambda: self._add_component("menu")),
                    ("Menu List", lambda: self._add_component("menu_list")),
                    ("List", lambda: self._add_component("list")),
                    ("List Item", lambda: self._add_component("list_item")),
                    ("Setting (int)", lambda: self._add_component("setting_int")),
                    ("Setting (bool)", lambda: self._add_component("setting_bool")),
                    ("Setting (enum)", lambda: self._add_component("setting_enum")),
                    ("Dialog", lambda: self._add_component("dialog")),
                    ("Card", lambda: self._add_component("card")),
                    ("Notification", lambda: self._add_component("notification")),
                    ("Modal", lambda: self._add_component("modal")),
                    ("Chart Bar", lambda: self._add_component("chart_bar")),
                    ("Chart Line", lambda: self._add_component("chart_line")),
                    ("Gauge HUD", lambda: self._add_component("gauge_hud")),
                    ("Dialog Confirm", lambda: self._add_component("dialog_confirm")),
                    ("Toast", lambda: self._add_component("toast")),
                ],
            ),
            (
                "Layout",
                [
                    ("Align Left", lambda: layout_tools.align_selection(self, "left")),
                    ("Align H Center", lambda: layout_tools.align_selection(self, "hcenter")),
                    ("Align Right", lambda: layout_tools.align_selection(self, "right")),
                    ("Align Top", lambda: layout_tools.align_selection(self, "top")),
                    ("Align V Center", lambda: layout_tools.align_selection(self, "vcenter")),
                    ("Align Bottom", lambda: layout_tools.align_selection(self, "bottom")),
                    ("Distribute H", lambda: layout_tools.distribute_selection(self, "h")),
                    ("Distribute V", lambda: layout_tools.distribute_selection(self, "v")),
                    ("Match Width", lambda: layout_tools.match_size_selection(self, "width")),
                    ("Match Height", lambda: layout_tools.match_size_selection(self, "height")),
                    ("Center", lambda: layout_tools.center_selection_in_scene(self, "both")),
                ],
            ),
            (
                "Profiles",
                [
                    ("ESP32 OS 256x128", lambda: self._set_profile("esp32os_256x128_gray4")),
                    ("ESP32 OS 240x128 1b", lambda: self._set_profile("esp32os_240x128_mono")),
                    ("ESP32 OS 240x128 RGB", lambda: self._set_profile("esp32os_240x128_rgb565")),
                    ("OLED 128x64", lambda: self._set_profile("oled_128x64")),
                    ("TFT 320x240", lambda: self._set_profile("tft_320x240")),
                    ("TFT 480x320", lambda: self._set_profile("tft_480x320")),
                ],
            ),
            ("Presets", self._build_widget_presets_actions()),
        ]
        self.palette_collapsed: set = {
            "Templates",
            "Colors",
            "Components",
            "Layout",
            "Profiles",
            "Presets",
        }
        self.inspector_collapsed: set = {"Layers"}
        self.palette_actions = []
        for _sec_name, items in self.palette_sections:
            self.palette_actions += items

    def _build_toolbar(self) -> None:
        """Construct toolbar actions and overflow-warning setting."""
        env_warn = os.getenv("ESP32OS_OVERFLOW_WARN", "").strip().lower()
        if env_warn in {"0", "false", "off", "no"}:
            self.show_overflow_warnings = False
        elif env_warn in {"1", "true", "on", "yes"}:
            self.show_overflow_warnings = True
        else:
            self.show_overflow_warnings = text_metrics.is_device_profile(self.hardware_profile)
        self.toolbar_actions = [
            ("New", self._new_scene),
            ("Load", self.load_json),
            ("Save", self.save_json),
            ("Undo", self._do_undo),
            ("Redo", self._do_redo),
            ("Tpl", self._open_template_menu),
            ("Live", self._open_live_dialog),
            ("Arrange", self._auto_arrange_grid),
            ("Fit Text", self._fit_selection_to_text),
            ("Fit Widget", self._fit_selection_to_widget),
            ("Warn", self._toggle_overflow_warnings),
        ]

    # ------------------------------------------------------------------ #
    # Undo/redo toolbar actions
    # ------------------------------------------------------------------ #
    def _do_undo(self) -> None:
        if self.designer.undo():
            self.state.selected_idx = None
            self.state.selected = []
            self._mark_dirty()
            self._set_status("Undo.", ttl_sec=1.5)
        else:
            self._set_status("Nothing to undo.", ttl_sec=1.5)

    def _do_redo(self) -> None:
        if self.designer.redo():
            self.state.selected_idx = None
            self.state.selected = []
            self._mark_dirty()
            self._set_status("Redo.", ttl_sec=1.5)
        else:
            self._set_status("Nothing to redo.", ttl_sec=1.5)

    def _open_template_menu(self) -> None:
        """Open a context-menu-style template picker below the Tpl button."""
        templates = self.template_library.templates
        if not templates:
            self._set_status("No templates available.", ttl_sec=2.0)
            return
        items: list = []
        for i, tpl in enumerate(templates[:12]):
            items.append((tpl.metadata.name, tpl.metadata.category, f"tpl_{i}"))
        if self.state.selected:
            items.append(("---", "", None))
            items.append(("Save Selection as Template", "", "save_as_template"))
        # Position below toolbar
        pos = (self.layout.toolbar_rect.x + 200, self.layout.toolbar_rect.bottom + 2)
        self._context_menu = {"visible": True, "pos": pos, "items": items}

    # ------------------------------------------------------------------ #
    # Status, inspector, and input helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, message: str, ttl_sec: float = 3.0) -> None:
        """Show a temporary status message for *ttl_sec* seconds."""
        self.dialog_message = str(message or "")
        self._status_until_ts = time.time() + float(ttl_sec)
        self._mark_dirty()

    def _on_text_input(self, text: str) -> None:
        if not self.state.inspector_selected_field:
            return
        if not text:
            return
        self.state.inspector_input_buffer += text
        self._mark_dirty()

    def _inspector_cancel_edit(self) -> None:
        self.state.inspector_selected_field = None
        self.state.inspector_input_buffer = ""
        try:
            pygame.key.stop_text_input()
        except (pygame.error, AttributeError):
            pass
        self._set_status("Edit canceled.", ttl_sec=1.5)

    def _inspector_start_edit(self, field: str) -> None:
        w = self.state.selected_widget()
        if w is None:
            self._set_status("No selection.", ttl_sec=2.0)
            return
        self.state.inspector_selected_field = str(field)
        self.state.inspector_input_buffer = self._inspector_field_to_str(str(field), w)
        try:
            pygame.key.start_text_input()
        except (pygame.error, AttributeError):
            pass
        self._set_status(f"Editing {field} (Enter=apply Esc=cancel)", ttl_sec=4.0)

    def _inspector_field_to_str(self, field: str, w: WidgetConfig) -> str:
        return inspector_field_to_str(self, field, w)

    def _is_valid_color_str(self, value: str) -> bool:
        s = str(value or "").strip().lower()
        if not s:
            return True
        if s in NAMED_COLORS:
            return True
        if s.startswith("#") and len(s) == 7:
            return all(c in "0123456789abcdef" for c in s[1:])
        if s.startswith("0x") and len(s) == 8:
            return all(c in "0123456789abcdef" for c in s[2:])
        return False

    def _inspector_commit_edit(self) -> bool:
        return inspector_commit_edit(self)

    def _open_live_dialog(self) -> None:
        """Send a framed UI JSON to ESP32 (best-effort) using configured port."""
        return live_preview.open_live_dialog(self)

    def _refresh_available_ports(self) -> None:
        """Best-effort serial port discovery (optional: requires pyserial)."""
        live_preview.refresh_available_ports(self)

    def _mark_dirty(self) -> None:
        """Mark the current scene as modified so it gets re-rendered and auto-saved."""
        self._dirty = True
        scene_name = getattr(self.designer, "current_scene", None)
        if scene_name:
            self._dirty_scenes.add(scene_name)

    # ------------------------------------------------------------------ #
    # Templates, presets, and profiles
    # ------------------------------------------------------------------ #
    def _apply_template(self, template: Template):
        scene_ops.apply_template(self, template)

    def _apply_color_preset(self, fg: str, bg: str):
        """Apply fg/bg colors to selected widgets."""
        if not self.state.selected:
            return
        sc = self.state.current_scene()
        safe_save_state(self.designer)
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                w = sc.widgets[idx]
                w.color_fg = fg
                w.color_bg = bg
        self._mark_dirty()

    def _set_profile(self, key: str):
        scene_ops.set_profile(self, key)

    def _apply_color_preset_index(self, index: int):
        """Apply color preset by zero-based index (for keyboard shortcuts)."""
        presets = [
            ("#f5f5f5", "#000000"),
            ("#f5f5f5", "#101010"),
            ("#e0e0e0", "#080808"),
            ("#b0b0b0", "#080808"),
            ("#000000", "#f5f5f5"),
            ("#101010", "#e0e0e0"),
        ]
        if 0 <= index < len(presets):
            fg, bg = presets[index]
            self._apply_color_preset(fg, bg)

    def _build_widget_presets_actions(self):
        actions = []
        actions.append(("-- Widget Presets --", None))
        for slot in range(1, 4):
            actions.append(
                (f"Save preset slot {slot}", lambda slot=slot: self._save_preset_slot(slot))
            )
            actions.append(
                (
                    f"Apply preset slot {slot}",
                    lambda slot=slot: self._apply_preset_slot(slot, add_new=False),
                )
            )
            actions.append(
                (
                    f"Add preset slot {slot}",
                    lambda slot=slot: self._apply_preset_slot(slot, add_new=True),
                )
            )
        return actions

    def _save_preset_slot(self, slot: int):
        """Save current selection as a widget preset into a numbered slot."""
        io_ops.save_preset_slot(self, slot)

    def _apply_preset_slot(self, slot: int, add_new: bool = False):
        """Apply or add preset from slot to selection (or as new widget)."""
        io_ops.apply_preset_slot(self, slot, add_new=add_new)

    # ------------------------------------------------------------------ #
    # File I/O and scene management
    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    # Event handling
    # ------------------------------------------------------------------ #
    @staticmethod
    def _coalesce_motion_and_wheel(events: List[pygame.event.Event]) -> List[pygame.event.Event]:
        """Keep only the latest mouse motion and wheel event per frame to reduce noise."""
        kept: List[pygame.event.Event] = []
        last_motion = None
        last_wheel = None
        for ev in events:
            etype = getattr(ev, "type", None)
            if etype == pygame.MOUSEMOTION:
                last_motion = ev
            elif etype == pygame.MOUSEWHEEL:
                last_wheel = ev
            else:
                kept.append(ev)
        if last_motion:
            kept.append(last_motion)
        if last_wheel:
            kept.append(last_wheel)
        return kept

    @staticmethod
    def _dedupe_keydowns(events: List[pygame.event.Event]) -> List[pygame.event.Event]:
        """Keep only the first KEYDOWN per key in this frame; always keep KEYUP."""
        seen_keys = set()
        filtered: List[pygame.event.Event] = []
        for ev in events:
            etype = getattr(ev, "type", None)
            if etype == pygame.KEYDOWN:
                key = getattr(ev, "key", None)
                # Pygame 2 may expose repeat flag; drop repeats
                if key in seen_keys or getattr(ev, "repeat", False):
                    continue
                seen_keys.add(key)
                filtered.append(ev)
            else:
                filtered.append(ev)
        return filtered

    def _event_priority(self, ev: pygame.event.Event) -> int:
        mapping = {
            pygame.QUIT: 0,
            pygame.VIDEORESIZE: 1,
            pygame.KEYDOWN: 2,
            pygame.KEYUP: 3,
            pygame.MOUSEBUTTONDOWN: 4,
            pygame.MOUSEBUTTONUP: 5,
            pygame.MOUSEWHEEL: 6,
            pygame.MOUSEMOTION: 7,
            pygame.TEXTINPUT: 8,
        }
        return mapping.get(ev.type, 10)

    def _screen_to_logical(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """Convert screen coordinates to logical coordinates."""
        return windowing.screen_to_logical(self, pos[0], pos[1])

    # ------------------------------------------------------------------ #
    # Auto-complete and auto-arrange
    # ------------------------------------------------------------------ #
    def _auto_complete_widget(self, w: WidgetConfig):
        scene_ops.auto_complete_widget(self, w)

    def _find_best_position(self, widget: WidgetConfig, scene) -> Tuple[int, int]:
        return scene_ops.find_best_position(self, widget, scene)

    def run(self):
        """Main loop."""
        while self.running:
            # Dynamic FPS adjustment
            if self.vsync_enabled or self.auto_scale_adjust:
                tick_fps = int(self.target_fps)
            elif self.fps_limit > 0:
                tick_fps = int(self.fps_limit)
            else:
                tick_fps = 0

            self.dt = self.clock.tick(tick_fps) / 1000.0
            self.fps = self.clock.get_fps()
            self.fps_history.append(self.fps)

            # Event handling
            self._handle_events()

            # Update mouse cursor based on pointer region
            self._update_cursor()

            # Auto quality adjustment
            if self.auto_optimize:
                self._auto_adjust_quality()

            self._optimized_draw_frame()

            # Auto-save and maintenance
            self._maybe_hide_help_overlay()
            self._maybe_autosave()

        pygame.quit()
        sys.exit(0)

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def _shade(self, color: Tuple[int, int, int], delta: int) -> Tuple[int, int, int]:
        """Lighten/darken a color channel-wise by delta."""
        return drawing.shade(color, delta)

    def _load_pixel_font(self, size: int) -> pygame.font.Font:
        """Load a readable pixel-ish font with deterministic fallback."""
        return drawing.load_pixel_font(size)

    def _render_pixel_text(
        self,
        text: str,
        color: Tuple[int, int, int],
        shadow: Optional[Tuple[int, int, int]] = None,
        scale: Optional[int] = None,
    ) -> pygame.Surface:
        """Render text WITHOUT upscaling - keep 1:1 for clarity."""
        return drawing.render_pixel_text(self, text, color, shadow=shadow, scale=scale)

    def _draw_pixel_frame(self, rect: pygame.Rect, pressed: bool = False, hover: bool = False):
        """1px pixel-perfect frame with retro highlight/shadow."""
        drawing.draw_pixel_frame(self, rect, pressed=pressed, hover=hover)

    def _draw_pixel_panel_bg(self, rect: pygame.Rect):
        """Fill a panel with subtle 8px grid for pixel-art aesthetic."""
        drawing.draw_pixel_panel_bg(self, rect)

    def _update_cursor(self) -> None:
        """Switch system cursor: crosshair on canvas, default elsewhere."""
        try:
            cr = self.layout.canvas_rect
            on_canvas = cr.collidepoint(self.pointer_pos)
            want = "cross" if on_canvas else "arrow"
            prev = getattr(self, "_cursor_kind", "arrow")
            if want != prev:
                self._cursor_kind = want
                if want == "cross":
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
                else:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except (pygame.error, AttributeError):
            pass

    def _panel(self, rect: pygame.Rect, title: str = ""):
        drawing.panel(self, rect, title=title)

    def _button(self, label: str, pos: Tuple[int, int]) -> pygame.Rect:
        """Render a small pixel-style button and return its rect."""
        return drawing.button(self, label, pos)

    def _value_ratio(self, w: WidgetConfig) -> float:
        try:
            min_v = int(getattr(w, "min_value", 0) or 0)
            max_v = int(getattr(w, "max_value", 100) or 100)
            val = int(getattr(w, "value", 0) or 0)
        except (ValueError, TypeError):
            min_v, max_v, val = 0, 100, 0
        denom = max(1, max_v - min_v)
        return max(0.0, min(1.0, (val - min_v) / denom))

    def _draw_border_style(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        style: str,
        color: Tuple[int, int, int],
    ) -> None:
        drawing.draw_border_style(self, surface, rect, style, color)

    def _draw_bevel_frame(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        base_color: Tuple[int, int, int],
        pressed: bool = False,
    ) -> None:
        drawing.draw_bevel_frame(self, surface, rect, base_color, pressed=pressed)

    def _text_width_px(self, text: str) -> int:
        return drawing.text_width_px(self, text)

    def _ellipsize_text_px(self, text: str, max_width_px: int, ellipsis: str = "...") -> str:
        return drawing.ellipsize_text_px(self, text, max_width_px, ellipsis=ellipsis)

    def _wrap_text_px(
        self, text: str, max_width_px: int, max_lines: int, ellipsis: str = "..."
    ) -> List[str]:
        return drawing.wrap_text_px(self, text, max_width_px, max_lines, ellipsis=ellipsis)

    def _draw_text_clipped(
        self,
        surface: pygame.Surface,
        text: str,
        rect: pygame.Rect,
        fg: Tuple[int, int, int],
        padding: int,
        align: str = "left",
        valign: str = "middle",
        max_lines: int = 1,
        ellipsis: str = "...",
    ) -> None:
        drawing.draw_text_clipped(
            self,
            surface=surface,
            text=text,
            rect=rect,
            fg=fg,
            padding=padding,
            align=align,
            valign=valign,
            max_lines=max_lines,
            ellipsis=ellipsis,
        )

    def _draw_text_in_rect(
        self,
        surface: pygame.Surface,
        text: str,
        rect: pygame.Rect,
        fg: Tuple[int, int, int],
        padding: int,
        w: WidgetConfig,
    ) -> None:
        drawing.draw_text_in_rect(self, surface, text, rect, fg, padding, w)

    def _draw_widget_preview(
        self,
        surface: pygame.Surface,
        w: WidgetConfig,
        rect: pygame.Rect,
        base_bg: Tuple[int, int, int],
        padding: int,
        is_selected: bool,
    ) -> None:
        drawing.draw_widget_preview(self, surface, w, rect, base_bg, padding, is_selected)

    def _toggle_overflow_warnings(self) -> None:
        self.show_overflow_warnings = not bool(getattr(self, "show_overflow_warnings", False))
        self._set_status(
            f"Overflow warnings: {'ON' if self.show_overflow_warnings else 'OFF'}",
            ttl_sec=2.0,
        )

    def _draw_overflow_marker(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        drawing.draw_overflow_marker(self, surface, rect)

    def _compute_inspector_rows(self) -> Tuple[List[Tuple[str, str]], bool, Optional[WidgetConfig]]:
        return compute_inspector_rows(self)

    def _is_pointer_over(self, rect: pygame.Rect) -> bool:
        """Check if pointer is over rect."""
        return rect.collidepoint(self.pointer_pos)

    def _snap_rect(self, rect: pygame.Rect) -> pygame.Rect:
        """Snap rect to grid."""
        rect.x = snap(rect.x)
        rect.y = snap(rect.y)
        rect.width = max(GRID, snap(rect.width))
        rect.height = max(GRID, snap(rect.height))
        return rect

    def _apply_snap(self, value: int) -> int:
        """Apply snap to value."""
        return snap(value) if self.snap_enabled else value

    # ------------------------------------------------------------------ #
    # Selection, groups, and components
    # ------------------------------------------------------------------ #
    def _set_selection(self, indices: List[int], anchor_idx: Optional[int] = None) -> None:
        selection_ops.set_selection(self, indices, anchor_idx=anchor_idx)

    def _groups_for_index(self, idx: int) -> List[str]:
        return groups.groups_for_index(self, idx)

    def _primary_group_for_index(self, idx: int) -> Optional[str]:
        return groups.primary_group_for_index(self, idx)

    def _group_members(self, name: str) -> List[int]:
        return groups.group_members(self, name)

    def _component_info_from_group(self, group_name: str) -> Optional[Tuple[str, str]]:
        return groups.component_info_from_group(group_name)

    def _component_role_index(self, indices: List[int], root_prefix: str) -> Dict[str, int]:
        return groups.component_role_index(self, indices, root_prefix)

    def _component_field_specs(self, component_type: str) -> Dict[str, Tuple[str, str, str]]:
        return component_field_specs(component_type)

    def _format_group_label(self, group_name: str, members: List[int]) -> str:
        return groups.format_group_label(group_name, members)

    def _tri_state(self, values: List[bool]) -> str:
        return groups.tri_state(values)

    def _selection_bounds(self, indices: List[int]) -> Optional[pygame.Rect]:
        return selection_ops.selection_bounds(self, indices)

    def _apply_click_selection(self, hit: int, mods: int) -> None:
        """Apply selection semantics for a clicked widget index."""
        selection_ops.apply_click_selection(self, hit, mods)

    def _move_selection(self, dx: int, dy: int) -> None:
        selection_ops.move_selection(self, dx, dy)

    def _resize_selection_to(self, new_w: int, new_h: int) -> bool:
        """Resize the current selection bounding box, scaling children proportionally."""
        return selection_ops.resize_selection_to(self, new_w, new_h)

    def _fit_selection_to_text(self) -> None:
        fit_text.fit_selection_to_text(self)

    def _fit_selection_to_widget(self) -> None:
        fit_widget.fit_selection_to_widget(self)

    def _next_group_name(self, prefix: str) -> str:
        return groups.next_group_name(self, prefix)

    def _is_widget_focusable(self, w: WidgetConfig) -> bool:
        return focus_nav.is_widget_focusable(w)

    def _focusable_indices(self) -> List[int]:
        return focus_nav.focusable_indices(self.state.current_scene())

    def _set_focus(self, idx: Optional[int], *, sync_selection: bool = True) -> None:
        focus_nav.set_focus(self, idx, sync_selection=sync_selection)

    def _focus_cycle(self, delta: int) -> None:
        focus_nav.focus_cycle(self, delta)

    def _focus_move_direction(self, direction: str) -> None:
        """Move focus based on widget geometry (D-pad style)."""
        focus_nav.focus_move_direction(self, direction)

    def _adjust_focused_value(self, delta: int) -> None:
        focus_nav.adjust_focused_value(self, delta)

    def _palette_content_height(self) -> int:
        """Return scrollable palette content height (excluding the fixed header row)."""
        sc = self.state.current_scene()
        rows = 0
        for sec_name, items in self.palette_sections:
            rows += 1  # section header
            if sec_name not in self.palette_collapsed:
                rows += len(items)
        rows += len(sc.widgets)  # widget list
        gap = max(0, int(getattr(self, "pixel_padding", 0) or 0))
        return int(self.pixel_row_height) * rows + gap

    def _inspector_content_height(self) -> int:
        """Calculate inspector content height accounting for collapsed sections."""
        rows, _, _ = self._compute_inspector_rows()
        collapsed = getattr(self, "inspector_collapsed", set())
        count = 0
        current_section: str | None = None
        for key, _text in rows:
            if key.startswith("_section:"):
                current_section = key[len("_section:") :]
                count += 1  # section header always visible
                continue
            if current_section and current_section in collapsed:
                continue
            count += 1
        return self.pixel_row_height * max(1, count)

    def _font_settings(self) -> Tuple[int, int]:
        """Return (font_size, pixel_scale) with env overrides."""

        def _int_env(name: str, default: int, lo: int, hi: int) -> int:
            try:
                val = int(os.getenv(name, default))
            except (ValueError, TypeError):
                val = default
            return max(lo, min(hi, val))

        size = _int_env("ESP32OS_FONT_SIZE", 10, 5, 24)
        scale = _int_env("ESP32OS_FONT_SCALE", 2, 1, 6)
        return size, scale

    # ------------------------------------------------------------------ #
    # Event dispatch and input handling
    # ------------------------------------------------------------------ #
    def _handle_events(self):
        """Main event pump."""
        raw_events = pygame.event.get()
        events = self._coalesce_motion_and_wheel(raw_events)
        events = self._dedupe_keydowns(events)
        for event in events:
            self.event_manager.post(event, priority=self._event_priority(event))
        self.event_manager.dispatch_all(self._dispatch_event)

    def _dispatch_event(self, event: pygame.event.Event):
        """Dispatch event to handlers."""
        et = event.type
        if et == pygame.QUIT:
            self._handle_quit()
            return
        if et == pygame.VIDEORESIZE:
            windowing.handle_video_resize(self, event.w, event.h)
            return
        if et == pygame.KEYDOWN:
            self._on_key_down(event)
            return
        if et == pygame.MOUSEBUTTONDOWN:
            self._dispatch_mouse_down(event)
            return
        if et == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pointer_down = False
            self.pointer_pos = self._screen_to_logical(event.pos)
            self._on_mouse_up(self.pointer_pos)
            self._mark_dirty()
            return
        if et == pygame.MOUSEMOTION:
            self.pointer_pos = self._screen_to_logical(event.pos)
            self._on_mouse_move(self.pointer_pos, event.buttons)
            self._mark_dirty()
            return
        if et == pygame.MOUSEWHEEL:
            try:
                dx = int(getattr(event, "x", 0))
                dy = int(getattr(event, "y", 0))
            except (ValueError, TypeError):
                dx, dy = 0, 0
            self._on_mouse_wheel(dx, dy)
            self._mark_dirty()
            return
        if et == pygame.TEXTINPUT:
            try:
                text = str(getattr(event, "text", ""))
            except (AttributeError, TypeError):
                text = ""
            self._on_text_input(text)
            self._mark_dirty()
            return

    def _handle_quit(self) -> None:
        """Handle QUIT event with dirty-check confirmation."""
        if self._dirty_scenes and time.time() - self._quit_confirm_ts > 3.0:
            self._quit_confirm_ts = time.time()
            n = len(self._dirty_scenes)
            self._set_status(
                f"Unsaved changes in {n} scene(s). Close again to quit.",
                ttl_sec=3.0,
            )
            return
        self.running = False

    def _dispatch_mouse_down(self, event: pygame.event.Event) -> None:
        """Route MOUSEBUTTONDOWN by button number."""
        if event.button == 3:
            self.pointer_pos = self._screen_to_logical(event.pos)
            lx, ly = self.pointer_pos
            if self.layout.scene_tabs_rect.collidepoint(lx, ly):
                self._open_tab_context_menu(self.pointer_pos)
            else:
                self._open_context_menu(self.pointer_pos)
            self._mark_dirty()
            return
        if event.button == 2:
            self.pointer_pos = self._screen_to_logical(event.pos)
            lx, ly = self.pointer_pos
            if self.layout.scene_tabs_rect.collidepoint(lx, ly):
                for rect, tab_idx, _tab_name in getattr(self, "tab_hitboxes", []):
                    if tab_idx >= 0 and rect.collidepoint(lx, ly):
                        self._jump_to_scene(tab_idx)
                        self._delete_current_scene()
                        self._mark_dirty()
                        return
            return
        if event.button == 1:
            self._handle_left_click(event)
            return

    def _handle_left_click(self, event: pygame.event.Event) -> None:
        """Handle left mouse button click (dismiss menu, double-click, drag)."""
        menu = getattr(self, "_context_menu", None)
        if menu and menu.get("visible"):
            self.pointer_pos = self._screen_to_logical(event.pos)
            self._click_context_menu(self.pointer_pos)
            self._mark_dirty()
            return
        self.pointer_down = True
        self.pointer_pos = self._screen_to_logical(event.pos)
        now = time.time()
        last_click_time = getattr(self, "_last_click_time", 0.0)
        last_click_pos = getattr(self, "_last_click_pos", (-9999, -9999))
        is_double = (
            now - last_click_time < DBLCLICK_SEC
            and abs(self.pointer_pos[0] - last_click_pos[0]) < DBLCLICK_PX
            and abs(self.pointer_pos[1] - last_click_pos[1]) < DBLCLICK_PX
        )
        self._last_click_time = now
        self._last_click_pos = self.pointer_pos
        if is_double and not self.sim_input_mode:
            self._handle_double_click(self.pointer_pos)
            self._mark_dirty()
            return
        self._on_mouse_down(self.pointer_pos)
        self._mark_dirty()

    def _open_tab_context_menu(self, pos: Tuple[int, int]) -> None:
        context_menu.open_tab_context_menu(self, pos)

    def _open_context_menu(self, pos: Tuple[int, int]) -> None:
        context_menu.open_context_menu(self, pos)

    def _ctx_single_items(self, SEP: tuple) -> list:
        return context_menu.ctx_single_items(self, SEP)

    def _ctx_multi_items(self, SEP: tuple) -> list:
        return context_menu.ctx_multi_items(self, SEP)

    def _ctx_add_items(self, SEP: tuple) -> list:
        return context_menu.ctx_add_items(self, SEP)

    def _click_context_menu(self, pos: Tuple[int, int]) -> None:
        context_menu.click_context_menu(self, pos)

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #

    # Action → method-name mapping for context menu dispatch.
    _CONTEXT_ACTION_MAP = context_menu.CONTEXT_ACTION_MAP

    def _execute_context_action(self, action: str) -> None:
        context_menu.execute_context_action(self, action)

    def _on_key_down(self, event: pygame.event.Event):
        # Dismiss context menu on any key press
        menu = getattr(self, "_context_menu", None)
        if menu and menu.get("visible"):
            if event.key == pygame.K_ESCAPE:
                menu["visible"] = False
                self._mark_dirty()
                return
        input_handlers.on_key_down(self, event)

    def _z_order_step(self, delta: int) -> None:
        scene_ops.z_order_step(self, delta)

    def _switch_scene(self, direction: int) -> None:
        scene_ops.switch_scene(self, direction)

    def _handle_double_click(self, pos: Tuple[int, int]) -> None:
        scene_ops.handle_double_click(self, pos)

    def _on_mouse_down(self, pos: Tuple[int, int]) -> None:
        input_handlers.on_mouse_down(self, pos)

    def _on_mouse_up(self, _pos: Tuple[int, int]) -> None:
        input_handlers.on_mouse_up(self, _pos)

    def _on_mouse_move(self, pos: Tuple[int, int], _buttons: Tuple[int, int, int]) -> None:
        input_handlers.on_mouse_move(self, pos, _buttons)

    def _on_mouse_wheel(self, _dx: int, dy: int) -> None:
        input_handlers.on_mouse_wheel(self, _dx, dy)

    # ------------------------------------------------------------------ #
    # Widget operations (delegates to selection_ops)
    # ------------------------------------------------------------------ #
    def _reorder_selection(self, direction: int) -> None:
        selection_ops.reorder_selection(self, direction)

    def _mirror_selection(self, axis: str) -> None:
        selection_ops.mirror_selection(self, axis)

    def _adjust_value(self, delta: int) -> None:
        selection_ops.adjust_value(self, delta)

    def _search_widgets_prompt(self) -> None:
        """Open inline input to search widgets by text/type."""
        self.state.inspector_selected_field = "_search"
        self.state.inspector_input_buffer = ""
        try:
            pygame.key.start_text_input()
        except (pygame.error, AttributeError):
            pass
        self._set_status("Search widgets (Enter=find Esc=cancel)", ttl_sec=4.0)

    def _array_duplicate_prompt(self) -> None:
        """Open inline input for array duplicate (count,dx,dy)."""
        if not self.state.selected:
            self._set_status("Array dup: nothing selected.", ttl_sec=2.0)
            return
        self.state.inspector_selected_field = "_array_dup"
        self.state.inspector_input_buffer = ""
        try:
            pygame.key.start_text_input()
        except (pygame.error, AttributeError):
            pass
        self._set_status("Array dup: count,dx,dy (e.g. 3,16,0) Enter=go", ttl_sec=5.0)

    def _toggle_center_guides(self) -> None:
        self.show_center_guides = not getattr(self, "show_center_guides", False)
        state_str = "ON" if self.show_center_guides else "OFF"
        self._set_status(f"Center guides: {state_str}", ttl_sec=2.0)
        self._mark_dirty()

    def _set_all_spacing_prompt(self) -> None:
        """Open inline input for all spacing (px,py,mx,my)."""
        if not self.state.selected:
            self._set_status("Spacing: nothing selected.", ttl_sec=2.0)
            return
        self.state.inspector_selected_field = "_spacing"
        self.state.inspector_input_buffer = ""
        try:
            pygame.key.start_text_input()
        except (pygame.error, AttributeError):
            pass
        self._set_status("Spacing: px,py,mx,my (e.g. 2,1,0,0) Enter=set", ttl_sec=5.0)

    def _toggle_widget_ids(self) -> None:
        self.show_widget_ids = not self.show_widget_ids
        label = "ON" if self.show_widget_ids else "OFF"
        self._set_status(f"Widget IDs: {label}", ttl_sec=2.0)
        self._mark_dirty()

    def _toggle_z_labels(self) -> None:
        self.show_z_labels = not self.show_z_labels
        label = "ON" if self.show_z_labels else "OFF"
        self._set_status(f"Z-index labels: {label}", ttl_sec=2.0)
        self._mark_dirty()

    def _equalize_gaps(self, axis: str = "auto") -> None:
        selection_ops.equalize_gaps(self, axis)

    # R42 quick-create composites
    # R43 quick-create composites
    # R44 quick-create composites
    # R45 quick-create composites
    # R46 widget manipulation
    # R47
    # R48 batch layout
    def _distribute_columns(self) -> None:
        selection_ops.distribute_columns(self, col_count=2)

    def _match_first_width(self) -> None:
        selection_ops.match_first_width(self)

    # R49 scene alignment
    # R50 scene cleanup
    # R52 batch property
    # ------------------------------------------------------------------ #
    # Scene navigation and management (delegates to scene_ops)
    # ------------------------------------------------------------------ #
    def _jump_to_scene(self, index: int) -> None:
        scene_ops.jump_to_scene(self, index)

    # ------------------------------------------------------------------ #
    # Export, add widget, and utilities (delegates to scene_ops)
    # ------------------------------------------------------------------ #
    def _add_widget(self, kind: str):
        scene_ops.add_widget(self, kind)

    def _add_component(self, name: str):
        component_insert.add_component(self, name)

    def _component_blueprints(self, name: str, sc) -> List[Dict[str, object]]:
        """Backward compatible wrapper for older callers."""
        return component_blueprints(str(name or ""), sc)

    def _toggle_panels(self):
        """Toggle panels visibility."""
        self.panels_collapsed = not self.panels_collapsed
        win_size = None
        try:
            win_size = self.window.get_size() if self.window else None
        except (pygame.error, AttributeError):
            win_size = None
        lock = self.scale if bool(getattr(self, "_scale_locked", False)) else None
        self._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=lock)

    def _reset_zoom(self):
        """Reset zoom."""
        self._set_scale(1)

    def _hex_or_default(self, val: str, default):
        """Convert hex or return default."""
        try:
            return hex_to_rgb(val)
        except ValueError:
            return default

    def _screenshot_canvas(self):
        """Screenshot canvas."""
        reporting.screenshot_canvas(self)

    def _send_live_preview(self):
        """Send live preview."""
        live_preview.send_live_preview(self)

    def _maybe_hide_help_overlay(self):
        """Auto-hide help after timeout."""
        if (
            self._help_shown_once
            or not self.show_help_overlay
            or bool(getattr(self, "_help_pinned", False))
        ):
            return
        now = time.time()
        if now - self._help_timer_start >= self._help_timeout_sec:
            self._set_help_overlay(False)

    def _set_help_overlay(self, visible: bool, *, pinned: bool = False) -> None:
        visible = bool(visible)
        pinned = bool(pinned) if visible else False
        cur_visible = bool(getattr(self, "show_help_overlay", False))
        cur_pinned = bool(getattr(self, "_help_pinned", False))
        if visible == cur_visible and pinned == cur_pinned:
            return
        self.show_help_overlay = visible
        self._help_pinned = pinned
        if visible:
            self._help_timer_start = time.time()
            if pinned:
                self._help_shown_once = True
        else:
            # Once dismissed, never auto-hide again; user can still toggle via F1.
            self._help_shown_once = True
            self._help_pinned = False
        self._force_full_redraw = True
        self._mark_dirty()

    def _toggle_help_overlay(self) -> None:
        if not bool(getattr(self, "show_help_overlay", False)):
            self._set_help_overlay(True, pinned=True)
            return
        if bool(getattr(self, "_help_pinned", False)):
            self._set_help_overlay(False)
        else:
            self._set_help_overlay(True, pinned=True)

    def _compute_scale(self, force_window: Optional[Tuple[int, int]] = None) -> int:
        """Compute scale."""
        return windowing.compute_scale(self, force_window=force_window)

    def _set_scale(self, new_scale: int):
        """Set scale."""
        self._scale_locked = True
        windowing.set_scale(self, new_scale)

    def _recompute_scale_for_window(self, win_w: int, win_h: int):
        """Recompute scale for window."""
        windowing.recompute_scale_for_window(self, win_w, win_h)

    def _rebuild_layout(
        self,
        window_size: Optional[Tuple[int, int]] = None,
        force_scene_size: bool = True,
        lock_scale: Optional[int] = None,
    ):
        """Rebuild UI layout."""
        windowing.rebuild_layout(
            self,
            window_size=window_size,
            force_scene_size=force_scene_size,
            lock_scale=lock_scale,
        )


def main():
    json_path = DEFAULT_JSON
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if not arg.strip():
            print("[FAIL] JSON path cannot be empty or whitespace-only")
            sys.exit(2)
        json_path = Path(arg).resolve()
    app = CyberpunkEditorApp(json_path, (480, 320))
    app.run()


if __name__ == "__main__":  # pragma: no cover
    main()
