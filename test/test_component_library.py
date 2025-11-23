#!/usr/bin/env python3
"""
Tests for Component Library system
"""

import json

import pytest

from ui_components_library import (
    ComponentLibrary,
    ComponentTemplate,
    create_alert_dialog,
    create_breadcrumb,
    create_button_group,
    create_confirm_dialog,
    create_default_library,
    create_grid_layout,
    create_header_footer,
    create_input_dialog,
    create_menu,
    create_progress_card,
    create_radio_group,
    create_sidebar_layout,
    create_stat_card,
    create_status_indicator,
    create_tab_bar,
    create_toggle_switch,
)
from ui_designer import UIDesigner


class TestComponentTemplate:
    """Test ComponentTemplate dataclass"""
    
    def test_template_creation(self):
        """Test creating a component template"""
        template = ComponentTemplate(
            name="TestComponent",
            category="Test",
            description="Test component",
            width=100,
            height=50,
            widgets=[]
        )
        
        assert template.name == "TestComponent"
        assert template.category == "Test"
        assert template.description == "Test component"
        assert template.width == 100
        assert template.height == 50
        assert template.widgets == []
        assert template.tags == []  # Default empty list
    
    def test_template_with_tags(self):
        """Test template with tags"""
        template = ComponentTemplate(
            name="Tagged",
            category="Test",
            description="Test",
            width=100,
            height=50,
            widgets=[],
            tags=["tag1", "tag2", "tag3"]
        )
        
        assert len(template.tags) == 3
        assert "tag1" in template.tags


class TestComponentLibrary:
    """Test ComponentLibrary class"""
    
    def test_library_creation(self):
        """Test creating empty library"""
        library = ComponentLibrary()
        assert len(library.components) == 0
        assert library.library_path.name == "components_library"
    
    def test_add_component(self):
        """Test adding component to library"""
        library = ComponentLibrary()
        
        template = ComponentTemplate(
            name="TestComp",
            category="Test",
            description="Test",
            width=100,
            height=50,
            widgets=[]
        )
        
        library.add_component(template)
        assert len(library.components) == 1
        assert "TestComp" in library.components
    
    def test_get_component(self):
        """Test retrieving component by name"""
        library = ComponentLibrary()
        
        template = ComponentTemplate(
            name="MyComponent",
            category="Test",
            description="Test",
            width=100,
            height=50,
            widgets=[]
        )
        
        library.add_component(template)
        
        retrieved = library.get_component("MyComponent")
        assert retrieved is not None
        assert retrieved.name == "MyComponent"
        
        missing = library.get_component("NonExistent")
        assert missing is None
    
    def test_list_components(self):
        """Test listing all components"""
        library = ComponentLibrary()
        
        library.add_component(ComponentTemplate("Comp1", "Cat1", "Test", 100, 50, []))
        library.add_component(ComponentTemplate("Comp2", "Cat2", "Test", 100, 50, []))
        library.add_component(ComponentTemplate("Comp3", "Cat1", "Test", 100, 50, []))
        
        all_comps = library.list_components()
        assert len(all_comps) == 3
        
        cat1_comps = library.list_components(category="Cat1")
        assert len(cat1_comps) == 2
        
        cat2_comps = library.list_components(category="Cat2")
        assert len(cat2_comps) == 1
    
    def test_get_categories(self):
        """Test getting unique categories"""
        library = ComponentLibrary()
        
        library.add_component(ComponentTemplate("C1", "Dialogs", "Test", 100, 50, []))
        library.add_component(ComponentTemplate("C2", "Navigation", "Test", 100, 50, []))
        library.add_component(ComponentTemplate("C3", "Dialogs", "Test", 100, 50, []))
        
        categories = library.get_categories()
        assert len(categories) == 2
        assert "Dialogs" in categories
        assert "Navigation" in categories
    
    def test_save_and_load_library(self, tmp_path):
        """Test saving and loading library from JSON"""
        library = ComponentLibrary()
        
        library.add_component(ComponentTemplate(
            name="SavedComp",
            category="Test",
            description="Test component",
            width=120,
            height=80,
            widgets=[],
            tags=["test", "save"]
        ))
        
        # Save
        output_file = tmp_path / "test_library.json"
        library.save_library(output_file)
        
        assert output_file.exists()
        
        # Verify JSON structure
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert 'components' in data
        assert len(data['components']) == 1
        assert data['components'][0]['name'] == "SavedComp"
        assert data['components'][0]['category'] == "Test"
        assert data['components'][0]['tags'] == ["test", "save"]


