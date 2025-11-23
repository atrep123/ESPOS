#!/usr/bin/env python3
"""
ASCII-Compatible UI Components Library
Pre-built, reusable UI components for ESP32OS (WidgetConfig-compatible)
"""

from typing import List, Optional

from ui_designer import WidgetConfig

# ========== NEW COMPONENTS ===========

def create_slider_ascii(label: str = "Volume", value: int = 50, min_value: int = 0, max_value: int = 100) -> List[WidgetConfig]:
    """Slider component (ASCII)"""
    bar_width = 16
    knob_x = int(bar_width * (value - min_value) / (max_value - min_value))
    return [
        WidgetConfig(type="label", x=0, y=0, width=8, height=1, text=label, color_fg="white"),
        WidgetConfig(type="box", x=0, y=2, width=bar_width, height=1, color_bg="gray", color_fg="black", border=True, border_style="single"),
        WidgetConfig(type="box", x=knob_x, y=2, width=2, height=1, color_bg="blue", color_fg="white", border=True, border_style="rounded"),
        WidgetConfig(type="label", x=bar_width+2, y=2, width=4, height=1, text=str(value), color_fg="yellow")
    ]

def create_checkbox_ascii(label: str = "Enable Feature", checked: bool = False) -> List[WidgetConfig]:
    """Checkbox component (ASCII)"""
    return [
        WidgetConfig(type="box", x=0, y=0, width=2, height=1, color_bg="white", color_fg="black", border=True, border_style="single"),
        WidgetConfig(type="label", x=3, y=0, width=len(label)+2, height=1, text=label, color_fg="white"),
        WidgetConfig(type="label", x=0, y=0, width=2, height=1, text="✔" if checked else "", color_fg="green" if checked else "gray")
    ]

def create_notification_ascii(message: str = "Update complete!", type_: str = "info") -> List[WidgetConfig]:
    """Notification banner (ASCII)"""
    color = {"info": "blue", "success": "green", "error": "red", "warning": "yellow"}.get(type_, "blue")
    return [
        WidgetConfig(type="box", x=0, y=0, width=len(message)+4, height=3, color_bg=color, color_fg="white", border=True, border_style="rounded"),
        WidgetConfig(type="label", x=2, y=1, width=len(message), height=1, text=message, color_fg="white", align="center")
    ]

def create_chart_ascii(label: str = "Chart", data: Optional[List[int]] = None) -> List[WidgetConfig]:
    """Simple bar chart (ASCII)"""
    if data is None:
        data = [3, 7, 5, 2, 9]
    max_val = max(data) if data else 1
    chart_height = 6
    chart_width = len(data) * 3
    widgets = [
        WidgetConfig(type="box", x=0, y=0, width=chart_width+2, height=chart_height+2, color_bg="black", color_fg="white", border=True, border_style="single"),
        WidgetConfig(type="label", x=2, y=chart_height+1, width=chart_width, height=1, text=label, color_fg="yellow")
    ]
    for i, val in enumerate(data):
        bar_height = int(chart_height * val / max_val)
        widgets.append(WidgetConfig(type="box", x=2+i*3, y=chart_height-bar_height+1, width=2, height=bar_height, color_bg="cyan", color_fg="black"))
        widgets.append(WidgetConfig(type="label", x=2+i*3, y=chart_height+1, width=2, height=1, text=str(val), color_fg="white"))
    return widgets
#!/usr/bin/env python3
"""
ASCII-Compatible UI Components Library
Pre-built, reusable UI components for ESP32OS (WidgetConfig-compatible)
"""

from typing import List

from ui_designer import WidgetConfig

# ========== DIALOG COMPONENTS ==========

def create_alert_dialog_ascii(title: str = "Alert", message: str = "Message", button_text: str = "OK") -> List[WidgetConfig]:
    """Alert dialog with OK button (ASCII)"""
    return [
        WidgetConfig(type="box", x=2, y=1, width=24, height=8, color_bg="blue", color_fg="white", border=True, border_style="double"),
        WidgetConfig(type="label", x=4, y=2, width=20, height=1, text=title, style="bold", align="center", color_fg="yellow"),
        WidgetConfig(type="label", x=4, y=4, width=20, height=2, text=message, align="center", color_fg="white"),
        WidgetConfig(type="button", x=10, y=7, width=8, height=1, text=button_text, color_bg="cyan", color_fg="black", style="bold")
    ]

