"""Tests for query_select.py — uncovered functions and guard branches.

Covers: select_same_type_as_current, select_unlocked, select_disabled,
select_largest, select_smallest, plus guard branches for search_widgets,
select_same_z, select_same_style, select_hidden, select_same_type,
select_locked, select_same_color, select_parent_panel, select_children,
select_same_size, select_bordered, select_overlapping, invert_selection,
select_all_panels.
"""

from __future__ import annotations

from cyberpunk_designer.selection_ops.query_select import (
    invert_selection,
    search_widgets,
    select_all_panels,
    select_bordered,
    select_children,
    select_disabled,
    select_hidden,
    select_largest,
    select_locked,
    select_overlapping,
    select_parent_panel,
    select_same_color,
    select_same_size,
    select_same_style,
    select_same_type,
    select_same_type_as_current,
    select_same_z,
    select_smallest,
    select_unlocked,
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
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None
    if indices:
        app.designer.selected_widget = indices[0]


# ===========================================================================
# select_same_type_as_current
# ===========================================================================

class TestSelectSameTypeAsCurrent:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        _sel(app, 0)
        select_same_type_as_current(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app)
        select_same_type_as_current(app)  # no crash


# ===========================================================================
# select_unlocked
# ===========================================================================

class TestSelectUnlocked:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=False)
        _add(app, locked=True)
        _add(app, locked=False)
        select_unlocked(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected

    def test_all_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=True)
        select_unlocked(app)  # none found


# ===========================================================================
# select_disabled
# ===========================================================================

class TestSelectDisabled:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, enabled=False)
        _add(app, enabled=True)
        _add(app, enabled=False)
        select_disabled(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected

    def test_all_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, enabled=True)
        select_disabled(app)  # none found


# ===========================================================================
# select_largest
# ===========================================================================

class TestSelectLargest:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=10, height=10)  # area=100
        _add(app, width=50, height=50)  # area=2500
        _add(app, width=20, height=20)  # area=400
        select_largest(app)
        assert app.state.selected == [1]

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_largest(app)  # no crash


# ===========================================================================
# select_smallest
# ===========================================================================

class TestSelectSmallest:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=50, height=50)  # area=2500
        _add(app, width=10, height=10)  # area=100
        _add(app, width=20, height=20)  # area=400
        select_smallest(app)
        assert app.state.selected == [1]

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_smallest(app)  # no crash


# ===========================================================================
# Guard branches for existing functions
# ===========================================================================

class TestSearchWidgetsGuards:
    def test_empty_query(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Hello")
        search_widgets(app, "")  # empty query — early return

    def test_no_match(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Hello")
        search_widgets(app, "zzz_no_match")
        assert not app.state.selected


class TestSelectSameZGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, z_index=0)
        _sel(app)
        select_same_z(app)  # no crash

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, z_index=0)
        _add(app, z_index=1)
        _add(app, z_index=0)
        _sel(app, 0)
        select_same_z(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected


class TestSelectSameStyleGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        select_same_style(app)  # no crash

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="default")
        _add(app, style="bold")
        _add(app, style="default")
        _sel(app, 0)
        select_same_style(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected


class TestSelectHiddenGuards:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_hidden(app)  # no crash

    def test_no_hidden(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, visible=True)
        select_hidden(app)  # no hidden — status message

    def test_has_hidden(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, visible=True)
        w = _add(app, visible=True)
        w.visible = False
        select_hidden(app)
        assert 1 in app.state.selected


class TestSelectSameTypeGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        select_same_type(app)  # no crash

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        _sel(app, 0)
        select_same_type(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected


class TestSelectLockedGuards:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_locked(app)  # no crash

    def test_selects_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=True)
        _add(app, locked=False)
        select_locked(app)
        assert 0 in app.state.selected

    def test_from_locked_selects_unlocked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=True)
        _add(app, locked=False)
        _sel(app, 0)  # current sel is all-locked
        select_locked(app)
        assert 1 in app.state.selected  # selects unlocked instead


class TestSelectOverlappingGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        select_overlapping(app)  # no crash

    def test_no_overlaps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=10, height=10)
        _add(app, x=100, y=100, width=10, height=10)
        _sel(app, 0)
        select_overlapping(app)  # no overlaps found


class TestInvertSelectionGuards:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        invert_selection(app)  # no crash

    def test_all_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        invert_selection(app)
        assert app.state.selected == []


class TestSelectSameColorGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        select_same_color(app)  # no crash

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="white", color_bg="black")
        _add(app, color_fg="red", color_bg="black")
        _add(app, color_fg="white", color_bg="black")
        _sel(app, 0)
        select_same_color(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected


class TestSelectParentPanelGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _sel(app)
        select_parent_panel(app)  # no crash

    def test_no_parent(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=10, height=10)
        _sel(app, 0)
        select_parent_panel(app)  # no enclosing panel

    def test_has_parent(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=100, height=100)
        _add(app, type="label", x=10, y=10, width=20, height=10)
        _sel(app, 1)
        select_parent_panel(app)
        assert 0 in app.state.selected


class TestSelectChildrenGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _sel(app)
        select_children(app)  # no crash

    def test_not_a_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        select_children(app)  # not a panel

    def test_has_children(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=100, height=100)
        _add(app, type="label", x=10, y=10, width=20, height=10)
        _add(app, type="label", x=200, y=200, width=10, height=10)  # outside
        _sel(app, 0)
        select_children(app)
        assert 1 in app.state.selected
        assert 2 not in app.state.selected

    def test_no_children(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=10, height=10)
        _sel(app, 0)
        select_children(app)  # no children inside


class TestSelectSameSizeGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        select_same_size(app)  # no crash

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=10)
        _add(app, width=30, height=30)
        _add(app, width=20, height=10)
        _sel(app, 0)
        select_same_size(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected


class TestSelectBorderedGuards:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_bordered(app)  # no crash

    def test_no_bordered(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, border=False)
        w.border = False
        select_bordered(app)


class TestSelectAllPanelsGuards:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_all_panels(app)  # no crash

    def test_no_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        select_all_panels(app)

    def test_has_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="panel")
        select_all_panels(app)
        assert 1 in app.state.selected
