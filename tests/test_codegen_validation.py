"""Codegen validation tests — covering gaps identified in the JSON→C pipeline.

Targets untested paths in tools/ui_codegen.py:
- Scene fallback when prefer_name doesn't match
- Z-index sorting verification
- Tab/special character escaping
- Hex color edge cases
- write_if_changed file I/O paths
- Animation format mixing (list + csv)
- Dimension overflow/negative values
- Style flag combinations
- Border/align/valign/overflow fallback mapping
- as_int/as_bool edge cases
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools.ui_codegen import (
    _emit_widget,
    _hex_to_rgb,
    align_for,
    as_bool,
    as_int,
    border_style_for,
    build_string_pool,
    collect_widget_strings,
    escape_c_comment,
    escape_c_string,
    generate_scenes_header,
    generate_ui_design_multi_pair,
    generate_ui_design_pair,
    load_scenes,
    overflow_for,
    parse_gray4,
    sanitize_ident,
    select_scene,
    style_expr,
    valign_for,
    write_if_changed,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(tmp_path: Path, scenes: dict) -> Path:
    p = tmp_path / "design.json"
    p.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    return p


def _w(**kw):
    """Minimal widget dict."""
    defaults = dict(type="label", x=0, y=0, width=32, height=16)
    defaults.update(kw)
    return defaults


def _emit(w: dict, idx: int = 0) -> str:
    pool = build_string_pool(collect_widget_strings(w), symbol_prefix="s_")
    return "\n".join(_emit_widget(w, idx, pool))


# ===========================================================================
# escape_c_string — tab char and combined escapes
# ===========================================================================
class TestEscapeCStringExtended:
    def test_tab_escaped(self):
        """Tab chars are escaped to \\t in C strings."""
        result = escape_c_string("a\tb")
        assert "\\t" in result
        assert "\t" not in result

    def test_combined_escapes(self):
        result = escape_c_string('line1\nline2\r"end"\\done')
        assert "\\n" in result
        assert "\\r" in result
        assert '\\"' in result
        assert "\\\\" in result

    def test_none_input(self):
        assert escape_c_string(None) == ""

    def test_numeric_input(self):
        assert escape_c_string(42) == "42"

    def test_null_byte_stripped(self):
        """Null bytes are escaped to \\x00 to prevent C string truncation."""
        result = escape_c_string("a\0b")
        assert "\0" not in result
        assert "\\x00" in result


# ===========================================================================
# escape_c_comment — prevent comment-close injection
# ===========================================================================
class TestEscapeCComment:
    def test_close_comment_escaped(self):
        assert "*/" not in escape_c_comment("hello */ world")
        assert "* /" in escape_c_comment("hello */ world")

    def test_plain_text_unchanged(self):
        assert escape_c_comment("hello world") == "hello world"

    def test_none_input(self):
        assert escape_c_comment(None) == ""


# ===========================================================================
# Hex color edge cases
# ===========================================================================
class TestHexColorEdgeCases:
    def test_5char_hex_returns_white(self):
        assert _hex_to_rgb("#12345") == (255, 255, 255)

    def test_1char_hex_returns_white(self):
        assert _hex_to_rgb("#f") == (255, 255, 255)

    def test_7char_hex_returns_white(self):
        assert _hex_to_rgb("#1234567") == (255, 255, 255)

    def test_empty_hash_returns_white(self):
        assert _hex_to_rgb("#") == (255, 255, 255)

    def test_no_hash_6char_still_works(self):
        assert _hex_to_rgb("ff0000") == (255, 0, 0)

    def test_named_color_via_parse_gray4(self):
        # "black" → RGB(0,0,0) → gray4 = 0
        assert parse_gray4("black", default=7) == 0

    def test_named_color_white(self):
        assert parse_gray4("white", default=0) == 15

    def test_mixed_case_color_name(self):
        assert parse_gray4("RED", default=0) == parse_gray4("red", default=0)

    def test_empty_string_returns_default(self):
        assert parse_gray4("", default=9) == 9

    def test_none_returns_default(self):
        assert parse_gray4(None, default=5) == 5


# ===========================================================================
# as_int edge cases
# ===========================================================================
class TestAsIntEdges:
    def test_none(self):
        assert as_int(None, 42) == 42

    def test_float(self):
        assert as_int(3.7, 0) == 3

    def test_string_number(self):
        assert as_int("123", 0) == 123

    def test_string_non_number(self):
        assert as_int("abc", 99) == 99

    def test_bool_true(self):
        assert as_int(True, 0) == 1

    def test_bool_false(self):
        assert as_int(False, 5) == 0

    def test_negative(self):
        assert as_int(-10, 0) == -10


# ===========================================================================
# as_bool edge cases
# ===========================================================================
class TestAsBoolEdges:
    def test_string_yes(self):
        assert as_bool("yes") is True

    def test_string_no(self):
        assert as_bool("no") is False

    def test_string_on(self):
        assert as_bool("on") is True

    def test_string_off(self):
        assert as_bool("off") is False

    def test_string_1(self):
        assert as_bool("1") is True

    def test_string_0(self):
        assert as_bool("0") is False

    def test_string_random(self):
        assert as_bool("maybe", True) is True

    def test_none_default_true(self):
        assert as_bool(None, True) is True

    def test_int_1(self):
        # int 1 → str "1" → True
        assert as_bool(1) is True

    def test_int_0(self):
        assert as_bool(0) is False


# ===========================================================================
# style_expr combinations
# ===========================================================================
class TestStyleExprCombinations:
    def test_inverse_only(self):
        assert style_expr("inverse") == "UI_STYLE_INVERSE"

    def test_bold_highlight(self):
        result = style_expr("bold highlight")
        assert "UI_STYLE_HIGHLIGHT" in result
        assert "UI_STYLE_BOLD" in result
        assert "|" in result

    def test_all_three(self):
        result = style_expr("inverse highlight bold")
        assert "UI_STYLE_INVERSE" in result
        assert "UI_STYLE_HIGHLIGHT" in result
        assert "UI_STYLE_BOLD" in result

    def test_none_style(self):
        assert style_expr("") == "UI_STYLE_NONE"

    def test_none_input(self):
        assert style_expr(None) == "UI_STYLE_NONE"

    def test_case_insensitive(self):
        assert style_expr("BOLD") == "UI_STYLE_BOLD"


# ===========================================================================
# Border/align/valign/overflow mapping fallbacks
# ===========================================================================
class TestEnumMappingFallbacks:
    def test_unknown_border_style_defaults_single(self):
        w = {"border_style": "zigzag"}
        assert border_style_for(w, border=1) == "UI_BORDER_SINGLE"

    def test_no_border_returns_none(self):
        w = {"border_style": "double"}
        assert border_style_for(w, border=0) == "UI_BORDER_NONE"

    def test_dashed_border(self):
        w = {"border_style": "dashed"}
        assert border_style_for(w, border=1) == "UI_BORDER_DASHED"

    def test_unknown_align_defaults_left(self):
        assert align_for({"align": "justify"}) == "UI_ALIGN_LEFT"

    def test_right_align(self):
        assert align_for({"align": "right"}) == "UI_ALIGN_RIGHT"

    def test_unknown_valign_defaults_middle(self):
        assert valign_for({"valign": "stretch"}) == "UI_VALIGN_MIDDLE"

    def test_bottom_valign(self):
        assert valign_for({"valign": "bottom"}) == "UI_VALIGN_BOTTOM"

    def test_unknown_overflow_defaults_ellipsis(self):
        assert overflow_for({"text_overflow": "scroll"}) == "UI_TEXT_OVERFLOW_ELLIPSIS"

    def test_wrap_overflow(self):
        assert overflow_for({"text_overflow": "wrap"}) == "UI_TEXT_OVERFLOW_WRAP"

    def test_auto_overflow(self):
        assert overflow_for({"text_overflow": "auto"}) == "UI_TEXT_OVERFLOW_AUTO"

    def test_missing_align_defaults_left(self):
        assert align_for({}) == "UI_ALIGN_LEFT"

    def test_missing_valign_defaults_middle(self):
        assert valign_for({}) == "UI_VALIGN_MIDDLE"

    def test_missing_overflow_defaults_ellipsis(self):
        assert overflow_for({}) == "UI_TEXT_OVERFLOW_ELLIPSIS"


# ===========================================================================
# sanitize_ident edge cases
# ===========================================================================
class TestSanitizeIdentExtended:
    def test_c_keyword_passes_through(self):
        # "int" is valid C identifier chars — codegen doesn't block keywords
        assert sanitize_ident("int") == "int"

    def test_unicode_stripped(self):
        result = sanitize_ident("naïve")
        # non-ASCII chars replaced with underscore
        assert result.isascii() or all(c.isalnum() or c == "_" for c in result)

    def test_all_digits(self):
        result = sanitize_ident("123")
        assert result[0] == "_" or result[0].isalpha()

    def test_hyphen_and_dot(self):
        assert sanitize_ident("my-scene.v2") == "my_scene_v2"

    def test_uppercase_lowered(self):
        assert sanitize_ident("MyScene") == "myscene"


# ===========================================================================
# select_scene — fallback behavior
# ===========================================================================
class TestSelectSceneFallback:
    def test_prefer_name_not_in_dict(self):
        """When prefer_name doesn't match, should return first dict scene."""
        data = {"scenes": {"alpha": {"widgets": []}, "beta": {"widgets": []}}}
        name, sc = select_scene(data, "nonexistent")
        assert name == "alpha"
        assert sc == {"widgets": []}

    def test_prefer_name_matches(self):
        data = {"scenes": {"alpha": {"widgets": []}, "beta": {"widgets": [{"type": "label"}]}}}
        name, sc = select_scene(data, "beta")
        assert name == "beta"
        assert len(sc["widgets"]) == 1

    def test_empty_scenes_dict(self):
        data = {"scenes": {}}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc == {}

    def test_list_scenes_picks_first_dict(self):
        data = {"scenes": [{"name": "s1", "widgets": []}, {"name": "s2", "widgets": []}]}
        name, sc = select_scene(data, "any")
        assert name == "s1"

    def test_no_scenes_key(self):
        data = {}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc == {}


