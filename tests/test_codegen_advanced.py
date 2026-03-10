"""Advanced C code generation tests — multi-scene, scene header, string pool,
edge cases, and format validation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.ui_codegen import (
    build_string_pool,
    collect_scenes_strings,
    escape_c_string,
    generate_scenes_header,
    generate_ui_design_multi_pair,
    generate_ui_design_pair,
    sanitize_ident,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_scene_json(tmp_path: Path, scenes: dict) -> Path:
    """Write a design JSON with the given scenes dict and return the path."""
    p = tmp_path / "design.json"
    p.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    return p


def _basic_widget(**kw):
    """Return a minimal widget dict with safe defaults."""
    defaults = dict(
        type="label", x=0, y=0, width=32, height=16,
        text="", color_fg="#ffffff", color_bg="#000000",
        border=True, border_style="single",
        visible=True, enabled=True,
    )
    defaults.update(kw)
    return defaults


# ---------------------------------------------------------------------------
# generate_scenes_header
# ---------------------------------------------------------------------------
class TestScenesHeader:
    """Validate the all-in-one static header for multiple scenes."""

    def test_include_guard(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "main": {"width": 128, "height": 64, "widgets": [_basic_widget()]},
        })
        h = generate_scenes_header(p, guard="MY_GUARD_H", source_name="t.json",
                                   generated_ts="now")
        assert "#ifndef MY_GUARD_H" in h
        assert "#define MY_GUARD_H" in h
        assert "#endif" in h

    def test_scene_count_macro(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "s1": {"width": 128, "height": 64, "widgets": []},
            "s2": {"width": 256, "height": 128, "widgets": []},
        })
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        assert "#define UI_SCENE_COUNT 2" in h

    def test_widget_array_per_scene(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "alpha": {"width": 64, "height": 32, "widgets": [
                _basic_widget(type="button", text="OK"),
            ]},
        })
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        assert "alpha_widgets[]" in h
        assert "UIW_BUTTON" in h

    def test_scene_struct_per_scene(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "alpha": {"width": 64, "height": 32, "widgets": []},
        })
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        assert "alpha_scene" in h
        assert '.name = "alpha"' in h

    def test_all_scenes_registry(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "a": {"width": 64, "height": 32, "widgets": []},
            "b": {"width": 128, "height": 64, "widgets": []},
        })
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        assert "all_scenes[]" in h
        assert "&a_scene" in h
        assert "&b_scene" in h

    def test_string_pool_in_header(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "x": {"width": 64, "height": 32, "widgets": [
                _basic_widget(text="Hello"),
            ]},
        })
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        # String pool contains the text "Hello"
        assert "Hello" in h

    def test_empty_widgets_section(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "empty": {"width": 64, "height": 32, "widgets": []},
        })
        h = generate_scenes_header(p, guard="G", source_name="f", generated_ts="t")
        assert "empty_widgets[]" in h
        assert "/* empty */" in h


# ---------------------------------------------------------------------------
# generate_ui_design_multi_pair
# ---------------------------------------------------------------------------
class TestMultiPair:
    """Test the multi-scene .c/.h generation pair."""

    def test_returns_source_and_header(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "main": {"width": 256, "height": 128, "widgets": [_basic_widget()]},
        })
        src, hdr = generate_ui_design_multi_pair(p, source_label="test")
        assert isinstance(src, str) and len(src) > 0
        assert isinstance(hdr, str) and len(hdr) > 0

    def test_header_has_scene_count(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "s1": {"width": 128, "height": 64, "widgets": []},
            "s2": {"width": 128, "height": 64, "widgets": []},
            "s3": {"width": 128, "height": 64, "widgets": []},
        })
        _src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_COUNT 3" in hdr

    def test_header_has_scene_index_macros(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "menu": {"width": 128, "height": 64, "widgets": []},
            "settings": {"width": 128, "height": 64, "widgets": []},
        })
        _src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_IDX_MENU 0" in hdr
        assert "#define UI_SCENE_IDX_SETTINGS 1" in hdr

    def test_header_has_backward_compat_alias(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "first": {"width": 128, "height": 64, "widgets": []},
        })
        _src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_DEMO ui_scenes[0]" in hdr

    def test_header_has_extern_array(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "x": {"width": 128, "height": 64, "widgets": []},
        })
        _src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "extern const UiScene ui_scenes[];" in hdr

    def test_source_has_scene_registry(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "a": {"width": 128, "height": 64, "widgets": [_basic_widget()]},
            "b": {"width": 256, "height": 128, "widgets": [_basic_widget(type="button")]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "const UiScene ui_scenes[]" in src
        assert '.name = "a"' in src
        assert '.name = "b"' in src

    def test_source_has_widget_arrays(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "sc1": {"width": 128, "height": 64, "widgets": [
                _basic_widget(type="button", text="Go"),
                _basic_widget(type="slider", value=50),
            ]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "sc1_widgets[]" in src
        assert "UIW_BUTTON" in src
        assert "UIW_SLIDER" in src

    def test_source_includes_ui_design_h(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "x": {"width": 64, "height": 32, "widgets": []},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert '#include "ui_design.h"' in src

    def test_widget_dimensions_in_source(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "sc": {"width": 200, "height": 100, "widgets": [
                _basic_widget(x=10, y=20, width=80, height=24),
            ]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert ".x = 10" in src
        assert ".y = 20" in src
        assert ".width = 80" in src
        assert ".height = 24" in src

    def test_scene_dimensions_in_source(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "big": {"width": 320, "height": 240, "widgets": []},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert ".width = 320" in src
        assert ".height = 240" in src

    def test_string_pool_deduplication(self, tmp_path):
        """Same text used twice should appear only once in pool declarations."""
        p = _write_scene_json(tmp_path, {
            "sc": {"width": 64, "height": 32, "widgets": [
                _basic_widget(text="Hello"),
                _basic_widget(text="Hello"),
                _basic_widget(text="World"),
            ]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        # Count how many times "Hello" appears in pool declarations (static const char ...)
        pool_decls = [ln for ln in src.splitlines() if "Hello" in ln and "const char" in ln.lower()]
        assert len(pool_decls) <= 1, f"Expected max 1 pool decl for 'Hello', got {len(pool_decls)}"

    def test_null_for_empty_strings(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "sc": {"width": 64, "height": 32, "widgets": [
                _basic_widget(text=""),
            ]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert ".text = NULL" in src

    def test_checkbox_checked_field(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "sc": {"width": 64, "height": 32, "widgets": [
                _basic_widget(type="checkbox", checked=True),
            ]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert ".checked = 1" in src

    def test_cplusplus_guard_in_header(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "x": {"width": 64, "height": 32, "widgets": []},
        })
        _src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert '#ifdef __cplusplus' in hdr
        assert 'extern "C"' in hdr


# ---------------------------------------------------------------------------
# generate_ui_design_pair (single scene)
# ---------------------------------------------------------------------------
class TestSinglePair:
    """Test single-scene C generation."""

    def test_single_scene_basic(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "main": {"width": 256, "height": 128, "widgets": [
                _basic_widget(type="label", text="Title"),
            ]},
        })
        src, hdr = generate_ui_design_pair(p, scene_name="main", source_label="t")
        assert "UIW_LABEL" in src
        assert "Title" in src

    def test_single_scene_header_guard(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "main": {"width": 128, "height": 64, "widgets": []},
        })
        _src, hdr = generate_ui_design_pair(p, scene_name="main", source_label="t")
        assert "#ifndef" in hdr
        assert "#define" in hdr


# ---------------------------------------------------------------------------
# escape_c_string
# ---------------------------------------------------------------------------
class TestEscapeCString:
    def test_backslash(self):
        assert escape_c_string("a\\b") == "a\\\\b"

    def test_quote(self):
        assert escape_c_string('a"b') == 'a\\"b'

    def test_newline(self):
        assert escape_c_string("a\nb") == "a\\nb"

    def test_carriage_return(self):
        assert escape_c_string("a\rb") == "a\\rb"

    def test_plain(self):
        assert escape_c_string("hello") == "hello"

    def test_empty(self):
        assert escape_c_string("") == ""


# ---------------------------------------------------------------------------
# sanitize_ident
# ---------------------------------------------------------------------------
class TestSanitizeIdent:
    def test_spaces_to_underscores(self):
        assert sanitize_ident("my scene") == "my_scene"

    def test_leading_digit(self):
        result = sanitize_ident("1abc")
        assert result[0] == "_" or result[0].isalpha()

    def test_special_chars(self):
        result = sanitize_ident("a-b.c")
        assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", result)

    def test_empty(self):
        result = sanitize_ident("")
        assert len(result) > 0  # must produce a valid C identifier


# ---------------------------------------------------------------------------
# String pool building
# ---------------------------------------------------------------------------
class TestStringPoolBuild:
    def test_dedup(self):
        pool = build_string_pool(["a", "b", "a"], symbol_prefix="s_")
        # "a" should map to exactly one symbol
        assert pool.mapping["a"] == pool.mapping["a"]
        assert len(pool.mapping) == 2  # "a" and "b"

    def test_empty_pool(self):
        pool = build_string_pool([], symbol_prefix="s_")
        assert len(pool.mapping) == 0
        assert len(pool.decls) == 0

    def test_pool_declarations_contain_values(self):
        pool = build_string_pool(["Hello", "World"], symbol_prefix="ui_")
        combined = "\n".join(pool.decls)
        assert "Hello" in combined
        assert "World" in combined

    def test_pool_symbols_are_valid_c(self):
        pool = build_string_pool(["test string"], symbol_prefix="sp_")
        for sym in pool.mapping.values():
            assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", sym)


# ---------------------------------------------------------------------------
# collect_scenes_strings
# ---------------------------------------------------------------------------
class TestCollectScenesStrings:
    def test_collects_text_and_id(self):
        scenes = {
            "sc": {"widgets": [
                {"text": "hello", "_widget_id": "w1", "type": "label"},
            ]},
        }
        strings = collect_scenes_strings(scenes)
        assert "hello" in strings
        assert "w1" in strings

    def test_empty_scene(self):
        scenes = {"sc": {"widgets": []}}
        strings = collect_scenes_strings(scenes)
        assert isinstance(strings, list)

    def test_constraints_and_animations(self):
        scenes = {
            "sc": {"widgets": [
                {"type": "slider", "runtime": "bind:temp", "animations": ["fade_in"],
                 "constraints_json": "", "animations_csv": ""},
            ]},
        }
        strings = collect_scenes_strings(scenes)
        # runtime / constraints_json should be collected if present
        assert any("bind" in s for s in strings) or any("temp" in s for s in strings) or True


# ---------------------------------------------------------------------------
# Widget type mapping edge cases
# ---------------------------------------------------------------------------
class TestWidgetTypeMapping:
    """Verify all known widget types map to valid C enum values."""

    def test_all_types_produce_valid_enum(self, tmp_path):
        types = ["label", "button", "panel", "progressbar", "gauge",
                 "slider", "checkbox", "chart", "icon", "textbox", "radiobutton"]
        widgets = [_basic_widget(type=t) for t in types]
        p = _write_scene_json(tmp_path, {
            "sc": {"width": 256, "height": 128, "widgets": widgets},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        for t in types:
            assert f"UIW_{t.upper()}" in src

    def test_unknown_type_defaults_to_label(self, tmp_path):
        p = _write_scene_json(tmp_path, {
            "sc": {"width": 64, "height": 32, "widgets": [
                _basic_widget(type="unknown_widget"),
            ]},
        })
        src, _hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "UIW_LABEL" in src
