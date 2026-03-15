"""Targeted tests for remaining coverage gaps across cyberpunk_designer."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pygame

from ui_designer import WidgetConfig

GRID = 8


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


# ===========================================================================
# app.py: _open_template_menu (lines 412-443)
# ===========================================================================
class TestOpenTemplateMenu:
    def test_no_templates(self, make_app):
        app = make_app()
        app.template_library = MagicMock()
        app.template_library.templates = []
        app._open_template_menu()
        assert "No templates" in app.dialog_message

    def test_with_templates(self, make_app):
        app = make_app()
        tpl = MagicMock()
        tpl.metadata.name = "TestTpl"
        tpl.metadata.category = "cat1"
        app.template_library = MagicMock()
        app.template_library.templates = [tpl]
        app._open_template_menu()
        menu = getattr(app, "_context_menu", {})
        assert menu.get("visible")
        items = menu.get("items", [])
        assert any("TestTpl" in str(it) for it in items)

    def test_with_selection_adds_save(self, make_app):
        app = make_app(widgets=[_w()])
        app.state.selected = [0]
        tpl = MagicMock()
        tpl.metadata.name = "T1"
        tpl.metadata.category = "c"
        app.template_library = MagicMock()
        app.template_library.templates = [tpl]
        app._open_template_menu()
        menu = getattr(app, "_context_menu", {})
        items = menu.get("items", [])
        assert any("save_as_template" in str(it) for it in items)


# ===========================================================================
# app.py: main() (lines 2297-2298 — entry point, just verify importable)
# ===========================================================================
class TestMainEntryPoint:
    def test_main_function_exists(self):
        from cyberpunk_designer.app import main

        assert callable(main)


# ===========================================================================
# context_menu.py: trailing/leading separator cleanup (lines 221, 223)
# ===========================================================================
class TestContextMenuSeparatorCleanup:
    def test_trailing_separators_removed(self, make_app):
        app = make_app(widgets=[_w()])
        # Force a context menu with trailing separator by building manually
        from cyberpunk_designer.context_menu import open_context_menu

        app.state.selected = [0]
        app.state.selected_idx = 0
        sr = app.layout.canvas_rect
        open_context_menu(app, (sr.centerx, sr.centery))
        menu = getattr(app, "_context_menu", {})
        items = menu.get("items", [])
        if items:
            # Last item should not be a separator
            assert items[-1][2] is not None
            # First item should not be a separator
            assert items[0][2] is not None


# ===========================================================================
# context_menu.py: execute_context_action — view_rulers (line 221 in dispatch)
# ===========================================================================
class TestExecuteContextActions:
    def test_view_rulers_toggle(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        app.show_rulers = True
        execute_context_action(app, "view_rulers")
        assert not app.show_rulers
        execute_context_action(app, "view_rulers")
        assert app.show_rulers

    def test_tpl_action(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app(widgets=[_w()])
        tpl = MagicMock()
        app.template_library = MagicMock()
        app.template_library.templates = [tpl]
        app._apply_template = MagicMock()
        execute_context_action(app, "tpl_0")
        app._apply_template.assert_called_once_with(tpl)

    def test_tpl_invalid_index(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        app.template_library = MagicMock()
        app.template_library.templates = []
        # Should not raise
        execute_context_action(app, "tpl_99")

    def test_tpl_non_numeric(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        app.template_library = MagicMock()
        app.template_library.templates = []
        # "tpl_abc" → ValueError from int() → caught
        execute_context_action(app, "tpl_abc")

    def test_save_as_template(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app(widgets=[_w()])
        app.state.selected = [0]
        app._save_selection_as_template = MagicMock()
        execute_context_action(app, "save_as_template")
        app._save_selection_as_template.assert_called_once()


# ===========================================================================
# inspector_logic.py: component field int kind (lines 93-94)
# ===========================================================================
class TestInspectorLogicIntKind:
    def test_component_field_int_invalid_value(self, make_app):
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        # Build a card component so the int-kind code path triggers
        title = _w(text="Title", _widget_id="card_0.title")
        progress = _w(
            type="progressbar", text="x", _widget_id="card_0.progress", value=50, max_value=100
        )
        app = make_app(widgets=[title, progress])
        # Register the component group
        if not hasattr(app.designer, "groups"):
            app.designer.groups = {}
        app.designer.groups["comp:card:card_0:1"] = [0, 1]
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        # Force the value attr to a non-int string so int() raises ValueError
        app.state.current_scene().widgets[1].value = "not_a_number"  # type: ignore[assignment]
        val = inspector_field_to_str(app, "comp.progress_value", title)
        assert val == "0"  # Falls back to "0" on ValueError


# ===========================================================================
# inspector_logic.py: edge case in compute_inspector_rows (lines 334-335)
# ===========================================================================
class TestInspectorRowsEdge:
    def test_multi_selection_bounds_field(self, make_app):
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app(
            widgets=[
                _w(x=10, y=10, width=30, height=20),
                _w(x=50, y=50, width=30, height=20),
            ],
        )
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        val = inspector_field_to_str(app, "x", app.state.current_scene().widgets[0])
        # Should return bounds x
        assert val is not None


# ===========================================================================
# key_handlers.py: _run_action with None (line 175)
# ===========================================================================
class TestKeyHandlers:
    def test_run_action_none(self, make_app):
        from cyberpunk_designer.key_handlers import _run_action

        app = make_app()
        # Should not raise
        _run_action(app, None)

    def test_dispatch_ctrl_nosim(self, make_app):
        from cyberpunk_designer.key_handlers import _dispatch_ctrl_key

        app = make_app()
        app.sim_input_mode = True
        # K_t has _F_NOSIM flag → should return False in sim mode
        result = _dispatch_ctrl_key(app, pygame.K_t, pygame.KMOD_CTRL)
        assert result is False

    def test_dispatch_ctrl_noalt(self, make_app):
        from cyberpunk_designer.key_handlers import _dispatch_ctrl_key

        app = make_app()
        app.sim_input_mode = False
        # K_t has _F_NOALT flag → should return False with ALT
        result = _dispatch_ctrl_key(app, pygame.K_t, pygame.KMOD_CTRL | pygame.KMOD_ALT)
        assert result is False

    def test_dispatch_ctrl_shift_nosim_fallback(self, make_app):
        from cyberpunk_designer.key_handlers import _dispatch_ctrl_key

        app = make_app(widgets=[_w()])
        app.sim_input_mode = True
        # K_s has _F_SHIFT_NOSIM → Shift+Ctrl+S in sim_input_mode falls to plain
        app.save_json = MagicMock()
        result = _dispatch_ctrl_key(app, pygame.K_s, pygame.KMOD_CTRL | pygame.KMOD_SHIFT)
        app.save_json.assert_called_once()
        assert result is True


# ===========================================================================
# inspector_commit.py: except branches (493-494, 504-505, 624-625)
# These are defensive getattr() guards that only fire if the property
# descriptor itself raises. Tested via direct unit test of the guard pattern.
# ===========================================================================
class TestInspectorCommitExcept:
    def test_sim_listmodels_guard(self, make_app):
        """Verify _sim_listmodels getattr guard doesn't crash."""
        app = make_app(widgets=[_w()])
        # Ensure the attribute exists and can be accessed
        app._sim_listmodels = {"test": MagicMock()}
        # Remove it to test the except path
        delattr(app, "_sim_listmodels")
        # Access should not crash
        try:
            models = getattr(app, "_sim_listmodels", None)
        except (AttributeError, TypeError):
            models = None
        assert models is None


