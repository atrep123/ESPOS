"""Widget component blueprints and defaults.

This module is a thin dispatcher.  The actual builder functions live in:
- components_display  (card, toast, notification, modal, dialog*, status_bar, dashboard)
- components_nav      (tabs, list, menu_list, list_item)
- components_input    (chart_bar, chart_line, gauge_hud, settings, toggle)

Shared constants/helpers are in components_shared.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from .components_display import (
    build_card,
    build_dashboard_256x128,
    build_dialog,
    build_dialog_confirm,
    build_modal,
    build_notification,
    build_status_bar,
    build_toast,
)
from .components_input import (
    build_chart_bar,
    build_chart_line,
    build_gauge_hud,
    build_setting_bool,
    build_setting_enum,
    build_setting_int,
    build_toggle,
)
from .components_nav import (
    build_list,
    build_list_item,
    build_menu_list,
    build_tabs,
)

_BUILDERS: Dict[str, Callable[[object], List[Dict[str, Any]]]] = {
    "card": build_card,
    "toast": build_toast,
    "modal": build_modal,
    "dialog_confirm": build_dialog_confirm,
    "notification": build_notification,
    "chart_bar": build_chart_bar,
    "chart_line": build_chart_line,
    "gauge_hud": build_gauge_hud,
    "dashboard_256x128": build_dashboard_256x128,
    "status_bar": build_status_bar,
    "tabs": build_tabs,
    "list": build_list,
    "menu_list": build_menu_list,
    "list_item": build_list_item,
    "setting_int": build_setting_int,
    "setting_bool": build_setting_bool,
    "setting_enum": build_setting_enum,
    "dialog": build_dialog,
    "toggle": build_toggle,
}


def component_blueprints(name: str, sc: object) -> List[Dict[str, Any]]:
    """Return a list of widget dicts for a named component."""
    name = str(name or "").strip().lower()
    if name == "menu":
        name = "menu_list"
    builder = _BUILDERS.get(name)
    return builder(sc) if builder else []
