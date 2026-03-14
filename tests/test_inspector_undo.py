"""Tests for undo/redo integration with inspector commit.

Verifies that inspector field commits call _save_state() and that
app.designer.undo() correctly restores previous widget state.
"""

from __future__ import annotations

from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


def _commit(app, field, buf):
    app.state.inspector_selected_field = field
    app.state.inspector_input_buffer = buf
    return app._inspector_commit_edit()


# ── Position undo ──────────────────────────────────────────────────────


class TestUndoPosition:
    def test_position_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=10, y=20)
        _sel(app, 0)
        _commit(app, "_position", "50,60")
        assert w.x == 50 and w.y == 60
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 10
        assert sc.widgets[0].y == 20

    def test_position_redo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20)
        _sel(app, 0)
        _commit(app, "_position", "50,60")
        app.designer.undo()
        app.designer.redo()
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 50
        assert sc.widgets[0].y == 60


# ── z_index undo ──────────────────────────────────────────────────────


class TestUndoZindex:
    def test_single_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, z_index=0)
        _sel(app, 0)
        _commit(app, "z_index", "5")
        sc = app.state.current_scene()
        assert sc.widgets[0].z_index == 5
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].z_index == 0

    def test_multi_select(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, z_index=1)
        _add(app, z_index=2)
        _sel(app, 0, 1)
        _commit(app, "z_index", "10")
        sc = app.state.current_scene()
        assert sc.widgets[0].z_index == 10
        assert sc.widgets[1].z_index == 10
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].z_index == 1
        assert sc.widgets[1].z_index == 2


# ── value undo ────────────────────────────────────────────────────────


class TestUndoValue:
    def test_value_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="slider", value=30, width=80, height=16)
        _sel(app, 0)
        _commit(app, "value", "75")
        sc = app.state.current_scene()
        assert sc.widgets[0].value == 75
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].value == 30

    def test_multi_value_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="slider", value=10, width=80, height=16)
        _add(app, type="gauge", value=20, width=80, height=16)
        _sel(app, 0, 1)
        _commit(app, "value", "50")
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].value == 10
        assert sc.widgets[1].value == 20


# ── checked undo ──────────────────────────────────────────────────────


class TestUndoChecked:
    def test_checked_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False, width=14, height=14)
        _sel(app, 0)
        _commit(app, "checked", "true")
        sc = app.state.current_scene()
        assert sc.widgets[0].checked is True
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].checked is False

    def test_multi_checked_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=True, width=14, height=14, text="a")
        _add(app, type="toggle", checked=False, width=60, height=14, text="b")
        _sel(app, 0, 1)
        _commit(app, "checked", "false")
        sc = app.state.current_scene()
        assert sc.widgets[0].checked is False
        assert sc.widgets[1].checked is False
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].checked is True
        assert sc.widgets[1].checked is False


# ── text undo ─────────────────────────────────────────────────────────


class TestUndoText:
    def test_text_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="hello")
        _sel(app, 0)
        _commit(app, "text", "world")
        sc = app.state.current_scene()
        assert sc.widgets[0].text == "world"
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].text == "hello"


# ── color undo ────────────────────────────────────────────────────────


class TestUndoColor:
    def test_color_fg_undo(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="white")
        _sel(app, 0)
        _commit(app, "color_fg", "#FF0000")
        sc = app.state.current_scene()
        assert sc.widgets[0].color_fg == "#FF0000"
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].color_fg == "white"


# ── multiple undo steps ──────────────────────────────────────────────


class TestMultipleUndoSteps:
    def test_two_edits_two_undos(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0)
        _sel(app, 0)
        _commit(app, "_position", "10,10")
        _commit(app, "_position", "20,20")
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 20
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 10
        app.designer.undo()
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 0

    def test_undo_no_stack_returns_false(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        assert app.designer.undo() is False


# ── undo preserves widget count ──────────────────────────────────────


class TestUndoWidgetCount:
    def test_undo_preserves_count(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A")
        _add(app, text="B")
        _sel(app, 0, 1)
        _commit(app, "z_index", "5")
        app.designer.undo()
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
