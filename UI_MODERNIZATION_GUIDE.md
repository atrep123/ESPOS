# UI Modernization Guide

ESP32OS UI Designer now features a modern, professional user interface with multiple themes, splash screen, welcome wizard, and comprehensive preferences.

## Features

### 🎨 Modern Themes

Four built-in professional themes:

- **Dark Modern** - VS Code inspired dark theme (default)
- **Light Modern** - Clean light theme  
- **Dracula** - Popular Dracula color scheme
- **Nord** - Arctic nord color palette

Each theme includes:
- Carefully chosen color palettes
- Consistent widget styling
- Canvas-specific colors (grid, guides, widgets)
- Status colors (success, warning, error, info)

### 🚀 Splash Screen

Professional startup splash screen with:
- Animated progress bar
- Version display
- Customizable loading messages
- Auto-dismiss after timeout

### 🧙 Welcome Wizard

First-run wizard guiding users through:
1. Welcome & overview
2. Theme & grid preferences  
3. Keyboard shortcuts
4. Getting started tips

### ⚙️ Preferences Dialog

Comprehensive settings organized in tabs:

#### Appearance
- Theme selection with live preview
- Visual theme demonstration

#### Canvas
- Canvas size (width/height)
- Grid settings (size, enabled/disabled)
- Snap to grid controls
- Visual aids (rulers, guides)

#### Export
- Default export format (JSON/HTML/PNG/SVG/PDF/C Code)
- Export directory
- Auto-backup settings

#### Performance
- Render caching with TTL
- Lazy loading toggle
- Render object pooling
- Performance tips

#### Editor
- Auto-save interval
- Display options (widget IDs, highlighting)

#### Advanced
- Undo/redo levels
- Performance profiler toggle
- Debug mode

## Usage

### Basic Theme Application

```python
from modern_ui import ThemeManager

root = tk.Tk()
theme_manager = ThemeManager(root)

# Switch themes
theme_manager.set_theme("Dracula")
theme_manager.set_theme("Nord")

# Get specific colors
bg_color = theme_manager.get_color("bg_primary")
accent = theme_manager.get_color("accent_primary")
```

### Splash Screen

```python
from modern_ui import SplashScreen

root = tk.Tk()
root.withdraw()

# Show splash for 3 seconds
splash = SplashScreen(root, duration=3000)

# Update loading status
splash.update_status("Loading modules...")
root.after(1000, lambda: splash.update_status("Initializing UI..."))
root.after(2000, lambda: splash.update_status("Ready!"))

# Splash auto-closes after 3000ms
root.after(3000, lambda: root.deiconify())
```

### Welcome Wizard

```python
from modern_ui import WelcomeWizard

root = tk.Tk()
wizard = WelcomeWizard(root)

# Wait for wizard to complete
root.wait_window(wizard.window)

# Get user preferences
settings = wizard.get_settings()
print(f"Selected theme: {settings['theme']}")
print(f"Grid enabled: {settings['grid_enabled']}")
```

### Preferences Dialog

```python
from preferences_dialog import PreferencesDialog, Preferences, save_preferences, load_preferences

# Load existing preferences
prefs = load_preferences("preferences.json")

def on_apply(new_prefs):
    """Called when user applies preferences"""
    save_preferences(new_prefs, "preferences.json")
    # Apply theme, update canvas, etc.
    theme_manager.set_theme(new_prefs.theme)
    canvas.config(width=new_prefs.canvas_width, height=new_prefs.canvas_height)

# Show dialog
dialog = PreferencesDialog(root, prefs, on_apply)
root.wait_window(dialog.window)
```

## Integration Example

Complete application startup flow:

