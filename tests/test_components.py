"""Tests for cyberpunk_designer/components.py component_blueprints."""

from types import SimpleNamespace

from cyberpunk_designer.components import component_blueprints

# Minimal scene config mock
SC = SimpleNamespace(width=256, height=128)
SC_SMALL = SimpleNamespace(width=128, height=64)

ALL_NAMES = [
    "card",
    "toast",
    "modal",
    "dialog_confirm",
    "notification",
    "chart_bar",
    "chart_line",
    "gauge_hud",
    "dashboard_256x128",
    "status_bar",
    "tabs",
    "list",
    "menu_list",
    "list_item",
    "setting_int",
    "setting_bool",
    "setting_enum",
    "dialog",
]


class TestComponentExistence:
    """Every known component name returns a non-empty list."""

    def test_card(self):
        assert len(component_blueprints("card", SC)) > 0

    def test_toast(self):
        assert len(component_blueprints("toast", SC)) > 0

    def test_modal(self):
        assert len(component_blueprints("modal", SC)) > 0

    def test_dialog_confirm(self):
        assert len(component_blueprints("dialog_confirm", SC)) > 0

    def test_notification(self):
        assert len(component_blueprints("notification", SC)) > 0

    def test_chart_bar(self):
        assert len(component_blueprints("chart_bar", SC)) > 0

    def test_chart_line(self):
        assert len(component_blueprints("chart_line", SC)) > 0

    def test_gauge_hud(self):
        assert len(component_blueprints("gauge_hud", SC)) > 0

    def test_dashboard(self):
        assert len(component_blueprints("dashboard_256x128", SC)) > 0

    def test_status_bar(self):
        assert len(component_blueprints("status_bar", SC)) > 0

    def test_tabs(self):
        assert len(component_blueprints("tabs", SC)) > 0

    def test_list(self):
        assert len(component_blueprints("list", SC)) > 0

    def test_menu_list(self):
        assert len(component_blueprints("menu_list", SC)) > 0

    def test_list_item(self):
        assert len(component_blueprints("list_item", SC)) > 0

    def test_setting_int(self):
        assert len(component_blueprints("setting_int", SC)) > 0

    def test_setting_bool(self):
        assert len(component_blueprints("setting_bool", SC)) > 0

    def test_setting_enum(self):
        assert len(component_blueprints("setting_enum", SC)) > 0

    def test_dialog(self):
        assert len(component_blueprints("dialog", SC)) > 0


class TestMenuAlias:
    def test_menu_aliases_to_menu_list(self):
        a = component_blueprints("menu", SC)
        b = component_blueprints("menu_list", SC)
        assert a == b


class TestUnknown:
    def test_unknown_returns_empty(self):
        assert component_blueprints("nonexistent_widget", SC) == []

    def test_empty_name_returns_empty(self):
        assert component_blueprints("", SC) == []


class TestWidgetDictShape:
    """Each widget dict must have type/x/y/width/height keys."""

    def test_card_widgets_have_required_keys(self):
        for w in component_blueprints("card", SC):
            assert "type" in w
            assert "x" in w
            assert "y" in w
            assert "width" in w
            assert "height" in w

    def test_modal_widgets_have_required_keys(self):
        for w in component_blueprints("modal", SC):
            assert "type" in w
            assert "x" in w
            assert "y" in w
            assert "width" in w
            assert "height" in w


class TestSmallScene:
    """Components should still produce valid output for smaller scenes."""

    def test_toast_small_scene(self):
        widgets = component_blueprints("toast", SC_SMALL)
        assert len(widgets) > 0
        for w in widgets:
            assert "type" in w

    def test_dialog_confirm_small_scene(self):
        widgets = component_blueprints("dialog_confirm", SC_SMALL)
        assert len(widgets) > 0


class TestAllComponentsReturn:
    """Parametric check that every known name returns widgets."""

    def test_all_names_return_widgets(self):
        for name in ALL_NAMES:
            result = component_blueprints(name, SC)
            assert len(result) > 0, f"component '{name}' returned empty list"

    def test_all_names_type_is_string(self):
        for name in ALL_NAMES:
            for w in component_blueprints(name, SC):
                assert isinstance(w.get("type"), str), f"component '{name}' has non-string type"
