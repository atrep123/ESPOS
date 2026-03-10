"""Tests for keyboard dispatch in cyberpunk_designer/input_handlers.py.

Exercises the major branches of on_key_down to improve coverage from 36%.
Each test fires one key event and asserts the expected dispatch happened.
"""

from __future__ import annotations

import pygame

from cyberpunk_designer.input_handlers import (
    _cycle_widget_selection,
    on_key_down,
)
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    return app


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _w(app, idx):
    return app.state.current_scene().widgets[idx]


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


def _key_event(key, mod=0, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode=unicode)


CTRL = pygame.KMOD_CTRL
SHIFT = pygame.KMOD_SHIFT
ALT = pygame.KMOD_ALT


# ===========================================================================
# Help overlay / inspector editing
# ===========================================================================

class TestHelpOverlayKeys:
    def test_escape_dismisses_pinned_help(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_pinned = True
        on_key_down(app, _key_event(pygame.K_ESCAPE))
        assert app.show_help_overlay is False

    def test_any_key_dismisses_auto_help(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_pinned = False
        # Non-escape key auto-dismisses but also dispatches to action
        on_key_down(app, _key_event(pygame.K_a))
        assert app.show_help_overlay is False


class TestInspectorEditing:
    def test_enter_commits_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Hello")
        _sel(app, 0)
        app._inspector_start_edit("text")
        app.state.inspector_input_buffer = "World"
        on_key_down(app, _key_event(pygame.K_RETURN))
        assert app.state.inspector_selected_field is None

    def test_global_shortcut_ignored_during_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Hello")
        _sel(app, 0)
        app._inspector_start_edit("text")
        # pressing 's' should not trigger save — it's swallowed
        on_key_down(app, _key_event(pygame.K_s))
        # field still in edit
        assert app.state.inspector_selected_field == "text"


# ===========================================================================
# Ctrl+key shortcuts
# ===========================================================================

class TestCtrlShortcuts:
    def test_ctrl_s_saves(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app.save_json = lambda: called.append("save")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_s, mod=CTRL))
        assert "save" in called

    def test_ctrl_shift_s_sorts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._sort_widgets_by_position = lambda: called.append("sort")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_s, mod=CTRL | SHIFT))
        assert "sort" in called

    def test_ctrl_c_copies(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._copy_selection = lambda: called.append("copy")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_c, mod=CTRL))
        assert "copy" in called

    def test_ctrl_shift_c_copies_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._copy_style = lambda: called.append("copystyle")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_c, mod=CTRL | SHIFT))
        assert "copystyle" in called

    def test_ctrl_x_cuts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cut_selection = lambda: called.append("cut")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_x, mod=CTRL))
        assert "cut" in called

    def test_ctrl_shift_x_removes_degenerate(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._remove_degenerate_widgets = lambda: called.append("degen")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_x, mod=CTRL | SHIFT))
        assert "degen" in called

    def test_ctrl_v_pastes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._paste_clipboard = lambda: called.append("paste")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_v, mod=CTRL))
        assert "paste" in called

    def test_ctrl_shift_v_pastes_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._paste_style = lambda: called.append("pastestyle")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_v, mod=CTRL | SHIFT))
        assert "pastestyle" in called

    def test_ctrl_z_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_z, mod=CTRL))

    def test_ctrl_shift_z_redo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_z, mod=CTRL | SHIFT))

    def test_ctrl_y_redo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_y, mod=CTRL))

    def test_ctrl_shift_y_enable_all(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._enable_all_widgets = lambda: called.append("enable")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_y, mod=CTRL | SHIFT))
        assert "enable" in called

    def test_ctrl_d_duplicates(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._duplicate_selection = lambda: called.append("dup")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_d, mod=CTRL))
        assert "dup" in called

    def test_ctrl_shift_d_dup_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._duplicate_current_scene = lambda: called.append("dupscene")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_d, mod=CTRL | SHIFT))
        assert "dupscene" in called

    def test_ctrl_a_selects_all(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_all = lambda: called.append("all")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_a, mod=CTRL))
        assert "all" in called

    def test_ctrl_shift_a_selects_same_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_same_type = lambda: called.append("type")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_a, mod=CTRL | SHIFT))
        assert "type" in called

    def test_ctrl_f_fits_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._fit_selection_to_text = lambda: called.append("fitt")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_f, mod=CTRL))
        assert "fitt" in called

    def test_ctrl_shift_f_fits_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._fit_selection_to_widget = lambda: called.append("fitw")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_f, mod=CTRL | SHIFT))
        assert "fitw" in called

    def test_ctrl_l_loads(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app.load_json = lambda: called.append("load")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_l, mod=CTRL))
        assert "load" in called

    def test_ctrl_shift_l_unlocks_all(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._unlock_all_widgets = lambda: called.append("unlock")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_l, mod=CTRL | SHIFT))
        assert "unlock" in called

    def test_ctrl_n_adds_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._add_new_scene = lambda: called.append("newscene")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_n, mod=CTRL))
        assert "newscene" in called

    def test_ctrl_shift_n_compacts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._compact_widgets = lambda: called.append("compact")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_n, mod=CTRL | SHIFT))
        assert "compact" in called

    def test_ctrl_r_renames_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._rename_current_scene = lambda: called.append("rename")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_r, mod=CTRL))
        assert "rename" in called

    def test_ctrl_shift_r_resets_defaults(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._reset_to_defaults = lambda: called.append("reset")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_r, mod=CTRL | SHIFT))
        assert "reset" in called

    def test_ctrl_e_exports(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._export_c_header = lambda: called.append("export")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_e, mod=CTRL))
        assert "export" in called

    def test_ctrl_shift_e_extract_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._extract_to_new_scene = lambda: called.append("extract")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_e, mod=CTRL | SHIFT))
        assert "extract" in called

    def test_ctrl_t_save_template(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._save_selection_as_template = lambda: called.append("save_tmpl")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_t, mod=CTRL))
        assert "save_tmpl" in called

    def test_ctrl_shift_t_list_templates(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._list_templates = lambda: called.append("list_tmpl")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_t, mod=CTRL | SHIFT))
        assert "list_tmpl" in called

    def test_ctrl_j_goto(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._goto_widget_prompt = lambda: called.append("goto")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_j, mod=CTRL))
        assert "goto" in called

    def test_ctrl_shift_j_snap_sizes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._snap_sizes_to_grid = lambda: called.append("snapsize")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_j, mod=CTRL | SHIFT))
        assert "snapsize" in called

    def test_ctrl_i_invert(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._invert_selection = lambda: called.append("invert")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_i, mod=CTRL))
        assert "invert" in called

    def test_ctrl_shift_i_show_all(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._show_all_widgets = lambda: called.append("show")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_i, mod=CTRL | SHIFT))
        assert "show" in called

    def test_ctrl_b_same_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_same_color = lambda: called.append("color")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_b, mod=CTRL))
        assert "color" in called

    def test_ctrl_shift_b_bordered(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_bordered = lambda: called.append("bordered")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_b, mod=CTRL | SHIFT))
        assert "bordered" in called

    def test_ctrl_w_stats(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._scene_stats = lambda: called.append("stats")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_w, mod=CTRL))
        assert "stats" in called

    def test_ctrl_shift_w_fit_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._fit_scene_to_content = lambda: called.append("fit")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_w, mod=CTRL | SHIFT))
        assert "fit" in called

    def test_ctrl_h_parent_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_parent_panel = lambda: called.append("parent")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_h, mod=CTRL))
        assert "parent" in called

    def test_ctrl_shift_h_hide_unselected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._hide_unselected = lambda: called.append("hide")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_h, mod=CTRL | SHIFT))
        assert "hide" in called

    def test_ctrl_k_children(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_children = lambda: called.append("children")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_k, mod=CTRL))
        assert "children" in called

    def test_ctrl_shift_k_clear_padding(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._clear_padding = lambda: called.append("clrpad")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_k, mod=CTRL | SHIFT))
        assert "clrpad" in called

    def test_ctrl_o_copy_to_next(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._copy_to_next_scene = lambda: called.append("copyscene")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_o, mod=CTRL))
        assert "copyscene" in called

    def test_ctrl_shift_o_toggle_borders(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_all_borders = lambda: called.append("borders")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_o, mod=CTRL | SHIFT))
        assert "borders" in called

    def test_ctrl_m_snap_grid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._snap_selection_to_grid = lambda: called.append("snap")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_m, mod=CTRL))
        assert "snap" in called

    def test_ctrl_shift_m_move_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._move_selection_to_origin = lambda: called.append("origin")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_m, mod=CTRL | SHIFT))
        assert "origin" in called

    def test_ctrl_p_paste_in_place(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._paste_in_place = lambda: called.append("pip")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_p, mod=CTRL))
        assert "pip" in called

    def test_ctrl_shift_p_all_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_all_panels = lambda: called.append("panels")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_p, mod=CTRL | SHIFT))
        assert "panels" in called

    def test_ctrl_q_broadcast(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._broadcast_to_all_scenes = lambda: called.append("bcast")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_q, mod=CTRL))
        assert "bcast" in called

    def test_ctrl_shift_q_quick_clone(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._quick_clone = lambda: called.append("clone")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_q, mod=CTRL | SHIFT))
        assert "clone" in called

    def test_ctrl_u_same_size(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_same_size = lambda: called.append("samesize")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_u, mod=CTRL))
        assert "samesize" in called

    def test_ctrl_shift_u_overlapping(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_overlapping = lambda: called.append("overlap")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_u, mod=CTRL | SHIFT))
        assert "overlap" in called

    def test_ctrl_g_groups(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._group_selection = lambda: called.append("group")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_g, mod=CTRL))
        assert "group" in called

    def test_ctrl_shift_g_ungroups(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._ungroup_selection = lambda: called.append("ungroup")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_g, mod=CTRL | SHIFT))
        assert "ungroup" in called

    def test_delete_deletes_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._delete_selected = lambda: called.append("del")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_DELETE))
        assert "del" in called

    def test_ctrl_shift_delete_deletes_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._delete_current_scene = lambda: called.append("delscene")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_DELETE, mod=CTRL | SHIFT))
        assert "delscene" in called


