# Modern UI Theme System for ESP32OS UI Designer
#
# Features:
# - Multiple dark/light themes
# - Customizable color schemes
# - Icon packs
# - Splash screen
# - Welcome wizard

import tkinter as tk
from tkinter import ttk
from typing import Dict, Tuple, Optional
import json
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class ThemeColors:
    """Color scheme for a theme"""
    # Background colors
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    
    # Foreground colors
    fg_primary: str
    fg_secondary: str
    fg_disabled: str
    
    # Accent colors
    accent_primary: str
    accent_secondary: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str
    
    # Canvas colors
    canvas_bg: str
    canvas_grid: str
    canvas_guide: str
    
    # Widget colors
    widget_bg: str
    widget_border: str
    widget_selected: str
    widget_hover: str


class ModernTheme:
    """Modern theme definitions"""
    
    THEMES = {
        "Dark Modern": ThemeColors(
            bg_primary="#1e1e1e",
            bg_secondary="#252526",
            bg_tertiary="#2d2d30",
            fg_primary="#cccccc",
            fg_secondary="#969696",
            fg_disabled="#6e6e6e",
            accent_primary="#007acc",
            accent_secondary="#005a9e",
            success="#4ec9b0",
            warning="#ce9178",
            error="#f48771",
            info="#569cd6",
            canvas_bg="#0d1117",
            canvas_grid="#30363d",
            canvas_guide="#007acc",
            widget_bg="#21262d",
            widget_border="#444d56",
            widget_selected="#58a6ff",
            widget_hover="#30363d"
        ),
        "Light Modern": ThemeColors(
            bg_primary="#ffffff",
            bg_secondary="#f3f3f3",
            bg_tertiary="#e8e8e8",
            fg_primary="#333333",
            fg_secondary="#666666",
            fg_disabled="#999999",
            accent_primary="#0078d4",
            accent_secondary="#106ebe",
            success="#10b981",
            warning="#f59e0b",
            error="#ef4444",
            info="#3b82f6",
            canvas_bg="#fafafa",
            canvas_grid="#e5e5e5",
            canvas_guide="#0078d4",
            widget_bg="#ffffff",
            widget_border="#d1d1d1",
            widget_selected="#0078d4",
            widget_hover="#f3f3f3"
        ),
        "Dracula": ThemeColors(
            bg_primary="#282a36",
            bg_secondary="#343746",
            bg_tertiary="#44475a",
            fg_primary="#f8f8f2",
            fg_secondary="#6272a4",
            fg_disabled="#44475a",
            accent_primary="#bd93f9",
            accent_secondary="#ff79c6",
            success="#50fa7b",
            warning="#f1fa8c",
            error="#ff5555",
            info="#8be9fd",
            canvas_bg="#21222c",
            canvas_grid="#44475a",
            canvas_guide="#bd93f9",
            widget_bg="#282a36",
            widget_border="#6272a4",
            widget_selected="#ff79c6",
            widget_hover="#44475a"
        ),
        "Nord": ThemeColors(
            bg_primary="#2e3440",
            bg_secondary="#3b4252",
            bg_tertiary="#434c5e",
            fg_primary="#eceff4",
            fg_secondary="#d8dee9",
            fg_disabled="#4c566a",
            accent_primary="#88c0d0",
            accent_secondary="#81a1c1",
            success="#a3be8c",
            warning="#ebcb8b",
            error="#bf616a",
            info="#5e81ac",
            canvas_bg="#2e3440",
            canvas_grid="#4c566a",
            canvas_guide="#88c0d0",
            widget_bg="#3b4252",
            widget_border="#4c566a",
            widget_selected="#88c0d0",
            widget_hover="#434c5e"
        )
    }
    
    @classmethod
    def get_theme(cls, name: str) -> ThemeColors:
        """Get theme colors by name"""
        return cls.THEMES.get(name, cls.THEMES["Dark Modern"])
    
    @classmethod
    def list_themes(cls) -> list:
        """List available theme names"""
        return list(cls.THEMES.keys())


