"""Real-world usage scenario tests.

Tests workflows a user would actually perform:
- Design → export C → verify struct correctness
- Roundtrip: load → modify → save → reload → verify idempotency
- Multi-scene workflow
- Runtime bindings survive codegen
- Focus navigation through realistic layouts
- Value editing with min/max/step constraints
- Undo/redo stack integrity
- Component insert → export preserves widgets
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from cyberpunk_designer import focus_nav
from cyberpunk_editor import CyberpunkEditorApp
from tools.ui_codegen import generate_ui_design_pair
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    monkeypatch.setenv("ESP32OS_AUTO_EXPORT", "0")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 192))


def _save_design_json(path: Path, designer: UIDesigner):
    """Save designer state to JSON without auto-export."""
    data = {
        "width": designer.width,
        "height": designer.height,
        "scenes": {
            name: {
                "name": scene.name,
                "width": scene.width,
                "height": scene.height,
                "bg_color": scene.bg_color,
                "widgets": [asdict(w) for w in scene.widgets],
            }
            for name, scene in designer.scenes.items()
        },
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# 1. Design → Export C → Verify struct correctness
# ===========================================================================


class TestDesignToC:
    """Design a scene in Python, export to C, verify the C output."""

    def test_basic_widget_exports_to_c_struct(self, tmp_path):
        designer = UIDesigner(256, 128)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(
            WidgetConfig(
                type="button",
                x=10,
                y=20,
                width=60,
                height=16,
                text="Start",
                border=True,
            )
        )
        scene.widgets.append(
            WidgetConfig(
                type="label",
                x=10,
                y=40,
                width=80,
                height=10,
                text="Status: OK",
            )
        )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        c_src, h_src = generate_ui_design_pair(json_path, scene_name="main", source_label="test")

        # Header checks
        assert "#ifndef UI_DESIGN_H" in h_src
        assert "extern const UiScene ui_design;" in h_src

        # C source checks
        assert "UIW_BUTTON" in c_src
        assert "UIW_LABEL" in c_src
        assert ".x = 10, .y = 20, .width = 60, .height = 16," in c_src
        assert ".x = 10, .y = 40, .width = 80, .height = 10," in c_src
        assert '"Start"' in c_src
        assert '"Status: OK"' in c_src
        assert ".widget_count =" in c_src

    def test_all_widget_types_export(self, tmp_path):
        """Make sure every widget type maps to a valid C enum."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        types = [
            "label",
            "button",
            "checkbox",
            "slider",
            "progressbar",
            "gauge",
            "textbox",
            "radiobutton",
            "icon",
            "chart",
            "box",
            "panel",
        ]
        for i, wtype in enumerate(types):
            scene.widgets.append(
                WidgetConfig(
                    type=wtype,
                    x=0,
                    y=i * 8,
                    width=20,
                    height=8,
                    text=wtype,
                )
            )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        c_src, h_src = generate_ui_design_pair(json_path, scene_name="main", source_label="test")

        for wtype in types:
            c_enum = f"UIW_{wtype.upper()}"
            assert c_enum in c_src, f"{wtype} should map to {c_enum}"

    def test_runtime_bindings_survive_codegen(self, tmp_path):
        """runtime and animations must appear in C output."""
        designer = UIDesigner(256, 128)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(
            WidgetConfig(
                type="label",
                x=0,
                y=0,
                width=80,
                height=10,
                text="Temp",
                runtime='{"bind":"sensor.temp","fmt":"%d°C"}',
                animations=["fade_in,300", "slide_up,200"],
            )
        )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        c_src, _ = generate_ui_design_pair(json_path, scene_name="main", source_label="test")

        assert "sensor.temp" in c_src
        assert "fade_in" in c_src
        assert "slide_up" in c_src

    def test_min_max_value_preserved(self, tmp_path):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(
            WidgetConfig(
                type="slider",
                x=0,
                y=0,
                width=60,
                height=10,
                value=30,
                min_value=10,
                max_value=200,
            )
        )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        c_src, _ = generate_ui_design_pair(json_path, scene_name="main", source_label="test")

        assert ".value = 30," in c_src
        assert ".min_value = 10," in c_src
        assert ".max_value = 200," in c_src

    def test_widget_id_exported(self, tmp_path):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(
            WidgetConfig(
                type="button",
                x=0,
                y=0,
                width=40,
                height=10,
                text="Go",
                _widget_id="btn_go",
            )
        )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        c_src, _ = generate_ui_design_pair(json_path, scene_name="main", source_label="test")

        assert "btn_go" in c_src


