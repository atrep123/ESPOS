# Preferences Dialog for ESP32OS UI Designer
#
# Modern settings dialog with tabs for different categories

import json
import tkinter as tk
from dataclasses import asdict, dataclass
from tkinter import filedialog, ttk
from typing import Callable, Optional

from modern_ui import ModernTheme, ThemeManager


@dataclass
class Preferences:
    """Application preferences"""
    # Theme
    theme: str = "Dark Modern"
    
    # Grid & Snap
    grid_enabled: bool = True
    grid_size: int = 8
    snap_enabled: bool = True
    snap_size: int = 8
    snap_threshold: int = 8
    
    # Canvas
    canvas_width: int = 320
    canvas_height: int = 240
    show_rulers: bool = True
    show_guides: bool = True
    
    # Export
    export_format: str = "JSON"
    export_path: str = ""
    auto_backup: bool = True
    backup_interval: int = 300  # seconds
    
    # Performance
    enable_caching: bool = True
    cache_ttl: int = 300
    lazy_loading: bool = True
    render_pooling: bool = True
    
    # Editor
    auto_save: bool = True
    auto_save_interval: int = 60
    show_widget_ids: bool = False
    highlight_selected: bool = True
    
    # Advanced
    max_undo_levels: int = 50
    enable_profiler: bool = False
    debug_mode: bool = False


