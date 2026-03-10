"""Tests for cyberpunk_designer/component_fields.py — component_field_specs
mapping for all known component types."""

from __future__ import annotations

import pytest

from cyberpunk_designer.component_fields import component_field_specs

# All component types that return non-empty specs
_KNOWN_COMPONENTS = [
    "card",
    "toast",
    "modal",
    "notification",
    "dialog_confirm",
    "chart_bar",
    "chart_line",
    "gauge_hud",
    "dashboard_256x128",
    "status_bar",
    "tabs",
    "list",
    "menu_list",
    "menu",
    "list_item",
    "dialog",
]


class TestComponentFieldSpecs:
    @pytest.mark.parametrize("comp", _KNOWN_COMPONENTS)
    def test_returns_dict(self, comp):
        specs = component_field_specs(comp)
        assert isinstance(specs, dict)
        assert len(specs) > 0

    @pytest.mark.parametrize("comp", _KNOWN_COMPONENTS)
    def test_field_spec_structure(self, comp):
        specs = component_field_specs(comp)
        for key, val in specs.items():
            assert isinstance(key, str), f"Key must be str: {key!r}"
            assert isinstance(val, tuple) and len(val) == 3, f"Value must be 3-tuple: {val!r}"
            role, attr, kind = val
            assert isinstance(role, str)
            assert isinstance(attr, str)
            assert isinstance(kind, str)

    def test_unknown_returns_empty(self):
        assert component_field_specs("nonexistent_widget") == {}

    def test_none_returns_empty(self):
        assert component_field_specs(None) == {}

    def test_empty_string_returns_empty(self):
        assert component_field_specs("") == {}

    def test_case_insensitive(self):
        assert component_field_specs("CARD") == component_field_specs("card")

    def test_card_keys(self):
        specs = component_field_specs("card")
        assert "title" in specs
        assert "value" in specs
        assert "progress_value" in specs

    def test_modal_keys(self):
        specs = component_field_specs("modal")
        assert "title" in specs
        assert "message" in specs
        assert "ok" in specs
        assert "cancel" in specs

    def test_list_has_items(self):
        specs = component_field_specs("list")
        assert "title" in specs
        assert "scroll" in specs
        # Has item0..item5 keys
        for i in range(6):
            assert f"item{i}" in specs
            assert f"value{i}" in specs

    def test_chart_bar_has_points(self):
        specs = component_field_specs("chart_bar")
        assert "points" in specs
        assert specs["points"][2] == "int_list"

    def test_chart_bar_and_line_same_structure(self):
        bar = component_field_specs("chart_bar")
        line = component_field_specs("chart_line")
        assert set(bar.keys()) == set(line.keys())

    def test_menu_alias(self):
        # "menu" should work (maps to menu_list internally or its own branch)
        specs = component_field_specs("menu")
        assert isinstance(specs, dict)

    def test_tabs_has_active(self):
        specs = component_field_specs("tabs")
        assert "active_tab" in specs

    def test_dashboard_has_metrics(self):
        specs = component_field_specs("dashboard_256x128")
        assert "metric0_title" in specs
        assert "metric0_value" in specs
        assert "main_text" in specs

    def test_gauge_hud_fields(self):
        specs = component_field_specs("gauge_hud")
        assert "gauge_value" in specs
        assert specs["gauge_value"][2] == "int"

    def test_kinds_are_valid(self):
        valid_prefixes = {
            "str",
            "int",
            "int_list",
            "choice:",
            "tabs_active",
            "list_count",
            "menu_active",
        }
        for comp in _KNOWN_COMPONENTS:
            specs = component_field_specs(comp)
            for key, (_, _, kind) in specs.items():
                matched = any(kind == p or kind.startswith(p) for p in valid_prefixes)
                assert matched, f"{comp}.{key}: unknown kind {kind!r}"
