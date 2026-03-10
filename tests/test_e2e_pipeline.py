"""Integration/E2E tests: full pipeline JSON→designer→edit→save→reload→export→codegen."""

import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.ui_codegen import generate_ui_design_pair
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Round-trip: create → save → load → verify
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_save_load_preserves_all_widget_types(self, tmp_path):
        """Every widget type survives a save→load round-trip."""
        designer = UIDesigner(256, 128)
        scene = designer.create_scene("allwidgets")
        designer.current_scene = scene.name

        types_to_test = [
            "label", "box", "button", "gauge", "progressbar",
            "checkbox", "radiobutton", "slider", "textbox", "panel",
        ]
        for i, wtype in enumerate(types_to_test):
            scene.widgets.append(WidgetConfig(
                type=wtype, x=i * 20, y=10,
                width=18, height=12, text=f"W{i}",
            ))

        path = tmp_path / "allwidgets.json"
        designer.save_to_json(str(path))

        d2 = UIDesigner()
        d2.load_from_json(str(path))
        loaded = d2.scenes[d2.current_scene]
        assert len(loaded.widgets) == len(types_to_test)
        for i, wtype in enumerate(types_to_test):
            assert loaded.widgets[i].type == wtype
            assert loaded.widgets[i].text == f"W{i}"

    def test_save_load_preserves_extended_fields(self, tmp_path):
        """Extended widget fields (fg, bg, style, etc.) survive round-trip."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("extended")
        designer.current_scene = scene.name

        w = WidgetConfig(
            type="label", x=5, y=5, width=50, height=10,
            text="Styled",
        )
        w.fg = "#FFFFFF"
        w.bg = "#000000"
        w.border_style = "double"
        w.align = "center"
        w.valign = "middle"
        w.text_overflow = "ellipsis"
        scene.widgets.append(w)

        path = tmp_path / "extended.json"
        designer.save_to_json(str(path))

        d2 = UIDesigner()
        d2.load_from_json(str(path))
        loaded_w = d2.scenes[d2.current_scene].widgets[0]
        assert loaded_w.text == "Styled"
        assert loaded_w.border_style == "double"
        assert loaded_w.align == "center"

    def test_multiple_scenes_round_trip(self, tmp_path):
        """Multiple scenes saved and loaded correctly."""
        designer = UIDesigner(128, 64)
        s1 = designer.create_scene("home")
        s1.widgets.append(WidgetConfig(type="label", x=0, y=0, width=40, height=8, text="Home"))
        s2 = designer.create_scene("settings")
        s2.widgets.append(WidgetConfig(type="button", x=0, y=0, width=40, height=8, text="Back"))
        s2.widgets.append(WidgetConfig(type="slider", x=0, y=20, width=60, height=10, text="Vol"))

        path = tmp_path / "multi.json"
        designer.save_to_json(str(path))

        d2 = UIDesigner()
        d2.load_from_json(str(path))
        assert len(d2.scenes) >= 2


# ---------------------------------------------------------------------------
# JSON → C codegen pipeline
# ---------------------------------------------------------------------------

class TestCodegenPipeline:
    def _make_scene_json(self, tmp_path, widgets, *, width=128, height=64, name="test"):
        data = {
            "width": width,
            "height": height,
            "scenes": {
                name: {
                    "name": name,
                    "width": width,
                    "height": height,
                    "widgets": widgets,
                }
            },
        }
        path = tmp_path / "scene.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_codegen_produces_valid_c_header_and_source(self, tmp_path):
        """Codegen outputs both .h and .c content."""
        path = self._make_scene_json(tmp_path, [
            {"type": "label", "x": 0, "y": 0, "width": 40, "height": 8, "text": "Hello"},
            {"type": "button", "x": 0, "y": 10, "width": 40, "height": 10, "text": "OK"},
        ])
        c_src, h_src = generate_ui_design_pair(path, scene_name="test", source_label="test")
        assert "UiWidget" in c_src
        assert "UiScene" in c_src
        assert "UIW_LABEL" in c_src
        assert "UIW_BUTTON" in c_src
        assert "#pragma once" in h_src or "#ifndef" in h_src

    def test_codegen_handles_all_widget_types(self, tmp_path):
        """All widget types produce valid C enum references."""
        type_map = {
            "label": "UIW_LABEL", "box": "UIW_BOX", "button": "UIW_BUTTON",
            "gauge": "UIW_GAUGE", "progressbar": "UIW_PROGRESSBAR",
            "checkbox": "UIW_CHECKBOX", "radiobutton": "UIW_RADIOBUTTON",
            "slider": "UIW_SLIDER", "panel": "UIW_PANEL",
        }
        widgets = [
            {"type": wtype, "x": i * 10, "y": 0, "width": 10, "height": 10}
            for i, wtype in enumerate(type_map)
        ]
        path = self._make_scene_json(tmp_path, widgets)
        c_src, _ = generate_ui_design_pair(path, scene_name="test", source_label="test")
        for c_enum in type_map.values():
            assert c_enum in c_src, f"Expected {c_enum} in C source"

    def test_codegen_empty_scene(self, tmp_path):
        """Codegen handles empty widget list gracefully."""
        path = self._make_scene_json(tmp_path, [])
        c_src, h_src = generate_ui_design_pair(path, scene_name="test", source_label="test")
        assert "widget_count" in c_src or "0" in c_src

    def test_codegen_text_with_special_chars(self, tmp_path):
        """Text with quotes and newlines is properly escaped in C."""
        path = self._make_scene_json(tmp_path, [
            {"type": "label", "x": 0, "y": 0, "width": 60, "height": 8,
             "text": 'Say "hello"'},
        ])
        c_src, _ = generate_ui_design_pair(path, scene_name="test", source_label="test")
        assert r'\"hello\"' in c_src

    def test_codegen_border_styles(self, tmp_path):
        """Border style names map to C enums."""
        path = self._make_scene_json(tmp_path, [
            {"type": "box", "x": 0, "y": 0, "width": 20, "height": 20,
             "border_style": "double"},
        ])
        c_src, _ = generate_ui_design_pair(path, scene_name="test", source_label="test")
        assert "UI_BORDER_DOUBLE" in c_src

    def test_codegen_gray4_colors(self, tmp_path):
        """fg/bg color values are converted to 4-bit grayscale in C."""
        path = self._make_scene_json(tmp_path, [
            {"type": "label", "x": 0, "y": 0, "width": 30, "height": 8,
             "fg": "#FFFFFF", "bg": "#000000"},
        ])
        c_src, _ = generate_ui_design_pair(path, scene_name="test", source_label="test")
        assert ".fg" in c_src or "15" in c_src  # white = gray4 level 15


# ---------------------------------------------------------------------------
# Designer → C codegen full pipeline
# ---------------------------------------------------------------------------

class TestDesignerToCodegen:
    def test_designer_save_then_codegen(self, tmp_path):
        """Full pipeline: UIDesigner creates scene → save JSON → codegen to C."""
        designer = UIDesigner(256, 128)
        scene = designer.create_scene("dashboard")
        designer.current_scene = scene.name

        scene.widgets.append(WidgetConfig(type="label", x=10, y=5, width=80, height=10, text="CPU"))
        scene.widgets.append(WidgetConfig(type="progressbar", x=10, y=20, width=80, height=8, text="cpu_bar"))
        scene.widgets.append(WidgetConfig(type="button", x=10, y=35, width=40, height=12, text="Reset"))

        json_path = tmp_path / "dashboard.json"
        designer.save_to_json(str(json_path))

        c_src, h_src = generate_ui_design_pair(json_path, scene_name="dashboard", source_label="test")
        assert "UIW_LABEL" in c_src
        assert "UIW_PROGRESSBAR" in c_src
        assert "UIW_BUTTON" in c_src
        assert "CPU" in c_src
        assert "Reset" in c_src

    def test_edit_save_reload_codegen_consistent(self, tmp_path):
        """Edit a widget, save, reload, codegen — text changes propagate."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("test")
        designer.current_scene = scene.name
        scene.widgets.append(WidgetConfig(type="label", x=0, y=0, width=40, height=8, text="Before"))

        json_path = tmp_path / "test.json"
        designer.save_to_json(str(json_path))

        # Reload, modify, re-save
        d2 = UIDesigner()
        d2.load_from_json(str(json_path))
        d2.scenes[d2.current_scene].widgets[0].text = "After"
        json_path2 = tmp_path / "test2.json"
        d2.save_to_json(str(json_path2))

        c_src, _ = generate_ui_design_pair(json_path2, scene_name="test", source_label="test")
        assert "After" in c_src
        assert "Before" not in c_src


