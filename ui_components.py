#!/usr/bin/env python3
"""
Component Library for UI Designer
Pre-built complex components and templates
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from ui_designer import UIDesigner, WidgetConfig, WidgetType, BorderStyle


@dataclass
class ComponentTemplate:
    """Component template definition"""
    name: str
    description: str
    category: str  # form, navigation, display, input, layout
    author: str
    version: str
    width: int
    height: int
    widgets: List[Dict[str, Any]]
    parameters: List[str] = field(default_factory=list)  # Customizable parameters
    tags: List[str] = field(default_factory=list)
    preview_ascii: str = ""


class ComponentLibrary:
    """Library of pre-built components"""
    
    def __init__(self):
        self.components: Dict[str, ComponentTemplate] = {}
        self._register_builtin_components()
    
    def _register_builtin_components(self):
        """Register all built-in components"""
        
        # LOGIN FORM
        login_form = ComponentTemplate(
            name="LoginForm",
            description="Complete login form with username, password, and button",
            category="form",
            author="ESP32OS",
            version="1.0",
            width=80,
            height=40,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 80, "height": 40, 
                 "text": "Login", "border": True, "border_style": "double"},
                {"type": "label", "x": 5, "y": 8, "width": 20, "height": 6, 
                 "text": "Username:"},
                {"type": "textbox", "x": 26, "y": 8, "width": 48, "height": 6, 
                 "text": "", "border": True},
                {"type": "label", "x": 5, "y": 16, "width": 20, "height": 6, 
                 "text": "Password:"},
                {"type": "textbox", "x": 26, "y": 16, "width": 48, "height": 6, 
                 "text": "********", "border": True},
                {"type": "button", "x": 20, "y": 28, "width": 40, "height": 8, 
                 "text": "Login", "border": True, "style": "bold"},
            ],
            parameters=["title", "button_text"],
            tags=["form", "login", "auth", "input"],
            preview_ascii="""
╔══════════════════════════════════╗
║ Login                            ║
╠══════════════════════════════════╣
║                                  ║
║ Username: [________________]     ║
║                                  ║
║ Password: [________________]     ║
║                                  ║
║        [ Login ]                 ║
║                                  ║
╚══════════════════════════════════╝
"""
        )
        
        # NAVIGATION MENU
        nav_menu = ComponentTemplate(
            name="NavigationMenu",
            description="Vertical navigation menu with 5 items",
            category="navigation",
            author="ESP32OS",
            version="1.0",
            width=60,
            height=45,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 60, "height": 45, 
                 "text": "Menu", "border": True, "border_style": "single"},
                {"type": "button", "x": 2, "y": 7, "width": 56, "height": 7, 
                 "text": "► Home", "border": True},
                {"type": "button", "x": 2, "y": 14, "width": 56, "height": 7, 
                 "text": "  Settings", "border": True},
                {"type": "button", "x": 2, "y": 21, "width": 56, "height": 7, 
                 "text": "  Data", "border": True},
                {"type": "button", "x": 2, "y": 28, "width": 56, "height": 7, 
                 "text": "  Info", "border": True},
                {"type": "button", "x": 2, "y": 35, "width": 56, "height": 7, 
                 "text": "  Exit", "border": True},
            ],
            parameters=["menu_items", "selected_index"],
            tags=["navigation", "menu", "sidebar"],
            preview_ascii="""
