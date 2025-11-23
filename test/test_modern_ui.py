"""Tests for modern_ui.py - modern theme system, splash screen, welcome wizard"""

import pytest

try:
    import tkinter as tk  # type: ignore
except Exception:  # pragma: no cover - skip in headless environments
    pytest.skip("tkinter not available", allow_module_level=True)

from modern_ui import ModernTheme, SplashScreen, ThemeColors, ThemeManager, WelcomeWizard


class TestThemeColors:
    """Test ThemeColors dataclass"""
    
    def test_theme_colors_creation(self):
        """Test creating theme colors"""
        colors = ThemeColors(
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
        )
        
        assert colors.bg_primary == "#1e1e1e"
        assert colors.accent_primary == "#007acc"
        assert colors.success == "#4ec9b0"


class TestModernTheme:
    """Test ModernTheme definitions"""
    
    def test_list_themes(self):
        """Test listing available themes"""
        themes = ModernTheme.list_themes()
        assert "Dark Modern" in themes
        assert "Light Modern" in themes
        assert "Dracula" in themes
        assert "Nord" in themes
        assert len(themes) >= 4
    
    def test_get_dark_theme(self):
        """Test getting dark theme"""
        colors = ModernTheme.get_theme("Dark Modern")
        assert colors.bg_primary == "#1e1e1e"
        assert colors.fg_primary == "#cccccc"
        assert colors.accent_primary == "#007acc"
    
    def test_get_light_theme(self):
        """Test getting light theme"""
        colors = ModernTheme.get_theme("Light Modern")
        assert colors.bg_primary == "#ffffff"
        assert colors.fg_primary == "#333333"
        assert colors.accent_primary == "#0078d4"
    
    def test_get_dracula_theme(self):
        """Test getting Dracula theme"""
        colors = ModernTheme.get_theme("Dracula")
        assert colors.bg_primary == "#282a36"
        assert colors.accent_primary == "#bd93f9"
        assert colors.success == "#50fa7b"
    
    def test_get_nord_theme(self):
        """Test getting Nord theme"""
        colors = ModernTheme.get_theme("Nord")
        assert colors.bg_primary == "#2e3440"
        assert colors.accent_primary == "#88c0d0"
    
    def test_get_invalid_theme(self):
        """Test getting invalid theme returns default"""
        colors = ModernTheme.get_theme("NonExistent")
        assert colors == ModernTheme.get_theme("Dark Modern")


class TestThemeManager:
    """Test ThemeManager"""
    
    def test_theme_manager_init(self):
        """Test theme manager initialization"""
        root = tk.Tk()
        try:
            manager = ThemeManager(root)
            assert manager.current_theme == "Dark Modern"
            assert manager.colors is not None
            assert manager.style is not None
        finally:
            root.destroy()
    
    def test_set_theme(self):
        """Test setting different theme"""
        root = tk.Tk()
        try:
            manager = ThemeManager(root)
            
            # Set to light theme
            result = manager.set_theme("Light Modern")
            assert result is True
            assert manager.current_theme == "Light Modern"
            assert manager.colors.bg_primary == "#ffffff"
            
            # Set to Dracula
            result = manager.set_theme("Dracula")
            assert result is True
            assert manager.current_theme == "Dracula"
            
            # Set invalid theme
            result = manager.set_theme("Invalid")
            assert result is False
            assert manager.current_theme == "Dracula"  # Should not change
        finally:
            root.destroy()
    
    def test_get_color(self):
        """Test getting specific colors"""
        root = tk.Tk()
        try:
            manager = ThemeManager(root)
            
            bg = manager.get_color("bg_primary")
            assert bg == "#1e1e1e"
            
            accent = manager.get_color("accent_primary")
            assert accent == "#007acc"
            
            # Invalid color should return black
            invalid = manager.get_color("nonexistent")
            assert invalid == "#000000"
        finally:
            root.destroy()