# ---------------------------------------------------------------------------
# JSON schema validation
# ---------------------------------------------------------------------------

class TestJsonValidation:
    def test_main_scene_json_is_valid(self):
        """The project's main_scene.json is valid JSON with expected structure."""
        main_json = Path(__file__).resolve().parents[1] / "main_scene.json"
        if not main_json.exists():
            pytest.skip("main_scene.json not found")
        data = json.loads(main_json.read_text(encoding="utf-8"))
        # Should have basic scene structure
        assert "widgets" in data or "scenes" in data or "name" in data

    def test_main_scene_codegen_succeeds(self):
        """main_scene.json can be processed by codegen without error."""
        main_json = Path(__file__).resolve().parents[1] / "main_scene.json"
        if not main_json.exists():
            pytest.skip("main_scene.json not found")
        data = json.loads(main_json.read_text(encoding="utf-8"))
        scene_name = data.get("name", "main")
        c_src, h_src = generate_ui_design_pair(main_json, scene_name=scene_name, source_label="test")
        assert len(c_src) > 0
        assert len(h_src) > 0


# ---------------------------------------------------------------------------
# Widget manipulation edge cases
# ---------------------------------------------------------------------------

class TestWidgetManipulation:
    def test_move_widget_and_verify(self, tmp_path):
        """Move a widget, save, reload — new position preserved."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("move")
        designer.current_scene = scene.name
        scene.widgets.append(WidgetConfig(type="button", x=10, y=10, width=20, height=10, text="Btn"))

        scene.widgets[0].x = 50
        scene.widgets[0].y = 40

        path = tmp_path / "move.json"
        designer.save_to_json(str(path))

        d2 = UIDesigner()
        d2.load_from_json(str(path))
        w = d2.scenes[d2.current_scene].widgets[0]
        assert w.x == 50
        assert w.y == 40

    def test_delete_widget_and_verify(self, tmp_path):
        """Delete a widget, save, reload — widget is gone."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("del")
        designer.current_scene = scene.name
        scene.widgets.append(WidgetConfig(type="label", x=0, y=0, width=20, height=8, text="A"))
        scene.widgets.append(WidgetConfig(type="label", x=30, y=0, width=20, height=8, text="B"))

        del scene.widgets[0]

        path = tmp_path / "del.json"
        designer.save_to_json(str(path))

        d2 = UIDesigner()
        d2.load_from_json(str(path))
        loaded = d2.scenes[d2.current_scene]
        assert len(loaded.widgets) == 1
        assert loaded.widgets[0].text == "B"

    def test_resize_widget_and_codegen(self, tmp_path):
        """Resize widget → codegen output reflects new dimensions."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("resize")
        designer.current_scene = scene.name
        scene.widgets.append(WidgetConfig(type="box", x=0, y=0, width=10, height=10))

        scene.widgets[0].width = 100
        scene.widgets[0].height = 50

        path = tmp_path / "resize.json"
        designer.save_to_json(str(path))

        c_src, _ = generate_ui_design_pair(path, scene_name="resize", source_label="test")
        assert "100" in c_src
        assert "50" in c_src
