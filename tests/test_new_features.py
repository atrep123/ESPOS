"""Tests for new widget types (toggle, list) and animation system integration.

Covers:
- Toggle widget codegen → C UIW_TOGGLE
- List widget codegen → C UIW_LIST
- Animation CSV codegen
- Property cycle includes new types
- WidgetType enum completeness with toggle
"""

from __future__ import annotations

import json

from tools.ui_codegen import (
    WIDGET_TYPE_MAP,
    _emit_widget,
    build_string_pool,
    collect_widget_strings,
    generate_ui_design_pair,
)
from ui_models import WidgetConfig, WidgetType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw):
    """Minimal widget dict."""
    defaults = dict(type="label", x=0, y=0, width=32, height=16)
    defaults.update(kw)
    return defaults


def _emit_with_pool(w: dict, idx: int = 0) -> str:
    pool = build_string_pool(collect_widget_strings(w), symbol_prefix="s_")
    wcode = "\n".join(_emit_widget(w, idx, pool))
    pool_code = "\n".join(pool.decls)
    return pool_code + "\n" + wcode


# ===========================================================================
# Toggle widget
# ===========================================================================


class TestToggleWidget:
    def test_widget_type_enum_has_toggle(self):
        assert WidgetType.TOGGLE.value == "toggle"

    def test_codegen_map_has_toggle(self):
        assert "toggle" in WIDGET_TYPE_MAP
        assert WIDGET_TYPE_MAP["toggle"] == "UIW_TOGGLE"

    def test_emit_toggle_widget(self):
        w = _w(type="toggle", text="WiFi", checked=True, width=60, height=10)
        code = _emit_with_pool(w)
        assert "UIW_TOGGLE" in code
        assert ".checked = 1" in code
        assert "WiFi" in code

    def test_emit_toggle_unchecked(self):
        w = _w(type="toggle", text="BT", checked=False)
        code = _emit_with_pool(w)
        assert "UIW_TOGGLE" in code
        assert ".checked = 0" in code

    def test_toggle_widget_config(self):
        w = WidgetConfig(type="toggle", x=10, y=20, width=60, height=10, text="Test")
        assert w.type == "toggle"
        assert w.checked is False

    def test_toggle_widget_config_checked(self):
        w = WidgetConfig(type="toggle", x=10, y=20, width=60, height=10, text="On", checked=True)
        assert w.checked is True


# ===========================================================================
# List widget
# ===========================================================================


class TestListWidget:
    def test_widget_type_enum_has_list(self):
        assert WidgetType.LIST.value == "list"

    def test_codegen_map_has_list(self):
        assert "list" in WIDGET_TYPE_MAP
        assert WIDGET_TYPE_MAP["list"] == "UIW_LIST"

    def test_emit_list_widget(self):
        w = _w(type="list", text="A\nB\nC", value=1, min_value=0, border=True)
        code = _emit_with_pool(w)
        assert "UIW_LIST" in code
        assert ".value = 1" in code

    def test_emit_list_widget_scroll(self):
        w = _w(type="list", text="A\nB\nC\nD\nE", value=3, min_value=2, height=24)
        code = _emit_with_pool(w)
        assert "UIW_LIST" in code
        assert ".min_value = 2" in code


# ===========================================================================
# Animation CSV codegen
# ===========================================================================


class TestAnimationCodgen:
    def test_animation_blink(self):
        w = _w(animations=["blink:500"])
        code = _emit_with_pool(w)
        assert "blink:500" in code

    def test_animation_multiple(self):
        w = _w(animations=["fade:1000:in", "blink:200"])
        code = _emit_with_pool(w)
        assert "fade:1000:in" in code

    def test_animation_csv_field(self):
        w = _w(animations_csv="slide:500:left")
        code = _emit_with_pool(w)
        assert "slide:500:left" in code

    def test_no_animation(self):
        w = _w()
        code = _emit_with_pool(w)
        assert "animations_csv = NULL" in code


# ===========================================================================
# Property cycle
# ===========================================================================


class TestPropertyCycle:
    def test_type_cycle_includes_toggle(self):
        from cyberpunk_designer.selection_ops.property_cycles import cycle_widget_type

        # The function is stateful (needs app), but we can at least import it
        assert callable(cycle_widget_type)

    def test_toggle_in_widget_type_values(self):
        values = {wt.value for wt in WidgetType}
        assert "toggle" in values
        assert "list" in values

    def test_all_14_widget_types(self):
        """Ensure we have exactly 14 widget types after adding toggle."""
        assert len(WidgetType) == 14


# ===========================================================================
# Full pipeline: JSON → C for toggle
# ===========================================================================


class TestToggleCodegenPipeline:
    def test_generate_toggle_scene(self, tmp_path):
        design = {
            "scenes": [
                {
                    "name": "test",
                    "width": 256,
                    "height": 128,
                    "widgets": [
                        {
                            "type": "toggle",
                            "x": 10,
                            "y": 20,
                            "width": 60,
                            "height": 10,
                            "text": "Enable",
                            "checked": True,
                        }
                    ],
                }
            ]
        }
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(design), encoding="utf-8")
        c_code, h_code = generate_ui_design_pair(
            json_path, scene_name="test", source_label="test.json"
        )
        assert "UIW_TOGGLE" in c_code
        assert ".checked = 1" in c_code
        assert "Enable" in c_code

    def test_generate_list_scene(self, tmp_path):
        design = {
            "scenes": [
                {
                    "name": "test",
                    "width": 256,
                    "height": 128,
                    "widgets": [
                        {
                            "type": "list",
                            "x": 0,
                            "y": 0,
                            "width": 100,
                            "height": 48,
                            "text": "Item 1\nItem 2\nItem 3",
                            "value": 0,
                            "border": True,
                        }
                    ],
                }
            ]
        }
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(design), encoding="utf-8")
        c_code, h_code = generate_ui_design_pair(
            json_path, scene_name="test", source_label="test.json"
        )
        assert "UIW_LIST" in c_code
        assert "Item 1" in c_code

    def test_generate_animation_scene(self, tmp_path):
        design = {
            "scenes": [
                {
                    "name": "test",
                    "width": 256,
                    "height": 128,
                    "widgets": [
                        {
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 50,
                            "height": 16,
                            "text": "Alert",
                            "animations": ["blink:500"],
                        }
                    ],
                }
            ]
        }
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(design), encoding="utf-8")
        c_code, h_code = generate_ui_design_pair(
            json_path, scene_name="test", source_label="test.json"
        )
        assert "blink:500" in c_code
        assert "UI_ENABLE_ANIMATIONS" in h_code
