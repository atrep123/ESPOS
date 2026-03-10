"""Tests for ui_cli.py — CLI command loop, help, and WCAG helpers."""

import os

import pytest

from ui_cli import (
    _NAMED_COLORS,
    MSG_FAILED,
    MSG_INDEX_INTEGER,
    MSG_INVALID_INDEX,
    MSG_NO_SCENE,
    MSG_UNKNOWN_ANIM,
    _contrast_ratio,
    _parse_color,
    _rel_lum,
    create_cli_interface,
    get_widget_help,
    show_command_help,
)
from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run(commands, capsys=None):
    """Run CLI commands and return captured stdout."""
    create_cli_interface(commands=commands)
    if capsys:
        return capsys.readouterr().out
    return ""


# ===========================================================================
# MSG constants
# ===========================================================================

class TestMsgConstants:
    def test_msg_constants_are_strings(self):
        for c in (MSG_INVALID_INDEX, MSG_NO_SCENE, MSG_INDEX_INTEGER, MSG_FAILED, MSG_UNKNOWN_ANIM):
            assert isinstance(c, str) and len(c) > 0


# ===========================================================================
# _parse_color
# ===========================================================================

class TestParseColor:
    def test_named_black(self):
        assert _parse_color("black") == (0, 0, 0)

    def test_named_white(self):
        assert _parse_color("white") == (255, 255, 255)

    def test_named_case_insensitive(self):
        assert _parse_color("RED") == (255, 0, 0)

    def test_hex_6_digit(self):
        assert _parse_color("#ff8800") == (255, 136, 0)

    def test_hex_bad_digits(self):
        assert _parse_color("#zzzzzz") == (0, 0, 0)

    def test_hex_short(self):
        # Not 6-digit hex -> fallback
        assert _parse_color("#fff") == (0, 0, 0)

    def test_empty_string(self):
        assert _parse_color("") == (0, 0, 0)

    def test_none_coerced(self):
        assert _parse_color(None) == (0, 0, 0)

    def test_unknown_name(self):
        assert _parse_color("chartreuse") == (0, 0, 0)

    def test_all_named_present(self):
        expected_names = {"black", "white", "red", "green", "blue", "yellow",
                          "cyan", "magenta", "gray", "grey", "orange", "purple"}
        assert expected_names == set(_NAMED_COLORS.keys())


# ===========================================================================
# _rel_lum / _contrast_ratio
# ===========================================================================

class TestContrastHelpers:
    def test_rel_lum_black(self):
        assert _rel_lum((0, 0, 0)) == pytest.approx(0.0)

    def test_rel_lum_white(self):
        assert _rel_lum((255, 255, 255)) == pytest.approx(1.0, abs=0.01)

    def test_contrast_white_black(self):
        ratio = _contrast_ratio("white", "black")
        assert ratio == pytest.approx(21.0, abs=0.1)

    def test_contrast_same_color(self):
        assert _contrast_ratio("red", "red") == pytest.approx(1.0)

    def test_contrast_order_independent(self):
        r1 = _contrast_ratio("white", "blue")
        r2 = _contrast_ratio("blue", "white")
        assert r1 == pytest.approx(r2)


# ===========================================================================
# show_command_help / get_widget_help  (already tested in test_ui_designer_extra
# but verify they work from ui_cli directly)
# ===========================================================================

class TestHelpers:
    def test_show_command_help_add(self, capsys):
        show_command_help("add")
        out = capsys.readouterr().out
        assert "add" in out.lower()

    def test_show_command_help_unknown(self, capsys):
        show_command_help("nonexistent_xyz")
        out = capsys.readouterr().out
        assert "No detailed help" in out

    def test_get_widget_help_label(self):
        w = WidgetConfig(type="label", x=0, y=0, width=10, height=10)
        info = get_widget_help(w)
        assert "description" in info
        assert "tips" in info

    def test_get_widget_help_unknown_type(self):
        w = WidgetConfig(type="alien", x=0, y=0, width=10, height=10)
        info = get_widget_help(w)
        assert info["description"] == "Generic widget."

    def test_get_widget_help_all_known_types(self):
        known = ["label", "button", "progressbar", "gauge", "checkbox",
                 "radiobutton", "textbox", "panel", "icon", "chart", "box", "slider"]
        for t in known:
            w = WidgetConfig(type=t, x=0, y=0, width=10, height=10)
            info = get_widget_help(w)
            assert info["description"] != "Generic widget.", f"{t} should have specific help"


