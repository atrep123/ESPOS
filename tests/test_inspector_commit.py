"""Focused unit tests for inspector_commit helper functions."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from types import SimpleNamespace

import pygame

from cyberpunk_designer.inspector_commit import (
    _commit_choice,
    _commit_color,
    _commit_epilogue,
    _commit_str_attr,
    _parse_active_count,
    _parse_pair,
    _sorted_role_indices,
)


class _Designer:
    def __init__(self) -> None:
        self.saved = 0

    def _save_state(self) -> None:
        self.saved += 1


class _Widget(SimpleNamespace):
    pass


def _make_app() -> SimpleNamespace:
    app = SimpleNamespace()
    app.designer = _Designer()
    app.state = SimpleNamespace(inspector_selected_field="field", inspector_input_buffer="value")
    app.status_calls = []
    app.dirty_count = 0

    def _set_status(msg: str, ttl_sec: float = 0.0) -> None:
        app.status_calls.append((msg, ttl_sec))

    def _mark_dirty() -> None:
        app.dirty_count += 1

    app._set_status = _set_status
    app._mark_dirty = _mark_dirty
    app._is_valid_color_str = lambda s: isinstance(s, str) and s.startswith("#") and len(s) == 7
    return app


def test_commit_choice_returns_none_for_unknown_field() -> None:
    app = _make_app()
    w = _Widget(align="left")

    result = _commit_choice(app, "unknown", "center", [w])

    assert result is None
    assert app.designer.saved == 0


def test_commit_choice_rejects_invalid_value() -> None:
    app = _make_app()
    w = _Widget(align="left")

    result = _commit_choice(app, "align", "bad", [w])

    assert result is False
    assert w.align == "left"
    assert app.designer.saved == 0
    assert "align must be" in app.status_calls[-1][0]


def test_commit_choice_applies_to_all_targets() -> None:
    app = _make_app()
    w0 = _Widget(align="left")
    w1 = _Widget(align="left")

    result = _commit_choice(app, "align", "CENTER", [w0, w1])

    assert result is True
    assert w0.align == "center"
    assert w1.align == "center"
    assert app.designer.saved == 1


def test_commit_str_attr_text_and_runtime() -> None:
    app = _make_app()
    w = _Widget(text="old", runtime="old")

    assert _commit_str_attr(app, "text", "Hello", [w]) is True
    assert w.text == "Hello"
    assert app.designer.saved == 1

    assert _commit_str_attr(app, "runtime", "sensor.temp", [w]) is True
    assert w.runtime == "sensor.temp"
    assert app.designer.saved == 2


def test_commit_str_attr_returns_none_for_other_fields() -> None:
    app = _make_app()
    w = _Widget()

    assert _commit_str_attr(app, "style", "bold", [w]) is None
    assert app.designer.saved == 0


def test_commit_color_rejects_invalid_value() -> None:
    app = _make_app()
    w = _Widget(color_fg="#ffffff")

    result = _commit_color(app, "color_fg", "red", [w])

    assert result is False
    assert w.color_fg == "#ffffff"
    assert app.designer.saved == 0
    assert "Invalid color_fg" in app.status_calls[-1][0]


def test_commit_color_accepts_valid_value() -> None:
    app = _make_app()
    w = _Widget(color_bg="#000000")

    result = _commit_color(app, "color_bg", "#112233", [w])

    assert result is True
    assert w.color_bg == "#112233"
    assert app.designer.saved == 1


def test_commit_color_returns_none_for_non_color_field() -> None:
    app = _make_app()
    w = _Widget()

    assert _commit_color(app, "text", "#abcdef", [w]) is None
    assert app.designer.saved == 0


def test_parse_pair_supports_comma_and_space() -> None:
    assert _parse_pair("10,20") == (10, 20)
    assert _parse_pair("30 40") == (30, 40)


def test_parse_pair_returns_none_on_invalid_input() -> None:
    assert _parse_pair("single") is None
    assert _parse_pair("a,b") is None
    assert _parse_pair("12;") is None


def test_commit_epilogue_clears_input_and_marks_dirty(monkeypatch) -> None:
    app = _make_app()

    def _raise_error() -> None:
        raise pygame.error("not initialized")

    monkeypatch.setattr(pygame.key, "stop_text_input", _raise_error)

    result = _commit_epilogue(app, "Done")

    assert result is True
    assert app.state.inspector_selected_field is None
    assert app.state.inspector_input_buffer == ""
    assert app.dirty_count == 1
    assert app.status_calls[-1][0] == "Done"


def test_parse_active_count_basic_cases() -> None:
    assert _parse_active_count("3/7") == (2, 7)
    assert _parse_active_count("9/4") == (3, 4)
    assert _parse_active_count("x/y") is None
    assert _parse_active_count("1/0") == (0, 0)


def test_sorted_role_indices_orders_numeric_suffix() -> None:
    roles = {"item10": 10, "item2": 2, "item1": 1, "other": 99, "itemx": 77}

    assert _sorted_role_indices(roles, "item") == [(1, 1), (2, 2), (10, 10)]
