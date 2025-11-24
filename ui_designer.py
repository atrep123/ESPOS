#!/usr/bin/env python3
"""
Visual UI Designer for ESP32 Simulator
Drag-and-drop widget editor with live preview and code generation
"""

import copy
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from design_tokens import color_hex
from ui_models import (
    BorderStyle,  # noqa: F401 - re-exported
    ConstraintBaseline,
    Constraints,
    Scene,  # noqa: F401 - re-exported
    SceneConfig,
    WidgetConfig,
    WidgetType,
    _coerce_bool_flag,
    _coerce_choice,
    _empty_constraints,
    _make_baseline,
    _normalize_int_list,
)

# CLI message constants
MSG_INVALID_INDEX = "Invalid index"
MSG_NO_SCENE = "No scene loaded"
MSG_INDEX_INTEGER = "Index must be integer"
MSG_FAILED = "❌ Failed"
MSG_UNKNOWN_ANIM = "Unknown animation name"

PREVIEW_SCRIPT = os.path.join(os.path.dirname(__file__), "ui_designer_preview.py")


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
        # Magnetic snapping settings
        self.snap_edges = True
        self.snap_centers = True
        self.snap_tolerance = 3
        self.snap_fluid = True  # fluid mode ignores strict grid when snapping
        self.show_guides = True
        self.last_guides: List[Dict[str, Any]] = []

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
            "light": {
                "bg": color_hex("theme_light_bg"),
                "text": color_hex("theme_light_text"),
                "primary": color_hex("theme_light_primary"),
                "secondary": color_hex("theme_light_secondary"),
                "accent": color_hex("theme_light_accent"),
                "danger": color_hex("theme_light_danger"),
            },
            "dark": {
                "bg": color_hex("theme_dark_bg"),
                "text": color_hex("theme_dark_text"),
                "primary": color_hex("theme_dark_primary"),
                "secondary": color_hex("theme_dark_secondary"),
                "accent": color_hex("theme_dark_accent"),
                "danger": color_hex("theme_dark_danger"),
            },
            "hc": {
                "bg": color_hex("theme_hc_bg"),
                "text": color_hex("theme_hc_text"),
                "primary": color_hex("theme_hc_primary"),
                "secondary": color_hex("theme_hc_secondary"),
                "accent": color_hex("theme_hc_accent"),
                "danger": color_hex("theme_hc_danger"),
            },
            "cyber": {
                "bg": color_hex("theme_cyber_bg"),
                "text": color_hex("theme_cyber_text"),
                "primary": color_hex("theme_cyber_primary"),
                "secondary": color_hex("theme_cyber_secondary"),
                "accent": color_hex("theme_cyber_accent"),
                "danger": color_hex("theme_cyber_danger"),
            },
        }
        self.theme_contrast_min = 4.5

        # Animation preview context
        self.anim_context: Optional[Dict[str, Any]] = None

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
        if self.current_scene and self.current_scene in self.scenes:
            scene_obj = self.scenes[self.current_scene]
            payload = asdict(scene_obj)
            state = json.dumps(payload)
            self.undo_stack.append(state)
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            # Lightweight diff summary (store alongside state for history preview)
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
            except Exception:
                pass
            # Autosave snapshot (undo-safe)
            try:
                backup_dir = Path.home() / ".esp32os" / "designer_backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                scene_name = (self.current_scene or "scene").replace(" ", "_")
                snap_path = backup_dir / f"{scene_name}_{ts}.json"
                with open(snap_path, "w", encoding="utf-8") as f:
                    f.write(state)
            except Exception:
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
        except Exception:
            return None

    def snap_position(self, x: int, y: int) -> Tuple[int, int]:
        """Snap coordinates to grid"""
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
        x, y = self._apply_best_offset(
            x, y, widget, scene, best_dx, best_dy, best_vline, best_hline
        )
        return self._clamp_to_scene(x, y, widget, scene)

    def _widget_bounds(self, widget: WidgetConfig, x: int, y: int) -> Dict[str, int]:
        return {
            "left": x,
            "right": x + widget.width,
            "top": y,
            "bottom": y + widget.height,
            "cx": x + widget.width // 2,
            "cy": y + widget.height // 2,
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
        widget: WidgetConfig,
        scene: SceneConfig,
        best_dx: Optional[int],
        best_dy: Optional[int],
        best_vline: Optional[Tuple[int, int, int, str]],
        best_hline: Optional[Tuple[int, int, int, str]],
    ) -> Tuple[int, int]:
        if best_dx is not None:
            x += best_dx
            if best_vline is not None:
                vx, vy1, vy2, k = best_vline
                self.last_guides.append(
                    {
                        "type": "v",
                        "x": vx,
                        "y1": max(0, vy1),
                        "y2": min(scene.height - 1, vy2),
                        "k": k,
                    }
                )
        if best_dy is not None:
            y += best_dy
            if best_hline is not None:
                hy, hx1, hx2, k = best_hline
                self.last_guides.append(
                    {
                        "type": "h",
                        "y": hy,
                        "x1": max(0, hx1),
                        "x2": min(scene.width - 1, hx2),
                        "k": k,
                    }
                )
        return x, y

    def _clamp_to_scene(
        self, x: int, y: int, widget: WidgetConfig, scene: SceneConfig
    ) -> Tuple[int, int]:
        x = max(0, min(scene.width - widget.width, x))
        y = max(0, min(scene.height - widget.height, y))
        return x, y

    def create_scene(self, name: str) -> SceneConfig:
        """Create new scene"""
        scene = SceneConfig(name=name, width=self.width, height=self.height, widgets=[])
        self.scenes[name] = scene
        self.current_scene = name
        return scene

    # --- Responsive helpers ---
    def set_responsive_base(self, scene_name: Optional[str] = None):
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        sc = self.scenes[scene_name]
        sc.base_width, sc.base_height = sc.width, sc.height

        # Store baseline into widget.constraints.b for later use
        for w in sc.widgets:
            b = _make_baseline(
                w.x,
                w.y,
                w.width,
                w.height,
                sc.base_width,
                sc.base_height,
            )
            w.constraints = w.constraints or _empty_constraints()
            w.constraints["b"] = b
            # Provide default anchors if absent
            w.constraints.setdefault("ax", "left")
            w.constraints.setdefault("ay", "top")
            w.constraints.setdefault("sx", False)
            w.constraints.setdefault("sy", False)
            w.constraints.setdefault("mx", 0)
            w.constraints.setdefault("my", 0)
            w.constraints.setdefault("mr", 0)
            w.constraints.setdefault("mb", 0)

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
            c = cast(Constraints, w.constraints or _empty_constraints())
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
        return cast(
            ConstraintBaseline,
            c.get("b") or _make_baseline(w.x, w.y, w.width, w.height, bw, bh),
        )

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
            print(f"⚠️ Scene '{scene_name or ''}' not found; widget not added.")
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
        except Exception as e:
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
            border=_coerce_bool_flag(kw.get("border", True), True),
            border_style=_coerce_choice(
                kw.get("border_style", "single"),
                ("none", "single", "double", "rounded", "bold", "dashed"),
                "single",
            ),
            align=_coerce_choice(kw.get("align", "left"), ("left", "center", "right"), "left"),
            valign=_coerce_choice(
                kw.get("valign", "middle"), ("top", "middle", "bottom"), "middle"
            ),
            value=int(kw.get("value", 0)) if kw.get("value") is not None else 0,
            min_value=int(kw.get("min_value", 0)),
            max_value=int(kw.get("max_value", 100)),
            checked=_coerce_bool_flag(kw.get("checked", False), False),
            enabled=_coerce_bool_flag(kw.get("enabled", True), True),
            visible=_coerce_bool_flag(kw.get("visible", True), True),
            icon_char=str(kw.get("icon_char", "")),
            data_points=_normalize_int_list(kw.get("data_points", []) or []),
            z_index=int(kw.get("z_index", 0)),
            padding_x=int(kw.get("padding_x", 1)),
            padding_y=int(kw.get("padding_y", 0)),
            margin_x=int(kw.get("margin_x", 0)),
            margin_y=int(kw.get("margin_y", 0)),
        )

    def add_widget_from_template(
        self, template_name: str, _widget_id: str, x: int, y: int, **kwargs: Any
    ):
        """Add widget from template with custom properties"""
        if template_name not in self.templates:
            print(f"❌ Template '{template_name}' not found")
            return

        widget = self._clone_template_with_overrides(template_name, x, y, kwargs)
        self.add_widget(widget)

    def _clone_template_with_overrides(
        self, template_name: str, x: int, y: int, overrides: Dict[str, Any]
    ) -> WidgetConfig:
        widget = copy.deepcopy(self.templates[template_name])
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
        except Exception:
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
        except Exception:
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
        keys = [
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
        changed = diff["widgets"]["changed"]
        for i in range(n):
            changes = {
                k: {"a": wa[i].get(k), "b": wb[i].get(k)}
                for k in keys
                if wa[i].get(k) != wb[i].get(k)
            }
            if changes:
                changed.append({"index": i, "changes": changes})

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
                    "widgets": [asdict(w) for w in scene.widgets],
                }
                for name, scene in self.scenes.items()
            },
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[OK] Design saved: {filename}")
        # Auto: run preflight and export previews unless disabled
        try:
            if os.environ.get("ESP32OS_AUTO_EXPORT", "1") != "0":
                _auto_preflight_and_export(self, filename)
        except Exception as _e:
            print(f"[WARN] Auto-export skipped: {_e}")

    def load_from_json(self, filename: str):
        """Load design from JSON file"""
        data = self._read_json_file(filename)
        self.width = data.get("width", 128)
        self.height = data.get("height", 64)
        self.scenes = self._build_scenes_from_data(data)
        if self.scenes:
            self.current_scene = list(self.scenes.keys())[0]
        print(f"[OK] Design loaded: {filename}")
        self._record_json_watch(filename)

    def _read_json_file(self, filename: str) -> Dict[str, Any]:
        with open(filename, "r") as f:
            return json.load(f)

    def _build_scenes_from_data(self, data: Dict[str, Any]) -> Dict[str, SceneConfig]:
        scenes: Dict[str, SceneConfig] = {}
        scenes_data = data.get("scenes", {})

        # Support both dict and list formats
        if isinstance(scenes_data, list):
            scenes_dict = {
                scene.get("id", f"scene_{i}"): scene for i, scene in enumerate(scenes_data)
            }
        else:
            scenes_dict = scenes_data

        # Get default width/height from display settings
        display = data.get("display", {})
        default_width = display.get("width", 320)
        default_height = display.get("height", 240)

        for name, scene_data in scenes_dict.items():
            # Parse widgets, converting 'id' to '_widget_id' if present
            widgets = []
            for w in scene_data.get("widgets", []):
                widget_dict = dict(w)
                if "id" in widget_dict:
                    widget_dict["_widget_id"] = widget_dict.pop("id")
                widgets.append(WidgetConfig(**widget_dict))

            scenes[name] = SceneConfig(
                name=scene_data.get("name", name),
                width=scene_data.get("width", default_width),
                height=scene_data.get("height", default_height),
                widgets=widgets,
                bg_color=scene_data.get("bg_color", "black"),
            )
        return scenes

    def _record_json_watch(self, filename: str) -> None:
        try:
            self._last_loaded_json = filename
            self._json_watch_mtime = os.path.getmtime(filename)
        except Exception:
            self._last_loaded_json = None
            self._json_watch_mtime = None

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
            code_lines.append("        Widget(")
            code_lines.append(f"            type='{widget.type}',")
            code_lines.append(f"            x={widget.x},")
            code_lines.append(f"            y={widget.y},")
            code_lines.append(f"            width={widget.width},")
            code_lines.append(f"            height={widget.height},")
            if widget.text:
                code_lines.append(f"            text='{widget.text}',")
            if widget.style != "default":
                code_lines.append(f"            style='{widget.style}',")
            if widget.color_fg != "white":
                code_lines.append(f"            color_fg='{widget.color_fg}',")
            if widget.color_bg != "black":
                code_lines.append(f"            color_bg='{widget.color_bg}',")
            if not widget.border:
                code_lines.append(f"            border={widget.border},")
            if widget.align != "left":
                code_lines.append(f"            align='{widget.align}',")
            code_lines.append("        ),")

        code_lines.append("    ]")
        code_lines.append("")
        code_lines.append("")
        code_lines.append("if __name__ == '__main__':")
        code_lines.append(f"    widgets = create_{scene.name.lower()}_scene()")
        code_lines.append(f"    print(f'Created {{len(widgets)}} widgets for {scene.name} scene')")

        return "\n".join(code_lines)

    def export_code(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as Python code file"""
        code = self.generate_python_code(scene_name)

        with open(filename, "w") as f:
            f.write(code)

        print(f"[OK] Code exported: {filename}")

    def auto_layout(
        self, layout_type: str = "vertical", spacing: int = 4, scene_name: Optional[str] = None
    ):
        """Auto-arrange widgets in scene"""
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
            widget.x = (scene.width - widget.width) // 2
            widget.y = y_offset
            y_offset += widget.height + spacing

    def _layout_horizontal(self, scene: SceneConfig, spacing: int) -> None:
        x_offset = spacing
        for widget in scene.widgets:
            widget.x = x_offset
            widget.y = (scene.height - widget.height) // 2
            x_offset += widget.width + spacing

    def _layout_grid(self, scene: SceneConfig, spacing: int) -> None:
        cols = max(1, int((scene.width + spacing) / (40 + spacing)))  # Assume 40px avg width
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

    def align_widgets(
        self, alignment: str, widget_indices: List[int], scene_name: Optional[str] = None
    ):
        """Align selected widgets"""
        scene = self._get_scene(scene_name)
        if not scene or not widget_indices:
            return
        self._save_state()
        widgets = self._widgets_by_indices(scene, widget_indices)
        if not widgets:
            return
        alignment = (alignment or "").lower()

        def _align_edge(ws: List[WidgetConfig], edge: str) -> None:
            if not ws:
                return
            if edge == "left":
                target = min(w.x for w in ws)
                for w in ws:
                    w.x = target
            elif edge == "right":
                target = max(w.x + w.width for w in ws)
                for w in ws:
                    w.x = target - w.width
            elif edge == "top":
                target = min(w.y for w in ws)
                for w in ws:
                    w.y = target
            elif edge == "bottom":
                target = max(w.y + w.height for w in ws)
                for w in ws:
                    w.y = target - w.height

        align_map = {
            "left": lambda ws: _align_edge(ws, "left"),
            "right": lambda ws: _align_edge(ws, "right"),
            "top": lambda ws: _align_edge(ws, "top"),
            "bottom": lambda ws: _align_edge(ws, "bottom"),
            "center_h": lambda ws: self._align_center(ws, axis="x"),
            "center_v": lambda ws: self._align_center(ws, axis="y"),
        }
        action = align_map.get(alignment)
        if action:
            action(widgets)

    def distribute_widgets(
        self, direction: str, widget_indices: List[int], scene_name: Optional[str] = None
    ):
        """Distribute widgets evenly"""
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
            avg = sum(w.x + w.width // 2 for w in widgets) // len(widgets)
            for w in widgets:
                w.x = avg - w.width // 2
        elif axis == "y":
            avg = sum(w.y + w.height // 2 for w in widgets) // len(widgets)
            for w in widgets:
                w.y = avg - w.height // 2

    def _widgets_by_indices(self, scene: SceneConfig, indices: List[int]) -> List[WidgetConfig]:
        return [scene.widgets[i] for i in indices if 0 <= i < len(scene.widgets)]

    def _distribute_axis(self, items: List[Tuple[int, WidgetConfig]], axis: str) -> None:
        if not items:
            return
        key = (lambda w: w[1].x) if axis == "x" else (lambda w: w[1].y)
        size = (lambda w: w[1].width) if axis == "x" else (lambda w: w[1].height)
        items.sort(key=key)
        start = key(items[0])
        end = key(items[-1]) + size(items[-1])
        total_span = sum(size(w) for w in items)
        spacing = (end - start - total_span) / max(1, (len(items) - 1))
        pos = start
        for _, widget in items:
            if axis == "x":
                widget.x = int(pos)
                pos += widget.width + spacing
            else:
                widget.y = int(pos)
                pos += widget.height + spacing

    def export_to_html(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as HTML preview"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return

        scene = self.scenes[scene_name]
        preview_raw = self.preview_ascii(scene_name)
        preview = escape(preview_raw)
        body_bg = color_hex("legacy_gray5")
        body_text = color_hex("legacy_green")
        preview_bg = color_hex("shadow")
        preview_border = color_hex("legacy_green")
        info_color = color_hex("legacy_cyan")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{scene.name} - UI Design Preview</title>
    <style>
        body {{
            background: {body_bg};
            color: {body_text};
            font-family: 'Courier New', monospace;
            padding: 20px;
        }}
        .preview {{
            background: {preview_bg};
            border: 2px solid {preview_border};
            padding: 20px;
            display: inline-block;
            white-space: pre;
            line-height: 1.2;
        }}
        .info {{
            margin-top: 20px;
            color: {info_color};
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

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"[OK] HTML preview exported: {filename}")

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
                        canvas[y][x] = "·"
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
        for g in self.last_guides:
            if g.get("type") == "v":
                x = g["x"]
                for y in range(max(0, g["y1"]), min(scene.height, g["y2"] + 1)):
                    if 0 <= x < scene.width:
                        canvas[y][x] = "┆"
            elif g.get("type") == "h":
                y = g["y"]
                for x in range(max(0, g["x1"]), min(scene.width, g["x2"] + 1)):
                    if 0 <= y < scene.height:
                        canvas[y][x] = "┄"

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
        }
        handler = handlers.get(widget.type)
        if handler:
            handler(canvas, widget, width, height)
        elif widget.text:
            self._draw_text(canvas, widget, width, height)

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
        """Draw widget border with bounds checks."""
        x0, y0 = widget.x, widget.y
        x1 = widget.x + widget.width - 1
        y1 = widget.y + widget.height - 1
        # Top/bottom
        for x in range(max(0, x0), min(x1 + 1, width)):
            if 0 <= y0 < height:
                canvas[y0][x] = border_chars["h"]
            if 0 <= y1 < height:
                canvas[y1][x] = border_chars["h"]
        # Left/right
        for y in range(max(0, y0), min(y1 + 1, height)):
            if 0 <= x0 < width:
                canvas[y][x0] = border_chars["v"]
            if 0 <= x1 < width:
                canvas[y][x1] = border_chars["v"]
        # Corners
        if 0 <= y0 < height and 0 <= x0 < width:
            canvas[y0][x0] = border_chars["tl"]
        if 0 <= y0 < height and 0 <= x1 < width:
            canvas[y0][x1] = border_chars["tr"]
        if 0 <= y1 < height and 0 <= x0 < width:
            canvas[y1][x0] = border_chars["bl"]
        if 0 <= y1 < height and 0 <= x1 < width:
            canvas[y1][x1] = border_chars["br"]

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

    def _apply_state_overrides_inplace(self, widget: WidgetConfig) -> None:
        try:
            overrides = (widget.state_overrides or {}).get(widget.state or "default")
            if overrides:
                for k, v in overrides.items():
                    if hasattr(widget, k):
                        try:
                            setattr(widget, k, type(getattr(widget, k))(v))
                        except Exception:
                            setattr(widget, k, v)
        except Exception:
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
            if name == "bounce":
                import math

                amp = max(1, min(3, scene.height // 10))
                dy = int(round(amp * math.sin(2 * math.pi * (t % steps) / steps)))
                widget.y = max(0, min(scene.height - widget.height, widget.y + dy))
            elif name == "slideinleft":
                # from -width .. to current x
                start = -widget.width
                end = widget.x
                pos = start + (end - start) * (t % steps) / steps
                widget.x = max(-widget.width, min(scene.width - 1, int(pos)))
            elif name == "pulse":
                # Toggle border style for visual emphasis
                if (t % 2) == 0:
                    widget.border_style = "bold"
                else:
                    widget.border_style = "single"
            elif name == "fadein":
                # Simulate by switching style
                if (t % 2) == 0:
                    widget.style = "highlight"
                else:
                    widget.style = "default"
        except Exception:
            pass

    def _get_border_chars(self, style: str) -> Dict[str, str]:
        """Get border characters for style"""
        styles = {
            "single": {"h": "─", "v": "│", "tl": "┌", "tr": "┐", "bl": "└", "br": "┘"},
            "double": {"h": "═", "v": "║", "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝"},
            "rounded": {"h": "─", "v": "│", "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯"},
            "bold": {"h": "━", "v": "┃", "tl": "┏", "tr": "┓", "bl": "┗", "br": "┛"},
            "dashed": {"h": "┄", "v": "┆", "tl": "┌", "tr": "┐", "bl": "└", "br": "┘"},
        }
        return styles.get(style, styles["single"])

    def _draw_text(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw text with alignment"""
        text_y = widget.y + widget.height // 2
        if widget.valign == "top":
            text_y = widget.y + (1 if widget.border else 0) + widget.padding_y
        elif widget.valign == "bottom":
            text_y = widget.y + widget.height - (1 if widget.border else 0) - widget.padding_y - 1

        text_x = widget.x + widget.padding_x + (1 if widget.border else 0)

        if widget.align == "center":
            text_x = widget.x + (widget.width - len(widget.text)) // 2
        elif widget.align == "right":
            text_x = (
                widget.x
                + widget.width
                - len(widget.text)
                - widget.padding_x
                - (1 if widget.border else 0)
            )

        if 0 <= text_y < height:
            self._write_text_line(canvas, text_y, text_x, widget.text, width)

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
        progress = self._calc_progress_value(widget.value, widget.max_value, inner_w)
        bar_y = widget.y + widget.height // 2
        if 0 <= bar_y < height:
            for i in range(inner_w):
                x = x0 + i
                if 0 <= x < width:
                    canvas[bar_y][x] = "█" if i < progress else "░"

    def _draw_gauge(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw gauge (simple bar)"""
        _x0, _y0, _inner_w, inner_h = self._inner_box(widget)
        progress = self._calc_progress_value(widget.value, widget.max_value, inner_h)
        gauge_x = widget.x + widget.width // 2
        gauge_y_start = widget.y + widget.height - (1 if widget.border else 0) - 1
        for i in range(inner_h):
            y = gauge_y_start - i
            if 0 <= y < height and 0 <= gauge_x < width:
                canvas[y][gauge_x] = "█" if i < progress else "░"

    def _draw_checkbox(
        self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int
    ):
        """Draw checkbox"""
        check_y = widget.y + widget.height // 2
        check_x = widget.x + (1 if widget.border else 0) + 1

        if 0 <= check_y < height and 0 <= check_x < width:
            canvas[check_y][check_x] = "☑" if widget.checked else "☐"

        # Draw label if text exists
        if widget.text and 0 <= check_y < height:
            text_x = check_x + 2
            for i, ch in enumerate(widget.text):
                x = text_x + i
                if 0 <= x < width:
                    canvas[check_y][x] = ch

    def _draw_slider(self, canvas: List[List[str]], widget: WidgetConfig, width: int, height: int):
        """Draw slider"""
        x0, _y0, inner_w, _inner_h = self._inner_box(widget)
        slider_pos = self._calc_slider_pos(widget.value, widget.max_value, max(0, inner_w - 1))
        slider_y = widget.y + widget.height // 2
        if 0 <= slider_y < height:
            for i in range(inner_w):
                x = x0 + i
                if 0 <= x < width:
                    canvas[slider_y][x] = "▓" if i == slider_pos else "─"

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
                    canvas[y][x] = "▌"


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
        w.type in ["label", "button", "textbox", "checkbox", "radiobutton"]
        and not (w.text or "").strip()
    ):
        warnings.append(f"[{idx}] {w.type}: empty text")


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
            if overlap(scene.widgets[i], scene.widgets[j]):
                warnings.append(
                    f"[{i}] {scene.widgets[i].type} overlaps [{j}] {scene.widgets[j].type}"
                )
    return warnings


def _auto_preflight_and_export(designer: "UIDesigner", json_path: str) -> None:
    """Run preflight and generate HTML/PNG next to the JSON file."""
    try:
        if not designer.current_scene or designer.current_scene not in designer.scenes:
            return
        scene = designer.scenes[designer.current_scene]
        result = _preflight_scene(scene)
        _log_preflight(result)
    except Exception as e:
        print(f"[WARN] Preflight failed: {e}")

    try:
        _run_auto_export(designer, json_path)
    except Exception as e:
        print(f"[WARN] Auto-export failed: {e}")


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


def _run_auto_export(designer: "UIDesigner", json_path: str) -> None:
    base, _ = os.path.splitext(json_path)
    out_html = base + ".html"
    out_png = base + ".png"
    designer.export_to_html(out_html)
    try:
        import subprocess
        import sys as _sys

        cmd = [
            _sys.executable,
            PREVIEW_SCRIPT,
            "--headless-preview",
            "--in-json",
            json_path,
            "--out-png",
            out_png,
            "--out-html",
            out_html,
        ]
        subprocess.run(cmd, check=False)
    except Exception:
        pass
    print(f"[OK] Auto-export: {out_html} | {out_png}")


def create_cli_interface(commands: Optional[List[str]] = None):  # noqa: C901 - CLI handler intentionally complex  # NOSONAR
    """Advanced CLI interface for UI designer.
    If 'commands' is provided, runs non-interactively executing each command in order.
    """
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
    print("  duplicate <idx> [dx] [dy]            - Alias for clone")
    print("  move <idx> <dx> <dy>                 - Move widget")
    print("  resize <idx> <dw> <dh>               - Resize widget")
    print("  delete <idx>                         - Delete widget")
    print("  lock <idx> <on|off|toggle>           - Toggle edit lock")
    print("  select <idx>                         - Select widget for context")
    print("  edit <idx> <prop> <value>            - Edit property")
    print()
    print("🎯 Advanced Features:")
    print("  undo                    - Undo last operation")
    print("  redo                    - Redo operation")
    print("  grid <on|off>           - Toggle grid")
    print("  snap <on|off>           - Toggle snap to grid")
    print("  guides <on|off>         - Toggle guide overlay in preview")
    print("  snaptol <px>            - Set magnetic snapping tolerance (px)")
    print("  snapmode <pixel|fluid>  - Pixel uses grid; fluid favors magnets")
    print("  preview [grid]          - Show ASCII preview")
    print("  templates               - List available templates")
    print("  layout <type>           - Auto-layout (vertical/horizontal/grid)")
    print("  align <type> <ids...>   - Align widgets (left/right/top/bottom/center_h/center_v)")
    print("  distribute <dir> <ids...> - Distribute evenly (horizontal/vertical)")
    print("  tree                    - Show group membership and widget hierarchy")
    print("  gridcols <4|8|12>       - Set grid columns and recompute grid size")
    print("  bp <WxH>                - Set breakpoint (scene size), e.g. 128x64")
    print("  resp base               - Record current as responsive base")
    print("  resp apply              - Apply constraints to current size")
    print("  state define <idx> <name> k=v [k=v]...  - Define/merge state overrides")
    print("  state set <idx> <name>                  - Switch current state")
    print("  state list <idx>                        - List states")
    print("  state clear <idx> <name>                - Remove a state override")
    print("  anim list                               - Show built-in animations")
    print("  anim add <idx> <name>                   - Attach an animation tag to widget")
    print("  anim clear <idx> <name>                 - Remove animation tag from widget")
    print("  anim preview <idx> <name> <steps> <t>   - Preview a single animation frame")
    print("  anim play <idx> <name> <steps> [delay]  - Play animation frames (delay ms)")
    print("  context [idx]           - Show contextual help and quick actions")
    print()
    print("💾 File Operations:")
    print("  save <file>             - Save to JSON")
    print("  load <file>             - Load from JSON")
    print("  export <file>           - Export Python code")
    print("  restore [latest|list|<index>] - Restore from autosave snapshot")
    print("  checkpoint <name>       - Create a named checkpoint of current scene")
    print("  checkpoints             - List named checkpoints")
    print("  rollback <name>         - Restore the scene from a checkpoint")
    print("  diff <A> [B]            - Diff checkpoints A and B (or A vs current)")
    print()
    print("👥 Groups:")
    print("  group create <name> <idx...>   - Create a group")
    print("  group add <name> <idx...>      - Add widgets to group")
    print("  group remove <name> <idx...>   - Remove widgets from group")
    print("  group delete <name>            - Delete a group")
    print("  group list                     - List groups")
    print("  group lock <name> <on|off|toggle>    - Lock/unlock all members")
    print("  group visible <name> <on|off|toggle> - Show/hide all members")
    print()
    print("🔁 Symbols:")
    print("  symbol save <name> <idx...>    - Save selection as a symbol")
    print("  symbol list                    - List saved symbols")
    print("  symbol place <name> <x> <y>    - Place a symbol instance")
    print()
    print("🎨 Themes & WCAG:")
    print("  theme list                    - List theme presets")
    print("  theme set <name>              - Set scene theme and bg color")
    print("  theme bind <idx> <fg|bg> <role> - Bind widget color to role")
    print("  theme apply                   - Apply bound theme roles to widgets")
    print("  contrast [min]                - Audit contrast (optionally set min, e.g., 4.5)")
    print()
    print("❓ Help & Info:")
    print("  help [command]          - Show help")
    print("  widgets                 - List available widget types")
    print("  quit                    - Exit")
    print()
    print("💡 Widget types: label, box, button, gauge, progressbar,")
    print("   checkbox, radiobutton, slider, textbox, panel, icon, chart")
    print()

    cmd_queue: Optional[List[str]] = list(commands) if commands is not None else None
    while True:
        try:
            if cmd_queue is not None:
                if not cmd_queue:
                    break
                cmd = cmd_queue.pop(0).strip()
                # Echo command to output for clarity in scripted runs
                if cmd:
                    print(f"> {cmd}")
            else:
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
            if action == "quit" or action == "exit":
                break

            elif action == "new":
                if len(parts) < 2:
                    print("Usage: new <scene_name>")
                    continue
                designer.create_scene(parts[1])
                print(f"✓ Created scene: {parts[1]}")

            elif action == "scenes":
                if designer.scenes:
                    print("\n📋 Available scenes:")
                    for name in designer.scenes:
                        marker = " (current)" if name == designer.current_scene else ""
                        print(f"  - {name}{marker}")
                else:
                    print("No scenes created")

            elif action == "switch":
                if len(parts) < 2:
                    print("Usage: switch <scene_name>")
                    continue
                if parts[1] in designer.scenes:
                    designer.current_scene = parts[1]
                    print(f"✓ Switched to scene: {parts[1]}")
                else:
                    print(f"❌ Scene '{parts[1]}' not found")

            # Widget Operations
            elif action == "add":
                if len(parts) < 6:
                    print("Usage: add <type> <x> <y> <w> <h> [text]")
                    continue

                widget = WidgetConfig(
                    type=parts[1],
                    x=int(parts[2]),
                    y=int(parts[3]),
                    width=int(parts[4]),
                    height=int(parts[5]),
                    text=" ".join(parts[6:]) if len(parts) > 6 else "",
                )
                designer.add_widget(widget)
                print(f"✓ Added {widget.type} widget")

            elif action == "template":
                if len(parts) < 5:
                    print("Usage: template <name> <id> <x> <y>")
                    continue
                designer.add_widget_from_template(parts[1], parts[2], int(parts[3]), int(parts[4]))
                print(f"✓ Added widget '{parts[2]}' from template: {parts[1]}")

            elif action == "clone":
                if len(parts) < 2:
                    print("Usage: clone <idx> [offset_x] [offset_y]")
                    continue
                offset_x = int(parts[2]) if len(parts) > 2 else 10
                offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), offset_x, offset_y)
                print("✓ Widget cloned")

            elif action == "duplicate":
                if len(parts) < 2:
                    print("Usage: duplicate <idx> [dx] [dy]")
                    continue
                _offset_x = int(parts[2]) if len(parts) > 2 else 10
                _offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), _offset_x, _offset_y)
                print("✓ Widget duplicated")

            elif action == "move":
                if len(parts) < 4:
                    print("Usage: move <idx> <dx> <dy>")
                    continue
                designer.move_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("✓ Widget moved")

            elif action == "resize":
                if len(parts) < 4:
                    print("Usage: resize <idx> <dw> <dh>")
                    continue
                designer.resize_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("✓ Widget resized")

            elif action == "delete":
                if len(parts) < 2:
                    print("Usage: delete <idx>")
                    continue
                designer.delete_widget(int(parts[1]))
                print("✓ Widget deleted")

            elif action == "lock":
                if len(parts) < 3:
                    print("Usage: lock <idx> <on|off|toggle>")
                    continue
                _idx = int(parts[1])
                _mode = parts[2].lower()
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        if _mode == "on":
                            scene.widgets[_idx].locked = True
                        elif _mode == "off":
                            scene.widgets[_idx].locked = False
                        elif _mode == "toggle":
                            scene.widgets[_idx].locked = not scene.widgets[_idx].locked
                        else:
                            print("Usage: lock <idx> <on|off|toggle>")
                            continue
                        state = "🔒" if scene.widgets[_idx].locked else "🔓"
                        print(f"✓ Widget {_idx} {state}")

            elif action == "select":
                if len(parts) < 2:
                    print("Usage: select <idx>")
                    continue
                try:
                    _idx = int(parts[1])
                except Exception:
                    print("Usage: select <idx>")
                    continue
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        designer.selected_widget = _idx
                        print(f"✓ Selected widget [{_idx}] {scene.widgets[_idx].type}")
                    else:
                        print(MSG_INVALID_INDEX)

            elif action == "edit":
                if len(parts) < 4:
                    print("Usage: edit <idx> <property> <value>")
                    continue
                _idx = int(parts[1])
                _prop = parts[2]
                _value = " ".join(parts[3:])

                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        # Save state before edit
                        _state = json.dumps(asdict(scene))
                        designer.undo_stack.append(_state)
                        designer.redo_stack.clear()

                        widget = scene.widgets[_idx]

                        # Set property
                        if _prop in [
                            "x",
                            "y",
                            "width",
                            "height",
                            "value",
                            "min_value",
                            "max_value",
                            "z_index",
                        ]:
                            setattr(widget, _prop, int(_value))
                        elif _prop in ["checked", "enabled", "visible", "border"]:
                            setattr(widget, _prop, _value.lower() in ["true", "1", "yes"])
                        else:
                            setattr(widget, _prop, _value)

                        print(f"✓ Updated {_prop} = {_value}")

            # Advanced Features
            elif action == "undo":
                if designer.undo():
                    print("✓ Undone")
                else:
                    print("❌ Nothing to undo")

            elif action == "redo":
                if designer.redo():
                    print("✓ Redone")
                else:
                    print("❌ Nothing to redo")

            elif action == "grid":
                if len(parts) < 2:
                    print(f"Grid is {'enabled' if designer.grid_enabled else 'disabled'}")
                elif parts[1].lower() in ["on", "true", "1"]:
                    designer.grid_enabled = True
                    print("✓ Grid enabled")
                else:
                    designer.grid_enabled = False
                    print("✓ Grid disabled")

            elif action == "snap":
                if len(parts) < 2:
                    print(f"Snap to grid is {'enabled' if designer.snap_to_grid else 'disabled'}")
                elif parts[1].lower() in ["on", "true", "1"]:
                    designer.snap_to_grid = True
                    print("✓ Snap to grid enabled")
                else:
                    designer.snap_to_grid = False
                    print("✓ Snap to grid disabled")

            elif action == "guides":
                if len(parts) < 2:
                    print(f"Guides overlay is {'on' if designer.show_guides else 'off'}")
                elif parts[1].lower() in ["on", "true", "1"]:
                    designer.show_guides = True
                    print("✓ Guides enabled")
                else:
                    designer.show_guides = False
                    print("✓ Guides disabled")

            elif action == "snaptol":
                if len(parts) < 2:
                    print(f"Snap tolerance: {designer.snap_tolerance} px")
                else:
                    try:
                        designer.snap_tolerance = max(0, int(parts[1]))
                        print(f"✓ Snap tolerance set to {designer.snap_tolerance} px")
                    except Exception:
                        print("Usage: snaptol <pixels>")

            elif action == "snapmode":
                if len(parts) < 2:
                    mode = "fluid" if designer.snap_fluid else "pixel"
                    print(f"Snap mode: {mode}")
                else:
                    val = parts[1].lower()
                    if val in ["pixel", "strict"]:
                        designer.snap_fluid = False
                        print("✓ Snap mode: pixel (grid-first)")
                    elif val in ["fluid", "magnetic"]:
                        designer.snap_fluid = True
                        print("✓ Snap mode: fluid (magnetic-first)")
                    else:
                        print("Usage: snapmode <pixel|fluid>")

            elif action == "list":
                if designer.current_scene:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\n📋 Scene: {scene.name} ({scene.width}x{scene.height})")
                    print(f"Widgets: {len(scene.widgets)}\n")
                    for i, w in enumerate(scene.widgets):
                        border_info = f" border={w.border_style}" if w.border else ""
                        value_info = (
                            f" value={w.value}"
                            if w.type in ["gauge", "progressbar", "slider"]
                            else ""
                        )
                        lock_info = " 🔒" if getattr(w, "locked", False) else ""
                        print(
                            f"  [{i}] {w.type:12s} pos=({w.x:3d},{w.y:3d}) size={w.width:3d}x{w.height:3d}{border_info}{value_info}{lock_info}"
                        )
                        if w.text:
                            print(f"       text='{w.text}'")
                else:
                    print(MSG_NO_SCENE)

            elif action == "preview":
                show_grid = len(parts) > 1 and parts[1].lower() == "grid"
                print("\n" + designer.preview_ascii(show_grid=show_grid))
                print()

            elif action == "templates":
                print("\n📦 Available templates:")
                for name, template in designer.templates.items():
                    print(f"  {name:20s} - {template.type} {template.width}x{template.height}")
                print()

            elif action == "widgets":
                print("\n🎨 Available widget types:")
                for wtype in WidgetType:
                    print(f"  - {wtype.value}")
                print()

            # Theme & WCAG
            elif action == "theme":
                if len(parts) < 2:
                    print("Usage: theme <list|set|bind|apply> ...")
                    continue
                sub = parts[1].lower()
                if sub == "list":
                    print("\n🎨 Themes:")
                    for name, roles in sorted(designer.themes.items()):
                        print(
                            f"  - {name:8s} bg={roles.get('bg')} text={roles.get('text')} primary={roles.get('primary')}"
                        )
                    print()
                elif sub == "set":
                    if len(parts) < 3:
                        print("Usage: theme set <name>")
                        continue
                    name = parts[2]
                    if name not in designer.themes:
                        print("Unknown theme name")
                        continue
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        sc = designer.scenes[designer.current_scene]
                        sc.theme = name
                        sc.bg_color = designer.themes[name].get("bg", sc.bg_color)
                        print(f"✓ Theme set: {name}")
                elif sub == "bind":
                    if len(parts) < 5:
                        print("Usage: theme bind <idx> <fg|bg> <role>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _which = parts[3].lower()
                    _role = parts[4]
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        if 0 <= _idx < len(_sc.widgets):
                            if _which == "fg":
                                _sc.widgets[_idx].theme_fg_role = _role
                            elif _which == "bg":
                                _sc.widgets[_idx].theme_bg_role = _role
                            else:
                                print("Use fg or bg")
                                continue
                            print("✓ Theme role bound")
                elif sub == "apply":
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        _roles = designer.themes.get(_sc.theme, designer.themes["default"])
                        for _w in _sc.widgets:
                            if _w.theme_fg_role:
                                _w.color_fg = _roles.get(_w.theme_fg_role, _w.color_fg)
                            if _w.theme_bg_role:
                                _w.color_bg = _roles.get(_w.theme_bg_role, _w.color_bg)
                        # Apply bg to preview HTML via scene.bg_color; ASCII unaffected
                        print("✓ Theme applied to bound widgets")
                else:
                    print("Unknown theme subcommand")

            elif action == "contrast":
                if designer.current_scene and designer.current_scene in designer.scenes:
                    _sc = designer.scenes[designer.current_scene]
                    if len(parts) > 1:
                        try:
                            designer.theme_contrast_min = float(parts[1])
                        except Exception:
                            pass
                    _min_ratio = designer.theme_contrast_min
                    _issues = 0
                    for _i, _w in enumerate(_sc.widgets):
                        if getattr(_w, "visible", True) and (
                            _w.text
                            or _w.type in ["label", "button", "textbox", "checkbox", "radiobutton"]
                        ):
                            _r = _contrast_ratio(_w.color_fg, _w.color_bg)
                            if _r < _min_ratio:
                                _issues += 1
                                print(
                                    f"  [low] [{_i}] {_w.type}: contrast={_r:.2f} (fg={_w.color_fg}, bg={_w.color_bg})"
                                )
                                if _sc.contrast_lock:
                                    # Try swapping to scene theme text color for better contrast
                                    _roles = designer.themes.get(
                                        _sc.theme, designer.themes["default"]
                                    )
                                    _candidate = _roles.get("text", _w.color_fg)
                                    if _contrast_ratio(_candidate, _w.color_bg) >= _min_ratio:
                                        _w.color_fg = _candidate
                                        print(f"       -> adjusted fg to {_candidate}")
                    if _issues == 0:
                        print(f"✓ All text meets contrast >= {_min_ratio}")
                    else:
                        print(f"⚠️  {_issues} items below contrast {_min_ratio}")

            elif action == "tree":
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\n🌲 Tree for scene: {scene.name}")
                    if designer.groups:
                        print("\nGroups:")
                        for gname, members in designer.list_groups():
                            mem_str = ", ".join(str(i) for i in members)
                            print(f"  - {gname}: [{mem_str}]")
                        print()
                    else:
                        print("(no groups)")
                    print("\nWidgets:")
                    for i, w in enumerate(scene.widgets):
                        tags = []
                        for gname, mem in designer.groups.items():
                            if i in mem:
                                tags.append(gname)
                        tag_str = f" groups={','.join(tags)}" if tags else ""
                        lock_info = " 🔒" if getattr(w, "locked", False) else ""
                        vis_info = " (hidden)" if not getattr(w, "visible", True) else ""
                        print(
                            f"  [{i}] {w.type} at ({w.x},{w.y}) {w.width}x{w.height}{tag_str}{lock_info}{vis_info}"
                        )
                    print()
                else:
                    print(MSG_NO_SCENE)

            # File Operations
            elif action == "save":
                if len(parts) < 2:
                    print("Usage: save <file>")
                    continue
                designer.save_to_json(parts[1])
                # Note: save_to_json already triggers preflight/auto-export by default

            elif action == "load":
                if len(parts) < 2:
                    print("Usage: load <file>")
                    continue
                designer.load_from_json(parts[1])
            elif action == "restore":
                # Autosave restore utility
                backup_dir = Path.home() / ".esp32os" / "designer_backups"
                snaps = []
                if backup_dir.exists():
                    snaps = sorted(backup_dir.glob("*.json"))
                if not snaps:
                    print("No snapshots found")
                    continue
                if len(parts) == 1 or parts[1] == "list":
                    print("\n📦 Snapshots:")
                    for i, p in enumerate(snaps):
                        print(f"  [{i}] {p.name}")
                    print()
                    continue
                _idx = -1
                if parts[1] == "latest":
                    _idx = len(snaps) - 1
                else:
                    try:
                        _idx = int(parts[1])
                    except Exception:
                        print("Usage: restore [latest|list|<index>]")
                        continue
                if 0 <= _idx < len(snaps):
                    try:
                        # Load snapshot into current scene (create scene if needed)
                        with open(snaps[_idx], "r", encoding="utf-8") as _f:
                            _state = json.load(_f)
                        _name = _state.get("name", "restored")
                        designer.scenes[_name] = SceneConfig(
                            name=_name,
                            width=int(_state.get("width", designer.width)),
                            height=int(_state.get("height", designer.height)),
                            widgets=[WidgetConfig(**_w) for _w in _state.get("widgets", [])],
                            bg_color=_state.get("bg_color", "black"),
                        )
                        designer.current_scene = _name
                        # Show quick diff summary if previous scene exists in undo
                        if designer.undo_stack:
                            try:
                                _prev = json.loads(designer.undo_stack[-1])
                                _pw = len(_prev.get("widgets", []))
                                _cw = len(_state.get("widgets", []))
                                print(
                                    f"✓ Restored snapshot {snaps[_idx].name} (widgets: {_pw} -> {_cw})"
                                )
                            except Exception:
                                print(f"✓ Restored snapshot {snaps[_idx].name}")
                        else:
                            print(f"✓ Restored snapshot {snaps[_idx].name}")
                    except Exception as e:
                        print(f"❌ Failed to restore: {e}")
                else:
                    print("Invalid index")

            elif action == "export":
                if len(parts) < 2:
                    print("Usage: export <file> [html]")
                    continue
                if len(parts) > 2 and parts[2].lower() == "html":
                    designer.export_to_html(parts[1])
                else:
                    designer.export_code(parts[1])

            # Groups
            elif action == "group":
                if len(parts) < 2:
                    print("Usage: group <create|add|remove|delete|list|lock|visible> ...")
                    continue
                _sub = parts[1].lower()
                if _sub == "list":
                    _groups = designer.list_groups()
                    if not _groups:
                        print("No groups")
                    else:
                        print("\n👥 Groups:")
                        for _name, _members in _groups:
                            print(f"  - {_name:20s} [{', '.join(map(str, _members))}]")
                        print()
                elif _sub in ["create", "add", "remove"]:
                    if len(parts) < 4:
                        print(f"Usage: group {_sub} <name> <idx1> [idx2...]")
                        continue
                    _name = parts[2]
                    try:
                        _idxs = [int(_x) for _x in parts[3:]]
                    except Exception:
                        print("Indices must be integers")
                        continue
                    _ok = False
                    if _sub == "create":
                        _ok = designer.create_group(_name, _idxs)
                    elif _sub == "add":
                        _ok = designer.add_to_group(_name, _idxs)
                    else:
                        _ok = designer.remove_from_group(_name, _idxs)
                    print("✓ Done" if _ok else MSG_FAILED)
                elif sub == "delete":
                    if len(parts) < 3:
                        print("Usage: group delete <name>")
                        continue
                    print("✓ Deleted" if designer.delete_group(parts[2]) else MSG_FAILED)
                elif sub in ["lock", "visible"]:
                    if len(parts) < 4:
                        print(f"Usage: group {sub} <name> <on|off|toggle>")
                        continue
                    _name = parts[2]
                    _mode = parts[3].lower()
                    if sub == "lock":
                        _ok = designer.group_set_lock(_name, _mode)
                    else:
                        _ok = designer.group_set_visible(_name, _mode)
                    print("✓ Done" if _ok else MSG_FAILED)
                else:
                    print("Unknown group subcommand")

            # Symbols
            elif action == "symbol":
                if len(parts) < 2:
                    print("Usage: symbol <save|list|place> ...")
                    continue
                _sub = parts[1].lower()
                if _sub == "list":
                    if not designer.symbols:
                        print("No symbols")
                    else:
                        print("\n🔁 Symbols:")
                        for _name, _spec in sorted(designer.symbols.items()):
                            _w, _h = _spec.get("size", (0, 0))
                            print(
                                f"  - {_name:20s} size={_w}x{_h} items={len(_spec.get('items', []))}"
                            )
                        print()
                    continue
                if _sub == "save":
                    if len(parts) < 4:
                        print("Usage: symbol save <name> <idx1> [idx2...]")
                        continue
                    _name = parts[2]
                    try:
                        _idxs = [int(_x) for _x in parts[3:]]
                    except Exception:
                        print("Indices must be integers")
                        continue
                    _ok = designer.save_symbol(_name, _idxs)
                    print("✓ Saved" if _ok else "❌ Failed to save symbol")
                elif _sub == "place":
                    if len(parts) < 5:
                        print("Usage: symbol place <name> <x> <y>")
                        continue
                    _name = parts[2]
                    try:
                        _x = int(parts[3])
                        _y = int(parts[4])
                    except Exception:
                        print("x/y must be integers")
                        continue
                    _ok = designer.place_symbol(_name, _x, _y)
                    print("✓ Placed" if _ok else "❌ Failed to place symbol")
                else:
                    print("Unknown symbol subcommand")

            elif action == "checkpoint":
                if len(parts) < 2:
                    print("Usage: checkpoint <name>")
                    continue
                _ok = designer.create_checkpoint(parts[1])
                if _ok:
                    print(f"✓ Checkpoint created: {parts[1]}")
                else:
                    print("❌ Failed to create checkpoint (no scene loaded?)")

            elif action == "checkpoints":
                cps = designer.list_checkpoints()
                if not cps:
                    print("No checkpoints")
                else:
                    print("\n🗂️  Checkpoints:")
                    for name, ts in cps:
                        print(f"  - {name:20s} {ts}")
                    print()

            elif action == "rollback":
                if len(parts) < 2:
                    print("Usage: rollback <name>")
                    continue
                if designer.rollback_checkpoint(parts[1]):
                    print(f"✓ Rolled back to checkpoint: {parts[1]}")
                else:
                    print("❌ Failed to rollback (unknown checkpoint?)")

            elif action == "diff":
                if len(parts) < 2:
                    print("Usage: diff <A> [B]")
                    continue
                _name_a = parts[1]
                _name_b = parts[2] if len(parts) > 2 else None
                if _name_a not in designer.checkpoints:
                    print("Unknown checkpoint A")
                    continue
                _a = designer.checkpoints[_name_a]["scene"]
                if _name_b:
                    if _name_b not in designer.checkpoints:
                        print("Unknown checkpoint B")
                        continue
                    _b = designer.checkpoints[_name_b]["scene"]
                else:
                    _cur = designer._current_scene_state()
                    if not _cur:
                        print("No current scene to diff against")
                        continue
                    _b = _cur
                _d = designer._diff_states(_a, _b)
                _ca = _d["widgets"]["count"]["a"]
                _cb = _d["widgets"]["count"]["b"]
                print("\n🔍 Diff:")
                print(f"  Scene A: {_d['scene']['a']}  size={_d['size']['a']}  widgets={_ca}")
                print(f"  Scene B: {_d['scene']['b']}  size={_d['size']['b']}  widgets={_cb}")
                if _d["widgets"]["added"]:
                    print(f"  + Added indices in B: {_d['widgets']['added']}")
                if _d["widgets"]["removed"]:
                    print(f"  - Removed indices from A: {_d['widgets']['removed']}")
                if _d["widgets"]["changed"]:
                    print(f"  ~ Changed widgets: {len(_d['widgets']['changed'])}")
                    for _ch in _d["widgets"]["changed"][:10]:
                        _ix = _ch["index"]
                        _keys = ", ".join(list(_ch["changes"].keys())[:6])
                        print(
                            f"     [{_ix}] fields: {_keys}{' ...' if len(_ch['changes'])>6 else ''}"
                        )
                else:
                    print("  No property changes in matching indices")
                print()

            elif action == "layout":
                if len(parts) < 2:
                    print("Usage: layout <vertical|horizontal|grid> [spacing]")
                    continue
                _spacing = int(parts[2]) if len(parts) > 2 else 4
                designer.auto_layout(parts[1], _spacing)
                print(f"✓ Applied {parts[1]} layout")

            elif action == "align":
                if len(parts) < 3:
                    print("Usage: align <left|right|top|bottom|center_h|center_v> <idx1> [idx2...]")
                    continue
                _indices = [int(_x) for _x in parts[2:]]
                designer.align_widgets(parts[1], _indices)
                print(f"✓ Aligned {len(_indices)} widgets ({parts[1]})")

            elif action == "distribute":
                if len(parts) < 4:
                    print("Usage: distribute <horizontal|vertical> <idx1> <idx2> [idx3...]")
                    continue
                _indices = [int(_x) for _x in parts[2:]]
                designer.distribute_widgets(parts[1], _indices)
                print(f"✓ Distributed {len(_indices)} widgets ({parts[1]})")

            elif action == "gridcols":
                if len(parts) < 2:
                    print(f"Grid columns: {designer.grid_columns} (grid size {designer.grid_size})")
                else:
                    try:
                        _n = int(parts[1])
                        designer.set_grid_columns(_n)
                        print(
                            f"✓ Grid columns set to {designer.grid_columns} (grid size {designer.grid_size})"
                        )
                    except Exception:
                        print("Usage: gridcols <4|8|12>")

            elif action == "bp":
                if len(parts) < 2:
                    print("Usage: bp <WxH>  (e.g., 128x64, 240x135, 320x240)")
                    continue
                try:
                    _wh = parts[1].lower().split("x")
                    _w = int(_wh[0])
                    _h = int(_wh[1])
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        _sc.width = _w
                        _sc.height = _h
                        print(f"✓ Breakpoint applied: {_w}x{_h}")
                except Exception:
                    print("Usage: bp <WxH>")

            elif action == "resp":
                if len(parts) < 2:
                    print("Usage: resp <base|apply>")
                    continue
                _sub = parts[1].lower()
                if _sub == "base":
                    designer.set_responsive_base()
                    print("✓ Responsive base recorded")
                elif _sub == "apply":
                    designer.apply_responsive()
                    print("✓ Responsive constraints applied")
                else:
                    print("Usage: resp <base|apply>")

            elif action == "state":
                if len(parts) < 2:
                    print("Usage: state <define|set|list|clear> ...")
                    continue
                if not (designer.current_scene and designer.current_scene in designer.scenes):
                    print(MSG_NO_SCENE)
                    continue
                _sub = parts[1].lower()
                _scene = designer.scenes[designer.current_scene]
                if _sub == "define":
                    if len(parts) < 5:
                        print("Usage: state define <idx> <name> k=v [k=v]...")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    _w.state_overrides = _w.state_overrides or {}
                    _cur = dict(_w.state_overrides.get(_name, {}))
                    for _kv in parts[4:]:
                        if "=" in _kv:
                            _k, _v = _kv.split("=", 1)
                            _cur[_k] = _v
                    _w.state_overrides[_name] = _cur
                    print(f"✓ State '{_name}' overrides defined for widget {_idx}")
                elif _sub == "set":
                    if len(parts) < 4:
                        print("Usage: state set <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _scene.widgets[_idx].state = _name
                    print(f"✓ Widget {_idx} state set to '{_name}'")
                elif _sub == "list":
                    if len(parts) < 3:
                        print("Usage: state list <idx>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    _keys = sorted((_w.state_overrides or {}).keys())
                    _cur = _w.state or "default"
                    if not _keys:
                        print(f"(no overrides). Current state: {_cur}")
                    else:
                        print(f"States for widget {_idx} (current: {_cur}): {', '.join(_keys)}")
                elif _sub == "clear":
                    if len(parts) < 4:
                        print("Usage: state clear <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    if _name in (_w.state_overrides or {}):
                        del _w.state_overrides[_name]
                        print(f"✓ Removed state '{_name}' from widget {_idx}")
                    else:
                        print("No such state override")
                else:
                    print("Unknown state subcommand")

            elif action == "anim":
                if len(parts) < 2:
                    print("Usage: anim <list|add|clear|preview|play> ...")
                    continue
                _sub = parts[1].lower()
                _builtins = ["bounce", "slideinleft", "pulse", "fadein"]
                if _sub == "list":
                    print("\n🎞️  Animations:")
                    for _n in _builtins:
                        print(f"  - {_n}")
                    print()
                    continue
                if not (designer.current_scene and designer.current_scene in designer.scenes):
                    print(MSG_NO_SCENE)
                    continue
                _scene = designer.scenes[designer.current_scene]
                if _sub == "add":
                    if len(parts) < 4:
                        print("Usage: anim add <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print(MSG_UNKNOWN_ANIM)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    if _name not in (_w.animations or []):
                        _w.animations.append(_name)
                    print(f"✓ Animation '{_name}' tagged on widget {_idx}")
                elif _sub == "clear":
                    if len(parts) < 4:
                        print("Usage: anim clear <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3].lower()
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    if _name in (_w.animations or []):
                        _w.animations = [_a for _a in (_w.animations or []) if _a != _name]
                        print(f"✓ Animation '{_name}' removed from widget {_idx}")
                    else:
                        print("Animation not tagged on widget")
                elif _sub == "preview":
                    if len(parts) < 6:
                        print("Usage: anim preview <idx> <name> <steps> <t>")
                        continue
                    try:
                        _idx = int(parts[2])
                        _steps = int(parts[4])
                        _t = int(parts[5])
                    except Exception:
                        print("Usage: anim preview <idx> <name> <steps> <t>")
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print(MSG_UNKNOWN_ANIM)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    # Set context, render once, then clear
                    designer.anim_context = {"idx": _idx, "name": _name, "steps": _steps, "t": _t}
                    print("\n" + designer.preview_ascii())
                    print()
                    designer.anim_context = None
                elif _sub == "play":
                    if len(parts) < 5:
                        print("Usage: anim play <idx> <name> <steps> [delay_ms]")
                        continue
                    try:
                        _idx = int(parts[2])
                        _steps = int(parts[4])
                        _delay_ms = int(parts[5]) if len(parts) > 5 else 120
                    except Exception:
                        print("Usage: anim play <idx> <name> <steps> [delay_ms]")
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print(MSG_UNKNOWN_ANIM)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    import time

                    try:
                        for _t in range(max(1, _steps)):
                            designer.anim_context = {
                                "idx": _idx,
                                "name": _name,
                                "steps": _steps,
                                "t": _t,
                            }
                            print(f"\n[# {_t+1}/{_steps}] {_name}\n")
                            print(designer.preview_ascii())
                            time.sleep(max(0, _delay_ms) / 1000.0)
                    except KeyboardInterrupt:
                        print("\n⏹️  Animation stopped")
                    finally:
                        designer.anim_context = None
                else:
                    print("Unknown anim subcommand")

            elif action == "context":
                # Contextual help for a widget
                _target_idx: Optional[int] = None
                if len(parts) > 1:
                    try:
                        _target_idx = int(parts[1])
                    except Exception:
                        print("Usage: context [idx]")
                        continue
                else:
                    _target_idx = designer.selected_widget
                if designer.current_scene and designer.current_scene in designer.scenes:
                    _scene = designer.scenes[designer.current_scene]
                    if _target_idx is None:
                        print(
                            "Select a widget first with 'select <idx>' or pass an index: context <idx>"
                        )
                        continue
                    if not (0 <= _target_idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_target_idx]
                    _info = get_widget_help(_w)
                    print(f"\n🧩 Context: [{_target_idx}] {_w.type}")
                    print(
                        f"   Size: {_w.width}x{_w.height} at ({_w.x},{_w.y})  Style: {_w.style}  Align: {_w.align}"
                    )
                    if getattr(_w, "text", ""):
                        print(f"   Text: '{_w.text}'")
                    if getattr(_w, "locked", False):
                        print(f"   State: 🔒 locked (use: lock {_target_idx} off)")
                    print(f"\n📖 About: {_info.get('description','N/A')}")
                    _tips = _info.get("tips", [])
                    if _tips:
                        print("🔧 Tips:")
                        for _t in _tips:
                            print(f"   - {_t}")
                    _qa = [
                        f"duplicate {_target_idx} 8 8",
                        f"align left {_target_idx} <idx2> [idx3...]",
                        f"distribute horizontal {_target_idx} <idx2> [idx3...]",
                        f"lock {_target_idx} toggle",
                    ]
                    print("\n⚡ Quick actions:")
                    for _a in _qa:
                        print(f"   > {_a}")
                    print()
                else:
                    print(MSG_NO_SCENE)

            elif action == "help":
                if len(parts) > 1:
                    show_command_help(parts[1])
                else:
                    print(
                        "Type command name for help. Available: add, template, edit, grid, layout, etc."
                    )

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
        "add": """
Add widget: add <type> <x> <y> <w> <h> [text]
  Examples:
    add label 10 10 100 10 "Hello World"
    add button 20 30 40 12 "Click Me"
    add progressbar 10 50 100 8
    add gauge 60 20 40 30
        """,
        "template": """
Add from template: template <name> <x> <y>
  Available templates: title_label, button_primary, button_secondary,
                       info_panel, progress_bar, gauge_half
  Example: template button_primary 20 30
        """,
        "edit": """
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


def get_widget_help(widget: WidgetConfig) -> Dict[str, Any]:
    """Return contextual description and layout/style tips for a widget."""
    wtype = str(widget.type).lower()
    base = {
        "label": {
            "description": "Static text. Use for titles, captions, and inline hints.",
            "tips": [
                "Use align=center for titles; turn off border for clean headers",
                "Increase padding_x on narrow labels to avoid cramped text",
                "Keep contrast high (color_fg vs color_bg) for readability",
            ],
        },
        "button": {
            "description": "Clickable action. Prefer concise verbs (OK, Save, Back).",
            "tips": [
                "Keep height >= 10 for legibility on small screens",
                "Use rounded/double border to indicate primary/secondary",
                "Align a group with align left/right; use distribute horizontal",
            ],
        },
        "progressbar": {
            "description": "Linear progress indicator for completion percentage.",
            "tips": [
                "Use full width minus margins for dashboard layouts",
                "Set min/max bounds consistently across related bars",
            ],
        },
        "gauge": {
            "description": "Vertical bar gauge for a single numeric value.",
            "tips": [
                "Group multiple gauges and distribute horizontally",
                "Show current value elsewhere; keep gauge visuals minimal",
            ],
        },
        "checkbox": {
            "description": "Binary toggle with a label.",
            "tips": [
                "Ensure text is non-empty for accessibility",
                "Align left with other inputs for neat forms",
            ],
        },
        "radiobutton": {
            "description": "Mutually exclusive options within a group.",
            "tips": [
                "Stack vertically; use distribute vertical to space evenly",
                "Group with a surrounding panel for clarity",
            ],
        },
        "textbox": {
            "description": "Editable text input.",
            "tips": [
                "Ensure width is sufficient for expected content",
                "Use a label above with smaller padding",
            ],
        },
        "panel": {
            "description": "Container/background for grouping elements.",
            "tips": [
                "Use double/bold border for emphasis",
                "Set z_index lower than foreground widgets",
            ],
        },
        "icon": {
            "description": "Single-character icon glyph.",
            "tips": [
                "Pair with a label; align center for symmetry",
            ],
        },
        "chart": {
            "description": "Compact bar chart for small datasets.",
            "tips": [
                "Limit categories to fit inner width",
                "Consider labels elsewhere to keep chart readable",
            ],
        },
        "box": {
            "description": "Generic rectangle. Useful as spacer or divider.",
            "tips": [
                "Use dashed/bold borders to separate sections",
            ],
        },
        "slider": {
            "description": "Adjustable control for a numeric range.",
            "tips": [
                "Reserve adequate width; show current value nearby",
            ],
        },
    }
    return base.get(wtype, {"description": "Generic widget.", "tips": []})


# --- Theme & WCAG helpers ---

_NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
}


def _parse_color(c: str) -> Tuple[int, int, int]:
    c = (c or "").strip().lower()
    if c in _NAMED_COLORS:
        return _NAMED_COLORS[c]
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 6:
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except Exception:
                return (0, 0, 0)
    return (0, 0, 0)


def _rel_lum(rgb: Tuple[int, int, int]) -> float:
    def f(u: float) -> float:
        u = u / 255.0
        return (u / 12.92) if (u <= 0.03928 * 255) else pow((u + 0.055) / 1.055, 2.4)

    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast_ratio(fg: str, bg: str) -> float:
    L1 = _rel_lum(_parse_color(fg))
    L2 = _rel_lum(_parse_color(bg))
    lmax, lmin = (max(L1, L2), min(L1, L2))
    return (lmax + 0.05) / (lmin + 0.05)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UI Designer CLI")
    parser.add_argument("--web", action="store_true", help="Start web interface (not implemented)")
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
        "--live-preview", metavar="JSON", help="Start live preview server watching JSON file"
    )
    parser.add_argument(
        "--export-c-header",
        nargs=2,
        metavar=("JSON", "HEADER"),
        help="Export JSON design to C header file",
    )
    args = parser.parse_args()

    # Live preview mode
    if args.live_preview:
        import subprocess

        live_script = Path(__file__).parent / "ui_designer_live.py"
        if not live_script.exists():
            print(f"❌ Live preview script not found: {live_script}")
            sys.exit(1)
        try:
            subprocess.run(
                [sys.executable, str(live_script), "--json", args.live_preview], check=True
            )
        except KeyboardInterrupt:
            print("\n✓ Live preview stopped")
        sys.exit(0)

    # C header export mode
    if args.export_c_header:
        json_file, header_file = args.export_c_header
        import subprocess

        export_script = Path(__file__).parent / "ui_export_c_header.py"
        if not export_script.exists():
            print(f"❌ C export script not found: {export_script}")
            sys.exit(1)
        try:
            subprocess.run(
                [sys.executable, str(export_script), json_file, "-o", header_file], check=True
            )
        except Exception as e:
            print(f"❌ C export failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.web:
        print("🌐 Web interface not yet implemented")
        print("   Use CLI mode for now")
        sys.exit(0)

    if args.guided:
        # Minimal guided flow
        d = UIDesigner(128, 64)
        print("\n🧭 Guided mode: Choose a preset [dashboard/menu/dialog]")
        preset = args.preset or input("Preset (dashboard): ").strip().lower() or "dashboard"
        scene_name = input("Scene name (Home): ").strip() or "Home"
        try:
            w = int(input("Width (128): ") or "128")
            h = int(input("Height (64): ") or "64")
        except Exception:
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
        else:  # dialog
            d.add_widget(WidgetType.PANEL, x=6, y=10, width=w - 12, height=h - 20)
            d.add_widget(
                WidgetType.LABEL,
                x=10,
                y=14,
                width=w - 20,
                height=8,
                text="Confirm action?",
                align="center",
            )
            d.add_widget(WidgetType.BUTTON, x=w // 2 - 44, y=h - 18, width=40, height=12, text="OK")
            d.add_widget(
                WidgetType.BUTTON, x=w // 2 + 4, y=h - 18, width=40, height=12, text="Cancel"
            )

        # Export flow
        out_json = args.out_json
        out_html = args.out_html
        out_png = args.out_png
        Path(os.path.dirname(out_json)).mkdir(parents=True, exist_ok=True)
        # Save triggers preflight + auto-export by default
        d.save_to_json(out_json)
        # Ensure HTML/PNG at requested paths as well
        try:
            d.export_to_html(out_html)
        except Exception:
            pass
        try:
            import subprocess
            import sys as _sys

            cmd = [
                _sys.executable,
                PREVIEW_SCRIPT,
                "--headless-preview",
                "--in-json",
                out_json,
                "--out-png",
                out_png,
                "--out-html",
                out_html,
            ]
            subprocess.run(cmd, check=False)
        except Exception:
            pass
        print(
            f"\n✅ Guided scene created and exported:\n  JSON: {out_json}\n  HTML: {out_html}\n  PNG:  {out_png}"
        )
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
        sc = d.scenes[d.current_scene]
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
        # Use provided out paths or default under examples/demo_*
        out_json = (
            args.out_json
            if args.out_json != "examples/guided_scene.json"
            else "examples/demo_scene.json"
        )
        out_html = (
            args.out_html
            if args.out_html != "examples/guided_scene.html"
            else "examples/demo_scene.html"
        )
        out_png = (
            args.out_png
            if args.out_png != "examples/guided_scene.png"
            else "examples/demo_scene.png"
        )
        Path(os.path.dirname(out_json)).mkdir(parents=True, exist_ok=True)
        # Save triggers preflight + auto-export
        d.save_to_json(out_json)
        # Ensure HTML/PNG at requested paths as well
        try:
            d.export_to_html(out_html)
        except Exception:
            pass
        try:
            import subprocess
            import sys as _sys

            cmd = [
                _sys.executable,
                PREVIEW_SCRIPT,
                "--headless-preview",
                "--in-json",
                out_json,
                "--out-png",
                out_png,
                "--out-html",
                out_html,
            ]
            subprocess.run(cmd, check=False)
        except Exception:
            pass
        print(
            f"\n✅ Demo scene created and exported:\n  JSON: {out_json}\n  HTML: {out_html}\n  PNG:  {out_png}"
        )
        sys.exit(0)

    # Scripted CLI mode
    if args.script_file:
        try:
            with open(args.script_file, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines()]
            # Drop blanks and comments
            lines = [ln for ln in lines if ln and not ln.lstrip().startswith("#")]
            create_cli_interface(commands=lines)
            sys.exit(0)
        except Exception as e:
            print(f"❌ Failed to run script file: {e}")
            sys.exit(1)

    create_cli_interface()


# Re-export for backward compatibility
__all__ = ["UIDesigner", "WidgetConfig", "WidgetType", "BorderStyle", "Scene", "SceneConfig"]