def create_confirm_dialog_ascii(title: str = "Confirm", message: str = "Are you sure?", yes_text: str = "Yes", no_text: str = "No") -> List[WidgetConfig]:
    """Confirm dialog with Yes/No buttons (ASCII)"""
    return [
        WidgetConfig(type="box", x=2, y=1, width=24, height=9, color_bg="magenta", color_fg="white", border=True, border_style="double"),
        WidgetConfig(type="label", x=4, y=2, width=20, height=1, text=title, style="bold", align="center", color_fg="yellow"),
        WidgetConfig(type="label", x=4, y=4, width=20, height=2, text=message, align="center", color_fg="white"),
        WidgetConfig(type="button", x=6, y=7, width=6, height=1, text=yes_text, color_bg="green", color_fg="white", style="bold"),
        WidgetConfig(type="button", x=16, y=7, width=6, height=1, text=no_text, color_bg="red", color_fg="white", style="bold")
    ]

def create_input_dialog_ascii(title: str = "Input", label: str = "Enter value:", placeholder: str = "") -> List[WidgetConfig]:
    """Input dialog with text field (ASCII)"""
    return [
        WidgetConfig(type="box", x=2, y=1, width=24, height=10, color_bg="gray", color_fg="white", border=True, border_style="double"),
        WidgetConfig(type="label", x=4, y=2, width=20, height=1, text=title, style="bold", align="center", color_fg="yellow"),
        WidgetConfig(type="label", x=4, y=4, width=20, height=1, text=label, align="left", color_fg="white"),
        WidgetConfig(type="box", x=4, y=6, width=16, height=1, color_bg="white", color_fg="black", border=True, border_style="single"),
        WidgetConfig(type="label", x=5, y=6, width=14, height=1, text=placeholder, align="left", color_fg="gray"),
        WidgetConfig(type="button", x=10, y=8, width=8, height=1, text="OK", color_bg="blue", color_fg="white", style="bold")
    ]

# ========== NAVIGATION COMPONENTS ==========

def create_tab_bar_ascii(tabs: Optional[List[str]] = None) -> List[WidgetConfig]:
    """Tab bar with 2-4 tabs (ASCII)"""
    if tabs is None:
        tabs = ["Home", "Settings", "About"]
    tab_count = len(tabs)
    tab_width = 24 // tab_count
    widgets = []
    for i, tab_name in enumerate(tabs):
        widgets.append(WidgetConfig(type="button", x=i * tab_width, y=0, width=tab_width, height=1, text=tab_name, color_bg="cyan" if i == 0 else "blue", color_fg="white", style="bold"))
    return widgets

def create_vertical_menu_ascii(items: Optional[List[str]] = None) -> List[WidgetConfig]:
    """Vertical menu list (ASCII)"""
    if items is None:
        items = ["Dashboard", "Settings", "Profile", "Help", "Logout"]
    widgets = [WidgetConfig(type="box", x=0, y=0, width=18, height=len(items)*2, color_bg="blue", color_fg="white", border=True, border_style="single")]
    for i, item_name in enumerate(items):
        widgets.append(WidgetConfig(type="button", x=2, y=i*2+1, width=14, height=1, text=item_name, color_bg="gray" if i == 0 else "blue", color_fg="white", align="left"))
    return widgets

def create_breadcrumb_ascii(path: Optional[List[str]] = None) -> List[WidgetConfig]:
    """Breadcrumb navigation (ASCII)"""
    if path is None:
        path = ["Home", "Settings", "Display"]
    widgets = []
    x_offset = 2
    for i, item in enumerate(path):
        widgets.append(WidgetConfig(type="label", x=x_offset, y=0, width=len(item)+2, height=1, text=item, color_fg="yellow" if i == len(path)-1 else "white", align="left"))
        x_offset += len(item) + 3
        if i < len(path)-1:
            widgets.append(WidgetConfig(type="label", x=x_offset, y=0, width=2, height=1, text=">", color_fg="gray"))
            x_offset += 3
    return widgets

# ========== DATA DISPLAY COMPONENTS ==========

def create_stat_card_ascii(label: str = "Total Users", value: str = "1,234", icon: str = "*") -> List[WidgetConfig]:
    """Statistics card (ASCII)"""
    return [
        WidgetConfig(type="box", x=0, y=0, width=14, height=6, color_bg="cyan", color_fg="black", border=True, border_style="rounded"),
        WidgetConfig(type="label", x=2, y=1, width=2, height=1, text=icon, color_fg="yellow"),
        WidgetConfig(type="label", x=5, y=1, width=7, height=1, text=value, style="bold", color_fg="black"),
        WidgetConfig(type="label", x=2, y=3, width=10, height=1, text=label, color_fg="white")
    ]