class ThemeManager:
    """Manage application theming"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.current_theme = "Dark Modern"
        self.colors = ModernTheme.get_theme(self.current_theme)
        
        # Create ttk style
        self.style = ttk.Style()
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply current theme to all widgets"""
        colors = self.colors
        
        # Configure root window
        self.root.configure(bg=colors.bg_primary)
        
        # Configure ttk style
        self.style.theme_use('clam')  # Base theme
        
        # Frame styles
        self.style.configure('TFrame', background=colors.bg_primary)
        self.style.configure('TLabelframe', background=colors.bg_primary,
                           foreground=colors.fg_primary, bordercolor=colors.widget_border)
        
        # Label styles
        self.style.configure('TLabel', background=colors.bg_primary,
                           foreground=colors.fg_primary)
        self.style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        
        # Button styles
        self.style.configure('TButton', background=colors.bg_secondary,
                           foreground=colors.fg_primary, bordercolor=colors.widget_border)
        self.style.map('TButton',
                      background=[('active', colors.widget_hover),
                                ('pressed', colors.accent_secondary)])
        
        # Accent button
        self.style.configure('Accent.TButton', background=colors.accent_primary,
                           foreground='white')
        self.style.map('Accent.TButton',
                      background=[('active', colors.accent_secondary)])
        
        # Entry styles
        self.style.configure('TEntry', fieldbackground=colors.widget_bg,
                           foreground=colors.fg_primary, bordercolor=colors.widget_border)
        
        # Combobox styles
        self.style.configure('TCombobox', fieldbackground=colors.widget_bg,
                           foreground=colors.fg_primary, bordercolor=colors.widget_border)
        
        # Notebook (tabs)
        self.style.configure('TNotebook', background=colors.bg_primary,
                           bordercolor=colors.widget_border)
        self.style.configure('TNotebook.Tab', background=colors.bg_secondary,
                           foreground=colors.fg_primary, padding=[10, 5])
        self.style.map('TNotebook.Tab',
                      background=[('selected', colors.bg_tertiary)])
        
        # Separator
        self.style.configure('TSeparator', background=colors.widget_border)
        
        # Progressbar
        self.style.configure('TProgressbar', background=colors.accent_primary,
                           troughcolor=colors.bg_tertiary)
        
        # Checkbutton
        self.style.configure('TCheckbutton', background=colors.bg_primary,
                           foreground=colors.fg_primary)
        
        # Scrollbar
        self.style.configure('TScrollbar', background=colors.bg_secondary,
                           troughcolor=colors.bg_tertiary, bordercolor=colors.widget_border)
    
    def set_theme(self, theme_name: str):
        """Switch to a different theme"""
        if theme_name in ModernTheme.THEMES:
            self.current_theme = theme_name
            self.colors = ModernTheme.get_theme(theme_name)
            self._apply_theme()
            return True
        return False
    
    def get_color(self, color_key: str) -> str:
        """Get specific color from current theme"""
        return getattr(self.colors, color_key, "#000000")