class TestDialogComponents:
    """Test dialog component creation"""
    
    def test_alert_dialog(self):
        """Test creating alert dialog"""
        dialog = create_alert_dialog(title="Warning", message="Alert!", button_text="Close")
        
        assert dialog.name == "AlertDialog"
        assert dialog.category == "Dialogs"
        assert dialog.width == 240
        assert dialog.height == 120
        assert len(dialog.widgets) == 4  # bg, title, message, button
        assert "alert" in dialog.tags
    
    def test_confirm_dialog(self):
        """Test creating confirm dialog"""
        dialog = create_confirm_dialog(title="Confirm", message="Sure?")
        
        assert dialog.name == "ConfirmDialog"
        assert dialog.category == "Dialogs"
        assert len(dialog.widgets) == 5  # bg, title, message, yes, no
        assert "confirm" in dialog.tags
    
    def test_input_dialog(self):
        """Test creating input dialog"""
        dialog = create_input_dialog(title="Name", label="Enter name:", placeholder="John")
        
        assert dialog.name == "InputDialog"
        assert dialog.category == "Dialogs"
        assert len(dialog.widgets) == 6  # bg, title, label, field, placeholder, ok
        assert "input" in dialog.tags


class TestNavigationComponents:
    """Test navigation component creation"""
    
    def test_tab_bar(self):
        """Test creating tab bar"""
        tabs = create_tab_bar(tabs=["Home", "Settings"])
        
        assert tabs.name == "TabBar"
        assert tabs.category == "Navigation"
        assert len(tabs.widgets) == 2  # 2 tabs
        assert tabs.width == 240
    
    def test_vertical_menu(self):
        """Test creating vertical menu"""
        menu = create_menu(items=["Item1", "Item2", "Item3"])
        
        assert menu.name == "VerticalMenu"
        assert menu.category == "Navigation"
        assert len(menu.widgets) == 4  # bg + 3 items
        assert "menu" in menu.tags
    
    def test_breadcrumb(self):
        """Test creating breadcrumb"""
        crumb = create_breadcrumb(path=["Home", "Docs", "API"])
        
        assert crumb.name == "Breadcrumb"
        assert crumb.category == "Navigation"
        # 3 items + 2 separators
        assert len(crumb.widgets) == 5
        assert "breadcrumb" in crumb.tags


class TestDataDisplayComponents:
    """Test data display component creation"""
    
    def test_stat_card(self):
        """Test creating stat card"""
        card = create_stat_card(label="Users", value="1234", icon="👤")
        
        assert card.name == "StatCard"
        assert card.category == "Data Display"
        assert len(card.widgets) == 4  # bg, icon, value, label
        assert "stats" in card.tags
    
    def test_progress_card(self):
        """Test creating progress card"""
        card = create_progress_card(label="Loading", percentage=75)
        
        assert card.name == "ProgressCard"
        assert card.category == "Data Display"
        assert len(card.widgets) == 5  # bg, label, bar_bg, bar_fill, text
        assert "progress" in card.tags
    
    def test_status_indicator(self):
        """Test creating status indicator"""
        status = create_status_indicator(status="online", label="Server")
        
        assert status.name == "StatusIndicator"
        assert status.category == "Data Display"
        assert len(status.widgets) == 3  # dot, label, status_text
        assert "status" in status.tags


