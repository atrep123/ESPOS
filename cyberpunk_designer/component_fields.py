from __future__ import annotations

from typing import Dict, Tuple

FieldSpec = Tuple[str, str, str]


def component_field_specs(component: str) -> Dict[str, FieldSpec]:
    """Define editable component-level fields for the inspector.

    Returns mapping: public_key -> (role, attr, kind)
    kind: "str" | "int" | "int_list" | "choice:..."
    """
    c = str(component or "").strip().lower()
    if c == "card":
        return {
            "title": ("title", "text", "str"),
            "value": ("value", "text", "str"),
            "progress_value": ("progress", "value", "int"),
            "progress_max": ("progress", "max_value", "int"),
        }
    if c == "toast":
        return {
            "message": ("message", "text", "str"),
            "button": ("button", "text", "str"),
        }
    if c == "modal":
        return {
            "title": ("title", "text", "str"),
            "message": ("message", "text", "str"),
            "ok": ("ok", "text", "str"),
            "cancel": ("cancel", "text", "str"),
        }
    if c == "notification":
        return {
            "title": ("title", "text", "str"),
            "message": ("message", "text", "str"),
            "button": ("button", "text", "str"),
        }
    if c == "dialog_confirm":
        return {
            "title": ("title", "text", "str"),
            "message": ("message", "text", "str"),
            "confirm": ("confirm", "text", "str"),
            "cancel": ("cancel", "text", "str"),
        }
    if c in {"chart_bar", "chart_line"}:
        return {
            "title": ("title", "text", "str"),
            "mode": ("chart", "style", "choice:bar|line"),
            "points": ("chart", "data_points", "int_list"),
        }
    if c == "gauge_hud":
        return {
            "title": ("title", "text", "str"),
            "gauge_label": ("gauge", "text", "str"),
            "gauge_value": ("gauge", "value", "int"),
            "gauge_max": ("gauge", "max_value", "int"),
            "line1": ("line1", "text", "str"),
            "line2": ("line2", "text", "str"),
        }
    if c == "dashboard_256x128":
        return {
            "metric0_title": ("metric0.title", "text", "str"),
            "metric0_value": ("metric0.progress", "value", "int"),
            "metric1_title": ("metric1.title", "text", "str"),
            "metric1_value": ("metric1.progress", "value", "int"),
            "metric2_title": ("metric2.title", "text", "str"),
            "metric2_value": ("metric2.progress", "value", "int"),
            "main_text": ("main.text", "text", "str"),
            "footer_hint": ("footer.hint", "text", "str"),
        }
    if c == "status_bar":
        return {
            "left": ("left", "text", "str"),
            "right": ("right", "text", "str"),
        }
    if c == "tabs":
        return {
            "tab1": ("tab1", "text", "str"),
            "tab2": ("tab2", "text", "str"),
            "tab3": ("tab3", "text", "str"),
            "content_title": ("content.title", "text", "str"),
            "active_tab": ("tabbar", "text", "tabs_active"),
        }
    if c == "list":
        out: Dict[str, FieldSpec] = {
            "title": ("title", "text", "str"),
            "scroll": ("scroll", "text", "str"),
            "count": ("scroll", "text", "list_count"),
            "active_item": ("panel", "text", "menu_active"),
        }
        for i in range(6):
            out[f"item{i}"] = (f"item{i}.label", "text", "str")
            out[f"value{i}"] = (f"item{i}.value", "text", "str")
        return out
    if c in {"menu_list", "menu"}:
        out: Dict[str, FieldSpec] = {
            "title": ("title", "text", "str"),
            "scroll": ("scroll", "text", "str"),
            "count": ("scroll", "text", "list_count"),
            "active_item": ("panel", "text", "menu_active"),
        }
        for i in range(6):
            out[f"item{i}"] = (f"item{i}", "text", "str")
        return out
    if c == "list_item":
        return {
            "label": ("item", "text", "str"),
            "value": ("value", "text", "str"),
        }
    if c == "dialog":
        return {
            "title": ("title", "text", "str"),
            "message": ("message", "text", "str"),
            "ok": ("ok", "text", "str"),
            "cancel": ("cancel", "text", "str"),
        }
    return {}