class PreferencesDialog:
    """Modern preferences dialog"""
    
    def __init__(self, parent: tk.Tk, initial_prefs: Optional[Preferences] = None,
                 on_apply: Optional[Callable[[Preferences], None]] = None):
        self.parent = parent
        self.prefs = initial_prefs or Preferences()
        self.on_apply = on_apply
        self.result = None
        
        # Create dialog window
        self.window = tk.Toplevel(parent)
        self.window.title("Preferences")
        self.window.geometry("700x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Apply theme
        self.theme_manager = ThemeManager(self.window)
        self.theme_manager.set_theme(self.prefs.theme)
        self.colors = self.theme_manager.colors
        
        # Create UI
        self._create_ui()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        """Create preferences UI"""
        # Main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.notebook.add(self._create_appearance_tab(), text="Appearance")
        self.notebook.add(self._create_canvas_tab(), text="Canvas")
        self.notebook.add(self._create_export_tab(), text="Export")
        self.notebook.add(self._create_performance_tab(), text="Performance")
        self.notebook.add(self._create_editor_tab(), text="Editor")
        self.notebook.add(self._create_advanced_tab(), text="Advanced")
        
        # Buttons
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Apply", command=self.apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="OK", command=self.ok,
                  style='Accent.TButton').pack(side=tk.RIGHT)
    
    def _create_appearance_tab(self):
        """Appearance preferences"""
        frame = ttk.Frame(self.notebook)
        
        # Theme selection
        theme_frame = ttk.LabelFrame(frame, text="Theme")
        theme_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.theme_var = tk.StringVar(value=self.prefs.theme)
        row = ttk.Frame(theme_frame)
        row.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(row, text="Color Scheme:").pack(side=tk.LEFT)
        theme_combo = ttk.Combobox(row, textvariable=self.theme_var,
                                   values=ModernTheme.list_themes(),
                                   state='readonly', width=20)
        theme_combo.pack(side=tk.LEFT, padx=10)
        theme_combo.bind('<<ComboboxSelected>>', self._preview_theme)
        
        # Preview
        preview_frame = ttk.LabelFrame(frame, text="Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=200,
                                       bg=self.colors.canvas_bg,
                                       highlightthickness=1,
                                       highlightbackground=self.colors.widget_border)
        self.preview_canvas.pack(padx=10, pady=10)
        self._draw_preview()
        
        return frame
    
    def _create_canvas_tab(self):
        """Canvas preferences"""
        frame = ttk.Frame(self.notebook)
        
        # Canvas size
        size_frame = ttk.LabelFrame(frame, text="Canvas Size")
        size_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row1 = ttk.Frame(size_frame)
        row1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row1, text="Width:").pack(side=tk.LEFT)
        self.canvas_width_var = tk.IntVar(value=self.prefs.canvas_width)
        ttk.Spinbox(row1, from_=160, to=1024, textvariable=self.canvas_width_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text="px").pack(side=tk.LEFT)
        
        row2 = ttk.Frame(size_frame)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Height:").pack(side=tk.LEFT)
        self.canvas_height_var = tk.IntVar(value=self.prefs.canvas_height)
        ttk.Spinbox(row2, from_=120, to=768, textvariable=self.canvas_height_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text="px").pack(side=tk.LEFT)
        
        # Grid settings
        grid_frame = ttk.LabelFrame(frame, text="Grid & Snap")
        grid_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.grid_enabled_var = tk.BooleanVar(value=self.prefs.grid_enabled)
        ttk.Checkbutton(grid_frame, text="Show grid",
                       variable=self.grid_enabled_var).pack(anchor=tk.W, padx=10, pady=5)
        
        row3 = ttk.Frame(grid_frame)
        row3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row3, text="Grid size:").pack(side=tk.LEFT)
        self.grid_size_var = tk.IntVar(value=self.prefs.grid_size)
        ttk.Spinbox(row3, from_=1, to=64, textvariable=self.grid_size_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row3, text="px").pack(side=tk.LEFT)

        self.snap_enabled_var = tk.BooleanVar(value=self.prefs.snap_enabled)
        ttk.Checkbutton(grid_frame, text="Snap to grid",
                       variable=self.snap_enabled_var).pack(anchor=tk.W, padx=10, pady=5)

        row_snap = ttk.Frame(grid_frame)
        row_snap.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row_snap, text="Snap step:").pack(side=tk.LEFT)
        self.snap_size_var = tk.IntVar(value=self.prefs.snap_size)
        ttk.Spinbox(row_snap, from_=1, to=64, textvariable=self.snap_size_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row_snap, text="px").pack(side=tk.LEFT)

        row_tol = ttk.Frame(grid_frame)
        row_tol.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row_tol, text="Snap tolerance:").pack(side=tk.LEFT)
        self.snap_threshold_var = tk.IntVar(value=self.prefs.snap_threshold)
        ttk.Spinbox(row_tol, from_=0, to=32, textvariable=self.snap_threshold_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row_tol, text="px").pack(side=tk.LEFT)
        
        # Visual aids
        aids_frame = ttk.LabelFrame(frame, text="Visual Aids")
        aids_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.show_rulers_var = tk.BooleanVar(value=self.prefs.show_rulers)
        ttk.Checkbutton(aids_frame, text="Show rulers",
                       variable=self.show_rulers_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.show_guides_var = tk.BooleanVar(value=self.prefs.show_guides)
        ttk.Checkbutton(aids_frame, text="Show alignment guides",
                       variable=self.show_guides_var).pack(anchor=tk.W, padx=10, pady=5)
        
        return frame
    
    def _create_export_tab(self):
        """Export preferences"""
        frame = ttk.Frame(self.notebook)
        
        # Export format
        format_frame = ttk.LabelFrame(frame, text="Default Export Format")
        format_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.export_format_var = tk.StringVar(value=self.prefs.export_format)
        for fmt in ["JSON", "HTML", "PNG", "SVG", "PDF", "C Code"]:
            ttk.Radiobutton(format_frame, text=fmt, variable=self.export_format_var,
                          value=fmt).pack(anchor=tk.W, padx=10, pady=2)
        
        # Export path
        path_frame = ttk.LabelFrame(frame, text="Export Location")
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row = ttk.Frame(path_frame)
        row.pack(fill=tk.X, padx=10, pady=5)
        
        self.export_path_var = tk.StringVar(value=self.prefs.export_path)
        ttk.Entry(row, textvariable=self.export_path_var).pack(side=tk.LEFT,
                                                               fill=tk.X, expand=True)
        ttk.Button(row, text="Browse...",
                  command=self._browse_export_path).pack(side=tk.LEFT, padx=5)
        
        # Backup
        backup_frame = ttk.LabelFrame(frame, text="Auto Backup")
        backup_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.auto_backup_var = tk.BooleanVar(value=self.prefs.auto_backup)
        ttk.Checkbutton(backup_frame, text="Enable auto backup",
                       variable=self.auto_backup_var).pack(anchor=tk.W, padx=10, pady=5)
        
        row2 = ttk.Frame(backup_frame)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Backup interval:").pack(side=tk.LEFT)
        self.backup_interval_var = tk.IntVar(value=self.prefs.backup_interval)
        ttk.Spinbox(row2, from_=60, to=3600, textvariable=self.backup_interval_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text="seconds").pack(side=tk.LEFT)
        
        return frame
    
    def _create_performance_tab(self):
        """Performance preferences"""
        frame = ttk.Frame(self.notebook)
        
        # Caching
        cache_frame = ttk.LabelFrame(frame, text="Caching")
        cache_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.enable_caching_var = tk.BooleanVar(value=self.prefs.enable_caching)
        ttk.Checkbutton(cache_frame, text="Enable render caching",
                       variable=self.enable_caching_var).pack(anchor=tk.W, padx=10, pady=5)
        
        row = ttk.Frame(cache_frame)
        row.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row, text="Cache TTL:").pack(side=tk.LEFT)
        self.cache_ttl_var = tk.IntVar(value=self.prefs.cache_ttl)
        ttk.Spinbox(row, from_=60, to=3600, textvariable=self.cache_ttl_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row, text="seconds").pack(side=tk.LEFT)
        
        # Optimization
        opt_frame = ttk.LabelFrame(frame, text="Optimizations")
        opt_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.lazy_loading_var = tk.BooleanVar(value=self.prefs.lazy_loading)
        ttk.Checkbutton(opt_frame, text="Enable lazy loading",
                       variable=self.lazy_loading_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.render_pooling_var = tk.BooleanVar(value=self.prefs.render_pooling)
        ttk.Checkbutton(opt_frame, text="Enable render object pooling",
                       variable=self.render_pooling_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # Info
        info_text = """Performance optimizations help reduce lag when
working with complex UI designs. Enable caching
and pooling for best performance."""
        
        ttk.Label(frame, text=info_text, foreground=self.colors.fg_secondary,
                 wraplength=400, justify=tk.LEFT).pack(padx=10, pady=20)
        
        return frame
    
    def _create_editor_tab(self):
        """Editor preferences"""
        frame = ttk.Frame(self.notebook)
        
        # Auto save
        save_frame = ttk.LabelFrame(frame, text="Auto Save")
        save_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.auto_save_var = tk.BooleanVar(value=self.prefs.auto_save)
        ttk.Checkbutton(save_frame, text="Enable auto save",
                       variable=self.auto_save_var).pack(anchor=tk.W, padx=10, pady=5)
        
        row = ttk.Frame(save_frame)
        row.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row, text="Save interval:").pack(side=tk.LEFT)
        self.auto_save_interval_var = tk.IntVar(value=self.prefs.auto_save_interval)
        ttk.Spinbox(row, from_=30, to=600, textvariable=self.auto_save_interval_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row, text="seconds").pack(side=tk.LEFT)
        
        # Display options
        display_frame = ttk.LabelFrame(frame, text="Display Options")
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.show_widget_ids_var = tk.BooleanVar(value=self.prefs.show_widget_ids)
        ttk.Checkbutton(display_frame, text="Show widget IDs",
                       variable=self.show_widget_ids_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.highlight_selected_var = tk.BooleanVar(value=self.prefs.highlight_selected)
        ttk.Checkbutton(display_frame, text="Highlight selected widgets",
                       variable=self.highlight_selected_var).pack(anchor=tk.W, padx=10, pady=5)
        
        return frame
    
    def _create_advanced_tab(self):
        """Advanced preferences"""
        frame = ttk.Frame(self.notebook)
        
        # Undo/Redo
        undo_frame = ttk.LabelFrame(frame, text="Undo/Redo")
        undo_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row = ttk.Frame(undo_frame)
        row.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row, text="Max undo levels:").pack(side=tk.LEFT)
        self.max_undo_levels_var = tk.IntVar(value=self.prefs.max_undo_levels)
        ttk.Spinbox(row, from_=10, to=200, textvariable=self.max_undo_levels_var,
                   width=10).pack(side=tk.LEFT, padx=10)
        
        # Developer options
        dev_frame = ttk.LabelFrame(frame, text="Developer Options")
        dev_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.enable_profiler_var = tk.BooleanVar(value=self.prefs.enable_profiler)
        ttk.Checkbutton(dev_frame, text="Enable performance profiler",
                       variable=self.enable_profiler_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.debug_mode_var = tk.BooleanVar(value=self.prefs.debug_mode)
        ttk.Checkbutton(dev_frame, text="Enable debug mode",
                       variable=self.debug_mode_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # Warning
        warning_text = """WARNING: Debug mode may impact performance.
Only enable for troubleshooting."""
        
        ttk.Label(frame, text=warning_text, foreground=self.colors.warning,
                 wraplength=400, justify=tk.LEFT).pack(padx=10, pady=20)
        
        return frame
    
    def _preview_theme(self, event=None):
        """Preview selected theme"""
        theme_name = self.theme_var.get()
        self.theme_manager.set_theme(theme_name)
        self.colors = self.theme_manager.colors
        
        # Update preview
        self.preview_canvas.config(bg=self.colors.canvas_bg)
        self._draw_preview()
    
    def _draw_preview(self):
        """Draw theme preview"""
        canvas = self.preview_canvas
        canvas.delete("all")
        
        # Background with grid
        for x in range(0, 400, 20):
            canvas.create_line(x, 0, x, 200, fill=self.colors.canvas_grid)
        for y in range(0, 200, 20):
            canvas.create_line(0, y, 400, y, fill=self.colors.canvas_grid)
        
        # Sample widgets
        # Button
        canvas.create_rectangle(50, 30, 150, 60,
                              fill=self.colors.widget_bg,
                              outline=self.colors.widget_border, width=2)
        canvas.create_text(100, 45, text="Button",
                         fill=self.colors.fg_primary, font=("Arial", 10))
        
        # Selected widget
        canvas.create_rectangle(170, 30, 270, 60,
                              fill=self.colors.widget_bg,
                              outline=self.colors.widget_selected, width=3)
        canvas.create_text(220, 45, text="Selected",
                         fill=self.colors.accent_primary, font=("Arial", 10, "bold"))
        
        # Label
        canvas.create_text(100, 90, text="Text Label",
                         fill=self.colors.fg_primary, font=("Arial", 12))
        
        # Accent elements
        canvas.create_rectangle(50, 110, 200, 115,
                              fill=self.colors.accent_primary, outline="")
        
        canvas.create_text(100, 140, text="Accent Color",
                         fill=self.colors.accent_primary, font=("Arial", 11, "bold"))
        
        # Status indicators
        status_y = 170
        canvas.create_oval(50, status_y, 65, status_y+15,
                         fill=self.colors.success, outline="")
        canvas.create_oval(80, status_y, 95, status_y+15,
                         fill=self.colors.warning, outline="")
        canvas.create_oval(110, status_y, 125, status_y+15,
                         fill=self.colors.error, outline="")
        canvas.create_oval(140, status_y, 155, status_y+15,
                         fill=self.colors.info, outline="")
    
    def _browse_export_path(self):
        """Browse for export directory"""
        path = filedialog.askdirectory(parent=self.window,
                                      title="Select Export Directory")
        if path:
            self.export_path_var.set(path)
    
    def _collect_preferences(self) -> Preferences:
        """Collect preferences from UI"""
        return Preferences(
            theme=self.theme_var.get(),
            grid_enabled=self.grid_enabled_var.get(),
            grid_size=self.grid_size_var.get(),
            snap_enabled=self.snap_enabled_var.get(),
            snap_size=self.snap_size_var.get(),
            snap_threshold=self.snap_threshold_var.get(),
            canvas_width=self.canvas_width_var.get(),
            canvas_height=self.canvas_height_var.get(),
            show_rulers=self.show_rulers_var.get(),
            show_guides=self.show_guides_var.get(),
            export_format=self.export_format_var.get(),
            export_path=self.export_path_var.get(),
            auto_backup=self.auto_backup_var.get(),
            backup_interval=self.backup_interval_var.get(),
            enable_caching=self.enable_caching_var.get(),
            cache_ttl=self.cache_ttl_var.get(),
            lazy_loading=self.lazy_loading_var.get(),
            render_pooling=self.render_pooling_var.get(),
            auto_save=self.auto_save_var.get(),
            auto_save_interval=self.auto_save_interval_var.get(),
            show_widget_ids=self.show_widget_ids_var.get(),
            highlight_selected=self.highlight_selected_var.get(),
            max_undo_levels=self.max_undo_levels_var.get(),
            enable_profiler=self.enable_profiler_var.get(),
            debug_mode=self.debug_mode_var.get()
        )
    
    def apply(self):
        """Apply preferences"""
        self.result = self._collect_preferences()
        if self.on_apply:
            self.on_apply(self.result)
    
    def ok(self):
        """Apply and close"""
        self.apply()
        self.window.destroy()
    
    def cancel(self):
        """Cancel without saving"""
        self.result = None
        self.window.destroy()
    
    def get_result(self) -> Optional[Preferences]:
        """Get dialog result"""
        return self.result


def save_preferences(prefs: Preferences, path: str = "preferences.json"):
    """Save preferences to JSON file"""
    with open(path, 'w') as f:
        json.dump(asdict(prefs), f, indent=2)


def load_preferences(path: str = "preferences.json") -> Preferences:
    """Load preferences from JSON file"""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            return Preferences(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        return Preferences()


def demo():
    """Demo preferences dialog"""
    root = tk.Tk()
    root.title("Preferences Demo")
    root.geometry("400x300")
    
    # Apply initial theme
    theme = ThemeManager(root)
    
    result_label = ttk.Label(root, text="No preferences set",
                            style='Header.TLabel')
    result_label.pack(pady=50)
    
    def show_prefs():
        """Show preferences dialog"""
        # Load existing preferences
        prefs = load_preferences()
        
        def on_apply(new_prefs: Preferences):
            """Handle preferences apply"""
            save_preferences(new_prefs)
            theme.set_theme(new_prefs.theme)
            result_label.config(text=f"Theme: {new_prefs.theme}\n"
                                    f"Canvas: {new_prefs.canvas_width}x{new_prefs.canvas_height}\n"
                                    f"Grid: {new_prefs.grid_size}px")
        
        dialog = PreferencesDialog(root, prefs, on_apply)
        root.wait_window(dialog.window)
    
    ttk.Button(root, text="Open Preferences",
              command=show_prefs,
              style='Accent.TButton').pack()
    
    root.mainloop()


if __name__ == "__main__":
    demo()