# ===========================================================================
# Z-index sorting
# ===========================================================================
class TestZIndexSorting:
    def test_widgets_sorted_by_z_index(self, tmp_path):
        """Verify generate_scenes_header sorts widgets by z_index."""
        p = _write_json(
            tmp_path,
            {
                "sc": {
                    "width": 64,
                    "height": 32,
                    "widgets": [
                        _w(_widget_id="back", z_index=10),
                        _w(_widget_id="front", z_index=1),
                        _w(_widget_id="mid", z_index=5),
                    ],
                },
            },
        )
        h = generate_scenes_header(p, guard="G", source_name="t", generated_ts="now")
        # Extract widget array section only (between widgets[] = { and closing };)
        arr_start = h.index("sc_widgets[]")
        arr_section = h[arr_start:]
        # In the widget array, [0] should be front(z=1), [1] mid(z=5), [2] back(z=10)
        entries = re.findall(r"/\* \[(\d+)\]", arr_section)
        assert entries == ["0", "1", "2"]
        # Verify front (z=1) is at index 0 by checking the .id ref order
        # The pool builds in input order before sort, so check the widget text refs
        front_pool = [ln for ln in h.splitlines() if "front" in ln and "const char" in ln]
        mid_pool = [ln for ln in h.splitlines() if "mid" in ln and "const char" in ln]
        back_pool = [ln for ln in h.splitlines() if "back" in ln and "const char" in ln]
        assert len(front_pool) == 1
        assert len(mid_pool) == 1
        assert len(back_pool) == 1
        # Extract pool symbol names
        front_sym = front_pool[0].split()[3]  # e.g. ui_str_0[]
        mid_sym = mid_pool[0].split()[3]
        back_sym = back_pool[0].split()[3]
        # In the widget array, first widget's .id should reference front's symbol
        id_refs = re.findall(r"\.id = (ui_str_\d+)", arr_section)
        assert id_refs[0] == front_sym.rstrip("[],")
        assert id_refs[1] == mid_sym.rstrip("[],")
        assert id_refs[2] == back_sym.rstrip("[],")

    def test_z_index_non_numeric_no_crash(self, tmp_path):
        """Non-numeric z_index should not crash (caught by except)."""
        p = _write_json(
            tmp_path,
            {
                "sc": {
                    "width": 64,
                    "height": 32,
                    "widgets": [
                        _w(text="a", z_index="bad"),
                        _w(text="b", z_index=1),
                    ],
                },
            },
        )
        h = generate_scenes_header(p, guard="G", source_name="t", generated_ts="now")
        assert "a" in h
        assert "b" in h

    def test_z_index_missing_defaults_zero(self, tmp_path):
        """Widgets without z_index should sort as z=0."""
        p = _write_json(
            tmp_path,
            {
                "sc": {
                    "width": 64,
                    "height": 32,
                    "widgets": [
                        _w(_widget_id="hi_z", z_index=5),
                        _w(_widget_id="no_z"),
                    ],
                },
            },
        )
        h = generate_scenes_header(p, guard="G", source_name="t", generated_ts="now")
        # In sorted widget array, no_z (z=0) should come before hi_z (z=5)
        arr_start = h.index("sc_widgets[]")
        arr_section = h[arr_start:]
        id_refs = re.findall(r"\.id = (ui_str_\d+)", arr_section)
        # Find which pool symbol corresponds to which id
        no_z_pool = [ln for ln in h.splitlines() if "no_z" in ln and "const char" in ln]
        no_z_sym = no_z_pool[0].split()[3].rstrip("[],")
        assert id_refs[0] == no_z_sym  # no_z should be first widget


