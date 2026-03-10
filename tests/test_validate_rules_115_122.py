"""Tests for validation rules 115-122."""

from __future__ import annotations

from tools.validate_design import validate_data


def _make(widgets, *, sw=256, sh=128, scene_name="s"):
    return {
        "scenes": {
            scene_name: {"width": sw, "height": sh, "widgets": widgets},
        }
    }


def _errs(data):
    return [
        i
        for i in validate_data(data, file_label="test", warnings_as_errors=False)
        if i.level == "ERROR"
    ]


def _warns(data):
    return [
        i
        for i in validate_data(data, file_label="test", warnings_as_errors=False)
        if i.level == "WARN"
    ]


# ---------------------------------------------------------------------------
# Rule 115: scene has no focusable widgets
# ---------------------------------------------------------------------------


class TestRule115:
    def test_no_widgets(self):
        d = _make([])
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert ws == []  # empty scene — no warning (no widgets at all)

    def test_only_labels(self):
        d = _make(
            [
                {"type": "label", "x": 0, "y": 0, "width": 80, "height": 16, "text": "Hi"},
                {"type": "label", "x": 0, "y": 20, "width": 80, "height": 16, "text": "There"},
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert len(ws) == 1

    def test_has_button(self):
        d = _make(
            [
                {"type": "label", "x": 0, "y": 0, "width": 80, "height": 16, "text": "Hi"},
                {"type": "button", "x": 0, "y": 20, "width": 80, "height": 16, "text": "OK"},
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert ws == []

    def test_has_checkbox(self):
        d = _make(
            [
                {"type": "checkbox", "x": 0, "y": 0, "width": 80, "height": 16, "text": "On"},
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert ws == []

    def test_has_slider(self):
        d = _make(
            [
                {
                    "type": "slider",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert ws == []

    def test_has_radiobutton(self):
        d = _make(
            [
                {"type": "radiobutton", "x": 0, "y": 0, "width": 80, "height": 16, "text": "A"},
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert ws == []

    def test_focusable_but_invisible(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "visible": False,
                },
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert len(ws) == 1

    def test_focusable_but_disabled(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "enabled": False,
                },
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert len(ws) == 1

    def test_only_panels_and_boxes(self):
        d = _make(
            [
                {"type": "panel", "x": 0, "y": 0, "width": 100, "height": 50},
                {"type": "box", "x": 10, "y": 10, "width": 40, "height": 30},
            ]
        )
        ws = [w for w in _warns(d) if "no focusable" in w.message]
        assert len(ws) == 1


# ---------------------------------------------------------------------------
# Rule 116: chart min_value >= max_value
# ---------------------------------------------------------------------------


class TestRule116:
    def test_chart_valid_range(self):
        d = _make(
            [
                {
                    "type": "chart",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 40,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        es = [e for e in _errs(d) if "chart" in e.message and "min_value" in e.message]
        assert es == []

    def test_chart_min_eq_max(self):
        d = _make(
            [
                {
                    "type": "chart",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 40,
                    "min_value": 50,
                    "max_value": 50,
                },
            ]
        )
        es = [e for e in _errs(d) if "chart" in e.message and "min_value" in e.message]
        assert len(es) == 1

    def test_chart_min_gt_max(self):
        d = _make(
            [
                {
                    "type": "chart",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 40,
                    "min_value": 100,
                    "max_value": 50,
                },
            ]
        )
        es = [e for e in _errs(d) if "chart" in e.message and "min_value" in e.message]
        assert len(es) == 1

    def test_chart_defaults_ok(self):
        """Default min=0 max=100 should be fine."""
        d = _make(
            [
                {"type": "chart", "x": 0, "y": 0, "width": 80, "height": 40},
            ]
        )
        es = [e for e in _errs(d) if "chart" in e.message and "min_value" in e.message]
        assert es == []

    def test_gauge_not_affected(self):
        """Rule 9 handles gauges; rule 116 only applies to charts."""
        d = _make(
            [
                {
                    "type": "gauge",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 40,
                    "min_value": 100,
                    "max_value": 50,
                },
            ]
        )
        es = [e for e in _errs(d) if "chart" in e.message and "min_value" in e.message]
        assert es == []


# ---------------------------------------------------------------------------
# Rule 117: progressbar height too small
# ---------------------------------------------------------------------------


class TestRule117:
    def test_progressbar_height_ok(self):
        d = _make(
            [
                {
                    "type": "progressbar",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 10,
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "progressbar" in w.message and "fill" in w.message]
        assert ws == []

    def test_progressbar_height_3_ok(self):
        d = _make(
            [
                {
                    "type": "progressbar",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 3,
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "progressbar" in w.message and "fill" in w.message]
        assert ws == []

    def test_progressbar_height_2(self):
        d = _make(
            [
                {
                    "type": "progressbar",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 2,
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "progressbar" in w.message and "fill" in w.message]
        assert len(ws) == 1

    def test_progressbar_height_1(self):
        d = _make(
            [
                {
                    "type": "progressbar",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 1,
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "progressbar" in w.message and "fill" in w.message]
        assert len(ws) == 1


# ---------------------------------------------------------------------------
# Rule 118: constraints unrecognized keys
# ---------------------------------------------------------------------------


class TestRule118:
    def test_valid_keys(self):
        d = _make(
            [
                {
                    "type": "label",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "Hi",
                    "constraints": {"ax": "center", "sy": True},
                },
            ]
        )
        ws = [w for w in _warns(d) if "unrecognized keys" in w.message]
        assert ws == []

    def test_all_valid_keys(self):
        d = _make(
            [
                {
                    "type": "label",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "Hi",
                    "constraints": {
                        "b": "top",
                        "ax": "c",
                        "ay": "m",
                        "sx": True,
                        "sy": False,
                        "mx": 5,
                        "my": 5,
                        "mr": 10,
                        "mb": 10,
                    },
                },
            ]
        )
        ws = [w for w in _warns(d) if "unrecognized keys" in w.message]
        assert ws == []

    def test_typo_key(self):
        d = _make(
            [
                {
                    "type": "label",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "Hi",
                    "constraints": {"xa": "center"},
                },
            ]
        )
        ws = [w for w in _warns(d) if "unrecognized keys" in w.message]
        assert len(ws) == 1
        assert "xa" in ws[0].message

    def test_empty_constraints_ok(self):
        d = _make(
            [
                {
                    "type": "label",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "Hi",
                    "constraints": {},
                },
            ]
        )
        ws = [w for w in _warns(d) if "unrecognized keys" in w.message]
        assert ws == []

    def test_multiple_bad_keys(self):
        d = _make(
            [
                {
                    "type": "label",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "Hi",
                    "constraints": {"foo": 1, "bar": 2, "ax": "c"},
                },
            ]
        )
        ws = [w for w in _warns(d) if "unrecognized keys" in w.message]
        assert len(ws) == 1
        assert "bar" in ws[0].message
        assert "foo" in ws[0].message


# ---------------------------------------------------------------------------
# Rule 119: icon too small for bitmap
# ---------------------------------------------------------------------------


class TestRule119:
    def test_icon_large_enough(self):
        d = _make(
            [
                {"type": "icon", "x": 0, "y": 0, "width": 24, "height": 24, "icon_char": "wifi"},
            ]
        )
        ws = [w for w in _warns(d) if "bitmap" in w.message]
        assert ws == []

    def test_icon_20x20_ok(self):
        d = _make(
            [
                {"type": "icon", "x": 0, "y": 0, "width": 20, "height": 20, "icon_char": "wifi"},
            ]
        )
        ws = [w for w in _warns(d) if "bitmap" in w.message]
        assert ws == []

    def test_icon_19x20_too_narrow(self):
        d = _make(
            [
                {"type": "icon", "x": 0, "y": 0, "width": 19, "height": 20, "icon_char": "wifi"},
            ]
        )
        ws = [w for w in _warns(d) if "bitmap" in w.message]
        assert len(ws) == 1

    def test_icon_20x19_too_short(self):
        d = _make(
            [
                {"type": "icon", "x": 0, "y": 0, "width": 20, "height": 19, "icon_char": "wifi"},
            ]
        )
        ws = [w for w in _warns(d) if "bitmap" in w.message]
        assert len(ws) == 1

    def test_icon_no_icon_char_no_warning(self):
        d = _make(
            [
                {"type": "icon", "x": 0, "y": 0, "width": 10, "height": 10},
            ]
        )
        ws = [w for w in _warns(d) if "bitmap" in w.message]
        assert ws == []


# ---------------------------------------------------------------------------
# Rule 120: checkbox/radiobutton too narrow for label
# ---------------------------------------------------------------------------


class TestRule120:
    def test_checkbox_wide_enough(self):
        d = _make(
            [
                {"type": "checkbox", "x": 0, "y": 0, "width": 60, "height": 16, "text": "On"},
            ]
        )
        ws = [w for w in _warns(d) if "too narrow" in w.message and "label" in w.message]
        assert ws == []

    def test_checkbox_16_ok(self):
        d = _make(
            [
                {"type": "checkbox", "x": 0, "y": 0, "width": 16, "height": 16, "text": "X"},
            ]
        )
        ws = [w for w in _warns(d) if "too narrow" in w.message and "label" in w.message]
        assert ws == []

    def test_checkbox_15_too_narrow(self):
        d = _make(
            [
                {"type": "checkbox", "x": 0, "y": 0, "width": 15, "height": 16, "text": "X"},
            ]
        )
        ws = [w for w in _warns(d) if "too narrow" in w.message and "label" in w.message]
        assert len(ws) == 1

    def test_checkbox_no_text_ok(self):
        d = _make(
            [
                {"type": "checkbox", "x": 0, "y": 0, "width": 12, "height": 16},
            ]
        )
        ws = [w for w in _warns(d) if "too narrow" in w.message and "label" in w.message]
        assert ws == []

    def test_radiobutton_too_narrow(self):
        d = _make(
            [
                {"type": "radiobutton", "x": 0, "y": 0, "width": 14, "height": 16, "text": "A"},
            ]
        )
        ws = [w for w in _warns(d) if "too narrow" in w.message and "label" in w.message]
        assert len(ws) == 1


# ---------------------------------------------------------------------------
# Rule 121: value/chart widget height too short for text
# ---------------------------------------------------------------------------


class TestRule121:
    def test_gauge_with_text_ok(self):
        d = _make(
            [
                {
                    "type": "gauge",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 20,
                    "text": "CPU",
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert ws == []

    def test_gauge_with_text_height_8(self):
        d = _make(
            [
                {
                    "type": "gauge",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 8,
                    "text": "CPU",
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert ws == []

    def test_gauge_with_text_height_7(self):
        d = _make(
            [
                {
                    "type": "gauge",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 7,
                    "text": "CPU",
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert len(ws) == 1

    def test_progressbar_with_text_short(self):
        d = _make(
            [
                {
                    "type": "progressbar",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 5,
                    "text": "Load",
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert len(ws) == 1

    def test_chart_with_text_short(self):
        d = _make(
            [
                {
                    "type": "chart",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 6,
                    "text": "Stats",
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert len(ws) == 1

    def test_gauge_no_text_no_warning(self):
        d = _make(
            [
                {
                    "type": "gauge",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 5,
                    "value": 50,
                    "min_value": 0,
                    "max_value": 100,
                },
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert ws == []

    def test_label_not_affected(self):
        """Labels use Rule 6, not 121."""
        d = _make(
            [
                {"type": "label", "x": 0, "y": 0, "width": 80, "height": 5, "text": "Hi"},
            ]
        )
        ws = [w for w in _warns(d) if "too short to render text" in w.message]
        assert ws == []


# ---------------------------------------------------------------------------
# Rule 122: runtime meta key validation
# ---------------------------------------------------------------------------


class TestRule122:
    def test_valid_runtime_keys(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "runtime": "bind=sensor.temp;kind=int;min=0;max=100;step=1",
                },
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert ws == []

    def test_valid_key_alias(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "runtime": "key=sensor.temp;type=bool;values=off|on",
                },
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert ws == []

    def test_unknown_key(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "runtime": "txt=sensor.temp;kind=int",
                },
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert len(ws) == 1
        assert "txt" in ws[0].message

    def test_multiple_unknown_keys(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "runtime": "foo=bar;baz=qux",
                },
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert len(ws) == 2

    def test_case_insensitive(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "runtime": "Bind=sensor.temp;Kind=int",
                },
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert ws == []

    def test_no_runtime_no_warning(self):
        d = _make(
            [
                {"type": "button", "x": 0, "y": 0, "width": 80, "height": 16, "text": "OK"},
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert ws == []

    def test_empty_parts_skipped(self):
        d = _make(
            [
                {
                    "type": "button",
                    "x": 0,
                    "y": 0,
                    "width": 80,
                    "height": 16,
                    "text": "X",
                    "runtime": "bind=x;;kind=int;",
                },
            ]
        )
        ws = [w for w in _warns(d) if "recognized meta key" in w.message]
        assert ws == []