# ===========================================================================
# Ctrl+F-key shortcuts
# ===========================================================================

class TestCtrlFKeyShortcuts:
    def test_ctrl_f6_auto_flow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._auto_flow_layout = lambda: called.append("flow")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F6, mod=CTRL))
        assert "flow" in called

    def test_ctrl_f7_measure(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._measure_selection = lambda: called.append("measure")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F7, mod=CTRL))
        assert "measure" in called

    def test_ctrl_f8_space_h(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._space_evenly_h = lambda: called.append("spaceh")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F8, mod=CTRL))
        assert "spaceh" in called

    def test_ctrl_f9_space_v(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._space_evenly_v = lambda: called.append("spacev")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F9, mod=CTRL))
        assert "spacev" in called

    def test_ctrl_f5_replace_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._replace_text_in_scene = lambda: called.append("replace")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F5, mod=CTRL))
        assert "replace" in called

    def test_ctrl_f3_same_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_same_type_as_current = lambda: called.append("sametype")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F3, mod=CTRL))
        assert "sametype" in called

    def test_ctrl_f4_zoom_sel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._zoom_to_selection = lambda: called.append("zoomsel")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F4, mod=CTRL))
        assert "zoomsel" in called

    def test_ctrl_f10_overview(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._scene_overview = lambda: called.append("overview")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F10, mod=CTRL))
        assert "overview" in called

    def test_ctrl_f1_still_toggles_help(self, tmp_path, monkeypatch):
        """F1 always toggles help overlay regardless of modifiers."""
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_help_overlay = lambda: called.append("help")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F1, mod=CTRL))
        assert "help" in called

    def test_ctrl_f2_focus_overlay(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_focus_order_overlay = lambda: called.append("focusov")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F2, mod=CTRL))
        assert "focusov" in called

    def test_ctrl_f11_export_json(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._export_selection_json = lambda: called.append("exportjson")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F11, mod=CTRL))
        assert "exportjson" in called

    def test_ctrl_f12_split_layout(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._create_split_layout = lambda: called.append("split")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_F12, mod=CTRL))
        assert "split" in called


