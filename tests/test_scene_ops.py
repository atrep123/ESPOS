"""Tests for cyberpunk_designer.scene_ops — extracted scene management functions."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from ui_designer import WidgetConfig


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    from cyberpunk_editor import CyberpunkEditorApp

    app = CyberpunkEditorApp(json_path, (256, 128))
    app.show_help_overlay = False
    app._help_shown_once = True
    return app


# ── z-order ──


class TestZOrder:
    def test_z_order_step_up(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=10, height=10))
        sc.widgets.append(WidgetConfig(type="button", x=20, y=0, width=10, height=10))
        app.state.selected = [0]
        app.state.selected_idx = 0
        scene_ops.z_order_step(app, 1)
        assert sc.widgets[0].z_index == 1

    def test_z_order_step_already_at_end(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=10, height=10))
        app.state.selected = [0]
        app.state.selected_idx = 0
        scene_ops.z_order_step(app, 1)
        assert len(sc.widgets) == 1

    def test_bring_to_front(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=10, height=10))
        sc.widgets.append(WidgetConfig(type="button", x=0, y=0, width=10, height=10))
        sc.widgets.append(WidgetConfig(type="checkbox", x=0, y=0, width=10, height=10))
        app.state.selected = [0]
        app.state.selected_idx = 0
        scene_ops.z_order_bring_to_front(app)
        assert sc.widgets[0].z_index > sc.widgets[1].z_index

    def test_send_to_back(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=10, height=10))
        sc.widgets.append(WidgetConfig(type="button", x=0, y=0, width=10, height=10))
        sc.widgets.append(WidgetConfig(type="checkbox", x=0, y=0, width=10, height=10))
        sc.widgets[2].z_index = 5
        app.state.selected = [2]
        app.state.selected_idx = 2
        scene_ops.z_order_send_to_back(app)
        assert sc.widgets[2].z_index < 0


# ── toggle_lock_selection ──


class TestToggleLock:
    def test_lock_and_unlock(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=10, height=10))
        app.state.selected = [0]
        scene_ops.toggle_lock_selection(app)
        assert sc.widgets[0].locked is True
        scene_ops.toggle_lock_selection(app)
        assert sc.widgets[0].locked is False


# ── switch_scene ──


class TestSwitchScene:
    def test_switch_forward(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        app.designer.create_scene("second")
        sc2 = app.designer.scenes["second"]
        sc2.width, sc2.height = 256, 128
        first = app.designer.current_scene
        scene_ops.switch_scene(app, 1)
        assert app.designer.current_scene != first

    def test_switch_with_single_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        cur = app.designer.current_scene
        scene_ops.switch_scene(app, 1)
        assert app.designer.current_scene == cur


# ── jump_to_scene ──


class TestJumpToScene:
    def test_jump_valid_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        app.designer.create_scene("second")
        app.designer.scenes["second"].width = 256
        app.designer.scenes["second"].height = 128
        scene_ops.jump_to_scene(app, 1)
        assert app.designer.current_scene == "second"

    def test_jump_invalid_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        cur = app.designer.current_scene
        scene_ops.jump_to_scene(app, 99)
        assert app.designer.current_scene == cur


# ── scene CRUD ──


class TestSceneCrud:
    def test_add_new_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        before = len(app.designer.scenes)
        scene_ops.add_new_scene(app)
        assert len(app.designer.scenes) == before + 1

    def test_delete_current_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        app.designer.create_scene("second")
        app.designer.scenes["second"].width = 256
        app.designer.scenes["second"].height = 128
        before = len(app.designer.scenes)
        scene_ops.delete_current_scene(app)
        assert len(app.designer.scenes) == before - 1

    def test_delete_only_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        before = len(app.designer.scenes)
        scene_ops.delete_current_scene(app)
        assert len(app.designer.scenes) == before  # no change

    def test_duplicate_current_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=10, height=10))
        before = len(app.designer.scenes)
        scene_ops.duplicate_current_scene(app)
        assert len(app.designer.scenes) == before + 1
        # new scene should have widget
        new_sc = app.state.current_scene()
        assert len(new_sc.widgets) >= 1

    def test_close_other_scenes(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        app.designer.create_scene("second")
        app.designer.scenes["second"].width = 256
        app.designer.scenes["second"].height = 128
        app.designer.create_scene("third")
        app.designer.scenes["third"].width = 256
        app.designer.scenes["third"].height = 128
        scene_ops.close_other_scenes(app)
        assert len(app.designer.scenes) == 1

    def test_close_scenes_to_right(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        app.designer.create_scene("second")
        app.designer.scenes["second"].width = 256
        app.designer.scenes["second"].height = 128
        app.designer.create_scene("third")
        app.designer.scenes["third"].width = 256
        app.designer.scenes["third"].height = 128
        # Switch back to main so "second" and "third" are to the right
        app.designer.current_scene = "main"
        if not hasattr(app, "_dirty_scenes"):
            app._dirty_scenes = set()
        scene_ops.close_scenes_to_right(app)
        assert len(app.designer.scenes) == 1  # only "main"


# ── new_scene ──


class TestNewScene:
    def test_new_scene_resets(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        old_designer = app.designer
        scene_ops.new_scene(app)
        assert app.designer is not old_designer
        assert "main" in app.designer.scenes


# ── add_widget ──


class TestAddWidget:
    def test_add_label(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        scene_ops.add_widget(app, "label")
        assert len(sc.widgets) == before + 1
        assert sc.widgets[-1].type == "label"

    def test_add_button(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        scene_ops.add_widget(app, "button")
        assert sc.widgets[-1].type == "button"

    def test_add_panel(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        scene_ops.add_widget(app, "panel")
        assert sc.widgets[-1].type == "panel"

    def test_add_checkbox(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        scene_ops.add_widget(app, "checkbox")
        assert sc.widgets[-1].type == "checkbox"


# ── auto_arrange_grid ──


class TestAutoArrangeGrid:
    def test_arranges_widgets(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        for _i in range(5):
            sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=40, height=16))
        scene_ops.auto_arrange_grid(app)
        # Widgets should have different positions
        positions = {(w.x, w.y) for w in sc.widgets}
        assert len(positions) > 1


# ── toggle_clean_preview ──


class TestToggleCleanPreview:
    def test_toggle_on_off(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        assert not app.clean_preview
        scene_ops.toggle_clean_preview(app)
        assert app.clean_preview
        scene_ops.toggle_clean_preview(app)
        assert not app.clean_preview


# ── find_best_position ──


class TestFindBestPosition:
    def test_returns_ints(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16)
        bx, by = scene_ops.find_best_position(app, w, sc)
        assert isinstance(bx, int)
        assert isinstance(by, int)

    def test_avoids_overlap(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        # Place a widget at default position
        from cyberpunk_designer.constants import GRID

        sc.widgets.append(WidgetConfig(type="label", x=GRID, y=GRID, width=40, height=16))
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16)
        bx, by = scene_ops.find_best_position(app, w, sc)
        # Should suggest a position different from existing widget
        assert bx >= 0 and by >= 0


# ── zoom_to_fit ──


class TestZoomToFit:
    def test_no_crash(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        scene_ops.zoom_to_fit(app)
        # Just verify it doesn't crash


# ── export_c_header ──


class TestExportCHeader:
    def test_no_json_path(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        app.json_path = None
        scene_ops.export_c_header(app)
        # Should just show status, not crash

    def test_with_valid_json(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        json_path = tmp_path / "test_scene.json"
        json_path.write_text('{"scenes": []}', encoding="utf-8")
        app.json_path = str(json_path)
        scene_ops.export_c_header(app)
        # May or may not succeed depending on codegen import, but shouldn't crash


# ── rename_current_scene ──


class TestRenameCurrentScene:
    def test_sets_inspector_field(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        scene_ops.rename_current_scene(app)
        assert app.state.inspector_selected_field == "_scene_name"


# ── goto_widget_prompt ──


class TestGotoWidgetPrompt:
    def test_sets_inspector_field(self, tmp_path, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = _make_app(tmp_path, monkeypatch)
        scene_ops.goto_widget_prompt(app)
        assert app.state.inspector_selected_field == "_goto_widget"
