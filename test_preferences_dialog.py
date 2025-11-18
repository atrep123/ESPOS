"""Tests for preferences_dialog.py"""

import pytest
import tkinter as tk
import tempfile
import os
from pathlib import Path
from preferences_dialog import (
    Preferences, PreferencesDialog, save_preferences, load_preferences
)


class TestPreferences:
    """Test Preferences dataclass"""
    
    def test_default_preferences(self):
        """Test default preferences"""
        prefs = Preferences()
        assert prefs.theme == "Dark Modern"
        assert prefs.grid_enabled is True
        assert prefs.grid_size == 10
        assert prefs.canvas_width == 320
        assert prefs.canvas_height == 240
        assert prefs.auto_save is True
        assert prefs.max_undo_levels == 50
    
    def test_custom_preferences(self):
        """Test custom preferences"""
        prefs = Preferences(
            theme="Dracula",
            grid_size=20,
            canvas_width=640,
            canvas_height=480,
            enable_profiler=True
        )
        assert prefs.theme == "Dracula"
        assert prefs.grid_size == 20
        assert prefs.canvas_width == 640
        assert prefs.enable_profiler is True


class TestPreferencesPersistence:
    """Test save/load preferences"""
    
    def test_save_and_load(self):
        """Test saving and loading preferences"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Create and save preferences
            prefs = Preferences(
                theme="Nord",
                grid_size=15,
                canvas_width=480,
                auto_save=False,
                debug_mode=True
            )
            save_preferences(prefs, temp_path)
            
            # Load and verify
            loaded = load_preferences(temp_path)
            assert loaded.theme == "Nord"
            assert loaded.grid_size == 15
            assert loaded.canvas_width == 480
            assert loaded.auto_save is False
            assert loaded.debug_mode is True
        finally:
            os.unlink(temp_path)
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns defaults"""
        prefs = load_preferences("nonexistent_file.json")
        assert isinstance(prefs, Preferences)
        assert prefs.theme == "Dark Modern"
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON returns defaults"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("invalid json {{{")
            temp_path = f.name
        
        try:
            prefs = load_preferences(temp_path)
            assert isinstance(prefs, Preferences)
            assert prefs.theme == "Dark Modern"
        finally:
            os.unlink(temp_path)


class TestPreferencesDialog:
    """Test PreferencesDialog"""
    
    def test_dialog_creation(self):
        """Test creating preferences dialog"""
        root = tk.Tk()
        try:
            prefs = Preferences()
            dialog = PreferencesDialog(root, prefs)
            assert dialog.prefs == prefs
            assert dialog.notebook is not None
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_dialog_with_callback(self):
        """Test dialog with apply callback"""
        root = tk.Tk()
        try:
            applied_prefs = []
            
            def on_apply(prefs):
                applied_prefs.append(prefs)
            
            initial = Preferences(theme="Light Modern")
            dialog = PreferencesDialog(root, initial, on_apply)
            
            # Simulate changing theme
            dialog.theme_var.set("Dracula")
            dialog.apply()
            
            assert len(applied_prefs) == 1
            assert applied_prefs[0].theme == "Dracula"
            
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_collect_preferences(self):
        """Test collecting preferences from UI"""
        root = tk.Tk()
        try:
            initial = Preferences()
            dialog = PreferencesDialog(root, initial)
            
            # Change some values
            dialog.theme_var.set("Nord")
            dialog.grid_size_var.set(25)
            dialog.canvas_width_var.set(800)
            dialog.enable_caching_var.set(False)
            
            # Collect
            collected = dialog._collect_preferences()
            assert collected.theme == "Nord"
            assert collected.grid_size == 25
            assert collected.canvas_width == 800
            assert collected.enable_caching is False
            
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_ok_button(self):
        """Test OK button applies and closes"""
        root = tk.Tk()
        try:
            applied = []
            
            def on_apply(prefs):
                applied.append(prefs)
            
            dialog = PreferencesDialog(root, Preferences(), on_apply)
            dialog.theme_var.set("Dracula")
            
            dialog.ok()
            
            assert len(applied) == 1
            assert applied[0].theme == "Dracula"
            # Window should be destroyed
        finally:
            root.destroy()
    
    def test_cancel_button(self):
        """Test cancel button doesn't apply"""
        root = tk.Tk()
        try:
            applied = []
            
            def on_apply(prefs):
                applied.append(prefs)
            
            dialog = PreferencesDialog(root, Preferences(), on_apply)
            dialog.theme_var.set("Dracula")
            
            dialog.cancel()
            
            assert len(applied) == 0
            assert dialog.result is None
        finally:
            root.destroy()
    
    def test_appearance_tab(self):
        """Test appearance tab controls"""
        root = tk.Tk()
        try:
            dialog = PreferencesDialog(root, Preferences())
            
            # Should have theme variable
            assert dialog.theme_var is not None
            assert dialog.theme_var.get() == "Dark Modern"
            
            # Change theme
            dialog.theme_var.set("Light Modern")
            dialog._preview_theme()
            
            assert dialog.colors.bg_primary == "#ffffff"
            
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_canvas_tab(self):
        """Test canvas tab controls"""
        root = tk.Tk()
        try:
            dialog = PreferencesDialog(root, Preferences())
            
            # Check default values
            assert dialog.canvas_width_var.get() == 320
            assert dialog.canvas_height_var.get() == 240
            assert dialog.grid_size_var.get() == 10
            
            # Change values
            dialog.canvas_width_var.set(640)
            dialog.canvas_height_var.set(480)
            dialog.grid_size_var.set(20)
            
            prefs = dialog._collect_preferences()
            assert prefs.canvas_width == 640
            assert prefs.canvas_height == 480
            assert prefs.grid_size == 20
            
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_export_tab(self):
        """Test export tab controls"""
        root = tk.Tk()
        try:
            dialog = PreferencesDialog(root, Preferences())
            
            # Check default format
            assert dialog.export_format_var.get() == "JSON"
            
            # Change format
            dialog.export_format_var.set("PDF")
            dialog.auto_backup_var.set(False)
            dialog.backup_interval_var.set(600)
            
            prefs = dialog._collect_preferences()
            assert prefs.export_format == "PDF"
            assert prefs.auto_backup is False
            assert prefs.backup_interval == 600
            
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_performance_tab(self):
        """Test performance tab controls"""
        root = tk.Tk()
        try:
            dialog = PreferencesDialog(root, Preferences())
            
            # Check defaults
            assert dialog.enable_caching_var.get() is True
            assert dialog.lazy_loading_var.get() is True
            
            # Disable optimizations
            dialog.enable_caching_var.set(False)
            dialog.lazy_loading_var.set(False)
            dialog.render_pooling_var.set(False)
            
            prefs = dialog._collect_preferences()
            assert prefs.enable_caching is False
            assert prefs.lazy_loading is False
            assert prefs.render_pooling is False
            
            dialog.window.destroy()
        finally:
            root.destroy()
    
    def test_advanced_tab(self):
        """Test advanced tab controls"""
        root = tk.Tk()
        try:
            dialog = PreferencesDialog(root, Preferences())
            
            # Check defaults
            assert dialog.max_undo_levels_var.get() == 50
            assert dialog.enable_profiler_var.get() is False
            
            # Enable debug options
            dialog.max_undo_levels_var.set(100)
            dialog.enable_profiler_var.set(True)
            dialog.debug_mode_var.set(True)
            
            prefs = dialog._collect_preferences()
            assert prefs.max_undo_levels == 100
            assert prefs.enable_profiler is True
            assert prefs.debug_mode is True
            
            dialog.window.destroy()
        finally:
            root.destroy()


class TestIntegration:
    """Integration tests"""
    
    def test_full_workflow(self):
        """Test complete preferences workflow"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            root = tk.Tk()
            try:
                # Create initial preferences
                initial = Preferences(theme="Dark Modern", grid_size=10)
                save_preferences(initial, temp_path)
                
                # Load in dialog
                loaded = load_preferences(temp_path)
                
                saved_prefs = []
                def on_apply(prefs):
                    save_preferences(prefs, temp_path)
                    saved_prefs.append(prefs)
                
                dialog = PreferencesDialog(root, loaded, on_apply)
                
                # Make changes
                dialog.theme_var.set("Nord")
                dialog.grid_size_var.set(20)
                dialog.canvas_width_var.set(640)
                
                # Apply
                dialog.ok()
                
                # Verify saved
                assert len(saved_prefs) == 1
                
                # Load again and verify persistence
                final = load_preferences(temp_path)
                assert final.theme == "Nord"
                assert final.grid_size == 20
                assert final.canvas_width == 640
            finally:
                root.destroy()
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