╔════════════════════════╗
║ Menu                   ║
╠════════════════════════╣
║ ┌──────────────────┐   ║
║ │ ► Home           │   ║
║ └──────────────────┘   ║
║ ┌──────────────────┐   ║
║ │   Settings       │   ║
║ └──────────────────┘   ║
║ ┌──────────────────┐   ║
║ │   Data           │   ║
║ └──────────────────┘   ║
╚════════════════════════╝
"""
        )
        
        # STATUS BAR
        status_bar = ComponentTemplate(
            name="StatusBar",
            description="Bottom status bar with icons and info",
            category="display",
            author="ESP32OS",
            version="1.0",
            width=128,
            height=10,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 128, "height": 10, 
                 "border": True, "border_style": "single"},
                {"type": "icon", "x": 2, "y": 2, "width": 6, "height": 6, 
                 "icon_char": "⚡", "text": "⚡"},
                {"type": "label", "x": 10, "y": 2, "width": 30, "height": 6, 
                 "text": "Battery: 85%"},
                {"type": "icon", "x": 45, "y": 2, "width": 6, "height": 6, 
                 "icon_char": "📶", "text": "📶"},
                {"type": "label", "x": 53, "y": 2, "width": 30, "height": 6, 
                 "text": "WiFi: OK"},
                {"type": "label", "x": 90, "y": 2, "width": 36, "height": 6, 
                 "text": "12:34:56", "align": "right"},
            ],
            parameters=["battery_level", "wifi_status", "time"],
            tags=["status", "info", "bar", "display"],
            preview_ascii="""
╔══════════════════════════════════════════════╗
║ ⚡ Battery: 85%  📶 WiFi: OK      12:34:56  ║
╚══════════════════════════════════════════════╝
"""
        )
        
        # GRAPH WIDGET
        graph_widget = ComponentTemplate(
            name="GraphWidget",
            description="Line graph with title and axis",
            category="display",
            author="ESP32OS",
            version="1.0",
            width=100,
            height=50,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 100, "height": 50, 
                 "text": "Performance", "border": True, "border_style": "double"},
                {"type": "chart", "x": 5, "y": 8, "width": 90, "height": 35, 
                 "border": True, "data_points": [10, 20, 35, 25, 40, 55, 45, 60]},
                {"type": "label", "x": 5, "y": 44, "width": 90, "height": 4, 
                 "text": "Time (seconds)", "align": "center"},
            ],
            parameters=["title", "data_points", "x_label", "y_label"],
            tags=["graph", "chart", "display", "data"],
            preview_ascii="""
╔══════════════════════════════════╗
║ Performance                      ║
╠══════════════════════════════════╣
║ ┌──────────────────────────────┐ ║
║ │         ╱╲    ╱╲             │ ║
║ │      ╱╲╱  ╲  ╱  ╲╱╲          │ ║
║ │   ╱╲╱      ╲╱                │ ║
║ │╱╲╱                           │ ║
║ └──────────────────────────────┘ ║
║      Time (seconds)              ║
╚══════════════════════════════════╝
"""
        )
        
        # SETTINGS PANEL
        settings_panel = ComponentTemplate(
            name="SettingsPanel",
            description="Settings panel with checkboxes and sliders",
            category="form",
            author="ESP32OS",
            version="1.0",
            width=120,
            height=60,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 120, "height": 60, 
                 "text": "Settings", "border": True, "border_style": "double"},
                
                {"type": "label", "x": 5, "y": 10, "width": 110, "height": 5, 
                 "text": "Display Options", "style": "bold"},
                {"type": "checkbox", "x": 10, "y": 16, "width": 100, "height": 6, 
                 "text": "Enable Animations", "checked": True},
                {"type": "checkbox", "x": 10, "y": 22, "width": 100, "height": 6, 
                 "text": "Show Grid", "checked": False},
                
                {"type": "label", "x": 5, "y": 30, "width": 110, "height": 5, 
                 "text": "Audio", "style": "bold"},
                {"type": "label", "x": 10, "y": 36, "width": 30, "height": 6, 
                 "text": "Volume:"},
                {"type": "slider", "x": 42, "y": 36, "width": 68, "height": 6, 
                 "value": 75, "min_value": 0, "max_value": 100},
                
                {"type": "button", "x": 30, "y": 48, "width": 30, "height": 8, 
                 "text": "Cancel", "border": True},
                {"type": "button", "x": 65, "y": 48, "width": 30, "height": 8, 
                 "text": "Apply", "border": True, "style": "bold"},
            ],
            parameters=["categories", "settings"],
            tags=["settings", "form", "options", "config"],
            preview_ascii="""
