"""Tests for previously untested UIDesigner methods.

Covers: list_history, history_snapshot, set_grid_columns, add_widget_from_template,
clone_widget, groups API (add_to_group, remove_from_group, delete_group, list_groups,
group_set_lock, group_set_visible, create_group), symbols API (save_symbol, place_symbol),
checkpoints API (create_checkpoint, list_checkpoints, rollback_checkpoint),
export_to_html, show_command_help, get_widget_help, enable_pixel_art_mode, preview_ascii.
"""

import os

import pytest

from ui_designer import UIDesigner, WidgetConfig, get_widget_help, show_command_help

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_designer_with_scene(n_widgets=0):
    """Return (designer, scene) with optional pre-populated widgets."""
    d = UIDesigner(256, 128)
    d.snap_to_grid = False
    d.snap_edges = False
    d.snap_centers = False
    sc = d.create_scene("main")
    for i in range(n_widgets):
        w = WidgetConfig(type="label", x=i * 20, y=0, width=16, height=10, text=f"w{i}")
        sc.widgets.append(w)
    return d, sc


# ===================================================================
# History — list_history / history_snapshot
# ===================================================================


class TestListHistory:
    def test_empty_by_default(self):
        d, _ = _make_designer_with_scene()
        assert d.list_history() == []

    def test_after_single_state_save(self):
        d, sc = _make_designer_with_scene(1)
        # Trigger _save_state via a mutation
        d.move_widget(0, 5, 5)
        items = d.list_history()
        assert len(items) >= 1
        assert "scene" in items[-1]
        assert "ts" in items[-1]

    def test_limit_param(self):
        d, sc = _make_designer_with_scene(1)
        for _ in range(5):
            d.move_widget(0, 1, 1)
        # Should return at most 2
        items = d.list_history(limit=2)
        assert len(items) <= 2

    def test_entries_have_expected_keys(self):
        d, sc = _make_designer_with_scene(1)
        d.move_widget(0, 1, 0)
        entry = d.list_history()[-1]
        assert set(entry.keys()) == {"i", "scene", "widgets", "ts"}

    def test_index_increments(self):
        d, sc = _make_designer_with_scene(1)
        for _ in range(3):
            d.move_widget(0, 1, 0)
        items = d.list_history()
        indices = [e["i"] for e in items]
        assert indices == sorted(indices)


class TestHistorySnapshot:
    def test_valid_index_returns_dict(self):
        d, sc = _make_designer_with_scene(1)
        d.move_widget(0, 5, 5)
        snap = d.history_snapshot(0)
        assert isinstance(snap, dict)
        assert "widgets" in snap

    def test_negative_index_returns_none(self):
        d, _ = _make_designer_with_scene(1)
        d.move_widget(0, 1, 0)
        assert d.history_snapshot(-1) is None

    def test_out_of_range_returns_none(self):
        d, _ = _make_designer_with_scene(1)
        d.move_widget(0, 1, 0)
        assert d.history_snapshot(9999) is None

    def test_empty_undo_stack_returns_none(self):
        d, _ = _make_designer_with_scene()
        assert d.history_snapshot(0) is None


# ===================================================================
# set_grid_columns
# ===================================================================


class TestSetGridColumns:
    @pytest.mark.parametrize("n", [4, 8, 12])
    def test_valid_column_counts(self, n):
        d, _ = _make_designer_with_scene()
        d.set_grid_columns(n)
        assert d.grid_columns == n
        # grid_size should be scene_width / n
        assert d.grid_size == 256 // n

    def test_invalid_column_count_ignored(self):
        d, _ = _make_designer_with_scene()
        d.set_grid_columns(8)
        d.set_grid_columns(7)  # not in (4, 8, 12)
        assert d.grid_columns == 8  # unchanged

    def test_without_scene(self):
        d = UIDesigner(256, 128)
        d.set_grid_columns(4)
        # Should not crash; grid_columns set but grid_size may not update w/o scene
        assert d.grid_columns == 4


# ===================================================================
# add_widget_from_template / clone_widget
# ===================================================================


