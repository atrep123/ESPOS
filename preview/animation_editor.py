"""Animation editor timeline window."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

from design_tokens import color_hex

# Check if Tkinter is available
try:
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

if TYPE_CHECKING:
    from preview.window import VisualPreviewWindow

try:
    COMBO_SELECTED = "<<ComboboxSelected>>"
except Exception:
    COMBO_SELECTED = "<ComboboxSelected>"


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

        ttk.Button(toolbar, text="➕ New", command=self._create_new_animation).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="🗑️ Delete", command=self._delete_animation).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Playback controls
        ttk.Button(toolbar, text="▶", width=3, command=self._play_preview).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⏸", width=3, command=self._pause_preview).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Button(toolbar, text="⏹", width=3, command=self._stop_preview).pack(
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
        ttk.Button(props_frame, text="📤 Export to C", command=self._export_to_c).grid(
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
        ttk.Button(timeline_ctrl, text="➕ Add", command=self._add_keyframe).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(timeline_ctrl, text="🗑️ Delete", command=self._delete_keyframe).pack(
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
                text="No keyframes yet. Click '➕ Add' to create one.",
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


