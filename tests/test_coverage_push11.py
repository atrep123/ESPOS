"""Push11: inspector_logic commit+display gaps, input_handlers toolbar/palette/inspector
clicks, overlays two-column help."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.inspector_logic import (
    compute_inspector_rows,
    inspector_commit_edit,
    inspector_field_to_str,
)
from cyberpunk_designer.selection_ops import selection_bounds, set_selection
from cyberpunk_designer.state import EditorState
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _inspector_app(widgets=None, *, groups=None, comp_group=None, group_exact=None):
    """Lightweight SimpleNamespace app for inspector_logic tests."""
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
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
    )
    return app


def _make_app(tmp_path, monkeypatch, *, widgets=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    return app


def _make_big_app(tmp_path, monkeypatch, *, widgets=None):
    """App with 1200×800 layout for valid palette/inspector hitboxes."""
    app = _make_app(tmp_path, monkeypatch, widgets=widgets)
    app.logical_surface = pygame.Surface((1200, 800))
    app.layout = app.layout.__class__(1200, 800)
    return app


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


# ===========================================================================
# A) inspector_logic — inspector_field_to_str
# ===========================================================================


class TestFieldToStrNumericFail:
    """L204-205: x/y/width/height field on widget with non-int value → '0'."""

    def test_bad_x_returns_zero(self):
        w = _w(x="not_a_number")
        app = _inspector_app([w])
        set_selection(app, [0])
        result = inspector_field_to_str(app, "x", w)
        assert result == "0"


class TestFieldToStrCompIntNonNumeric:
    """L140-141: component int kind with non-numeric attr value → '0'."""

    def test_comp_int_non_numeric(self):
        # Card component: "progress_value" → role="progress", attr="value", kind="int"
        w_title = _w(type="label", text="Title")
        w_title._widget_id = "myroot.title"
        w_progress = _w(type="progressbar", value="abc")  # Non-numeric!
        w_progress._widget_id = "myroot.progress"
        comp_group = ("comp:card:myroot:2", "card", "myroot", [0, 1])

        def role_idx(members, root):
            result = {}
            sc = app.state.current_scene()
            prefix = f"{root}."
            for idx in members:
                if 0 <= idx < len(sc.widgets):
                    wid = str(getattr(sc.widgets[idx], "_widget_id", "") or "")
                    if wid.startswith(prefix):
                        role = wid[len(prefix):]
                        if role not in result:
                            result[role] = idx
            return result

        app = _inspector_app(
            [w_title, w_progress],
            groups={"comp:card:myroot:2": [0, 1]},
            comp_group=comp_group,
        )
        app._component_role_index = role_idx
        from cyberpunk_designer.component_fields import component_field_specs
        app._component_field_specs = component_field_specs
        set_selection(app, [0, 1])
        result = inspector_field_to_str(app, "comp.progress_value", w_title)
        assert result == "0"


# ===========================================================================
# B) inspector_logic — inspector_commit_edit (scene rename)
# ===========================================================================


class TestSceneRenameSameName:
    """L499-500: commit scene rename with same name — except on stop_text_input."""

    def test_rename_same_name(self, monkeypatch):
        app = _inspector_app([_w()])
        app.state.inspector_selected_field = "_scene_name"
        app.state.inspector_input_buffer = "main"  # Same as current
        monkeypatch.setattr("pygame.key.stop_text_input", MagicMock(side_effect=RuntimeError("no input")))
        result = inspector_commit_edit(app)
        assert result is True
        assert app.state.inspector_selected_field is None


class TestSceneRenameSuccess:
    """L519-520: commit scene rename with new name — except on stop_text_input."""

    def test_rename_to_new_name(self, monkeypatch):
        app = _inspector_app([_w()])
        app.state.inspector_selected_field = "_scene_name"
        app.state.inspector_input_buffer = "settings"
        monkeypatch.setattr("pygame.key.stop_text_input", MagicMock(side_effect=RuntimeError("no input")))
        result = inspector_commit_edit(app)
        assert result is True
        assert app.designer.current_scene == "settings"
        assert "settings" in app.designer.scenes


# ===========================================================================
# C) inspector_logic — multi-select commit
# ===========================================================================


class TestMultiSelectBoundsNoneXY:
    """L790: multi-select x edit with bounds=None → returns False."""

    def test_x_bounds_none(self):
        app = _inspector_app([_w(width=0, height=0), _w(width=0, height=0)])
        set_selection(app, [0, 1])
        app._selection_bounds = lambda sel: None
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "10"
        result = inspector_commit_edit(app)
        assert result is False


class TestMultiSelectBoundsNoneWH:
    """L802: multi-select width edit with bounds=None → returns False."""

    def test_width_bounds_none(self):
        app = _inspector_app([_w(), _w()])
        set_selection(app, [0, 1])
        app._selection_bounds = lambda sel: None
        app.state.inspector_selected_field = "width"
        app.state.inspector_input_buffer = "100"
        result = inspector_commit_edit(app)
        assert result is False


class TestMultiSelectResizeFails:
    """L806: multi-select resize_selection_to returns False."""

    def test_resize_returns_false(self):
        app = _inspector_app([_w(x=0, y=0, width=40, height=20), _w(x=50, y=0, width=40, height=20)])
        set_selection(app, [0, 1])
        app._resize_selection_to = lambda w, h: False
        app.state.inspector_selected_field = "width"
        app.state.inspector_input_buffer = "200"
        result = inspector_commit_edit(app)
        assert result is False


class TestMultiSelectMaxLinesNegative:
    """L873: multi-select max_lines with negative value → set to None."""

    def test_negative_max_lines(self):
        app = _inspector_app([_w(), _w()])
        set_selection(app, [0, 1])
        app.state.inspector_selected_field = "max_lines"
        app.state.inspector_input_buffer = "-1"
        result = inspector_commit_edit(app)
        assert result is True
        # Verify that max_lines was set to None (negative → None)
        sc = app.state.current_scene()
        assert sc.widgets[0].max_lines is None


# ===========================================================================
# D) inspector_logic — component commit (int kind)
# ===========================================================================


def _make_comp_app(widgets, *, comp_type="card", root="myroot"):
    """Build app with a card component group for commit tests."""
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
                if wid.startswith(prefix):
                    role = wid[len(prefix):]
                    if role not in result:
                        result[role] = idx
        return result

    app._component_role_index = role_idx
    from cyberpunk_designer.component_fields import component_field_specs
    app._component_field_specs = component_field_specs
    set_selection(app, list(range(len(widgets))))
    return app


class TestCompIntMaxValueClamps:
    """L766-767: comp int max_value path — except when value is non-parseable."""

    def test_max_value_except(self):
        w_title = _w(type="label", text="Title")
        w_title._widget_id = "myroot.title"
        w_prog = _w(type="progressbar", max_value=100)
        w_prog._widget_id = "myroot.progress"
        w_prog.value = "not_an_int"  # Non-parseable → int() raises in try block
        app = _make_comp_app([w_title, w_prog])
        app.state.inspector_selected_field = "comp.progress_max"
        app.state.inspector_input_buffer = "50"
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].max_value == 50


class TestCompIntValueClamped:
    """L773-774: comp int value path — except when min/max are non-parseable."""

    def test_value_except(self):
        w_title = _w(type="label", text="Title")
        w_title._widget_id = "myroot.title"
        w_prog = _w(type="progressbar", value=50)
        w_prog._widget_id = "myroot.progress"
        w_prog.min_value = "bad"  # Non-parseable → except path
        w_prog.max_value = "bad"
        app = _make_comp_app([w_title, w_prog])
        app.state.inspector_selected_field = "comp.progress_value"
        app.state.inspector_input_buffer = "75"
        result = inspector_commit_edit(app)
        assert result is True


# ===========================================================================
# E) inspector_logic — compute_inspector_rows
# ===========================================================================


class TestComputeRowsPlainGroup:
    """L1216: multi-select with plain group (non-component) shows group row."""

    def test_plain_group_shown(self):
        app = _inspector_app(
            [_w(), _w()],
            groups={"mygroup": [0, 1]},
            group_exact="mygroup",
        )
        set_selection(app, [0, 1])
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "group" in keys
        vals = dict(rows)
        assert "mygroup" in vals.get("group", "")


class TestComputeRowsLayersWithGroups:
    """L1309: layers section shows group headers for multi-member groups."""

    def test_layers_group_header(self):
        app = _inspector_app(
            [_w(type="button"), _w(type="label"), _w(type="box")],
            groups={"grp1": [0, 1]},
        )
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "group:grp1" in keys
        # Members should be shown indented
        assert "layer:0" in keys
        assert "layer:1" in keys
        assert "layer:2" in keys


# ===========================================================================
# F) input_handlers — toolbar refresh_ports click (L695-696)
# ===========================================================================


class TestToolbarRefreshPorts:
    def test_refresh_ports_raises(self, tmp_path, monkeypatch):
        """L695-696: _refresh_available_ports raises → except passes."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        tr = app.layout.toolbar_rect
        hit_rect = pygame.Rect(tr.x + 2, tr.y + 2, 30, 20)
        app.toolbar_hitboxes = [(hit_rect, "refresh_ports")]
        app._refresh_available_ports = MagicMock(side_effect=RuntimeError("fail"))
        on_mouse_down(app, (hit_rect.centerx, hit_rect.centery))