def create_progress_card_ascii(label: str = "Progress", percentage: int = 65) -> List[WidgetConfig]:
    """Progress card (ASCII)"""
    bar_width = int(12 * percentage / 100)
    return [
        WidgetConfig(type="box", x=0, y=0, width=16, height=4, color_bg="gray", color_fg="white", border=True, border_style="single"),
        WidgetConfig(type="label", x=2, y=1, width=10, height=1, text=label, color_fg="white"),
        WidgetConfig(type="box", x=2, y=2, width=12, height=1, color_bg="white", color_fg="black", border=True, border_style="single"),
        WidgetConfig(type="box", x=2, y=2, width=bar_width, height=1, color_bg="green", color_fg="black"),
        WidgetConfig(type="label", x=6, y=3, width=4, height=1, text=f"{percentage}%", color_fg="gray")
    ]

def create_status_indicator_ascii(status: str = "online", label: str = "System Status") -> List[WidgetConfig]:
    """Status indicator (ASCII)"""
    status_colors = {"online": "green", "offline": "gray", "warning": "yellow", "error": "red"}
    color = status_colors.get(status.lower(), "gray")
    return [
        WidgetConfig(type="label", x=0, y=0, width=2, height=1, text="●", color_fg=color),
        WidgetConfig(type="label", x=3, y=0, width=12, height=1, text=label, color_fg="white"),
        WidgetConfig(type="label", x=3, y=1, width=8, height=1, text=status.capitalize(), color_fg=color)
    ]

# ========== CONTROL COMPONENTS ==========

def create_button_group_ascii(labels: Optional[List[str]] = None) -> List[WidgetConfig]:
    """Button group (ASCII)"""
    if labels is None:
        labels = ["Option 1", "Option 2", "Option 3"]
    widgets = []
    for i, label in enumerate(labels):
        widgets.append(WidgetConfig(type="button", x=i*8, y=0, width=7, height=1, text=label, color_bg="cyan" if i == 0 else "gray", color_fg="black", style="bold"))
    return widgets

def create_toggle_switch_ascii(label: str = "Enable Feature", enabled: bool = False) -> List[WidgetConfig]:
    """Toggle switch (ASCII)"""
    return [
        WidgetConfig(type="label", x=0, y=0, width=14, height=1, text=label, color_fg="white"),
        WidgetConfig(type="box", x=16, y=0, width=6, height=1, color_bg="green" if enabled else "gray", color_fg="black", border=True, border_style="rounded"),
        WidgetConfig(type="label", x=17 if enabled else 16, y=0, width=2, height=1, text="●", color_fg="white")
    ]

def create_radio_group_ascii(options: List[str] = None, selected: int = 0) -> List[WidgetConfig]:
    """Radio button group (ASCII)"""
    if options is None:
        options = ["Option A", "Option B", "Option C"]
    widgets = []
    for i, option in enumerate(options):
        widgets.append(WidgetConfig(type="label", x=0, y=i*2, width=2, height=1, text="◉" if i == selected else "○", color_fg="cyan" if i == selected else "gray"))
        widgets.append(WidgetConfig(type="label", x=3, y=i*2, width=10, height=1, text=option, color_fg="white"))
    return widgets

# ========== LAYOUT COMPONENTS ==========

def create_header_footer_layout_ascii(header_text: str = "Application Title", footer_text: str = "© 2025 ESP32OS") -> List[WidgetConfig]:
    """Header and footer layout (ASCII)"""
    return [
        WidgetConfig(type="box", x=0, y=0, width=24, height=2, color_bg="blue", color_fg="white", border=True, border_style="single"),
        WidgetConfig(type="label", x=2, y=0, width=20, height=1, text=header_text, style="bold", align="center", color_fg="yellow"),
        WidgetConfig(type="box", x=0, y=2, width=24, height=16, color_bg="black", color_fg="white", border=True, border_style="single"),
        WidgetConfig(type="box", x=0, y=18, width=24, height=2, color_bg="blue", color_fg="white", border=True, border_style="single"),
        WidgetConfig(type="label", x=2, y=19, width=20, height=1, text=footer_text, align="center", color_fg="gray")
    ]

def create_sidebar_layout_ascii(sidebar_width: int = 6) -> List[WidgetConfig]:
    """Sidebar layout (ASCII)"""
    return [
        WidgetConfig(type="box", x=0, y=0, width=sidebar_width, height=20, color_bg="blue", color_fg="white", border=True, border_style="single"),
        WidgetConfig(type="box", x=sidebar_width, y=0, width=24-sidebar_width, height=20, color_bg="black", color_fg="white", border=True, border_style="single")
    ]

def create_grid_layout_ascii(rows: int = 2, cols: int = 2) -> List[WidgetConfig]:
    """Grid layout (ASCII)"""
    cell_width = 24 // cols
    cell_height = 20 // rows
    widgets = []
    for row in range(rows):
        for col in range(cols):
            widgets.append(WidgetConfig(type="box", x=col*cell_width, y=row*cell_height, width=cell_width-1, height=cell_height-1, color_bg="gray", color_fg="black", border=True, border_style="single"))
    return widgets
