"""Tests for _cycle_widget_selection in cyberpunk_designer/input_handlers.py."""

from types import SimpleNamespace

from cyberpunk_designer.input_handlers import _cycle_widget_selection


def _widget(name="w"):
    return SimpleNamespace(type="label", x=0, y=0, width=50, height=12, text=name,
                           visible=True)


def _app(n_widgets=3, selected_idx=None, selected=None):
    widgets = [_widget(f"w{i}") for i in range(n_widgets)]
    scene = SimpleNamespace(widgets=widgets)
    state = SimpleNamespace(
        selected_idx=selected_idx,
        selected=selected or ([selected_idx] if selected_idx is not None else []),
    )
    state.current_scene = lambda: scene

    selections = []
    dirty = []

    def set_sel(sel, anchor_idx=None):
        state.selected = list(sel)
        state.selected_idx = anchor_idx
        selections.append((list(sel), anchor_idx))

    def mark_dirty():
        dirty.append(True)

    app = SimpleNamespace(state=state, _set_selection=set_sel, _mark_dirty=mark_dirty)
    app._selections = selections
    app._dirty_calls = dirty
    return app


# ── forward cycling ───────────────────────────────────────────────────


def test_cycle_forward_from_0():
    app = _app(n_widgets=3, selected_idx=0)
    _cycle_widget_selection(app, direction=1)
    assert app.state.selected == [1]
    assert app.state.selected_idx == 1


def test_cycle_forward_wraps():
    app = _app(n_widgets=3, selected_idx=2)
    _cycle_widget_selection(app, direction=1)
    assert app.state.selected == [0]


def test_cycle_forward_no_selection():
    app = _app(n_widgets=3, selected_idx=None)
    _cycle_widget_selection(app, direction=1)
    assert app.state.selected == [0]


# ── backward cycling ─────────────────────────────────────────────────


def test_cycle_backward_from_1():
    app = _app(n_widgets=3, selected_idx=1)
    _cycle_widget_selection(app, direction=-1)
    assert app.state.selected == [0]


def test_cycle_backward_wraps():
    app = _app(n_widgets=3, selected_idx=0)
    _cycle_widget_selection(app, direction=-1)
    assert app.state.selected == [2]


def test_cycle_backward_no_selection():
    app = _app(n_widgets=3, selected_idx=None)
    _cycle_widget_selection(app, direction=-1)
    assert app.state.selected == [2]


# ── extend mode ──────────────────────────────────────────────────────


def test_cycle_extend_adds():
    app = _app(n_widgets=3, selected_idx=0, selected=[0])
    _cycle_widget_selection(app, direction=1, extend=True)
    assert 0 in app.state.selected
    assert 1 in app.state.selected
    assert len(app.state.selected) == 2


def test_cycle_extend_no_duplicate():
    app = _app(n_widgets=3, selected_idx=0, selected=[0, 1])
    _cycle_widget_selection(app, direction=1, extend=True)
    assert app.state.selected.count(1) == 1


# ── edge cases ───────────────────────────────────────────────────────


def test_cycle_empty_scene():
    app = _app(n_widgets=0, selected_idx=None)
    _cycle_widget_selection(app, direction=1)
    # Should not crash; no selection change
    assert app._selections == []


def test_cycle_single_widget():
    app = _app(n_widgets=1, selected_idx=0)
    _cycle_widget_selection(app, direction=1)
    assert app.state.selected == [0]


def test_cycle_marks_dirty():
    app = _app(n_widgets=3, selected_idx=0)
    _cycle_widget_selection(app, direction=1)
    assert len(app._dirty_calls) == 1