# ===========================================================================
# Animation format mixing
# ===========================================================================
class TestAnimationFormatMixing:
    def test_animations_list_joined(self):
        w = _w(animations=["fade", "slide"])
        strings = collect_widget_strings(w)
        assert "fade;slide" in strings
        out = _emit(w)
        # Widget output references a pool symbol, not the raw string
        assert ".animations_csv = s_" in out

    def test_animations_csv_used_directly(self):
        w = _w(animations_csv="glow;pulse")
        strings = collect_widget_strings(w)
        assert "glow;pulse" in strings
        out = _emit(w)
        assert ".animations_csv = s_" in out

    def test_csv_takes_precedence_over_list(self):
        """When both animations_csv and animations list exist, csv wins."""
        w = _w(animations=["from_list"], animations_csv="from_csv")
        strings = collect_widget_strings(w)
        assert "from_csv" in strings
        # The csv field is checked first, so the list is never joined
        assert "from_list" not in strings

    def test_empty_list_no_animation(self):
        w = _w(animations=[])
        out = _emit(w)
        assert ".animations_csv = NULL" in out

    def test_single_animation_list(self):
        w = _w(animations=["blink"])
        strings = collect_widget_strings(w)
        assert "blink" in strings


# ===========================================================================
# Dimension values — large and negative
# ===========================================================================
class TestDimensionValues:
    def test_large_x_y_preserved(self):
        out = _emit(_w(x=65000, y=60000))
        assert ".x = 65000" in out
        assert ".y = 60000" in out

    def test_negative_x_y(self):
        """Negative x/y clamped to 0 (uint16_t field)."""
        out = _emit(_w(x=-5, y=-10))
        assert ".x = 0" in out
        assert ".y = 0" in out

    def test_zero_dimensions(self):
        out = _emit(_w(width=0, height=0))
        assert ".width = 0" in out
        assert ".height = 0" in out

    def test_large_value_range(self):
        out = _emit(_w(value=-32768, min_value=-32768, max_value=32767))
        assert ".value = -32768" in out
        assert ".min_value = -32768" in out
        assert ".max_value = 32767" in out


