"""Tests for validation rules 130-132 in tools/validate_design.py.

Rule 130: LIST items must be a list of strings
Rule 131: LIST with no text and no items
Rule 132: items on non-list widget
"""

from tools.validate_design import validate_data

FL = "test"


def _make(widgets, *, scene_w=128, scene_h=64, scene_name="main"):
    return {
        "scenes": {
            scene_name: {
                "width": scene_w,
                "height": scene_h,
                "widgets": widgets,
            }
        }
    }


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _errors(data, **kw):
    return [i for i in _issues(data, **kw) if i.level == "ERROR"]


def _warns(data, **kw):
    return [i for i in _issues(data, **kw) if i.level == "WARN"]


# ── Rule 130: LIST items must be a list of strings ────────────────────


def test_r130_valid_items_no_error():
    d = _make(
        [
            {
                "type": "list",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 40,
                "items": ["Alpha", "Beta", "Gamma"],
            },
        ]
    )
    es = [e for e in _errors(d) if "items" in e.message]
    assert es == []


def test_r130_items_not_list_errors():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "items": "not a list"},
        ]
    )
    es = [e for e in _errors(d) if "items field must be a list" in e.message]
    assert len(es) == 1


def test_r130_items_contains_non_string_errors():
    d = _make(
        [
            {
                "type": "list",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 40,
                "items": ["ok", 42, "also_ok"],
            },
        ]
    )
    es = [e for e in _errors(d) if "items[1] must be a string" in e.message]
    assert len(es) == 1


def test_r130_items_first_non_string_reported():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "items": [123, 456]},
        ]
    )
    es = [e for e in _errors(d) if "items[0]" in e.message]
    assert len(es) == 1


def test_r130_empty_items_no_error():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "items": []},
        ]
    )
    es = [e for e in _errors(d) if "items" in e.message and "must be" in e.message]
    assert es == []


def test_r130_items_none_no_error():
    """items=None should not trigger Rule 130 (treated as absent)."""
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "text": "A\nB"},
        ]
    )
    es = [e for e in _errors(d) if "items" in e.message and "must be" in e.message]
    assert es == []


# ── Rule 131: LIST with no text and no items ──────────────────────────


def test_r131_list_no_text_no_items_warns():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40},
        ]
    )
    ws = [w for w in _warns(d) if "no text and no items" in w.message]
    assert len(ws) == 1


def test_r131_list_with_text_no_warn():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "text": "A\nB"},
        ]
    )
    ws = [w for w in _warns(d) if "no text and no items" in w.message]
    assert ws == []


def test_r131_list_with_items_no_warn():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "items": ["A", "B"]},
        ]
    )
    ws = [w for w in _warns(d) if "no text and no items" in w.message]
    assert ws == []


def test_r131_list_empty_text_and_empty_items_warns():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "text": "", "items": []},
        ]
    )
    ws = [w for w in _warns(d) if "no text and no items" in w.message]
    assert len(ws) == 1


# ── Rule 132: items on non-list widget ────────────────────────────────


def test_r132_items_on_label_warns():
    d = _make(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 16,
                "text": "hi",
                "items": ["A", "B"],
            },
        ]
    )
    ws = [w for w in _warns(d) if "items field on non-list" in w.message]
    assert len(ws) == 1


def test_r132_items_on_button_warns():
    d = _make(
        [
            {
                "type": "button",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 16,
                "text": "ok",
                "items": ["X"],
            },
        ]
    )
    ws = [w for w in _warns(d) if "items field on non-list" in w.message]
    assert len(ws) == 1


def test_r132_empty_items_on_label_no_warn():
    d = _make(
        [
            {"type": "label", "x": 0, "y": 0, "width": 80, "height": 16, "text": "hi", "items": []},
        ]
    )
    ws = [w for w in _warns(d) if "items field on non-list" in w.message]
    assert ws == []


def test_r132_items_on_list_no_warn():
    d = _make(
        [
            {"type": "list", "x": 0, "y": 0, "width": 80, "height": 40, "items": ["A", "B"]},
        ]
    )
    ws = [w for w in _warns(d) if "items field on non-list" in w.message]
    assert ws == []


# ── Rule 83 toggle fix verification ──────────────────────────────────


def test_r83_checked_on_toggle_ok():
    """toggle with checked=true should NOT trigger Rule 83 warning."""
    d = _make(
        [
            {
                "type": "toggle",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "text": "WiFi",
                "checked": True,
            },
        ]
    )
    ws = [w for w in _warns(d) if "checked=true" in w.message and "non-checkbox" in w.message]
    assert ws == []


# ── Rule 109 toggle fix verification ─────────────────────────────────


def test_r109_disabled_checked_toggle_no_runtime_warns():
    """disabled+checked toggle without runtime should warn (stuck state)."""
    d = _make(
        [
            {
                "type": "toggle",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "text": "WiFi",
                "checked": True,
                "enabled": False,
            },
        ]
    )
    ws = [w for w in _warns(d) if "stuck state" in w.message]
    assert len(ws) == 1


def test_r109_disabled_checked_toggle_with_runtime_ok():
    d = _make(
        [
            {
                "type": "toggle",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "text": "WiFi",
                "checked": True,
                "enabled": False,
                "runtime": "bind=wifi_toggle",
            },
        ]
    )
    ws = [w for w in _warns(d) if "stuck state" in w.message]
    assert ws == []