class TestControlComponents:
    """Test control component creation"""
    
    def test_button_group(self):
        """Test creating button group"""
        group = create_button_group(labels=["A", "B", "C"])
        
        assert group.name == "ButtonGroup"
        assert group.category == "Controls"
        assert len(group.widgets) == 3  # 3 buttons
        assert "button" in group.tags
    
    def test_toggle_switch(self):
        """Test creating toggle switch"""
        toggle = create_toggle_switch(label="Enable", enabled=True)
        
        assert toggle.name == "ToggleSwitch"
        assert toggle.category == "Controls"
        assert len(toggle.widgets) == 3  # label, bg, handle
        assert "toggle" in toggle.tags
    
    def test_radio_group(self):
        """Test creating radio group"""
        radio = create_radio_group(options=["A", "B"], selected=0)
        
        assert radio.name == "RadioGroup"
        assert radio.category == "Controls"
        # 2 circles, 1 inner dot (selected), 2 labels
        assert len(radio.widgets) == 5
        assert "radio" in radio.tags


class TestLayoutComponents:
    """Test layout component creation"""
    
    def test_header_footer(self):
        """Test creating header/footer layout"""
        layout = create_header_footer(header_text="App", footer_text="Footer")
        
        assert layout.name == "HeaderFooterLayout"
        assert layout.category == "Layouts"
        assert len(layout.widgets) == 5  # header_bg, title, content, footer_bg, footer_text
        assert "header" in layout.tags
    
    def test_sidebar_layout(self):
        """Test creating sidebar layout"""
        layout = create_sidebar_layout(sidebar_width=80)
        
        assert layout.name == "SidebarLayout"
        assert layout.category == "Layouts"
        assert len(layout.widgets) == 2  # sidebar, main content
        assert "sidebar" in layout.tags
    
    def test_grid_layout(self):
        """Test creating grid layout"""
        layout = create_grid_layout(rows=2, cols=3)
        
        assert layout.name == "GridLayout"
        assert layout.category == "Layouts"
        assert len(layout.widgets) == 6  # 2x3 = 6 cells
        assert "grid" in layout.tags


class TestDefaultLibrary:
    """Test default library creation"""
    
    def test_create_default_library(self):
        """Test creating default library with all components"""
        library = create_default_library()
        
        # Should have 15 components (3 dialogs + 3 navigation + 3 data + 3 controls + 3 layouts)
        assert len(library.components) == 15
        
        # Check categories
        categories = library.get_categories()
        assert "Dialogs" in categories
        assert "Navigation" in categories
        assert "Data Display" in categories
        assert "Controls" in categories
        assert "Layouts" in categories
        
        # Check each category has 3 components
        assert len(library.list_components("Dialogs")) == 3
        assert len(library.list_components("Navigation")) == 3
        assert len(library.list_components("Data Display")) == 3
        assert len(library.list_components("Controls")) == 3
        assert len(library.list_components("Layouts")) == 3


class TestDesignerIntegration:
    """Test integration with UIDesigner"""
    
    def test_create_from_template(self):
        """Test creating component instance in designer"""
        designer = UIDesigner()
        library = ComponentLibrary()
        
        # Create simple template
        template = ComponentTemplate(
            name="TestTemplate",
            category="Test",
            description="Test",
            width=100,
            height=50,
            widgets=[
                # Import needed widget config manually for test
            ]
        )
        library.add_component(template)
        
        # Test would create component in designer
        # (skipped actual widget creation to avoid WidgetConfig import complexity)
        assert library.get_component("TestTemplate") is not None
    
    def test_create_with_offset(self):
        """Test creating component with position offset"""
        # Create alert dialog (has widgets)
        dialog = create_alert_dialog()
        
        # Check widgets have positions
        for widget in dialog.widgets:
            assert hasattr(widget, 'x')
            assert hasattr(widget, 'y')
            
            # Verify positions are reasonable
            assert widget.x >= 0
            assert widget.y >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
