#!/usr/bin/env python3
"""
Visual Preview Window for UI Designer
Real-time graphical preview with mouse interaction and export
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time

try:
    import tkinter as tk  # type: ignore
    from tkinter import colorchooser, filedialog, messagebox, ttk  # type: ignore
    from tkinter import font as tkfont
except Exception:
    tk = None  # type: ignore
    colorchooser = filedialog = messagebox = ttk = tkfont = None  # type: ignore

TK_AVAILABLE = tk is not None
from PIL import Image, ImageDraw

if TK_AVAILABLE:
    from PIL import ImageTk  # type: ignore
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from performance_profiler import PerformanceProfiler
except Exception:
    try:
        from tools.performance_profiler import PerformanceProfiler  # type: ignore
    except Exception:

        class PerformanceProfiler:  # type: ignore
            """Fallback no-op profiler when optional dependency is unavailable."""

            def __init__(self, *args, **kwargs):
                self.history_size = kwargs.get("history_size", 0)

            def calculate_stats(self):
                class Stats:  # minimal stub for UI display
                    fps_avg = fps_min = fps_max = 0.0
                    render_avg_ms = render_min_ms = render_max_ms = 0.0
                    frame_avg_ms = frame_min_ms = frame_max_ms = 0.0
                    memory_avg_mb = memory_peak_mb = 0.0
                    cpu_avg_percent = cpu_peak_percent = 0.0
                    samples = 0

                return Stats()

            def analyze_performance(self):
                return []

            def export_to_html(self, *_args, **_kwargs):
                return None

            def export_to_csv(self, *_args, **_kwargs):
                return None

            def export_to_json(self, *_args, **_kwargs):
                return None

            def record_frame(self, *_args, **_kwargs):
                return None


from svg_export_enhanced import EnhancedSVGExporter, ExportOptions, ExportPreset
from ui_animations import AnimationDesigner

try:
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
except Exception:
    try:
        from tools.ui_components_library_ascii import (  # type: ignore
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
        # Provide no-op factories to keep preview importable when optional extras are missing.
        def _empty_widgets(*_args, **_kwargs):
            return []

        create_alert_dialog_ascii = create_breadcrumb_ascii = _empty_widgets  # type: ignore
        create_button_group_ascii = create_chart_ascii = _empty_widgets  # type: ignore
        create_checkbox_ascii = create_confirm_dialog_ascii = _empty_widgets  # type: ignore
        create_grid_layout_ascii = create_header_footer_layout_ascii = _empty_widgets  # type: ignore
        create_input_dialog_ascii = create_notification_ascii = _empty_widgets  # type: ignore
        create_progress_card_ascii = create_radio_group_ascii = _empty_widgets  # type: ignore
        create_sidebar_layout_ascii = create_slider_ascii = _empty_widgets  # type: ignore
        create_stat_card_ascii = create_status_indicator_ascii = _empty_widgets  # type: ignore
        create_tab_bar_ascii = create_toggle_switch_ascii = _empty_widgets  # type: ignore
        create_vertical_menu_ascii = _empty_widgets  # type: ignore
from design_tokens import color_hex
from ui_designer import UIDesigner, WidgetConfig, WidgetType

DATA_DISPLAY = "Data Display"
COMBO_SELECTED = "<<ComboboxSelected>>"
REFRESH_LABEL = "Refresh"
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
HEADLESS: bool = (
    os.environ.get("ESP32OS_HEADLESS") == "1"
    or os.environ.get("PYTEST_CURRENT_TEST") is not None
    or not TK_AVAILABLE
)


@dataclass
class PreviewSettings:
    """Preview window settings"""

    zoom: float = 4.0  # 4x zoom by default
    grid_enabled: bool = True
    grid_size: int = 8
    snap_enabled: bool = True
    snap_size: int = 8  # align with main preview
    show_bounds: bool = True
    show_handles: bool = True
    background_color: str = color_hex("shadow")
    pixel_perfect: bool = True
    nudge_distance: int = 1  # Normal arrow nudge distance (px)
    nudge_shift_distance: int = 8  # Shift+arrow nudge distance (px)
    # Alignment guides
    snap_to_widgets: bool = True  # Snap to other widget edges
    snap_distance: int = 8  # Snap tolerance in pixels (aligned with snap_size)
    show_alignment_guides: bool = True  # Show alignment guide lines
    # Debug overlay
    show_debug_overlay: bool = False
    # Accessibility
    high_contrast_overlays: bool = False
    # Auto JSON hot-reload of last loaded design file
    auto_reload_json: bool = False
    # Performance budgeting
    performance_budget_enabled: bool = True
    performance_budget_ms: float = 16.7  # Target frame time (~60 FPS)
    performance_warn_ms: float = 25.0  # Soft warning threshold
    # Grid aesthetics
    grid_padding_pct: float = 0.0  # No inset; grid from origin
    grid_padding_min_px: int = 0  # Match main preview defaults
    grid_color_dark: Tuple[int, int, int] = (36, 36, 36)  # Slightly softer than old (40,40,40)
    grid_color_light: Tuple[int, int, int] = (50, 50, 50)  # For high contrast overlays



# Import main window class from preview package
from preview.window import VisualPreviewWindow

class AnimationEditorWindow:
    """Timeline editor for creating and editing animations"""

    def __init__(self, parent, preview_window: VisualPreviewWindow):
        self.preview = preview_window
        self.anim_designer = preview_window.anim

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Animation Timeline Editor")
        self.window.geometry("800x600")
        self.window.configure(bg=color_hex("legacy_gray4"))

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

        anim_combo = ttk.Combobox(toolbar, textvariable=self.anim_var, values=animations, width=20)
        anim_combo.pack(side=tk.LEFT, padx=5)
        anim_combo.bind(COMBO_SELECTED, self._on_anim_selected)

        ttk.Button(toolbar, text="New", command=self._create_new_animation).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="Delete", command=self._delete_animation).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Playback controls
        ttk.Button(toolbar, text="Play", width=4, command=self._play_preview).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="Pause", width=4, command=self._pause_preview).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="Stop", width=4, command=self._stop_preview).pack(
            side=tk.LEFT, padx=1
        )

        # Main content area
        content = ttk.Frame(self.window)
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Properties panel (left)
        props_frame = ttk.LabelFrame(
            content, text="Animation Properties", padding=self._scale_spacing(10, minimum=6)
        )
        props_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Type
        ttk.Label(props_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.type_var = tk.StringVar(value="fade")
        type_combo = ttk.Combobox(
            props_frame,
            textvariable=self.type_var,
            width=15,
            values=["fade", "slide_left", "slide_right", "move", "scale", "pulse", "bounce"],
        )
        type_combo.grid(row=0, column=1, pady=2)

        # Duration
        ttk.Label(props_frame, text="Duration (ms):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.duration_var = tk.IntVar(value=500)
        ttk.Spinbox(
            props_frame, from_=100, to=5000, textvariable=self.duration_var, width=13, increment=100
        ).grid(row=1, column=1, pady=2)

        # Easing
        ttk.Label(props_frame, text="Easing:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.easing_var = tk.StringVar(value="ease_in_out")
        easing_combo = ttk.Combobox(
            props_frame,
            textvariable=self.easing_var,
            width=15,
            values=[
                "linear",
                "ease_in",
                "ease_out",
                "ease_in_out",
                "ease_in_quad",
                "ease_out_quad",
            ],
        )
        easing_combo.grid(row=2, column=1, pady=2)
        easing_combo.bind(COMBO_SELECTED, self._on_easing_changed)

        # Easing curve preview
        self.easing_canvas = tk.Canvas(props_frame, width=120, height=80, bg=color_hex("surface"))
        self.easing_canvas.grid(row=3, column=0, columnspan=2, pady=5)
        self._draw_easing_curve()

        # Loop
        self.loop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(props_frame, text="Loop", variable=self.loop_var).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=5
        )

        # Apply button
        ttk.Button(props_frame, text="Apply Changes", command=self._apply_changes).grid(
            row=5, column=0, columnspan=2, pady=10
        )

        # Export button
        ttk.Button(props_frame, text="Export to C", command=self._export_to_c).grid(
            row=6, column=0, columnspan=2, pady=5
        )

        # Timeline canvas (right)
        timeline_frame = ttk.LabelFrame(
            content, text="Timeline", padding=self._scale_spacing(5, minimum=3)
        )
        timeline_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Timeline controls
        timeline_ctrl = ttk.Frame(timeline_frame)
        timeline_ctrl.pack(side=tk.TOP, fill=tk.X, pady=5)

        ttk.Label(timeline_ctrl, text="Keyframes:").pack(side=tk.LEFT, padx=5)
        ttk.Button(timeline_ctrl, text="Add", command=self._add_keyframe).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(timeline_ctrl, text="Delete", command=self._delete_keyframe).pack(
            side=tk.LEFT, padx=2
        )

        # Timeline canvas with scrollbar
        canvas_container = ttk.Frame(timeline_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)

        self.timeline_canvas = tk.Canvas(canvas_container, bg=color_hex("legacy_gray4"), height=200)
        scrollbar = ttk.Scrollbar(
            canvas_container, orient=tk.VERTICAL, command=self.timeline_canvas.yview
        )
        self.timeline_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Timeline click events
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.selected_keyframe_idx = None

        # Keyframe properties panel
        keyframe_frame = ttk.LabelFrame(
            timeline_frame, text="Keyframe Properties", padding=self._scale_spacing(5, minimum=3)
        )
        keyframe_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        ttk.Label(keyframe_frame, text="Time (0-1):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.keyframe_time_var = tk.DoubleVar(value=0.0)
        ttk.Spinbox(
            keyframe_frame,
            from_=0.0,
            to=1.0,
            textvariable=self.keyframe_time_var,
            width=10,
            increment=0.1,
            format="%.2f",
        ).grid(row=0, column=1, padx=5)

        ttk.Label(keyframe_frame, text="Property:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.keyframe_prop_var = tk.StringVar(value="opacity")
        prop_combo = ttk.Combobox(
            keyframe_frame,
            textvariable=self.keyframe_prop_var,
            width=10,
            values=["opacity", "x", "y", "width", "height", "scale", "rotation"],
        )
        prop_combo.grid(row=1, column=1, padx=5)

        ttk.Label(keyframe_frame, text="Value:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.keyframe_value_var = tk.StringVar(value="1.0")
        ttk.Entry(keyframe_frame, textvariable=self.keyframe_value_var, width=12).grid(
            row=2, column=1, padx=5
        )

        ttk.Button(keyframe_frame, text="Update Keyframe", command=self._update_keyframe).grid(
            row=3, column=0, columnspan=2, pady=5
        )

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
            50,
            timeline_y,
            canvas_width - 50,
            timeline_y + timeline_height,
            fill=color_hex("surface"),
            outline=color_hex("text_primary"),
            width=2,
            tags="timeline_bar",
        )

        # Time markers (0%, 25%, 50%, 75%, 100%)
        bar_width = canvas_width - 100
        for pct in [0, 0.25, 0.5, 0.75, 1.0]:
            x = 50 + int(bar_width * pct)
            self.timeline_canvas.create_line(
                x,
                timeline_y + timeline_height,
                x,
                timeline_y + timeline_height + 10,
                fill=color_hex("text_primary"),
                width=1,
            )
            self.timeline_canvas.create_text(
                x,
                timeline_y + timeline_height + 20,
                text=f"{int(pct*100)}%",
                fill=color_hex("text_primary"),
                font=("Arial", 8),
            )

        # Draw keyframes
        if not anim.keyframes:
            self.timeline_canvas.create_text(
                canvas_width // 2,
                timeline_y + 80,
                text="No keyframes yet. Click 'Add' to create one.",
                fill="gray",
                font=("Arial", 10),
            )
            return

        for idx, kf in enumerate(anim.keyframes):
            x = 50 + int(bar_width * kf.time)

            # Keyframe marker
            color = (
                color_hex("success")
                if idx == self.selected_keyframe_idx
                else color_hex("legacy_orange_bright")
            )
            self.timeline_canvas.create_oval(
                x - 8,
                timeline_y + 6,
                x + 8,
                timeline_y + 34,
                fill=color,
                outline="white",
                width=2,
                tags=f"keyframe_{idx}",
            )

            # Keyframe label
            props_text = ", ".join([f"{k}={v}" for k, v in list(kf.properties.items())[:2]])
            if len(kf.properties) > 2:
                props_text += "..."

            self.timeline_canvas.create_text(
                x,
                timeline_y + 50,
                text=f"KF{idx}\n{props_text}",
                fill="white",
                font=("Arial", 8),
                tags=f"keyframe_{idx}",
            )

    def _on_timeline_click(self, event):
        """Handle timeline click to select keyframe"""
        # Find clicked keyframe
        items = self.timeline_canvas.find_overlapping(
            event.x - 5, event.y - 5, event.x + 5, event.y + 5
        )

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
        kf = Keyframe(time=self.keyframe_time_var.get(), properties={prop: value}, easing="linear")

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
        self.easing_canvas.create_line(
            padding, height - padding, width - padding, height - padding, fill="gray", width=1
        )  # X axis
        self.easing_canvas.create_line(
            padding, height - padding, padding, padding, fill="gray", width=1
        )  # Y axis

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
            self.easing_canvas.create_line(points, fill=color_hex("success"), width=2, smooth=True)

        # Labels
        self.easing_canvas.create_text(
            width // 2, height - 3, text="Time", fill="gray", font=("Arial", 7)
        )
        self.easing_canvas.create_text(
            3, height // 2, text="Value", fill="gray", font=("Arial", 7), angle=90
        )

    def _on_easing_changed(self, event=None):
        """Handle easing function change"""
        self._draw_easing_curve()

    def _create_new_animation(self):
        """Create new animation"""
        from ui_animations import Animation, AnimationType, EasingFunction

        # Simple dialog
        name = tk.simpledialog.askstring("New Animation", "Animation name:", parent=self.window)
        if not name:
            return

        # Create animation
        anim = Animation(
            name=name,
            type=AnimationType.FADE.value,
            duration=500,  # milliseconds
            easing=EasingFunction.EASE_IN_OUT.value,
            iterations=1,
            keyframes=[],
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

        if messagebox.askyesno(
            "Delete Animation", f"Delete animation '{anim_name}'?", parent=self.window
        ):
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
            messagebox.showwarning(NO_ANIMATION_TITLE, NO_ANIMATION_MSG, parent=self.window)
            return

        anim = self.anim_designer.animations[anim_name]
        anim.type = self.type_var.get()
        anim.duration = self.duration_var.get()
        anim.easing = self.easing_var.get()
        anim.iterations = -1 if self.loop_var.get() else 1

        self.status.configure(text=f"Updated: {anim_name}")
        messagebox.showinfo("Applied", f"Changes applied to '{anim_name}'", parent=self.window)

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
            messagebox.showwarning(NO_ANIMATION_TITLE, NO_ANIMATION_MSG, parent=self.window)
            return

        # Ask for output directory
        output_dir = filedialog.askdirectory(title="Select Export Directory", parent=self.window)

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
            messagebox.showinfo(
                EXPORT_COMPLETE_TITLE,
                f"Animation exported to:\n{header_file}\n{impl_file}",
                parent=self.window,
            )

        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {str(e)}", parent=self.window)


if TK_AVAILABLE:
    # ---------------- Component / Template / Icon Palette Windows -----------------
    class ComponentPaletteWindow(tk.Toplevel):
        """Component library manager with search, preview, and insert."""

        def __init__(self, root, preview: "VisualPreviewWindow"):
            super().__init__(root)
            self.title("Component Library")
            self.configure(bg=color_hex("legacy_gray4"))
            self.preview = preview
            self.geometry("640x520")
            self.recent = list(getattr(preview, "_recent_components", []))
            self.favorites = list(getattr(preview, "_favorite_components", []))
            self.default_filter = getattr(preview, "_component_filter_default", "all")
            self._build_ui()

        def _build_ui(self):
            top = ttk.Frame(self)
            top.pack(fill=tk.X, padx=8, pady=6)
            ttk.Label(top, text=SEARCH_LABEL_TEXT).pack(side=tk.LEFT)
            self.search_var = tk.StringVar()
            entry = ttk.Entry(top, textvariable=self.search_var, width=32)
            entry.pack(side=tk.LEFT, padx=6)
            entry.bind(KEY_RELEASE, lambda e: self._refresh_list())
            # Filter All/Recent/Favorites
            default_filter = self.default_filter or ("favorites" if self.favorites else "all")
            self.filter_var = tk.StringVar(value=default_filter)
            ttk.Label(top, text="Filter:").pack(side=tk.LEFT, padx=(6, 2))
            for val, label in (("all", "All"), ("recent", "Recent"), ("favorites", "Favorites")):
                ttk.Radiobutton(
                    top,
                    text=label,
                    variable=self.filter_var,
                    value=val,
                    command=lambda: self._refresh_list(),
                ).pack(side=tk.LEFT, padx=2)
            # Category dropdown
            ttk.Label(top, text="Category:").pack(side=tk.LEFT)
            self.category_var = tk.StringVar(value="All")
            self.category_combo = ttk.Combobox(
                top, textvariable=self.category_var, width=14, state="readonly"
            )
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

            self.listbox = tk.Listbox(
                body,
                bg=color_hex("legacy_gray4"),
                fg=color_hex("text_primary"),
                selectbackground=color_hex("legacy_green_material"),
            )
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_preview())
            self.listbox.bind(RETURN_KEY, lambda e: self._insert_selected())

            right = ttk.Frame(body)
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
            ttk.Label(right, text="Preview:").pack(anchor=tk.W)
            self.preview_text = tk.Text(
                right,
                height=20,
                bg=color_hex("legacy_gray15"),
                fg=color_hex("text_secondary"),
                state=tk.DISABLED,
            )
            self.preview_text.pack(fill=tk.BOTH, expand=True)
            btn_row = ttk.Frame(right)
            btn_row.pack(fill=tk.X, pady=4)
            ttk.Button(btn_row, text="Insert", command=self._insert_selected).pack(side=tk.LEFT)
            ttk.Button(
                btn_row,
                text="Add ButtonGroup",
                command=lambda: self._insert_component("ButtonGroup"),
            ).pack(side=tk.LEFT, padx=4)
            ttk.Button(btn_row, text="Favorite", command=self._favorite_selected).pack(
                side=tk.LEFT, padx=4
            )
            ttk.Button(btn_row, text="Unfavorite", command=self._unfavorite_selected).pack(
                side=tk.LEFT, padx=4
            )
            ttk.Button(
                btn_row,
                text="Use Favorites for Quick Slots",
                command=self._use_favorites_for_quick_slots,
            ).pack(side=tk.LEFT, padx=4)

            self._build_library()
            self._refresh_list()

        def _build_library(self):
            self._entries = []
            seen = set()

            def make_tags(text: str):
                base = (text or "").lower().replace(",", " ").split()
                return [t for t in base if len(t) > 2][:10]

            for comp in self.preview.ascii_components:
                name = comp.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                cat = comp.get("category", "Misc")
                desc = comp.get("description", "")
                self._entries.append(
                    {
                        "name": name,
                        "category": cat,
                        "desc": desc,
                        "factory": comp.get("factory"),
                        "tags": make_tags(name + " " + desc),
                    }
                )
            for qi in self.preview.quick_insert_components:
                name = qi.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                cat = "Quick"
                desc = f"Quick insert {qi.get('type')}"
                self._entries.append(
                    {
                        "name": name,
                        "category": cat,
                        "desc": desc,
                        "defaults": qi.get("defaults"),
                        "type": qi.get("type"),
                        "tags": make_tags(name + " " + desc),
                    }
                )
            # Add recent pseudo entries
            for r in self.recent:
                if r not in seen:
                    self._entries.append(
                        {
                            "name": r,
                            "category": "Recent",
                            "desc": "Recently used component",
                            "tags": make_tags(r),
                        }
                    )
            for f in self.favorites:
                if f not in seen:
                    self._entries.append(
                        {
                            "name": f,
                            "category": "Favorites",
                            "desc": "Favorite component",
                            "tags": make_tags(f),
                        }
                    )
            self._entries.sort(key=lambda e: (e["category"], e["name"]))
            cats = sorted({e["category"] for e in self._entries})
            for special in ("Favorites", "Recent"):
                if special in cats:
                    cats.remove(special)
                    cats.insert(0, special)
            self.category_combo["values"] = ["All"] + cats

        def _refresh_list(self):
            term = self.search_var.get().lower().strip()
            cat = self.category_var.get()
            filter_mode = (
                getattr(self, "filter_var", None).get()
                if getattr(self, "filter_var", None)
                else "all"
            )
            tags_filter = [t for t in self.tags_var.get().lower().split() if t]
            self.listbox.delete(0, tk.END)
            for e in self._entries:
                if filter_mode == "recent" and e.get("category") != "Recent":
                    continue
                if filter_mode == "favorites" and e.get("category") != "Favorites":
                    continue
                if cat != "All" and e["category"] != cat:
                    continue
                if term and term not in e["name"].lower() and term not in e.get("desc", "").lower():
                    continue
                if tags_filter and not all(
                    any(tf in tag for tag in e.get("tags", [])) for tf in tags_filter
                ):
                    continue
                self.listbox.insert(tk.END, f"{e['name']}  [{e['category']}]")

        def _get_selected_entry(self):
            sel = self.listbox.curselection()
            if not sel:
                return None
            label = self.listbox.get(sel[0])
            name = label.split("  [", 1)[0]
            for e in self._entries:
                if e["name"] == name:
                    return e
            return None

        def _show_preview(self):
            e = self._get_selected_entry()
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            if not e:
                self.preview_text.insert(tk.END, "No selection")
            else:
                self.preview_text.insert(tk.END, f"{e['name']}\n{e.get('desc', '')}\n\n")
                if e.get("factory"):
                    try:
                        ascii_art = e["factory"]()
                        ascii_lines = (
                            ascii_art
                            if isinstance(ascii_art, (list, tuple))
                            else str(ascii_art).splitlines()
                        )
                        for ln in ascii_lines:
                            self.preview_text.insert(tk.END, ln + "\\n")
                    except Exception as ex:
                        self.preview_text.insert(tk.END, f"[preview error: {ex}]")
                elif e.get("defaults"):
                    self.preview_text.insert(tk.END, f"Widget defaults: {e['defaults']}")
            self.preview_text.config(state=tk.DISABLED)

        def _insert_selected(self):
            e = self._get_selected_entry()
            if e:
                self._insert_component(e["name"])

        def _favorite_selected(self):
            entry = self._get_selected_entry()
            if entry and entry["name"] not in self.favorites:
                self.favorites.insert(0, entry["name"])
                self.preview._save_favorites_from_names(self.favorites)
                self._build_library()
                self._refresh_list()
                # Remember filter preference if user is working in favorites
                if self.filter_var.get() == "favorites":
                    self.preview._settings_cache["component_filter_default"] = "favorites"
                    self.preview._save_settings()

        def _unfavorite_selected(self):
            entry = self._get_selected_entry()
            if entry and entry["name"] in self.favorites:
                self.favorites.remove(entry["name"])
                self.preview._save_favorites_from_names(self.favorites)
                self._build_library()
                self._refresh_list()
                if self.filter_var.get() == "favorites":
                    self.preview._settings_cache["component_filter_default"] = "favorites"
                    self.preview._save_settings()

        def _use_favorites_for_quick_slots(self):
            self.preview._save_favorites_from_names(self.favorites)
            self.preview._apply_favorites_to_quick_slots()

        def _insert_component(self, name: str):
            scene = (
                self.preview.designer.scenes.get(self.preview.designer.current_scene)
                if self.preview.designer.current_scene
                else None
            )
            if not scene:
                return
            cx = max(0, scene.width // 2 - 30)
            cy = max(0, scene.height // 2 - 10)
            entry = next((e for e in self._entries if e["name"] == name), None)
            if not entry:
                return
            wtype = entry.get("type") or "label"
            defaults = entry.get("defaults", {})
            if wtype == "label":
                widget_enum = WidgetType.LABEL
            elif wtype == "button":
                widget_enum = WidgetType.BUTTON
            else:
                widget_enum = WidgetType.PANEL
            self.preview.designer.add_widget(
                widget_enum,
                x=cx,
                y=cy,
                width=defaults.get("width", 40),
                height=defaults.get("height", 12),
                text=defaults.get("text", name),
                value=defaults.get("value", 0),
                checked=defaults.get("checked", False),
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
            self.preview._record_recent_component(name)
            self._build_library()
            self._refresh_list()

    class IconPaletteWindow(tk.Toplevel):
        """Icon palette with search, category filter and insertion.

        Keeps implementation lightweight: textual list + metadata preview
        (no raster glyph rendering). Designed to work within existing
        project style and without introducing new dependencies.
        """

        def __init__(self, root, preview: "VisualPreviewWindow"):
            super().__init__(root)
            from ui_icons import (  # local import to avoid startup cost headless
                filter_icons,
                get_all_categories,
            )

            self.title("Icon Palette")
            self.configure(bg=color_hex("legacy_gray4"))
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
            cat_combo = ttk.Combobox(
                top,
                textvariable=self.cat_var,
                values=self._all_categories,
                width=16,
                state="readonly",
            )
            cat_combo.pack(side=tk.LEFT, padx=6)
            cat_combo.bind(COMBO_SELECTED, lambda e: self._refresh_list())

            ttk.Button(top, text="Close", command=self.destroy).pack(side=tk.RIGHT)

            body = ttk.Frame(self)
            body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

            # Icon list
            self.listbox = tk.Listbox(
                body,
                bg=color_hex("surface"),
                fg=color_hex("legacy_gray12"),
                selectbackground=color_hex("legacy_blue_material"),
            )
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_preview())
            self.listbox.bind(RETURN_KEY, lambda e: self._insert_selected())

            # Right panel
            right = ttk.Frame(body)
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
            ttk.Label(right, text="Preview:").pack(anchor=tk.W)
            self.preview_text = tk.Text(
                right,
                height=14,
                bg=color_hex("legacy_gray13"),
                fg=color_hex("legacy_gray6"),
                state=tk.DISABLED,
                wrap=tk.WORD,
            )
            self.preview_text.pack(fill=tk.BOTH, expand=True)

            btn_row = ttk.Frame(right)
            btn_row.pack(fill=tk.X, pady=4)
            ttk.Button(btn_row, text="Insert", command=self._insert_selected).pack(side=tk.LEFT)
            ttk.Button(
                btn_row,
                text="Insert 16px",
                command=lambda: self._insert_selected(size_variant="size_16"),
            ).pack(side=tk.LEFT, padx=4)
            ttk.Button(
                btn_row,
                text="Insert 24px",
                command=lambda: self._insert_selected(size_variant="size_24"),
            ).pack(side=tk.LEFT, padx=4)
            ttk.Button(btn_row, text="Export C", command=self._export_c_header).pack(
                side=tk.LEFT, padx=4
            )
            ttk.Button(btn_row, text="Export Bitmap", command=self._export_bitmap).pack(
                side=tk.LEFT, padx=4
            )

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
            ascii_char = icon["ascii"]
            # Basic sizing based on variant
            if size_variant == "size_24":
                w = 24
            else:
                w = 16
            h = w
            x = max(0, (self.preview.designer.width - w) // 2)
            y = max(0, (self.preview.designer.height - h) // 2)
            from ui_designer import WidgetType

            self.preview.designer.add_widget(
                WidgetType.ICON, x=x, y=y, width=w, height=h, icon_char=ascii_char
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

            path = filedialog.asksaveasfilename(
                defaultextension=".h",
                filetypes=[("Header", "*.h"), ("All", "*.*")],
                initialfile=f"icon_{icon['symbol']}.h",
            )
            if not path:
                return
            guard = f"ICON_{icon['symbol'].upper()}_H".replace("-", "_")
            content = (
                f"#ifndef {guard}\n"
                f"#define {guard}\n\n"
                "/* Auto-generated single-character icon fallback */\n"
                f"#define ICON_{icon['symbol'].upper()} \"{icon['ascii']}\" "
                f"/* {icon['name']} */\n\n"
                f"#endif /* {guard} */\n"
            )
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Export", f"C header saved: {path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"{e}")
        
        def _export_bitmap(self):
            """Export selected icon as bitmap using image_tools (if PNG available)."""
            icon = self._get_selected_icon()
            if not icon:
                return
            
            from tkinter import filedialog, messagebox
            
            # Try to find PNG icon asset
            from pathlib import Path
            icon_paths = [
                Path("assets/icons") / f"{icon['symbol']}.png",
                Path("ui/icons") / f"{icon['symbol']}.png",
                Path("assets/material_icons/24px") / f"{icon['symbol']}.png",
            ]
            
            icon_file = None
            for path in icon_paths:
                if path.exists():
                    icon_file = path
                    break
            
            if not icon_file:
                messagebox.showwarning(
                    "No Bitmap Asset",
                    f"No PNG file found for '{icon['name']}'.\n\n"
                    f"Searched:\n" + "\n".join(str(p) for p in icon_paths) + "\n\n"
                    "Using ASCII fallback export instead.",
                    parent=self
                )
                self._export_c_header()
                return
            
            # Use image_tools for bitmap export
            try:
                from ui_designer_image_tools import IconBitmapExporter
                
                size_choice = messagebox.askquestion(
                    "Icon Size",
                    f"Export {icon['name']} as 16x16 or 24x24?\n\n"
                    "Yes = 16x16 (compact)\n"
                    "No = 24x24 (detailed)",
                    parent=self
                )
                size = 16 if size_choice == "yes" else 24
                
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".h",
                    filetypes=[("Header", "*.h"), ("All", "*.*")],
                    initialfile=f"icon_{icon['symbol']}_{size}x{size}.h",
                    parent=self
                )
                
                if not output_path:
                    return
                
                exporter = IconBitmapExporter()
                exporter.add_icon_from_file(str(icon_file), icon['symbol'], size)
                exporter.export_to_header(output_path)
                
                messagebox.showinfo(
                    "Bitmap Export Complete",
                    f"Icon: {icon['name']}\n"
                    f"Size: {size}x{size} px\n"
                    f"File: {Path(output_path).name}\n\n"
                    f"Dithering: Floyd-Steinberg\n"
                    f"Format: XBM (1bpp)",
                    parent=self
                )
            
            except ImportError:
                messagebox.showerror(
                    "Missing Dependency",
                    "PIL/Pillow required for bitmap export.\n\n"
                    "Install: pip install Pillow",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Export Failed", f"{e}", parent=self)

else:
    ComponentPaletteWindow = None  # type: ignore
    IconPaletteWindow = None  # type: ignore

if __name__ == "__main__":
    # Headless CLI for automated preview/export
    parser = argparse.ArgumentParser(description="UI Designer Preview (GUI/Headless)")
    parser.add_argument(
        "--headless-preview",
        action="store_true",
        help="Run a headless PNG export without Tk (JSON-driven)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run headless PNG export with a default scene if no JSON provided",
    )
    parser.add_argument("--in-json", dest="in_json", help="Path to a UI Designer JSON file")
    parser.add_argument("--out-png", dest="out_png", help="Output PNG file path")
    parser.add_argument(
        "--out-html", dest="out_html", help="Optional output HTML path (export from designer)"
    )
    parser.add_argument("--scene", dest="scene", help="Optional scene name to render")
    default_bg = color_hex("shadow")
    parser.add_argument(
        "--bg",
        dest="bg",
        default=default_bg,
        help=f"Background color for PNG (default: {default_bg})",
    )
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
                    designer.add_widget(
                        WidgetType.PANEL,
                        x=4,
                        y=4,
                        width=max(8, sc.width - 8),
                        height=max(6, sc.height - 8),
                        text="",
                        color_bg=color_hex("legacy_gray15"),
                    )
                    # Centered label
                    label_text = "ESP32OS Preview"
                    lw = max(40, len(label_text) + 12)
                    lh = 16
                    designer.add_widget(
                        WidgetType.LABEL,
                        x=(sc.width - lw) // 2,
                        y=(sc.height - lh) // 2,
                        width=lw,
                        height=lh,
                        text=label_text,
                        border=False,
                    )
                    # Progress bar and gauge to add content
                    designer.add_widget(
                        WidgetType.PROGRESSBAR,
                        x=40,
                        y=sc.height - 40,
                        width=sc.width - 80,
                        height=12,
                        value=65,
                        min_value=0,
                        max_value=100,
                    )
                    designer.add_widget(
                        WidgetType.GAUGE, x=sc.width - 60, y=20, width=40, height=40, value=75
                    )

            vp = VisualPreviewWindow(designer)
            scene = designer.scenes.get(designer.current_scene)
            if scene is None:
                raise SystemExit(1)
            img = vp._render_scene_image(
                scene,
                background_color=args.bg,
                include_grid=False,
                use_overlays=False,
                highlight_selection=False,
            )
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