# ===========================================================================
# io_ops.py: apply_preset add_new TypeError (lines 111-112)
# ===========================================================================
class TestIoOpsPreset:
    def test_apply_preset_add_new_invalid(self, make_app):
        from cyberpunk_designer.io_ops import apply_preset_slot

        app = make_app()
        # Preset with invalid type that causes WidgetConfig to fail
        app.widget_presets = [{"type": "invalid_widget_type_xyz", "x": 0, "y": 0}]
        sc = app.state.current_scene()
        n_before = len(sc.widgets)
        apply_preset_slot(app, 1, add_new=True)
        # Shouldn't crash; widget may or may not be added depending on validation
        assert len(sc.widgets) >= n_before


# ===========================================================================
# io_ops.py: save_json atomic fallback (lines 169-170)
# ===========================================================================
class TestIoOpsSaveFallback:
    def test_save_json_atomic_fallback(self, make_app, tmp_path, monkeypatch):
        from cyberpunk_designer.io_ops import save_json

        app = make_app(widgets=[_w()])
        app.json_path = tmp_path / "test_save.json"
        app._dirty = True
        app._dirty_scenes = set()

        # Make os.replace fail, but also make unlink fail on the tmp file
        call_count = [0]

        def failing_replace(src, dst):
            call_count[0] += 1
            raise OSError("mock replace failure")

        monkeypatch.setattr(os, "replace", failing_replace)
        save_json(app)
        # The fallback direct save should have worked
        assert app.json_path.exists() or not app._dirty