# ===========================================================================
# create_cli_interface — Scene management
# ===========================================================================

class TestCliSceneManagement:
    def test_quit(self, capsys):
        out = _run(["quit"], capsys)
        assert "ESP32 UI Designer" in out

    def test_exit(self, capsys):
        out = _run(["exit"], capsys)
        assert "ESP32 UI Designer" in out

    def test_empty_command_skipped(self, capsys):
        out = _run(["", "quit"], capsys)
        assert "ESP32 UI Designer" in out

    def test_new_scene(self, capsys):
        out = _run(["new TestScene", "quit"], capsys)
        assert "[OK] Created scene: TestScene" in out

    def test_new_missing_name(self, capsys):
        out = _run(["new", "quit"], capsys)
        assert "Usage: new" in out

    def test_scenes_empty(self, capsys):
        out = _run(["scenes", "quit"], capsys)
        assert "No scenes created" in out

    def test_scenes_listing(self, capsys):
        out = _run(["new A", "new B", "scenes", "quit"], capsys)
        assert "A" in out and "B" in out

    def test_switch_scene(self, capsys):
        out = _run(["new A", "new B", "switch A", "quit"], capsys)
        assert "[OK] Switched to scene: A" in out

    def test_switch_missing_name(self, capsys):
        out = _run(["switch", "quit"], capsys)
        assert "Usage: switch" in out

    def test_switch_nonexistent(self, capsys):
        out = _run(["new A", "switch Z", "quit"], capsys)
        assert "[FAIL]" in out


# ===========================================================================
# Widget operations
# ===========================================================================

class TestCliWidgetOps:
    def test_add_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 Hello", "quit"], capsys)
        assert "[OK] Added label widget" in out

    def test_add_missing_args(self, capsys):
        out = _run(["new S", "add label 10", "quit"], capsys)
        assert "Usage: add" in out

    def test_list_widgets(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 Hello", "list", "quit"], capsys)
        assert "label" in out and "Hello" in out

    def test_list_no_scene(self, capsys):
        out = _run(["list", "quit"], capsys)
        assert MSG_NO_SCENE in out

    def test_clone_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "clone 0", "quit"], capsys)
        assert "[OK] Widget cloned" in out

    def test_clone_missing_idx(self, capsys):
        out = _run(["new S", "clone", "quit"], capsys)
        assert "Usage: clone" in out

    def test_clone_with_offset(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "clone 0 5 5", "quit"], capsys)
        assert "[OK] Widget cloned" in out

    def test_duplicate_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "duplicate 0", "quit"], capsys)
        assert "[OK] Widget duplicated" in out

    def test_duplicate_missing_idx(self, capsys):
        out = _run(["new S", "duplicate", "quit"], capsys)
        assert "Usage: duplicate" in out

    def test_move_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "move 0 5 5", "quit"], capsys)
        assert "[OK] Widget moved" in out

    def test_move_missing_args(self, capsys):
        out = _run(["new S", "move 0 5", "quit"], capsys)
        assert "Usage: move" in out

    def test_resize_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "resize 0 10 10", "quit"], capsys)
        assert "[OK] Widget resized" in out

    def test_resize_missing_args(self, capsys):
        out = _run(["new S", "resize 0 10", "quit"], capsys)
        assert "Usage: resize" in out

    def test_delete_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "delete 0", "quit"], capsys)
        assert "[OK] Widget deleted" in out

    def test_delete_missing_idx(self, capsys):
        out = _run(["new S", "delete", "quit"], capsys)
        assert "Usage: delete" in out

    def test_select_widget(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "select 0", "quit"], capsys)
        assert "[OK] Selected widget" in out

    def test_select_missing_idx(self, capsys):
        out = _run(["new S", "select", "quit"], capsys)
        assert "Usage: select" in out

    def test_select_invalid_idx(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "select 99", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_select_non_integer(self, capsys):
        out = _run(["new S", "select abc", "quit"], capsys)
        assert "Usage: select" in out


# ===========================================================================
# Lock
# ===========================================================================

class TestCliLock:
    def test_lock_on(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "lock 0 on", "quit"], capsys)
        assert "[LOCK]" in out

    def test_lock_off(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "lock 0 on", "lock 0 off", "quit"], capsys)
        assert "[UNLOCK]" in out

    def test_lock_toggle(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "lock 0 toggle", "quit"], capsys)
        assert "[LOCK]" in out

    def test_lock_bad_mode(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "lock 0 maybe", "quit"], capsys)
        assert "Usage: lock" in out

    def test_lock_missing_args(self, capsys):
        out = _run(["new S", "lock 0", "quit"], capsys)
        assert "Usage: lock" in out


