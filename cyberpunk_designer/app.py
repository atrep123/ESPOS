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
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from event_manager import EventManager
from ui_designer import HARDWARE_PROFILES, UIDesigner, WidgetConfig
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
        self.status_h = 18
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
        self._force_full_redraw: bool = False
        self._restored_from_autosave = False
        self.snap_enabled = True
        self.show_grid = True
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
        if start_max and not is_dummy:
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

        # Palette buttons (add widget)
        self.palette_actions = [
            ("Add Label", lambda: self._add_widget("label")),
            ("Add Button", lambda: self._add_widget("button")),
            ("Add Panel", lambda: self._add_widget("panel")),
            ("Add Progress", lambda: self._add_widget("progressbar")),
            ("Add Gauge", lambda: self._add_widget("gauge")),
            ("Add Slider", lambda: self._add_widget("slider")),
            ("Add Checkbox", lambda: self._add_widget("checkbox")),
            ("Add Textbox", lambda: self._add_widget("textbox")),
            ("Add Chart", lambda: self._add_widget("chart")),
            ("Add Icon", lambda: self._add_widget("icon")),
        ]
        self.template_actions = self._build_template_actions()
        self.palette_actions += self.template_actions
        self.color_presets = [
            ("Color: White/Black", lambda: self._apply_color_preset("#f5f5f5", "#000000")),
            ("Color: White/Panel", lambda: self._apply_color_preset("#f5f5f5", "#101010")),
            ("Color: Light Gray/Dark", lambda: self._apply_color_preset("#e0e0e0", "#080808")),
            ("Color: Gray/Dark", lambda: self._apply_color_preset("#b0b0b0", "#080808")),
        ]
        self.palette_actions += self.color_presets
        self.component_actions = [
            ("-- Components --", None),
            ("Component: Dashboard 256x128", lambda: self._add_component("dashboard_256x128")),
            ("-- OS UI --", None),
            ("Component: Status Bar", lambda: self._add_component("status_bar")),
            ("Component: Tabs", lambda: self._add_component("tabs")),
            ("Component: Menu", lambda: self._add_component("menu")),
            ("Component: Menu List (legacy)", lambda: self._add_component("menu_list")),
            ("Component: List", lambda: self._add_component("list")),
            ("Component: List Item", lambda: self._add_component("list_item")),
            ("Component: Setting (int)", lambda: self._add_component("setting_int")),
            ("Component: Setting (bool)", lambda: self._add_component("setting_bool")),
            ("Component: Setting (enum)", lambda: self._add_component("setting_enum")),
            ("Component: Dialog", lambda: self._add_component("dialog")),
            ("Component: Card", lambda: self._add_component("card")),
            ("Component: Notification", lambda: self._add_component("notification")),
            ("Component: Modal", lambda: self._add_component("modal")),
            ("Component: Chart Bar", lambda: self._add_component("chart_bar")),
            ("Component: Chart Line", lambda: self._add_component("chart_line")),
            ("Component: Gauge HUD", lambda: self._add_component("gauge_hud")),
            ("Component: Dialog Confirm", lambda: self._add_component("dialog_confirm")),
            ("Component: Toast", lambda: self._add_component("toast")),
        ]
        self.palette_actions += self.component_actions
        self.layout_actions = [
            ("-- Layout --", None),
            ("Align Left (Ctrl+Alt+Left)", lambda: layout_tools.align_selection(self, "left")),
            ("Align H Center", lambda: layout_tools.align_selection(self, "hcenter")),
            ("Align Right (Ctrl+Alt+Right)", lambda: layout_tools.align_selection(self, "right")),
            ("Align Top (Ctrl+Alt+Up)", lambda: layout_tools.align_selection(self, "top")),
            ("Align V Center", lambda: layout_tools.align_selection(self, "vcenter")),
            ("Align Bottom (Ctrl+Alt+Down)", lambda: layout_tools.align_selection(self, "bottom")),
            ("Distribute H (Ctrl+Alt+H)", lambda: layout_tools.distribute_selection(self, "h")),
            ("Distribute V (Ctrl+Alt+V)", lambda: layout_tools.distribute_selection(self, "v")),
            ("Match Width (Ctrl+Alt+W)", lambda: layout_tools.match_size_selection(self, "width")),
            (
                "Match Height (Ctrl+Alt+T)",
                lambda: layout_tools.match_size_selection(self, "height"),
            ),
            (
                "Center Selection (Ctrl+Alt+C)",
                lambda: layout_tools.center_selection_in_scene(self, "both"),
            ),
        ]
        self.palette_actions += self.layout_actions
        self.profile_actions = [
            ("-- Hardware Profiles --", None),
            (
                "Profile: ESP32 OS 256x128 (4bpp Gray)",
                lambda: self._set_profile("esp32os_256x128_gray4"),
            ),
            ("Profile: ESP32 OS 240x128 (1bpp)", lambda: self._set_profile("esp32os_240x128_mono")),
            (
                "Profile: ESP32 OS 240x128 (RGB565)",
                lambda: self._set_profile("esp32os_240x128_rgb565"),
            ),
            ("Profile: OLED 128x64", lambda: self._set_profile("oled_128x64")),
            ("Profile: TFT 320x240", lambda: self._set_profile("tft_320x240")),
            ("Profile: TFT 480x320", lambda: self._set_profile("tft_480x320")),
        ]
        self.palette_actions += self.profile_actions
        self.preset_actions = self._build_widget_presets_actions()
        self.palette_actions += self.preset_actions

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

    @lru_cache(maxsize=256)
    def _screen_to_logical_cached(self, pos_hash: int) -> Tuple[int, int]:
        """Cached version of coordinate conversion."""
        # Reconstruct position from hash
        x = pos_hash >> 16
        y = pos_hash & 0xFFFF
        return windowing.screen_to_logical(self, x, y)

    def _screen_to_logical(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """Convert screen coords with caching."""
        pos_hash = (pos[0] << 16) | pos[1]
        return self._screen_to_logical_cached(pos_hash)

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
                len(self.state.selected),
                int(bool(self.show_help_overlay)),
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
            self._draw_toolbar()
            self._draw_palette()
            self._draw_canvas()
            self._draw_inspector()
            self._draw_status()

        if self.show_help_overlay:
            drawing.draw_help_overlay(self)

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
        for widget_type, widgets in groups.items():
            # Sort by size for better packing
            widgets.sort(key=lambda w: w.width * w.height, reverse=True)

            for w in widgets:
                # Find best position with least overlap
                best_x, best_y = self._find_best_position(w, sc)
                w.x = best_x
                w.y = best_y

        self._mark_dirty()

    def _find_best_position(self, widget: WidgetConfig, scene) -> Tuple[int, int]:
        """Find optimal position for widget using spatial heuristics."""
        best_score = float("inf")
        best_pos = (GRID, GRID)

        # Try different positions
        for y in range(0, scene.height - widget.height, GRID):
            for x in range(0, scene.width - widget.width, GRID):
                score = self._calculate_position_score(x, y, widget, scene)
                if score < best_score:
                    best_score = score
                    best_pos = (x, y)

        return best_pos

    def _calculate_position_score(self, x: int, y: int, widget: WidgetConfig, scene) -> float:
        """Calculate score for position (lower is better)."""
        score = 0.0

        # Prefer top-left
        score += (x + y) * 0.01

        # Check overlaps
        test_rect = pygame.Rect(x, y, widget.width, widget.height)
        for other in scene.widgets:
            if other == widget:
                continue
            other_rect = pygame.Rect(other.x, other.y, other.width, other.height)
            if test_rect.colliderect(other_rect):
                score += 1000  # Heavy penalty for overlap

        return score

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
            if not name:
                continue
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

    def _panel(self, rect: pygame.Rect, title: str = ""):
        drawing.panel(self, rect, title=title)

    def _button(self, label: str, pos: Tuple[int, int]) -> pygame.Rect:
        """Render a small pixel-style button and return its rect."""
        return drawing.button(self, label, pos)

    def _draw_toolbar(self):
        drawing.draw_toolbar(self)

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
            if not members:
                continue
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
        rows = int(len(self.palette_actions)) + int(len(sc.widgets))
        gap = max(0, int(getattr(self, "pixel_padding", 0) or 0))
        return int(self.pixel_row_height) * rows + gap

    def _inspector_content_height(self) -> int:
        """Calculate inspector content height."""
        rows, _, _ = self._compute_inspector_rows()
        return self.pixel_row_height * max(1, len(rows))

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
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            windowing.handle_video_resize(self, event.w, event.h)
            return
        if event.type == pygame.KEYDOWN:
            self._on_key_down(event)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pointer_down = True
            self.pointer_pos = self._screen_to_logical(event.pos)
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

    def _on_key_down(self, event: pygame.event.Event):
        input_handlers.on_key_down(self, event)

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
        json_path = Path(sys.argv[1])
    app = CyberpunkEditorApp(json_path, (480, 320))
    app.run()


if __name__ == "__main__":
    main()