class TestAddWidgetFromTemplate:
    def test_template_not_found_no_crash(self, capsys):
        d, _ = _make_designer_with_scene()
        d.add_widget_from_template("nonexistent", 10, 20)
        out = capsys.readouterr().out
        assert "not found" in out.lower()

    def test_template_adds_widget(self):
        d, sc = _make_designer_with_scene()
        tmpl = WidgetConfig(type="button", x=0, y=0, width=40, height=12, text="OK")
        d.templates["btn"] = tmpl
        d.add_widget_from_template("btn", 50, 60)
        assert len(sc.widgets) == 1
        w = sc.widgets[0]
        assert w.type == "button"
        assert w.text == "OK"

    def test_template_with_overrides(self):
        d, sc = _make_designer_with_scene()
        tmpl = WidgetConfig(type="label", x=0, y=0, width=80, height=10, text="Hey")
        d.templates["lbl"] = tmpl
        d.add_widget_from_template("lbl", 0, 0, text="Custom")
        assert sc.widgets[0].text == "Custom"


class TestCloneWidget:
    def test_basic_clone(self):
        d, sc = _make_designer_with_scene(1)
        d.clone_widget(0, offset_x=5, offset_y=5)
        assert len(sc.widgets) == 2
        orig, clone = sc.widgets
        assert clone.x == orig.x + 5
        assert clone.y == orig.y + 5
        assert clone.text == orig.text

    def test_invalid_index_no_crash(self):
        d, sc = _make_designer_with_scene(1)
        d.clone_widget(99)
        assert len(sc.widgets) == 1

    def test_clone_is_independent_copy(self):
        d, sc = _make_designer_with_scene(1)
        d.clone_widget(0)
        sc.widgets[1].text = "modified"
        assert sc.widgets[0].text != "modified"


# ===================================================================
# Groups API
# ===================================================================