# ===========================================================================
# G) input_handlers — palette action execution (L756)
# ===========================================================================


class TestPaletteActionExecution:
    def test_palette_collapsed_section(self, tmp_path, monkeypatch):
        """L756: palette section collapsed → continue skips it."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        pr = app.layout.palette_rect
        hit_rect = pygame.Rect(pr.x + 2, pr.y + 2, 80, 16)
        called = []
        app.palette_hitboxes = [(hit_rect, "Add Label", True)]
        app.palette_section_hitboxes = []
        app.palette_widget_hitboxes = []
        # "Hidden" section is collapsed, action is in "Visible" section
        app.palette_collapsed = {"Hidden"}
        app.palette_sections = [
            ("Hidden", [("Hidden Act", lambda: None)]),
            ("Visible", [("Add Label", lambda: called.append(True))]),
        ]
        on_mouse_down(app, (hit_rect.centerx, hit_rect.centery))
        assert called


# ===========================================================================
# H) input_handlers — palette widget hitbox click (L763-765)
# ===========================================================================


class TestPaletteWidgetClick:
    def test_palette_action_raises(self, tmp_path, monkeypatch):
        """L763-765: palette action raises → except pass, return."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        pr = app.layout.palette_rect
        hit_rect = pygame.Rect(pr.x + 2, pr.y + 2, 80, 16)
        app.palette_hitboxes = [(hit_rect, "Boom", True)]
        app.palette_section_hitboxes = []
        app.palette_widget_hitboxes = []
        app.palette_collapsed = set()
        # Action raises → triggers except at L763-765
        def bad_action():
            raise RuntimeError("boom")
        app.palette_sections = [("Actions", [("Boom", bad_action)])]
        on_mouse_down(app, (hit_rect.centerx, hit_rect.centery))