# ===========================================================================
# Plain letter keys (no Ctrl)
# ===========================================================================

class TestPlainKeyShortcuts:
    def test_g_toggles_grid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        before = app.show_grid
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_g))
        assert app.show_grid != before

    def test_shift_g_center_guides(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_center_guides = lambda: called.append("guides")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_g, mod=SHIFT))
        assert "guides" in called

    def test_x_toggles_snap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        before = app.snap_enabled
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_x))
        assert app.snap_enabled != before

    def test_shift_x_swap_dims(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._swap_dimensions = lambda: called.append("swapdim")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_x, mod=SHIFT))
        assert "swapdim" in called

    def test_l_toggle_lock(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_lock_selection = lambda: called.append("lock")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_l))
        assert "lock" in called

    def test_shift_l_select_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_locked = lambda: called.append("locked")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_l, mod=SHIFT))
        assert "locked" in called

    def test_s_cycle_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_style = lambda: called.append("style")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_s))
        assert "style" in called

    def test_shift_s_same_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_same_style = lambda: called.append("samestyle")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_s, mod=SHIFT))
        assert "samestyle" in called

    def test_v_toggle_vis(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_visibility = lambda: called.append("vis")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_v))
        assert "vis" in called

    def test_t_cycle_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_widget_type = lambda: called.append("wtype")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_t))
        assert "wtype" in called

    def test_b_cycle_border(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_border_style = lambda: called.append("border")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_b))
        assert "border" in called

    def test_q_cycle_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_color_preset = lambda: called.append("color")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_q))
        assert "color" in called

    def test_shift_q_swap_fg_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._swap_fg_bg = lambda: called.append("swap")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_q, mod=SHIFT))
        assert "swap" in called

    def test_a_cycle_align(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_align = lambda: called.append("align")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_a))
        assert "align" in called

    def test_shift_a_cycle_valign(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_valign = lambda: called.append("valign")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_a, mod=SHIFT))
        assert "valign" in called

    def test_m_mirror_h(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._mirror_selection = lambda axis: called.append(f"mirror_{axis}")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_m))
        assert "mirror_h" in called

    def test_shift_m_mirror_v(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._mirror_selection = lambda axis: called.append(f"mirror_{axis}")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_m, mod=SHIFT))
        assert "mirror_v" in called

    def test_w_toggle_border(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_border = lambda: called.append("bdr")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_w))
        assert "bdr" in called

    def test_shift_w_full_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._make_full_width = lambda: called.append("fw")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_w, mod=SHIFT))
        assert "fw" in called

    def test_o_cycle_overflow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_text_overflow = lambda: called.append("overflow")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_o))
        assert "overflow" in called

    def test_shift_o_select_overflow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_overflow = lambda: called.append("selover")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_o, mod=SHIFT))
        assert "selover" in called

    def test_y_toggle_checked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_checked = lambda: called.append("checked")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_y))
        assert "checked" in called

    def test_shift_y_select_hidden(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._select_hidden = lambda: called.append("hidden")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_y, mod=SHIFT))
        assert "hidden" in called

    def test_shift_f_full_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._make_full_height = lambda: called.append("fh")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_f, mod=SHIFT))
        assert "fh" in called

    def test_e_smart_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._smart_edit = lambda: called.append("edit")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_e))
        assert "edit" in called

    def test_f8_toggle_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_enabled = lambda: called.append("enabled")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F8))
        assert "enabled" in called

    def test_f9_clean_preview(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_clean_preview = lambda: called.append("clean")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F9))
        assert "clean" in called

    def test_f10_switch_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._switch_scene = lambda d: called.append(d)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F10))
        assert called == [1]

    def test_shift_f10_switch_scene_back(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._switch_scene = lambda d: called.append(d)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_F10, mod=SHIFT))
        assert called == [-1]

    def test_f6_arrange_in_row(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._arrange_in_row = lambda: called.append("row")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F6))
        assert "row" in called

    def test_f7_arrange_in_column(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._arrange_in_column = lambda: called.append("col")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F7))
        assert "col" in called

    def test_slash_search(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._search_widgets_prompt = lambda: called.append("search")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_SLASH))
        assert "search" in called

    def test_period_center_in_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._center_in_scene = lambda: called.append("center")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_PERIOD))
        assert "center" in called

    def test_shift_period_dup_right(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._duplicate_right = lambda: called.append("dupr")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_PERIOD, mod=SHIFT))
        assert "dupr" in called

    def test_comma_swap_positions(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._swap_positions = lambda: called.append("swappos")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_COMMA))
        assert "swappos" in called

    def test_shift_comma_dup_below(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._duplicate_below = lambda: called.append("dupbelow")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_COMMA, mod=SHIFT))
        assert "dupbelow" in called