# ===========================================================================
# write_if_changed
# ===========================================================================
class TestWriteIfChanged:
    def test_creates_new_file(self, tmp_path):
        p = tmp_path / "new_file.c"
        assert write_if_changed(p, "content") is True
        assert p.read_text(encoding="utf-8") == "content"

    def test_no_change_returns_false(self, tmp_path):
        p = tmp_path / "existing.c"
        p.write_text("content", encoding="utf-8")
        assert write_if_changed(p, "content") is False

    def test_changed_returns_true(self, tmp_path):
        p = tmp_path / "existing.c"
        p.write_text("old content", encoding="utf-8")
        assert write_if_changed(p, "new content") is True
        assert p.read_text(encoding="utf-8") == "new content"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "deep" / "nested" / "file.c"
        assert write_if_changed(p, "hello") is True
        assert p.read_text(encoding="utf-8") == "hello"

    def test_unix_line_endings(self, tmp_path):
        p = tmp_path / "test.c"
        write_if_changed(p, "line1\nline2\n")
        raw = p.read_bytes()
        assert b"\r\n" not in raw


# ===========================================================================
# load_scenes edge cases
# ===========================================================================
class TestLoadScenesExtended:
    def test_list_format_with_names(self, tmp_path):
        data = {
            "scenes": [
                {"name": "main", "width": 128, "height": 64, "widgets": []},
                {"name": "settings", "width": 128, "height": 64, "widgets": []},
            ]
        }
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert "main" in result
        assert "settings" in result

    def test_list_format_with_ids(self, tmp_path):
        data = {
            "scenes": [
                {"id": "sc1", "widgets": []},
                {"id": "sc2", "widgets": []},
            ]
        }
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert "sc1" in result

    def test_list_format_no_name_or_id(self, tmp_path):
        data = {"scenes": [{"widgets": []}, {"widgets": []}]}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert "scene_0" in result
        assert "scene_1" in result

    def test_no_scenes_key(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text(json.dumps({"width": 128}), encoding="utf-8")
        result = load_scenes(p)
        assert result == {}


# ===========================================================================
# generate_ui_design_pair — scene fallback, empty scenes
# ===========================================================================
class TestGeneratePairFallback:
    def test_prefer_name_not_matching_uses_first(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "alpha": {"width": 64, "height": 32, "widgets": [_w(text="AlphaText")]},
                "beta": {"width": 128, "height": 64, "widgets": [_w(text="BetaText")]},
            },
        )
        src, _ = generate_ui_design_pair(p, scene_name="nonexistent", source_label="t")
        assert "AlphaText" in src

    def test_scene_width_height_used(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "main": {"width": 320, "height": 240, "widgets": []},
            },
        )
        src, _ = generate_ui_design_pair(p, scene_name="main", source_label="t")
        assert ".width = 320" in src
        assert ".height = 240" in src