class TestSplashScreen:
    """Test SplashScreen"""
    
    def test_splash_screen_creation(self):
        """Test creating splash screen"""
        root = tk.Tk()
        try:
            splash = SplashScreen(root, duration=0)  # No auto-close
            assert splash.splash is not None
            assert splash.duration == 0
            splash.close()
        finally:
            root.destroy()
    
    def test_splash_screen_update_status(self):
        """Test updating splash screen status"""
        root = tk.Tk()
        try:
            splash = SplashScreen(root, duration=0)
            splash.update_status("Loading modules...")
            splash.update_status("Ready!")
            splash.close()
        finally:
            root.destroy()
    
    def test_splash_screen_standalone(self):
        """Test splash screen without parent"""
        splash = SplashScreen(parent=None, duration=0)
        assert splash.splash is not None
        splash.close()


class TestWelcomeWizard:
    """Test WelcomeWizard"""
    
    def test_wizard_creation(self):
        """Test creating welcome wizard"""
        root = tk.Tk()
        try:
            wizard = WelcomeWizard(root)
            assert wizard.current_page == 0
            assert len(wizard.pages) == 4
            wizard.window.destroy()
        finally:
            root.destroy()
    
    def test_wizard_navigation(self):
        """Test wizard page navigation"""
        root = tk.Tk()
        try:
            wizard = WelcomeWizard(root)
            
            # Start on page 0
            assert wizard.current_page == 0
            
            # Go to next page
            wizard.next_page()
            assert wizard.current_page == 1
            
            # Go forward multiple pages
            wizard.next_page()
            wizard.next_page()
            assert wizard.current_page == 3
            
            # Can't go beyond last page
            wizard.next_page()
            assert wizard.current_page == 3
            
            # Go back
            wizard.prev_page()
            assert wizard.current_page == 2
            
            wizard.window.destroy()
        finally:
            root.destroy()
    
    def test_wizard_settings(self):
        """Test wizard settings collection"""
        root = tk.Tk()
        try:
            wizard = WelcomeWizard(root)
            
            # Navigate to preferences page
            wizard.next_page()
            
            # Set some preferences
            wizard.theme_var.set("Dracula")
            wizard.grid_enabled.set(False)
            wizard.snap_enabled.set(True)
            
            # Finish wizard
            wizard.finish()
            
            settings = wizard.get_settings()
            assert settings["theme"] == "Dracula"
            assert settings["grid_enabled"] is False
            assert settings["snap_enabled"] is True
            assert settings["wizard_completed"] is True
        finally:
            root.destroy()


class TestIntegration:
    """Integration tests"""
    
    def test_theme_manager_with_widgets(self):
        """Test theme manager with actual widgets"""
        root = tk.Tk()
        try:
            manager = ThemeManager(root)
            
            # Create some widgets
            frame = tk.Frame(root)
            frame.pack()
            
            import tkinter.ttk as ttk
            label = ttk.Label(frame, text="Test")
            button = ttk.Button(frame, text="Click")
            label.pack()
            button.pack()
            
            # Switch theme
            manager.set_theme("Light Modern")
            root.update()
            
            manager.set_theme("Dracula")
            root.update()
        finally:
            root.destroy()
    
    def test_complete_workflow(self):
        """Test complete workflow: splash -> wizard -> themed app"""
        root = tk.Tk()
        root.withdraw()
        
        try:
            # Create splash
            splash = SplashScreen(root, duration=0)
            splash.update_status("Loading...")
            splash.close()
            
            # Show wizard
            root.deiconify()
            wizard = WelcomeWizard(root)
            
            # Navigate to preferences page to set theme
            wizard.next_page()
            wizard.theme_var.set("Nord")
            wizard.finish()
            
            settings = wizard.get_settings()
            
            # Apply theme
            manager = ThemeManager(root)
            manager.set_theme(settings["theme"])
            
            assert manager.current_theme == "Nord"
        finally:
            root.destroy()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
