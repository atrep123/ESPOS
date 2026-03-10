"""Push13: edge-case guards — OOB indices, property-raises, empty roles,
degenerate save_state, shrink-no-children, fill_parent non-panel, transforms OOB."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.inspector_logic import (
    inspector_commit_edit,
    inspector_field_to_str,
)
from cyberpunk_designer.selection_ops import selection_bounds, set_selection
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers (same pattern as push12)
# ---------------------------------------------------------------------------

GRID = 8


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _inspector_app(widgets=None, *, groups=None, comp_group=None, group_exact=None):
    """Lightweight SimpleNamespace app for inspector_logic tests."""
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in widgets or []:
        sc.widgets.append(w)
    if groups is not None:
        designer.groups = groups
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        hardware_profile="esp32os_256x128_gray4",
        snap_enabled=False,
        show_grid=False,
        panels_collapsed=False,
        live_preview_port=None,
        live_preview_baud=0,
        clipboard=[],
        layout=layout,
        _mark_dirty=MagicMock(),
        _set_status=MagicMock(),
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _set_selection=lambda indices, anchor_idx=None: set_selection(app, indices, anchor_idx),
        _selected_component_group=lambda: comp_group,
        _selected_group_exact=lambda: group_exact,
        _primary_group_for_index=lambda idx: None,
        _group_members=lambda name: [],
        _tri_state=lambda vals: "on" if all(vals) else ("off" if not any(vals) else "mixed"),
        _component_role_index=lambda members, root: {},
        _component_field_specs=lambda ctype: {},
        _inspector_cancel_edit=MagicMock(),
        _resize_selection_to=lambda w, h: True,
        _move_selection=lambda dx, dy: None,
        _is_valid_color_str=lambda s: True,
        _format_group_label=lambda gname, members: f"group: {gname} ({len(members)})",
        _component_info_from_group=lambda gname: None,
        _dirty_scenes=set(),
        _set_focus=MagicMock(),
        _sim_listmodels={},
        _next_group_name=lambda base: base + "1",
    )
    return app


def _make_comp_app(widgets, *, comp_type="card", root="myroot"):
    """Build app with component group for commit tests."""
    group_name = f"comp:{comp_type}:{root}:2"
    comp_group = (group_name, comp_type, root, list(range(len(widgets))))
    groups = {group_name: list(range(len(widgets)))}
    app = _inspector_app(widgets, groups=groups, comp_group=comp_group)

    def role_idx(members, rt):
        result = {}
        sc = app.state.current_scene()
        prefix = f"{rt}."
        for idx in members:
            if 0 <= idx < len(sc.widgets):
                wid = str(getattr(sc.widgets[idx], "_widget_id", "") or "")
                if wid == rt:
                    result[str(getattr(sc.widgets[idx], "type", "") or "")] = idx
                elif wid.startswith(prefix):
                    role = wid[len(prefix) :]
                    if role not in result:
                        result[role] = idx
        return result

    app._component_role_index = role_idx
    from cyberpunk_designer.component_fields import component_field_specs

    app._component_field_specs = component_field_specs
    set_selection(app, list(range(len(widgets))))
    return app


# ===========================================================================
# A) inspector_logic L109 — tabs_active field_to_str with NO tab roles
# ===========================================================================


class TestFieldToStrTabsActiveEmpty:
    """L109: field_to_str tabs_active returns '' when no tab roles found."""

    def test_empty_tabs(self):
        # Component with tabs type but no tab# role entries — only a tabbar
        w_tabbar = _w(type="panel", text="1")
        w_tabbar._widget_id = "mytabs.tabbar"

        app = _make_comp_app(
            [w_tabbar],
            comp_type="tabs",
            root="mytabs",
        )
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.active_tab", sc.widgets[0])
        # No tab roles → should return ""
        assert result == ""


# ===========================================================================
# B) inspector_logic L658 — menu_active with OOB item widget index
# ===========================================================================


class TestMenuActiveOOBItem:
    """L658: continue when item role maps to OOB widget index."""

    def test_oob_item(self):
        w_panel = _w(type="panel", text="0/1")
        w_panel._widget_id = "mymenu"
        w_scroll = _w(type="label", text="1/1")
        w_scroll._widget_id = "mymenu.scroll"

        app = _make_comp_app(
            [w_panel, w_scroll],
            comp_type="menu_list",
            root="mymenu",
        )
        # Override role_idx to return OOB index for item0
        original_role_idx = app._component_role_index

        def oob_role_idx(members, rt):
            result = original_role_idx(members, rt)
            # Add an item that points beyond scene widget list
            result["item0"] = 999
            return result

        app._component_role_index = oob_role_idx
        app.state.inspector_selected_field = "comp.active_item"
        app.state.inspector_input_buffer = "1"
        result = inspector_commit_edit(app)
        # Should succeed (OOB item is skipped via continue)
        assert result is True


# ===========================================================================
# C) inspector_logic L702 — tabs_active with OOB tab widget index
# ===========================================================================


class TestTabsActiveOOBTab:
    """L702: continue when tab role maps to OOB widget index."""

    def test_oob_tab(self):
        w_tabbar = _w(type="panel", text="1")
        w_tabbar._widget_id = "mytabs.tabbar"

        app = _make_comp_app(
            [w_tabbar],
            comp_type="tabs",
            root="mytabs",
        )
        original_role_idx = app._component_role_index

        def oob_role_idx(members, rt):
            result = original_role_idx(members, rt)
            result["tab1"] = 999
            result["tab2"] = 998
            return result

        app._component_role_index = oob_role_idx
        app.state.inspector_selected_field = "comp.active_tab"
        app.state.inspector_input_buffer = "1"
        result = inspector_commit_edit(app)
        assert result is True


# ===========================================================================
# D) inspector_logic L669-670 — scroll sync exception in menu_active
# ===========================================================================


class TestMenuActiveScrollSyncException:
    """L669-670: except block when scroll sync raises during menu_active."""

    def test_scroll_sync_raises(self):
        w_panel = _w(type="panel", text="")
        w_panel._widget_id = "mymenu"
        w_i0 = _w(type="label", text="Item0", style="highlight")
        w_i0._widget_id = "mymenu.item0"

        app = _make_comp_app(
            [w_panel, w_i0],
            comp_type="menu_list",
            root="mymenu",
        )
        original_role_idx = app._component_role_index

        def bad_scroll_role_idx(members, rt):
            result = original_role_idx(members, rt)
            # "scroll" maps to a value that can't be int()
            result["scroll"] = "bad"
            return result

        app._component_role_index = bad_scroll_role_idx
        app.state.inspector_selected_field = "comp.active_item"
        app.state.inspector_input_buffer = "1"
        result = inspector_commit_edit(app)
        # Should still succeed — exception is caught
        assert result is True


# ===========================================================================
# E) inspector_logic L602-603 — root rename groups getattr raises
# ===========================================================================


class TestRootRenameGroupsRaises:
    """L602-603: except when getattr(designer, 'groups') raises."""

    def test_groups_property_raises(self):
        w_panel = _w(type="panel", text="Panel")
        w_panel._widget_id = "mymenu"
        w_item = _w(type="label", text="Item")
        w_item._widget_id = "mymenu.item0"

        app = _make_comp_app(
            [w_panel, w_item],
            comp_type="menu",
            root="mymenu",
        )

        # Replace designer with one that raises on .groups access
        class DesignerWithBadGroups:
            """Proxy that raises RuntimeError on .groups access."""

            def __init__(self, real):
                object.__setattr__(self, "_real", real)

            @property
            def groups(self):
                raise RuntimeError("groups broken")

            def __getattr__(self, name):
                return getattr(object.__getattribute__(self, "_real"), name)

            def _save_state(self):
                pass

        app.designer = DesignerWithBadGroups(app.designer)
        # Re-wire state to use the new designer's scenes
        app.state._designer = app.designer

        app.state.inspector_selected_field = "comp.root"
        app.state.inspector_input_buffer = "newmenu"
        result = inspector_commit_edit(app)
        # Should succeed — groups exception is caught, rename still works
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[0]._widget_id == "newmenu"


# ===========================================================================
# F) inspector_logic L613-614 — root rename _sim_listmodels getattr raises
# ===========================================================================


class TestRootRenameModelsRaises:
    """L613-614: except when getattr(app, '_sim_listmodels') raises."""

    def test_models_property_raises(self):
        w_panel = _w(type="panel", text="Panel")
        w_panel._widget_id = "mymenu"
        w_item = _w(type="label", text="Item")
        w_item._widget_id = "mymenu.item0"

        app = _make_comp_app(
            [w_panel, w_item],
            comp_type="menu",
            root="mymenu",
        )

        # Make _sim_listmodels a property that raises on the app object.
        # SimpleNamespace doesn't support descriptors, so wrap in a class.
        class AppProxy:
            """Proxy that raises on _sim_listmodels access."""

            def __init__(self, real):
                object.__setattr__(self, "_real", real)

            @property
            def _sim_listmodels(self):
                raise RuntimeError("models broken")

            def __getattr__(self, name):
                return getattr(object.__getattribute__(self, "_real"), name)

            def __setattr__(self, name, value):
                if name == "_real":
                    object.__setattr__(self, name, value)
                else:
                    setattr(object.__getattribute__(self, "_real"), name, value)

        proxy = AppProxy(app)
        proxy.state.inspector_selected_field = "comp.root"
        proxy.state.inspector_input_buffer = "newmenu2"
        result = inspector_commit_edit(proxy)
        assert result is True


# ===========================================================================
# G) inspector_logic L736-737 — list_count models getattr raises
# ===========================================================================


class TestListCountModelsRaises:
    """L736-737: except when getattr(app, '_sim_listmodels') raises in list_count."""

    def test_models_raises(self):
        w_panel = _w(type="panel", text="0/3")
        w_panel._widget_id = "mymenu"
        w_scroll = _w(type="label", text="1/3")
        w_scroll._widget_id = "mymenu.scroll"
        w_i0 = _w(type="label", text="Item0", style="highlight")
        w_i0._widget_id = "mymenu.item0"

        app = _make_comp_app(
            [w_panel, w_scroll, w_i0],
            comp_type="menu_list",
            root="mymenu",
        )

        class AppProxy:
            def __init__(self, real):
                object.__setattr__(self, "_real", real)

            @property
            def _sim_listmodels(self):
                raise RuntimeError("models broken")

            def __getattr__(self, name):
                return getattr(object.__getattribute__(self, "_real"), name)

            def __setattr__(self, name, value):
                if name == "_real":
                    object.__setattr__(self, name, value)
                else:
                    setattr(object.__getattribute__(self, "_real"), name, value)

        proxy = AppProxy(app)
        proxy.state.inspector_selected_field = "comp.count"
        proxy.state.inspector_input_buffer = "2"
        result = inspector_commit_edit(proxy)
        assert result is True


# ===========================================================================
# H) transforms L20 — move_selection with OOB selected (bounds=None)
# ===========================================================================


class TestMoveSelectionBoundsNone:
    """L20: move_selection returns when bounds is None (OOB selected index)."""

    def test_oob_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.transforms import move_selection

        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        json_path = tmp_path / "scene.json"
        app = CyberpunkEditorApp(json_path, (256, 128))
        app.state.selected = [999]  # OOB index
        # Should not crash — returns silently because bounds is None
        move_selection(app, 10, 10)


# ===========================================================================
# I) transforms L220 — make_full_height with OOB selected (items empty)
# ===========================================================================


class TestMakeFullHeightOOB:
    """L220: make_full_height returns when items list is empty (OOB indices)."""

    def test_oob_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.transforms import make_full_height

        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        json_path = tmp_path / "scene.json"
        app = CyberpunkEditorApp(json_path, (256, 128))
        app.state.selected = [999]  # OOB
        make_full_height(app)
        # No crash, no status message about locked widgets


# ===========================================================================
# J) batch_ops L369-370 — remove_degenerate_widgets save_state raises
# ===========================================================================


class TestRemoveDegenerateSaveStateRaises:
    """L369-370: save_state raises during remove_degenerate_widgets."""

    def test_save_raises(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.batch_ops import remove_degenerate_widgets

        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        json_path = tmp_path / "scene.json"
        app = CyberpunkEditorApp(json_path, (256, 128))
        sc = app.state.current_scene()
        w = _w(width=10, height=10)
        w._width = 0  # Force degenerate (bypass setter)
        sc.widgets.append(w)
        # Make _save_state raise
        app.designer._save_state = MagicMock(side_effect=RuntimeError("no undo"))
        remove_degenerate_widgets(app)
        # Widget was removed despite save_state raising
        assert len(sc.widgets) == 0


# ===========================================================================
# K) batch_ops L1275 — fill_parent non-panel widget in scene
# ===========================================================================


class TestFillParentNonPanel:
    """L1275: fill_parent skips non-panel widgets when searching for enclosing
    panel (the inner `continue`)."""

    def test_non_panel_skipped(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.batch_ops import fill_parent

        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        json_path = tmp_path / "scene.json"
        app = CyberpunkEditorApp(json_path, (256, 128))
        if not hasattr(app, "_save_undo_state"):
            app._save_undo_state = lambda: None
        sc = app.state.current_scene()
        # Add a non-panel widget and a child inside it (geometrically)
        big_label = _w(type="label", x=0, y=0, width=100, height=100, text="big")
        child = _w(type="label", x=10, y=10, width=20, height=20, text="child")
        sc.widgets.append(big_label)
        sc.widgets.append(child)
        app.state.selected = [1]  # Select child
        fill_parent(app)
        # No enclosing panel found → child dimensions unchanged
        assert int(sc.widgets[1].width) == 20


# ===========================================================================
# L) selection_ops/layout L375 — shrink_to_content panel with no children
# ===========================================================================


class TestShrinkPanelNoChildren:
    """L375: shrink_to_content skips panel when no children_rects (continue)."""

    def test_no_children(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.layout import shrink_to_content

        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        json_path = tmp_path / "scene.json"
        app = CyberpunkEditorApp(json_path, (256, 128))
        if not hasattr(app, "_save_undo_state"):
            app._save_undo_state = lambda: None
        sc = app.state.current_scene()
        # Panel at (10,10) with no children inside
        panel = _w(type="panel", x=10, y=10, width=80, height=60, text="panel")
        # Label outside the panel bounds
        label = _w(type="label", x=200, y=200, width=30, height=10, text="far away")
        sc.widgets.append(panel)
        sc.widgets.append(label)
        # Include OOB index 999 to cover L375 (continue on OOB idx)
        app.state.selected = [999, 0]
        shrink_to_content(app)
        # Panel should be unchanged (no children to shrink to)
        assert int(sc.widgets[0].width) == 80
        assert int(sc.widgets[0].height) == 60