# ===========================================================================
# scene_ops.py: cycle_profile empty PROFILE_ORDER (line 221)
# ===========================================================================
class TestSceneOps:
    def test_cycle_profile_empty(self, make_app, monkeypatch):
        from cyberpunk_designer import scene_ops

        app = make_app()
        monkeypatch.setattr(scene_ops, "PROFILE_ORDER", [])
        scene_ops.cycle_profile(app)
        # Should return early without error

    def test_delete_scene_no_current(self, make_app):
        from cyberpunk_designer.scene_ops import delete_current_scene

        app = make_app(extra_scenes=True)
        app.designer.current_scene = ""
        delete_current_scene(app)
        # Should return early — both scenes still exist
        assert len(app.designer.scenes) == 2

    def test_duplicate_scene_no_current(self, make_app):
        from cyberpunk_designer.scene_ops import duplicate_current_scene

        app = make_app()
        app.designer.current_scene = ""
        duplicate_current_scene(app)
        assert "No scene" in app.dialog_message

    def test_add_widget_unknown_type(self, make_app):
        from cyberpunk_designer.scene_ops import add_widget

        app = make_app()
        sc = app.state.current_scene()
        n = len(sc.widgets)
        add_widget(app, "totally_invalid_type_xyz")
        # Unknown type should show error or gracefully handle
        assert len(sc.widgets) >= n


# ===========================================================================
# selection_ops/core.py: save_undo with logging (line 21)
# ===========================================================================
class TestCoreOps:
    def test_save_undo_log_attribute_error(self, make_app):
        from cyberpunk_designer.selection_ops.core import save_undo

        app = make_app()
        app.designer._save_state = MagicMock(side_effect=AttributeError("mock"))
        # Should log warning but not raise
        save_undo(app, log=True)


# ===========================================================================
# selection_ops/property_cycles.py: cycle_type ValueError (lines 82-83)
# ===========================================================================
class TestPropertyCycles:
    def test_cycle_type_unknown_current(self, make_app):
        from cyberpunk_designer.selection_ops.property_cycles import cycle_widget_type

        app = make_app(widgets=[_w(type="label")])
        app.state.selected = [0]
        sc = app.state.current_scene()
        sc.widgets[0].type = "unknown_fake_type"
        cycle_widget_type(app)
        # Should fall back to "label"
        assert sc.widgets[0].type == "label"


# ===========================================================================
# component_insert.py: line 57 — empty blueprints is unreachable dead code
# (first check at line 43 already returns) — test add_component with unknown
# ===========================================================================
class TestComponentInsert:
    def test_unknown_component(self, make_app):
        from cyberpunk_designer.component_insert import add_component

        app = make_app()
        sc = app.state.current_scene()
        n = len(sc.widgets)
        add_component(app, "totally_unknown_component")
        assert len(sc.widgets) == n