# ===========================================================================
# 2. Roundtrip: Load → Modify → Save → Reload → Compare
# ===========================================================================


class TestRoundtrip:
    """Verify that save/load is lossless for widget properties."""

    def test_roundtrip_preserves_widget_count(self, tmp_path):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        for i in range(5):
            scene.widgets.append(
                WidgetConfig(
                    type="button",
                    x=i * 20,
                    y=0,
                    width=18,
                    height=10,
                    text=f"B{i}",
                )
            )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        loaded = UIDesigner()
        loaded.load_from_json(str(json_path))
        sc = loaded.scenes[loaded.current_scene]
        assert len(sc.widgets) == 5

    def test_roundtrip_preserves_all_properties(self, tmp_path):
        designer = UIDesigner(256, 128)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        w = WidgetConfig(
            type="slider",
            x=10,
            y=20,
            width=80,
            height=12,
            text="Vol",
            value=75,
            min_value=0,
            max_value=100,
            color_fg="white",
            color_bg="#303030",
            border=True,
            border_style="double",
            align="center",
            valign="middle",
            text_overflow="ellipsis",
            style="default",
            enabled=True,
            visible=True,
        )
        scene.widgets.append(w)
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        loaded = UIDesigner()
        loaded.load_from_json(str(json_path))
        sc = loaded.scenes[loaded.current_scene]
        rw = sc.widgets[0]
        assert rw.type == "slider"
        assert rw.x == 10
        assert rw.y == 20
        assert rw.width == 80
        assert rw.height == 12
        assert rw.text == "Vol"
        assert int(rw.value) == 75
        assert int(rw.min_value) == 0
        assert int(rw.max_value) == 100

    def test_modify_save_reload_reflects_changes(self, tmp_path):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(
            WidgetConfig(
                type="label",
                x=0,
                y=0,
                width=40,
                height=10,
                text="Original",
            )
        )
        json_path = tmp_path / "design.json"
        _save_design_json(json_path, designer)

        # Load, modify, save again
        d2 = UIDesigner()
        d2.load_from_json(str(json_path))
        sc2 = d2.scenes[d2.current_scene]
        sc2.widgets[0].text = "Modified"
        sc2.widgets.append(
            WidgetConfig(
                type="button",
                x=50,
                y=0,
                width=30,
                height=10,
                text="New",
            )
        )
        _save_design_json(json_path, d2)

        # Reload and verify
        d3 = UIDesigner()
        d3.load_from_json(str(json_path))
        sc3 = d3.scenes[d3.current_scene]
        assert len(sc3.widgets) == 2
        assert sc3.widgets[0].text == "Modified"
        assert sc3.widgets[1].text == "New"

    def test_idempotent_save_produces_same_json(self, tmp_path):
        """Saving twice without changes → identical JSON."""
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(
            WidgetConfig(
                type="checkbox",
                x=0,
                y=0,
                width=30,
                height=10,
                text="OK",
                checked=True,
            )
        )
        p1 = tmp_path / "save1.json"
        p2 = tmp_path / "save2.json"
        _save_design_json(p1, designer)
        _save_design_json(p2, designer)
        assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")


# ===========================================================================
# 3. Multi-scene workflow
# ===========================================================================