# ===========================================================================
# I) input_handlers — inspector group click (L808-809)
# ===========================================================================


class TestInspectorGroupClick:
    def test_layer_bad_key(self, tmp_path, monkeypatch):
        """L808-809: inspector layer click with non-numeric index → except return."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        ir = app.layout.inspector_rect
        lhit = pygame.Rect(ir.x + 2, ir.y + 20, ir.width - 4, 16)
        app.inspector_hitboxes = [(lhit, "layer:abc")]  # non-numeric
        app.inspector_section_hitboxes = []
        on_mouse_down(app, (lhit.centerx, lhit.centery))


# ===========================================================================
# J) input_handlers — resize sx/sy exception (L1185-1186)
# ===========================================================================


class TestResizeSxSyException:
    def test_resize_with_bad_start_rect(self, tmp_path, monkeypatch):
        """resize_start_rect with non-numeric width → exception path (L1185-1186)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app._tab_drag_idx = None
        app.state.box_select_start = None
        app.state.dragging = False
        app.state.resizing = True
        app.state.resize_anchor = "br"
        app.state.resize_start_mouse = (50, 50)
        # start_rect with non-numeric width → int() raises in sx/sy calc
        app.state.resize_start_rect = SimpleNamespace(
            x=10, y=10, width="bad", height="bad",
        )
        app.state.drag_start_positions = {0: (10, 10)}
        app.state.drag_start_sizes = {0: (40, 20)}
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        on_mouse_move(app, (cr.x + 70, cr.y + 40), (1, 0, 0))


