"""Tests for tools/ui_codegen.py helper functions."""

import json

from tools.ui_codegen import (
    StringPool,
    _get_rgb,
    _hex_to_rgb,
    _rgb_to_gray4,
    align_for,
    as_bool,
    as_int,
    border_style_for,
    build_string_pool,
    collect_scenes_strings,
    collect_widget_strings,
    escape_c_string,
    load_scenes,
    overflow_for,
    parse_gray4,
    sanitize_ident,
    select_scene,
    style_expr,
    valign_for,
    write_if_changed,
)

# ── escape_c_string ──

class TestEscapeCString:
    def test_plain(self):
        assert escape_c_string("hello") == "hello"

    def test_quotes(self):
        assert escape_c_string('say "hi"') == 'say \\"hi\\"'

    def test_backslash(self):
        assert escape_c_string("a\\b") == "a\\\\b"

    def test_newline(self):
        assert escape_c_string("line1\nline2") == "line1\\nline2"

    def test_carriage_return(self):
        assert escape_c_string("a\rb") == "a\\rb"

    def test_none(self):
        assert escape_c_string(None) == ""

    def test_empty(self):
        assert escape_c_string("") == ""

    def test_int_input(self):
        assert escape_c_string(42) == "42"


# ── as_int ──

class TestAsInt:
    def test_int(self):
        assert as_int(5) == 5

    def test_string(self):
        assert as_int("10") == 10

    def test_none(self):
        assert as_int(None) == 0

    def test_none_with_default(self):
        assert as_int(None, 99) == 99

    def test_bad_string(self):
        assert as_int("abc") == 0

    def test_float(self):
        assert as_int(3.7) == 3

    def test_bool(self):
        assert as_int(True) == 1


# ── as_bool ──

class TestAsBool:
    def test_true(self):
        assert as_bool(True) is True

    def test_false(self):
        assert as_bool(False) is False

    def test_none(self):
        assert as_bool(None) is False

    def test_none_default_true(self):
        assert as_bool(None, True) is True

    def test_string_true(self):
        assert as_bool("true") is True

    def test_string_yes(self):
        assert as_bool("yes") is True

    def test_string_1(self):
        assert as_bool("1") is True

    def test_string_on(self):
        assert as_bool("on") is True

    def test_string_false(self):
        assert as_bool("false") is False

    def test_string_no(self):
        assert as_bool("no") is False

    def test_string_0(self):
        assert as_bool("0") is False

    def test_string_off(self):
        assert as_bool("off") is False

    def test_garbage_string(self):
        assert as_bool("maybe") is False


# ── _hex_to_rgb ──

class TestHexToRgb:
    def test_white(self):
        assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)

    def test_black(self):
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_red(self):
        assert _hex_to_rgb("#FF0000") == (255, 0, 0)

    def test_no_hash(self):
        assert _hex_to_rgb("00FF00") == (0, 255, 0)

    def test_short_hex_fallback(self):
        assert _hex_to_rgb("#FFF") == (255, 255, 255)  # Too short, defaults

    def test_empty(self):
        assert _hex_to_rgb("") == (255, 255, 255)

    def test_invalid(self):
        assert _hex_to_rgb("not_a_hex") == (255, 255, 255)


# ── _get_rgb ──

class TestGetRgb:
    def test_named_white(self):
        assert _get_rgb("white") == (255, 255, 255)

    def test_named_black(self):
        assert _get_rgb("black") == (0, 0, 0)

    def test_named_red(self):
        assert _get_rgb("red") == (255, 0, 0)

    def test_hex(self):
        assert _get_rgb("#00FF00") == (0, 255, 0)

    def test_unknown_name(self):
        assert _get_rgb("chartreuse") == (255, 255, 255)

    def test_none(self):
        assert _get_rgb(None) == (255, 255, 255)

    def test_gray_alias(self):
        assert _get_rgb("grey") == (128, 128, 128)
        assert _get_rgb("gray") == (128, 128, 128)


# ── _rgb_to_gray4 ──

class TestRgbToGray4:
    def test_white(self):
        assert _rgb_to_gray4(255, 255, 255) == 15

    def test_black(self):
        assert _rgb_to_gray4(0, 0, 0) == 0

    def test_mid_gray(self):
        g = _rgb_to_gray4(128, 128, 128)
        assert 7 <= g <= 8

    def test_clamped_high(self):
        assert _rgb_to_gray4(999, 999, 999) <= 15

    def test_red(self):
        # ~0.2126*255 = 54.2 → 54.2/255*15 ≈ 3.2 → 3
        g = _rgb_to_gray4(255, 0, 0)
        assert 2 <= g <= 4


# ── parse_gray4 ──

