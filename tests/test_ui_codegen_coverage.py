"""Targeted tests for ui_codegen edge cases to improve coverage."""

import json

from tools.ui_codegen import (
    _hex_to_rgb,
    _rgb_to_gray4,
    generate_scenes_header,
    generate_ui_design_multi_pair,
    generate_ui_design_pair,
    load_scenes,
    parse_gray4,
    select_scene,
)


class TestHexToRgbExcept:
    """Lines 106-107: bad hex digits trigger except fallback."""

    def test_bad_hex_chars(self):
        assert _hex_to_rgb("#zzzzzz") == (255, 255, 255)

    def test_partial_bad_hex(self):
        assert _hex_to_rgb("#gg0000") == (255, 255, 255)


class TestRgbToGray4Except:
    """Lines 120-121: non-numeric args trigger except."""

    def test_non_numeric_args(self):
        result = _rgb_to_gray4("bad", "data", "here")
        assert 0 <= result <= 15


class TestParseGray4Except:
    """Lines 133-134: _get_rgb failure triggers except fallback."""

    def test_unparseable_color(self):
        # Short hex falls through to _hex_to_rgb which returns (255,255,255)
        # for len != 6, so parse_gray4 returns gray4(white) = 15, not default
        assert parse_gray4("#xy", default=7) == 15


class TestSelectSceneEdge:
    """Lines 181-182: select_scene with unusual scenes format."""

    def test_list_with_no_dicts(self):
        data = {"scenes": ["not_a_dict", 123, None]}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc == {}

    def test_non_dict_non_list_scenes(self):
        data = {"scenes": "just_a_string"}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc == {}


class TestGenerateUiDesignPairEdge:
    """Lines 257, 314, 348: edge cases in generate_ui_design_pair."""

    def test_widgets_not_list(self, tmp_path):
        """Line 257: widgets is not a list → replaced with []."""
        data = {"scenes": {"main": {"name": "main", "width": 128, "height": 64, "widgets": "bad"}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        c_src, h_src = generate_ui_design_pair(p, scene_name="main", source_label="test")
        assert "UiScene" in c_src
        assert "widgets" not in c_src or "widgets[]" in c_src

    def test_non_dict_widget_skipped(self, tmp_path):
        """Line 314: non-dict widget triggers continue."""
        data = {"scenes": {"main": {"name": "main", "width": 128, "height": 64,
                                     "widgets": ["not_a_dict", {"type": "label", "x": 0, "y": 0, "width": 10, "height": 3, "text": "ok"}]}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        c_src, _ = generate_ui_design_pair(p, scene_name="main", source_label="test")
        assert "UIW_LABEL" in c_src

    def test_negative_max_lines_clamped(self, tmp_path):
        """Line 348: max_lines < 0 → 0."""
        data = {"scenes": {"main": {"name": "main", "width": 128, "height": 64,
                                     "widgets": [{"type": "label", "x": 0, "y": 0, "width": 10, "height": 3, "max_lines": -5}]}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        c_src, _ = generate_ui_design_pair(p, scene_name="main", source_label="test")
        assert ".max_lines = 0" in c_src


class TestLoadScenesEdge:
    """Line 395: scenes_raw is neither dict nor list."""

    def test_non_dict_non_list(self, tmp_path):
        data = {"scenes": 42}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert result == {}


class TestGenerateScenesHeaderEdge:
    """Lines 440-441, 449, 468, 484: edge cases in generate_scenes_header."""

    def test_empty_widgets_scene(self, tmp_path):
        """Line 449: scene with no widgets → '/* empty */' comment."""
        data = {"scenes": {"main": {"width": 128, "height": 64, "widgets": []}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = generate_scenes_header(p, guard="TEST_H", source_name="test", generated_ts="now")
        assert "/* empty */" in result

    def test_widget_with_animations_list(self, tmp_path):
        """Line 468: animations list gets joined to anim_csv."""
        data = {"scenes": {"main": {"width": 128, "height": 64, "widgets": [
            {"type": "label", "x": 0, "y": 0, "width": 10, "height": 3,
             "animations": ["fade_in", "slide_left"]}
        ]}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = generate_scenes_header(p, guard="TEST_H", source_name="test", generated_ts="now")
        assert "fade_in;slide_left" in result

    def test_negative_max_lines(self, tmp_path):
        """Line 484: max_lines < 0 → clamped to 0."""
        data = {"scenes": {"main": {"width": 128, "height": 64, "widgets": [
            {"type": "label", "x": 0, "y": 0, "width": 10, "height": 3, "max_lines": -3}
        ]}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = generate_scenes_header(p, guard="TEST_H", source_name="test", generated_ts="now")
        assert ".max_lines = 0" in result


class TestGenerateMultiPairEdge:
    """Lines 600, 645, 664: edge cases in generate_ui_design_multi_pair."""

    def test_widgets_not_list(self, tmp_path):
        """Line 600: widgets is not a list → replaced with []."""
        data = {"scenes": {"main": {"width": 128, "height": 64, "widgets": "bad"}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        c_src, h_src = generate_ui_design_multi_pair(p, source_label="test")
        assert "ui_scenes" in c_src

    def test_widgets_not_list_in_registry(self, tmp_path):
        """Line 645: widgets not a list in scene registry path."""
        # Use None for widgets (falsy but iterable after `or []`)
        data = {"scenes": {"main": {"width": 128, "height": 64, "widgets": None}}}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        c_src, h_src = generate_ui_design_multi_pair(p, source_label="test")
        assert "UI_SCENE_COUNT" in h_src