# ===========================================================================
# Number keys → widget creation
# ===========================================================================

class TestNumberKeyWidgetCreation:
    def test_number_1_through_9(self, tmp_path, monkeypatch):
        keys = [
            (pygame.K_1, "label"), (pygame.K_2, "button"),
            (pygame.K_3, "panel"), (pygame.K_4, "progressbar"),
            (pygame.K_5, "gauge"), (pygame.K_6, "slider"),
            (pygame.K_7, "checkbox"), (pygame.K_8, "chart"),
            (pygame.K_9, "icon"),
        ]
        for key, expected_type in keys:
            app = _make_app(tmp_path, monkeypatch)
            called = []
            app._add_widget = lambda t, _c=called: _c.append(t)
            monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
            on_key_down(app, _key_event(key))
            assert expected_type in called, f"key {key} should add {expected_type}"

    def test_0_adds_textbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._add_widget = lambda t: called.append(t)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_0))
        assert "textbox" in called

    def test_shift_0_adds_radiobutton(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._add_widget = lambda t: called.append(t)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_0, mod=SHIFT))
        assert "radiobutton" in called


# ===========================================================================
# Z-order bracket keys
# ===========================================================================

class TestZOrderKeys:
    def test_left_bracket_step_back(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._z_order_step = lambda d: called.append(d)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_LEFTBRACKET))
        assert called == [-1]

    def test_right_bracket_step_forward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._z_order_step = lambda d: called.append(d)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_RIGHTBRACKET))
        assert called == [1]

    def test_ctrl_left_bracket_send_to_back(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._z_order_send_to_back = lambda: called.append("back")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_LEFTBRACKET, mod=CTRL))
        assert "back" in called

    def test_ctrl_right_bracket_bring_to_front(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._z_order_bring_to_front = lambda: called.append("front")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_RIGHTBRACKET, mod=CTRL))
        assert "front" in called


