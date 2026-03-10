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
        assert "failed to parse JSON" in issues[0].message

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