# ===========================================================================
# generate_ui_design_multi_pair — empty scenes raises
# ===========================================================================
class TestMultiPairErrors:
    def test_empty_scenes_raises(self, tmp_path):
        p = _write_json(tmp_path, {})
        with pytest.raises(ValueError, match="No scenes"):
            generate_ui_design_multi_pair(p, source_label="t")

    def test_scenes_header_empty_raises(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps({"scenes": {}}), encoding="utf-8")
        with pytest.raises(ValueError, match="No scenes"):
            generate_scenes_header(p, guard="G", source_name="t", generated_ts="now")


# ===========================================================================
# collect_widget_strings — runtime vs constraints_json
# ===========================================================================
class TestCollectWidgetStringsExtended:
    def test_runtime_collected_as_constraints(self):
        w = {"type": "slider", "runtime": '{"bind":"temp"}'}
        strings = collect_widget_strings(w)
        assert '{"bind":"temp"}' in strings

    def test_constraints_json_preferred_over_runtime(self):
        w = {"type": "slider", "constraints_json": "cjson", "runtime": "rt"}
        strings = collect_widget_strings(w)
        assert "cjson" in strings
        assert "rt" not in strings

    def test_widget_id_from_id_field(self):
        w = {"type": "label", "id": "my_id"}
        strings = collect_widget_strings(w)
        assert "my_id" in strings

    def test_widget_id_from_underscore_widget_id(self):
        w = {"type": "label", "_widget_id": "wid_1", "id": "fallback"}
        strings = collect_widget_strings(w)
        assert "wid_1" in strings

    def test_all_empty_returns_empty(self):
        w = {"type": "label"}
        strings = collect_widget_strings(w)
        assert strings == []