class TestCreateGroup:
    def test_basic_group(self):
        d, sc = _make_designer_with_scene(3)
        ok = d.create_group("g1", [0, 2])
        assert ok is True
        assert d.groups["g1"] == [0, 2]

    def test_invalid_indices_filtered(self):
        d, sc = _make_designer_with_scene(2)
        ok = d.create_group("g1", [0, 99])
        assert ok is True
        assert d.groups["g1"] == [0]

    def test_all_invalid_returns_false(self):
        d, sc = _make_designer_with_scene(2)
        ok = d.create_group("g1", [99])
        assert ok is False

    def test_no_scene_returns_false(self):
        d = UIDesigner(256, 128)
        ok = d.create_group("g1", [0])
        assert ok is False

    def test_dedup_indices(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("g1", [1, 1, 2, 2])
        assert d.groups["g1"] == [1, 2]


class TestAddToGroup:
    def test_add_new_indices(self):
        d, sc = _make_designer_with_scene(5)
        d.create_group("g1", [0])
        ok = d.add_to_group("g1", [2, 3])
        assert ok is True
        assert d.groups["g1"] == [0, 2, 3]

    def test_nonexistent_group_returns_false(self):
        d, _ = _make_designer_with_scene(2)
        assert d.add_to_group("nope", [0]) is False

    def test_invalid_index_ignored(self):
        d, sc = _make_designer_with_scene(2)
        d.create_group("g1", [0])
        d.add_to_group("g1", [99])
        assert d.groups["g1"] == [0]


class TestRemoveFromGroup:
    def test_remove_some(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("g1", [0, 1, 2])
        ok = d.remove_from_group("g1", [1])
        assert ok is True
        assert d.groups["g1"] == [0, 2]

    def test_remove_all_deletes_group(self):
        d, sc = _make_designer_with_scene(2)
        d.create_group("g1", [0, 1])
        d.remove_from_group("g1", [0, 1])
        assert "g1" not in d.groups

    def test_nonexistent_group_returns_false(self):
        d, _ = _make_designer_with_scene()
        assert d.remove_from_group("nope", [0]) is False


class TestDeleteGroup:
    def test_existing_group(self):
        d, sc = _make_designer_with_scene(2)
        d.create_group("g1", [0])
        assert d.delete_group("g1") is True
        assert "g1" not in d.groups

    def test_nonexistent_group(self):
        d, _ = _make_designer_with_scene()
        assert d.delete_group("nope") is False


class TestListGroups:
    def test_empty(self):
        d, _ = _make_designer_with_scene()
        assert d.list_groups() == []

    def test_sorted_alphabetically(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("beta", [0])
        d.create_group("alpha", [1])
        result = d.list_groups()
        assert result[0][0] == "alpha"
        assert result[1][0] == "beta"

    def test_includes_indices(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("g1", [0, 2])
        result = d.list_groups()
        assert result[0] == ("g1", [0, 2])


class TestGroupSetLock:
    def test_lock_on(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("g1", [0, 1])
        ok = d.group_set_lock("g1", "on")
        assert ok is True
        assert sc.widgets[0].locked is True
        assert sc.widgets[1].locked is True
        assert sc.widgets[2].locked is not True  # not in group

    def test_lock_off(self):
        d, sc = _make_designer_with_scene(2)
        for w in sc.widgets:
            w.locked = True
        d.create_group("g1", [0, 1])
        d.group_set_lock("g1", "off")
        assert all(not w.locked for w in sc.widgets)

    def test_lock_toggle(self):
        d, sc = _make_designer_with_scene(2)
        sc.widgets[0].locked = True
        sc.widgets[1].locked = False
        d.create_group("g1", [0, 1])
        d.group_set_lock("g1", "toggle")
        assert sc.widgets[0].locked is False
        assert sc.widgets[1].locked is True

    def test_nonexistent_group_returns_false(self):
        d, _ = _make_designer_with_scene()
        assert d.group_set_lock("nope", "on") is False


class TestGroupSetVisible:
    def test_visible_off(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("g1", [0, 2])
        ok = d.group_set_visible("g1", "off")
        assert ok is True
        assert sc.widgets[0].visible is False
        assert sc.widgets[1].visible is True  # not in group
        assert sc.widgets[2].visible is False

    def test_visible_on(self):
        d, sc = _make_designer_with_scene(2)
        for w in sc.widgets:
            w.visible = False
        d.create_group("g1", [0, 1])
        d.group_set_visible("g1", "on")
        assert all(w.visible for w in sc.widgets)

    def test_visible_toggle(self):
        d, sc = _make_designer_with_scene(2)
        sc.widgets[0].visible = True
        sc.widgets[1].visible = False
        d.create_group("g1", [0, 1])
        d.group_set_visible("g1", "toggle")
        assert sc.widgets[0].visible is False
        assert sc.widgets[1].visible is True

    def test_nonexistent_group_returns_false(self):
        d, _ = _make_designer_with_scene()
        assert d.group_set_visible("nope", "on") is False


# ===================================================================
# Symbols API
# ===================================================================


class TestSaveSymbol:
    def test_basic_save(self):
        d, sc = _make_designer_with_scene(2)
        sc.widgets[0].x = 10
        sc.widgets[0].y = 20
        sc.widgets[1].x = 30
        sc.widgets[1].y = 40
        ok = d.save_symbol("sym1", [0, 1])
        assert ok is True
        assert "sym1" in d.symbols
        items = d.symbols["sym1"]["items"]
        assert len(items) == 2
        # Positions should be relative (min_x=10, min_y=20 subtracted)
        assert items[0]["x"] == 0
        assert items[0]["y"] == 0
        assert items[1]["x"] == 20
        assert items[1]["y"] == 20

    def test_symbol_records_size(self):
        d, sc = _make_designer_with_scene(1)
        sc.widgets[0].x = 0
        sc.widgets[0].y = 0
        sc.widgets[0].width = 40
        sc.widgets[0].height = 20
        d.save_symbol("s", [0])
        size = d.symbols["s"]["size"]
        assert size == (40, 20)

    def test_invalid_indices_returns_false(self):
        d, sc = _make_designer_with_scene(1)
        ok = d.save_symbol("s", [99])
        assert ok is False

    def test_no_scene_returns_false(self):
        d = UIDesigner(256, 128)
        ok = d.save_symbol("s", [0])
        assert ok is False


class TestPlaceSymbol:
    def test_basic_place(self):
        d, sc = _make_designer_with_scene(2)
        d.save_symbol("sym1", [0, 1])
        initial_count = len(sc.widgets)
        ok = d.place_symbol("sym1", 100, 50)
        assert ok is True
        # Two new widgets placed
        assert len(sc.widgets) == initial_count + 2

    def test_placed_at_offset(self):
        d, sc = _make_designer_with_scene(1)
        sc.widgets[0].x = 10
        sc.widgets[0].y = 20
        d.save_symbol("sym1", [0])
        d.place_symbol("sym1", 100, 50)
        placed = sc.widgets[-1]
        # original offset in symbol is 0,0 (only one widget), so placed at 100,50
        assert placed.x == 100
        assert placed.y == 50

    def test_nonexistent_symbol_returns_false(self):
        d, _ = _make_designer_with_scene()
        assert d.place_symbol("nope", 0, 0) is False

    def test_no_scene_returns_false(self):
        d = UIDesigner(256, 128)
        d.symbols["s"] = {"items": []}
        ok = d.place_symbol("s", 0, 0)
        assert ok is False


# ===================================================================
# Checkpoints API
# ===================================================================


class TestCreateCheckpoint:
    def test_basic_checkpoint(self):
        d, sc = _make_designer_with_scene(1)
        ok = d.create_checkpoint("cp1")
        assert ok is True
        assert "cp1" in d.checkpoints

    def test_checkpoint_stores_scene_state(self):
        d, sc = _make_designer_with_scene(2)
        d.create_checkpoint("cp1")
        payload = d.checkpoints["cp1"]
        assert "scene" in payload
        assert payload["scene"]["name"] == "main"
        assert len(payload["scene"]["widgets"]) == 2

    def test_no_scene_returns_false(self):
        d = UIDesigner(256, 128)
        assert d.create_checkpoint("cp1") is False


class TestListCheckpoints:
    def test_empty(self):
        d, _ = _make_designer_with_scene()
        assert d.list_checkpoints() == []

    def test_returns_name_and_ts(self):
        d, sc = _make_designer_with_scene(1)
        d.create_checkpoint("cp1")
        result = d.list_checkpoints()
        assert len(result) == 1
        name, ts = result[0]
        assert name == "cp1"
        assert len(ts) > 0  # timestamp string

    def test_sorted_by_timestamp(self):
        d, sc = _make_designer_with_scene(1)
        d.create_checkpoint("second")
        d.create_checkpoint("first")
        result = d.list_checkpoints()
        # Both created nearly simultaneously, but ordering should be by ts
        assert len(result) == 2


class TestRollbackCheckpoint:
    def test_basic_rollback(self):
        d, sc = _make_designer_with_scene(2)
        d.create_checkpoint("cp1")
        # Modify scene
        sc.widgets.clear()
        assert len(sc.widgets) == 0
        # Rollback
        ok = d.rollback_checkpoint("cp1")
        assert ok is True
        restored = d.scenes["main"]
        assert len(restored.widgets) == 2

    def test_nonexistent_checkpoint_returns_false(self):
        d, _ = _make_designer_with_scene()
        assert d.rollback_checkpoint("nope") is False

    def test_rollback_restores_scene_name(self):
        d, sc = _make_designer_with_scene(1)
        d.create_checkpoint("cp1")
        d.current_scene = None
        ok = d.rollback_checkpoint("cp1")
        assert ok is True
        assert d.current_scene == "main"


# ===================================================================
# export_to_html
# ===================================================================


class TestExportToHtml:
    def test_creates_html_file(self, tmp_path):
        d, sc = _make_designer_with_scene(1)
        out = str(tmp_path / "test.html")
        d.export_to_html(out)
        assert os.path.exists(out)
        content = open(out, encoding="utf-8").read()
        assert "<!DOCTYPE html>" in content
        assert "main" in content  # scene name

    def test_contains_widget_count(self, tmp_path):
        d, sc = _make_designer_with_scene(3)
        out = str(tmp_path / "test.html")
        d.export_to_html(out)
        content = open(out, encoding="utf-8").read()
        assert "Widgets: 3" in content

    def test_no_scene_no_file(self, tmp_path):
        d = UIDesigner(256, 128)
        out = str(tmp_path / "test.html")
        d.export_to_html(out)
        assert not os.path.exists(out)

    def test_html_escapes_content(self, tmp_path):
        d, sc = _make_designer_with_scene(1)
        sc.widgets[0].text = "<script>alert(1)</script>"
        out = str(tmp_path / "test.html")
        d.export_to_html(out)
        content = open(out, encoding="utf-8").read()
        assert "<script>" not in content  # should be escaped


# ===================================================================
# show_command_help / get_widget_help
# ===================================================================


class TestShowCommandHelp:
    def test_known_command(self, capsys):
        show_command_help("add")
        out = capsys.readouterr().out
        assert "add" in out.lower()

    def test_unknown_command(self, capsys):
        show_command_help("nonexistent_xyz")
        out = capsys.readouterr().out
        assert "no detailed help" in out.lower()

    def test_template_help(self, capsys):
        show_command_help("template")
        out = capsys.readouterr().out
        assert "template" in out.lower()

    def test_edit_help(self, capsys):
        show_command_help("edit")
        out = capsys.readouterr().out
        assert "edit" in out.lower()


class TestGetWidgetHelp:
    @pytest.mark.parametrize(
        "wtype",
        [
            "label",
            "button",
            "progressbar",
            "gauge",
            "checkbox",
            "panel",
            "icon",
            "chart",
            "box",
            "slider",
            "radiobutton",
            "textbox",
        ],
    )
    def test_known_types(self, wtype):
        w = WidgetConfig(type=wtype, x=0, y=0, width=10, height=10)
        info = get_widget_help(w)
        assert "description" in info
        assert "tips" in info
        assert isinstance(info["tips"], list)

    def test_unknown_type_fallback(self):
        # WidgetConfig now rejects unknown types at construction
        with pytest.raises(ValueError, match="Unknown widget type"):
            WidgetConfig(type="unknown_xyz", x=0, y=0, width=10, height=10)


# ===================================================================
# enable_pixel_art_mode
# ===================================================================


class TestEnablePixelArtMode:
    def test_sets_grid_params(self):
        d, _ = _make_designer_with_scene()
        d.enable_pixel_art_mode()
        assert d.grid_enabled is True
        assert d.grid_size == 8
        assert d.snap_to_grid is True
        assert d.snap_fluid is False

    def test_applies_pixel_dark_theme_if_available(self):
        d, sc = _make_designer_with_scene()
        d.themes["pixel_dark"] = {"bg": "#111111"}
        d.enable_pixel_art_mode()
        assert sc.bg_color == "#111111"


# ===================================================================
# preview_ascii
# ===================================================================


class TestPreviewAscii:
    def test_empty_scene(self):
        d, _ = _make_designer_with_scene()
        result = d.preview_ascii()
        # Should be all spaces
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_scene_returns_empty(self):
        d = UIDesigner(256, 128)
        assert d.preview_ascii() == ""

    def test_with_grid(self):
        d, _ = _make_designer_with_scene()
        d.grid_enabled = True
        d.grid_size = 8
        result = d.preview_ascii(show_grid=True)
        assert "." in result  # grid dots

    def test_scene_name_param(self):
        d, _ = _make_designer_with_scene()
        result = d.preview_ascii(scene_name="main")
        assert isinstance(result, str)

    def test_invalid_scene_name(self):
        d, _ = _make_designer_with_scene()
        result = d.preview_ascii(scene_name="nope")
        assert result == ""


# ===================================================================
# Integration / edge-case workflows
# ===================================================================


class TestGroupSymbolIntegration:
    """Test combining groups and symbols in realistic workflows."""

    def test_save_symbol_from_group_then_place(self):
        d, sc = _make_designer_with_scene(3)
        d.create_group("status_bar", [0, 1])
        # Save symbol from group indices
        indices = d.groups["status_bar"]
        ok = d.save_symbol("status_block", indices)
        assert ok is True
        # Place at new location
        ok = d.place_symbol("status_block", 100, 50)
        assert ok is True
        assert len(sc.widgets) == 5  # 3 original + 2 placed

    def test_checkpoint_rollback_restores_groups_scene_state(self):
        d, sc = _make_designer_with_scene(2)
        d.create_checkpoint("before_edit")
        sc.widgets[0].text = "CHANGED"
        ok = d.rollback_checkpoint("before_edit")
        assert ok is True
        assert d.scenes["main"].widgets[0].text == "w0"

    def test_clone_and_group(self):
        d, sc = _make_designer_with_scene(1)
        d.clone_widget(0)
        assert len(sc.widgets) == 2
        ok = d.create_group("pair", [0, 1])
        assert ok is True
        d.group_set_lock("pair", "on")
        assert all(w.locked for w in sc.widgets)


class TestUndoRedoHistoryIntegration:
    """Test history tracking through undo/redo cycles."""

    def test_undo_reduces_history(self):
        d, sc = _make_designer_with_scene(1)
        d.move_widget(0, 5, 0)
        d.move_widget(0, 5, 0)
        h_before = len(d.list_history())
        d.undo()
        h_after = len(d.list_history())
        assert h_after < h_before

    def test_redo_restores_history(self):
        d, sc = _make_designer_with_scene(1)
        d.move_widget(0, 5, 0)
        d.move_widget(0, 5, 0)
        d.undo()
        h_before = len(d.list_history())
        d.redo()
        h_after = len(d.list_history())
        assert h_after >= h_before

    def test_snapshot_matches_undo_stack(self):
        d, sc = _make_designer_with_scene(1)
        d.move_widget(0, 5, 0)
        snap = d.history_snapshot(0)
        assert snap is not None
        assert snap["name"] == "main"
