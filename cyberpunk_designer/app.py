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
    PALETTE,
    SCALE,
    SCENE_TABS_H,
    STATUS_H,
    TOOLBAR_H,
    WIN_MARGIN_H,
    WIN_MARGIN_W,
    clamp,
    hex_to_rgb,
    safe_save_state,
    snap,
)
from .inspector_logic import compute_inspector_rows, inspector_commit_edit, inspector_field_to_str
from .perf import RenderCache, compute_dirty_rects
from .state import EditorState


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
            self.live_preview_baud = int(
                os.getenv("ESP32OS_LIVE_BAUD", str(BAUD_DEFAULT))
            )
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
            self.autosave_interval = float(
                os.getenv("ESP32OS_AUTOSAVE_SECS", str(AUTOSAVE_SEC))
            )
        except (ValueError, TypeError):
            self.autosave_interval = AUTOSAVE_SEC
        self._last_autosave_ts: float = time.time()
        self.autosave_path = self.json_path.with_suffix(".autosave.json")
        self._dirty = False
        self._dirty_scenes: set[str] = set()
        self._quit_confirm_ts: float = 0.0
        self._force_full_redraw: bool = False
        self.clean_preview = False
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
        self._default_palette_w = DEFAULT_PALETTE_W
        self._default_inspector_w = DEFAULT_INSPECTOR_W
        self.panels_collapsed = False
        self.fullscreen = False
        self._help_timer_start: float = time.time()
        self._help_timeout_sec: float = 5.0
        self._status_until_ts: float = 0.0
        self.clipboard: List[WidgetConfig] = []
        self.window = None
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
            "Templates", "Colors", "Components", "Layout", "Profiles", "Presets",
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
            ("Live", self._open_live_dialog),
            ("Arrange", self._auto_arrange_grid),
            ("Fit Text", self._fit_selection_to_text),
            ("Fit Widget", self._fit_selection_to_widget),
            ("Warn", self._toggle_overflow_warnings),
        ]

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

    def _load_or_default(self):
        io_ops.load_or_default(self)

    # ------------------------------------------------------------------ #
    # Templates, presets, and profiles
    # ------------------------------------------------------------------ #
    def _build_template_actions(self):
        return scene_ops.build_template_actions(self)

    def _apply_template(self, template: Template):
        scene_ops.apply_template(self, template)

    def _apply_first_template(self):
        scene_ops.apply_first_template(self)

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

    def _cycle_profile(self):
        scene_ops.cycle_profile(self)

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

    def _load_widget_presets(self) -> List[dict]:
        return io_ops.load_widget_presets(self)

    def _save_widget_presets(self):
        io_ops.save_widget_presets(self)

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
    def save_json(self):
        io_ops.save_json(self)

    def load_json(self):
        io_ops.load_json(self)

    def _new_scene(self): scene_ops.new_scene(self)

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

    def _smart_dirty_tracking(self):
        """Track only changed regions for optimized rendering."""
        self.dirty_rects = compute_dirty_rects(
            self.layout,
            self.state,
            force_full=bool(getattr(self, "_force_full_redraw", False)),
            show_help=bool(getattr(self, "show_help_overlay", False)),
        )

    def _auto_adjust_quality(self):
        """Automatically adjust quality settings based on performance."""
        if not self.auto_optimize or len(self.fps_history) < 30:
            return

        avg_fps = sum(self.fps_history) / len(self.fps_history)

        if avg_fps < self.min_acceptable_fps:
            # Reduce quality for better performance
            if self.show_grid:
                self.show_grid = False
            elif self.scale > 1:
                self.scale = max(1, self.scale - 1)
            elif not self.panels_collapsed:
                self._toggle_panels()
        elif avg_fps > self.min_acceptable_fps * 2:
            # Can afford higher quality
            if not self.show_grid:
                self.show_grid = True

    def _draw_frame(self) -> None:
        """Public draw entrypoint (simplified for headless tests)."""
        drawing.draw_frame(self)

    def _optimized_draw_frame(self):
        """Highly optimized frame drawing with caching and dirty rect tracking."""
        cache_key = RenderCache.frame_cache_key(
            self.scale,
            self.state.selected_idx,
            self.state.selected,
            self.show_help_overlay,
            self.designer.current_scene,
            len(self.state.current_scene().widgets),
        )
        cached = self.render_cache.get(cache_key)

        if cached and not self._dirty:
            self.window.blit(cached, (0, 0))
            pygame.display.flip()
            return

        # Smart dirty tracking
        self._smart_dirty_tracking()

        # Only redraw dirty regions
        if len(self.dirty_rects) == 1 and self.dirty_rects[0] == self.layout.canvas_rect:
            # Only canvas changed - keep rest from cache
            self._draw_canvas()
        else:
            # Full redraw needed
            self.logical_surface.fill(PALETTE["bg"])
            if self.clean_preview:
                self._draw_canvas()
            else:
                self._draw_toolbar()
                self._draw_scene_tabs()
                self._draw_palette()
                self._draw_canvas()
                self._draw_inspector()
                self._draw_status()

        if self.show_help_overlay:
            drawing.draw_help_overlay(self)

        drawing.draw_context_menu(self)
        drawing.draw_tooltip(self)

        # Apply scaling with hardware acceleration if available
        self._hardware_accelerated_scale()

        # Cache result
        self.render_cache.set(cache_key, self.window.copy())

        # Update display
        if self.vsync_enabled:
            pygame.display.flip()
        else:
            pygame.display.update(self.dirty_rects)
        self._dirty = False
        self._force_full_redraw = False

    def _hardware_accelerated_scale(self):
        """Use hardware acceleration for scaling if available."""
        windowing.hardware_accelerated_scale(self)

    # ------------------------------------------------------------------ #
    # Auto-complete and auto-arrange
    # ------------------------------------------------------------------ #
    def _auto_complete_widget(self, w: WidgetConfig):
        scene_ops.auto_complete_widget(self, w)

    def _intelligent_auto_arrange(self):
        scene_ops.intelligent_auto_arrange(self)

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
        r, g, b = color
        return (clamp(r + delta, 0, 255), clamp(g + delta, 0, 255), clamp(b + delta, 0, 255))

    def _load_pixel_font(self, size: int) -> pygame.font.Font:
        """Load a readable pixel-ish font with deterministic fallback."""
        env_font = os.getenv("ESP32OS_FONT")
        is_headless = os.getenv("SDL_VIDEODRIVER", "").strip().lower() == "dummy" or bool(
            os.getenv("PYTEST_CURRENT_TEST")
        )

        candidates = [env_font] if env_font else []
        # For interactive runs, prefer a familiar monospace font if present.
        # For tests/headless, avoid system fonts to keep metrics consistent across OSes.
        if not is_headless:
            candidates += [
                "consolas",
                "cascadiamono",
                "courier new",
            ]

        for name in candidates:
            try:
                # Allow explicit path override via ESP32OS_FONT
                path = Path(name)
                if path.exists():
                    font = pygame.font.Font(str(path), size)
                    return font
                font_path = pygame.font.match_font(name)
                if font_path:
                    return pygame.font.Font(font_path, size)
            except (OSError, pygame.error):
                continue

        if is_headless:
            try:
                # Pygame bundled default font is available cross-platform and keeps tests stable.
                return pygame.font.Font(None, size)
            except pygame.error:
                pass

        try:
            return pygame.font.SysFont("monospace", size, bold=False)
        except pygame.error:
            try:
                return pygame.font.Font(None, size)
            except pygame.error:
                return pygame.font.Font(pygame.font.get_default_font(), size)

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

    def _draw_toolbar(self):
        drawing.draw_toolbar(self)

    def _draw_scene_tabs(self):
        drawing.draw_scene_tabs(self)

    def _draw_palette(self):
        drawing.draw_palette(self)

    def _draw_canvas(self) -> None:
        """Draw canvas background + widgets."""
        drawing.draw_canvas(self)

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

    def _draw_inspector(self) -> None:
        """Inspector panel with cached hitboxes (click row to edit)."""
        drawing.draw_inspector(self)

    def _draw_status(self) -> None:
        """Status bar with file/selection info."""
        drawing.draw_status(self)

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
        groups: List[str] = []
        try:
            gdict = getattr(self.designer, "groups", {}) or {}
        except (TypeError, AttributeError):
            gdict = {}
        for gname, members in gdict.items():
            try:
                if idx in members:
                    groups.append(str(gname))
            except TypeError:
                continue
        groups.sort()
        return groups

    def _primary_group_for_index(self, idx: int) -> Optional[str]:
        groups = self._groups_for_index(idx)
        return groups[0] if groups else None

    def _group_members(self, name: str) -> List[int]:
        try:
            members = list((getattr(self.designer, "groups", {}) or {}).get(name, []))
        except (TypeError, AttributeError):
            members = []
        sc = self.state.current_scene()
        valid: List[int] = []
        for m in members:
            try:
                i = int(m)
            except (ValueError, TypeError):
                continue
            if 0 <= i < len(sc.widgets):
                valid.append(i)
        return sorted(set(valid))

    def _selected_group_exact(self) -> Optional[str]:
        """Return group name when current selection matches it exactly."""
        if not self.state.selected or self.state.selected_idx is None:
            return None
        gname = self._primary_group_for_index(int(self.state.selected_idx))
        if not gname:
            return None
        members = self._group_members(gname)
        return gname if set(members) == set(self.state.selected) else None

    def _selected_component_group(self) -> Optional[Tuple[str, str, str, List[int]]]:
        """Return (group_name, component_type, root_prefix, members) when selection is inside a component group."""
        if not self.state.selected or self.state.selected_idx is None:
            return None
        try:
            idx = int(self.state.selected_idx)
        except (ValueError, TypeError):
            return None
        selection = [int(i) for i in (self.state.selected or [])]
        for gname in self._groups_for_index(idx):
            info = self._component_info_from_group(gname)
            if not info:
                continue
            comp_type, root = info
            members = self._group_members(gname)
            if all(i in members for i in selection):
                return str(gname), str(comp_type), str(root), members
        return None

    def _component_info_from_group(self, group_name: str) -> Optional[Tuple[str, str]]:
        g = str(group_name or "")
        if not g.startswith("comp:"):
            return None
        parts = g.split(":")
        # New scheme: comp:{type}:{root}:{n}
        if len(parts) >= 4 and parts[1] and parts[2]:
            return str(parts[1]), str(parts[2])
        # Legacy: comp:{type}:{n} (root == type)
        if len(parts) >= 3 and parts[1]:
            return str(parts[1]), str(parts[1])
        return None

    def _component_role_index(self, indices: List[int], root_prefix: str) -> Dict[str, int]:
        """Map component role -> widget index within selection."""
        sc = self.state.current_scene()
        roles: Dict[str, int] = {}
        prefix = f"{root_prefix or ''!s}."
        if prefix == ".":
            return roles
        for idx in indices:
            if not (0 <= idx < len(sc.widgets)):
                continue
            wid = str(getattr(sc.widgets[idx], "_widget_id", "") or "")
            if not wid.startswith(prefix):
                continue
            role = wid[len(prefix) :].strip()
            if role and role not in roles:
                roles[role] = idx
        return roles

    def _component_field_specs(self, component_type: str) -> Dict[str, Tuple[str, str, str]]:
        """Define editable component-level fields for the inspector."""
        return component_field_specs(component_type)

    def _format_group_label(self, group_name: str, members: List[int]) -> str:
        info = self._component_info_from_group(group_name)
        if info:
            comp_type, root = info
            if root and root != comp_type:
                return f"component: {comp_type} ({root}) ({len(members)})"
            return f"component: {comp_type} ({len(members)})"
        return f"group: {group_name} ({len(members)})"

    def _tri_state(self, values: List[bool]) -> str:
        if not values:
            return "off"
        if all(values):
            return "on"
        if not any(values):
            return "off"
        return "mixed"

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
        try:
            existing = set((getattr(self.designer, "groups", {}) or {}).keys())
        except (AttributeError, TypeError):
            existing = set()
        n = 1
        while f"{prefix}{n}" in existing:
            n += 1
        return f"{prefix}{n}"

    def _group_selection(self) -> None:
        if len(self.state.selected) < 2:
            self._set_status("Group: select 2+ widgets (Ctrl+Click).", ttl_sec=3.0)
            return
        name = self._next_group_name("group")
        try:
            ok = bool(self.designer.create_group(name, list(self.state.selected)))
        except (TypeError, ValueError, KeyError):
            ok = False
        if ok:
            self._set_status(f"Grouped as {name}.", ttl_sec=3.0)
        else:
            self._set_status("Group failed.", ttl_sec=3.0)

    def _ungroup_selection(self) -> None:
        if not self.state.selected:
            return
        target: List[str] = []
        if self.state.selected_idx is not None:
            gname = self._primary_group_for_index(int(self.state.selected_idx))
            if gname:
                target = [gname]
        if not target:
            sel = set(self.state.selected)
            try:
                gdict = getattr(self.designer, "groups", {}) or {}
            except (TypeError, AttributeError):
                gdict = {}
            for gname, members in gdict.items():
                try:
                    if sel.intersection(set(members)):
                        target.append(str(gname))
                except TypeError:
                    continue
        if not target:
            self._set_status("Ungroup: no group.", ttl_sec=2.0)
            return
        removed = 0
        for gname in sorted(set(target)):
            try:
                if self.designer.delete_group(gname):
                    removed += 1
            except (TypeError, ValueError, KeyError):
                continue
        self._set_status(f"Ungrouped {removed} group(s).", ttl_sec=3.0)

    def _is_widget_focusable(self, w: WidgetConfig) -> bool:
        return focus_nav.is_widget_focusable(w)

    def _focusable_indices(self) -> List[int]:
        return focus_nav.focusable_indices(self.state.current_scene())

    def _set_focus(self, idx: Optional[int], *, sync_selection: bool = True) -> None:
        focus_nav.set_focus(self, idx, sync_selection=sync_selection)

    def _ensure_focus(self) -> None:
        focus_nav.ensure_focus(self)

    def _focus_cycle(self, delta: int) -> None:
        focus_nav.focus_cycle(self, delta)

    def _focus_move_direction(self, direction: str) -> None:
        """Move focus based on widget geometry (D-pad style)."""
        focus_nav.focus_move_direction(self, direction)

    def _adjust_focused_value(self, delta: int) -> None:
        focus_nav.adjust_focused_value(self, delta)

    def _activate_focused(self) -> None:
        """Simulate device 'OK/press' on the focused widget."""
        focus_nav.activate_focused(self)

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

    def _load_prefs(self):
        """Load preferences from file."""
        io_ops.load_prefs(self)

    def _save_prefs(self):
        """Save preferences to file."""
        io_ops.save_prefs(self)

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

    def _ctx_view_items(self) -> list:
        return context_menu.ctx_view_items(self)

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

    def _z_order_bring_to_front(self) -> None:
        scene_ops.z_order_bring_to_front(self)

    def _z_order_send_to_back(self) -> None:
        scene_ops.z_order_send_to_back(self)

    def _toggle_lock_selection(self) -> None:
        scene_ops.toggle_lock_selection(self)

    def _zoom_to_fit(self) -> None:
        scene_ops.zoom_to_fit(self)

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
    def _delete_selected(self):
        """Delete selected widgets."""
        selection_ops.delete_selected(self)

    def _copy_selection(self) -> None:
        selection_ops.copy_selection(self)

    def _paste_clipboard(self) -> None:
        selection_ops.paste_clipboard(self)

    def _cut_selection(self) -> None:
        selection_ops.cut_selection(self)

    def _duplicate_selection(self) -> None:
        selection_ops.duplicate_selection(self)

    def _select_all(self) -> None:
        selection_ops.select_all(self)

    def _reorder_selection(self, direction: int) -> None:
        selection_ops.reorder_selection(self, direction)

    def _cycle_style(self) -> None:
        selection_ops.cycle_style(self)

    def _toggle_visibility(self) -> None:
        selection_ops.toggle_visibility(self)

    def _cycle_widget_type(self) -> None:
        selection_ops.cycle_widget_type(self)

    def _cycle_border_style(self) -> None:
        selection_ops.cycle_border_style(self)

    def _copy_style(self) -> None:
        selection_ops.copy_style(self)

    def _paste_style(self) -> None:
        selection_ops.paste_style(self)

    def _arrange_in_row(self) -> None:
        selection_ops.arrange_in_row(self)

    def _arrange_in_column(self) -> None:
        selection_ops.arrange_in_column(self)

    def _cycle_color_preset(self) -> None:
        selection_ops.cycle_color_preset(self)

    def _toggle_border(self) -> None:
        selection_ops.toggle_border(self)

    def _cycle_text_overflow(self) -> None:
        selection_ops.cycle_text_overflow(self)

    def _cycle_align(self) -> None:
        selection_ops.cycle_align(self)

    def _cycle_valign(self) -> None:
        selection_ops.cycle_valign(self)

    def _mirror_selection(self, axis: str) -> None:
        selection_ops.mirror_selection(self, axis)

    def _smart_edit(self) -> None:
        selection_ops.smart_edit(self)

    def _adjust_value(self, delta: int) -> None:
        selection_ops.adjust_value(self, delta)

    def _toggle_enabled(self) -> None:
        selection_ops.toggle_enabled(self)

    def _swap_fg_bg(self) -> None:
        selection_ops.swap_fg_bg(self)

    def _search_widgets_prompt(self) -> None:
        """Open inline input to search widgets by text/type."""
        self.state.inspector_selected_field = "_search"
        self.state.inspector_input_buffer = ""
        try:
            pygame.key.start_text_input()
        except (pygame.error, AttributeError):
            pass
        self._set_status("Search widgets (Enter=find Esc=cancel)", ttl_sec=4.0)

    def _select_same_type(self) -> None:
        selection_ops.select_same_type(self)

    def _toggle_checked(self) -> None:
        selection_ops.toggle_checked(self)

    def _reset_to_defaults(self) -> None:
        selection_ops.reset_to_defaults(self)

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

    def _select_locked(self) -> None:
        selection_ops.select_locked(self)

    def _select_overflow(self) -> None:
        selection_ops.select_overflow(self)

    def _toggle_center_guides(self) -> None:
        self.show_center_guides = not getattr(self, "show_center_guides", False)
        state_str = "ON" if self.show_center_guides else "OFF"
        self._set_status(f"Center guides: {state_str}", ttl_sec=2.0)
        self._mark_dirty()

    def _make_full_width(self) -> None:
        selection_ops.make_full_width(self)

    def _make_full_height(self) -> None:
        selection_ops.make_full_height(self)

    def _swap_dimensions(self) -> None:
        selection_ops.swap_dimensions(self)

    def _select_same_z(self) -> None:
        selection_ops.select_same_z(self)

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

    def _select_same_style(self) -> None:
        selection_ops.select_same_style(self)

    def _select_hidden(self) -> None:
        selection_ops.select_hidden(self)

    def _widget_info(self) -> None:
        selection_ops.widget_info(self)

    def _invert_selection(self) -> None:
        selection_ops.invert_selection(self)

    def _auto_rename(self) -> None:
        selection_ops.auto_rename(self)

    def _select_same_color(self) -> None:
        selection_ops.select_same_color(self)

    def _scene_stats(self) -> None:
        selection_ops.scene_stats(self)

    def _select_parent_panel(self) -> None:
        selection_ops.select_parent_panel(self)

    def _select_children(self) -> None:
        selection_ops.select_children(self)

    def _copy_to_next_scene(self) -> None:
        selection_ops.copy_to_next_scene(self)

    def _snap_selection_to_grid(self) -> None:
        selection_ops.snap_selection_to_grid(self)

    def _paste_in_place(self) -> None:
        selection_ops.paste_in_place(self)

    def _broadcast_to_all_scenes(self) -> None:
        selection_ops.broadcast_to_all_scenes(self)

    def _select_same_size(self) -> None:
        selection_ops.select_same_size(self)

    def _clear_margins(self) -> None:
        selection_ops.clear_margins(self)

    def _hide_unselected(self) -> None:
        selection_ops.hide_unselected(self)

    def _select_bordered(self) -> None:
        selection_ops.select_bordered(self)

    def _move_selection_to_origin(self) -> None:
        selection_ops.move_selection_to_origin(self)

    def _fit_scene_to_content(self) -> None:
        selection_ops.fit_scene_to_content(self)

    def _show_all_widgets(self) -> None:
        selection_ops.show_all_widgets(self)

    def _unlock_all_widgets(self) -> None:
        selection_ops.unlock_all_widgets(self)

    def _select_overlapping(self) -> None:
        selection_ops.select_overlapping(self)

    def _toggle_all_borders(self) -> None:
        selection_ops.toggle_all_borders(self)

    def _remove_degenerate_widgets(self) -> None:
        selection_ops.remove_degenerate_widgets(self)

    def _enable_all_widgets(self) -> None:
        selection_ops.enable_all_widgets(self)

    def _sort_widgets_by_position(self) -> None:
        selection_ops.sort_widgets_by_position(self)

    def _compact_widgets(self) -> None:
        selection_ops.compact_widgets(self)

    def _snap_sizes_to_grid(self) -> None:
        selection_ops.snap_sizes_to_grid(self)

    def _select_all_panels(self) -> None:
        selection_ops.select_all_panels(self)

    def _quick_clone(self) -> None:
        selection_ops.quick_clone(self)

    def _list_templates(self) -> None:
        selection_ops.list_templates(self)

    def _extract_to_new_scene(self) -> None:
        selection_ops.extract_to_new_scene(self)

    def _clear_padding(self) -> None:
        selection_ops.clear_padding(self)

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

    def _flatten_z_indices(self) -> None:
        selection_ops.flatten_z_indices(self)

    def _stack_vertical(self) -> None:
        selection_ops.stack_vertical(self)

    def _stack_horizontal(self) -> None:
        selection_ops.stack_horizontal(self)

    def _equalize_widths(self) -> None:
        selection_ops.equalize_widths(self)

    def _equalize_heights(self) -> None:
        selection_ops.equalize_heights(self)

    def _swap_positions(self) -> None:
        selection_ops.swap_positions(self)

    def _center_in_scene(self) -> None:
        selection_ops.center_in_scene(self)

    def _duplicate_below(self) -> None:
        selection_ops.duplicate_below(self)

    def _duplicate_right(self) -> None:
        selection_ops.duplicate_right(self)

    def _cycle_gray_fg(self) -> None:
        selection_ops.cycle_gray_fg(self)

    def _cycle_gray_bg(self) -> None:
        selection_ops.cycle_gray_bg(self)

    def _equalize_gaps(self, axis: str = "auto") -> None:
        selection_ops.equalize_gaps(self, axis)

    def _grid_arrange(self) -> None:
        selection_ops.grid_arrange(self)

    def _reverse_widget_order(self) -> None:
        selection_ops.reverse_widget_order(self)

    def _flip_vertical(self) -> None:
        selection_ops.flip_vertical(self)

    def _normalize_sizes(self) -> None:
        selection_ops.normalize_sizes(self)

    def _auto_name_scene(self) -> None:
        selection_ops.auto_name_scene(self)

    def _propagate_border(self) -> None:
        selection_ops.propagate_border(self)

    def _remove_duplicates(self) -> None:
        selection_ops.remove_duplicates(self)

    def _increment_text(self) -> None:
        selection_ops.increment_text(self)

    def _propagate_style(self) -> None:
        selection_ops.propagate_style(self)

    def _swap_content(self) -> None:
        selection_ops.swap_content(self)

    def _outline_mode(self) -> None:
        selection_ops.outline_mode(self)

    def _clone_text(self) -> None:
        selection_ops.clone_text(self)

    def _propagate_align(self) -> None:
        selection_ops.propagate_align(self)

    def _propagate_colors(self) -> None:
        selection_ops.propagate_colors(self)

    def _flip_horizontal(self) -> None:
        selection_ops.flip_horizontal(self)

    def _propagate_value(self) -> None:
        selection_ops.propagate_value(self)

    def _propagate_padding(self) -> None:
        selection_ops.propagate_padding(self)

    def _propagate_margin(self) -> None:
        selection_ops.propagate_margin(self)

    def _propagate_appearance(self) -> None:
        selection_ops.propagate_appearance(self)

    def _auto_flow_layout(self) -> None:
        selection_ops.auto_flow_layout(self)

    def _measure_selection(self) -> None:
        selection_ops.measure_selection(self)

    def _space_evenly_h(self) -> None:
        selection_ops.space_evenly_h(self)

    def _space_evenly_v(self) -> None:
        selection_ops.space_evenly_v(self)

    def _replace_text_in_scene(self) -> None:
        selection_ops.replace_text_in_scene(self)

    def _select_same_type_as_current(self) -> None:
        selection_ops.select_same_type_as_current(self)

    def _zoom_to_selection(self) -> None:
        selection_ops.zoom_to_selection(self)

    def _scene_overview(self) -> None:
        selection_ops.scene_overview(self)

    def _widget_type_summary(self) -> None:
        selection_ops.widget_type_summary(self)

    def _toggle_focus_order_overlay(self) -> None:
        selection_ops.toggle_focus_order_overlay(self)

    def _export_selection_json(self) -> None:
        selection_ops.export_selection_json(self)

    # R42 quick-create composites
    def _create_header_bar(self) -> None:
        selection_ops.create_header_bar(self)

    def _create_nav_row(self) -> None:
        selection_ops.create_nav_row(self)

    def _create_form_pair(self) -> None:
        selection_ops.create_form_pair(self)

    # R43 quick-create composites
    def _create_status_bar(self) -> None:
        selection_ops.create_status_bar(self)

    def _create_toggle_group(self) -> None:
        selection_ops.create_toggle_group(self)

    def _create_slider_with_label(self) -> None:
        selection_ops.create_slider_with_label(self)

    # R44 quick-create composites
    def _create_gauge_panel(self) -> None:
        selection_ops.create_gauge_panel(self)

    def _create_progress_section(self) -> None:
        selection_ops.create_progress_section(self)

    def _create_icon_button_row(self) -> None:
        selection_ops.create_icon_button_row(self)

    # R45 quick-create composites
    def _create_card_layout(self) -> None:
        selection_ops.create_card_layout(self)

    def _create_dashboard_grid(self) -> None:
        selection_ops.create_dashboard_grid(self)

    def _create_split_layout(self) -> None:
        selection_ops.create_split_layout(self)

    # R46 widget manipulation
    def _wrap_in_panel(self) -> None:
        selection_ops.wrap_in_panel(self)

    def _fill_scene(self) -> None:
        selection_ops.fill_scene(self)

    def _shrink_to_content(self) -> None:
        selection_ops.shrink_to_content(self)

    # R47
    def _auto_label_widgets(self) -> None:
        selection_ops.auto_label_widgets(self)

    # R48 batch layout
    def _distribute_columns(self) -> None:
        selection_ops.distribute_columns(self, col_count=2)

    def _inset_widgets(self) -> None:
        selection_ops.inset_widgets(self)

    def _outset_widgets(self) -> None:
        selection_ops.outset_widgets(self)

    # R49 scene alignment
    def _align_to_scene_top(self) -> None:
        selection_ops.align_to_scene_top(self)

    def _align_to_scene_bottom(self) -> None:
        selection_ops.align_to_scene_bottom(self)

    def _align_to_scene_left(self) -> None:
        selection_ops.align_to_scene_left(self)

    def _align_to_scene_right(self) -> None:
        selection_ops.align_to_scene_right(self)

    def _center_horizontal(self) -> None:
        selection_ops.center_horizontal(self)

    def _center_vertical(self) -> None:
        selection_ops.center_vertical(self)

    # R50 scene cleanup
    def _delete_hidden_widgets(self) -> None:
        selection_ops.delete_hidden_widgets(self)

    def _delete_offscreen_widgets(self) -> None:
        selection_ops.delete_offscreen_widgets(self)

    def _tile_fill_scene(self) -> None:
        selection_ops.tile_fill_scene(self)

        # R51 transform helpers\n    def _match_first_width(self) -> None:
        selection_ops.match_first_width(self)

    def _match_first_height(self) -> None:
        selection_ops.match_first_height(self)

    def _scatter_random(self) -> None:
        selection_ops.scatter_random(self)

    # R52 batch property
    def _toggle_all_checked(self) -> None:
        selection_ops.toggle_all_checked(self)

    def _reset_all_values(self) -> None:
        selection_ops.reset_all_values(self)

    def _propagate_text(self) -> None:
        selection_ops.propagate_text(self)

    def _flatten_z_index(self) -> None:
        selection_ops.flatten_z_index(self)

    def _number_widget_ids(self) -> None:
        selection_ops.number_widget_ids(self)

    def _z_by_position(self) -> None:
        selection_ops.z_by_position(self)

    def _clone_to_grid(self) -> None:
        selection_ops.clone_to_grid(self)

    def _distribute_rows(self) -> None:
        selection_ops.distribute_rows(self)

    def _mirror_scene_horizontal(self) -> None:
        selection_ops.mirror_scene_horizontal(self)

    def _sort_widgets_by_z(self) -> None:
        selection_ops.sort_widgets_by_z(self)

    def _clamp_to_scene(self) -> None:
        selection_ops.clamp_to_scene(self)

    def _mirror_scene_vertical(self) -> None:
        selection_ops.mirror_scene_vertical(self)

    def _select_unlocked(self) -> None:
        selection_ops.select_unlocked(self)

    def _snap_all_to_grid(self) -> None:
        selection_ops.snap_all_to_grid(self)

    def _select_disabled(self) -> None:
        selection_ops.select_disabled(self)

    def _center_in_parent(self) -> None:
        selection_ops.center_in_parent(self)

    def _size_to_text(self) -> None:
        selection_ops.size_to_text(self)

    def _pack_left(self) -> None:
        selection_ops.pack_left(self)

    def _pack_top(self) -> None:
        selection_ops.pack_top(self)

    def _fill_parent(self) -> None:
        selection_ops.fill_parent(self)

    def _clear_all_text(self) -> None:
        selection_ops.clear_all_text(self)

    def _move_to_origin(self) -> None:
        selection_ops.move_to_origin(self)

    def _make_square(self) -> None:
        selection_ops.make_square(self)

    def _scale_up(self) -> None:
        selection_ops.scale_up(self)

    def _scale_down(self) -> None:
        selection_ops.scale_down(self)

    def _number_text(self) -> None:
        selection_ops.number_text(self)

    def _spread_values(self) -> None:
        selection_ops.spread_values(self)

    def _reset_padding(self) -> None:
        selection_ops.reset_padding(self)

    def _reset_colors(self) -> None:
        selection_ops.reset_colors(self)

    def _outline_only(self) -> None:
        selection_ops.outline_only(self)

    def _select_largest(self) -> None:
        selection_ops.select_largest(self)

    def _select_smallest(self) -> None:
        selection_ops.select_smallest(self)

    def _cascade_arrange(self) -> None:
        selection_ops.cascade_arrange(self)

    def _set_inverse_style(self) -> None:
        selection_ops.set_inverse_style(self)

    def _set_bold_style(self) -> None:
        selection_ops.set_bold_style(self)

    def _set_default_style(self) -> None:
        selection_ops.set_default_style(self)

    def _align_h_centers(self) -> None:
        selection_ops.align_h_centers(self)

    def _align_v_centers(self) -> None:
        selection_ops.align_v_centers(self)

    def _align_left_edges(self) -> None:
        selection_ops.align_left_edges(self)

    def _align_top_edges(self) -> None:
        selection_ops.align_top_edges(self)

    def _align_right_edges(self) -> None:
        selection_ops.align_right_edges(self)

    def _align_bottom_edges(self) -> None:
        selection_ops.align_bottom_edges(self)

    def _distribute_columns_3(self) -> None:
        selection_ops.distribute_columns_3(self)

    # ------------------------------------------------------------------ #
    # Scene navigation and management (delegates to scene_ops)
    # ------------------------------------------------------------------ #
    def _jump_to_scene(self, index: int) -> None: scene_ops.jump_to_scene(self, index)
    def _save_selection_as_template(self) -> None: scene_ops.save_selection_as_template(self)
    def _delete_current_scene(self) -> None: scene_ops.delete_current_scene(self)
    def _close_other_scenes(self) -> None: scene_ops.close_other_scenes(self)
    def _close_scenes_to_right(self) -> None: scene_ops.close_scenes_to_right(self)
    def _add_new_scene(self) -> None: scene_ops.add_new_scene(self)
    def _duplicate_current_scene(self) -> None: scene_ops.duplicate_current_scene(self)
    def _rename_current_scene(self) -> None: scene_ops.rename_current_scene(self)

    # ------------------------------------------------------------------ #
    # Export, add widget, and utilities (delegates to scene_ops)
    # ------------------------------------------------------------------ #
    def _export_c_header(self) -> None: scene_ops.export_c_header(self)
    def _add_widget(self, kind: str): scene_ops.add_widget(self, kind)

    def _add_component(self, name: str):
        component_insert.add_component(self, name)

    def _component_blueprints(self, name: str, sc) -> List[Dict[str, object]]:
        """Backward compatible wrapper for older callers."""
        return component_blueprints(str(name or ""), sc)

    def _auto_arrange_grid(self): scene_ops.auto_arrange_grid(self)
    def _toggle_clean_preview(self) -> None: scene_ops.toggle_clean_preview(self)
    def _goto_widget_prompt(self) -> None: scene_ops.goto_widget_prompt(self)

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

    def _toggle_fullscreen(self):
        """Toggle fullscreen."""
        windowing.toggle_fullscreen(self)

    def _screenshot_canvas(self):
        """Screenshot canvas."""
        reporting.screenshot_canvas(self)

    def _send_live_preview(self):
        """Send live preview."""
        live_preview.send_live_preview(self)

    def _write_audit_report(self):
        """Write audit report."""
        io_ops.write_audit_report(self)

    def _maybe_autosave(self):
        """Auto-save if dirty and enabled."""
        io_ops.maybe_autosave(self)

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
