#!/usr/bin/env python3
"""
Visual UI Designer for ESP32 Simulator
Drag-and-drop widget editor with live preview and code generation
"""

import copy
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union, cast

from constants import BACKUP_DIR, GRID_SIZE_MEDIUM
from design_tokens import color_hex
from ui_models import (
    BorderStyle,
    ConstraintBaseline,
    Constraints,
    Scene,
    SceneConfig,
    SceneConfigDict,
    WidgetConfig,
    WidgetType,
    coerce_bool_flag,
    coerce_choice,
    empty_constraints,
    make_baseline,
    normalize_int_list,
    normalize_str_list,
)


class WidgetValidationError(Exception):
    """Raised when widget or scene data fails validation."""


class SceneLoadError(Exception):
    """Raised when a scene JSON cannot be loaded or parsed."""


# CLI message constants
MSG_INVALID_INDEX = "Invalid index"
MSG_NO_SCENE = "No scene loaded"
MSG_INDEX_INTEGER = "Index must be integer"
MSG_FAILED = "Failed"
MSG_UNKNOWN_ANIM = "Unknown animation name"


# Hardware profiles for common ESP32 displays
class HardwareProfile(TypedDict):
    label: str
    width: int
    height: int
    color_depth: int
    max_fb_kb: float
    max_flash_kb: float


HARDWARE_PROFILES: Dict[str, HardwareProfile] = {
    # ── Tiny monochrome OLEDs (SSD1306 / SH1106) ──
    "oled_128x64": {
        "label": "OLED 128x64 (1bpp, SSD1306)",
        "width": 128,
        "height": 64,
        "color_depth": 1,
        "max_fb_kb": 2.0,
        "max_flash_kb": 32.0,
    },
    "oled_128x32": {
        "label": "OLED 128x32 (1bpp, SSD1306)",
        "width": 128,
        "height": 32,
        "color_depth": 1,
        "max_fb_kb": 1.0,
        "max_flash_kb": 32.0,
    },
    "oled_72x40": {
        "label": "OLED 72x40 (1bpp, SSD1306)",
        "width": 72,
        "height": 40,
        "color_depth": 1,
        "max_fb_kb": 0.5,
        "max_flash_kb": 16.0,
    },
    # ── Medium monochrome OLEDs (SH1107 / SSD1309) ──
    "oled_128x128_sh1107": {
        "label": "OLED 128x128 (1bpp, SH1107)",
        "width": 128,
        "height": 128,
        "color_depth": 1,
        "max_fb_kb": 4.0,
        "max_flash_kb": 64.0,
    },
    "oled_256x64_ssd1322": {
        "label": "OLED 256x64 (4bpp, SSD1322)",
        "width": 256,
        "height": 64,
        "color_depth": 4,
        "max_fb_kb": 16.0,
        "max_flash_kb": 128.0,
    },
    # ── Project main target ──
    "esp32os_256x128_gray4": {
        "label": "ESP32 OS 256x128 (4bpp Gray, SSD1363)",
        "width": 256,
        "height": 128,
        "color_depth": 4,
        "max_fb_kb": 32.0,
        "max_flash_kb": 256.0,
    },
    "esp32os_240x128_mono": {
        "label": "ESP32 OS 240x128 (1bpp)",
        "width": 240,
        "height": 128,
        "color_depth": 1,
        "max_fb_kb": 8.0,
        "max_flash_kb": 256.0,
    },
    "esp32os_240x128_rgb565": {
        "label": "ESP32 OS 240x128 (16bpp RGB565)",
        "width": 240,
        "height": 128,
        "color_depth": 16,
        "max_fb_kb": 128.0,
        "max_flash_kb": 512.0,
    },
    # ── Small color TFTs (ST7735) ──
    "tft_160x128_st7735": {
        "label": "TFT 160x128 (16bpp, ST7735)",
        "width": 160,
        "height": 128,
        "color_depth": 16,
        "max_fb_kb": 40.0,
        "max_flash_kb": 128.0,
    },
    "tft_160x80_st7735": {
        "label": "TFT 160x80 (16bpp, ST7735)",
        "width": 160,
        "height": 80,
        "color_depth": 16,
        "max_fb_kb": 25.0,
        "max_flash_kb": 64.0,
    },
    # ── Medium color TFTs (ST7789 / ILI9341) ──
    "tft_240x135_st7789": {
        "label": "TFT 240x135 (16bpp, ST7789)",
        "width": 240,
        "height": 135,
        "color_depth": 16,
        "max_fb_kb": 64.0,
        "max_flash_kb": 256.0,
    },
    "tft_240x240_st7789": {
        "label": "TFT 240x240 (16bpp, ST7789)",
        "width": 240,
        "height": 240,
        "color_depth": 16,
        "max_fb_kb": 115.0,
        "max_flash_kb": 256.0,
    },
    "tft_320x240": {
        "label": "TFT 320x240 (16bpp, ILI9341)",
        "width": 320,
        "height": 240,
        "color_depth": 16,
        "max_fb_kb": 200.0,
        "max_flash_kb": 256.0,
    },
    # ── Large color TFTs (ILI9488 / ST7796) ──
    "tft_480x320": {
        "label": "TFT 480x320 (16bpp, ILI9488)",
        "width": 480,
        "height": 320,
        "color_depth": 16,
        "max_fb_kb": 320.0,
        "max_flash_kb": 512.0,
    },
}

logger = logging.getLogger(__name__)


def _safe_int(value: Optional[int]) -> int:
    return int(value) if value is not None else 0


def _clamp_int(value: Optional[int], minimum: int = 0, maximum: Optional[int] = None) -> int:
    """Clamp potentially-optional ints to a bounded range."""
    try:
        v = int(value) if value is not None else minimum
    except (ValueError, TypeError):
        v = minimum
    if maximum is not None:
        v = min(v, maximum)
    return max(minimum, v)


def _widget_dims(widget: WidgetConfig) -> Tuple[int, int]:
    """Return safe (width, height) with minimum of 1."""
    w = getattr(widget, "width", 1)
    h = getattr(widget, "height", 1)
    return max(1, int(w or 1)), max(1, int(h or 1))


