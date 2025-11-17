#!/usr/bin/env python3
"""
UI Components Library
Pre-built, reusable UI components for ESP32OS
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ui_designer import UIDesigner, WidgetConfig, WidgetType


@dataclass
class ComponentTemplate:
    """Component template definition"""
    name: str
    category: str
    description: str
    width: int
    height: int
    widgets: List[WidgetConfig]
    preview_image: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ComponentLibrary:
    """Manage reusable UI components"""
    
    def __init__(self, library_path: Optional[Path] = None):
        self.library_path = library_path or Path("components_library")
        self.library_path.mkdir(exist_ok=True)
        self.components: Dict[str, ComponentTemplate] = {}
        self._load_library()
    
    def _load_library(self):
        """Load all components from library directory"""
        if not self.library_path.exists():
            return
        
        for json_file in self.library_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if 'components' in data:
                    for comp_data in data['components']:
                        comp = ComponentTemplate(**comp_data)
                        self.components[comp.name] = comp
            except Exception as e:
                print(f"Warning: Failed to load {json_file}: {e}")
    
    def add_component(self, component: ComponentTemplate):
        """Add component to library"""
        self.components[component.name] = component
    
    def get_component(self, name: str) -> Optional[ComponentTemplate]:
        """Get component by name"""
        return self.components.get(name)
    
    def list_components(self, category: Optional[str] = None) -> List[ComponentTemplate]:
        """List all components, optionally filtered by category"""
        if category:
            return [c for c in self.components.values() if c.category == category]
        return list(self.components.values())
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        return sorted(set(c.category for c in self.components.values()))
    
    def save_library(self, output_file: Path):
        """Save library to JSON file"""
        data = {
            'components': [asdict(c) for c in self.components.values()]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def create_from_template(self, designer: UIDesigner, template_name: str, 
                            offset_x: int = 0, offset_y: int = 0) -> List[int]:
        """Create component instance in designer from template"""
        template = self.get_component(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        created_indices = []
        
        for widget in template.widgets:
            # Apply offset
            widget_dict = asdict(widget)
            widget_dict['x'] += offset_x
            widget_dict['y'] += offset_y
            
            # Add to designer
            designer.add_widget(**widget_dict)
            created_indices.append(len(designer.current_scene.widgets) - 1)
        
        return created_indices


# ========== DIALOG COMPONENTS ==========

def create_alert_dialog(title: str = "Alert", message: str = "Message", 
                       button_text: str = "OK") -> ComponentTemplate:
    """Alert dialog with OK button"""
    widgets = [
        # Background panel
        WidgetConfig(
            type=WidgetType.PANEL,
            x=20, y=10,
            width=200, height=100,
            bg_color=0x2C3E50,
            border_width=2,
            border_color=0x3498DB
        ),
        # Title
        WidgetConfig(
            type=WidgetType.LABEL,
            x=30, y=20,
            text=title,
            font_size=16,
            color=0xECF0F1,
            bold=True
        ),
        # Message
        WidgetConfig(
            type=WidgetType.LABEL,
            x=30, y=45,
            text=message,
            font_size=12,
            color=0xBDC3C7,
            width=180
        ),
        # OK Button
        WidgetConfig(
            type=WidgetType.BUTTON,
            x=80, y=75,
            width=80, height=25,
            text=button_text,
            bg_color=0x3498DB,
            text_color=0xFFFFFF,
            corner_radius=4
        )
    ]
    
    return ComponentTemplate(
        name="AlertDialog",
        category="Dialogs",
        description="Simple alert dialog with OK button",
        width=240,
        height=120,
        widgets=widgets,
        tags=["dialog", "alert", "notification"]
    )


def create_confirm_dialog(title: str = "Confirm", message: str = "Are you sure?",
                         yes_text: str = "Yes", no_text: str = "No") -> ComponentTemplate:
    """Confirm dialog with Yes/No buttons"""
    widgets = [
        # Background
        WidgetConfig(
            type=WidgetType.PANEL,
            x=20, y=10,
            width=200, height=110,
            bg_color=0x2C3E50,
            border_width=2,
            border_color=0xE74C3C
        ),
        # Title
        WidgetConfig(
            type=WidgetType.LABEL,
            x=30, y=20,
            text=title,
            font_size=16,
            color=0xECF0F1,
            bold=True
        ),
        # Message
        WidgetConfig(
            type=WidgetType.LABEL,
            x=30, y=45,
            text=message,
            font_size=12,
            color=0xBDC3C7,
            width=180
        ),
        # Yes Button
        WidgetConfig(
            type=WidgetType.BUTTON,
            x=30, y=80,
            width=80, height=25,
            text=yes_text,
            bg_color=0x27AE60,
            text_color=0xFFFFFF,
            corner_radius=4
        ),
        # No Button
        WidgetConfig(
            type=WidgetType.BUTTON,
            x=120, y=80,
            width=80, height=25,
            text=no_text,
            bg_color=0xE74C3C,
            text_color=0xFFFFFF,
            corner_radius=4
        )
    ]
    
    return ComponentTemplate(
        name="ConfirmDialog",
        category="Dialogs",
        description="Confirmation dialog with Yes/No buttons",
        width=240,
        height=130,
        widgets=widgets,
        tags=["dialog", "confirm", "yesno"]
    )


def create_input_dialog(title: str = "Input", label: str = "Enter value:",
                       placeholder: str = "") -> ComponentTemplate:
    """Input dialog with text field"""
    widgets = [
        # Background
        WidgetConfig(
            type=WidgetType.PANEL,
            x=20, y=10,
            width=200, height=120,
            bg_color=0x2C3E50,
            border_width=2,
            border_color=0x9B59B6
        ),
        # Title
        WidgetConfig(
            type=WidgetType.LABEL,
            x=30, y=20,
            text=title,
            font_size=16,
            color=0xECF0F1,
            bold=True
        ),
        # Label
        WidgetConfig(
            type=WidgetType.LABEL,
            x=30, y=45,
            text=label,
            font_size=12,
            color=0xBDC3C7
        ),
        # Text field (represented as box)
        WidgetConfig(
            type=WidgetType.BOX,
            x=30, y=65,
            width=180, height=25,
            bg_color=0x34495E,
            border_width=1,
            border_color=0x7F8C8D
        ),
        # Placeholder text
        WidgetConfig(
            type=WidgetType.LABEL,
            x=35, y=70,
            text=placeholder,
            font_size=10,
            color=0x7F8C8D
        ),
        # OK Button
        WidgetConfig(
            type=WidgetType.BUTTON,
            x=80, y=95,
            width=80, height=25,
            text="OK",
            bg_color=0x9B59B6,
            text_color=0xFFFFFF,
            corner_radius=4
        )
    ]
    
    return ComponentTemplate(
        name="InputDialog",
        category="Dialogs",
        description="Input dialog with text field and OK button",
        width=240,
        height=140,
        widgets=widgets,
        tags=["dialog", "input", "textfield"]
    )


# ========== NAVIGATION COMPONENTS ==========

def create_tab_bar(tabs: List[str] = None) -> ComponentTemplate:
    """Tab bar with 2-4 tabs"""
    if tabs is None:
        tabs = ["Home", "Settings", "About"]
    
    tab_count = len(tabs)
    tab_width = 240 // tab_count
    
    widgets = []
    
    for i, tab_name in enumerate(tabs):
        # Tab button
        widgets.append(WidgetConfig(
            _widget_id=f"tab_{i}",
            type=WidgetType.BUTTON,
            x=i * tab_width,
            y=0,
            width=tab_width,
            height=30,
            text=tab_name,
            bg_color=0x3498DB if i == 0 else 0x2C3E50,
            text_color=0xFFFFFF,
            corner_radius=0
        ))
    
    return ComponentTemplate(
        name="TabBar",
        category="Navigation",
        description=f"Tab bar with {tab_count} tabs",
        width=240,
        height=30,
        widgets=widgets,
        tags=["navigation", "tabs", "menu"]
    )


def create_menu(items: List[str] = None) -> ComponentTemplate:
    """Vertical menu list"""
    if items is None:
        items = ["Dashboard", "Settings", "Profile", "Help", "Logout"]
    
    item_height = 35
    
    widgets = [
        # Menu background
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=0,
            width=180,
            height=len(items) * item_height,
            bg_color=0x2C3E50
        )
    ]
    
    for i, item_name in enumerate(items):
        # Menu item
        widgets.append(WidgetConfig(
            _widget_id=f"menu_item_{i}",
            type=WidgetType.BUTTON,
            x=5,
            y=i * item_height + 2,
            width=170,
            height=30,
            text=item_name,
            bg_color=0x34495E if i == 0 else 0x2C3E50,
            text_color=0xECF0F1,
            corner_radius=3,
            align="left"
        ))
    
    return ComponentTemplate(
        name="VerticalMenu",
        category="Navigation",
        description=f"Vertical menu with {len(items)} items",
        width=180,
        height=len(items) * item_height,
        widgets=widgets,
        tags=["navigation", "menu", "sidebar"]
    )


def create_breadcrumb(path: List[str] = None) -> ComponentTemplate:
    """Breadcrumb navigation"""
    if path is None:
        path = ["Home", "Settings", "Display"]
    
    widgets = []
    x_offset = 10
    
    for i, item in enumerate(path):
        # Item label
        widgets.append(WidgetConfig(
            _widget_id=f"breadcrumb_{i}",
            type=WidgetType.LABEL,
            x=x_offset,
            y=5,
            text=item,
            font_size=12,
            color=0x3498DB if i == len(path) - 1 else 0x7F8C8D
        ))
        
        x_offset += len(item) * 8 + 10
        
        # Separator (except last)
        if i < len(path) - 1:
            widgets.append(WidgetConfig(
                _widget_id=f"breadcrumb_sep_{i}",
                type=WidgetType.LABEL,
                x=x_offset,
                y=5,
                text=">",
                font_size=12,
                color=0x7F8C8D
            ))
            x_offset += 20
    
    return ComponentTemplate(
        name="Breadcrumb",
        category="Navigation",
        description="Breadcrumb navigation trail",
        width=240,
        height=20,
        widgets=widgets,
        tags=["navigation", "breadcrumb", "path"]
    )


# ========== DATA DISPLAY COMPONENTS ==========

def create_stat_card(label: str = "Total Users", value: str = "1,234",
                    icon: str = "👤") -> ComponentTemplate:
    """Statistics card with value and label"""
    widgets = [
        # Card background
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=0,
            width=110, height=80,
            bg_color=0x3498DB,
            corner_radius=8
        ),
        # Icon
        WidgetConfig(
            type=WidgetType.LABEL,
            x=10, y=10,
            text=icon,
            font_size=24,
            color=0xFFFFFF
        ),
        # Value
        WidgetConfig(
            type=WidgetType.LABEL,
            x=10, y=40,
            text=value,
            font_size=18,
            color=0xFFFFFF,
            bold=True
        ),
        # Label
        WidgetConfig(
            type=WidgetType.LABEL,
            x=10, y=60,
            text=label,
            font_size=10,
            color=0xECF0F1
        )
    ]
    
    return ComponentTemplate(
        name="StatCard",
        category="Data Display",
        description="Statistics card with icon, value, and label",
        width=110,
        height=80,
        widgets=widgets,
        tags=["card", "stats", "metrics"]
    )


def create_progress_card(label: str = "Progress", percentage: int = 65) -> ComponentTemplate:
    """Progress card with circular/linear indicator"""
    widgets = [
        # Card background
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=0,
            width=150, height=70,
            bg_color=0x2C3E50,
            corner_radius=6
        ),
        # Label
        WidgetConfig(
            type=WidgetType.LABEL,
            x=10, y=10,
            text=label,
            font_size=12,
            color=0xECF0F1
        ),
        # Progress bar background
        WidgetConfig(
            type=WidgetType.BOX,
            x=10, y=35,
            width=130, height=15,
            bg_color=0x34495E,
            corner_radius=8
        ),
        # Progress bar fill
        WidgetConfig(
            type=WidgetType.BOX,
            x=10, y=35,
            width=int(130 * percentage / 100), height=15,
            bg_color=0x27AE60,
            corner_radius=8
        ),
        # Percentage text
        WidgetConfig(
            type=WidgetType.LABEL,
            x=60, y=53,
            text=f"{percentage}%",
            font_size=10,
            color=0xBDC3C7
        )
    ]
    
    return ComponentTemplate(
        name="ProgressCard",
        category="Data Display",
        description="Progress card with linear indicator",
        width=150,
        height=70,
        widgets=widgets,
        tags=["progress", "percentage", "indicator"]
    )


def create_status_indicator(status: str = "online", label: str = "System Status") -> ComponentTemplate:
    """Status indicator with colored dot"""
    status_colors = {
        "online": 0x27AE60,
        "offline": 0x95A5A6,
        "warning": 0xF39C12,
        "error": 0xE74C3C
    }
    
    color = status_colors.get(status.lower(), 0x95A5A6)
    
    widgets = [
        # Status dot
        WidgetConfig(
            type=WidgetType.BOX,
            x=0, y=2,
            width=12, height=12,
            bg_color=color,
            corner_radius=6
        ),
        # Label
        WidgetConfig(
            type=WidgetType.LABEL,
            x=20, y=0,
            text=label,
            font_size=12,
            color=0xECF0F1
        ),
        # Status text
        WidgetConfig(
            type=WidgetType.LABEL,
            x=20, y=15,
            text=status.capitalize(),
            font_size=10,
            color=color
        )
    ]
    
    return ComponentTemplate(
        name="StatusIndicator",
        category="Data Display",
        description="Status indicator with colored dot and text",
        width=120,
        height=30,
        widgets=widgets,
        tags=["status", "indicator", "dot"]
    )


# ========== CONTROL COMPONENTS ==========

def create_button_group(labels: List[str] = None) -> ComponentTemplate:
    """Button group with 2-3 buttons"""
    if labels is None:
        labels = ["Option 1", "Option 2", "Option 3"]
    
    button_width = 75
    spacing = 5
    
    widgets = []
    
    for i, label in enumerate(labels):
        widgets.append(WidgetConfig(
            _widget_id=f"btn_{i}",
            type=WidgetType.BUTTON,
            x=i * (button_width + spacing),
            y=0,
            width=button_width,
            height=30,
            text=label,
            bg_color=0x3498DB if i == 0 else 0x7F8C8D,
            text_color=0xFFFFFF,
            corner_radius=4
        ))
    
    return ComponentTemplate(
        name="ButtonGroup",
        category="Controls",
        description=f"Button group with {len(labels)} buttons",
        width=len(labels) * (button_width + spacing) - spacing,
        height=30,
        widgets=widgets,
        tags=["button", "group", "controls"]
    )


def create_toggle_switch(label: str = "Enable Feature", enabled: bool = False) -> ComponentTemplate:
    """Toggle switch control"""
    widgets = [
        # Label
        WidgetConfig(
            type=WidgetType.LABEL,
            x=0, y=5,
            text=label,
            font_size=12,
            color=0xECF0F1
        ),
        # Switch background
        WidgetConfig(
            type=WidgetType.BOX,
            x=150, y=2,
            width=50, height=25,
            bg_color=0x27AE60 if enabled else 0x95A5A6,
            corner_radius=12
        ),
        # Switch handle
        WidgetConfig(
            type=WidgetType.BOX,
            x=175 if enabled else 153,
            y=5,
            width=20, height=19,
            bg_color=0xFFFFFF,
            corner_radius=10
        )
    ]
    
    return ComponentTemplate(
        name="ToggleSwitch",
        category="Controls",
        description="Toggle switch with label",
        width=210,
        height=30,
        widgets=widgets,
        tags=["toggle", "switch", "checkbox"]
    )


def create_radio_group(options: List[str] = None, selected: int = 0) -> ComponentTemplate:
    """Radio button group"""
    if options is None:
        options = ["Option A", "Option B", "Option C"]
    
    item_height = 25
    
    widgets = []
    
    for i, option in enumerate(options):
        # Radio circle
        widgets.append(WidgetConfig(
            _widget_id=f"radio_{i}",
            type=WidgetType.BOX,
            x=0,
            y=i * item_height + 2,
            width=16, height=16,
            bg_color=0x3498DB if i == selected else 0x34495E,
            border_width=2,
            border_color=0x3498DB,
            corner_radius=8
        ))
        
        # Inner dot (if selected)
        if i == selected:
            widgets.append(WidgetConfig(
                _widget_id=f"radio_dot_{i}",
                type=WidgetType.BOX,
                x=4,
                y=i * item_height + 6,
                width=8, height=8,
                bg_color=0xFFFFFF,
                corner_radius=4
            ))
        
        # Label
        widgets.append(WidgetConfig(
            _widget_id=f"radio_label_{i}",
            type=WidgetType.LABEL,
            x=25,
            y=i * item_height + 2,
            text=option,
            font_size=12,
            color=0xECF0F1
        ))
    
    return ComponentTemplate(
        name="RadioGroup",
        category="Controls",
        description=f"Radio button group with {len(options)} options",
        width=150,
        height=len(options) * item_height,
        widgets=widgets,
        tags=["radio", "choice", "selection"]
    )


# ========== LAYOUT COMPONENTS ==========

def create_header_footer(header_text: str = "Application Title",
                        footer_text: str = "© 2025 ESP32OS") -> ComponentTemplate:
    """Header and footer layout"""
    widgets = [
        # Header
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=0,
            width=240, height=40,
            bg_color=0x2C3E50
        ),
        WidgetConfig(
            type=WidgetType.LABEL,
            x=10, y=12,
            text=header_text,
            font_size=16,
            color=0xECF0F1,
            bold=True
        ),
        # Content area indicator
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=40,
            width=240, height=240,
            bg_color=0x34495E,
            border_width=1,
            border_color=0x7F8C8D
        ),
        # Footer
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=280,
            width=240, height=30,
            bg_color=0x2C3E50
        ),
        WidgetConfig(
            type=WidgetType.LABEL,
            x=10, y=287,
            text=footer_text,
            font_size=10,
            color=0x95A5A6
        )
    ]
    
    return ComponentTemplate(
        name="HeaderFooterLayout",
        category="Layouts",
        description="Layout with header, content area, and footer",
        width=240,
        height=310,
        widgets=widgets,
        tags=["layout", "header", "footer"]
    )


def create_sidebar_layout(sidebar_width: int = 60) -> ComponentTemplate:
    """Sidebar layout"""
    widgets = [
        # Sidebar
        WidgetConfig(
            type=WidgetType.PANEL,
            x=0, y=0,
            width=sidebar_width, height=320,
            bg_color=0x2C3E50
        ),
        # Main content area
        WidgetConfig(
            type=WidgetType.PANEL,
            x=sidebar_width, y=0,
            width=240 - sidebar_width, height=320,
            bg_color=0x34495E,
            border_width=1,
            border_color=0x7F8C8D
        )
    ]
    
    return ComponentTemplate(
        name="SidebarLayout",
        category="Layouts",
        description="Layout with sidebar and main content area",
        width=240,
        height=320,
        widgets=widgets,
        tags=["layout", "sidebar", "navigation"]
    )


def create_grid_layout(rows: int = 2, cols: int = 2) -> ComponentTemplate:
    """Grid layout"""
    cell_width = 240 // cols
    cell_height = 320 // rows
    
    widgets = []
    
    for row in range(rows):
        for col in range(cols):
            widgets.append(WidgetConfig(
                _widget_id=f"grid_{row}_{col}",
                type=WidgetType.PANEL,
                x=col * cell_width,
                y=row * cell_height,
                width=cell_width - 4,
                height=cell_height - 4,
                bg_color=0x34495E,
                border_width=2,
                border_color=0x7F8C8D
            ))
    
    return ComponentTemplate(
        name="GridLayout",
        category="Layouts",
        description=f"{rows}x{cols} grid layout",
        width=240,
        height=320,
        widgets=widgets,
        tags=["layout", "grid", "cells"]
    )


# ========== LIBRARY INITIALIZATION ==========

def create_default_library() -> ComponentLibrary:
    """Create library with all default components"""
    library = ComponentLibrary()
    
    # Dialogs
    library.add_component(create_alert_dialog())
    library.add_component(create_confirm_dialog())
    library.add_component(create_input_dialog())
    
    # Navigation
    library.add_component(create_tab_bar())
    library.add_component(create_menu())
    library.add_component(create_breadcrumb())
    
    # Data Display
    library.add_component(create_stat_card())
    library.add_component(create_progress_card())
    library.add_component(create_status_indicator())
    
    # Controls
    library.add_component(create_button_group())
    library.add_component(create_toggle_switch())
    library.add_component(create_radio_group())
    
    # Layouts
    library.add_component(create_header_footer())
    library.add_component(create_sidebar_layout())
    library.add_component(create_grid_layout())
    
    return library


if __name__ == "__main__":
    # Create and save default library
    library = create_default_library()
    output_file = Path("components_library/default_components.json")
    output_file.parent.mkdir(exist_ok=True)
    library.save_library(output_file)
    
    print(f"✅ Created component library with {len(library.components)} components")
    print(f"📁 Saved to {output_file}")
    print("\nCategories:")
    for category in library.get_categories():
        components = library.list_components(category)
        print(f"  {category}: {len(components)} components")