class TestParseGray4:
    def test_white(self):
        assert parse_gray4("white", default=0) == 15

    def test_black(self):
        assert parse_gray4("black", default=15) == 0

    def test_hex(self):
        v = parse_gray4("#808080", default=0)
        assert 7 <= v <= 8

    def test_empty_returns_default(self):
        assert parse_gray4("", default=7) == 7

    def test_none_returns_default(self):
        assert parse_gray4(None, default=10) == 10


# ── style_expr ──

class TestStyleExpr:
    def test_none(self):
        assert style_expr(None) == "UI_STYLE_NONE"

    def test_empty(self):
        assert style_expr("") == "UI_STYLE_NONE"

    def test_bold(self):
        assert style_expr("bold") == "UI_STYLE_BOLD"

    def test_inverse(self):
        assert style_expr("inverse") == "UI_STYLE_INVERSE"

    def test_highlight(self):
        assert style_expr("highlight") == "UI_STYLE_HIGHLIGHT"

    def test_combined(self):
        expr = style_expr("bold inverse")
        assert "UI_STYLE_INVERSE" in expr
        assert "UI_STYLE_BOLD" in expr
        assert "|" in expr

    def test_default_no_flags(self):
        assert style_expr("default") == "UI_STYLE_NONE"

    def test_case_insensitive(self):
        assert style_expr("BOLD") == "UI_STYLE_BOLD"


# ── build_string_pool ──

class TestBuildStringPool:
    def test_basic(self):
        pool = build_string_pool(["hello", "world"], symbol_prefix="s_")
        assert isinstance(pool, StringPool)
        assert "hello" in pool.mapping
        assert "world" in pool.mapping
        assert len(pool.decls) == 2

    def test_dedup(self):
        pool = build_string_pool(["a", "b", "a", "c"], symbol_prefix="p_")
        assert len(pool.mapping) == 3
        assert len(pool.decls) == 3

    def test_empty_strings_skipped(self):
        pool = build_string_pool(["", "x", ""], symbol_prefix="t_")
        assert len(pool.mapping) == 1

    def test_symbol_naming(self):
        pool = build_string_pool(["one", "two"], symbol_prefix="str_")
        assert pool.mapping["one"] == "str_0"
        assert pool.mapping["two"] == "str_1"

    def test_decls_contain_c_strings(self):
        pool = build_string_pool(["hi"], symbol_prefix="s_")
        assert 'static const char s_0[] = "hi";' in pool.decls[0]

    def test_empty_input(self):
        pool = build_string_pool([], symbol_prefix="s_")
        assert pool.mapping == {}
        assert pool.decls == []


# ── sanitize_ident ──

class TestSanitizeIdent:
    def test_simple(self):
        assert sanitize_ident("main") == "main"

    def test_spaces(self):
        assert sanitize_ident("my scene") == "my_scene"

    def test_starts_with_digit(self):
        assert sanitize_ident("1st_scene") == "scene_1st_scene"

    def test_empty(self):
        assert sanitize_ident("") == "scene"

    def test_special_chars(self):
        assert sanitize_ident("hello-world!") == "hello_world_"

    def test_uppercase(self):
        assert sanitize_ident("MyScene") == "myscene"


# ── select_scene ──

class TestSelectScene:
    def test_dict_prefer_name(self):
        data = {"scenes": {"main": {"width": 128}, "alt": {"width": 64}}}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc["width"] == 128

    def test_dict_fallback(self):
        data = {"scenes": {"alt": {"width": 64}}}
        name, sc = select_scene(data, "missing")
        assert name == "alt"
        assert sc["width"] == 64

    def test_dict_empty_scenes(self):
        data = {"scenes": {}}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc == {}

    def test_list_scenes(self):
        data = {"scenes": [{"name": "first", "width": 100}]}
        name, sc = select_scene(data, "any")
        assert name == "first"
        assert sc["width"] == 100

    def test_no_scenes_key(self):
        data = {}
        name, sc = select_scene(data, "main")
        assert name == "main"
        assert sc == {}


# ── collect_widget_strings ──


class TestCollectWidgetStrings:
    def test_text_and_id(self):
        w = {"_widget_id": "btn1", "text": "OK"}
        result = collect_widget_strings(w)
        assert "btn1" in result
        assert "OK" in result

    def test_runtime_as_constraints(self):
        w = {"runtime": "val=sensor.temp"}
        result = collect_widget_strings(w)
        assert "val=sensor.temp" in result

    def test_animations_list_joined(self):
        w = {"animations": ["fade", "slide"]}
        result = collect_widget_strings(w)
        assert "fade;slide" in result

    def test_empty_widget(self):
        assert collect_widget_strings({}) == []

    def test_empty_text_excluded(self):
        w = {"text": "", "_widget_id": ""}
        assert collect_widget_strings(w) == []


# ── collect_scenes_strings ──