╔════════════════════════════════════════╗
║ Settings                               ║
╠════════════════════════════════════════╣
║                                        ║
║ Display Options                        ║
║   ☑ Enable Animations                 ║
║   ☐ Show Grid                          ║
║                                        ║
║ Audio                                  ║
║   Volume: ═════════●═══                ║
║                                        ║
║     [Cancel]      [Apply]              ║
╚════════════════════════════════════════╝
"""
        )
        
        # CARD WIDGET
        card_widget = ComponentTemplate(
            name="CardWidget",
            description="Info card with icon, title, and stats",
            category="display",
            author="ESP32OS",
            version="1.0",
            width=60,
            height=35,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 60, "height": 35, 
                 "border": True, "border_style": "rounded"},
                {"type": "icon", "x": 5, "y": 5, "width": 10, "height": 10, 
                 "icon_char": "📊", "text": "📊"},
                {"type": "label", "x": 18, "y": 5, "width": 37, "height": 8, 
                 "text": "Analytics", "style": "bold"},
                {"type": "label", "x": 5, "y": 18, "width": 50, "height": 6, 
                 "text": "Total: 1,234"},
                {"type": "label", "x": 5, "y": 24, "width": 50, "height": 6, 
                 "text": "Active: 567"},
            ],
            parameters=["icon", "title", "stats"],
            tags=["card", "display", "info", "dashboard"],
            preview_ascii="""
╭──────────────────────────────╮
│                              │
│  📊  Analytics               │
│                              │
│  Total: 1,234                │
│  Active: 567                 │
│                              │
╰──────────────────────────────╯
"""
        )
        
        # DIALOG BOX
        dialog_box = ComponentTemplate(
            name="DialogBox",
            description="Modal dialog with message and buttons",
            category="form",
            author="ESP32OS",
            version="1.0",
            width=90,
            height=40,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 90, "height": 40, 
                 "border": True, "border_style": "double"},
                {"type": "icon", "x": 5, "y": 8, "width": 8, "height": 8, 
                 "icon_char": "⚠", "text": "⚠"},
                {"type": "label", "x": 15, "y": 8, "width": 70, "height": 16, 
                 "text": "Are you sure you want to delete this item?"},
                {"type": "button", "x": 15, "y": 28, "width": 30, "height": 8, 
                 "text": "Cancel", "border": True},
                {"type": "button", "x": 50, "y": 28, "width": 30, "height": 8, 
                 "text": "Delete", "border": True, "style": "bold"},
            ],
            parameters=["icon", "message", "buttons"],
            tags=["dialog", "modal", "confirm", "alert"],
            preview_ascii="""
╔═══════════════════════════════════╗
║                                   ║
║  ⚠  Are you sure you want to     ║
║      delete this item?            ║
║                                   ║
║    [Cancel]      [Delete]         ║
║                                   ║
╚═══════════════════════════════════╝
"""
        )
        
        # PROGRESS TRACKER
        progress_tracker = ComponentTemplate(
            name="ProgressTracker",
            description="Multi-step progress indicator",
            category="display",
            author="ESP32OS",
            version="1.0",
            width=120,
            height=25,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 120, "height": 25, 
                 "text": "Installation Progress", "border": True},
                {"type": "label", "x": 10, "y": 8, "width": 8, "height": 6, 
                 "text": "✓", "style": "bold"},
                {"type": "label", "x": 20, "y": 8, "width": 25, "height": 6, 
                 "text": "Download"},
                {"type": "label", "x": 50, "y": 8, "width": 8, "height": 6, 
                 "text": "►", "style": "bold"},
                {"type": "label", "x": 60, "y": 8, "width": 25, "height": 6, 
                 "text": "Install"},
                {"type": "label", "x": 90, "y": 8, "width": 8, "height": 6, 
                 "text": "○"},
                {"type": "label", "x": 100, "y": 8, "width": 15, "height": 6, 
                 "text": "Done"},
                {"type": "progressbar", "x": 10, "y": 16, "width": 100, "height": 6, 
                 "value": 65, "border": True},
            ],
            parameters=["steps", "current_step", "progress"],
            tags=["progress", "stepper", "wizard", "install"],
            preview_ascii="""