# ===========================================================================
# Escape behavior
# ===========================================================================

class TestEscKey:
    def test_escape_deselects_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_ESCAPE))
        assert app.state.selected == []

    def test_escape_sets_running_false(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_ESCAPE))
        assert app.running is False


# ===========================================================================
# Sim / input mode
# ===========================================================================

class TestSimInputMode:
    def test_f2_toggles_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app.sim_input_mode is False
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F2))
        assert app.sim_input_mode is True
        on_key_down(app, _key_event(pygame.K_F2))
        assert app.sim_input_mode is False

    def test_escape_in_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.sim_input_mode = True
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_ESCAPE))
        # Should not set running=False, just dispatch sim B
        assert app.running is True

    def test_backspace_in_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.sim_input_mode = True
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_BACKSPACE))
        # Should not crash

    def test_enter_in_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.sim_input_mode = True
        called = []
        app._activate_focused = lambda: called.append("act")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_RETURN))
        assert "act" in called

    def test_space_in_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.sim_input_mode = True
        called = []
        app._activate_focused = lambda: called.append("act")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_SPACE))
        assert "act" in called

    def test_arrows_in_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.sim_input_mode = True
        called = []
        app._focus_move_direction = lambda d: called.append(d)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_LEFT))
        on_key_down(app, _key_event(pygame.K_RIGHT))
        on_key_down(app, _key_event(pygame.K_UP))
        on_key_down(app, _key_event(pygame.K_DOWN))
        assert called == ["left", "right", "up", "down"]

    def test_pageup_down_in_sim_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.sim_input_mode = True
        called = []
        app._adjust_focused_value = lambda s: called.append(s)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_PAGEUP))
        on_key_down(app, _key_event(pygame.K_PAGEDOWN))
        assert called == [1, -1]


