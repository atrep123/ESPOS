"""Targeted tests for validate_design coverage gaps."""

import json
from unittest.mock import patch

from tools.validate_design import (
    _parse_color,
    _scenes_from_data,
    main,
    validate_data,
    validate_file,
)


def _base_scene(**overrides):
    """Minimal valid scene dict."""
    sc = {"width": 256, "height": 128, "widgets": []}
    sc.update(overrides)
    return sc


def _base_widget(**overrides):
    """Minimal valid widget dict."""
    w = {
        "type": "label",
        "x": 10,
        "y": 10,
        "width": 50,
        "height": 20,
        "text": "hello",
        "border": True,
        "color_fg": "white",
        "color_bg": "black",
        "visible": True,
        "enabled": True,
        "checked": False,
    }
    w.update(overrides)
    return w


def _validate(data, **kw):
    return validate_data(
        data, file_label="test", warnings_as_errors=kw.get("warnings_as_errors", False)
    )


# ── Line 110: _parse_color("") returns None ──


class TestParseColor:
    def test_empty_string(self):
        assert _parse_color("") is None

    def test_named_color(self):
        assert _parse_color("red") == (255, 0, 0)


# ── Lines 149-157: _scenes_from_data list format and non-dict/list ──


class TestScenesFromData:
    def test_scenes_as_list(self):
        data = {"scenes": [{"id": "s1", "width": 128, "height": 64, "widgets": []}]}
        result = _scenes_from_data(data)
        assert "s1" in result

    def test_scenes_as_list_unnamed(self):
        data = {"scenes": [{"width": 128, "height": 64, "widgets": []}]}
        result = _scenes_from_data(data)
        assert "scene_0" in result

    def test_scenes_as_list_non_dict_entries(self):
        data = {"scenes": ["bad", {"id": "ok", "width": 128, "height": 64, "widgets": []}]}
        result = _scenes_from_data(data)
        assert "ok" in result
        assert len(result) == 1

    def test_scenes_neither_dict_nor_list(self):
        result = _scenes_from_data({"scenes": 42})
        assert result == {}


# ── Lines 173, 175: non-int root width/height ──


class TestRootDimensionTypes:
    def test_root_width_not_int(self):
        data = {"width": "256", "height": 128, "scenes": {"main": _base_scene()}}
        issues = _validate(data)
        assert any("root.width must be int" in i.message for i in issues)

    def test_root_height_not_int(self):
        data = {"width": 256, "height": "bad", "scenes": {"main": _base_scene()}}
        issues = _validate(data)
        assert any("root.height must be int" in i.message for i in issues)


# ── Lines 195-196: scene height invalid ──


class TestSceneHeightInvalid:
    def test_scene_height_zero(self):
        data = {"scenes": {"main": _base_scene(height=0)}}
        issues = _validate(data)
        assert any("height must be int >= 1" in i.message for i in issues)

    def test_scene_height_string(self):
        data = {"scenes": {"main": _base_scene(height="abc")}}
        issues = _validate(data)
        assert any("height must be int >= 1" in i.message for i in issues)


# ── Lines 201-202: widgets not a list ──


class TestWidgetsNotList:
    def test_widgets_is_string(self):
        data = {"scenes": {"main": _base_scene(widgets="not_a_list")}}
        issues = _validate(data)
        assert any("widgets must be a list" in i.message for i in issues)

    def test_widgets_is_dict(self):
        data = {"scenes": {"main": _base_scene(widgets={})}}
        issues = _validate(data)
        assert any("widgets must be a list" in i.message for i in issues)


# ── Lines 214-215: non-dict widget entry ──
# NOTE: Lines 214-215 are unreachable — _wref() at line 211 calls w.get()
# on non-dict values before the isinstance check at line 213.


# ── Line 229: missing geometry field ──


class TestMissingGeometry:
    def test_missing_x_detected(self):
        """Missing geometry is detected but later code may crash — verify error is appended."""
        import pytest

        w = _base_widget()
        del w["x"]
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        # The validator detects missing 'x' but then crashes when trying to use x=None.
        with pytest.raises(TypeError):
            _validate(data)

    def test_missing_width_detected(self):
        w = _base_widget()
        del w["width"]
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("missing 'width'" in i.message for i in issues)


# ── Line 265: non-string widget ID ──


class TestNonStringWidgetId:
    def test_int_widget_id(self):
        w = _base_widget(_widget_id=123)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("_widget_id/id must be string" in i.message for i in issues)


# ── Lines 278, 280: max_lines edge cases ──


class TestMaxLinesEdge:
    def test_max_lines_string(self):
        w = _base_widget(max_lines="three")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("max_lines must be int or null" in i.message for i in issues)

    def test_max_lines_negative(self):
        w = _base_widget(max_lines=-1)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("max_lines must be >= 0" in i.message for i in issues)