╔════════════════════════════════════════╗
║ Installation Progress                  ║
╠════════════════════════════════════════╣
║  ✓ Download    ► Install    ○ Done    ║
║  ████████████████░░░░░░░░░░  65%      ║
╚════════════════════════════════════════╝
"""
        )
        
        # TABLE WIDGET
        table_widget = ComponentTemplate(
            name="TableWidget",
            description="Data table with headers and rows",
            category="display",
            author="ESP32OS",
            version="1.0",
            width=120,
            height=50,
            widgets=[
                {"type": "panel", "x": 0, "y": 0, "width": 120, "height": 50, 
                 "text": "Data Table", "border": True, "border_style": "double"},
                # Headers
                {"type": "label", "x": 3, "y": 8, "width": 30, "height": 6, 
                 "text": "Name", "style": "bold", "border": True},
                {"type": "label", "x": 35, "y": 8, "width": 30, "height": 6, 
                 "text": "Value", "style": "bold", "border": True},
                {"type": "label", "x": 67, "y": 8, "width": 50, "height": 6, 
                 "text": "Status", "style": "bold", "border": True},
                # Row 1
                {"type": "label", "x": 3, "y": 15, "width": 30, "height": 6, 
                 "text": "Item 1"},
                {"type": "label", "x": 35, "y": 15, "width": 30, "height": 6, 
                 "text": "100"},
                {"type": "label", "x": 67, "y": 15, "width": 50, "height": 6, 
                 "text": "Active"},
                # Row 2
                {"type": "label", "x": 3, "y": 22, "width": 30, "height": 6, 
                 "text": "Item 2"},
                {"type": "label", "x": 35, "y": 22, "width": 30, "height": 6, 
                 "text": "250"},
                {"type": "label", "x": 67, "y": 22, "width": 50, "height": 6, 
                 "text": "Pending"},
            ],
            parameters=["headers", "rows"],
            tags=["table", "data", "grid", "list"],
            preview_ascii="""