# ===========================================================================
# Arrow keys in normal mode
# ===========================================================================

class TestArrowKeysNormal:
    def test_arrow_moves_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=50, y=50)
        _sel(app, 0)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_RIGHT))
        # Should have moved right by GRID (or 1, depending on snap)

    def test_ctrl_shift_arrows_reorder(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0)
        called = []
        app._reorder_selection = lambda d: called.append(d)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_UP, mod=CTRL | SHIFT))
        on_key_down(app, _key_event(pygame.K_DOWN, mod=CTRL | SHIFT))
        assert called == [-1, 1]

    def test_no_selection_arrows_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=50, y=50)
        _sel(app)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_LEFT))
        assert _w(app, 0).x == 50  # unchanged


# ===========================================================================
# Tab, Home, End, F keys
# ===========================================================================

class TestMiscKeys:
    def test_tab_toggles_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_panels = lambda: called.append("panels")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_TAB))
        assert "panels" in called

    def test_home_selects_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_HOME))
        assert 0 in app.state.selected

    def test_end_selects_last(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_END))
        assert 1 in app.state.selected

    def test_f3_overflow_warnings(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_overflow_warnings = lambda: called.append("ow")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F3))
        assert "ow" in called

    def test_f4_zoom_to_fit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._zoom_to_fit = lambda: called.append("zoom")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F4))
        assert "zoom" in called

    def test_f5_live_preview(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._send_live_preview = lambda: called.append("preview")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F5))
        assert "preview" in called

    def test_f11_fullscreen(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_fullscreen = lambda: called.append("fs")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F11))
        assert "fs" in called

    def test_f12_screenshot(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._screenshot_canvas = lambda: called.append("ss")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_F12))
        assert "ss" in called

    def test_n_cycle_forward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_n))
        assert 1 in app.state.selected

    def test_p_key_cycle_backward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 1)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_p))
        assert 0 in app.state.selected

    def test_semicolon_stack_v(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._stack_vertical = lambda: called.append("sv")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_SEMICOLON))
        assert "sv" in called

    def test_shift_semicolon_eq_heights(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._equalize_heights = lambda: called.append("eqh")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_SEMICOLON, mod=SHIFT))
        assert "eqh" in called

    def test_quote_stack_h(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._stack_horizontal = lambda: called.append("sh")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_QUOTE))
        assert "sh" in called

    def test_shift_quote_eq_widths(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._equalize_widths = lambda: called.append("eqw")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_QUOTE, mod=SHIFT))
        assert "eqw" in called

    def test_backslash_gray_fg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_gray_fg = lambda: called.append("gfg")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_BACKSLASH))
        assert "gfg" in called

    def test_shift_backslash_gray_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._cycle_gray_bg = lambda: called.append("gbg")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_BACKSLASH, mod=SHIFT))
        assert "gbg" in called

    def test_plus_adjust_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._adjust_value = lambda s: called.append(s)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_EQUALS))
        assert called == [1]

    def test_shift_plus_adjust_5(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._adjust_value = lambda s: called.append(s)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_EQUALS, mod=SHIFT))
        assert called == [5]

    def test_minus_adjust_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._adjust_value = lambda s: called.append(s)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_MINUS))
        assert called == [-1]

    def test_ctrl_plus_zoom_in(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._set_scale = lambda s: called.append(s)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_EQUALS, mod=CTRL))
        assert len(called) == 1

    def test_ctrl_minus_zoom_out(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._set_scale = lambda s: called.append(s)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_MINUS, mod=CTRL))
        assert len(called) == 1

    def test_ctrl_0_reset_zoom(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._reset_zoom = lambda: called.append("reset")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_0, mod=CTRL))
        assert "reset" in called

    def test_ctrl_shift_0_flatten_z(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._flatten_z_indices = lambda: called.append("flat")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | SHIFT)
        on_key_down(app, _key_event(pygame.K_0, mod=CTRL | SHIFT))
        assert "flat" in called

    def test_backtick_widget_ids(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_widget_ids = lambda: called.append("ids")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_key_down(app, _key_event(pygame.K_BACKQUOTE))
        assert "ids" in called

    def test_shift_backtick_z_labels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_z_labels = lambda: called.append("zlabels")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_BACKQUOTE, mod=SHIFT))
        assert "zlabels" in called