# ===========================================================================
# Edit
# ===========================================================================

class TestCliEdit:
    def test_edit_text(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 Hello", "edit 0 text World", "quit"], capsys)
        assert "[OK] Updated text = World" in out

    def test_edit_integer_prop(self, capsys):
        out = _run(["new S", "add progressbar 10 10 50 10", "edit 0 value 42", "quit"], capsys)
        assert "[OK] Updated value = 42" in out

    def test_edit_bool_prop(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "edit 0 visible false", "quit"], capsys)
        assert "[OK] Updated visible = false" in out

    def test_edit_missing_args(self, capsys):
        out = _run(["new S", "edit 0 text", "quit"], capsys)
        assert "Usage: edit" in out


# ===========================================================================
# Undo / Redo
# ===========================================================================

class TestCliUndoRedo:
    def test_undo_nothing(self, capsys):
        out = _run(["undo", "quit"], capsys)
        assert "Nothing to undo" in out

    def test_redo_nothing(self, capsys):
        out = _run(["redo", "quit"], capsys)
        assert "Nothing to redo" in out

    def test_undo_after_add(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "undo", "quit"], capsys)
        assert "[OK] Undone" in out


# ===========================================================================
# Grid / Snap / Guides
# ===========================================================================

class TestCliGridSnap:
    def test_grid_status(self, capsys):
        out = _run(["grid", "quit"], capsys)
        assert "Grid is" in out

    def test_grid_on(self, capsys):
        out = _run(["grid on", "quit"], capsys)
        assert "[OK] Grid enabled" in out

    def test_grid_off(self, capsys):
        out = _run(["grid off", "quit"], capsys)
        assert "[OK] Grid disabled" in out

    def test_snap_status(self, capsys):
        out = _run(["snap", "quit"], capsys)
        assert "Snap to grid is" in out

    def test_snap_on(self, capsys):
        out = _run(["snap on", "quit"], capsys)
        assert "[OK] Snap to grid enabled" in out

    def test_snap_off(self, capsys):
        out = _run(["snap off", "quit"], capsys)
        assert "[OK] Snap to grid disabled" in out

    def test_guides_status(self, capsys):
        out = _run(["guides", "quit"], capsys)
        assert "Guides overlay is" in out

    def test_guides_on(self, capsys):
        out = _run(["guides on", "quit"], capsys)
        assert "[OK] Guides enabled" in out

    def test_guides_off(self, capsys):
        out = _run(["guides off", "quit"], capsys)
        assert "[OK] Guides disabled" in out

    def test_snaptol_status(self, capsys):
        out = _run(["snaptol", "quit"], capsys)
        assert "Snap tolerance:" in out

    def test_snaptol_set(self, capsys):
        out = _run(["snaptol 8", "quit"], capsys)
        assert "[OK] Snap tolerance set to 8" in out

    def test_snaptol_bad(self, capsys):
        out = _run(["snaptol abc", "quit"], capsys)
        assert "Usage: snaptol" in out

    def test_snapmode_status(self, capsys):
        out = _run(["snapmode", "quit"], capsys)
        assert "Snap mode:" in out

    def test_snapmode_pixel(self, capsys):
        out = _run(["snapmode pixel", "quit"], capsys)
        assert "pixel" in out

    def test_snapmode_fluid(self, capsys):
        out = _run(["snapmode fluid", "quit"], capsys)
        assert "fluid" in out

    def test_snapmode_bad(self, capsys):
        out = _run(["snapmode xxx", "quit"], capsys)
        assert "Usage: snapmode" in out


# ===========================================================================
# Preview / Templates / Widgets listing
# ===========================================================================