class UIDesigner:
    """Visual UI designer with layout editor"""

    _last_loaded_json: Optional[str] = None
    _json_watch_mtime: Optional[float] = None

    def __init__(self, width: int = 128, height: int = 64):
        self.width = width
        self.height = height
        self.scenes: Dict[str, SceneConfig] = {}
        self.current_scene: Optional[str] = None
        self.selected_widget: Optional[int] = None
        self._last_loaded_json: Optional[str] = None
        self._json_watch_mtime: Optional[float] = None

        # Undo/redo stacks
        self.undo_stack: List[str] = []  # JSON snapshots
        self.redo_stack: List[str] = []
        self.max_undo = 50

        # Templates
        self.templates: Dict[str, WidgetConfig] = self._create_default_templates()

        # Grid settings (align with preview defaults)
        self.grid_enabled = True
        self.grid_size = GRID_SIZE_MEDIUM
        self.snap_to_grid = True
        # Magnetic snapping settings
        self.snap_edges = True
        self.snap_centers = True
        self.snap_tolerance = 3
        self.snap_fluid = True  # fluid mode ignores strict grid when snapping
        self.show_guides = True
        self.last_guides: List[Dict[str, Any]] = []
        self._update_snap_tolerance()

        # Named checkpoints (in-memory) for quick diff/rollback
        self.checkpoints: Dict[str, Dict[str, Any]] = {}

        # Groups and Symbols
        self.groups: Dict[str, List[int]] = {}
        self.symbols: Dict[str, Dict[str, Any]] = {}

        # Grid columns (affects grid size helper)
        self.grid_columns = 8

        # Theme presets
        self.themes: Dict[str, Dict[str, str]] = {
            "default": {
                "bg": color_hex("theme_default_bg"),
                "text": color_hex("theme_default_text"),
                "primary": color_hex("theme_default_primary"),
                "secondary": color_hex("theme_default_secondary"),
                "accent": color_hex("theme_default_accent"),
                "danger": color_hex("theme_default_danger"),
            },
            "dark": {
                "bg": color_hex("theme_dark_bg"),
                "text": color_hex("theme_dark_text"),
                "primary": color_hex("theme_dark_primary"),
                "secondary": color_hex("theme_dark_secondary"),
                "accent": color_hex("theme_dark_accent"),
                "danger": color_hex("theme_dark_danger"),
            },
            "pixel_dark": {
                "bg": "#05060a",
                "text": "#f4f4f4",
                "primary": "#00ffc8",
                "secondary": "#1b2228",
                "accent": "#ffcc33",
                "danger": "#ff3355",
            },
            "pixelhud": {
                "bg": "#000000",
                "text": "#ffffff",
                "primary": "#00ffaa",
                "secondary": "#202020",
                "accent": "#ffff55",
                "danger": "#ff3355",
            },
        }
        self.theme_contrast_min = 4.5

        # Animation preview context
        self.anim_context: Optional[Dict[str, Any]] = None
        self.hardware_profile: Optional[str] = None

    def _create_default_templates(self) -> Dict[str, WidgetConfig]:
        """Create default widget templates"""
        return {
            "title_label": WidgetConfig(
                type="label",
                x=0,
                y=0,
                width=128,
                height=10,
                text="Title",
                align="center",
                style="bold",
                border=False,
                color_fg="cyan",
            ),
            "button_primary": WidgetConfig(
                type="button",
                x=0,
                y=0,
                width=40,
                height=12,
                text="OK",
                align="center",
                border=True,
                border_style="rounded",
                color_fg="black",
                color_bg="green",
            ),
            "button_secondary": WidgetConfig(
                type="button",
                x=0,
                y=0,
                width=40,
                height=12,
                text="Cancel",
                align="center",
                border=True,
                border_style="rounded",
                color_fg="white",
                color_bg="red",
            ),
            "info_panel": WidgetConfig(
                type="panel",
                x=0,
                y=0,
                width=120,
                height=50,
                border=True,
                border_style="double",
                color_fg="white",
                color_bg="blue",
            ),
            "progress_bar": WidgetConfig(
                type="progressbar",
                x=0,
                y=0,
                width=100,
                height=8,
                value=50,
                min_value=0,
                max_value=100,
                border=True,
                color_fg="green",
                color_bg="black",
            ),
            "hud_title": WidgetConfig(
                type="label",
                x=0,
                y=0,
                width=128,
                height=10,
                text="CORE CONTROL",
                align="center",
                style="bold",
                border=False,
                color_fg="cyan",
            ),
            "hud_progress_segmented": WidgetConfig(
                type="progressbar",
                x=0,
                y=0,
                width=100,
                height=8,
                value=40,
                min_value=0,
                max_value=100,
                border=True,
                border_style="single",
                color_fg="green",
                color_bg="black",
                style="segmented",
            ),
            "hud_stat_label": WidgetConfig(
                type="label",
                x=0,
                y=0,
                width=40,
                height=8,
                text="PWR: 084%",
                align="left",
                border=False,
                style="default",
                color_fg="white",
            ),
            "gauge_half": WidgetConfig(
                type="gauge",
                x=0,
                y=0,
                width=40,
                height=20,
                value=75,
                min_value=0,
                max_value=100,
                border=True,
                color_fg="yellow",
            ),
        }

    def _save_state(self):
        """Save current state for undo"""
        if not (self.current_scene and self.current_scene in self.scenes):
            return
        scene_obj = self.scenes[self.current_scene]
        payload = asdict(scene_obj)
        state = json.dumps(payload)
        self._push_undo_state(state)
        self._record_history_meta(payload)
        self._write_backup_snapshot(state)

    def _push_undo_state(self, state: str) -> None:
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _record_history_meta(self, payload: Dict[str, Any]) -> None:
        try:
            if not hasattr(self, "_history_meta"):
                self._history_meta = []  # parallel to undo_stack indices
            diff_summary = {
                "widgets": len(payload.get("widgets", [])),
                "name": payload.get("name"),
                "ts": datetime.now().isoformat(timespec="seconds"),
            }
            self._history_meta.append(diff_summary)
            if len(self._history_meta) > self.max_undo:
                self._history_meta.pop(0)
        except (AttributeError, TypeError):
            pass

    def _write_backup_snapshot(self, state: str) -> None:
        try:
            backup_dir = BACKUP_DIR
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            scene_name = (self.current_scene or "scene").replace(" ", "_")
            snap_path = backup_dir / f"{scene_name}_{ts}.json"
            with open(snap_path, "w", encoding="utf-8") as f:
                f.write(state)
        except OSError:
            pass

    def undo(self) -> bool:
        """Undo last operation"""
        if not self.undo_stack or not self.current_scene:
            return False

        # Save current state to redo
        current_state = json.dumps(asdict(self.scenes[self.current_scene]))
        self.redo_stack.append(current_state)
        # Move meta entry to redo_meta for potential redo preview
        if hasattr(self, "_history_meta"):
            if not hasattr(self, "_redo_meta"):
                self._redo_meta = []
            if self._history_meta:
                self._redo_meta.append(self._history_meta.pop())

        # Restore previous state
        prev_state = json.loads(self.undo_stack.pop())
        widgets = [WidgetConfig(**w) for w in prev_state["widgets"]]
        self.scenes[self.current_scene] = SceneConfig(
            name=prev_state["name"],
            width=prev_state["width"],
            height=prev_state["height"],
            widgets=widgets,
            bg_color=prev_state.get("bg_color", "black"),
        )
        return True

    def redo(self) -> bool:
        """Redo last undone operation"""
        if not self.redo_stack or not self.current_scene:
            return False

        # Save current state to undo
        current_state = json.dumps(asdict(self.scenes[self.current_scene]))
        self.undo_stack.append(current_state)
        if hasattr(self, "_redo_meta") and self._redo_meta:
            if not hasattr(self, "_history_meta"):
                self._history_meta = []
            # Restore meta back to history
            self._history_meta.append(self._redo_meta.pop())

        # Restore next state
        next_state = json.loads(self.redo_stack.pop())
        widgets = [WidgetConfig(**w) for w in next_state["widgets"]]
        self.scenes[self.current_scene] = SceneConfig(
            name=next_state["name"],
            width=next_state["width"],
            height=next_state["height"],
            widgets=widgets,
            bg_color=next_state.get("bg_color", "black"),
        )
        return True

    def list_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Return recent undo history metadata (most recent last).

        Each entry contains: index, scene name, widget count, timestamp.
        Does not deserialize full states (keeps operation lightweight).
        """
        if not hasattr(self, "_history_meta"):
            return []
        items = self._history_meta[-limit:]
        start_index = len(self._history_meta) - len(items)
        return [
            {
                "i": start_index + idx,
                "scene": meta.get("name"),
                "widgets": meta.get("widgets"),
                "ts": meta.get("ts"),
            }
            for idx, meta in enumerate(items)
        ]

    def history_snapshot(self, index: int) -> Optional[Dict[str, Any]]:
        """Return deserialized snapshot of a given history index (without altering stacks)."""
        if index < 0 or index >= len(self.undo_stack):
            return None
        try:
            data = json.loads(self.undo_stack[index])
            return data
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def snap_position(self, x: int, y: int) -> Tuple[int, int]:
        """Snap coordinates to the active grid if enabled.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Tuple of snapped (x, y) integers.
        """
        if self.snap_to_grid and self.grid_enabled:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size
        return x, y

    def _apply_snapping(
        self, widget: WidgetConfig, x: int, y: int, scene: SceneConfig
    ) -> Tuple[int, int]:
        """Apply magnetic snapping to edges and centers within tolerance. Records guides."""
        self.last_guides = []
        if not (self.snap_edges or self.snap_centers):
            return x, y
        if not self.snap_fluid:
            x, y = self.snap_position(x, y)
        bounds = self._widget_bounds(widget, x, y)
        best_dx, best_dy, best_vline, best_hline = self._find_best_snaps(widget, scene, bounds)
        x, y = self._apply_best_offset(x, y, scene, best_dx, best_dy, best_vline, best_hline)
        if self.snap_to_grid and not self.snap_fluid:
            x, y = self.snap_position(x, y)
        return self._clamp_to_scene(x, y, widget, scene)

    def _widget_bounds(self, widget: WidgetConfig, x: int, y: int) -> Dict[str, int]:
        w, h = _widget_dims(widget)
        return {
            "left": x,
            "right": x + w,
            "top": y,
            "bottom": y + h,
            "cx": x + w // 2,
            "cy": y + h // 2,
        }

    def _find_best_snaps(
        self,
        widget: WidgetConfig,
        scene: SceneConfig,
        bounds: Dict[str, int],
    ) -> Tuple[
        Optional[int],
        Optional[int],
        Optional[Tuple[int, int, int, str]],
        Optional[Tuple[int, int, int, str]],
    ]:
        best_dx = None
        best_dy = None
        best_vline: Optional[Tuple[int, int, int, str]] = None
        best_hline: Optional[Tuple[int, int, int, str]] = None
        for other in scene.widgets:
            if other is widget:
                continue
            other_bounds = self._widget_bounds(other, other.x, other.y)
            best_dx, best_vline = self._best_for_axis(
                bounds, other_bounds, best_dx, best_vline, axis="x"
            )
            best_dy, best_hline = self._best_for_axis(
                bounds, other_bounds, best_dy, best_hline, axis="y"
            )
        return best_dx, best_dy, best_vline, best_hline

    def _best_for_axis(
        self,
        subject: Dict[str, int],
        other: Dict[str, int],
        best_delta: Optional[int],
        best_line: Optional[Tuple[int, int, int, str]],
        axis: str,
    ) -> Tuple[Optional[int], Optional[Tuple[int, int, int, str]]]:
        candidates = self._axis_candidates(subject, other, axis)
        for delta, line in candidates:
            if abs(delta) <= self.snap_tolerance:
                if best_delta is None or abs(delta) < abs(best_delta):
                    best_delta = delta
                    best_line = line
        return best_delta, best_line

    def _axis_candidates(
        self,
        subject: Dict[str, int],
        other: Dict[str, int],
        axis: str,
    ) -> List[Tuple[int, Tuple[int, int, int, str]]]:
        if axis == "x":
            return self._axis_candidates_x(subject, other)
        return self._axis_candidates_y(subject, other)

    def _axis_candidates_x(
        self, s: Dict[str, int], o: Dict[str, int]
    ) -> List[Tuple[int, Tuple[int, int, int, str]]]:
        candidates: List[Tuple[int, Tuple[int, int, int, str]]] = []
        if self.snap_edges:
            candidates += [
                (
                    o["left"] - s["left"],
                    (o["left"], min(s["top"], o["top"]), max(s["bottom"], o["bottom"]), "L"),
                ),
                (
                    o["right"] - s["right"],
                    (o["right"], min(s["top"], o["top"]), max(s["bottom"], o["bottom"]), "R"),
                ),
            ]
        if self.snap_centers:
            candidates.append(
                (
                    o["cx"] - s["cx"],
                    (o["cx"], min(s["top"], o["top"]), max(s["bottom"], o["bottom"]), "C"),
                )
            )
        return candidates

    def _axis_candidates_y(
        self, s: Dict[str, int], o: Dict[str, int]
    ) -> List[Tuple[int, Tuple[int, int, int, str]]]:
        candidates: List[Tuple[int, Tuple[int, int, int, str]]] = []
        if self.snap_edges:
            candidates += [
                (
                    o["top"] - s["top"],
                    (o["top"], min(s["left"], o["left"]), max(s["right"], o["right"]), "T"),
                ),
                (
                    o["bottom"] - s["bottom"],
                    (o["bottom"], min(s["left"], o["left"]), max(s["right"], o["right"]), "B"),
                ),
            ]
        if self.snap_centers:
            candidates.append(
                (
                    o["cy"] - s["cy"],
                    (o["cy"], min(s["left"], o["left"]), max(s["right"], o["right"]), "C"),
                )
            )
        return candidates

    def _apply_best_offset(
        self,
        x: int,
        y: int,
        scene: SceneConfig,
        best_dx: Optional[int],
        best_dy: Optional[int],
        best_vline: Optional[Tuple[int, int, int, str]],
        best_hline: Optional[Tuple[int, int, int, str]],
    ) -> Tuple[int, int]:
        if best_dx is not None:
            x += best_dx
            if best_vline is not None:
                self._record_vertical_guide(best_vline, scene)
        if best_dy is not None:
            y += best_dy
            if best_hline is not None:
                self._record_horizontal_guide(best_hline, scene)
        return x, y

    def _record_vertical_guide(self, guide: Tuple[int, int, int, str], scene: SceneConfig) -> None:
        vx, vy1, vy2, k = guide
        self.last_guides.append(
            {
                "type": "v",
                "x": vx,
                "y1": max(0, vy1),
                "y2": min(scene.height - 1, vy2),
                "k": k,
            }
        )

    def _record_horizontal_guide(
        self, guide: Tuple[int, int, int, str], scene: SceneConfig
    ) -> None:
        hy, hx1, hx2, k = guide
        self.last_guides.append(
            {
                "type": "h",
                "y": hy,
                "x1": max(0, _safe_int(hx1)),
                "x2": min(scene.width - 1, _safe_int(hx2)),
                "k": k,
            }
        )

    def _clamp_to_scene(
        self, x: int, y: int, widget: WidgetConfig, scene: SceneConfig
    ) -> Tuple[int, int]:
        w, h = _widget_dims(widget)
        x = max(0, min(scene.width - w, x))
        y = max(0, min(scene.height - h, y))
        return x, y

    def _update_snap_tolerance(self):
        """Tighten snap tolerance based on grid size for more accurate snapping."""
        self.snap_tolerance = max(1, min(3, self.grid_size // 2 if self.grid_size else 3))

    @property
    def snap_to_grid(self) -> bool:  # type: ignore[override]
        return getattr(self, "_snap_to_grid", False)

    @snap_to_grid.setter
    def snap_to_grid(self, value: Any) -> None:  # type: ignore[override]
        if value is None:
            self._snap_to_grid = False
            return
        if isinstance(value, bool):
            self._snap_to_grid = value
            return
        try:
            self._snap_to_grid = bool(int(value))
        except (ValueError, TypeError):
            self._snap_to_grid = bool(value)

    def create_scene(self, name: str) -> SceneConfig:
        """Create a new scene and register it as current.

        Args:
            name: Scene identifier.

        Returns:
            The created SceneConfig instance.
        """
        scene = SceneConfig(name=name, width=self.width, height=self.height, widgets=[])
        # Apply pixel HUD theme if available so new scenes start in the neon palette.
        for candidate in ("pixelhud", "pixel_dark"):
            if candidate in self.themes:
                roles = self.themes[candidate]
                scene.theme = candidate
                scene.bg_color = roles.get("bg", scene.bg_color)
                scene.grid_size = self.grid_size  # type: ignore[attr-defined]
                break
        self.scenes[name] = scene
        self.current_scene = name
        return scene

    # --- Hardware profiles and resource estimation ---
    def set_hardware_profile(self, profile_key: str) -> Optional["HardwareProfile"]:
        """Assign hardware profile (width/height/color depth) for new scenes and estimation.

        Args:
            profile_key: Key from HARDWARE_PROFILES.

        Returns:
            The applied profile dict, or None if the key is unknown.
        """
        if profile_key not in HARDWARE_PROFILES:
            return None
        profile = HARDWARE_PROFILES[profile_key]
        self.hardware_profile = profile_key
        self.width = profile["width"]
        self.height = profile["height"]
        if self.current_scene and self.current_scene in self.scenes:
            sc = self.scenes[self.current_scene]
            sc.width = profile["width"]
            sc.height = profile["height"]
        return profile

    def estimate_resources(
        self,
        scene_name: Optional[str] = None,
        profile: Optional[str] = None,
        color_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Estimate framebuffer RAM and a rough flash footprint for the current scene.

        - framebuffer assumes color_depth bits per pixel (1bpp OLED or 16bpp TFT).
        - flash estimate is a simple heuristic based on widget count and text length.

        Args:
            scene_name: Optional scene key; defaults to current.
            profile: Optional hardware profile key; defaults to active profile.
            color_depth: Optional override for bits-per-pixel.

        Returns:
            Mapping of framebuffer/flash sizes and over-limit flags; empty if no scene.
        """
        sc = self._resolve_scene(scene_name)
        if not sc:
            return {}
        prof = self._resolve_profile_limits(profile or self.hardware_profile)
        depth = self._resolve_color_depth(color_depth, prof)
        area = max(1, sc.width * sc.height)
        fb_bytes = self._framebuffer_bytes(area, depth)
        text_bytes = self._text_bytes(sc.widgets)
        widget_bytes = 128 * len(sc.widgets)
        flash_bytes = widget_bytes + text_bytes
        overlaps = self._count_overlaps(sc)
        max_fb_kb = prof["max_fb_kb"] if prof else 0.0
        max_flash_kb = prof["max_flash_kb"] if prof else 0.0
        fb_over = self._over_limit(fb_bytes, max_fb_kb)
        flash_over = self._over_limit(flash_bytes, max_flash_kb)
        # Include profile key for tests expecting the active profile identifier.
        return {
            "framebuffer_bytes": float(fb_bytes),
            "framebuffer_kb": fb_bytes / 1024.0,
            "flash_bytes": float(flash_bytes),
            "flash_kb": flash_bytes / 1024.0,
            "color_depth": float(depth),
            "area": float(area),
            "widgets": float(len(sc.widgets)),
            "fb_over": float(1.0 if fb_over else 0.0),
            "flash_over": float(1.0 if flash_over else 0.0),
            "max_fb_kb": float(max_fb_kb),
            "max_flash_kb": float(max_flash_kb),
            "text_bytes": float(text_bytes),
            "widget_bytes": float(widget_bytes),
            "overlaps": float(overlaps),
            "overlap_pairs": float(overlaps),
            "profile": str(profile or self.hardware_profile or ""),
        }

    def _resolve_color_depth(
        self, override: Optional[int], profile: Optional[HardwareProfile]
    ) -> int:
        if override is not None:
            return int(override)
        if profile:
            return int(profile.get("color_depth", 1) or 1)
        return 1

    def _framebuffer_bytes(self, area: int, depth: int) -> int:
        if depth <= 1:
            return (area + 7) // 8
        return int(area * (depth / 8.0))

    def _text_bytes(self, widgets: List[WidgetConfig]) -> int:
        return sum(len(getattr(wi, "text", "") or "") for wi in widgets)

    def _over_limit(self, bytes_val: int, limit_kb: float) -> bool:
        return bool(limit_kb and (bytes_val / 1024.0) > limit_kb)

    def _count_overlaps(self, sc: SceneConfig) -> int:
        """Count how many widget pairs overlap (rough heuristic)."""
        count = 0
        for i, a in enumerate(sc.widgets):
            aw, ah = _widget_dims(a)
            ar = (a.x, a.y, a.x + aw, a.y + ah)
            for b in sc.widgets[i + 1 :]:
                bw, bh = _widget_dims(b)
                br = (b.x, b.y, b.x + bw, b.y + bh)
                if ar[0] < br[2] and ar[2] > br[0] and ar[1] < br[3] and ar[3] > br[1]:
                    count += 1
        return count

    def _resolve_profile_limits(self, profile_key: Optional[str]) -> Optional[HardwareProfile]:
        if not profile_key:
            return None
        prof = HARDWARE_PROFILES.get(profile_key)
        if not prof:
            return None
        try:
            max_fb = float(prof.get("max_fb_kb", 0) or 0)
        except (ValueError, TypeError):
            max_fb = 0.0
        try:
            max_flash = float(prof.get("max_flash_kb", 0) or 0)
        except (ValueError, TypeError):
            max_flash = 0.0
        return cast(
            HardwareProfile,
            {
                "label": str(prof.get("label", "")),
                "width": int(prof.get("width", 0)),
                "height": int(prof.get("height", 0)),
                "color_depth": int(prof.get("color_depth", 1)),
                "max_fb_kb": max(0.0, max_fb),
                "max_flash_kb": max(0.0, max_flash),
            },
        )

    # --- Responsive helpers ---
    def set_responsive_base(self, scene_name: Optional[str] = None):
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        sc = self.scenes[scene_name]
        sc.base_width, sc.base_height = sc.width, sc.height

        # Store baseline into widget.constraints.b for later use
        for w in sc.widgets:
            b = self._baseline_for_widget(w, sc)
            w.constraints = w.constraints or empty_constraints()
            w.constraints["b"] = b
            self._set_default_constraints(w)

    def _baseline_for_widget(self, widget: WidgetConfig, scene: SceneConfig) -> ConstraintBaseline:
        return make_baseline(
            widget.x,
            widget.y,
            widget.width,
            widget.height,
            scene.base_width,
            scene.base_height,
        )

    def _set_default_constraints(self, widget: WidgetConfig) -> None:
        widget.constraints.setdefault("ax", "left")
        widget.constraints.setdefault("ay", "top")
        widget.constraints.setdefault("sx", False)
        widget.constraints.setdefault("sy", False)
        widget.constraints.setdefault("mx", 0)
        widget.constraints.setdefault("my", 0)
        widget.constraints.setdefault("mr", 0)
        widget.constraints.setdefault("mb", 0)

    def apply_responsive(self, scene_name: Optional[str] = None):
        sc = self._resolve_scene(scene_name)
        if not sc:
            return
        bw, bh = self._responsive_base_dims(sc)
        if bw <= 0 or bh <= 0:
            return
        dw, dh = sc.width - bw, sc.height - bh
        sx_ratio = sc.width / bw
        sy_ratio = sc.height / bh
        for w in sc.widgets:
            c = w.constraints or empty_constraints()
            baseline = self._responsive_baseline(w, c, bw, bh)
            nx, ny, scale_x, scale_y = self._responsive_position(c, baseline, dw, dh)
            nw, nh = self._responsive_size(baseline, scale_x, scale_y, sx_ratio, sy_ratio)
            w.x, w.y, w.width, w.height = self._clamp_responsive(sc, nx, ny, nw, nh)

    def _resolve_scene(self, scene_name: Optional[str]) -> Optional[SceneConfig]:
        scene_key = scene_name or self.current_scene
        if not scene_key:
            return None
        return self.scenes.get(scene_key)

    def _responsive_base_dims(self, sc: SceneConfig) -> Tuple[int, int]:
        return sc.base_width or sc.width, sc.base_height or sc.height

    def _responsive_baseline(
        self, w: WidgetConfig, c: Constraints, bw: int, bh: int
    ) -> ConstraintBaseline:
        return c.get("b") or make_baseline(w.x, w.y, w.width, w.height, bw, bh)

    def _responsive_position(
        self,
        c: Constraints,
        b: ConstraintBaseline,
        dw: int,
        dh: int,
    ) -> Tuple[int, int, bool, bool]:
        ax = c.get("ax", "left")
        ay = c.get("ay", "top")
        scale_x = bool(c.get("sx", False))
        scale_y = bool(c.get("sy", False))
        bx = b.get("x", 0)
        by = b.get("y", 0)

        nx, scale_x = self._align_axis(bx, dw, ax, scale_x)
        ny, scale_y = self._align_axis(by, dh, ay, scale_y)
        return nx, ny, scale_x, scale_y

    def _align_axis(
        self, base: int, delta: int, anchor: str, scale_state: bool
    ) -> Tuple[int, bool]:
        if anchor in ("left", "top"):
            return base, scale_state
        if anchor in ("right", "bottom"):
            return base + delta, scale_state
        if anchor in ("center", "middle"):
            return int(base + delta / 2), scale_state
        if anchor == "stretch":
            return base, True
        return base, scale_state

    def _responsive_size(
        self,
        b: ConstraintBaseline,
        scale_x: bool,
        scale_y: bool,
        sx_ratio: float,
        sy_ratio: float,
    ) -> Tuple[int, int]:
        bwid = b.get("width", 0)
        bhgt = b.get("height", 0)
        nw = int(bwid * sx_ratio) if scale_x else bwid
        nh = int(bhgt * sy_ratio) if scale_y else bhgt
        return nw, nh

    def _clamp_responsive(
        self, sc: SceneConfig, x: int, y: int, w: int, h: int
    ) -> Tuple[int, int, int, int]:
        x = max(0, min(sc.width - 1, x))
        y = max(0, min(sc.height - 1, y))
        w = max(1, min(sc.width, w))
        h = max(1, min(sc.height, h))
        return x, y, w, h

    def set_grid_columns(self, n: int):
        if n in (4, 8, 12):
            self.grid_columns = n
            if self.current_scene and self.current_scene in self.scenes:
                sc = self.scenes[self.current_scene]
                self.grid_size = max(1, sc.width // n)
                self._update_snap_tolerance()
        self._update_snap_tolerance()

    def enable_pixel_art_mode(self) -> None:
        """Configure grid/snapping and theme for pixel-art HUD workflows."""
        self.grid_enabled = True
        self.grid_size = 8
        self.snap_to_grid = True
        self.snap_fluid = False
        self.snap_tolerance = 1
        self.set_grid_columns(8)
        # Re-assert 8px grid after column helper adjusts it
        self.grid_size = 8
        self._update_snap_tolerance()

        if self.current_scene and self.current_scene in self.scenes:
            sc = self.scenes[self.current_scene]
            if "pixel_dark" in self.themes:
                roles = self.themes["pixel_dark"]
                sc.theme = "pixel_dark"
                sc.bg_color = roles.get("bg", sc.bg_color)
            sc.grid_size = self.grid_size  # type: ignore[attr-defined]

    def add_widget(
        self,
        widget: Union[WidgetConfig, WidgetType, str],
        scene_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add widget to scene.

        Accepts either a WidgetConfig instance (existing behavior) or a widget type
        (WidgetType or str) with keyword args like x, y, width, height, text, etc.
        """
        new_widget = self._normalize_widget_input(widget, kwargs)
        self._save_state()
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            print(f"WARNING: Scene '{scene_name or ''}' not found; widget not added.")
            return
        # Snap to grid and magnetic snap against existing widgets
        sx, sy = self.snap_position(new_widget.x, new_widget.y)
        sx, sy = self._apply_snapping(new_widget, sx, sy, self.scenes[scene_name])
        new_widget.x, new_widget.y = sx, sy
        self.scenes[scene_name].widgets.append(new_widget)

    def _normalize_widget_input(
        self, widget: Union[WidgetConfig, WidgetType, str], kw: Dict[str, Any]
    ) -> WidgetConfig:
        if isinstance(widget, WidgetConfig):
            return widget
        wtype = self._widget_type_str(widget)
        x, y, width, height = self._extract_required_dimensions(kw)
        return self._build_widget_config(wtype, x, y, width, height, kw)

    def _widget_type_str(self, widget: Union[WidgetType, str]) -> str:
        if isinstance(widget, WidgetType):
            return widget.value
        return str(widget)

    def _extract_required_dimensions(self, kw: Dict[str, Any]) -> Tuple[int, int, int, int]:
        raw_x = kw.get("x")
        raw_y = kw.get("y")
        raw_w = kw.get("width")
        raw_h = kw.get("height")
        if raw_x is None or raw_y is None or raw_w is None or raw_h is None:
            raise TypeError("add_widget requires x, y, width, height when providing a type")
        try:
            return int(raw_x), int(raw_y), int(raw_w), int(raw_h)
        except (TypeError, ValueError) as e:
            raise TypeError("add_widget requires x, y, width, height as integers") from e

    def _build_widget_config(
        self,
        wtype: str,
        x: int,
        y: int,
        width: int,
        height: int,
        kw: Dict[str, Any],
    ) -> WidgetConfig:
        return WidgetConfig(
            type=wtype,
            x=x,
            y=y,
            width=width,
            height=height,
            text=kw.get("text", ""),
            style=str(kw.get("style", "default")),
            color_fg=str(kw.get("color_fg", "white")),
            color_bg=str(kw.get("color_bg", "black")),
            border=coerce_bool_flag(kw.get("border", True), True),
            border_style=coerce_choice(
                kw.get("border_style", "single"),
                ("none", "single", "double", "rounded", "bold", "dashed"),
                "single",
            ),
            align=coerce_choice(kw.get("align", "left"), ("left", "center", "right"), "left"),
            valign=coerce_choice(kw.get("valign", "middle"), ("top", "middle", "bottom"), "middle"),
            value=int(kw.get("value", 0)) if kw.get("value") is not None else 0,
            min_value=int(kw.get("min_value", 0)),
            max_value=int(kw.get("max_value", 100)),
            checked=coerce_bool_flag(kw.get("checked", False), False),
            enabled=coerce_bool_flag(kw.get("enabled", True), True),
            visible=coerce_bool_flag(kw.get("visible", True), True),
            icon_char=str(kw.get("icon_char", "")),
            data_points=normalize_int_list(kw.get("data_points", []) or []),
            items=normalize_str_list(kw.get("items") or kw.get("list_items") or []),
            z_index=int(kw.get("z_index", 0)),
            padding_x=int(kw.get("padding_x", 1)),
            padding_y=int(kw.get("padding_y", 0)),
            margin_x=int(kw.get("margin_x", 0)),
            margin_y=int(kw.get("margin_y", 0)),
        )

    def add_widget_from_template(self, template_name: str, x: int, y: int, **kwargs: Any):
        """Add widget from template with custom properties"""
        if template_name not in self.templates:
            print(f"Template '{template_name}' not found")
            return

        widget = self._clone_template_with_overrides(template_name, x, y, kwargs)
        self.add_widget(widget)

    def _clone_template_with_overrides(
        self, template_name: str, x: int, y: int, overrides: Dict[str, Any]
    ) -> WidgetConfig:
        template = self.templates.get(template_name)
        if template is None:
            raise KeyError(f"Template '{template_name}' not found")
        widget = copy.deepcopy(template)
        widget.x = x
        widget.y = y
        for key, value in overrides.items():
            if hasattr(widget, key):
                setattr(widget, key, value)
        return widget

    def clone_widget(
        self,
        widget_idx: int,
        offset_x: int = 10,
        offset_y: int = 10,
        scene_name: Optional[str] = None,
    ):
        """Clone existing widget"""
        scene = self._get_scene(scene_name)
        if not scene:
            return
        if 0 <= widget_idx < len(scene.widgets):
            self._save_state()
            cloned = copy.deepcopy(scene.widgets[widget_idx])
            cloned.x += offset_x
            cloned.y += offset_y
            scene.widgets.append(cloned)

    def move_widget(self, widget_idx: int, dx: int, dy: int, scene_name: Optional[str] = None):
        """Move widget by delta"""
        scene = self._get_scene(scene_name)
        if not scene:
            return
        if 0 <= widget_idx < len(scene.widgets):
            widget = scene.widgets[widget_idx]
            if getattr(widget, "locked", False):
                return
            # Record state only if the widget is allowed to move.
            self._save_state()
            nx = widget.x + dx
            ny = widget.y + dy
            nx, ny = self._apply_snapping(widget, nx, ny, scene)
            widget.x = nx
            widget.y = ny

    def resize_widget(self, widget_idx: int, dw: int, dh: int, scene_name: Optional[str] = None):
        """Resize widget by delta"""
        scene = self._get_scene(scene_name)
        if not scene:
            return
        if 0 <= widget_idx < len(scene.widgets):
            widget = scene.widgets[widget_idx]
            if getattr(widget, "locked", False):
                return
            self._save_state()
            widget.width = max(1, widget.width + dw)
            widget.height = max(1, widget.height + dh)

    def delete_widget(self, widget_idx: int, scene_name: Optional[str] = None):
        """Delete widget"""
        scene = self._get_scene(scene_name)
        if not scene:
            return
        if 0 <= widget_idx < len(scene.widgets):
            if getattr(scene.widgets[widget_idx], "locked", False):
                return
            self._save_state()
            del scene.widgets[widget_idx]
            self._reindex_after_delete(widget_idx)

    def _reindex_after_delete(self, deleted_idx: int):
        """Adjust group indices and selection after a widget deletion."""
        # Update selection
        if self.selected_widget is not None:
            if self.selected_widget == deleted_idx:
                self.selected_widget = None
            elif self.selected_widget > deleted_idx:
                self.selected_widget -= 1
        # Update groups
        self._reindex_groups_after_delete(deleted_idx)

    def _reindex_groups_after_delete(self, deleted_idx: int) -> None:
        to_delete = []
        for gname, members in self.groups.items():
            new_members = [m - 1 if m > deleted_idx else m for m in members if m != deleted_idx]
            if new_members:
                self.groups[gname] = new_members
            else:
                to_delete.append(gname)
        for gname in to_delete:
            del self.groups[gname]

    # --- Groups API ---
    def create_group(self, name: str, indices: List[int]) -> bool:
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        valid = [i for i in indices if 0 <= i < len(self.scenes[self.current_scene].widgets)]
        if not valid:
            return False
        self.groups[name] = sorted(set(valid))
        return True

    def add_to_group(self, name: str, indices: List[int]) -> bool:
        if name not in self.groups:
            return False
        cur = set(self.groups[name])
        for i in indices:
            if self.current_scene and self.current_scene in self.scenes:
                if 0 <= i < len(self.scenes[self.current_scene].widgets):
                    cur.add(i)
        self.groups[name] = sorted(cur)
        return True

    def remove_from_group(self, name: str, indices: List[int]) -> bool:
        if name not in self.groups:
            return False
        cur = [i for i in self.groups[name] if i not in set(indices)]
        if cur:
            self.groups[name] = sorted(cur)
        else:
            del self.groups[name]
        return True

    def delete_group(self, name: str) -> bool:
        return bool(self.groups.pop(name, None) is not None)

    def list_groups(self) -> List[Tuple[str, List[int]]]:
        return sorted([(k, v) for k, v in self.groups.items()], key=lambda x: x[0])

    def group_set_lock(self, name: str, mode: str) -> bool:
        if name not in self.groups:
            return False
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        scene = self.scenes[self.current_scene]
        for i in self.groups[name]:
            if 0 <= i < len(scene.widgets):
                if mode == "on":
                    scene.widgets[i].locked = True
                elif mode == "off":
                    scene.widgets[i].locked = False
                elif mode == "toggle":
                    scene.widgets[i].locked = not scene.widgets[i].locked
        return True

    def group_set_visible(self, name: str, mode: str) -> bool:
        if name not in self.groups:
            return False
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        scene = self.scenes[self.current_scene]
        for i in self.groups[name]:
            if 0 <= i < len(scene.widgets):
                if mode == "on":
                    scene.widgets[i].visible = True
                elif mode == "off":
                    scene.widgets[i].visible = False
                elif mode == "toggle":
                    scene.widgets[i].visible = not scene.widgets[i].visible
        return True

    # --- Symbols API ---
    def save_symbol(self, name: str, indices: List[int]) -> bool:
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        scene = self.scenes[self.current_scene]
        sel = [scene.widgets[i] for i in indices if 0 <= i < len(scene.widgets)]
        if not sel:
            return False
        min_x = min(w.x for w in sel)
        min_y = min(w.y for w in sel)
        items = []
        for w in sel:
            d = asdict(w)
            d["x"] = w.x - min_x
            d["y"] = w.y - min_y
            items.append(d)
        self.symbols[name] = {
            "items": items,
            "size": (
                max(w.x + w.width for w in sel) - min_x,
                max(w.y + w.height for w in sel) - min_y,
            ),
        }
        return True

    def place_symbol(self, name: str, x: int, y: int) -> bool:
        if name not in self.symbols:
            return False
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        spec = self.symbols[name]
        for item in spec.get("items", []):
            w = WidgetConfig(
                **{k: v for k, v in item.items() if k in WidgetConfig.__dataclass_fields__}
            )
            w.x = x + int(item.get("x", 0))
            w.y = y + int(item.get("y", 0))
            self.add_widget(w)
        return True

    # --- Checkpoints & Diff ---
    def _current_scene_state(self) -> Optional[Dict[str, Any]]:
        if not self.current_scene or self.current_scene not in self.scenes:
            return None
        scene = self.scenes[self.current_scene]
        return {
            "name": scene.name,
            "width": scene.width,
            "height": scene.height,
            "bg_color": scene.bg_color,
            "widgets": [asdict(w) for w in scene.widgets],
        }

    def create_checkpoint(self, name: str) -> bool:
        state = self._current_scene_state()
        if state is None:
            return False
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        payload = {"ts": ts, "scene": state}
        self.checkpoints[name] = payload
        # Persist snapshot to disk for durability
        try:
            base_dir = (
                Path.home() / ".esp32os" / "designer_checkpoints" / (self.current_scene or "scene")
            )
            base_dir.mkdir(parents=True, exist_ok=True)
            with open(base_dir / f"{ts}_{name}.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass
        return True

    def list_checkpoints(self) -> List[Tuple[str, str]]:
        return sorted(
            [(k, v.get("ts", "")) for k, v in self.checkpoints.items()], key=lambda x: x[1]
        )

    def rollback_checkpoint(self, name: str) -> bool:
        if name not in self.checkpoints:
            return False
        snap = self.checkpoints[name].get("scene")
        if not snap:
            return False
        try:
            widgets = [WidgetConfig(**w) for w in snap.get("widgets", [])]
            self.scenes[snap["name"]] = SceneConfig(
                name=snap["name"],
                width=int(snap.get("width", self.width)),
                height=int(snap.get("height", self.height)),
                widgets=widgets,
                bg_color=snap.get("bg_color", "black"),
            )
            self.current_scene = snap["name"]
            return True
        except (TypeError, KeyError, ValueError):
            return False

    def _diff_states(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """Compute a simple diff between two scene states."""
        diff: Dict[str, Any] = {
            "scene": {"a": a.get("name"), "b": b.get("name")},
            "size": {
                "a": (a.get("width"), a.get("height")),
                "b": (b.get("width"), b.get("height")),
            },
            "widgets": {
                "count": {"a": len(a.get("widgets", [])), "b": len(b.get("widgets", []))},
                "changed": [],
                "added": [],
                "removed": [],
            },
        }
        wa = a.get("widgets", [])
        wb = b.get("widgets", [])
        n = min(len(wa), len(wb))
        self._collect_widget_changes(diff, wa, wb, n)
        self._collect_added_removed(diff, wa, wb, n)
        return diff

    def _collect_widget_changes(
        self, diff: Dict[str, Any], wa: List[Dict[str, Any]], wb: List[Dict[str, Any]], n: int
    ) -> None:
        keys = self._widget_diff_keys()
        changed = diff["widgets"]["changed"]
        for i in range(n):
            changes = self._widget_diff_entry(wa[i], wb[i], keys)
            if changes:
                changed.append({"index": i, "changes": changes})

    def _widget_diff_keys(self) -> List[str]:
        return [
            "type",
            "x",
            "y",
            "width",
            "height",
            "text",
            "style",
            "color_fg",
            "color_bg",
            "border",
            "border_style",
            "align",
            "valign",
            "value",
            "min_value",
            "max_value",
            "checked",
            "enabled",
            "visible",
            "z_index",
        ]

    def _widget_diff_entry(
        self, wa: Dict[str, Any], wb: Dict[str, Any], keys: List[str]
    ) -> Dict[str, Any]:
        return {k: {"a": wa.get(k), "b": wb.get(k)} for k in keys if wa.get(k) != wb.get(k)}

    def _collect_added_removed(
        self, diff: Dict[str, Any], wa: List[Dict[str, Any]], wb: List[Dict[str, Any]], n: int
    ) -> None:
        if len(wa) > n:
            diff["widgets"]["removed"] = list(range(n, len(wa)))
        if len(wb) > n:
            diff["widgets"]["added"] = list(range(n, len(wb)))

    def _get_scene(self, scene_name: Optional[str]) -> Optional[SceneConfig]:
        """Return SceneConfig by name (or current scene if None)."""
        key = scene_name or self.current_scene
        if key and key in self.scenes:
            return self.scenes[key]
        return None

    def _coerce_groups(self, raw: Any) -> Dict[str, List[int]]:
        """Coerce group data loaded from JSON into a safe in-memory form."""
        if not isinstance(raw, dict):
            return {}
        if not self.current_scene or self.current_scene not in self.scenes:
            return {}
        max_idx = len(self.scenes[self.current_scene].widgets) - 1
        out: Dict[str, List[int]] = {}
        for name, members in raw.items():
            try:
                gname = str(name)
            except (TypeError, ValueError):
                continue
            if not isinstance(members, list):
                continue
            cleaned: List[int] = []
            for m in members:
                try:
                    idx = int(m)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx <= max_idx:
                    cleaned.append(idx)
            if cleaned:
                out[gname] = sorted(set(cleaned))
        return out

    def _groups_payload_for_save(self) -> Dict[str, Dict[str, List[int]]]:
        """Return groups in a JSON-friendly form (stored per scene name)."""
        if not self.current_scene or self.current_scene not in self.scenes:
            return {}
        # Ensure indices are valid for current widget list.
        groups = self._coerce_groups(self.groups)
        if not groups:
            return {}
        return {str(self.current_scene): groups}

    def save_to_json(self, filename: str):
        """Save design to JSON file."""
        data = {
            "width": self.width,
            "height": self.height,
            "groups": self._groups_payload_for_save(),
            "scenes": {
                name: {
                    "name": scene.name,
                    "width": scene.width,
                    "height": scene.height,
                    "bg_color": scene.bg_color,
                    "widgets": [asdict(w) for w in scene.widgets],
                }
                for name, scene in self.scenes.items()
            },
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("[OK] Design saved: %s", filename)
        except OSError as exc:
            logger.error("Failed to save design %s: %s", filename, exc)
            return

        # Auto: run preflight unless disabled
        try:
            if os.environ.get("ESP32OS_AUTO_EXPORT", "1") != "0":
                _auto_preflight_and_export(self, filename)
        except Exception as _e:
            print(f"[WARN] Auto-export skipped: {_e}")

    def load_from_json(self, filename: str):
        """Load a design from disk and populate scenes.

        Args:
            filename: Path to a JSON file in UI Designer schema.

        Returns:
            None; updates internal scenes and current_scene.
        """
        try:
            data = self._read_json_file(filename)
            self.width = data.get("width", 128)
            self.height = data.get("height", 64)
            self.scenes = self._build_scenes_from_data(data)
            if self.scenes:
                self.current_scene = next(iter(self.scenes.keys()))
            raw_groups = data.get("groups")
            if (
                isinstance(raw_groups, dict)
                and raw_groups
                and all(isinstance(v, dict) for v in raw_groups.values())
            ):
                scene_groups = raw_groups.get(self.current_scene, {})
                self.groups = self._coerce_groups(scene_groups)
            else:
                self.groups = self._coerce_groups(raw_groups)
            logger.info("[OK] Design loaded: %s", filename)
            self._record_json_watch(filename)
        except SceneLoadError as exc:
            logger.error("Load failed for %s: %s; falling back to default scene", filename, exc)
            self.scenes.clear()
            self.create_scene("main")
            self.current_scene = "main"

    def _read_json_file(self, filename: str) -> Dict[str, Any]:
        try:
            with open(filename, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise SceneLoadError(f"File not found: {filename}") from exc
        except PermissionError as exc:
            raise SceneLoadError(f"Permission denied reading: {filename}") from exc
        except json.JSONDecodeError as exc:
            raise SceneLoadError(f"Invalid JSON in: {filename}") from exc
        except OSError as exc:
            raise SceneLoadError(f"Failed to read JSON: {filename}") from exc

    def _build_scenes_from_data(self, data: Dict[str, Any]) -> Dict[str, SceneConfig]:
        scenes: Dict[str, SceneConfig] = {}
        scenes_data = data.get("scenes", {})

        scenes_dict = self._scenes_dict_from_data(scenes_data, data)
        for name, scene_data in scenes_dict.items():
            widgets = self._widgets_for_scene(data, name)
            scenes[name] = self._build_scene_config(name, scene_data, widgets, data)
        return scenes

    def _scenes_dict_from_data(
        self, scenes_data: Union[Dict[str, Any], List[Any]], root_data: Dict[str, Any]
    ) -> Dict[str, SceneConfigDict]:
        if isinstance(scenes_data, list):
            return {
                str(scene.get("id", f"scene_{i}")): self._validate_scene_dict(
                    scene, root_data, idx=i
                )
                for i, scene in enumerate(scenes_data)
            }
        return {
            str(name): self._validate_scene_dict(scene, root_data)
            for name, scene in scenes_data.items()
        }

    def _widgets_for_scene(self, data: Dict[str, Any], name: str) -> List[WidgetConfig]:
        raw_widgets = (
            data.get("scenes", {}).get(name, {}).get("widgets")
            if isinstance(data.get("scenes", {}), dict)
            else None
        )
        raw_widgets = raw_widgets if isinstance(raw_widgets, list) else []
        widgets: List[WidgetConfig] = []
        for w in raw_widgets:
            widget_dict = dict(w)
            if "id" in widget_dict:
                widget_dict["_widget_id"] = widget_dict.pop("id")
            widgets.append(WidgetConfig(**widget_dict))
        return widgets

    def _build_scene_config(
        self,
        name: str,
        scene_data: SceneConfigDict,
        widgets: List[WidgetConfig],
        data: Dict[str, Any],
    ) -> SceneConfig:
        return SceneConfig(
            name=scene_data["name"],
            width=scene_data["width"],
            height=scene_data["height"],
            widgets=widgets,
            bg_color=data.get("bg_color", "black"),
            theme=scene_data["theme"],
            hardware_profile=scene_data.get("hardware_profile"),
            max_fb_kb=scene_data.get("max_fb_kb"),
            max_flash_kb=scene_data.get("max_flash_kb"),
        )

    def _validate_scene_dict(
        self, scene_data: Dict[str, Any], root_data: Dict[str, Any], idx: int = 0
    ) -> SceneConfigDict:
        if not isinstance(scene_data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise WidgetValidationError("scene data must be a dict")
        defaults = self._scene_defaults(root_data)
        name = self._coerce_scene_name(scene_data, idx)
        theme = self._coerce_scene_theme(scene_data)
        width = self._opt_scene_int(scene_data.get("width")) or defaults["width"]
        height = self._opt_scene_int(scene_data.get("height")) or defaults["height"]
        hw_profile = scene_data.get("hardware_profile")
        if hw_profile is not None and not isinstance(hw_profile, str):
            raise WidgetValidationError("hardware_profile must be a string or None")

        return {
            "name": name,
            "width": width,
            "height": height,
            "theme": theme,
            "hardware_profile": hw_profile,
            "max_fb_kb": self._opt_scene_int(scene_data.get("max_fb_kb")),
            "max_flash_kb": self._opt_scene_int(scene_data.get("max_flash_kb")),
        }

    def _scene_defaults(self, root_data: Dict[str, Any]) -> Dict[str, int]:
        display = root_data.get("display", {})
        return {
            "width": int(display.get("width", 320) or 320),
            "height": int(display.get("height", 240) or 240),
        }

    def _coerce_scene_name(self, scene_data: Dict[str, Any], idx: int) -> str:
        return str(scene_data.get("name") or scene_data.get("id") or f"scene_{idx}")

    def _coerce_scene_theme(self, scene_data: Dict[str, Any]) -> str:
        return str(scene_data.get("theme") or "default")

    def _opt_scene_int(self, val: Any) -> Optional[int]:
        if val is None:
            return None
        if isinstance(val, bool):
            raise WidgetValidationError("boolean not allowed for size fields")
        try:
            return int(val)
        except (ValueError, TypeError) as exc:
            raise WidgetValidationError("size fields must be numeric") from exc

    def _record_json_watch(self, filename: str) -> None:
        try:
            mtime = os.path.getmtime(filename)
            # Store on both instance and class for legacy callers and tests.
            self._last_loaded_json = filename
            self._json_watch_mtime = mtime
            UIDesigner._last_loaded_json = filename
            UIDesigner._json_watch_mtime = mtime
        except OSError:
            self._last_loaded_json = None
            self._json_watch_mtime = None
            UIDesigner._last_loaded_json = None
            UIDesigner._json_watch_mtime = None

    def generate_python_code(self, scene_name: Optional[str] = None) -> str:
        """Generate Python code for scene"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return ""

        scene = self.scenes[scene_name]

        code_lines = []
        code_lines.extend(self._generate_imports(scene))
        code_lines.extend(self._generate_scene_init(scene))
        return "\n".join(code_lines)

    def _generate_imports(self, scene: SceneConfig) -> List[str]:
        """Generate file header and imports for code export."""
        return [
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
        ]

    def _generate_widget_code(self, widget: WidgetConfig) -> List[str]:
        """Render a single widget constructor block."""
        lines = [
            "        Widget(",
            f"            type='{widget.type}',",
            f"            x={widget.x},",
            f"            y={widget.y},",
            f"            width={widget.width},",
            f"            height={widget.height},",
        ]
        if widget.text:
            lines.append(f"            text='{widget.text}',")
        if widget.style != "default":
            lines.append(f"            style='{widget.style}',")
        if widget.color_fg != "white":
            lines.append(f"            color_fg='{widget.color_fg}',")
        if widget.color_bg != "black":
            lines.append(f"            color_bg='{widget.color_bg}',")
        if not widget.border:
            lines.append(f"            border={widget.border},")
        if widget.align != "left":
            lines.append(f"            align='{widget.align}',")
        lines.append("        ),")
        return lines

    def _generate_scene_init(self, scene: SceneConfig) -> List[str]:
        """Generate scene factory function and main guard."""
        lines = [
            f"def create_{scene.name.lower()}_scene() -> List[Widget]:",
            f'    """Create {scene.name} scene widgets"""',
            "    return [",
        ]
        for widget in scene.widgets:
            lines.extend(self._generate_widget_code(widget))
        lines.extend(
            [
                "    ]",
                "",
                "",
                "if __name__ == '__main__':",
                f"    widgets = create_{scene.name.lower()}_scene()",
                f"    print(f'Created {{len(widgets)}} widgets for {scene.name} scene')",
            ]
        )
        return lines

    def export_code(self, filename: str, scene_name: Optional[str] = None):
        """Export a scene as a standalone Python module.

        Args:
            filename: Destination file path.
            scene_name: Optional scene key; defaults to current.
        """
        code = self.generate_python_code(scene_name)
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info("[OK] Code exported: %s", filename)
        except OSError as exc:
            logger.error("Failed to export code to %s: %s", filename, exc)
            return

    def auto_layout(
        self, layout_type: str = "vertical", spacing: int = 4, scene_name: Optional[str] = None
    ):
        """Auto-arrange widgets in the given scene.

        Args:
            layout_type: "vertical", "horizontal", or "grid".
            spacing: Padding between widgets in pixels.
            scene_name: Optional scene key; defaults to current.
        """
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return

        self._save_state()
        scene = self.scenes[scene_name]
        layout_type = (layout_type or "").lower()
        if layout_type == "vertical":
            self._layout_vertical(scene, spacing)
        elif layout_type == "horizontal":
            self._layout_horizontal(scene, spacing)
        elif layout_type == "grid":
            self._layout_grid(scene, spacing)

    def _layout_vertical(self, scene: SceneConfig, spacing: int) -> None:
        y_offset = spacing
        for widget in scene.widgets:
            max_x = max(0, scene.width - widget.width)
            widget.x = _clamp_int((scene.width - widget.width) // 2, 0, max_x)
            widget.y = _clamp_int(y_offset, 0, max(0, scene.height - widget.height))
            y_offset += widget.height + spacing

    def _layout_horizontal(self, scene: SceneConfig, spacing: int) -> None:
        x_offset = spacing
        for widget in scene.widgets:
            widget.x = _clamp_int(x_offset, 0, max(0, scene.width - widget.width))
            widget.y = _clamp_int(
                (scene.height - widget.height) // 2, 0, max(0, scene.height - widget.height)
            )
            x_offset += widget.width + spacing

    def _layout_grid(self, scene: SceneConfig, spacing: int) -> None:
        cols = max(1, int((scene.width + spacing) / (40 + spacing)))  # Assume 40px avg width
        x_offset = spacing
        y_offset = spacing
        col = 0
        for widget in scene.widgets:
            widget.x = _clamp_int(x_offset, 0, max(0, scene.width - widget.width))
            widget.y = _clamp_int(y_offset, 0, max(0, scene.height - widget.height))
            col += 1
            x_offset += widget.width + spacing
            if col >= cols:
                col = 0
                x_offset = spacing
                y_offset += 30 + spacing  # Assume 30px avg height

    def align_widgets(
        self, alignment: str, widget_indices: List[int], scene_name: Optional[str] = None
    ):
        """Align selected widgets to a common edge or center.

        Args:
            alignment: One of left/right/top/bottom/center_h/center_v.
            widget_indices: Indices to align.
            scene_name: Optional scene key; defaults to current.
        """
        scene = self._get_scene(scene_name)
        if not scene or not widget_indices:
            return
        self._save_state()
        widgets = self._widgets_by_indices(scene, widget_indices)
        if not widgets:
            return

        alignment = (alignment or "").lower()
        action = self._alignment_action(alignment, widgets)
        if action:
            action()

    def _alignment_action(self, alignment: str, widgets: List[WidgetConfig]):
        actions = {
            "left": lambda: self._align_left(widgets),
            "right": lambda: self._align_right(widgets),
            "top": lambda: self._align_top(widgets),
            "bottom": lambda: self._align_bottom(widgets),
            "center_h": lambda: self._align_center(widgets, axis="x"),
            "center_v": lambda: self._align_center(widgets, axis="y"),
        }
        return actions.get(alignment)

    def _align_left(self, widgets: List[WidgetConfig]) -> None:
        """Align widgets to leftmost edge"""
        if widgets:
            target = min(w.x for w in widgets)
            for w in widgets:
                w.x = target

    def _align_right(self, widgets: List[WidgetConfig]) -> None:
        """Align widgets to rightmost edge"""
        if widgets:
            target = max(w.x + w.width for w in widgets)
            for w in widgets:
                w.x = target - w.width

    def _align_top(self, widgets: List[WidgetConfig]) -> None:
        """Align widgets to topmost edge"""
        if widgets:
            target = min(w.y for w in widgets)
            for w in widgets:
                w.y = target

    def _align_bottom(self, widgets: List[WidgetConfig]) -> None:
        """Align widgets to bottommost edge"""
        if widgets:
            target = max(w.y + w.height for w in widgets)
            for w in widgets:
                w.y = target - w.height

    def distribute_widgets(
        self, direction: str, widget_indices: List[int], scene_name: Optional[str] = None
    ):
        """Distribute widgets evenly along an axis.

        Args:
            direction: "horizontal" or "vertical".
            widget_indices: Indices to distribute.
            scene_name: Optional scene key; defaults to current.
        """
        scene = self._get_scene(scene_name)
        if not scene or len(widget_indices) < 2:
            return
        self._save_state()
        items = [(i, scene.widgets[i]) for i in widget_indices if 0 <= i < len(scene.widgets)]
        if direction == "horizontal":
            self._distribute_axis(items, axis="x")
        elif direction == "vertical":
            self._distribute_axis(items, axis="y")

    def _align_center(self, widgets: List[WidgetConfig], axis: str) -> None:
        if not widgets:
            return
        if axis == "x":
            avg = self._calculate_center(widgets, axis="x")
            for w in widgets:
                ww, _ = _widget_dims(w)
                w.x = _clamp_int(avg - ww // 2)
        elif axis == "y":
            avg = self._calculate_center(widgets, axis="y")
            for w in widgets:
                _, hh = _widget_dims(w)
                w.y = _clamp_int(avg - hh // 2)

    def _calculate_center(self, widgets: List[WidgetConfig], axis: str) -> int:
        centers = (
            [int(w.x + w.width // 2) for w in widgets]
            if axis == "x"
            else [int(w.y + w.height // 2) for w in widgets]
        )
        return sum(centers) // len(centers) if centers else 0

    def _widgets_by_indices(self, scene: SceneConfig, indices: List[int]) -> List[WidgetConfig]:
        return [scene.widgets[i] for i in indices if 0 <= i < len(scene.widgets)]

    def _distribute_axis(self, items: List[Tuple[int, WidgetConfig]], axis: str) -> None:
        if not items:
            return
        key = (lambda w: w[1].x) if axis == "x" else (lambda w: w[1].y)
        size = (
            (lambda w: _widget_dims(w[1])[0]) if axis == "x" else (lambda w: _widget_dims(w[1])[1])
        )
        items.sort(key=key)
        start = _safe_int(key(items[0])) if key(items[0]) is not None else 0
        end = _safe_int(key(items[-1])) + max(0, int(size(items[-1]) or 0))
        total_span = sum(max(0, int(size(w) or 0)) for w in items)
        spacing = (end - start - total_span) / max(1, (len(items) - 1))
        pos = start
        for _, widget in items:
            if axis == "x":
                widget.x = int(pos)
                pos += max(0, widget.width if widget.width else 0) + spacing
            else:
                widget.y = int(pos)
                pos += max(0, widget.height if widget.height else 0) + spacing

    def export_to_html(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as HTML preview"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        scene = self.scenes[scene_name]
        html = self._build_html_export(scene, self.preview_ascii(scene_name))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("[OK] HTML preview exported: %s", filename)

    def _build_html_export(self, scene: SceneConfig, preview_raw: str) -> str:
        """Compose full HTML document for a scene preview."""
        preview = escape(preview_raw)
        colors = self._html_colors()
        return "\n".join(
            [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "<head>",
                '    <meta charset="UTF-8">',
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                f"    <title>{scene.name} - UI Design Preview</title>",
                "    <style>",
                *self._html_styles(colors),
                "    </style>",
                "</head>",
                "<body>",
                f"    <h1>{scene.name}</h1>",
                f'    <div class="preview">{preview}</div>',
                '    <div class="info">',
                f"        <p>Size: {scene.width} x {scene.height}</p>",
                f"        <p>Widgets: {len(scene.widgets)}</p>",
                f"        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
                "    </div>",
                "</body>",
                "</html>",
            ]
        )

    def _html_colors(self) -> Dict[str, str]:
        return {
            "body_bg": color_hex("legacy_gray5"),
            "body_text": color_hex("legacy_green"),
            "preview_bg": color_hex("shadow"),
            "preview_border": color_hex("legacy_green"),
            "info_color": color_hex("legacy_cyan"),
        }

    def _html_styles(self, colors: Dict[str, str]) -> List[str]:
        """Return inline CSS lines for export HTML."""
        return [
            "        body {",
            f"            background: {colors['body_bg']};",
            f"            color: {colors['body_text']};",
            "            font-family: 'Courier New', monospace;",
            "            padding: 20px;",
            "        }",
            "        .preview {",
            f"            background: {colors['preview_bg']};",
            f"            border: 2px solid {colors['preview_border']};",
            "            padding: 20px;",
            "            display: inline-block;",
            "            white-space: pre;",
            "            line-height: 1.2;",
            "        }",
            "        .info {",
            "            margin-top: 20px;",
            f"            color: {colors['info_color']};",
            "        }",
        ]

    def preview_ascii(self, scene_name: Optional[str] = None, show_grid: bool = False) -> str:
        """Generate ASCII preview of scene with enhanced rendering"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return ""

        scene = self.scenes[scene_name]
        canvas = self._create_canvas(scene, show_grid)
        self._draw_widgets(canvas, scene)
        self._draw_guides(canvas, scene)
        return "\n".join("".join(row) for row in canvas)

    # --- ASCII Preview Helpers ---
    # Lightweight type aliases to improve clarity
    border_chars_t = Dict[str, str]
    scene_state_t = Dict[str, Any]
    guide_spec_t = Dict[str, Any]

    def _create_canvas(self, scene: SceneConfig, show_grid: bool) -> List[List[str]]:
        canvas = [[" " for _ in range(scene.width)] for _ in range(scene.height)]
        if show_grid and self.grid_enabled:
            for y in range(0, scene.height, self.grid_size):
                for x in range(0, scene.width, self.grid_size):
                    if x < scene.width and y < scene.height:
                        canvas[y][x] = "."
        return canvas

    def _draw_widgets(self, canvas: List[List[str]], scene: SceneConfig) -> None:
        sorted_widgets = sorted(enumerate(scene.widgets), key=lambda w: w[1].z_index)
        for idx, widget in sorted_widgets:
            if not widget.visible:
                continue
            eff = copy.deepcopy(widget)
            self._apply_state_overrides_inplace(eff)
            self._apply_animation_preview_inplace(eff, idx, scene)
            self._render_widget_to_canvas(canvas, eff, idx, scene.width, scene.height)

    def _draw_guides(self, canvas: List[List[str]], scene: SceneConfig) -> None:
        if not (self.show_guides and self.last_guides):
            return
        v_guides = [g for g in self.last_guides if g.get("type") == "v" and g.get("k") != "C"]
        h_guides = [g for g in self.last_guides if g.get("type") == "h" and g.get("k") != "C"]
        center_guides = [g for g in self.last_guides if g.get("k") == "C"]
        self._draw_vertical_guides(canvas, scene, v_guides)
        self._draw_horizontal_guides(canvas, scene, h_guides)
        self._draw_center_guides(canvas, scene, center_guides)

    def _draw_vertical_guides(
        self, canvas: List[List[str]], scene: SceneConfig, guides: List[Dict[str, Any]]
    ) -> None:
        if not guides:
            return
        for g in guides:
            x = g.get("x")
            if x is None or not (0 <= x < scene.width):
                continue
            y1 = max(0, g.get("y1", 0))
            y2 = min(scene.height, g.get("y2", scene.height - 1) + 1)
            for y in range(y1, y2):
                canvas[y][x] = "|"

    def _draw_horizontal_guides(
        self, canvas: List[List[str]], scene: SceneConfig, guides: List[Dict[str, Any]]
    ) -> None:
        if not guides:
            return
        for g in guides:
            y = g.get("y")
            if y is None or not (0 <= y < scene.height):
                continue
            x1 = max(0, g.get("x1", 0))
            x2 = min(scene.width, g.get("x2", scene.width - 1) + 1)
            for x in range(x1, x2):
                canvas[y][x] = "-"

    def _draw_center_guides(
        self, canvas: List[List[str]], scene: SceneConfig, guides: List[Dict[str, Any]]
    ) -> None:
        if not guides:
            return
        for g in guides:
            orient = g.get("type")
            if orient == "v":
                self._draw_vertical_guides(canvas, scene, [g])
            elif orient == "h":
                self._draw_horizontal_guides(canvas, scene, [g])

    def _render_widget_to_canvas(
        self, canvas: List[List[str]], widget: WidgetConfig, idx: int, width: int, height: int
    ):
        """Render single widget to canvas"""
        border_chars = self._get_border_chars(widget.border_style)
        if widget.border:
            self._draw_border(canvas, widget, border_chars, width, height)
        self._render_content(canvas, widget, width, height)
        self._draw_widget_index(canvas, widget, idx, width, height)

    def _render_content(
        self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int
    ) -> None:
        handlers: Dict[str, Any] = {
            "progressbar": self._draw_progressbar,
            "gauge": self._draw_gauge,
            "checkbox": self._draw_checkbox,
            "slider": self._draw_slider,
            "chart": self._draw_chart,
            "icon": self._draw_icon,
        }
        handler = handlers.get(widget.type)
        if handler:
            handler(canvas, widget, width, height)
        elif widget.text:
            self._draw_text(canvas, widget, width, height)

    def _draw_icon(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Render icon glyph (single char) centered in its box."""
        glyph = (
            str(getattr(widget, "icon_char", "") or getattr(widget, "text", "") or "?")
            .replace("\n", " ")
            .strip()
        )
        if not glyph:
            return

        pad_x = int(getattr(widget, "padding_x", 0) or 0)
        pad_y = int(getattr(widget, "padding_y", 0) or 0)
        border_pad = 1 if bool(getattr(widget, "border", True)) else 0

        x0 = int(widget.x) + border_pad + pad_x
        y0 = int(widget.y) + border_pad + pad_y
        x1 = int(widget.x) + int(widget.width) - border_pad - pad_x - 1
        y1 = int(widget.y) + int(widget.height) - border_pad - pad_y - 1

        inner_w = x1 - x0 + 1
        inner_h = y1 - y0 + 1
        if inner_w <= 0 or inner_h <= 0:
            return

        glyph = glyph[: max(1, min(4, inner_w))]
        text_y = y0 + (inner_h // 2)
        text_x = x0 + max(0, (inner_w - len(glyph)) // 2)
        if 0 <= text_y < height:
            self._write_text_line(canvas, text_y, text_x, glyph, width)

    def _draw_widget_index(
        self, canvas: List[List[str]], widget: WidgetConfig, idx: int, width: int, height: int
    ) -> None:
        num_str = str(idx)
        num_y = widget.y if not widget.border else widget.y + 1
        num_x = widget.x + 1
        if 0 <= num_y < height:
            self._write_text_line(canvas, num_y, num_x, num_str, width)

    def _draw_border(
        self,
        canvas: List[List[str]],
        widget: WidgetConfig,
        border_chars: Dict[str, str],
        width: int,
        height: int,
    ) -> None:
        """Draw widget border with bounds checks (pixel-perfect, single stroke)."""
        w_span = max(1, int(getattr(widget, "width", 1) or 1))
        h_span = max(1, int(getattr(widget, "height", 1) or 1))
        x0 = int(getattr(widget, "x", 0) or 0)
        y0 = int(getattr(widget, "y", 0) or 0)
        x1 = x0 + w_span - 1
        y1 = y0 + h_span - 1

        # Clamp to canvas to avoid out-of-bounds when widgets are partially visible
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = max(x0, min(width - 1, x1))
        y1 = max(y0, min(height - 1, y1))
        if x0 > x1 or y0 > y1:
            return

        # Draw edges while leaving corners for explicit corner glyphs
        self._draw_border_horizontal(
            canvas, x0, x1, y0, y1, border_chars["h"], width, height, skip_corners=True
        )
        self._draw_border_vertical(
            canvas, x0, x1, y0, y1, border_chars["v"], width, height, skip_corners=True
        )
        self._draw_border_corners(canvas, x0, x1, y0, y1, border_chars, width, height)

    def _draw_border_horizontal(
        self,
        canvas: List[List[str]],
        x0: int,
        x1: int,
        y0: int,
        y1: int,
        char: str,
        width: int,
        height: int,
        skip_corners: bool = False,
    ) -> None:
        """Draw top and bottom border lines"""
        start_x = x0 + (1 if skip_corners else 0)
        end_x = x1 - (1 if skip_corners else 0)
        for x in range(max(0, start_x), min(end_x + 1, width)):
            if 0 <= y0 < height:
                canvas[y0][x] = char
            if 0 <= y1 < height:
                canvas[y1][x] = char

    def _draw_border_vertical(
        self,
        canvas: List[List[str]],
        x0: int,
        x1: int,
        y0: int,
        y1: int,
        char: str,
        width: int,
        height: int,
        skip_corners: bool = False,
    ) -> None:
        """Draw left and right border lines"""
        start_y = y0 + (1 if skip_corners else 0)
        end_y = y1 - (1 if skip_corners else 0)
        for y in range(max(0, start_y), min(end_y + 1, height)):
            if 0 <= x0 < width:
                canvas[y][x0] = char
            if 0 <= x1 < width:
                canvas[y][x1] = char

    def _draw_border_corners(
        self,
        canvas: List[List[str]],
        x0: int,
        x1: int,
        y0: int,
        y1: int,
        border_chars: Dict[str, str],
        width: int,
        height: int,
    ) -> None:
        """Draw border corner characters"""
        corners = [
            (y0, x0, "tl"),  # top-left
            (y0, x1, "tr"),  # top-right
            (y1, x0, "bl"),  # bottom-left
            (y1, x1, "br"),  # bottom-right
        ]
        for y, x, key in corners:
            if 0 <= y < height and 0 <= x < width:
                canvas[y][x] = border_chars[key]

    def _write_text_line(
        self, canvas: List[List[str]], y: int, x_start: int, text: str, width: int
    ) -> None:
        """Write a text string to a single canvas row with bounds checks."""
        if not (0 <= y < len(canvas)):
            return
        for i, ch in enumerate(text):
            x = x_start + i
            if 0 <= x < width:
                canvas[y][x] = ch

    def _ellipsize_text(self, text: str, max_len: int, ellipsis: str = "...") -> str:
        s = str(text or "")
        max_len = int(max_len)
        if max_len <= 0 or not s:
            return ""
        if len(s) <= max_len:
            return s
        if max_len <= len(ellipsis):
            return s[:max_len]
        return s[: max_len - len(ellipsis)] + ellipsis

    def _apply_state_overrides_inplace(self, widget: WidgetConfig) -> None:
        try:
            overrides = (widget.state_overrides or {}).get(widget.state or "default")
            if overrides:
                for k, v in overrides.items():
                    if hasattr(widget, k):
                        try:
                            setattr(widget, k, type(getattr(widget, k))(v))
                        except (ValueError, TypeError):
                            setattr(widget, k, v)
        except (AttributeError, TypeError):
            pass

    def _apply_animation_preview_inplace(
        self, widget: WidgetConfig, idx: int, scene: SceneConfig
    ) -> None:
        ctx = self.anim_context
        if not ctx:
            return
        if ctx.get("idx") != idx:
            return
        name = (ctx.get("name") or "").lower()
        t = int(ctx.get("t", 0))
        steps = max(1, int(ctx.get("steps", 10)))
        try:
            self._apply_animation_step(name, widget, scene, t, steps)
        except (ValueError, TypeError, KeyError, AttributeError):
            pass

    def _apply_animation_step(
        self, name: str, widget: WidgetConfig, scene: SceneConfig, t: int, steps: int
    ) -> None:
        handlers = {
            "bounce": lambda: self._anim_bounce(widget, scene, t, steps),
            "slideinleft": lambda: self._anim_slide_in_left(widget, scene, t, steps),
            "pulse": lambda: self._anim_pulse(widget, t),
            "fadein": lambda: self._anim_fade_in(widget, t),
        }
        handler = handlers.get(name)
        if handler:
            handler()

    def _anim_bounce(self, widget: WidgetConfig, scene: SceneConfig, t: int, steps: int) -> None:
        import math

        amp = max(1, min(3, scene.height // 10))
        dy = round(amp * math.sin(2 * math.pi * (t % steps) / steps))
        widget.y = max(0, min(scene.height - widget.height, widget.y + dy))

    def _anim_slide_in_left(
        self, widget: WidgetConfig, scene: SceneConfig, t: int, steps: int
    ) -> None:
        start = -widget.width
        end = widget.x
        pos = start + (end - start) * (t % steps) / steps
        widget.x = max(-widget.width, min(scene.width - 1, int(pos)))

    def _anim_pulse(self, widget: WidgetConfig, t: int) -> None:
        widget.border_style = "bold" if (t % 2) == 0 else "single"

    def _anim_fade_in(self, widget: WidgetConfig, t: int) -> None:
        widget.style = "highlight" if (t % 2) == 0 else "default"

    def _get_border_chars(self, style: str) -> Dict[str, str]:
        """Get border characters for style"""
        styles = {
            "single": {"h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+", "br": "+"},
            "double": {"h": "=", "v": "║", "tl": "+", "tr": "+", "bl": "+", "br": "+"},
            "rounded": {"h": "-", "v": "|", "tl": "(", "tr": ")", "bl": "(", "br": ")"},
            "bold": {"h": "#", "v": "#", "tl": "#", "tr": "#", "bl": "#", "br": "#"},
            "dashed": {"h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+", "br": "+"},
        }
        return styles.get(style, styles["single"])

    def _draw_text(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw text with alignment, clipped to widget inner box."""
        text_raw = str(getattr(widget, "text", "") or "")
        if not text_raw.strip():
            return

        pad_x = int(getattr(widget, "padding_x", 0) or 0)
        pad_y = int(getattr(widget, "padding_y", 0) or 0)
        border_pad = 1 if bool(getattr(widget, "border", True)) else 0

        x0 = int(widget.x) + border_pad + pad_x
        y0 = int(widget.y) + border_pad + pad_y
        x1 = int(widget.x) + int(widget.width) - border_pad - pad_x - 1
        y1 = int(widget.y) + int(widget.height) - border_pad - pad_y - 1

        inner_w = x1 - x0 + 1
        inner_h = y1 - y0 + 1
        if inner_w <= 0 or inner_h <= 0:
            return

        align = str(getattr(widget, "align", "left") or "left").lower()
        valign = str(getattr(widget, "valign", "middle") or "middle").lower()

        overflow = str(getattr(widget, "text_overflow", "ellipsis") or "ellipsis").strip().lower()
        if overflow not in {"ellipsis", "wrap", "clip", "auto"}:
            overflow = "ellipsis"

        # Determine final mode.
        use_wrap = overflow == "wrap"
        if overflow == "auto":
            flat = text_raw.replace("\t", " ").replace("\n", " ").strip()
            use_wrap = inner_h >= 2 and (("\n" in text_raw) or (len(flat) > inner_w))

        if use_wrap:
            max_lines = inner_h
            try:
                ml = getattr(widget, "max_lines", None)
                if ml is not None and str(ml) != "":
                    ml_i = int(ml)
                    if ml_i > 0:
                        max_lines = min(max_lines, ml_i)
            except (ValueError, TypeError):
                pass
            max_lines = max(1, int(max_lines))

            s = text_raw.replace("\t", " ").strip()
            paras = [p.strip() for p in s.splitlines() if p.strip()]
            if not paras:
                paras = [s]

            lines: List[str] = []
            truncated = False

            def _push_line(line: str) -> None:
                nonlocal truncated
                if len(lines) >= max_lines:
                    truncated = True
                    return
                lines.append(line)

            for para in paras:
                words = para.split()
                current = ""
                for word in words:
                    cand = word if not current else f"{current} {word}"
                    if len(cand) <= inner_w:
                        current = cand
                        continue
                    if current:
                        _push_line(current)
                        if len(lines) >= max_lines:
                            break
                        current = word
                        continue

                    # Single word too long: split by characters.
                    chunk = ""
                    for ch in word:
                        cand2 = chunk + ch
                        if len(cand2) <= inner_w:
                            chunk = cand2
                        else:
                            if chunk:
                                _push_line(chunk)
                                if len(lines) >= max_lines:
                                    break
                            chunk = ch if len(ch) <= inner_w else ""
                    if len(lines) >= max_lines:
                        break
                    current = chunk

                if len(lines) >= max_lines:
                    break
                if current:
                    _push_line(current)
                if len(lines) >= max_lines:
                    break

            if truncated and lines:
                lines[-1] = self._ellipsize_text(lines[-1], inner_w)
        else:
            line_text = text_raw.replace("\t", " ").replace("\n", " ").strip()
            if overflow == "clip":
                line = line_text[:inner_w]
            else:
                line = self._ellipsize_text(line_text, inner_w)
            lines = [line]

        n_lines = max(1, len(lines))
        if valign == "top":
            start_y = y0
        elif valign == "bottom":
            start_y = y1 - (n_lines - 1)
        else:
            start_y = y0 + max(0, (inner_h - n_lines) // 2)

        for i, line in enumerate(lines[:inner_h]):
            y = start_y + i
            if not (0 <= y < height):
                continue
            if align == "center":
                x = x0 + max(0, (inner_w - len(line)) // 2)
            elif align == "right":
                x = x0 + max(0, inner_w - len(line))
            else:
                x = x0
            self._write_text_line(canvas, y, x, line[:inner_w], width)

    # Small utility helpers to reduce duplication in ASCII drawing
    def _inner_box(self, widget: WidgetConfig) -> Tuple[int, int, int, int]:
        """Return (x_start, y_start, inner_width, inner_height) considering border."""
        x_start = widget.x + (1 if widget.border else 0)
        y_start = widget.y + (1 if widget.border else 0)
        inner_w = widget.width - (2 if widget.border else 0)
        inner_h = widget.height - (2 if widget.border else 0)
        return x_start, y_start, inner_w, inner_h

    def _calc_progress_value(self, value: int, max_value: int, span: int) -> int:
        """Compute filled span for bars; preserves existing normalization semantics."""
        return int((value / max(max_value, 1)) * max(0, span))

    def _calc_slider_pos(self, value: int, max_value: int, span: int) -> int:
        """Compute slider knob position within [0, span]."""
        span = max(0, span)
        if span == 0:
            return 0
        return int((value / max(max_value, 1)) * span)

    def _draw_progressbar(
        self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int
    ):
        """Draw progress bar"""
        x0, _y0, inner_w, _inner_h = self._inner_box(widget)
        fill_ratio = self._calc_fill_ratio(widget)
        progress = int(fill_ratio * max(0, inner_w))
        bar_y = widget.y + widget.height // 2

        if not (0 <= bar_y < height):
            return

        style = (widget.style or "default").lower()
        if style == "segmented":
            self._draw_segmented_bar(canvas, x0, bar_y, inner_w, fill_ratio, width)
        else:
            self._draw_simple_bar(canvas, x0, bar_y, inner_w, progress, width)

    def _calc_fill_ratio(self, widget: WidgetConfig) -> float:
        """Calculate fill ratio for progress bar"""
        denom = max(1, widget.max_value - widget.min_value)
        return max(0.0, min(1.0, (widget.value - widget.min_value) / denom))

    def _draw_segmented_bar(
        self,
        canvas: List[List[str]],
        x0: int,
        bar_y: int,
        inner_w: int,
        fill_ratio: float,
        width: int,
    ) -> None:
        """Draw segmented progress bar"""
        segment = 3
        gap = 1
        span = segment + gap
        total_segments = max(1, inner_w // span)
        filled_segments = int(fill_ratio * total_segments)

        for i in range(inner_w):
            x = x0 + i
            if not (0 <= x < width):
                continue

            in_segment = (i % span) < segment
            current_segment = i // span

            if current_segment < filled_segments and in_segment:
                canvas[bar_y][x] = "#"
            elif in_segment:
                canvas[bar_y][x] = "."
            else:
                canvas[bar_y][x] = " "

    def _draw_simple_bar(
        self, canvas: List[List[str]], x0: int, bar_y: int, inner_w: int, progress: int, width: int
    ) -> None:
        """Draw simple progress bar"""
        for i in range(inner_w):
            x = x0 + i
            if 0 <= x < width:
                canvas[bar_y][x] = "#" if i < progress else "."

    def _draw_gauge(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw gauge (simple bar)"""
        _x0, _y0, _inner_w, inner_h = self._inner_box(widget)
        progress = self._calc_progress_value(widget.value, widget.max_value, inner_h)
        gauge_x = widget.x + widget.width // 2
        gauge_y_start = widget.y + widget.height - (1 if widget.border else 0) - 1
        for i in range(inner_h):
            y = gauge_y_start - i
            if 0 <= y < height and 0 <= gauge_x < width:
                canvas[y][gauge_x] = "#" if i < progress else "."

    def _draw_checkbox(
        self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int
    ):
        """Draw checkbox"""
        check_y = widget.y + widget.height // 2
        check_x = widget.x + (1 if widget.border else 0) + 1

        if 0 <= check_y < height and 0 <= check_x < width:
            canvas[check_y][check_x] = "X" if widget.checked else " "

        # Draw label if text exists
        if widget.text and 0 <= check_y < height:
            pad_x = int(getattr(widget, "padding_x", 0) or 0)
            border_pad = 1 if bool(getattr(widget, "border", True)) else 0
            text_x = check_x + 2
            inner_right = widget.x + widget.width - border_pad - pad_x - 1
            max_len = int(inner_right - text_x + 1)
            if max_len > 0:
                line = self._ellipsize_text(str(widget.text or "").replace("\n", " "), max_len)
                self._write_text_line(canvas, check_y, text_x, line, width)

    def _draw_slider(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw slider"""
        x0, _y0, inner_w, _inner_h = self._inner_box(widget)
        slider_pos = self._calc_slider_pos(widget.value, widget.max_value, max(0, inner_w - 1))
        slider_y = widget.y + widget.height // 2
        if 0 <= slider_y < height:
            for i in range(inner_w):
                x = x0 + i
                if 0 <= x < width:
                    canvas[slider_y][x] = "#" if i == slider_pos else "-"

    def _draw_chart(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw simple chart"""
        if not widget.data_points:
            return
        x0, y0, inner_w, inner_h = self._inner_box(widget)
        max_val = max(widget.data_points) if widget.data_points else 1
        for i, val in enumerate(widget.data_points[:inner_w]):
            bar_h = self._calc_progress_value(val, max_val, inner_h)
            x = x0 + i
            for j in range(bar_h):
                y = y0 + inner_h - 1 - j
                if 0 <= y < height and 0 <= x < width:
                    canvas[y][x] = "#"


def _preflight_scene(scene: SceneConfig) -> Dict[str, Any]:
    """Run basic preflight checks and return results dict."""
    issues: List[str] = []
    warnings: List[str] = []
    hints: List[str] = []
    n = len(scene.widgets)
    issues, warnings, hints = _preflight_widget_checks(scene, issues, warnings, hints)
    warnings = _preflight_overlap_checks(scene, warnings)
    return {
        "issues": issues,
        "warnings": warnings,
        "hints": hints,
        "ok": not issues,
        "counts": {"issues": len(issues), "warnings": len(warnings), "widgets": n},
    }


def _preflight_widget_checks(
    scene: SceneConfig, issues: List[str], warnings: List[str], hints: List[str]
) -> Tuple[List[str], List[str], List[str]]:
    for i, w in enumerate(scene.widgets):
        _check_size(i, w, issues)
        _check_offcanvas(i, w, scene, issues, hints)
        _check_min_size_and_text(i, w, warnings)
        _check_text_overflow(i, w, warnings)
        _check_pixel_grid(i, w, scene, warnings, hints)
    return issues, warnings, hints


def _check_size(idx: int, w: WidgetConfig, issues: List[str]) -> None:
    if w.width < 1 or w.height < 1:
        issues.append(f"[{idx}] {w.type}: invalid size {w.width}x{w.height}")


def _check_offcanvas(
    idx: int, w: WidgetConfig, scene: SceneConfig, issues: List[str], hints: List[str]
) -> None:
    off_left = max(0, -w.x)
    off_top = max(0, -w.y)
    off_right = max(0, (w.x + w.width) - scene.width)
    off_bottom = max(0, (w.y + w.height) - scene.height)
    if not (off_left or off_top or off_right or off_bottom):
        return
    off_area = (off_left + off_right) * max(0, min(w.height, scene.height)) + (
        off_top + off_bottom
    ) * max(0, min(w.width, scene.width))
    approx_area = max(1, w.width * w.height)
    sev = "major" if (off_area / approx_area) > 0.25 else "minor"
    issues.append(
        f"[{idx}] {w.type}: off-canvas ({sev}) pos=({w.x},{w.y}) size={w.width}x{w.height}"
    )
    if sev == "minor":
        hints.append(f"[{idx}] Consider nudging into canvas or resizing")


def _check_min_size_and_text(idx: int, w: WidgetConfig, warnings: List[str]) -> None:
    w_type = (w.type or "").lower()
    if w_type in ["progressbar", "slider"] and w.height < 2:
        warnings.append(f"[{idx}] {w.type}: height < 2 may be hard to see")
    if w_type in ["checkbox", "radiobutton"] and w.height < 2:
        warnings.append(f"[{idx}] {w.type}: very small height may clip symbol")
    if (
        w_type in {"button", "checkbox", "radiobutton"}
        and not (getattr(w, "text", "") or "").strip()
    ):
        warnings.append(f"[{idx}] {w.type}: empty text")


def _check_text_overflow(idx: int, w: WidgetConfig, warnings: List[str]) -> None:
    text = str(getattr(w, "text", "") or "")
    if not text.strip():
        return

    # Preflight is pixel-based (export uses pixel coords). Assume fixed 6x8 font cells,
    # matching `src/ui_render.h` defaults in firmware.
    char_w = 6
    char_h = 8

    try:
        w_span = int(getattr(w, "width", 0) or 0)
        h_span = int(getattr(w, "height", 0) or 0)
    except (ValueError, TypeError):
        return

    pad_x = int(getattr(w, "padding_x", 0) or 0)
    pad_y = int(getattr(w, "padding_y", 0) or 0)
    border_pad = 1 if bool(getattr(w, "border", True)) else 0
    inner_w = w_span - 2 * border_pad - 2 * pad_x
    inner_h = h_span - 2 * border_pad - 2 * pad_y
    if inner_w <= 0 or inner_h <= 0:
        warnings.append(f"[{idx}] {w.type}: no space for text (size={w_span}x{h_span})")
        return

    max_chars = inner_w // max(1, char_w)
    max_lines_by_h = inner_h // max(1, char_h)
    if max_chars <= 0 or max_lines_by_h <= 0:
        warnings.append(f"[{idx}] {w.type}: no space for text (size={w_span}x{h_span})")
        return

    overflow = str(getattr(w, "text_overflow", "ellipsis") or "ellipsis").strip().lower()
    if overflow not in {"ellipsis", "wrap", "clip", "auto"}:
        overflow = "ellipsis"

    use_wrap = overflow == "wrap"
    if overflow == "auto":
        flat = text.replace("\t", " ").replace("\n", " ").strip()
        use_wrap = (max_lines_by_h >= 2) and (("\n" in text) or (len(flat) > max_chars))

    if use_wrap:
        max_lines = max_lines_by_h
        try:
            ml = getattr(w, "max_lines", None)
            if ml is not None and str(ml) != "":
                ml_i = int(ml)
                if ml_i > 0:
                    max_lines = min(max_lines, ml_i)
        except (ValueError, TypeError):
            pass
        max_lines = max(1, int(max_lines))

        # Fast wrap check: if we still have content after filling max_lines, it's truncated.
        remaining = text.replace("\t", " ").strip()
        paras = [p.strip() for p in remaining.splitlines() if p.strip()]
        if not paras:
            paras = [remaining]
        lines_used = 0
        truncated = False
        for para in paras:
            words = para.split()
            current = ""
            for word in words:
                cand = word if not current else f"{current} {word}"
                if len(cand) <= max_chars:
                    current = cand
                    continue
                if current:
                    lines_used += 1
                    if lines_used >= max_lines:
                        truncated = True
                        break
                    current = word
                    continue
                # Split a single long word; each chunk consumes a line.
                chunks = (len(word) + max(1, max_chars) - 1) // max(1, max_chars)
                lines_used += chunks
                if lines_used >= max_lines:
                    truncated = True
                    break
                current = ""
            if truncated:
                break
            if current:
                lines_used += 1
                if lines_used > max_lines:
                    truncated = True
                    break
        if truncated:
            warnings.append(f"[{idx}] {w.type}: text truncated (wrap)")
        return

    line = text.replace("\t", " ").replace("\n", " ").strip()
    if len(line) > max_chars:
        if overflow == "clip":
            warnings.append(f"[{idx}] {w.type}: text clipped to {max_chars} chars")
        else:
            warnings.append(f"[{idx}] {w.type}: text truncated (ellipsis) to {max_chars} chars")


def _check_pixel_grid(
    idx: int, w: WidgetConfig, scene: SceneConfig, warnings: List[str], hints: List[str]
) -> None:
    grid = getattr(scene, "grid_size", 8)
    if w.x % grid or w.y % grid:
        hints.append(f"[{idx}] {w.type}: position not aligned to {grid}px grid")
    if (w.width % 2) or (w.height % 2):
        warnings.append(f"[{idx}] {w.type}: odd size {w.width}x{w.height} may look fuzzy")


def _preflight_overlap_checks(scene: SceneConfig, warnings: List[str]) -> List[str]:
    def overlap(a: WidgetConfig, b: WidgetConfig) -> bool:
        return not (
            a.x + a.width <= b.x
            or b.x + b.width <= a.x
            or a.y + a.height <= b.y
            or b.y + b.height <= a.y
        )

    n = len(scene.widgets)
    for i in range(n):
        for j in range(i + 1, n):
            a = scene.widgets[i]
            b = scene.widgets[j]
            at = str(getattr(a, "type", "") or "").lower()
            bt = str(getattr(b, "type", "") or "").lower()
            # Overlaps with container-like widgets (panel/box) are expected (background layers).
            if at in {"panel", "box"} or bt in {"panel", "box"}:
                continue
            if overlap(a, b):
                warnings.append(f"[{i}] {a.type} overlaps [{j}] {b.type}")
    return warnings


def _auto_preflight_and_export(designer: "UIDesigner", json_path: str) -> None:
    """Run preflight checks after saving JSON.

    Phase 0 cleanup removed the legacy HTML/PNG auto-export hook to keep the
    repo focused on the embedded OS UI path (Pygame designer + C header export).
    """
    try:
        if not designer.current_scene or designer.current_scene not in designer.scenes:
            return
        scene = designer.scenes[designer.current_scene]
        result = _preflight_scene(scene)
        _log_preflight(result)
    except Exception as e:
        print(f"[WARN] Preflight failed: {e}")


def _log_preflight(result: Dict[str, Any]) -> None:
    counts = result["counts"]
    print("\n[INFO] Preflight:")
    if counts["issues"]:
        for m in result["issues"][:10]:
            print(f"  [fail] {m}")
    if counts["warnings"]:
        for m in result["warnings"][:10]:
            print(f"  [warn] {m}")
    print(
        f"  Summary: {counts['widgets']} widgets | {counts['issues']} issues | {counts['warnings']} warnings"
    )


# --- CLI interface, helpers, and WCAG utilities (extracted to ui_cli.py) ---
from ui_cli import (
    NAMED_COLORS,
    contrast_ratio,
    create_cli_interface,
    get_widget_help,
    parse_color,
    rel_lum,
    show_command_help,
)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UI Designer CLI")
    parser.add_argument(
        "--guided", action="store_true", help="Run guided wizard for quick scene creation"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Generate a demo scene showcasing states and animations"
    )
    parser.add_argument(
        "--script-file", default="", help="Run CLI commands from a file (one per line)"
    )
    parser.add_argument("--preset", default="", help="Screen preset: dashboard|menu|dialog")
    parser.add_argument("--export", action="store_true", help="Export after guided flow")
    parser.add_argument("--out-json", default="examples/guided_scene.json")
    parser.add_argument("--out-html", default="examples/guided_scene.html")
    parser.add_argument("--out-png", default="examples/guided_scene.png")
    parser.add_argument(
        "--export-c-header",
        nargs=2,
        metavar=("JSON", "HEADER"),
        help="Export JSON design to C header file",
    )
    args = parser.parse_args()

    # C header export mode
    if args.export_c_header:
        json_file, header_file = args.export_c_header
        if not json_file.strip():
            print("[FAIL] JSON path cannot be empty or whitespace-only")
            sys.exit(2)
        if not header_file.strip():
            print("[FAIL] Header path cannot be empty or whitespace-only")
            sys.exit(2)
        json_path = Path(json_file).resolve()
        if not json_path.exists():
            print(f"[FAIL] JSON file not found: {json_path}")
            sys.exit(1)
        import subprocess

        export_script = Path(__file__).parent / "tools" / "ui_export_c_header.py"
        if not export_script.exists():
            print(f"[FAIL] C export script not found: {export_script}")
            sys.exit(1)
        try:
            subprocess.run(
                [sys.executable, str(export_script), str(json_path), "-o", header_file], check=True
            )
        except (OSError, subprocess.SubprocessError) as e:
            print(f"[FAIL] C export failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.guided:
        # Minimal guided flow
        d = UIDesigner(128, 64)
        print("\nGuide Guided mode: Choose a preset [dashboard/menu/dialog/pixelhud]")
        preset = (
            args.preset
            or input("Preset (dashboard/menu/dialog/pixelhud): ").strip().lower()
            or "dashboard"
        )
        scene_name = input("Scene name (Home): ").strip() or "Home"
        try:
            w = int(input("Width (128): ") or "128")
            h = int(input("Height (64): ") or "64")
        except (ValueError, TypeError):
            w, h = 128, 64
        d.width, d.height = w, h
        d.create_scene(scene_name)
        # Apply preset templates
        if preset == "dashboard":
            d.add_widget(
                WidgetType.LABEL,
                x=0,
                y=0,
                width=128,
                height=10,
                text=scene_name,
                border=False,
                align="center",
                style="bold",
                color_fg="cyan",
            )
            d.add_widget(WidgetType.GAUGE, x=4, y=14, width=w // 3, height=h // 2, value=72)
            d.add_widget(
                WidgetType.GAUGE, x=w // 3 + 8, y=14, width=w // 3, height=h // 2, value=42
            )
            d.add_widget(WidgetType.PROGRESSBAR, x=4, y=h - 14, width=w - 8, height=8, value=60)
            d.add_widget(WidgetType.BUTTON, x=w - 48, y=2, width=44, height=10, text="Menu")
        elif preset == "menu":
            d.add_widget(
                WidgetType.LABEL,
                x=0,
                y=0,
                width=w,
                height=10,
                text=scene_name,
                border=False,
                align="center",
                style="bold",
            )
            y = 14
            for label in ["Start", "Settings", "About"]:
                d.add_widget(
                    WidgetType.BUTTON, x=(w - 60) // 2, y=y, width=60, height=12, text=label
                )
                y += 14
        elif preset == "pixelhud":
            d.enable_pixel_art_mode()
            sc = d.scenes[d.current_scene or ""]
            w, h = sc.width, sc.height
            d.add_widget(
                WidgetType.LABEL,
                x=0,
                y=0,
                width=w,
                height=10,
                text=scene_name.upper(),
                border=False,
                align="center",
                style="bold",
                color_fg="cyan",
            )
            d.add_widget(
                WidgetType.LABEL,
                x=4,
                y=14,
                width=60,
                height=8,
                text="PWR: 084%",
                border=False,
                align="left",
                color_fg="white",
            )
            d.add_widget(
                WidgetType.PROGRESSBAR,
                x=4,
                y=h - 14,
                width=w - 8,
                height=8,
                value=60,
                border=True,
                border_style="single",
                style="segmented",
            )
        else:  # dialog
            d.add_widget(WidgetType.PANEL, x=6, y=10, width=w - 12, height=h - 20)
            d.add_widget(
                WidgetType.LABEL,
                x=10,
                y=14,
                width=w - 20,
                height=8,
                text="Confirm action[OK]",
                align="center",
            )
            d.add_widget(WidgetType.BUTTON, x=w // 2 - 44, y=h - 18, width=40, height=12, text="OK")
            d.add_widget(
                WidgetType.BUTTON, x=w // 2 + 4, y=h - 18, width=40, height=12, text="Cancel"
            )

        # Export flow
        out_json = args.out_json
        out_html = args.out_html
        Path(os.path.dirname(out_json)).mkdir(parents=True, exist_ok=True)
        # Save triggers preflight by default
        d.save_to_json(out_json)
        # Optional: write an ASCII-based HTML preview for quick inspection.
        try:
            d.export_to_html(out_html)
        except OSError:
            pass
        print(f"\n[OK] Guided scene created:\n  JSON: {out_json}\n  HTML: {out_html}")
        sys.exit(0)

    if args.demo:
        # Build a small demo scene with state variants and an animation
        d = UIDesigner(128, 64)
        d.create_scene("Demo")
        w, h = 128, 64
        # Title
        d.add_widget(
            WidgetType.LABEL,
            x=0,
            y=0,
            width=w,
            height=10,
            text="Demo",
            border=False,
            align="center",
            style="bold",
            color_fg="cyan",
        )
        # Button with states
        d.add_widget(WidgetType.BUTTON, x=(w - 50) // 2, y=16, width=50, height=12, text="Play")
        # Gauge and progress bar
        d.add_widget(WidgetType.GAUGE, x=8, y=14, width=32, height=24, value=70)
        d.add_widget(WidgetType.PROGRESSBAR, x=8, y=h - 12, width=w - 16, height=8, value=40)
        sc = d.scenes[d.current_scene or ""]
        # Define button states
        btn = sc.widgets[1]
        btn.state_overrides = {
            "hover": {"style": "bold", "color_bg": color_hex("legacy_gray24")},
            "active": {"style": "inverse", "color_bg": color_hex("legacy_gray8")},
            "disabled": {"enabled": False, "style": "default"},
        }
        btn.state = "default"
        # Tag animation and set preview context for export consistency
        btn.animations.append("bounce")
        # Use provided out paths or default under output/demo_*
        out_json = (
            args.out_json
            if args.out_json != "output/guided_scene.json"
            else "output/demo_scene.json"
        )
        out_html = (
            args.out_html
            if args.out_html != "output/guided_scene.html"
            else "output/demo_scene.html"
        )
        Path(os.path.dirname(out_json)).mkdir(parents=True, exist_ok=True)
        # Save triggers preflight by default
        d.save_to_json(out_json)
        # Optional: write an ASCII-based HTML preview for quick inspection.
        try:
            d.export_to_html(out_html)
        except OSError:
            pass
        print(f"\n[OK] Demo scene created:\n  JSON: {out_json}\n  HTML: {out_html}")
        sys.exit(0)

    # Scripted CLI mode
    if args.script_file:
        try:
            with open(args.script_file, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines()]
            # Drop blanks and comments
            lines = [ln for ln in lines if ln and not ln.lstrip().startswith("#")]
            create_cli_interface(commands=lines)
            sys.exit(0)
        except OSError as e:
            print(f"[FAIL] Failed to run script file: {e}")
            sys.exit(1)

    create_cli_interface()


# Re-export for backward compatibility
__all__ = [
    "NAMED_COLORS",
    "BorderStyle",
    "Scene",
    "SceneConfig",
    "UIDesigner",
    "WidgetConfig",
    "WidgetType",
    "contrast_ratio",
    "create_cli_interface",
    "get_widget_help",
    "parse_color",
    "rel_lum",
    "show_command_help",
]