# ===========================================================================
# Ctrl+Alt shortcuts
# ===========================================================================

class TestCtrlAltShortcuts:
    def test_ctrl_alt_left(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from cyberpunk_designer import layout_tools
        called = []
        monkeypatch.setattr(layout_tools, "align_selection", lambda a, d: called.append(d))
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | ALT)
        on_key_down(app, _key_event(pygame.K_LEFT, mod=CTRL | ALT))
        assert "left" in called

    def test_ctrl_alt_h_distribute(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from cyberpunk_designer import layout_tools
        called = []
        monkeypatch.setattr(layout_tools, "distribute_selection", lambda a, d: called.append(d))
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | ALT)
        on_key_down(app, _key_event(pygame.K_h, mod=CTRL | ALT))
        assert "h" in called

    def test_ctrl_alt_app_table_entries(self, tmp_path, monkeypatch):
        """Test a few Ctrl+Alt app-table entries dispatch correctly."""
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._equalize_gaps = lambda: called.append("eqgaps")
        app._grid_arrange = lambda: called.append("grid")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL | ALT)
        on_key_down(app, _key_event(pygame.K_e, mod=CTRL | ALT))
        on_key_down(app, _key_event(pygame.K_g, mod=CTRL | ALT))
        assert "eqgaps" in called
        assert "grid" in called


# ===========================================================================
# Shift+Fkey creators
# ===========================================================================

class TestShiftFKeys:
    def test_shift_f1_still_toggles_help(self, tmp_path, monkeypatch):
        """F1 always toggles help overlay regardless of modifiers."""
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._toggle_help_overlay = lambda: called.append("help")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_F1, mod=SHIFT))
        assert "help" in called

    def test_shift_f2_nav_row(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._create_nav_row = lambda: called.append("nav")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_F2, mod=SHIFT))
        assert "nav" in called

    def test_shift_f3_form_pair(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._create_form_pair = lambda: called.append("form")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: SHIFT)
        on_key_down(app, _key_event(pygame.K_F3, mod=SHIFT))
        assert "form" in called


# ===========================================================================
# _cycle_widget_selection
# ===========================================================================

class TestCycleWidgetSelection:
    def test_forward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _add(app)
        _sel(app, 0)
        _cycle_widget_selection(app, 1)
        assert 1 in app.state.selected

    def test_backward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 1)
        _cycle_widget_selection(app, -1)
        assert 0 in app.state.selected

    def test_wraps_around(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 1)
        _cycle_widget_selection(app, 1)
        assert 0 in app.state.selected

    def test_extend_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _add(app)
        _sel(app, 0)
        _cycle_widget_selection(app, 1, extend=True)
        assert 0 in app.state.selected
        assert 1 in app.state.selected

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _cycle_widget_selection(app, 1)  # no crash

    def test_no_selection_starts_at_zero(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app)  # nothing selected
        app.state.selected_idx = None
        _cycle_widget_selection(app, 1)
        assert 0 in app.state.selected

    def test_no_selection_backward_starts_at_end(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app)
        app.state.selected_idx = None
        _cycle_widget_selection(app, -1)
        assert 1 in app.state.selected


# ===========================================================================
# Ctrl+1..9 jump to scene
# ===========================================================================

class TestCtrlNumberSceneJump:
    def test_ctrl_1_jumps_to_first_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._jump_to_scene = lambda i: called.append(i)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_1, mod=CTRL))
        assert called == [0]

    def test_ctrl_3_jumps_to_third(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        called = []
        app._jump_to_scene = lambda i: called.append(i)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        on_key_down(app, _key_event(pygame.K_3, mod=CTRL))
        assert called == [2]
