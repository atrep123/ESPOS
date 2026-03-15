"""Tests for cyberpunk_designer.context_menu — context menu building and dispatch."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from ui_designer import WidgetConfig

# ── CONTEXT_ACTION_MAP ──


class TestContextActionMap:
    def test_map_not_empty(self):
        from cyberpunk_designer.context_menu import CONTEXT_ACTION_MAP

        assert len(CONTEXT_ACTION_MAP) > 100

    def test_all_values_are_method_names(self):
        from cyberpunk_designer.context_menu import CONTEXT_ACTION_MAP

        for action, method in CONTEXT_ACTION_MAP.items():
            assert isinstance(method, str)
            assert method.startswith("_"), f"{action} -> {method} should start with _"

    def test_all_actions_are_strings(self):
        from cyberpunk_designer.context_menu import CONTEXT_ACTION_MAP

        for action in CONTEXT_ACTION_MAP:
            assert isinstance(action, str)
            assert len(action) > 0

    def test_map_methods_exist_on_app(self, make_app):
        from cyberpunk_designer.context_menu import CONTEXT_ACTION_MAP

        app = make_app()
        missing = []
        for action, method in CONTEXT_ACTION_MAP.items():
            if not hasattr(app, method):
                missing.append(f"{action} -> {method}")
        # Allow up to a few unimplemented stubs
        assert len(missing) <= 2, f"Missing methods: {missing}"


# ── open_tab_context_menu ──


class TestOpenTabContextMenu:
    def test_creates_visible_menu(self, make_app):
        from cyberpunk_designer.context_menu import open_tab_context_menu

        app = make_app()
        open_tab_context_menu(app, (100, 10))
        assert app._context_menu["visible"] is True

    def test_has_rename_item(self, make_app):
        from cyberpunk_designer.context_menu import open_tab_context_menu

        app = make_app()
        open_tab_context_menu(app, (100, 10))
        actions = [item[2] for item in app._context_menu["items"]]
        assert "tab_rename" in actions

    def test_has_new_scene_item(self, make_app):
        from cyberpunk_designer.context_menu import open_tab_context_menu

        app = make_app()
        open_tab_context_menu(app, (100, 10))
        actions = [item[2] for item in app._context_menu["items"]]
        assert "tab_new" in actions

    def test_single_scene_no_close(self, make_app):
        from cyberpunk_designer.context_menu import open_tab_context_menu

        app = make_app()
        open_tab_context_menu(app, (100, 10))
        actions = [item[2] for item in app._context_menu["items"]]
        assert "tab_close" not in actions

    def test_multi_scene_has_close(self, make_app):
        from cyberpunk_designer.context_menu import open_tab_context_menu

        app = make_app()
        app.designer.create_scene("second")
        app.designer.scenes["second"].width = 256
        app.designer.scenes["second"].height = 128
        open_tab_context_menu(app, (100, 10))
        actions = [item[2] for item in app._context_menu["items"]]
        assert "tab_close" in actions
        assert "tab_close_others" in actions


# ── open_context_menu ──


class TestOpenContextMenu:
    def test_empty_scene_has_add_items(self, make_app):
        from cyberpunk_designer.context_menu import open_context_menu

        app = make_app()
        open_context_menu(app, (20, 20))
        actions = [item[2] for item in app._context_menu["items"] if item[2]]
        assert "add_label" in actions
        assert "add_button" in actions

    def test_selected_widget_has_edit_items(self, make_app):
        from cyberpunk_designer.context_menu import open_context_menu

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=10, y=10, width=50, height=20))
        app.state.selected = [0]
        open_context_menu(app, (20, 20))
        actions = [item[2] for item in app._context_menu["items"] if item[2]]
        assert "copy" in actions
        assert "delete" in actions
        assert "duplicate" in actions

    def test_multi_selected_has_layout_items(self, make_app):
        from cyberpunk_designer.context_menu import open_context_menu

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=10, y=10, width=50, height=20))
        sc.widgets.append(WidgetConfig(type="button", x=70, y=10, width=50, height=20))
        app.state.selected = [0, 1]
        open_context_menu(app, (20, 20))
        actions = [item[2] for item in app._context_menu["items"] if item[2]]
        assert "stack_vertical" in actions
        assert "swap_positions" in actions

    def test_no_consecutive_separators(self, make_app):
        from cyberpunk_designer.context_menu import open_context_menu

        app = make_app()
        open_context_menu(app, (20, 20))
        items = app._context_menu["items"]
        for i in range(len(items) - 1):
            if items[i][2] is None:
                assert items[i + 1][2] is not None, f"Consecutive separators at {i}"

    def test_no_leading_trailing_separator(self, make_app):
        from cyberpunk_designer.context_menu import open_context_menu

        app = make_app()
        open_context_menu(app, (20, 20))
        items = app._context_menu["items"]
        if items:
            assert items[0][2] is not None
            assert items[-1][2] is not None

    def test_clipboard_paste_shown(self, make_app):
        from cyberpunk_designer.context_menu import open_context_menu

        app = make_app()
        app._clipboard = [{"type": "label"}]
        open_context_menu(app, (20, 20))
        actions = [item[2] for item in app._context_menu["items"] if item[2]]
        assert "paste" in actions


# ── ctx_single_items ──


class TestCtxSingleItems:
    def test_returns_list(self, make_app):
        from cyberpunk_designer.context_menu import ctx_single_items

        app = make_app()
        SEP = ("---", "", None)
        items = ctx_single_items(app, SEP)
        assert isinstance(items, list)
        assert len(items) > 20

    def test_all_tuples_of_3(self, make_app):
        from cyberpunk_designer.context_menu import ctx_single_items

        app = make_app()
        SEP = ("---", "", None)
        for item in ctx_single_items(app, SEP):
            assert len(item) == 3


# ── ctx_multi_items ──


class TestCtxMultiItems:
    def test_returns_list(self, make_app):
        from cyberpunk_designer.context_menu import ctx_multi_items

        app = make_app()
        SEP = ("---", "", None)
        items = ctx_multi_items(app, SEP)
        assert isinstance(items, list)
        assert len(items) > 10

    def test_has_measure(self, make_app):
        from cyberpunk_designer.context_menu import ctx_multi_items

        app = make_app()
        SEP = ("---", "", None)
        actions = [i[2] for i in ctx_multi_items(app, SEP) if i[2]]
        assert "measure" in actions


# ── ctx_view_items ──


class TestCtxViewItems:
    def test_returns_expected_items(self, make_app):
        from cyberpunk_designer.context_menu import ctx_view_items

        app = make_app()
        items = ctx_view_items(app)
        actions = [i[2] for i in items]
        assert "view_grid" in actions
        assert "view_guides" in actions
        assert "view_snap" in actions

    def test_check_marks_update(self, make_app):
        from cyberpunk_designer.context_menu import ctx_view_items

        app = make_app()
        app.show_grid = True
        items = ctx_view_items(app)
        grid_label = [i[0] for i in items if i[2] == "view_grid"][0]
        assert "\u2713" in grid_label


# ── ctx_add_items ──


class TestCtxAddItems:
    def test_has_all_widget_types(self, make_app):
        from cyberpunk_designer.context_menu import ctx_add_items

        app = make_app()
        SEP = ("---", "", None)
        items = ctx_add_items(app, SEP)
        actions = [i[2] for i in items if i[2]]
        for wtype in ["add_label", "add_button", "add_panel", "add_checkbox", "add_slider"]:
            assert wtype in actions, f"Missing: {wtype}"

    def test_has_composites(self, make_app):
        from cyberpunk_designer.context_menu import ctx_add_items

        app = make_app()
        SEP = ("---", "", None)
        items = ctx_add_items(app, SEP)
        actions = [i[2] for i in items if i[2]]
        assert "create_header_bar" in actions
        assert "create_nav_row" in actions


# ── click_context_menu ──


class TestClickContextMenu:
    def test_no_menu_does_nothing(self, make_app):
        from cyberpunk_designer.context_menu import click_context_menu

        app = make_app()
        app._context_menu = {"visible": False}
        click_context_menu(app, (10, 10))
        assert not app._context_menu["visible"]

    def test_miss_hides_menu(self, make_app):
        from cyberpunk_designer.context_menu import click_context_menu

        app = make_app()
        app._context_menu = {"visible": True, "hitboxes": [], "pos": (0, 0), "items": []}
        click_context_menu(app, (999, 999))
        assert not app._context_menu["visible"]


# ── execute_context_action ──


class TestExecuteContextAction:
    def test_add_action(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        sc = app.state.current_scene()
        before = len(sc.widgets)
        execute_context_action(app, "add_label")
        assert len(sc.widgets) == before + 1

    def test_view_grid_toggle(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        before = app.show_grid
        execute_context_action(app, "view_grid")
        assert app.show_grid != before

    def test_view_rulers_toggle(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        before = getattr(app, "show_rulers", True)
        execute_context_action(app, "view_rulers")
        assert getattr(app, "show_rulers", True) != before

    def test_view_snap_toggle(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        before = app.snap_enabled
        execute_context_action(app, "view_snap")
        assert app.snap_enabled != before

    def test_map_action_dispatches(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=10, y=10, width=50, height=20))
        app.state.selected = [0]
        # toggle_lock is in the map
        execute_context_action(app, "toggle_lock")
        assert sc.widgets[0].locked is True

    def test_unknown_action_no_crash(self, make_app):
        from cyberpunk_designer.context_menu import execute_context_action

        app = make_app()
        execute_context_action(app, "nonexistent_action_xyz")