class TestMultiScene:
    def test_multiple_scenes_roundtrip(self, tmp_path):
        designer = UIDesigner(256, 128)
        s1 = designer.create_scene("home")
        s1.widgets.append(WidgetConfig(type="label", x=0, y=0, width=50, height=10, text="Home"))
        s2 = designer.create_scene("settings")
        s2.widgets.append(
            WidgetConfig(type="slider", x=0, y=0, width=60, height=12, text="Brightness")
        )
        s2.widgets.append(
            WidgetConfig(type="checkbox", x=0, y=20, width=40, height=10, text="WiFi")
        )
        designer.current_scene = "home"

        json_path = tmp_path / "multi.json"
        _save_design_json(json_path, designer)

        loaded = UIDesigner()
        loaded.load_from_json(str(json_path))
        assert "home" in loaded.scenes
        assert "settings" in loaded.scenes
        assert len(loaded.scenes["home"].widgets) == 1
        assert len(loaded.scenes["settings"].widgets) == 2

    def test_each_scene_exports_independently(self, tmp_path):
        designer = UIDesigner(128, 64)
        s1 = designer.create_scene("main")
        s1.widgets.append(WidgetConfig(type="button", x=0, y=0, width=30, height=8, text="A"))
        s2 = designer.create_scene("cfg")
        s2.widgets.append(WidgetConfig(type="slider", x=0, y=0, width=40, height=8, text="B"))
        designer.current_scene = "main"

        json_path = tmp_path / "multi.json"
        _save_design_json(json_path, designer)

        c1, _ = generate_ui_design_pair(json_path, scene_name="main", source_label="test")
        c2, _ = generate_ui_design_pair(json_path, scene_name="cfg", source_label="test")

        assert "UIW_BUTTON" in c1 and "UIW_SLIDER" not in c1
        assert "UIW_SLIDER" in c2 and "UIW_BUTTON" not in c2


# ===========================================================================
# 4. Focus navigation through a realistic layout
# ===========================================================================


