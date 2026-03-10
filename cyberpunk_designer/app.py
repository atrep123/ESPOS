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
from ui_models import SceneConfig
from ui_template_manager import Template, TemplateLibrary

from . import (
    component_insert,
    drawing,
    fit_text,
    fit_widget,
    focus_nav,
    input_handlers,
    io_ops,
    layout_tools,
    live_preview,
    reporting,
    selection_ops,
    text_metrics,
    windowing,
)
from .component_fields import component_field_specs
from .components import component_blueprints
from .constants import (
    _NAMED_COLORS,
    DEFAULT_JSON,
    FPS,
    GRID,
    PALETTE,
    PROFILE_ORDER,
    SCALE,
    hex_to_rgb,
    snap,
)
from .inspector_logic import compute_inspector_rows, inspector_commit_edit, inspector_field_to_str
from .perf import RenderCache
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
        pygame.init()
        pygame.font.init()
        self.json_path = json_path
        self.hardware_profile = profile
        # Apply hardware profile to default canvas if provided
        if self.hardware_profile and self.hardware_profile in HARDWARE_PROFILES:
            pinfo = HARDWARE_PROFILES[self.hardware_profile]
            default_size = (pinfo["width"], pinfo["height"])
        self.default_size = default_size
        self.designer = UIDesigner()
        if self.hardware_profile:
            self.designer.set_hardware_profile(self.hardware_profile)
        self.live_preview_port = os.getenv("ESP32OS_LIVE_PORT")
        try:
            self.live_preview_baud = int(os.getenv("ESP32OS_LIVE_BAUD", "115200"))
        except Exception:
            self.live_preview_baud = 115200
        self.toolbar_h = 24
        self.scene_tabs_h = 14
        self.status_h = 18
        self.tab_hitboxes = []
        self.scale = SCALE
        self._scale_locked = False
        self.template_library = TemplateLibrary()
        # Autosave settings (off by default to avoid overwriting originals)
        env_autosave = os.getenv("ESP32OS_AUTOSAVE", "0")
        self.autosave_enabled = env_autosave not in ("0", "false", "False", "")
        try:
            self.autosave_interval = float(os.getenv("ESP32OS_AUTOSAVE_SECS", "10.0"))
        except Exception:
            self.autosave_interval = 10.0  # seconds
        self._last_autosave_ts: float = time.time()
        # Autosave vedle zdrojového souboru, ne do temp
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
        # Preferences / live preview (persisted in PREFS_PATH via io_ops)
        self.prefs: Dict[str, str] = {}
        self.favorite_ports: List[str] = []
        self.available_ports: List[str] = []
        self.available_ports_idx: int = -1
        self.dialog_message: str = ""
        self._load_prefs()

        # User widget presets
        self.preset_path = Path("user_widget_presets.json")
        self.widget_presets: List[dict] = self._load_widget_presets()

        self.inspector_hitboxes: List[Tuple[pygame.Rect, str]] = []
        self.show_help_overlay: bool = True  # show once on start
        self._help_shown_once: bool = False
        self._help_pinned: bool = False
        self._default_palette_w = 120
        self._default_inspector_w = 200
        self.panels_collapsed = False
        self.fullscreen = False
        self._help_timer_start: float = time.time()
        self._help_timeout_sec: float = 5.0
        self._status_until_ts: float = 0.0
        self.clipboard: List[WidgetConfig] = []
        self.window = None  # Initialize window attribute
        try:
            self.fps_limit = max(0, int(os.getenv("ESP32OS_FPS", str(FPS))))
        except Exception:
            self.fps_limit = FPS
        try:
            self.max_auto_scale = max(1, int(os.getenv("ESP32OS_MAX_SCALE", "4")))
        except Exception:
            self.max_auto_scale = 4
        # Keep UI scale when switching HW profile (can disable via env)
        self.lock_profile_scale = os.getenv("ESP32OS_LOCK_PROFILE_SCALE", "1") not in (
            "0",
            "false",
            "False",
        )
        # Apply prefs if CLI profile not provided
        if not self.hardware_profile and self.prefs.get("profile"):
            self.hardware_profile = self.prefs["profile"]
        else:
            self.prefs["profile"] = self.hardware_profile or ""
        if self.prefs.get("live_port"):
            self.live_preview_port = self.prefs["live_port"]
        if self.prefs.get("live_baud"):
            try:
                self.live_preview_baud = int(self.prefs["live_baud"])
            except Exception:
                self.live_preview_baud = 115200
        # Seed favorites if empty
        if self.live_preview_port and self.live_preview_port not in self.favorite_ports:
            self.favorite_ports.append(self.live_preview_port)
        self._load_or_default()
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
                    # Leave room for OS chrome/taskbar; sizing is best-effort.
                    margin_w, margin_h = 24, 64
                    win_size = (max(1, scr_w - margin_w), max(1, scr_h - margin_h))
            except Exception:
                win_size = None
        self._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
        pygame.display.set_caption("ESP32OS UI Designer (pygame)")
        # Restrict event queue to relevant types to reduce overhead
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
        # Pixel-art styling helpers
        self.pixel_font_size, self.pixel_scale = self._font_settings()
        self.pixel_font = self._load_pixel_font(self.pixel_font_size)
        base_height = self.pixel_font.get_height() * self.pixel_scale
        row_target = max(GRID * 2, base_height + GRID // 2)
        # Keep row height aligned to GRID to avoid snapping shrinking the hitbox.
        self.pixel_row_height = GRID * max(2, (row_target + GRID - 1) // GRID)
        self.pixel_padding = GRID // 2
        self.pointer_pos: Tuple[int, int] = (-9999, -9999)
        self.pointer_down: bool = False
        # Device input simulation (focus-first UI for buttons/encoder)
        self.sim_input_mode: bool = False
        self.focus_idx: Optional[int] = None
        self.focus_edit_value: bool = False
        self.font = self.pixel_font
        self.font_small = self.pixel_font
        # Render scale/offets (for centering + logical mouse coords)
        self._render_scale_x: float = 1.0
        self._render_scale_y: float = 1.0
        self._render_offset_x: int = 0
        self._render_offset_y: int = 0
        self.state = EditorState(self.designer, self.layout)
        self.running = True
        # Performance enhancements
        self.render_cache = RenderCache()
        self.dirty_rects: List[pygame.Rect] = []
        self.target_fps = 60  # Standard 60 FPS, not 144
        self.vsync_enabled = True
        self.auto_optimize = False  # Disabled by default

        # Auto-optimization thresholds
        self.fps_history = deque(maxlen=60)
        self.auto_scale_adjust = False
        self.min_acceptable_fps = 30

        # Palette organised into collapsible sections.
        # Each section: (section_name, items_list)
        # Section names starting with "" (empty) are always expanded.
        self.palette_sections = [
            ("Add Widget", [
                ("Label", lambda: self._add_widget("label")),
                ("Button", lambda: self._add_widget("button")),
                ("Panel", lambda: self._add_widget("panel")),
                ("Progress", lambda: self._add_widget("progressbar")),
                ("Gauge", lambda: self._add_widget("gauge")),
                ("Slider", lambda: self._add_widget("slider")),
                ("Checkbox", lambda: self._add_widget("checkbox")),
                ("Textbox", lambda: self._add_widget("textbox")),
                ("Chart", lambda: self._add_widget("chart")),
                ("Icon", lambda: self._add_widget("icon")),
            ]),
            ("Templates", self._build_template_actions()),
            ("Colors", [
                ("White / Black", lambda: self._apply_color_preset("#f5f5f5", "#000000")),
                ("White / Panel", lambda: self._apply_color_preset("#f5f5f5", "#101010")),
                ("LightGray / Dark", lambda: self._apply_color_preset("#e0e0e0", "#080808")),
                ("Gray / Dark", lambda: self._apply_color_preset("#b0b0b0", "#080808")),
            ]),
            ("Components", [
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
            ]),
            ("Layout", [
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
            ]),
            ("Profiles", [
                ("ESP32 OS 256x128", lambda: self._set_profile("esp32os_256x128_gray4")),
                ("ESP32 OS 240x128 1b", lambda: self._set_profile("esp32os_240x128_mono")),
                ("ESP32 OS 240x128 RGB", lambda: self._set_profile("esp32os_240x128_rgb565")),
                ("OLED 128x64", lambda: self._set_profile("oled_128x64")),
                ("TFT 320x240", lambda: self._set_profile("tft_320x240")),
                ("TFT 480x320", lambda: self._set_profile("tft_480x320")),
            ]),
            ("Presets", self._build_widget_presets_actions()),
        ]
        # Sections collapsed by default (all except "Add Widget")
        self.palette_collapsed: set = {"Templates", "Colors", "Components", "Layout", "Profiles", "Presets"}
        # Inspector sections collapsed by default (Layers collapsed, Info+Selection open)
        self.inspector_collapsed: set = {"Layers"}
        # Build flat palette_actions for backward-compat with click handler
        self.palette_actions = []
        for _sec_name, items in self.palette_sections:
            self.palette_actions += items

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
        if self._restored_from_autosave:
            print(f"[INFO] Autosave restored from {self.autosave_path}")

    # ------------------------------------------------------------------ #
    # Scene load/save
    # ------------------------------------------------------------------ #
    def _set_status(self, message: str, ttl_sec: float = 3.0) -> None:
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
        except Exception:
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
        except Exception:
            pass
        self._set_status(f"Editing {field} (Enter=apply Esc=cancel)", ttl_sec=4.0)

    def _inspector_field_to_str(self, field: str, w: WidgetConfig) -> str:
        return inspector_field_to_str(self, field, w)

    def _is_valid_color_str(self, value: str) -> bool:
        s = str(value or "").strip().lower()
        if not s:
            return True
        if s in _NAMED_COLORS:
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
        self._dirty = True
        scene_name = getattr(self.designer, "current_scene", None)
        if scene_name:
            self._dirty_scenes.add(scene_name)

    def _load_or_default(self):
        io_ops.load_or_default(self)

    def _build_template_actions(self):
        actions = []
        if not self.template_library.templates:
            return actions
        actions.append(("-- Templates --", None))
        for tpl in self.template_library.templates[:6]:
            label = f"Template: {tpl.metadata.name}"
            actions.append((label, lambda tpl=tpl: self._apply_template(tpl)))
        return actions

    def _apply_template(self, template: Template):
        """Replace current scene with widgets from a template."""
        sc = self.state.current_scene()
        self.designer._save_state()
        sc.widgets.clear()
        for wdict in template.scene._raw_data.get("widgets", []):
            try:
                sc.widgets.append(WidgetConfig(**wdict))
            except Exception:
                continue
        self.state.selected_idx = 0 if sc.widgets else None
        self.state.selected = [0] if sc.widgets else []
        self._mark_dirty()

    def _apply_first_template(self):
        """Quick apply first template to current scene."""
        if not self.template_library.templates:
            return
        self._apply_template(self.template_library.templates[0])

    def _apply_color_preset(self, fg: str, bg: str):
        """Apply fg/bg colors to selected widgets."""
        if not self.state.selected:
            return
        sc = self.state.current_scene()
        try:
            self.designer._save_state()
        except Exception:
            pass
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                w = sc.widgets[idx]
                w.color_fg = fg
                w.color_bg = bg
        self._mark_dirty()

    def _set_profile(self, key: str):
        """Switch hardware profile (updates scene size + estimation)."""
        if key not in HARDWARE_PROFILES:
            return
        pinfo = HARDWARE_PROFILES[key]
        self.hardware_profile = key
        self.default_size = (pinfo["width"], pinfo["height"])
        self.designer.set_hardware_profile(key)
        # Preserve current window size; recompute scale to fit new canvas.
        win_size = self.window.get_size() if self.window else None
        self._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
        self._mark_dirty()
        print(f"[INFO] Hardware profile: {pinfo['label']}")

    def _cycle_profile(self):
        """Cycle through known hardware profiles (F6)."""
        if not PROFILE_ORDER:
            return
        if self.hardware_profile in PROFILE_ORDER:
            idx = PROFILE_ORDER.index(self.hardware_profile)
            next_key = PROFILE_ORDER[(idx + 1) % len(PROFILE_ORDER)]
        else:
            next_key = PROFILE_ORDER[0]
        self._set_profile(next_key)

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

    def save_json(self):
        io_ops.save_json(self)

    def load_json(self):
        io_ops.load_json(self)

    def _new_scene(self):
        """Clear current design to a fresh scene."""
        self.designer = UIDesigner(*self.default_size)
        self.designer.create_scene("main")
        self.designer.set_responsive_base()
        sc = self.designer.scenes[self.designer.current_scene]
        sc.width, sc.height = self.default_size
        self.designer.width, self.designer.height = sc.width, sc.height
        win_size = self.window.get_size() if self.window else None
        self._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
        self.state = EditorState(self.designer, self.layout)
        self._dirty = True

    # ------------------------------------------------------------------ #
    # Event handling
    # ------------------------------------------------------------------ #
    @staticmethod
    def _coalesce_motion_and_wheel(events: List[object]) -> List[object]:
        """Keep only the latest mouse motion and wheel event per frame to reduce noise."""
        kept: List[object] = []
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
    def _dedupe_keydowns(events: List[object]) -> List[object]:
        """Keep only the first KEYDOWN per key in this frame; always keep KEYUP."""
        seen_keys = set()
        filtered: List[object] = []
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
        self.dirty_rects.clear()

        # Force a full redraw when requested (e.g., overlay toggles).
        if bool(getattr(self, "_force_full_redraw", False)) or bool(
            getattr(self, "show_help_overlay", False)
        ):
            self.dirty_rects = [pygame.Rect(0, 0, self.layout.width, self.layout.height)]
            return

        # Check what changed
        if self.state.dragging or self.state.resizing:
            # Only canvas needs update
            self.dirty_rects.append(self.layout.canvas_rect)
        elif self.state.inspector_selected_field:
            # Only inspector needs update
            self.dirty_rects.append(self.layout.inspector_rect)

        # If nothing specific, check all
        if not self.dirty_rects:
            self.dirty_rects = [pygame.Rect(0, 0, self.layout.width, self.layout.height)]

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
        # Check cache first
        cache_key = hash(
            (
                self.scale,
                self.state.selected_idx,
                tuple(sorted(self.state.selected)),
                int(bool(self.show_help_overlay)),
                self.designer.current_scene,
                len(self.state.current_scene().widgets),
            )
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

    def _auto_complete_widget(self, w: WidgetConfig):
        """Automatically complete widget configuration with smart defaults."""
        if not w.text and w.type == "button":
            w.text = "Button"
        if not w.color_fg:
            w.color_fg = "#f5f5f5"
        if not w.color_bg:
            w.color_bg = "#000000"

        # Smart sizing based on content
        if w.type == "label" and w.text:
            if text_metrics.is_device_profile(self.hardware_profile):
                text_w = len(str(w.text)) * text_metrics.DEVICE_CHAR_W
                text_h = text_metrics.DEVICE_CHAR_H
                w.width = max(w.width, int(text_w + 4))
                w.height = max(w.height, int(text_h + 4))
            else:
                text_size = self.font.size(w.text)
                w.width = max(w.width, text_size[0] + GRID)
                w.height = max(w.height, text_size[1] + GRID // 2)

        # Auto-align to grid
        w.x = snap(w.x)
        w.y = snap(w.y)
        w.width = snap(w.width)
        w.height = snap(w.height)

    def _intelligent_auto_arrange(self):
        """Smart auto-arrangement using AI-like heuristics."""
        sc = self.state.current_scene()
        if not sc.widgets:
            return

        self.designer._save_state()

        # Group widgets by type
        groups = {}
        for w in sc.widgets:
            if w.type not in groups:
                groups[w.type] = []
            groups[w.type].append(w)

        # Smart placement based on widget relationships
        for _widget_type, widgets in groups.items():
            # Sort by size for better packing
            widgets.sort(key=lambda w: w.width * w.height, reverse=True)

            for w in widgets:
                # Find best position with least overlap
                best_x, best_y = self._find_best_position(w, sc)
                w.x = best_x
                w.y = best_y

        self._mark_dirty()

    def _find_best_position(self, widget: WidgetConfig, scene) -> Tuple[int, int]:
        """Find a good position: next to selection, at mouse cursor, or first free slot."""
        ww = max(GRID, int(widget.width))
        wh = max(GRID, int(widget.height))
        max_x = max(0, int(scene.width) - ww)
        max_y = max(0, int(scene.height) - wh)

        def _overlaps(x: int, y: int) -> bool:
            r = pygame.Rect(x, y, ww, wh)
            for other in scene.widgets:
                if other is widget:
                    continue
                o = pygame.Rect(int(other.x), int(other.y), int(other.width), int(other.height))
                if r.colliderect(o):
                    return True
            return False

        def _clamp_snap(x: int, y: int) -> Tuple[int, int]:
            x = max(0, min(max_x, snap(x) if self.snap_enabled else x))
            y = max(0, min(max_y, snap(y) if self.snap_enabled else y))
            return x, y

        # Strategy 1: Place next to selected widget (right, then below)
        if self.state.selected:
            bounds = self._selection_bounds(self.state.selected)
            if bounds is not None:
                # Try right of selection
                cx, cy = _clamp_snap(bounds.right + GRID, bounds.y)
                if not _overlaps(cx, cy):
                    return cx, cy
                # Try below selection
                cx, cy = _clamp_snap(bounds.x, bounds.bottom + GRID)
                if not _overlaps(cx, cy):
                    return cx, cy

        # Strategy 2: Place at mouse cursor if on canvas
        sr = getattr(self, "scene_rect", None)
        if sr and isinstance(sr, pygame.Rect) and sr.collidepoint(self.pointer_pos):
            cx = int(self.pointer_pos[0] - sr.x) - ww // 2
            cy = int(self.pointer_pos[1] - sr.y) - wh // 2
            cx, cy = _clamp_snap(cx, cy)
            if not _overlaps(cx, cy):
                return cx, cy

        # Strategy 3: Scan rows for first non-overlapping slot
        for y in range(0, max_y + 1, GRID):
            for x in range(0, max_x + 1, GRID):
                if not _overlaps(x, y):
                    return x, y

        # Fallback
        return _clamp_snap(GRID, GRID)

    def run(self):
        """Main loop."""
        while self.running:
            # Dynamic FPS adjustment
            if self.vsync_enabled:
                tick_fps = int(self.target_fps)
            elif self.auto_scale_adjust:
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
        return tuple(max(0, min(255, c + delta)) for c in color)

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
            except Exception:
                continue

        if is_headless:
            try:
                # Pygame bundled default font is available cross-platform and keeps tests stable.
                return pygame.font.Font(None, size)
            except Exception:
                pass

        try:
            return pygame.font.SysFont("monospace", size, bold=False)
        except Exception:
            try:
                return pygame.font.Font(None, size)
            except Exception:
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
        except Exception:
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
        except Exception:
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

    def _set_selection(self, indices: List[int], anchor_idx: Optional[int] = None) -> None:
        selection_ops.set_selection(self, indices, anchor_idx=anchor_idx)

    def _groups_for_index(self, idx: int) -> List[str]:
        groups: List[str] = []
        try:
            gdict = getattr(self.designer, "groups", {}) or {}
        except Exception:
            gdict = {}
        for gname, members in gdict.items():
            try:
                if idx in members:
                    groups.append(str(gname))
            except Exception:
                continue
        groups.sort()
        return groups

    def _primary_group_for_index(self, idx: int) -> Optional[str]:
        groups = self._groups_for_index(idx)
        return groups[0] if groups else None

    def _group_members(self, name: str) -> List[int]:
        try:
            members = list((getattr(self.designer, "groups", {}) or {}).get(name, []))
        except Exception:
            members = []
        sc = self.state.current_scene()
        valid: List[int] = []
        for m in members:
            try:
                i = int(m)
            except Exception:
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
        except Exception:
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
        prefix = f"{str(root_prefix or '')}."
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
        except Exception:
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
        except Exception:
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
            except Exception:
                gdict = {}
            for gname, members in gdict.items():
                try:
                    if sel.intersection(set(members)):
                        target.append(str(gname))
                except Exception:
                    continue
        if not target:
            self._set_status("Ungroup: no group.", ttl_sec=2.0)
            return
        removed = 0
        for gname in sorted(set(target)):
            try:
                if self.designer.delete_group(gname):
                    removed += 1
            except Exception:
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
        rows += int(len(sc.widgets))  # widget list
        gap = max(0, int(getattr(self, "pixel_padding", 0) or 0))
        return int(self.pixel_row_height) * rows + gap

    def _inspector_content_height(self) -> int:
        """Calculate inspector content height accounting for collapsed sections."""
        rows, _, _ = self._compute_inspector_rows()
        collapsed = getattr(self, "inspector_collapsed", set())
        count = 0
        current_section: str | None = None
        for key, _text in rows:
            if isinstance(key, str) and key.startswith("_section:"):
                current_section = key[len("_section:"):]
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
            except Exception:
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
        if event.type == pygame.QUIT:
            if self._dirty_scenes and time.time() - self._quit_confirm_ts > 3.0:
                self._quit_confirm_ts = time.time()
                n = len(self._dirty_scenes)
                self._set_status(
                    f"Unsaved changes in {n} scene(s). Close again to quit.",
                    ttl_sec=3.0,
                )
                return
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            windowing.handle_video_resize(self, event.w, event.h)
            return
        if event.type == pygame.KEYDOWN:
            self._on_key_down(event)
            return
        # Right-click context menu
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.pointer_pos = self._screen_to_logical(event.pos)
            lx, ly = self.pointer_pos
            # Right-click on scene tab → tab context menu
            if self.layout.scene_tabs_rect.collidepoint(lx, ly):
                self._open_tab_context_menu(self.pointer_pos)
                self._mark_dirty()
                return
            self._open_context_menu(self.pointer_pos)
            self._mark_dirty()
            return

        # Middle-click to close tab
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Dismiss context menu on left click
            menu = getattr(self, "_context_menu", None)
            if menu and menu.get("visible"):
                self.pointer_pos = self._screen_to_logical(event.pos)
                self._click_context_menu(self.pointer_pos)
                self._mark_dirty()
                return
            self.pointer_down = True
            self.pointer_pos = self._screen_to_logical(event.pos)
            # Detect double-click for quick text editing
            now = time.time()
            last_click_time = getattr(self, "_last_click_time", 0.0)
            last_click_pos = getattr(self, "_last_click_pos", (-9999, -9999))
            is_double = (
                now - last_click_time < 0.4
                and abs(self.pointer_pos[0] - last_click_pos[0]) < 6
                and abs(self.pointer_pos[1] - last_click_pos[1]) < 6
            )
            self._last_click_time = now
            self._last_click_pos = self.pointer_pos
            if is_double and not self.sim_input_mode:
                self._handle_double_click(self.pointer_pos)
                self._mark_dirty()
                return
            self._on_mouse_down(self.pointer_pos)
            self._mark_dirty()
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pointer_down = False
            self.pointer_pos = self._screen_to_logical(event.pos)
            self._on_mouse_up(self.pointer_pos)
            self._mark_dirty()
            return
        if event.type == pygame.MOUSEMOTION:
            self.pointer_pos = self._screen_to_logical(event.pos)
            self._on_mouse_move(self.pointer_pos, event.buttons)
            self._mark_dirty()
            return
        if event.type == pygame.MOUSEWHEEL:
            try:
                dx = int(getattr(event, "x", 0))
                dy = int(getattr(event, "y", 0))
            except Exception:
                dx, dy = 0, 0
            self._on_mouse_wheel(dx, dy)
            self._mark_dirty()
            return
        if event.type == pygame.TEXTINPUT:
            try:
                text = str(getattr(event, "text", ""))
            except Exception:
                text = ""
            self._on_text_input(text)
            self._mark_dirty()
            return

    def _open_tab_context_menu(self, pos: Tuple[int, int]) -> None:
        """Open right-click context menu for scene tabs."""
        lx, ly = pos
        # Find which tab was right-clicked
        for rect, tab_idx, _tab_name in getattr(self, "tab_hitboxes", []):
            if tab_idx >= 0 and rect.collidepoint(lx, ly):
                self._jump_to_scene(tab_idx)
                break
        items: list = []
        items.append(("Rename Scene", "DblClick", "tab_rename"))
        items.append(("Duplicate Scene", "", "tab_duplicate"))
        items.append(("New Scene", "Ctrl+N", "tab_new"))
        names = list(self.designer.scenes.keys())
        if len(names) > 1:
            items.append(("---", "", None))
            items.append(("Close Scene", "MidClick", "tab_close"))
            items.append(("Close Others", "", "tab_close_others"))
            cur_idx = names.index(self.designer.current_scene) if self.designer.current_scene in names else 0
            if cur_idx < len(names) - 1:
                items.append(("Close Right", "", "tab_close_right"))
        self._context_menu = {"visible": True, "pos": pos, "items": items}

    def _open_context_menu(self, pos: Tuple[int, int]) -> None:
        """Open right-click context menu at pos."""
        sr = getattr(self, "scene_rect", self.layout.canvas_rect)
        if not isinstance(sr, pygame.Rect):
            sr = self.layout.canvas_rect
        items: list = []
        hit = self.state.hit_test_at(pos, sr) if sr.collidepoint(*pos) else None
        if hit is not None and hit not in self.state.selected:
            self._set_selection([hit], anchor_idx=hit)

        SEP = ("---", "", None)

        if self.state.selected:
            # -- Edit --
            items.append(("Edit Text", "DblClick", "edit_text"))
            items.append(("Smart Edit", "E", "smart_edit"))
            items.append(SEP)
            # -- Clipboard --
            items.append(("Copy", "Ctrl+C", "copy"))
            items.append(("Cut", "Ctrl+X", "cut"))
            items.append(("Duplicate", "Ctrl+D", "duplicate"))
            items.append(("Delete", "Del", "delete"))
            items.append(SEP)
            # -- Z-order --
            items.append(("Bring Forward", "]", "z_forward"))
            items.append(("Send Backward", "[", "z_backward"))
            items.append(("Bring to Front", "Ctrl+]", "z_front"))
            items.append(("Send to Back", "Ctrl+[", "z_back"))
            items.append(("Move Up", "C+S+Up", "reorder_up"))
            items.append(("Move Down", "C+S+Dn", "reorder_down"))
            items.append(SEP)
            # -- Appearance --
            items.append(("Cycle Style", "S", "cycle_style"))
            items.append(("Cycle Type", "T", "cycle_type"))
            items.append(("Cycle Border", "B", "cycle_border"))
            items.append(SEP)
            # -- Transform --
            items.append(("Mirror", "M", "mirror"))
            items.append(("Center in Scene", ".", "center_in_scene"))
            items.append(("Snap to Grid", "Ctrl+M", "snap_to_grid"))
            items.append(("Wrap in Panel", "", "wrap_in_panel"))
            items.append(("Fill Scene", "", "fill_scene"))
            items.append(("Shrink Panel", "", "shrink_to_content"))
            items.append(("Select Children", "", "select_children"))
            items.append(("Select Overlap", "", "select_overlapping"))
            items.append(("Auto-Label", "", "auto_label"))
            items.append(("Inset 8px", "", "inset_widgets"))
            items.append(("Outset 8px", "", "outset_widgets"))
            items.append(("Align Top", "", "align_scene_top"))
            items.append(("Align Bottom", "", "align_scene_bottom"))
            items.append(("Align Left", "", "align_scene_left"))
            items.append(("Align Right", "", "align_scene_right"))
            items.append(("Center Horiz", "", "center_h"))
            items.append(("Center Vert", "", "center_v"))
            items.append(("Tile Fill", "", "tile_fill"))
            items.append(("Del Hidden", "", "delete_hidden"))
            items.append(("Del Offscreen", "", "delete_offscreen"))
            items.append(("Swap W\u2194H", "", "swap_dims"))
            items.append(("Scatter Random", "", "scatter_random"))
            items.append(("Toggle Checked", "", "toggle_checked"))
            items.append(("Reset Values", "", "reset_values"))
            items.append(("Flatten Z", "", "flatten_z"))
            items.append(("Number IDs", "", "number_ids"))
            items.append(("Z by Position", "", "z_by_position"))
            items.append(("Clone Grid", "", "clone_grid"))
            items.append(("Mirror Scene H", "", "mirror_scene_h"))
            items.append(("Mirror Scene V", "", "mirror_scene_v"))
            items.append(("Sort by Z", "", "sort_by_z"))
            items.append(("Clamp to Scene", "", "clamp_to_scene"))
            items.append(("Select Unlocked", "", "select_unlocked"))
            items.append(("Select Disabled", "", "select_disabled"))
            items.append(("Snap All Grid", "", "snap_all_grid"))
            items.append(("Center in Parent", "", "center_in_parent"))
            items.append(("Size to Text", "", "size_to_text"))
            items.append(("Fill Parent", "", "fill_parent"))
            items.append(("Clear Text", "", "clear_all_text"))
            items.append(("Move to Origin", "", "move_to_origin"))
            items.append(("Make Square", "", "make_square"))
            items.append(("Scale Up 2\u00d7", "", "scale_up"))
            items.append(("Scale Down \u00bd", "", "scale_down"))
            items.append(("Number Text", "", "number_text"))
            items.append(("Reset Padding", "", "reset_padding"))
            items.append(("Reset Colors", "", "reset_colors"))
            items.append(("Outline Only", "", "outline_only"))
            items.append(("Select Largest", "", "select_largest"))
            items.append(("Select Smallest", "", "select_smallest"))
            items.append(("Set Inverse", "", "set_inverse"))
            items.append(("Set Bold", "", "set_bold"))
            items.append(("Set Default Style", "", "set_default_style"))
            items.append(SEP)
            # -- Flags --
            items.append(("Lock/Unlock", "L", "toggle_lock"))
            items.append(("Show/Hide", "V", "toggle_visibility"))
            items.append(("Enable/Disable", "F8", "toggle_enabled"))

        if len(self.state.selected) >= 2:
            items.append(SEP)
            # -- Multi: Layout --
            items.append(("Stack Vertical", ";", "stack_vertical"))
            items.append(("Stack Horizontal", "'", "stack_horizontal"))
            items.append(("Equal Gaps", "C+A+E", "equalize_gaps"))
            items.append(("Space Even H", "C+F8", "space_h"))
            items.append(("Space Even V", "C+F9", "space_v"))
            items.append(("Grid Arrange", "C+A+G", "grid_arrange"))
            items.append(("Flow Layout", "C+F6", "flow_layout"))
            items.append(SEP)
            # -- Multi: Transform --
            items.append(("Swap Positions", ",", "swap_positions"))
            items.append(("Reverse Order", "C+A+R", "reverse_order"))
            items.append(("Normalize Size", "C+A+N", "normalize_sizes"))
            items.append(("Distribute 2-Col", "", "distribute_columns"))
            items.append(("Distribute 2-Row", "", "distribute_rows"))
            items.append(("Pack Left", "", "pack_left"))
            items.append(("Pack Top", "", "pack_top"))
            items.append(("Cascade", "", "cascade_arrange"))
            items.append(("Align Centers H", "", "align_h_centers"))
            items.append(("Align Centers V", "", "align_v_centers"))
            items.append(("Align Left", "", "align_left_edges"))
            items.append(("Align Top", "", "align_top_edges"))
            items.append(("Align Right", "", "align_right_edges"))
            items.append(("Align Bottom", "", "align_bottom_edges"))
            items.append(("Spread Values", "", "spread_values"))
            items.append(("Distribute 3-Col", "", "distribute_3col"))
            items.append(("Match Width", "", "match_first_width"))
            items.append(("Match Height", "", "match_first_height"))
            items.append(SEP)
            # -- Multi: Propagate --
            items.append(("Prop Style", "C+A+P", "propagate_style"))
            items.append(("Prop Colors", "C+A+K", "propagate_colors"))
            items.append(("Prop Border", "C+A+B", "propagate_border"))
            items.append(("Prop Align", "C+A+J", "propagate_align"))
            items.append(("Prop Padding", "C+A+U", "propagate_padding"))
            items.append(("Prop Margin", "C+A+Y", "propagate_margin"))
            items.append(("Prop Value", "C+A+Q", "propagate_value"))
            items.append(("Prop Look", "C+A+Z", "propagate_appearance"))
            items.append(("Prop Text", "", "propagate_text"))
            items.append(SEP)
            # -- Multi: Clone --
            items.append(("Quick Clone", "C+S+Q", "quick_clone"))
            items.append(("Dup Below", "S+,", "dup_below"))
            items.append(("Dup Right", "S+.", "dup_right"))
            items.append(("Clone Text", "C+A+L", "clone_text"))
            items.append(("Inc Text #", "C+A+I", "increment_text"))
            items.append(SEP)
            # -- Multi: Info --
            items.append(("Measure Gaps", "C+F7", "measure"))

        if getattr(self, "_clipboard", None):
            items.append(SEP)
            items.append(("Paste", "Ctrl+V", "paste"))
        if getattr(self, "_style_clipboard", None):
            items.append(("Paste Style", "C+S+V", "paste_style"))

        items.append(SEP)
        # -- View toggles --
        gc = "\u2713 " if self.show_grid else "  "
        rc = "\u2713 " if getattr(self, "show_rulers", True) else "  "
        cc = "\u2713 " if getattr(self, "show_center_guides", False) else "  "
        xc = "\u2713 " if self.snap_enabled else "  "
        ic = "\u2713 " if getattr(self, "show_widget_ids", False) else "  "
        zc = "\u2713 " if getattr(self, "show_z_labels", False) else "  "
        items.append((f"{gc}Grid", "G", "view_grid"))
        items.append((f"{rc}Rulers", "", "view_rulers"))
        items.append((f"{cc}Center Guides", "Shift+G", "view_guides"))
        items.append((f"{xc}Snap", "X", "view_snap"))
        items.append((f"{ic}Widget IDs", "", "view_ids"))
        items.append((f"{zc}Z-Labels", "", "view_zlabels"))

        items.append(SEP)
        # -- Add Widgets --
        items.append(("Add Label", "1", "add_label"))
        items.append(("Add Button", "2", "add_button"))
        items.append(("Add Panel", "3", "add_panel"))
        items.append(("Add Progress", "4", "add_progressbar"))
        items.append(("Add Gauge", "5", "add_gauge"))
        items.append(("Add Slider", "6", "add_slider"))
        items.append(("Add Checkbox", "7", "add_checkbox"))
        items.append(("Add Chart", "8", "add_chart"))
        items.append(("Add Icon", "9", "add_icon"))
        items.append(("Add Textbox", "0", "add_textbox"))
        items.append(("Add Radiobutton", "S+0", "add_radiobutton"))
        items.append(SEP)
        # -- Quick Composites --
        items.append(("Header Bar", "S+F1", "create_header_bar"))
        items.append(("Nav Row", "S+F2", "create_nav_row"))
        items.append(("Form Pair", "S+F3", "create_form_pair"))
        items.append(("Status Bar", "S+F4", "create_status_bar"))
        items.append(("Toggle Group", "S+F5", "create_toggle_group"))
        items.append(("Slider+Label", "S+F6", "create_slider_label"))
        items.append(("Gauge Panel", "S+F7", "create_gauge_panel"))
        items.append(("Progress Row", "S+F8", "create_progress_section"))
        items.append(("Icon Btn Row", "S+F9", "create_icon_btn_row"))
        items.append(("Card Layout", "S+F11", "create_card_layout"))
        items.append(("Dashboard 2x2", "S+F12", "create_dashboard_grid"))
        items.append(("Split Layout", "C+F12", "create_split_layout"))

        # Collapse consecutive separators and strip leading/trailing
        cleaned: list = []
        for lbl, sc, act in items:
            if act is None:
                if not cleaned or cleaned[-1][2] is None:
                    continue
                cleaned.append((lbl, sc, act))
            else:
                cleaned.append((lbl, sc, act))
        while cleaned and cleaned[-1][2] is None:  # pragma: no cover — list always ends non-None
            cleaned.pop()
        while cleaned and cleaned[0][2] is None:  # pragma: no cover — loop above strips leading None
            cleaned.pop(0)

        self._context_menu = {"visible": True, "pos": pos, "items": cleaned}

    def _click_context_menu(self, pos: Tuple[int, int]) -> None:
        """Process a click on the context menu, or dismiss it."""
        menu = getattr(self, "_context_menu", None)
        if not menu or not menu.get("visible"):
            return
        hitboxes = menu.get("hitboxes", [])
        for rect, action in hitboxes:
            if rect.collidepoint(pos[0], pos[1]):
                menu["visible"] = False
                self._execute_context_action(action)
                return
        menu["visible"] = False

    def _execute_context_action(self, action: str) -> None:
        """Execute a context menu action."""
        if action == "tab_rename":
            self._rename_current_scene()
        elif action == "tab_duplicate":
            self._duplicate_current_scene()
        elif action == "tab_new":
            self._add_new_scene()
        elif action == "tab_close":
            self._delete_current_scene()
        elif action == "tab_close_others":
            self._close_other_scenes()
        elif action == "tab_close_right":
            self._close_scenes_to_right()
        elif action == "edit_text":
            self._inspector_start_edit("text")
        elif action == "duplicate":
            self._duplicate_selection()
        elif action == "delete":
            self._delete_selected()
        elif action == "copy":
            self._copy_selection()
        elif action == "cut":
            self._cut_selection()
        elif action == "paste":
            self._paste_clipboard()
        elif action == "z_forward":
            self._z_order_step(1)
        elif action == "z_backward":
            self._z_order_step(-1)
        elif action == "z_front":
            self._z_order_bring_to_front()
        elif action == "z_back":
            self._z_order_send_to_back()
        elif action == "toggle_lock":
            self._toggle_lock_selection()
        elif action == "toggle_visibility":
            self._toggle_visibility()
        elif action == "cycle_style":
            self._cycle_style()
        elif action == "cycle_type":
            self._cycle_widget_type()
        elif action == "cycle_border":
            self._cycle_border_style()
        elif action == "reorder_up":
            self._reorder_selection(-1)
        elif action == "reorder_down":
            self._reorder_selection(1)
        elif action == "paste_style":
            self._paste_style()
        elif action == "smart_edit":
            self._smart_edit()
        elif action == "toggle_enabled":
            self._toggle_enabled()
        elif action == "mirror":
            self._mirror_selection()
        elif action == "center_in_scene":
            self._center_in_scene()
        elif action == "snap_to_grid":
            self._snap_selection_to_grid()
        elif action == "swap_positions":
            self._swap_positions()
        elif action == "stack_vertical":
            self._stack_vertical()
        elif action == "stack_horizontal":
            self._stack_horizontal()
        elif action == "quick_clone":
            self._quick_clone()
        elif action == "dup_below":
            self._duplicate_below()
        elif action == "dup_right":
            self._duplicate_right()
        elif action == "equalize_gaps":
            self._equalize_gaps()
        elif action == "grid_arrange":
            self._grid_arrange()
        elif action == "reverse_order":
            self._reverse_widget_order()
        elif action == "normalize_sizes":
            self._normalize_sizes()
        elif action == "propagate_border":
            self._propagate_border()
        elif action == "increment_text":
            self._increment_text()
        elif action == "propagate_style":
            self._propagate_style()
        elif action == "clone_text":
            self._clone_text()
        elif action == "propagate_align":
            self._propagate_align()
        elif action == "propagate_colors":
            self._propagate_colors()
        elif action == "propagate_value":
            self._propagate_value()
        elif action == "propagate_padding":
            self._propagate_padding()
        elif action == "propagate_margin":
            self._propagate_margin()
        elif action == "propagate_appearance":
            self._propagate_appearance()
        elif action == "flow_layout":
            self._auto_flow_layout()
        elif action == "measure":
            self._measure_selection()
        elif action == "space_h":
            self._space_evenly_h()
        elif action == "space_v":
            self._space_evenly_v()
        elif action == "create_header_bar":
            self._create_header_bar()
        elif action == "create_nav_row":
            self._create_nav_row()
        elif action == "create_form_pair":
            self._create_form_pair()
        elif action == "create_status_bar":
            self._create_status_bar()
        elif action == "create_toggle_group":
            self._create_toggle_group()
        elif action == "create_slider_label":
            self._create_slider_with_label()
        elif action == "create_gauge_panel":
            self._create_gauge_panel()
        elif action == "create_progress_section":
            self._create_progress_section()
        elif action == "create_icon_btn_row":
            self._create_icon_button_row()
        elif action == "create_card_layout":
            self._create_card_layout()
        elif action == "create_dashboard_grid":
            self._create_dashboard_grid()
        elif action == "create_split_layout":
            self._create_split_layout()
        elif action == "wrap_in_panel":
            self._wrap_in_panel()
        elif action == "fill_scene":
            self._fill_scene()
        elif action == "shrink_to_content":
            self._shrink_to_content()
        elif action == "select_children":
            self._select_children()
        elif action == "select_overlapping":
            self._select_overlapping()
        elif action == "auto_label":
            self._auto_label_widgets()
        elif action == "inset_widgets":
            self._inset_widgets()
        elif action == "outset_widgets":
            self._outset_widgets()
        elif action == "distribute_columns":
            self._distribute_columns()
        elif action == "align_scene_top":
            self._align_to_scene_top()
        elif action == "align_scene_bottom":
            self._align_to_scene_bottom()
        elif action == "align_scene_left":
            self._align_to_scene_left()
        elif action == "align_scene_right":
            self._align_to_scene_right()
        elif action == "center_h":
            self._center_horizontal()
        elif action == "center_v":
            self._center_vertical()
        elif action == "tile_fill":
            self._tile_fill_scene()
        elif action == "delete_hidden":
            self._delete_hidden_widgets()
        elif action == "delete_offscreen":
            self._delete_offscreen_widgets()
        elif action == "swap_dims":
            self._swap_dimensions()
        elif action == "scatter_random":
            self._scatter_random()
        elif action == "toggle_checked":
            self._toggle_all_checked()
        elif action == "reset_values":
            self._reset_all_values()
        elif action == "flatten_z":
            self._flatten_z_index()
        elif action == "number_ids":
            self._number_widget_ids()
        elif action == "z_by_position":
            self._z_by_position()
        elif action == "clone_grid":
            self._clone_to_grid()
        elif action == "mirror_scene_h":
            self._mirror_scene_horizontal()
        elif action == "sort_by_z":
            self._sort_widgets_by_z()
        elif action == "clamp_to_scene":
            self._clamp_to_scene()
        elif action == "mirror_scene_v":
            self._mirror_scene_vertical()
        elif action == "select_unlocked":
            self._select_unlocked()
        elif action == "select_disabled":
            self._select_disabled()
        elif action == "snap_all_grid":
            self._snap_all_to_grid()
        elif action == "center_in_parent":
            self._center_in_parent()
        elif action == "size_to_text":
            self._size_to_text()
        elif action == "fill_parent":
            self._fill_parent()
        elif action == "clear_all_text":
            self._clear_all_text()
        elif action == "move_to_origin":
            self._move_to_origin()
        elif action == "make_square":
            self._make_square()
        elif action == "scale_up":
            self._scale_up()
        elif action == "scale_down":
            self._scale_down()
        elif action == "number_text":
            self._number_text()
        elif action == "reset_padding":
            self._reset_padding()
        elif action == "reset_colors":
            self._reset_colors()
        elif action == "outline_only":
            self._outline_only()
        elif action == "select_largest":
            self._select_largest()
        elif action == "select_smallest":
            self._select_smallest()
        elif action == "set_inverse":
            self._set_inverse_style()
        elif action == "set_bold":
            self._set_bold_style()
        elif action == "set_default_style":
            self._set_default_style()
        elif action == "align_h_centers":
            self._align_h_centers()
        elif action == "align_v_centers":
            self._align_v_centers()
        elif action == "align_left_edges":
            self._align_left_edges()
        elif action == "align_top_edges":
            self._align_top_edges()
        elif action == "align_right_edges":
            self._align_right_edges()
        elif action == "align_bottom_edges":
            self._align_bottom_edges()
        elif action == "distribute_3col":
            self._distribute_columns_3()
        elif action == "cascade_arrange":
            self._cascade_arrange()
        elif action == "spread_values":
            self._spread_values()
        elif action == "pack_left":
            self._pack_left()
        elif action == "pack_top":
            self._pack_top()
        elif action == "distribute_rows":
            self._distribute_rows()
        elif action == "propagate_text":
            self._propagate_text()
        elif action == "match_first_width":
            self._match_first_width()
        elif action == "match_first_height":
            self._match_first_height()
        elif action == "view_grid":
            self.show_grid = not self.show_grid
            self._mark_dirty()
        elif action == "view_rulers":
            self.show_rulers = not getattr(self, "show_rulers", True)
            self._mark_dirty()
        elif action == "view_guides":
            self._toggle_center_guides()
        elif action == "view_snap":
            self.snap_enabled = not self.snap_enabled
            self._mark_dirty()
        elif action == "view_ids":
            self._toggle_widget_ids()
        elif action == "view_zlabels":
            self._toggle_z_labels()
        elif action.startswith("add_"):
            kind = action[4:]  # strip "add_"
            self._add_widget(kind)

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
        """Move selected widgets z_index by delta."""
        if not self.state.selected:
            return
        try:
            self.designer._save_state()
        except Exception:
            pass
        sc = self.state.current_scene()
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                w = sc.widgets[idx]
                w.z_index = int(getattr(w, "z_index", 0) or 0) + delta
        direction = "forward" if delta > 0 else "backward"
        self._set_status(f"z-order: {direction}", ttl_sec=1.5)
        self._mark_dirty()

    def _z_order_bring_to_front(self) -> None:
        """Set selected widgets z_index above all others."""
        if not self.state.selected:
            return
        try:
            self.designer._save_state()
        except Exception:
            pass
        sc = self.state.current_scene()
        max_z = 0
        for w in sc.widgets:
            z = int(getattr(w, "z_index", 0) or 0)
            if z > max_z:
                max_z = z
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                max_z += 1
                sc.widgets[idx].z_index = max_z
        self._set_status("z-order: bring to front", ttl_sec=1.5)
        self._mark_dirty()

    def _z_order_send_to_back(self) -> None:
        """Set selected widgets z_index below all others."""
        if not self.state.selected:
            return
        try:
            self.designer._save_state()
        except Exception:
            pass
        sc = self.state.current_scene()
        min_z = 0
        for w in sc.widgets:
            z = int(getattr(w, "z_index", 0) or 0)
            if z < min_z:
                min_z = z
        for idx in reversed(self.state.selected):
            if 0 <= idx < len(sc.widgets):
                min_z -= 1
                sc.widgets[idx].z_index = min_z
        self._set_status("z-order: send to back", ttl_sec=1.5)
        self._mark_dirty()

    def _toggle_lock_selection(self) -> None:
        """Toggle locked state on selected widgets."""
        if not self.state.selected:
            self._set_status("Lock: nothing selected.", ttl_sec=2.0)
            return
        try:
            self.designer._save_state()
        except Exception:
            pass
        sc = self.state.current_scene()
        values = []
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                values.append(bool(getattr(sc.widgets[idx], "locked", False)))
        new_val = not all(values) if values else True
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                sc.widgets[idx].locked = new_val
        label = "locked" if new_val else "unlocked"
        self._set_status(f"Widget(s) {label}.", ttl_sec=1.5)
        self._mark_dirty()

    def _zoom_to_fit(self) -> None:
        """Auto-compute scale to fit the entire scene in the window."""
        try:
            sc = self.state.current_scene()
            scene_w = max(1, int(sc.width))
            scene_h = max(1, int(sc.height))
            canvas = self.layout.canvas_rect
            if canvas.width <= 0 or canvas.height <= 0:
                return
            # Compute scale that makes the scene fill the canvas at current window size
            win_w, win_h = self.window.get_size()
            # The canvas is a fraction of the logical surface; compute available space
            avail_w = max(1, canvas.width)
            avail_h = max(1, canvas.height)
            # At scale=current, avail is avail_w×avail_h for scene_w×scene_h
            # We want scale * scene_w <= win_canvas_w, so scale = win_canvas_w / scene_w
            # But canvas size also depends on scale... use window-based estimate
            fit_w = win_w // max(1, self.layout.width) * avail_w // scene_w
            fit_h = win_h // max(1, self.layout.height) * avail_h // scene_h
            new_scale = max(1, min(int(getattr(self, "max_auto_scale", 8) or 8), fit_w, fit_h))
            self._set_scale(new_scale)
            self._set_status(f"Zoom to fit: scale={new_scale}", ttl_sec=2.0)
        except Exception:
            pass

    def _switch_scene(self, direction: int) -> None:
        """Switch to next/previous scene."""
        names = list(self.designer.scenes.keys())
        if len(names) <= 1:
            self._set_status("Only one scene.", ttl_sec=2.0)
            return
        current = self.designer.current_scene
        try:
            idx = names.index(current)
        except ValueError:
            idx = 0
        idx = (idx + direction) % len(names)
        self.designer.current_scene = names[idx]
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"Scene: {names[idx]}", ttl_sec=2.0)
        self._mark_dirty()

    def _handle_double_click(self, pos: Tuple[int, int]) -> None:
        """Double-click on a widget to start editing its text, or on a tab to rename."""
        lx, ly = pos
        # Double-click on scene tab → rename
        if self.layout.scene_tabs_rect.collidepoint(lx, ly):
            for rect, tab_idx, _tab_name in getattr(self, "tab_hitboxes", []):
                if tab_idx >= 0 and rect.collidepoint(lx, ly):
                    self._jump_to_scene(tab_idx)
                    self._rename_current_scene()
                    return
            return
        sr = getattr(self, "scene_rect", self.layout.canvas_rect)
        if not isinstance(sr, pygame.Rect):
            sr = self.layout.canvas_rect
        if not sr.collidepoint(pos[0], pos[1]):
            return
        hit = self.state.hit_test_at(pos, sr)
        if hit is None:
            return
        sc = self.state.current_scene()
        if not (0 <= hit < len(sc.widgets)):
            return
        self._set_selection([hit], anchor_idx=hit)
        self._inspector_start_edit("text")

    def _on_mouse_down(self, pos: Tuple[int, int]) -> None:
        input_handlers.on_mouse_down(self, pos)

    def _on_mouse_up(self, _pos: Tuple[int, int]) -> None:
        input_handlers.on_mouse_up(self, _pos)

    def _on_mouse_move(self, pos: Tuple[int, int], _buttons: Tuple[int, int, int]) -> None:
        input_handlers.on_mouse_move(self, pos, _buttons)

    def _on_mouse_wheel(self, _dx: int, dy: int) -> None:
        input_handlers.on_mouse_wheel(self, _dx, dy)

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
        except Exception:
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
        except Exception:
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
        except Exception:
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

    def _jump_to_scene(self, index: int) -> None:
        """Jump to scene by 0-based index."""
        names = list(self.designer.scenes.keys())
        if index >= len(names):
            self._set_status(f"Scene #{index + 1} does not exist ({len(names)} scenes).", ttl_sec=2.0)
            return
        self.designer.current_scene = names[index]
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"Scene {index + 1}: {names[index]}", ttl_sec=2.0)
        self._mark_dirty()

    def _save_selection_as_template(self) -> None:
        """Save selected widgets as a named template."""
        if not self.state.selected:
            self._set_status("Save template: nothing selected.", ttl_sec=2.0)
            return
        sc = self.state.current_scene()
        widgets = []
        for idx in self.state.selected:
            if 0 <= idx < len(sc.widgets):
                from dataclasses import asdict
                widgets.append(asdict(sc.widgets[idx]))
        if not widgets:
            return
        # Use inline input to get a name
        self.state.inspector_selected_field = "_template_name"
        self.state.inspector_input_buffer = ""
        self._pending_template_widgets = widgets
        try:
            pygame.key.start_text_input()
        except Exception:
            pass
        self._set_status("Template name (Enter=save Esc=cancel)", ttl_sec=4.0)

    def _delete_current_scene(self) -> None:
        """Delete the current scene if more than one exists."""
        names = list(self.designer.scenes.keys())
        if len(names) <= 1:
            self._set_status("Cannot delete the only scene.", ttl_sec=2.0)
            return
        cur = self.designer.current_scene
        idx = names.index(cur) if cur in names else 0
        del self.designer.scenes[cur]
        self._dirty_scenes.discard(cur)
        # Switch to adjacent scene
        remaining = list(self.designer.scenes.keys())
        new_idx = min(idx, len(remaining) - 1)
        self.designer.current_scene = remaining[new_idx]
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"Deleted scene: {cur}", ttl_sec=2.0)
        self._mark_dirty()

    def _close_other_scenes(self) -> None:
        """Close all scenes except the current one."""
        cur = self.designer.current_scene
        names = [n for n in self.designer.scenes if n != cur]
        if not names:
            return
        for n in names:
            del self.designer.scenes[n]
            self._dirty_scenes.discard(n)
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"Closed {len(names)} scene(s)", ttl_sec=2.0)
        self._mark_dirty()

    def _close_scenes_to_right(self) -> None:
        """Close all scenes to the right of the current one."""
        names = list(self.designer.scenes.keys())
        cur = self.designer.current_scene
        idx = names.index(cur) if cur in names else 0
        to_remove = names[idx + 1:]
        if not to_remove:
            return
        for n in to_remove:
            del self.designer.scenes[n]
            self._dirty_scenes.discard(n)
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"Closed {len(to_remove)} scene(s) to the right", ttl_sec=2.0)
        self._mark_dirty()

    def _add_new_scene(self) -> None:
        """Add a new scene to the design."""
        names = list(self.designer.scenes.keys())
        base = "scene"
        idx = len(names) + 1
        while f"{base}_{idx}" in names:
            idx += 1
        name = f"{base}_{idx}"
        self.designer.create_scene(name)
        sc = self.designer.scenes[name]
        sc.width, sc.height = self.default_size
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"New scene: {name}", ttl_sec=2.0)
        self._mark_dirty()

    def _duplicate_current_scene(self) -> None:
        """Duplicate the current scene with all widgets."""
        from dataclasses import asdict

        cur = self.designer.current_scene
        src = self.designer.scenes.get(cur)
        if src is None:
            self._set_status("No scene to duplicate.", ttl_sec=2.0)
            return
        names = list(self.designer.scenes.keys())
        base = f"{cur}_copy"
        idx = 1
        name = base
        while name in names:
            idx += 1
            name = f"{base}_{idx}"
        # Deep-copy widgets
        new_widgets = []
        for w in src.widgets:
            try:
                new_widgets.append(WidgetConfig(**asdict(w)))
            except Exception:
                continue
        new_sc = SceneConfig(
            name=name,
            width=src.width,
            height=src.height,
            widgets=new_widgets,
            bg_color=src.bg_color,
            theme=src.theme,
        )
        self.designer.scenes[name] = new_sc
        self.designer.current_scene = name
        self.state.selected = []
        self.state.selected_idx = None
        self.designer.selected_widget = None
        self._set_status(f"Duplicated scene: {name}", ttl_sec=2.0)
        self._mark_dirty()

    def _rename_current_scene(self) -> None:
        """Start inline editing to rename the current scene."""
        self.state.inspector_selected_field = "_scene_name"
        self.state.inspector_input_buffer = str(self.designer.current_scene or "")
        try:
            pygame.key.start_text_input()
        except Exception:
            pass
        self._set_status("Rename scene (Enter=apply Esc=cancel)", ttl_sec=4.0)

    def _export_c_header(self) -> None:
        """Quick-export current JSON to a C header."""
        from pathlib import Path

        json_path = getattr(self, "json_path", None)
        if json_path is None:
            self._set_status("Export: no JSON file loaded.", ttl_sec=2.0)
            return
        json_path = Path(json_path)
        if not json_path.exists():
            self._set_status("Export: JSON file not found.", ttl_sec=2.0)
            return
        try:
            import sys
            repo_root = json_path.resolve().parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from tools.ui_codegen import generate_scenes_header
        except ImportError:
            self._set_status("Export: ui_codegen not found.", ttl_sec=3.0)
            return
        # Save first so export reflects current state
        try:
            self.save_json()
        except Exception:
            pass
        out_dir = json_path.parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "ui_design_export.h"
        try:
            from datetime import datetime
            guard = "UI_DESIGN_EXPORT_H"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text = generate_scenes_header(
                json_path, guard=guard,
                source_name=json_path.name, generated_ts=ts,
            )
            out_path.write_text(text, encoding="utf-8", newline="\n")
            self._set_status(f"Exported: {out_path.name}", ttl_sec=3.0)
        except Exception as exc:
            self._set_status(f"Export failed: {exc}", ttl_sec=4.0)

    def _add_widget(self, kind: str):
        """Add widget to scene."""
        sc = self.state.current_scene()
        try:
            self.designer._save_state()
        except Exception:
            pass
        kind = str(kind or "").lower()
        defaults: Dict[str, Dict[str, object]] = {
            "label": {
                "width": 90,
                "height": 16,
                "border": False,
                "align": "left",
                "valign": "middle",
            },
            "button": {
                "width": 88,
                "height": 24,
                "border_style": "rounded",
                "style": "bold",
                "align": "center",
                "valign": "middle",
            },
            "panel": {"width": 160, "height": 96, "text": "", "border_style": "single"},
            "progressbar": {"width": 140, "height": 16, "text": "Progress", "value": 65},
            "gauge": {
                "width": 64,
                "height": 64,
                "text": "Gauge",
                "value": 70,
                "align": "center",
                "valign": "bottom",
            },
            "slider": {"width": 160, "height": 24, "text": "Slider", "value": 40},
            "checkbox": {"width": 140, "height": 16, "text": "Checkbox"},
            "textbox": {
                "width": 160,
                "height": 24,
                "text": "Text",
                "align": "left",
                "valign": "middle",
            },
            "chart": {"width": 200, "height": 120, "text": "Line chart", "border_style": "rounded"},
            "icon": {
                "width": 24,
                "height": 24,
                "text": "",
                "icon_char": "@",
                "border": False,
                "align": "center",
                "valign": "middle",
            },
        }
        cfg = defaults.get(kind, {})
        w = WidgetConfig(
            type=kind,
            x=GRID,
            y=GRID,
            width=int(cfg.get("width", 60)),
            height=int(cfg.get("height", 16)),
            text=str(cfg.get("text", kind.capitalize()) or ""),
            style=str(cfg.get("style", "default") or "default"),
            color_fg=str(cfg.get("color_fg", "white") or "white"),
            color_bg=str(cfg.get("color_bg", "black") or "black"),
            border=bool(cfg.get("border", True)),
            border_style=str(cfg.get("border_style", "single") or "single"),
            align=str(cfg.get("align", "left") or "left"),
            valign=str(cfg.get("valign", "middle") or "middle"),
            value=int(cfg.get("value", 0) or 0),
            min_value=int(cfg.get("min_value", 0) or 0),
            max_value=int(cfg.get("max_value", 100) or 100),
            icon_char=str(cfg.get("icon_char", "") or ""),
        )
        try:
            self._auto_complete_widget(w)
            bx, by = self._find_best_position(w, sc)
            w.x, w.y = int(bx), int(by)
        except Exception:
            pass
        sc.widgets.append(w)
        self.state.selected = [len(sc.widgets) - 1]
        self.state.selected_idx = self.state.selected[0]
        self._mark_dirty()

    def _add_component(self, name: str):
        component_insert.add_component(self, name)

    def _component_blueprints(self, name: str, sc) -> List[Dict[str, object]]:
        """Backward compatible wrapper for older callers."""
        return component_blueprints(str(name or ""), sc)

    def _auto_arrange_grid(self):
        """Auto-arrange widgets in grid."""
        sc = self.state.current_scene()
        x, y = GRID, GRID
        row_h = 0
        for w in sc.widgets:
            if x + w.width > sc.width - GRID:
                x, y = GRID, y + row_h + GRID
                row_h = 0
            w.x, w.y = x, y
            x += w.width + GRID
            row_h = max(row_h, w.height)
        self._mark_dirty()

    def _toggle_clean_preview(self) -> None:
        """Toggle clean preview mode — shows only the scene with no UI chrome."""
        self.clean_preview = not self.clean_preview
        if self.clean_preview:
            self._saved_show_grid = self.show_grid
            self._saved_panels_collapsed = self.panels_collapsed
            self.show_grid = False
            if not self.panels_collapsed:
                self._toggle_panels()
            self.state.selected = []
            self.state.selected_idx = None
            self._set_status("Preview ON (F9=exit)", ttl_sec=2.0)
        else:
            self.show_grid = getattr(self, "_saved_show_grid", True)
            if getattr(self, "_saved_panels_collapsed", False) != self.panels_collapsed:
                self._toggle_panels()
            self._set_status("Preview OFF", ttl_sec=1.5)
        self._mark_dirty()

    def _goto_widget_prompt(self) -> None:
        """Open inline input to jump to a widget by index."""
        self.state.inspector_selected_field = "_goto_widget"
        self.state.inspector_input_buffer = ""
        try:
            pygame.key.start_text_input()
        except Exception:
            pass
        self._set_status("Go to widget # (Enter=jump Esc=cancel)", ttl_sec=4.0)

    def _toggle_panels(self):
        """Toggle panels visibility."""
        self.panels_collapsed = not self.panels_collapsed
        win_size = None
        try:
            win_size = self.window.get_size() if self.window else None
        except Exception:
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
        except Exception:
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