class TestCliDisplay:
    def test_preview(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 X", "preview", "quit"], capsys)
        # Preview returns ASCII art — just check it doesn't crash
        assert ">" in out  # echoed command

    def test_preview_grid(self, capsys):
        out = _run(["new S", "preview grid", "quit"], capsys)
        assert ">" in out

    def test_templates(self, capsys):
        out = _run(["templates", "quit"], capsys)
        assert "Templates" in out

    def test_widgets_listing(self, capsys):
        out = _run(["widgets", "quit"], capsys)
        assert "label" in out


# ===========================================================================
# Theme & WCAG
# ===========================================================================

class TestCliTheme:
    def test_theme_no_sub(self, capsys):
        out = _run(["theme", "quit"], capsys)
        assert "Usage: theme" in out

    def test_theme_list(self, capsys):
        out = _run(["theme list", "quit"], capsys)
        assert "Themes" in out

    def test_theme_set(self, capsys):
        out = _run(["new S", "theme set default", "quit"], capsys)
        assert "[OK] Theme set: default" in out

    def test_theme_set_missing(self, capsys):
        out = _run(["theme set", "quit"], capsys)
        assert "Usage: theme set" in out

    def test_theme_set_unknown(self, capsys):
        out = _run(["new S", "theme set nonexistent", "quit"], capsys)
        assert "Unknown theme" in out

    def test_theme_bind(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "theme bind 0 fg text", "quit"], capsys)
        assert "[OK] Theme role bound" in out

    def test_theme_bind_bg(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "theme bind 0 bg primary", "quit"], capsys)
        assert "[OK] Theme role bound" in out

    def test_theme_bind_bad_which(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "theme bind 0 xx text", "quit"], capsys)
        assert "Use fg or bg" in out

    def test_theme_bind_missing(self, capsys):
        out = _run(["theme bind 0 fg", "quit"], capsys)
        assert "Usage: theme bind" in out

    def test_theme_bind_non_int(self, capsys):
        out = _run(["new S", "theme bind abc fg text", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_theme_apply(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "theme bind 0 fg text", "theme apply", "quit"
        ], capsys)
        assert "[OK] Theme applied" in out

    def test_theme_unknown_sub(self, capsys):
        out = _run(["theme xyz", "quit"], capsys)
        assert "Unknown theme subcommand" in out

    def test_contrast_all_ok(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10 Hi",
            "edit 0 color_fg white", "edit 0 color_bg black",
            "contrast", "quit"
        ], capsys)
        assert "All text meets contrast" in out

    def test_contrast_with_min(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 Hi", "contrast 1.0", "quit"], capsys)
        assert "contrast" in out.lower()


# ===========================================================================
# Tree
# ===========================================================================

class TestCliTree:
    def test_tree_no_scene(self, capsys):
        out = _run(["tree", "quit"], capsys)
        assert MSG_NO_SCENE in out

    def test_tree_empty_scene(self, capsys):
        out = _run(["new S", "tree", "quit"], capsys)
        assert "Tree" in out and "(no groups)" in out

    def test_tree_with_widgets(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 A", "tree", "quit"], capsys)
        assert "label" in out


# ===========================================================================
# File operations — save / load / export
# ===========================================================================

class TestCliFileOps:
    def test_save_missing_file(self, capsys):
        out = _run(["save", "quit"], capsys)
        assert "Usage: save" in out

    def test_load_missing_file(self, capsys):
        out = _run(["load", "quit"], capsys)
        assert "Usage: load" in out

    def test_save_and_load(self, capsys, tmp_path):
        fpath = str(tmp_path / "test_scene.json").replace("\\", "/")
        _run([
            "new S", "add label 10 10 50 10 SaveTest",
            f"save {fpath}", f"load {fpath}", "quit"
        ], capsys)
        assert os.path.exists(fpath)

    def test_export_missing_file(self, capsys):
        out = _run(["export", "quit"], capsys)
        assert "Usage: export" in out

    def test_export_code(self, capsys, tmp_path):
        fpath = str(tmp_path / "test_export.py").replace("\\", "/")
        _run(["new S", "add label 10 10 50 10", f"export {fpath}", "quit"], capsys)
        # export_code may print something or just write file

    def test_restore_no_snapshots(self, capsys):
        out = _run(["restore", "quit"], capsys)
        assert "No snapshots" in out or "Snapshots" in out


# ===========================================================================
# Layout / Align / Distribute
# ===========================================================================

class TestCliLayout:
    def test_layout_missing_type(self, capsys):
        out = _run(["new S", "layout", "quit"], capsys)
        assert "Usage: layout" in out

    def test_layout_vertical(self, capsys):
        out = _run([
            "new S",
            "add label 10 10 50 10",
            "add label 10 30 50 10",
            "layout vertical", "quit"
        ], capsys)
        assert "[OK] Applied vertical layout" in out

    def test_layout_horizontal(self, capsys):
        out = _run([
            "new S",
            "add label 10 10 50 10",
            "add label 10 30 50 10",
            "layout horizontal 8", "quit"
        ], capsys)
        assert "[OK] Applied horizontal layout" in out

    def test_align_missing(self, capsys):
        out = _run(["new S", "align left", "quit"], capsys)
        assert "Usage: align" in out

    def test_align_left(self, capsys):
        out = _run([
            "new S",
            "add label 10 10 50 10",
            "add label 20 30 50 10",
            "align left 0 1", "quit"
        ], capsys)
        assert "[OK] Aligned" in out

    def test_distribute_missing(self, capsys):
        out = _run(["new S", "distribute horizontal 0", "quit"], capsys)
        assert "Usage: distribute" in out

    def test_distribute_horizontal(self, capsys):
        out = _run([
            "new S",
            "add label 10 10 50 10",
            "add label 20 30 50 10",
            "add label 30 50 50 10",
            "distribute horizontal 0 1 2", "quit"
        ], capsys)
        assert "[OK] Distributed" in out


# ===========================================================================
# Grid columns / Breakpoint / Responsive
# ===========================================================================

class TestCliGridcols:
    def test_gridcols_status(self, capsys):
        out = _run(["gridcols", "quit"], capsys)
        assert "Grid columns:" in out

    def test_gridcols_set(self, capsys):
        out = _run(["gridcols 8", "quit"], capsys)
        assert "[OK] Grid columns set to" in out

    def test_gridcols_bad(self, capsys):
        out = _run(["gridcols abc", "quit"], capsys)
        assert "Usage: gridcols" in out

    def test_bp_missing(self, capsys):
        out = _run(["bp", "quit"], capsys)
        assert "Usage: bp" in out

    def test_bp_set(self, capsys):
        out = _run(["new S", "bp 128x64", "quit"], capsys)
        assert "[OK] Breakpoint applied: 128x64" in out

    def test_bp_bad(self, capsys):
        out = _run(["new S", "bp abc", "quit"], capsys)
        assert "Usage: bp" in out

    def test_resp_missing(self, capsys):
        out = _run(["resp", "quit"], capsys)
        assert "Usage: resp" in out

    def test_resp_base(self, capsys):
        out = _run(["new S", "resp base", "quit"], capsys)
        assert "[OK] Responsive base recorded" in out

    def test_resp_apply(self, capsys):
        out = _run(["new S", "resp apply", "quit"], capsys)
        assert "[OK] Responsive constraints applied" in out

    def test_resp_bad(self, capsys):
        out = _run(["resp xyz", "quit"], capsys)
        assert "Usage: resp" in out


# ===========================================================================
# State management
# ===========================================================================

class TestCliState:
    def test_state_no_sub(self, capsys):
        out = _run(["state", "quit"], capsys)
        assert "Usage: state" in out

    def test_state_no_scene(self, capsys):
        out = _run(["state define 0 hover x=1", "quit"], capsys)
        assert MSG_NO_SCENE in out

    def test_state_define(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "state define 0 hover color_fg=cyan", "quit"
        ], capsys)
        assert "[OK] State 'hover' overrides defined" in out

    def test_state_define_missing_args(self, capsys):
        out = _run(["new S", "state define 0 hover", "quit"], capsys)
        assert "Usage: state define" in out

    def test_state_define_bad_idx(self, capsys):
        out = _run(["new S", "state define abc hover x=1", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_state_define_invalid_idx(self, capsys):
        out = _run(["new S", "state define 99 hover x=1", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_state_set(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "state define 0 hover x=1",
            "state set 0 hover", "quit"
        ], capsys)
        assert "[OK] Widget 0 state set to 'hover'" in out

    def test_state_set_missing(self, capsys):
        out = _run(["new S", "state set 0", "quit"], capsys)
        assert "Usage: state set" in out

    def test_state_set_bad_idx(self, capsys):
        out = _run(["new S", "state set abc hover", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_state_set_invalid_idx(self, capsys):
        out = _run(["new S", "state set 99 hover", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_state_list(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "state define 0 hover x=1",
            "state list 0", "quit"
        ], capsys)
        assert "hover" in out

    def test_state_list_no_overrides(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "state list 0", "quit"], capsys)
        assert "(no overrides)" in out

    def test_state_list_missing(self, capsys):
        out = _run(["new S", "state list", "quit"], capsys)
        assert "Usage: state list" in out

    def test_state_list_bad_idx(self, capsys):
        out = _run(["new S", "state list abc", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_state_list_invalid_idx(self, capsys):
        out = _run(["new S", "state list 99", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_state_clear(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "state define 0 hover x=1",
            "state clear 0 hover", "quit"
        ], capsys)
        assert "[OK] Removed state 'hover'" in out

    def test_state_clear_missing(self, capsys):
        out = _run(["new S", "state clear 0", "quit"], capsys)
        assert "Usage: state clear" in out

    def test_state_clear_bad_idx(self, capsys):
        out = _run(["new S", "state clear abc hover", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_state_clear_invalid_idx(self, capsys):
        out = _run(["new S", "state clear 99 hover", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_state_clear_nonexistent(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "state clear 0 nope", "quit"], capsys)
        assert "No such state override" in out

    def test_state_unknown_sub(self, capsys):
        out = _run(["new S", "state xyz", "quit"], capsys)
        assert "Unknown state subcommand" in out


# ===========================================================================
# Animations
# ===========================================================================

class TestCliAnim:
    def test_anim_no_sub(self, capsys):
        out = _run(["anim", "quit"], capsys)
        assert "Usage: anim" in out

    def test_anim_list(self, capsys):
        out = _run(["anim list", "quit"], capsys)
        assert "bounce" in out

    def test_anim_add(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "anim add 0 bounce", "quit"
        ], capsys)
        assert "[OK] Animation 'bounce' tagged" in out

    def test_anim_add_missing(self, capsys):
        out = _run(["new S", "anim add 0", "quit"], capsys)
        assert "Usage: anim add" in out

    def test_anim_add_bad_idx(self, capsys):
        out = _run(["new S", "anim add abc bounce", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_anim_add_unknown_name(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "anim add 0 xxx", "quit"], capsys)
        assert MSG_UNKNOWN_ANIM in out

    def test_anim_add_invalid_idx(self, capsys):
        out = _run(["new S", "anim add 99 bounce", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_anim_add_no_scene(self, capsys):
        out = _run(["anim add 0 bounce", "quit"], capsys)
        assert MSG_NO_SCENE in out

    def test_anim_clear(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "anim add 0 bounce", "anim clear 0 bounce", "quit"
        ], capsys)
        assert "[OK] Animation 'bounce' removed" in out

    def test_anim_clear_missing(self, capsys):
        out = _run(["new S", "anim clear 0", "quit"], capsys)
        assert "Usage: anim clear" in out

    def test_anim_clear_bad_idx(self, capsys):
        out = _run(["new S", "anim clear abc bounce", "quit"], capsys)
        assert MSG_INDEX_INTEGER in out

    def test_anim_clear_invalid_idx(self, capsys):
        out = _run(["new S", "anim clear 99 bounce", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_anim_clear_not_tagged(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "anim clear 0 bounce", "quit"
        ], capsys)
        assert "Animation not tagged" in out

    def test_anim_preview(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "anim add 0 bounce",
            "anim preview 0 bounce 10 5", "quit"
        ], capsys)
        # Just check it doesn't crash
        assert ">" in out

    def test_anim_preview_missing(self, capsys):
        out = _run(["new S", "anim preview 0 bounce 10", "quit"], capsys)
        assert "Usage: anim preview" in out

    def test_anim_preview_bad_args(self, capsys):
        out = _run(["new S", "anim preview abc bounce 10 5", "quit"], capsys)
        assert "Usage: anim preview" in out

    def test_anim_preview_unknown(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "anim preview 0 xxx 10 5", "quit"], capsys)
        assert MSG_UNKNOWN_ANIM in out

    def test_anim_preview_invalid_idx(self, capsys):
        out = _run(["new S", "anim preview 99 bounce 10 5", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_anim_play(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "anim add 0 bounce",
            "anim play 0 bounce 2 1", "quit"
        ], capsys)
        assert "bounce" in out

    def test_anim_play_missing(self, capsys):
        out = _run(["new S", "anim play 0 bounce", "quit"], capsys)
        assert "Usage: anim play" in out

    def test_anim_play_bad_args(self, capsys):
        out = _run(["new S", "anim play abc bounce 2", "quit"], capsys)
        assert "Usage: anim play" in out

    def test_anim_play_unknown(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "anim play 0 xxx 2", "quit"], capsys)
        assert MSG_UNKNOWN_ANIM in out

    def test_anim_play_invalid_idx(self, capsys):
        out = _run(["new S", "anim play 99 bounce 2", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_anim_unknown_sub(self, capsys):
        out = _run(["new S", "anim xyz", "quit"], capsys)
        assert "Unknown anim subcommand" in out


# ===========================================================================
# Context
# ===========================================================================

class TestCliContext:
    def test_context_with_idx(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 Hi", "context 0", "quit"], capsys)
        assert "Context" in out and "Quick actions" in out

    def test_context_no_selection(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "context", "quit"], capsys)
        assert "Select a widget first" in out

    def test_context_with_select(self, capsys):
        out = _run(["new S", "add label 10 10 50 10 Hi", "select 0", "context", "quit"], capsys)
        assert "Context" in out

    def test_context_bad_idx(self, capsys):
        out = _run(["new S", "context abc", "quit"], capsys)
        assert "Usage: context" in out

    def test_context_invalid_idx(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "context 99", "quit"], capsys)
        assert MSG_INVALID_INDEX in out

    def test_context_no_scene(self, capsys):
        out = _run(["context 0", "quit"], capsys)
        assert MSG_NO_SCENE in out

    def test_context_locked_widget(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10 Hi",
            "lock 0 on", "context 0", "quit"
        ], capsys)
        assert "[LOCK]" in out


# ===========================================================================
# Groups
# ===========================================================================

class TestCliGroups:
    def test_group_no_sub(self, capsys):
        out = _run(["group", "quit"], capsys)
        assert "Usage: group" in out

    def test_group_list_empty(self, capsys):
        out = _run(["group list", "quit"], capsys)
        assert "No groups" in out

    def test_group_create(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10", "add label 20 20 50 10",
            "group create g1 0 1", "quit"
        ], capsys)
        assert "[OK] Done" in out

    def test_group_create_missing(self, capsys):
        out = _run(["new S", "group create g1", "quit"], capsys)
        assert "Usage: group create" in out

    def test_group_create_bad_idx(self, capsys):
        out = _run(["new S", "group create g1 abc", "quit"], capsys)
        assert "Indices must be integers" in out

    def test_group_add(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10", "add label 20 20 50 10",
            "add label 30 30 50 10",
            "group create g1 0 1", "group add g1 2", "quit"
        ], capsys)
        assert "[OK] Done" in out

    def test_group_remove(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10", "add label 20 20 50 10",
            "group create g1 0 1", "group remove g1 1", "quit"
        ], capsys)
        assert "[OK] Done" in out

    def test_group_list_with_groups(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "group create g1 0", "group list", "quit"
        ], capsys)
        assert "g1" in out

    def test_group_unknown_sub(self, capsys):
        out = _run(["group xyz", "quit"], capsys)
        assert "Unknown group subcommand" in out


# ===========================================================================
# Symbols
# ===========================================================================

class TestCliSymbols:
    def test_symbol_no_sub(self, capsys):
        out = _run(["symbol", "quit"], capsys)
        assert "Usage: symbol" in out

    def test_symbol_list_empty(self, capsys):
        out = _run(["symbol list", "quit"], capsys)
        assert "No symbols" in out

    def test_symbol_save(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "symbol save sym1 0", "quit"
        ], capsys)
        assert "[OK] Saved" in out

    def test_symbol_save_missing(self, capsys):
        out = _run(["new S", "symbol save sym1", "quit"], capsys)
        assert "Usage: symbol save" in out

    def test_symbol_save_bad_idx(self, capsys):
        out = _run(["new S", "symbol save sym1 abc", "quit"], capsys)
        assert "Indices must be integers" in out

    def test_symbol_place(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "symbol save sym1 0", "symbol place sym1 0 0", "quit"
        ], capsys)
        assert "[OK] Placed" in out

    def test_symbol_place_missing(self, capsys):
        out = _run(["new S", "symbol place sym1 0", "quit"], capsys)
        assert "Usage: symbol place" in out

    def test_symbol_place_bad_xy(self, capsys):
        out = _run(["new S", "symbol place sym1 abc def", "quit"], capsys)
        assert "x/y must be integers" in out

    def test_symbol_list_with_symbols(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "symbol save sym1 0", "symbol list", "quit"
        ], capsys)
        assert "sym1" in out

    def test_symbol_unknown_sub(self, capsys):
        out = _run(["symbol xyz", "quit"], capsys)
        assert "Unknown symbol subcommand" in out


# ===========================================================================
# Checkpoints / Rollback / Diff
# ===========================================================================

class TestCliCheckpoints:
    def test_checkpoint_missing(self, capsys):
        out = _run(["checkpoint", "quit"], capsys)
        assert "Usage: checkpoint" in out

    def test_checkpoint_create(self, capsys):
        out = _run(["new S", "add label 10 10 50 10", "checkpoint cp1", "quit"], capsys)
        assert "[OK] Checkpoint created: cp1" in out

    def test_checkpoint_no_scene(self, capsys):
        out = _run(["checkpoint cp1", "quit"], capsys)
        assert "[FAIL]" in out

    def test_checkpoints_empty(self, capsys):
        out = _run(["checkpoints", "quit"], capsys)
        assert "No checkpoints" in out

    def test_checkpoints_list(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "checkpoint cp1", "checkpoints", "quit"
        ], capsys)
        assert "cp1" in out

    def test_rollback_missing(self, capsys):
        out = _run(["rollback", "quit"], capsys)
        assert "Usage: rollback" in out

    def test_rollback_success(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "checkpoint cp1",
            "add button 20 20 40 12 Btn",
            "rollback cp1", "quit"
        ], capsys)
        assert "[OK] Rolled back to checkpoint: cp1" in out

    def test_rollback_unknown(self, capsys):
        out = _run(["new S", "rollback nope", "quit"], capsys)
        assert "[FAIL]" in out

    def test_diff_missing(self, capsys):
        out = _run(["diff", "quit"], capsys)
        assert "Usage: diff" in out

    def test_diff_unknown_a(self, capsys):
        out = _run(["diff nope", "quit"], capsys)
        assert "Unknown checkpoint A" in out

    def test_diff_two_checkpoints(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "checkpoint cp1",
            "add button 20 20 40 12 Btn",
            "checkpoint cp2",
            "diff cp1 cp2", "quit"
        ], capsys)
        assert "Diff" in out

    def test_diff_unknown_b(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "checkpoint cp1",
            "diff cp1 nope", "quit"
        ], capsys)
        assert "Unknown checkpoint B" in out

    def test_diff_vs_current(self, capsys):
        out = _run([
            "new S", "add label 10 10 50 10",
            "checkpoint cp1",
            "add button 20 20 40 12 Btn",
            "diff cp1", "quit"
        ], capsys)
        assert "Diff" in out


# ===========================================================================
# Help / Unknown command / Shlex fallback
# ===========================================================================

class TestCliMisc:
    def test_help_no_arg(self, capsys):
        out = _run(["help", "quit"], capsys)
        assert "Type command name for help" in out

    def test_help_with_arg(self, capsys):
        out = _run(["help add", "quit"], capsys)
        assert "add" in out.lower()

    def test_unknown_command(self, capsys):
        out = _run(["xyzcommand", "quit"], capsys)
        assert "[FAIL] Unknown command: xyzcommand" in out

    def test_shlex_fallback(self, capsys):
        """Command with unbalanced quotes should still parse via split()."""
        out = _run(['new "unclosed', "quit"], capsys)
        # shlex.split fails on unbalanced quote, should fall back to cmd.split()
        assert ">" in out

    def test_template_command(self, capsys):
        out = _run(["new S", "template button_primary btn1 10 10", "quit"], capsys)
        assert "template" in out.lower()