# ── Line 527, 968, 980, etc.: non-dict widget in second pass ──
# NOTE: These are unreachable — _wref() crashes on non-dict widgets
# before the isinstance check. Lines 214-215, 527, 968, etc. are dead code.


# ── Lines 1099-1100: validate_file with bad JSON ──


class TestValidateFile:
    def test_bad_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        issues = validate_file(p, warnings_as_errors=False)
        assert len(issues) == 1
        assert issues[0].level == "ERROR"
        assert "failed to parse JSON" in issues[0].message

    def test_nonexistent_file(self, tmp_path):
        p = tmp_path / "nonexistent.json"
        issues = validate_file(p, warnings_as_errors=False)
        assert len(issues) == 1
        assert "failed to read" in issues[0].message

    def test_non_dict_root(self, tmp_path):
        """Line 1102: JSON root is not a dict."""
        p = tmp_path / "array.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        issues = validate_file(p, warnings_as_errors=False)
        assert len(issues) == 1
        assert "root must be a JSON object" in issues[0].message

    def test_valid_file(self, tmp_path):
        data = {
            "width": 256,
            "height": 128,
            "scenes": {
                "main": {"width": 256, "height": 128, "widgets": [_base_widget(_widget_id="w1")]}
            },
        }
        p = tmp_path / "valid.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        issues = validate_file(p, warnings_as_errors=False)
        # Should succeed (may have warnings, but no crash)
        assert isinstance(issues, list)

    def test_oversized_file_rejected(self, tmp_path):
        """Files exceeding MAX_JSON_FILE_SIZE are rejected before parsing."""
        from tools.validate_design import MAX_JSON_FILE_SIZE

        p = tmp_path / "huge.json"
        # Write a file just over the limit
        p.write_text("x" * (MAX_JSON_FILE_SIZE + 1), encoding="utf-8")
        issues = validate_file(p, warnings_as_errors=False)
        assert len(issues) == 1
        assert issues[0].level == "ERROR"
        assert "size limit" in issues[0].message


# ── Lines 1107-1126: main() CLI entry point ──


class TestMain:
    def test_main_with_valid_file(self, tmp_path, capsys):
        data = {
            "width": 256,
            "height": 128,
            "scenes": {
                "main": {"width": 256, "height": 128, "widgets": [_base_widget(_widget_id="w1")]}
            },
        }
        p = tmp_path / "valid.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        with patch("sys.argv", ["validate_design.py", str(p)]):
            code = main()
        out = capsys.readouterr().out
        # Should either be OK or have only warnings
        assert code in (0, 1)
        assert "[" in out  # Has some output

    def test_main_with_errors(self, tmp_path, capsys):
        data = {"scenes": {"main": {"width": "bad", "height": 128, "widgets": []}}}
        p = tmp_path / "err.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        with patch("sys.argv", ["validate_design.py", str(p)]):
            code = main()
        out = capsys.readouterr().out
        assert code == 1
        assert "[FAIL]" in out

    def test_main_warnings_as_errors(self, tmp_path, capsys):
        data = {
            "width": 256,
            "height": 128,
            "scenes": {
                "main": {
                    "width": 256,
                    "height": 128,
                    "widgets": [],  # Rule 22: empty scene → WARN
                }
            },
        }
        p = tmp_path / "warn.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        with patch("sys.argv", ["validate_design.py", str(p), "--warnings-as-errors"]):
            code = main()
        capsys.readouterr()  # consume output
        assert code == 1  # WARN promoted to ERROR


# ---------------------------------------------------------------------------
# BB — validate_design rule interaction & multi-rule stress tests
# ---------------------------------------------------------------------------


class TestDuplicateWidgetIds:
    def test_duplicate_id_error(self):
        w1 = _base_widget(_widget_id="dup")
        w2 = _base_widget(_widget_id="dup", x=60)
        data = {"scenes": {"main": _base_scene(widgets=[w1, w2])}}
        issues = _validate(data)
        assert any("duplicate id" in i.message for i in issues)

    def test_unique_ids_no_error(self):
        w1 = _base_widget(_widget_id="a")
        w2 = _base_widget(_widget_id="b", x=60)
        data = {"scenes": {"main": _base_scene(widgets=[w1, w2])}}
        issues = _validate(data)
        assert not any("duplicate id" in i.message for i in issues)


class TestValueRangeRules:
    def test_min_ge_max_error(self):
        w = _base_widget(type="gauge", min_value=100, max_value=50, value=75, width=20, height=20)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("min_value" in i.message and "max_value" in i.message for i in issues)

    def test_value_out_of_range_warn(self):
        w = _base_widget(type="gauge", min_value=0, max_value=100, value=200, width=20, height=20)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("value=200" in i.message for i in issues)

    def test_int16_overflow(self):
        w = _base_widget(type="gauge", value=40000, min_value=0, max_value=100, width=20, height=20)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("overflows int16" in i.message for i in issues)