╔══════════════════════════════════════════╗
║ Data Table                               ║
╠══════════════════════════════════════════╣
║ ┌────────┬────────┬──────────────────┐   ║
║ │ Name   │ Value  │ Status           │   ║
║ ├────────┼────────┼──────────────────┤   ║
║ │ Item 1 │ 100    │ Active           │   ║
║ │ Item 2 │ 250    │ Pending          │   ║
║ └────────┴────────┴──────────────────┘   ║
╚══════════════════════════════════════════╝
"""
        )
        
        # Register all components
        for comp in [login_form, nav_menu, status_bar, graph_widget, 
                     settings_panel, card_widget, dialog_box, 
                     progress_tracker, table_widget]:
            self.register_component(comp)
    
    def register_component(self, component: ComponentTemplate):
        """Register a component"""
        self.components[component.name] = component
    
    def get_component(self, name: str) -> Optional[ComponentTemplate]:
        """Get component by name"""
        return self.components.get(name)
    
    def list_components(self, category: Optional[str] = None) -> List[str]:
        """List all components, optionally filtered by category"""
        if category:
            return [name for name, comp in self.components.items() 
                   if comp.category == category]
        return list(self.components.keys())
    
    def search_components(self, tag: str) -> List[ComponentTemplate]:
        """Search components by tag"""
        return [comp for comp in self.components.values() if tag in comp.tags]
    
    def instantiate_component(self, name: str, x: int = 0, y: int = 0, 
                            params: Optional[Dict[str, Any]] = None) -> List[WidgetConfig]:
        """Create widget instances from component template"""
        comp = self.components.get(name)
        if not comp:
            raise ValueError(f"Component '{name}' not found")
        
        widgets = []
        for widget_dict in comp.widgets:
            # Create widget config
            widget = WidgetConfig(
                type=widget_dict["type"],
                x=x + widget_dict["x"],
                y=y + widget_dict["y"],
                width=widget_dict["width"],
                height=widget_dict["height"],
                text=widget_dict.get("text", ""),
                style=widget_dict.get("style", "default"),
                color_fg=widget_dict.get("color_fg", "white"),
                color_bg=widget_dict.get("color_bg", "black"),
                border=widget_dict.get("border", False),
                border_style=widget_dict.get("border_style", "single"),
                align=widget_dict.get("align", "left"),
                valign=widget_dict.get("valign", "middle"),
                value=widget_dict.get("value", 0),
                checked=widget_dict.get("checked", False),
                icon_char=widget_dict.get("icon_char", ""),
                data_points=widget_dict.get("data_points", [])
            )
            
            # Apply parameters
            if params:
                self._apply_parameters(widget, params, comp.parameters)
            
            widgets.append(widget)
        
        return widgets
    
    def _apply_parameters(self, widget: WidgetConfig, params: Dict[str, Any], 
                         param_names: List[str]):
        """Apply custom parameters to widget"""
        # Simple parameter mapping
        if "title" in params and widget.type == "panel":
            widget.text = params["title"]
        if "button_text" in params and widget.type == "button":
            widget.text = params["button_text"]
        # Add more parameter mappings as needed
    
    def export_component(self, component_name: str, filename: str):
        """Export component to JSON"""
        comp = self.components.get(component_name)
        if not comp:
            raise ValueError(f"Component '{component_name}' not found")
        
        comp_dict = asdict(comp)
        with open(filename, 'w') as f:
            json.dump(comp_dict, f, indent=2)
    
    def import_component(self, filename: str) -> ComponentTemplate:
        """Import component from JSON"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        comp = ComponentTemplate(**data)
        self.register_component(comp)
        return comp
    
    def preview_component(self, component_name: str) -> str:
        """Get ASCII preview of component"""
        comp = self.components.get(component_name)
        if not comp:
            return f"Component '{component_name}' not found"
        
        info = f"""
╔══════════════════════════════════════════════════════════╗
║ {comp.name:<54} ║
╠══════════════════════════════════════════════════════════╣
║ Category: {comp.category:<46} ║
║ Size: {comp.width}×{comp.height:<49} ║
║ Widgets: {len(comp.widgets):<47} ║
╠══════════════════════════════════════════════════════════╣
║ {comp.description:<54} ║
╠══════════════════════════════════════════════════════════╣
{comp.preview_ascii}
╠══════════════════════════════════════════════════════════╣
║ Tags: {', '.join(comp.tags):<50} ║
╚══════════════════════════════════════════════════════════╝
"""
        return info


def main():
    """Demo component library"""
    print("📦 UI DESIGNER COMPONENT LIBRARY\n")
    
    library = ComponentLibrary()
    
    print("Available Components:")
    print()
    
    categories = ["form", "navigation", "display"]
    for category in categories:
        comps = library.list_components(category)
        print(f"  {category.upper()}:")
        for comp_name in comps:
            comp = library.get_component(comp_name)
            print(f"    • {comp_name} - {comp.description}")
        print()
    
    # Preview some components
    print("="*60)
    for comp_name in ["LoginForm", "NavigationMenu", "StatusBar", "GraphWidget"]:
        print(library.preview_component(comp_name))
    
    # Export example
    print("\n📦 Exporting 'LoginForm' component...")
    library.export_component("LoginForm", "component_login.json")
    print("✓ Saved to component_login.json")
    
    # Instantiate example
    print("\n🎯 Instantiating 'StatusBar' component...")
    widgets = library.instantiate_component("StatusBar", x=0, y=54, 
                                          params={"battery_level": 90, "time": "14:30:00"})
    print(f"✓ Created {len(widgets)} widgets")
    
    print("\n✅ Component library ready!")
    print(f"   Total components: {len(library.components)}")


if __name__ == "__main__":
    main()