class TestCollectScenesStrings:
    def test_single_scene(self):
        scenes = {"main": {"widgets": [{"text": "hi", "_widget_id": "lbl"}]}}
        result = collect_scenes_strings(scenes)
        assert "hi" in result
        assert "lbl" in result

    def test_multiple_scenes(self):
        scenes = {
            "a": {"widgets": [{"text": "A"}]},
            "b": {"widgets": [{"text": "B"}]},
        }
        result = collect_scenes_strings(scenes)
        assert "A" in result
        assert "B" in result

    def test_empty_scenes(self):
        assert collect_scenes_strings({}) == []


# ── border_style_for ──


class TestBorderStyleFor:
    def test_no_border(self):
        assert border_style_for({}, border=0) == "UI_BORDER_NONE"

    def test_single(self):
        assert border_style_for({"border_style": "single"}, border=1) == "UI_BORDER_SINGLE"

    def test_double(self):
        assert border_style_for({"border_style": "double"}, border=1) == "UI_BORDER_DOUBLE"

    def test_rounded(self):
        assert border_style_for({"border_style": "rounded"}, border=1) == "UI_BORDER_ROUNDED"

    def test_default_single(self):
        assert border_style_for({}, border=1) == "UI_BORDER_SINGLE"

    def test_unknown_defaults_single(self):
        assert border_style_for({"border_style": "fancy"}, border=1) == "UI_BORDER_SINGLE"


# ── align_for ──


class TestAlignFor:
    def test_left(self):
        assert align_for({"align": "left"}) == "UI_ALIGN_LEFT"

    def test_center(self):
        assert align_for({"align": "center"}) == "UI_ALIGN_CENTER"

    def test_right(self):
        assert align_for({"align": "right"}) == "UI_ALIGN_RIGHT"

    def test_default_left(self):
        assert align_for({}) == "UI_ALIGN_LEFT"

    def test_unknown_defaults_left(self):
        assert align_for({"align": "justify"}) == "UI_ALIGN_LEFT"


# ── valign_for ──


class TestValignFor:
    def test_top(self):
        assert valign_for({"valign": "top"}) == "UI_VALIGN_TOP"

    def test_middle(self):
        assert valign_for({"valign": "middle"}) == "UI_VALIGN_MIDDLE"

    def test_bottom(self):
        assert valign_for({"valign": "bottom"}) == "UI_VALIGN_BOTTOM"

    def test_default_middle(self):
        assert valign_for({}) == "UI_VALIGN_MIDDLE"


# ── overflow_for ──


class TestOverflowFor:
    def test_ellipsis(self):
        assert overflow_for({"text_overflow": "ellipsis"}) == "UI_TEXT_OVERFLOW_ELLIPSIS"

    def test_wrap(self):
        assert overflow_for({"text_overflow": "wrap"}) == "UI_TEXT_OVERFLOW_WRAP"

    def test_clip(self):
        assert overflow_for({"text_overflow": "clip"}) == "UI_TEXT_OVERFLOW_CLIP"

    def test_auto(self):
        assert overflow_for({"text_overflow": "auto"}) == "UI_TEXT_OVERFLOW_AUTO"

    def test_default_ellipsis(self):
        assert overflow_for({}) == "UI_TEXT_OVERFLOW_ELLIPSIS"


# ── write_if_changed ──


class TestWriteIfChanged:
    def test_creates_new_file(self, tmp_path):
        p = tmp_path / "out.c"
        assert write_if_changed(p, "hello") is True
        assert p.read_text() == "hello"

    def test_same_content_returns_false(self, tmp_path):
        p = tmp_path / "out.c"
        p.write_text("hello", encoding="utf-8", newline="\n")
        assert write_if_changed(p, "hello") is False

    def test_different_content_rewrites(self, tmp_path):
        p = tmp_path / "out.c"
        p.write_text("old", encoding="utf-8", newline="\n")
        assert write_if_changed(p, "new") is True
        assert p.read_text() == "new"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "sub" / "dir" / "out.h"
        assert write_if_changed(p, "/* header */") is True
        assert p.exists()


# ── load_scenes ──


class TestLoadScenes:
    def test_dict_scenes(self, tmp_path):
        p = tmp_path / "test.json"
        data = {"scenes": {"main": {"widgets": []}}}
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert "main" in result

    def test_list_scenes(self, tmp_path):
        p = tmp_path / "test.json"
        data = {"scenes": [{"name": "s1", "widgets": []}, {"id": "s2", "widgets": []}]}
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert "s1" in result
        assert "s2" in result

    def test_missing_scenes_returns_empty(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text("{}", encoding="utf-8")
        result = load_scenes(p)
        assert result == {}

    def test_list_scene_fallback_index(self, tmp_path):
        p = tmp_path / "test.json"
        data = {"scenes": [{"widgets": []}]}
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_scenes(p)
        assert "scene_0" in result