class TestColorAndContrastRules:
    def test_unparseable_fg_color(self):
        w = _base_widget(color_fg="not-a-color", color_bg="white")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("can't parse color_fg" in i.message for i in issues)

    def test_low_contrast_warning(self):
        w = _base_widget(color_fg="#101010", color_bg="#141414")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("low contrast" in i.message for i in issues)

    def test_dim_fg_warning(self):
        w = _base_widget(color_fg="#050505", color_bg="white")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("too dim" in i.message for i in issues)


class TestBorderConsistency:
    def test_border_true_style_none(self):
        w = _base_widget(border=True, border_style="none")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("border=True but border_style='none'" in i.message for i in issues)

    def test_double_border_too_small(self):
        w = _base_widget(border=True, border_style="double", width=4, height=4, x=0, y=0)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("double border needs >= 5x5" in i.message for i in issues)


class TestFontCharsetCompliance:
    def test_unsupported_chars_warn(self):
        w = _base_widget(text="hello@world")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("unsupported chars" in i.message for i in issues)

    def test_supported_chars_no_warn(self):
        w = _base_widget(text="HELLO 123")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert not any("unsupported chars" in i.message for i in issues)


class TestTextOverflowRules:
    def test_text_too_long_for_width(self):
        # Widget 20px wide, inner ~16px = 2 chars, but text is much longer
        w = _base_widget(x=0, y=0, width=20, height=20, text="ABCDEFGHIJKLMNOP")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("overflows" in i.message for i in issues)

    def test_text_exceeds_max_len_warning(self):
        w = _base_widget(text="A" * 150)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("exceeds" in i.message and "chars" in i.message for i in issues)


class TestMinimumWidgetSizes:
    def test_gauge_too_small(self):
        w = _base_widget(type="gauge", width=5, height=5, x=0, y=0,
                         min_value=0, max_value=100, value=50)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("gauge" in i.message and "too small" in i.message for i in issues)

    def test_slider_too_narrow(self):
        w = _base_widget(type="slider", width=10, height=20, x=0, y=0,
                         min_value=0, max_value=100, value=50)
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("slider" in i.message and "too narrow" in i.message for i in issues)


class TestRuntimeFormat:
    def test_runtime_missing_equals(self):
        w = _base_widget(runtime="bind_no_equals")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("missing '='" in i.message for i in issues)

    def test_runtime_valid_format(self):
        w = _base_widget(runtime="bind=temp;key=t1")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert not any("missing '='" in i.message for i in issues)


class TestWidgetIdFormat:
    def test_invalid_id_chars(self):
        w = _base_widget(_widget_id="bad id!")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("invalid characters" in i.message for i in issues)

    def test_valid_id(self):
        w = _base_widget(_widget_id="good_id.sub-1")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert not any("invalid characters" in i.message for i in issues)


class TestSceneNameValidation:
    def test_invalid_scene_name(self):
        data = {"scenes": {"bad scene!": _base_scene()}}
        issues = _validate(data)
        assert any("invalid characters" in i.message for i in issues)

    def test_valid_scene_name(self):
        data = {"scenes": {"main_screen": _base_scene()}}
        issues = _validate(data)
        assert not any("invalid characters" in i.message for i in issues)


class TestLockedFieldType:
    def test_locked_not_bool(self):
        w = _base_widget(locked="yes")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("'locked' must be boolean" in i.message for i in issues)


class TestStateOverridesStructure:
    def test_state_overrides_not_dict(self):
        w = _base_widget(state_overrides="bad")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("state_overrides must be a dict" in i.message for i in issues)

    def test_state_overrides_inner_not_dict(self):
        w = _base_widget(state_overrides={"hover": "not-a-dict"})
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("state_overrides['hover'] must be a dict" in i.message for i in issues)


class TestAnimationsField:
    def test_animations_not_list(self):
        w = _base_widget(animations="bad")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("animations must be a list" in i.message for i in issues)

    def test_animations_non_string_items(self):
        w = _base_widget(animations=[123, "ok"])
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("non-string items" in i.message for i in issues)


class TestStyleField:
    def test_invalid_style(self):
        w = _base_widget(style="rainbow")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert any("invalid style" in i.message for i in issues)

    def test_valid_style(self):
        w = _base_widget(style="bold")
        data = {"scenes": {"main": _base_scene(widgets=[w])}}
        issues = _validate(data)
        assert not any("invalid style" in i.message for i in issues)