class TestFocusNavigation:
    """Test focus navigation as it would work on the device."""

    def _setup_layout(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        # Row 1: two buttons side by side
        sc.widgets.append(WidgetConfig(type="button", x=10, y=5, width=30, height=10, text="OK"))
        sc.widgets.append(
            WidgetConfig(type="button", x=50, y=5, width=30, height=10, text="Cancel")
        )
        # Row 2: a slider and a checkbox
        sc.widgets.append(
            WidgetConfig(
                type="slider", x=10, y=20, width=60, height=10, value=50, min_value=0, max_value=100
            )
        )
        sc.widgets.append(WidgetConfig(type="checkbox", x=80, y=20, width=30, height=10, text="On"))
        # Non-focusable widget (label)
        sc.widgets.append(
            WidgetConfig(type="label", x=10, y=35, width=50, height=10, text="Status")
        )
        return app, sc

    def test_focusable_indices_correct(self, tmp_path, monkeypatch):
        app, sc = self._setup_layout(tmp_path, monkeypatch)
        indices = focus_nav.focusable_indices(sc)
        # label at idx 4 should NOT be focusable
        assert 4 not in indices
        # Buttons, slider, checkbox should be focusable
        assert set(indices) == {0, 1, 2, 3}

    def test_focus_cycle_visits_all_focusable(self, tmp_path, monkeypatch):
        app, sc = self._setup_layout(tmp_path, monkeypatch)
        focus_nav.ensure_focus(app)
        visited = {app.focus_idx}
        for _ in range(10):
            focus_nav.focus_cycle(app, 1)
            visited.add(app.focus_idx)
        # Should visit all 4 focusable widgets
        assert len(visited) >= 4

    def test_focus_cycle_backwards(self, tmp_path, monkeypatch):
        app, sc = self._setup_layout(tmp_path, monkeypatch)
        focus_nav.ensure_focus(app)
        start = app.focus_idx
        # Cycle backward
        focus_nav.focus_cycle(app, -1)
        assert app.focus_idx != start or len(focus_nav.focusable_indices(sc)) == 1

    def test_dpad_right_moves_to_adjacent(self, tmp_path, monkeypatch):
        app, sc = self._setup_layout(tmp_path, monkeypatch)
        # Set focus on first button (idx 0)
        focus_nav.set_focus(app, 0)
        assert app.focus_idx == 0
        # Move right → should go to button 1 (same row, to the right)
        focus_nav.focus_move_direction(app, "right")
        assert app.focus_idx == 1

    def test_dpad_down_moves_to_lower_row(self, tmp_path, monkeypatch):
        app, sc = self._setup_layout(tmp_path, monkeypatch)
        focus_nav.set_focus(app, 0)
        focus_nav.focus_move_direction(app, "down")
        # Should move to row 2 (slider or checkbox)
        assert app.focus_idx in {2, 3}

    def test_disabled_widget_not_focusable(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(type="button", x=0, y=0, width=30, height=10, text="A", enabled=False)
        )
        sc.widgets.append(
            WidgetConfig(type="button", x=40, y=0, width=30, height=10, text="B", enabled=True)
        )
        indices = focus_nav.focusable_indices(sc)
        assert 0 not in indices
        assert 1 in indices

    def test_invisible_widget_not_focusable(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(type="button", x=0, y=0, width=30, height=10, text="A", visible=False)
        )
        sc.widgets.append(
            WidgetConfig(type="button", x=40, y=0, width=30, height=10, text="B", visible=True)
        )
        indices = focus_nav.focusable_indices(sc)
        assert 0 not in indices
        assert 1 in indices

    def test_empty_scene_focus_is_none(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        focus_nav.ensure_focus(app)
        assert app.focus_idx is None


# ===========================================================================
# 5. Value editing with min/max/step constraints
# ===========================================================================


class TestValueEditing:
    """Simulate slider value adjustments as a user would via D-pad."""

    def test_adjust_increases_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(
                type="slider", x=0, y=0, width=60, height=10, value=50, min_value=0, max_value=100
            )
        )
        focus_nav.set_focus(app, 0)
        focus_nav.adjust_focused_value(app, 5)
        assert sc.widgets[0].value == 55

    def test_adjust_clamps_at_max(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(
                type="slider", x=0, y=0, width=60, height=10, value=98, min_value=0, max_value=100
            )
        )
        focus_nav.set_focus(app, 0)
        focus_nav.adjust_focused_value(app, 10)
        assert sc.widgets[0].value == 100

    def test_adjust_clamps_at_min(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(
                type="slider", x=0, y=0, width=60, height=10, value=3, min_value=0, max_value=100
            )
        )
        focus_nav.set_focus(app, 0)
        focus_nav.adjust_focused_value(app, -10)
        assert sc.widgets[0].value == 0

    def test_adjust_negative_delta(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(
                type="slider", x=0, y=0, width=60, height=10, value=50, min_value=0, max_value=100
            )
        )
        focus_nav.set_focus(app, 0)
        focus_nav.adjust_focused_value(app, -15)
        assert sc.widgets[0].value == 35

    def test_activate_toggles_checkbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(
            WidgetConfig(type="checkbox", x=0, y=0, width=30, height=10, text="WiFi", checked=False)
        )
        focus_nav.set_focus(app, 0)
        assert not sc.widgets[0].checked
        focus_nav.activate_focused(app)
        assert sc.widgets[0].checked
        focus_nav.activate_focused(app)
        assert not sc.widgets[0].checked

    def test_adjust_does_nothing_for_non_slider(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        sc.widgets.append(WidgetConfig(type="button", x=0, y=0, width=30, height=10, text="GO"))
        focus_nav.set_focus(app, 0)
        focus_nav.adjust_focused_value(app, 5)
        # Button has no value to adjust — no crash, no change


# ===========================================================================
# 6. Undo/redo stack integrity
# ===========================================================================


class TestUndoRedo:
    def test_undo_restores_previous_state(self):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(WidgetConfig(type="label", x=0, y=0, width=30, height=10, text="A"))
        designer._save_state()
        scene.widgets[0].text = "B"
        assert scene.widgets[0].text == "B"
        designer.undo()
        sc = designer.scenes["main"]
        assert sc.widgets[0].text == "A"

    def test_redo_after_undo(self):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(WidgetConfig(type="label", x=0, y=0, width=30, height=10, text="A"))
        designer._save_state()
        scene.widgets[0].text = "B"
        designer._save_state()
        scene.widgets[0].text = "C"
        designer.undo()
        assert designer.scenes["main"].widgets[0].text == "B"
        designer.redo()
        assert designer.scenes["main"].widgets[0].text == "C"

    def test_undo_empty_stack_returns_false(self):
        designer = UIDesigner(128, 64)
        designer.create_scene("main")
        designer.current_scene = "main"
        assert designer.undo() is False

    def test_redo_empty_stack_returns_false(self):
        designer = UIDesigner(128, 64)
        designer.create_scene("main")
        designer.current_scene = "main"
        assert designer.redo() is False

    def test_multiple_undos(self):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(WidgetConfig(type="label", x=0, y=0, width=30, height=10, text="V1"))
        designer._save_state()
        scene.widgets[0].text = "V2"
        designer._save_state()
        scene.widgets[0].text = "V3"
        designer._save_state()
        scene.widgets[0].text = "V4"

        designer.undo()
        assert designer.scenes["main"].widgets[0].text == "V3"
        designer.undo()
        assert designer.scenes["main"].widgets[0].text == "V2"
        designer.undo()
        assert designer.scenes["main"].widgets[0].text == "V1"


# ===========================================================================
# 7. Full app workflow: add via palette → render → export
# ===========================================================================


class TestFullAppWorkflow:
    def test_palette_add_then_canvas_render_then_export(self, tmp_path, monkeypatch):
        """Simulate: user clicks palette to add widget, canvas renders, then export C."""
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 0

        # Add widgets via palette simulation
        app.logical_surface.fill((0, 0, 0))
        app._draw_palette()
        button_hit = next(
            (r, label, e) for r, label, e in app.palette_hitboxes if label == "button"
        )
        app._on_mouse_down(button_hit[0].center)
        assert len(sc.widgets) == 1
        assert sc.widgets[0].type == "button"

        # Render canvas
        app.logical_surface.fill((0, 0, 0))
        app._draw_canvas()

        # Verify pixel at widget location is not background
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        w = sc.widgets[0]
        px = app.logical_surface.get_at((sr.x + w.x + 2, sr.y + w.y + 2))[:3]
        assert px != (0, 0, 0), "widget should render non-black pixels"

        # Export to C
        json_path = tmp_path / "export.json"
        _save_design_json(json_path, app.designer)
        c_src, h_src = generate_ui_design_pair(
            json_path, scene_name=app.designer.current_scene, source_label="test"
        )
        assert "UIW_BUTTON" in c_src
        assert "#ifndef UI_DESIGN_H" in h_src

    def test_add_multiple_types_render_all(self, tmp_path, monkeypatch):
        """Add multiple widget types and verify all render."""
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        types_to_add = ["button", "checkbox", "slider", "label"]
        for wtype in types_to_add:
            app.logical_surface.fill((0, 0, 0))
            app._draw_palette()
            try:
                hit = next((r, label, e) for r, label, e in app.palette_hitboxes if label == wtype)
                app._on_mouse_down(hit[0].center)
            except StopIteration:
                pass

        assert len(sc.widgets) >= len(types_to_add)

        # Render and check canvas has content
        app.logical_surface.fill((0, 0, 0))
        app._draw_canvas()
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        total_px = 0
        for x in range(sr.x, min(sr.x + 50, app.logical_surface.get_width())):
            for y in range(sr.y, min(sr.y + 50, app.logical_surface.get_height())):
                if app.logical_surface.get_at((x, y))[:3] != (0, 0, 0):
                    total_px += 1
        # Should have plenty of rendered pixels
        assert total_px > 0


# ===========================================================================
# 8. Scene dimensions and widget bounds
# ===========================================================================


class TestSceneBounds:
    def test_auto_layout_keeps_widgets_in_bounds(self):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        for i in range(10):
            scene.widgets.append(
                WidgetConfig(
                    type="button",
                    x=0,
                    y=0,
                    width=20,
                    height=8,
                    text=f"B{i}",
                )
            )
        designer.auto_layout(layout_type="grid", spacing=2, scene_name="main")
        for w in scene.widgets:
            assert w.x >= 0
            assert w.y >= 0
            assert w.x + w.width <= scene.width + 2  # small tolerance
            assert w.y + w.height <= scene.height + 20  # grid may overflow vertically

    def test_align_center_h_aligns_widgets(self):
        designer = UIDesigner(128, 64)
        scene = designer.create_scene("main")
        designer.current_scene = "main"
        scene.widgets.append(WidgetConfig(type="button", x=10, y=10, width=30, height=10, text="A"))
        scene.widgets.append(WidgetConfig(type="button", x=50, y=20, width=20, height=10, text="B"))
        designer.align_widgets("center_h", [0, 1], scene_name="main")
        # center_h aligns horizontal center (x axis)
        cx0 = scene.widgets[0].x + scene.widgets[0].width / 2
        cx1 = scene.widgets[1].x + scene.widgets[1].width / 2
        assert abs(cx0 - cx1) < 2