```python
import tkinter as tk
from modern_ui import SplashScreen, WelcomeWizard, ThemeManager
from preferences_dialog import PreferencesDialog, load_preferences, save_preferences

def main():
    root = tk.Tk()
    root.withdraw()
    
    # 1. Show splash screen
    splash = SplashScreen(root, duration=2000)
    splash.update_status("Loading...")
    
    def after_splash():
        # 2. Check if first run
        prefs = load_preferences()
        
        if not prefs.wizard_completed:
            # Show welcome wizard
            root.deiconify()
            wizard = WelcomeWizard(root)
            root.wait_window(wizard.window)
            
            # Save wizard settings
            settings = wizard.get_settings()
            prefs.theme = settings.get("theme", "Dark Modern")
            prefs.grid_enabled = settings.get("grid_enabled", True)
            save_preferences(prefs)
        
        # 3. Apply theme
        theme = ThemeManager(root)
        theme.set_theme(prefs.theme)
        
        # 4. Show main window
        root.title("ESP32OS UI Designer")
        root.geometry("1024x768")
        root.deiconify()
        
        # Create menu with preferences
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences...", 
                            command=lambda: show_preferences(root, theme))
    
    root.after(2000, after_splash)
    root.mainloop()

def show_preferences(root, theme_manager):
    """Show preferences dialog"""
    prefs = load_preferences()
    
    def on_apply(new_prefs):
        save_preferences(new_prefs)
        theme_manager.set_theme(new_prefs.theme)
    
    dialog = PreferencesDialog(root, prefs, on_apply)

if __name__ == "__main__":
    main()
```

## Theme Customization

Create custom themes:

```python
from modern_ui import ThemeColors, ModernTheme

# Define custom theme
custom_theme = ThemeColors(
    bg_primary="#1a1b26",
    bg_secondary="#24283b",
    bg_tertiary="#414868",
    fg_primary="#c0caf5",
    fg_secondary="#9aa5ce",
    fg_disabled="#545c7e",
    accent_primary="#7aa2f7",
    accent_secondary="#2ac3de",
    success="#9ece6a",
    warning="#e0af68",
    error="#f7768e",
    info="#7dcfff",
    canvas_bg="#1a1b26",
    canvas_grid="#414868",
    canvas_guide="#7aa2f7",
    widget_bg="#24283b",
    widget_border="#414868",
    widget_selected="#7aa2f7",
    widget_hover="#343a55"
)

# Add to available themes
ModernTheme.THEMES["Tokyo Night"] = custom_theme

# Now selectable in preferences
theme_manager.set_theme("Tokyo Night")
```

## Preferences Persistence

Preferences are automatically saved to `preferences.json`:

```json
{
  "theme": "Dark Modern",
  "grid_enabled": true,
  "grid_size": 10,
  "snap_enabled": true,
  "canvas_width": 320,
  "canvas_height": 240,
  "export_format": "JSON",
  "enable_caching": true,
  "cache_ttl": 300,
  "auto_save": true,
  "max_undo_levels": 50
}
```

## Best Practices

1. **Always apply theme on startup** - Load preferences and set theme before creating widgets
2. **Use theme colors** - Access colors via `theme_manager.get_color()` instead of hardcoding
3. **Show splash on load** - Improves perceived performance during initialization
4. **Run wizard once** - Check `wizard_completed` flag to avoid showing every time
5. **Validate preferences** - Use Preferences dataclass for type safety
6. **Auto-save preferences** - Call `save_preferences()` in apply callback

## Testing

Run comprehensive tests:

```bash
# Theme system tests
pytest test_modern_ui.py -v

# Preferences dialog tests  
pytest test_preferences_dialog.py -v
```

All 34 tests passing (18 + 16).

## Demo

Run interactive demos:

```bash
# Theme system with splash & wizard
python modern_ui.py

# Preferences dialog
python preferences_dialog.py
```

## Files

- `modern_ui.py` - Theme system, splash screen, welcome wizard
- `preferences_dialog.py` - Comprehensive preferences dialog
- `test_modern_ui.py` - Theme system tests (18 tests)
- `test_preferences_dialog.py` - Preferences tests (16 tests)

## Next Steps

Consider adding:
- Icon theme packs
- Custom keyboard shortcuts editor
- Recent files list in wizard
- Export templates gallery
- Onboarding tooltips
- Context-sensitive help

The UI modernization provides a solid foundation for a professional, user-friendly application!