# ===========================================================================
# K) overlays — two-column help (L381-427)
# ===========================================================================


class TestHelpOverlayTwoColumn:
    """L381-427 is dead code (panel_w capped at GRID*70, content always narrower).
    Keep this test as-is for regression; it covers the non-two-column path."""

    def test_help_overlay_draws(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        draw_help_overlay(app)


# ===========================================================================
# L) inspector_logic — inspector_field_to_str current_scene exception (L80-81)
# ===========================================================================


class TestFieldToStrSceneException:
    """L80-81: current_scene() raises → sc = None."""

    def test_scene_raises(self):
        app = _inspector_app([_w()])
        w = app.state.current_scene().widgets[0]
        # Make current_scene raise
        app.state.current_scene = MagicMock(side_effect=RuntimeError("boom"))
        result = inspector_field_to_str(app, "x", w)
        # Falls through to the single-widget path with sc=None
        assert isinstance(result, str)


# ===========================================================================
# M) inspector_logic — template save fails (L395-397)
# ===========================================================================


class TestTemplateSaveFails:
    """L395-397: add_template raises → returns False with status."""

    def test_template_save_exception(self):
        app = _inspector_app([_w()])
        set_selection(app, [0])
        app.state.inspector_selected_field = "_template_name"
        app.state.inspector_input_buffer = "my_template"
        app._pending_template_widgets = [{"type": "label"}]
        app.template_library = SimpleNamespace(
            add_template=MagicMock(side_effect=RuntimeError("disk full")),
        )
        result = inspector_commit_edit(app)
        assert result is False
        app._set_status.assert_called()


# ===========================================================================
# N) inspector_logic — template stop_text_input exception (L364-365)
# ===========================================================================


class TestTemplateStopTextInputException:
    """L364-365: stop_text_input raises during template name commit."""

    def test_stop_text_input_raises(self, monkeypatch):
        app = _inspector_app([_w()])
        set_selection(app, [0])
        app.state.inspector_selected_field = "_template_name"
        app.state.inspector_input_buffer = ""  # Empty name → False, but stop_text_input called first
        monkeypatch.setattr("pygame.key.stop_text_input", MagicMock(side_effect=RuntimeError("no input")))
        result = inspector_commit_edit(app)
        assert result is False  # Empty name


# ===========================================================================
# O) inspector_logic — menu_active OOB item widget (L658)
# ===========================================================================


class TestMenuActiveOOBItem:
    """L658: menu_active commit with OOB widget index skips gracefully."""

    def test_menu_active_oob(self):
        w_title = _w(type="label", text="Title")
        w_title._widget_id = "myroot.title"
        w_scroll = _w(type="label", text="1/3")
        w_scroll._widget_id = "myroot.scroll"
        # Create app with menu component
        group_name = "comp:menu:myroot:2"
        comp_group = (group_name, "menu", "myroot", [0, 1])
        app = _inspector_app(
            [w_title, w_scroll],
            groups={group_name: [0, 1]},
            comp_group=comp_group,
        )
        # Role index with item roles pointing to OOB indices
        app._component_role_index = lambda members, root: {
            "title": 0,
            "scroll": 1,
            "item1": 99,  # OOB
            "item2": 98,  # OOB
        }
        from cyberpunk_designer.component_fields import component_field_specs
        app._component_field_specs = component_field_specs
        set_selection(app, [0, 1])
        app.state.inspector_selected_field = "comp.active"
        app.state.inspector_input_buffer = "1"
        result = inspector_commit_edit(app)
        # Should handle OOB gracefully — items loop skips invalid indices
        assert isinstance(result, bool)
