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


# ===================================================================
# BH – Blueprint validation & scene-dependent sizing
# ===================================================================

REQUIRED_KEYS = {"type", "x", "y", "width", "height"}


class TestAllBlueprintsHaveRequiredKeys:
    """Every widget dict from every component must have the 5 required keys."""

    def test_all_components_all_widgets(self):
        for name in ALL_NAMES:
            bps = component_blueprints(name, SC)
            for i, bp in enumerate(bps):
                missing = REQUIRED_KEYS - set(bp.keys())
                assert not missing, f"component '{name}' widget {i} missing keys: {missing}"


class TestBlueprintGeometry:
    """Widget dimensions must be positive integers."""

    def test_positive_dimensions(self):
        for name in ALL_NAMES:
            for bp in component_blueprints(name, SC):
                w = int(bp.get("width", 0))
                h = int(bp.get("height", 0))
                assert w > 0, f"component '{name}' widget has width={w}"
                assert h > 0, f"component '{name}' widget has height={h}"

    def test_coords_are_integers(self):
        for name in ALL_NAMES:
            for bp in component_blueprints(name, SC):
                for key in ("x", "y", "width", "height"):
                    val = bp.get(key, 0)
                    assert isinstance(val, int), (
                        f"component '{name}' widget has {key}={val!r} ({type(val).__name__})"
                    )


class TestSceneSizeAdaptation:
    """Components that use scene dimensions should adapt to smaller screens."""

    def test_toast_adapts_to_small_scene(self):
        bps_big = component_blueprints("toast", SC)
        bps_small = component_blueprints("toast", SC_SMALL)
        # Toast should be narrower on the smaller scene
        big_w = max(int(b["width"]) for b in bps_big if b.get("role") == "panel")
        small_w = max(int(b["width"]) for b in bps_small if b.get("role") == "panel")
        assert small_w <= big_w

    def test_modal_adapts_to_small_scene(self):
        bps_big = component_blueprints("modal", SC)
        bps_small = component_blueprints("modal", SC_SMALL)
        # Modal dialog panels (not the overlay) should scale
        big_w = max(int(b["width"]) for b in bps_big if b.get("role") != "overlay")
        small_w = max(int(b["width"]) for b in bps_small if b.get("role") != "overlay")
        assert small_w <= big_w

    def test_notification_adapts_to_small_scene(self):
        bps_big = component_blueprints("notification", SC)
        bps_small = component_blueprints("notification", SC_SMALL)
        big_w = max(int(b["width"]) for b in bps_big if b.get("role") == "panel")
        small_w = max(int(b["width"]) for b in bps_small if b.get("role") == "panel")
        assert small_w <= big_w

    def test_status_bar_stretches_to_scene_width(self):
        bps = component_blueprints("status_bar", SC)
        bar_panel = next(b for b in bps if b.get("role") == "bar")
        assert bar_panel["width"] >= 200  # at least most of 256 wide

    def test_none_scene_uses_defaults(self):
        """Passing sc=None shouldn't crash; uses safe fallback dimensions."""
        for name in ALL_NAMES:
            bps = component_blueprints(name, None)
            assert isinstance(bps, list)
            if bps:
                assert all("type" in b for b in bps)


class TestBlueprintRoles:
    """Components should have unique role names per blueprint."""

    def test_roles_are_unique(self):
        for name in ALL_NAMES:
            bps = component_blueprints(name, SC)
            roles = [bp.get("role") for bp in bps if bp.get("role")]
            # Some may share role prefix (like item0, item1), but exact duplicates are bad
            assert len(roles) == len(set(roles)), f"component '{name}' has duplicate roles: {roles}"

    def test_all_widgets_have_role(self):
        """Every widget in a component should have a role for identification."""
        for name in ALL_NAMES:
            for bp in component_blueprints(name, SC):
                assert "role" in bp, f"component '{name}' widget missing 'role'"


class TestToggleComponent:
    def test_toggle_returns_widgets(self):
        bps = component_blueprints("toggle", SC)
        assert len(bps) >= 1  # at least the toggle widget itself

    def test_toggle_type_is_toggle(self):
        bps = component_blueprints("toggle", SC)
        types = {bp["type"] for bp in bps}
        assert "toggle" in types