class SplashScreen:
    """Modern splash screen"""
    
    def __init__(self, parent: Optional[tk.Tk] = None, duration: int = 2000):
        self.parent = parent
        self.duration = duration
        
        # Create splash window
        self.splash = tk.Toplevel(parent) if parent else tk.Tk()
        self.splash.title("")
        self.splash.overrideredirect(True)
        
        # Size and position
        width, height = 400, 300
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.splash.geometry(f"{width}x{height}+{x}+{y}")
        
        # Dark background
        self.splash.configure(bg="#1e1e1e")
        
        # Create content
        self._create_content()
        
        # Auto-close after duration
        if duration > 0:
            self.splash.after(duration, self.close)
    
    def _create_content(self):
        """Create splash screen content"""
        # Main frame
        main_frame = tk.Frame(self.splash, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo area
        logo_frame = tk.Frame(main_frame, bg="#1e1e1e")
        logo_frame.pack(pady=40)
        
        # App name
        tk.Label(logo_frame, text="ESP32OS", font=("Arial", 32, "bold"),
                fg="#007acc", bg="#1e1e1e").pack()
        tk.Label(logo_frame, text="UI Designer", font=("Arial", 18),
                fg="#cccccc", bg="#1e1e1e").pack()
        
        # Version
        tk.Label(main_frame, text="Version 1.0.0", font=("Arial", 10),
                fg="#969696", bg="#1e1e1e").pack(pady=10)
        
        # Progress bar
        progress_frame = tk.Frame(main_frame, bg="#1e1e1e")
        progress_frame.pack(pady=20, fill=tk.X, padx=50)
        
        canvas = tk.Canvas(progress_frame, width=300, height=4,
                          bg="#2d2d30", highlightthickness=0)
        canvas.pack()
        
        # Animate progress bar
        self._animate_progress(canvas, 0)
        
        # Loading text
        self.loading_label = tk.Label(main_frame, text="Loading...",
                                     font=("Arial", 9), fg="#969696", bg="#1e1e1e")
        self.loading_label.pack()
    
    def _animate_progress(self, canvas, progress):
        """Animate loading progress bar"""
        if progress <= 300:
            canvas.delete("all")
            canvas.create_rectangle(0, 0, progress, 4, fill="#007acc", outline="")
            self.splash.after(10, lambda: self._animate_progress(canvas, progress + 6))
    
    def update_status(self, text: str):
        """Update loading status text"""
        if hasattr(self, 'loading_label'):
            self.loading_label.config(text=text)
            self.splash.update()
    
    def close(self):
        """Close splash screen"""
        self.splash.destroy()
    
    def show(self):
        """Show splash screen"""
        self.splash.mainloop()


class WelcomeWizard:
    """Welcome wizard for first-time users"""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.current_page = 0
        self.settings = {}
        
        # Create wizard window
        self.window = tk.Toplevel(parent)
        self.window.title("Welcome to ESP32OS UI Designer")
        self.window.geometry("600x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Apply theme
        theme = ThemeManager(self.window)
        self.colors = theme.colors
        
        # Create wizard pages
        self.pages = [
            self._create_welcome_page,
            self._create_preferences_page,
            self._create_shortcuts_page,
            self._create_finish_page
        ]
        
        # Container for pages
        self.page_container = tk.Frame(self.window, bg=self.colors.bg_primary)
        self.page_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Navigation buttons
        nav_frame = tk.Frame(self.window, bg=self.colors.bg_secondary)
        nav_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.back_btn = ttk.Button(nav_frame, text="← Back", command=self.prev_page)
        self.back_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self.next_page,
                                   style='Accent.TButton')
        self.next_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Show first page
        self.show_page(0)
    
    def _create_welcome_page(self):
        """Welcome page"""
        frame = tk.Frame(self.page_container, bg=self.colors.bg_primary)
        
        # Header
        tk.Label(frame, text="Welcome to ESP32OS UI Designer! 🎨",
                font=("Arial", 18, "bold"), fg=self.colors.accent_primary,
                bg=self.colors.bg_primary).pack(pady=30)
        
        # Description
        text = """Create stunning user interfaces for ESP32 displays.

This wizard will help you get started with:
• Setting up your preferences
• Learning keyboard shortcuts
• Exploring key features

Click Next to continue."""
        
        tk.Label(frame, text=text, font=("Arial", 11), fg=self.colors.fg_primary,
                bg=self.colors.bg_primary, justify=tk.LEFT).pack(pady=20)
        
        return frame
    
    def _create_preferences_page(self):
        """Preferences page"""
        frame = tk.Frame(self.page_container, bg=self.colors.bg_primary)
        
        tk.Label(frame, text="Preferences", font=("Arial", 16, "bold"),
                fg=self.colors.fg_primary, bg=self.colors.bg_primary).pack(pady=20)
        
        # Theme selection
        theme_frame = tk.LabelFrame(frame, text="Theme", bg=self.colors.bg_primary,
                                   fg=self.colors.fg_primary)
        theme_frame.pack(fill=tk.X, pady=10)
        
        self.theme_var = tk.StringVar(value="Dark Modern")
        for theme in ModernTheme.list_themes():
            ttk.Radiobutton(theme_frame, text=theme, variable=self.theme_var,
                           value=theme).pack(anchor=tk.W, padx=20, pady=5)
        
        # Grid settings
        grid_frame = tk.LabelFrame(frame, text="Grid Settings", bg=self.colors.bg_primary,
                                  fg=self.colors.fg_primary)
        grid_frame.pack(fill=tk.X, pady=10)
        
        self.grid_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(grid_frame, text="Show grid by default",
                       variable=self.grid_enabled).pack(anchor=tk.W, padx=20, pady=5)
        
        self.snap_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(grid_frame, text="Enable snap to grid",
                       variable=self.snap_enabled).pack(anchor=tk.W, padx=20, pady=5)
        
        return frame
    
    def _create_shortcuts_page(self):
        """Keyboard shortcuts page"""
        frame = tk.Frame(self.page_container, bg=self.colors.bg_primary)
        
        tk.Label(frame, text="Keyboard Shortcuts", font=("Arial", 16, "bold"),
                fg=self.colors.fg_primary, bg=self.colors.bg_primary).pack(pady=20)
        
        shortcuts = [
            ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
            ("Ctrl+C / Ctrl+V", "Copy / Paste"),
            ("Delete", "Delete widget"),
            ("Arrow keys", "Nudge widget"),
            ("Ctrl+1-9", "Quick add widgets"),
            ("Space+Drag", "Pan canvas"),
            ("Ctrl+Wheel", "Zoom in/out"),
        ]
        
        for key, desc in shortcuts:
            row = tk.Frame(frame, bg=self.colors.bg_primary)
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=key, font=("Consolas", 10, "bold"),
                    fg=self.colors.accent_primary, bg=self.colors.bg_primary,
                    width=20, anchor=tk.W).pack(side=tk.LEFT, padx=10)
            
            tk.Label(row, text=desc, font=("Arial", 10),
                    fg=self.colors.fg_primary, bg=self.colors.bg_primary,
                    anchor=tk.W).pack(side=tk.LEFT)
        
        return frame
    
    def _create_finish_page(self):
        """Finish page"""
        frame = tk.Frame(self.page_container, bg=self.colors.bg_primary)
        
        tk.Label(frame, text="You're All Set! ✓", font=("Arial", 18, "bold"),
                fg=self.colors.success, bg=self.colors.bg_primary).pack(pady=30)
        
        text = """You're ready to start creating amazing UIs!

Quick tips:
• Add widgets from the left palette
• Export to PNG, SVG, PDF, or C code
• Use templates for common layouts
• Enable profiler to monitor performance

Happy designing!"""
        
        tk.Label(frame, text=text, font=("Arial", 11), fg=self.colors.fg_primary,
                bg=self.colors.bg_primary, justify=tk.LEFT).pack(pady=20)
        
        return frame
    
    def show_page(self, page_index):
        """Show specific wizard page"""
        # Clear container
        for widget in self.page_container.winfo_children():
            widget.destroy()
        
        # Create and show page
        page_frame = self.pages[page_index]()
        page_frame.pack(fill=tk.BOTH, expand=True)
        
        # Update buttons
        self.back_btn.config(state=tk.NORMAL if page_index > 0 else tk.DISABLED)
        if page_index == len(self.pages) - 1:
            self.next_btn.config(text="Finish", command=self.finish)
        else:
            self.next_btn.config(text="Next →", command=self.next_page)
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.show_page(self.current_page)
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page(self.current_page)
    
    def finish(self):
        """Finish wizard"""
        # Save settings
        self.settings = {
            "theme": self.theme_var.get() if hasattr(self, 'theme_var') else "Dark Modern",
            "grid_enabled": self.grid_enabled.get() if hasattr(self, 'grid_enabled') else True,
            "snap_enabled": self.snap_enabled.get() if hasattr(self, 'snap_enabled') else True,
            "wizard_completed": True
        }
        
        self.window.destroy()
    
    def get_settings(self) -> Dict:
        """Get wizard settings"""
        return self.settings


def demo():
    """Demo of modern UI components"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Show splash screen
    splash = SplashScreen(root, duration=3000)
    splash.update_status("Loading modules...")
    root.after(1000, lambda: splash.update_status("Initializing UI..."))
    root.after(2000, lambda: splash.update_status("Ready!"))
    root.after(3000, lambda: show_wizard())
    
    def show_wizard():
        root.deiconify()  # Show main window
        wizard = WelcomeWizard(root)
        root.wait_window(wizard.window)
        
        # Apply theme from wizard
        theme = ThemeManager(root)
        settings = wizard.get_settings()
        if settings.get("theme"):
            theme.set_theme(settings["theme"])
        
        # Show main window
        root.title("ESP32OS UI Designer - Modern Theme Demo")
        root.geometry("800x600")
        
        ttk.Label(root, text="Modern UI Applied!", style='Header.TLabel').pack(pady=50)
        ttk.Button(root, text="Accent Button", style='Accent.TButton').pack()
    
    root.mainloop()


if __name__ == "__main__":
    demo()