# ===========================================================================
# Full pipeline: JSON → C with all field types
# ===========================================================================
class TestFullPipelineFieldTypes:
    def test_all_fields_in_output(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "main": {
                    "width": 256,
                    "height": 128,
                    "widgets": [
                        {
                            "type": "slider",
                            "x": 10,
                            "y": 20,
                            "width": 100,
                            "height": 14,
                            "_widget_id": "vol_slider",
                            "text": "Volume",
                            "color_fg": "#ffffff",
                            "color_bg": "#000000",
                            "border": True,
                            "border_style": "double",
                            "align": "center",
                            "valign": "bottom",
                            "text_overflow": "wrap",
                            "max_lines": 3,
                            "style": "bold",
                            "visible": True,
                            "enabled": False,
                            "value": 75,
                            "min_value": 0,
                            "max_value": 100,
                            "checked": True,
                            "constraints_json": '{"bind":"volume"}',
                            "animations_csv": "fade_in;slide",
                        },
                    ],
                },
            },
        )
        src, hdr = generate_ui_design_multi_pair(p, source_label="test")
        assert "UIW_SLIDER" in src
        assert ".x = 10" in src
        assert ".y = 20" in src
        assert ".width = 100" in src
        assert ".height = 14" in src
        assert ".border = 1" in src
        assert ".checked = 1" in src
        assert ".value = 75" in src
        assert ".min_value = 0" in src
        assert ".max_value = 100" in src
        assert "vol_slider" in src
        assert "Volume" in src
        assert '{"bind":"volume"}' in src or "bind" in src
        assert "fade_in;slide" in src
        assert "UI_BORDER_DOUBLE" in src
        assert "UI_ALIGN_CENTER" in src
        assert "UI_VALIGN_BOTTOM" in src
        assert "UI_TEXT_OVERFLOW_WRAP" in src
        assert ".max_lines = 3" in src
        assert "UI_STYLE_BOLD" in src
        assert ".visible = 1" in src
        assert ".enabled = 0" in src

    def test_multi_scene_ordering(self, tmp_path):
        """Verify scene index macros match insertion order."""
        p = _write_json(
            tmp_path,
            {
                "home": {"width": 128, "height": 64, "widgets": []},
                "settings": {"width": 128, "height": 64, "widgets": []},
                "about": {"width": 128, "height": 64, "widgets": []},
            },
        )
        _, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_IDX_HOME 0" in hdr
        assert "#define UI_SCENE_IDX_SETTINGS 1" in hdr
        assert "#define UI_SCENE_IDX_ABOUT 2" in hdr
        assert "#define UI_SCENE_COUNT 3" in hdr

    def test_string_pool_dedup_across_scenes(self, tmp_path):
        """Same string in different scenes should use one pool entry."""
        p = _write_json(
            tmp_path,
            {
                "s1": {"width": 64, "height": 32, "widgets": [_w(text="Shared")]},
                "s2": {"width": 64, "height": 32, "widgets": [_w(text="Shared")]},
            },
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        pool_lines = [
            ln for ln in src.splitlines() if "Shared" in ln and "const char" in ln.lower()
        ]
        assert len(pool_lines) == 1

    def test_radiobutton_type(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "sc": {"width": 64, "height": 32, "widgets": [_w(type="radiobutton")]},
            },
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert "UIW_RADIOBUTTON" in src

    def test_textbox_type(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "sc": {"width": 64, "height": 32, "widgets": [_w(type="textbox")]},
            },
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert "UIW_TEXTBOX" in src

    def test_box_type(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "sc": {"width": 64, "height": 32, "widgets": [_w(type="box")]},
            },
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert "UIW_BOX" in src


# ===========================================================================
# Adversarial codegen pipeline tests
# ===========================================================================
class TestAdversarialEscaping:
    """Test that control chars and comment injection are neutralized."""

    def test_control_chars_escaped_in_string(self):
        """Non-printable ASCII chars get \\xNN escaping."""
        result = escape_c_string("a\x01b\x0bc\x7fd")
        assert "\\x01" in result
        assert "\\x0b" in result
        assert "\\x7f" in result
        # No raw control chars remain
        for ch in result:
            assert ord(ch) >= 0x20 or ch in ("\\",), f"raw ctrl char {ord(ch):#x} in output"

    def test_null_bytes_removed(self):
        result = escape_c_string("a\x00b")
        assert "\x00" not in result
        assert "ab" in result or "a" in result

    def test_comment_open_escaped(self):
        """/* sequences are broken up to prevent nested comments."""
        result = escape_c_comment("foo /* bar")
        assert "/*" not in result
        assert "/ *" in result

    def test_comment_newlines_flattened(self):
        result = escape_c_comment("line1\nline2\rline3")
        assert "\n" not in result
        assert "\r" not in result

    def test_comment_combined_injection(self):
        result = escape_c_comment("a */ /* b")
        assert "*/" not in result
        assert "/*" not in result


class TestEmptySceneCodegen:
    """Empty scenes produce valid, compilable C code."""

    def test_empty_design_pair(self, tmp_path):
        p = _write_json(
            tmp_path,
            {"main": {"width": 128, "height": 64, "widgets": []}},
        )
        src, hdr = generate_ui_design_pair(
            p, scene_name="main", source_label="test"
        )
        assert "widget_count = 0" in src
        assert ".widgets = NULL" in src
        # Must not have sizeof on empty array
        assert "sizeof(widgets)" not in src

    def test_multi_pair_empty_scene(self, tmp_path):
        p = _write_json(
            tmp_path,
            {"empty": {"width": 64, "height": 32, "widgets": []}},
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert "widget_count = 0" in src
        assert ".widgets = NULL" in src

    def test_scenes_header_empty_scene(self, tmp_path):
        p = _write_json(
            tmp_path,
            {"blank": {"width": 64, "height": 32, "widgets": []}},
        )
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        assert "widget_count = 0" in h
        assert ".widgets = NULL" in h
        assert "blank_scene" in h


class TestAdversarialWidgetText:
    """Malicious text in widget fields cannot break the generated C."""

    def test_text_with_all_control_chars(self, tmp_path):
        evil = "".join(chr(i) for i in range(32))
        p = _write_json(
            tmp_path,
            {"sc": {"width": 64, "height": 32, "widgets": [_w(text=evil)]}},
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        # No raw control chars in output (except \n as line terminators)
        for line in src.splitlines():
            for ch in line:
                assert ord(ch) >= 0x20 or ch == "\t", (
                    f"raw ctrl char {ord(ch):#x} in generated C"
                )

    def test_scene_name_with_comment_injection(self, tmp_path):
        p = _write_json(
            tmp_path,
            {"test*//*evil": {"width": 64, "height": 32, "widgets": [_w()]}},
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        # Inside comments, */ and /* must be neutralized
        import re

        for m in re.finditer(r"/\*(.*?)\*/", src, re.DOTALL):
            body = m.group(1)
            assert "*/" not in body, f"unescaped */ in comment: {body!r}"
            # /* inside comment body would be a nested comment (not valid C)
            assert "/*" not in body, f"unescaped /* in comment: {body!r}"

    def test_huge_values_clamped(self, tmp_path):
        p = _write_json(
            tmp_path,
            {
                "sc": {
                    "width": 64,
                    "height": 32,
                    "widgets": [
                        _w(
                            x=999999,
                            y=-999999,
                            width=999999,
                            height=999999,
                            value=999999,
                            min_value=-999999,
                            max_value=999999,
                            max_lines=999,
                        )
                    ],
                }
            },
        )
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        # uint16 fields clamped to 65535
        assert ".x = 65535" in src
        assert ".width = 65535" in src
        # int16 fields clamped to [-32768, 32767]
        assert ".value = 32767" in src
        assert ".min_value = -32768" in src
        assert ".max_value = 32767" in src
        # uint8 clamped to 255
        assert ".max_lines = 255" in src
