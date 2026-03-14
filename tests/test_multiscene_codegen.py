"""End-to-end tests for multi-scene codegen using the real main_scene.json.

Verifies that generate_ui_design_multi_pair() produces correct C source
and header for all 3 scenes (main, settings, metrics) with accurate
widget counts, scene indices, defines, and structural integrity.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools.ui_codegen import generate_ui_design_multi_pair, load_scenes

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_SCENE_JSON = REPO_ROOT / "main_scene.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(tmp_path: Path, scenes: dict) -> Path:
    p = tmp_path / "design.json"
    p.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    return p


def _w(**kw):
    defaults = dict(type="label", x=0, y=0, width=32, height=16)
    defaults.update(kw)
    return defaults


# ===========================================================================
# Real main_scene.json E2E — header
# ===========================================================================
class TestMultiSceneHeaderReal:
    """Tests against the real main_scene.json shipped in the repo."""

    @pytest.fixture
    def pair(self):
        if not MAIN_SCENE_JSON.exists():
            pytest.skip("main_scene.json not found")
        return generate_ui_design_multi_pair(MAIN_SCENE_JSON, source_label="test")

    def test_scene_count_is_3(self, pair):
        _, hdr = pair
        assert "#define UI_SCENE_COUNT 3" in hdr

    def test_scene_index_main(self, pair):
        _, hdr = pair
        assert "#define UI_SCENE_IDX_MAIN 0" in hdr

    def test_scene_index_settings(self, pair):
        _, hdr = pair
        assert "#define UI_SCENE_IDX_SETTINGS 1" in hdr

    def test_scene_index_metrics(self, pair):
        _, hdr = pair
        assert "#define UI_SCENE_IDX_METRICS 2" in hdr

    def test_backward_compat_alias(self, pair):
        _, hdr = pair
        assert "#define UI_SCENE_DEMO ui_scenes[0]" in hdr

    def test_extern_scenes_array(self, pair):
        _, hdr = pair
        assert "extern const UiScene ui_scenes[];" in hdr

    def test_includes_ui_scene_h(self, pair):
        _, hdr = pair
        assert '#include "ui_scene.h"' in hdr

    def test_header_guard(self, pair):
        _, hdr = pair
        assert "#ifndef UI_DESIGN_H" in hdr
        assert "#define UI_DESIGN_H" in hdr
        assert "#endif" in hdr

    def test_cpp_guard(self, pair):
        _, hdr = pair
        assert '#ifdef __cplusplus' in hdr
        assert 'extern "C"' in hdr

    def test_constraints_and_animations_enabled(self, pair):
        _, hdr = pair
        assert "#define UI_ENABLE_CONSTRAINTS 1" in hdr
        assert "#define UI_ENABLE_ANIMATIONS  1" in hdr


# ===========================================================================
# Real main_scene.json E2E — source
# ===========================================================================
class TestMultiSceneSourceReal:
    """Tests against the generated .c source from main_scene.json."""

    @pytest.fixture
    def pair(self):
        if not MAIN_SCENE_JSON.exists():
            pytest.skip("main_scene.json not found")
        return generate_ui_design_multi_pair(MAIN_SCENE_JSON, source_label="test")

    def test_includes_ui_design_h(self, pair):
        src, _ = pair
        assert '#include "ui_design.h"' in src

    def test_has_string_pool(self, pair):
        src, _ = pair
        assert "String pool" in src

    # --- Scene widget arrays ---

    def test_main_widgets_array(self, pair):
        src, _ = pair
        assert "static const UiWidget main_widgets[]" in src

    def test_settings_widgets_array(self, pair):
        src, _ = pair
        assert "static const UiWidget settings_widgets[]" in src

    def test_metrics_widgets_array(self, pair):
        src, _ = pair
        assert "static const UiWidget metrics_widgets[]" in src

    # --- Scene registry ---

    def test_scene_registry_array(self, pair):
        src, _ = pair
        assert "const UiScene ui_scenes[]" in src

    def test_scene_registry_has_3_entries(self, pair):
        src, _ = pair
        # Each scene adds one '.name = "..."' in the registry
        _names = re.findall(r'\.name\s*=\s*"(\w+)"', src)
        # Filter to only registry entries (after "Scene registry" comment)
        reg_start = src.index("Scene registry")
        reg_src = src[reg_start:]
        reg_names = re.findall(r'\.name\s*=\s*"(\w+)"', reg_src)
        assert len(reg_names) == 3
        assert reg_names == ["main", "settings", "metrics"]

    # --- Widget counts match JSON ---

    def test_main_widget_count_matches(self, pair):
        src, _ = pair
        scenes = load_scenes(MAIN_SCENE_JSON)
        expected = len(scenes["main"]["widgets"])
        comment = f"Scene: main ({expected} widgets)"
        assert comment in src

    def test_settings_widget_count_matches(self, pair):
        src, _ = pair
        scenes = load_scenes(MAIN_SCENE_JSON)
        expected = len(scenes["settings"]["widgets"])
        comment = f"Scene: settings ({expected} widgets)"
        assert comment in src

    def test_metrics_widget_count_matches(self, pair):
        src, _ = pair
        scenes = load_scenes(MAIN_SCENE_JSON)
        expected = len(scenes["metrics"]["widgets"])
        comment = f"Scene: metrics ({expected} widgets)"
        assert comment in src

    # --- Scene dimensions ---

    def test_scene_dimensions_256x128(self, pair):
        src, _ = pair
        assert ".width = 256" in src
        assert ".height = 128" in src

    # --- Widget type diversity ---

    def test_main_has_diverse_widget_types(self, pair):
        src, _ = pair
        for wtype in ["UIW_LABEL", "UIW_BUTTON", "UIW_GAUGE", "UIW_PROGRESSBAR",
                       "UIW_SLIDER", "UIW_CHECKBOX", "UIW_CHART", "UIW_PANEL"]:
            assert wtype in src, f"{wtype} missing from generated source"

    def test_settings_has_slider_and_checkbox(self, pair):
        src, _ = pair
        # Settings scene should have slider for contrast/col_offset and checkbox for invert
        reg_start = src.index("Scene: settings")
        # Find next scene or end
        try:
            reg_end = src.index("Scene: metrics")
        except ValueError:
            reg_end = len(src)
        settings_src = src[reg_start:reg_end]
        assert "UIW_SLIDER" in settings_src
        assert "UIW_CHECKBOX" in settings_src

    def test_metrics_has_gauge_and_chart(self, pair):
        src, _ = pair
        metrics_start = src.index("Scene: metrics")
        metrics_src = src[metrics_start:]
        assert "UIW_GAUGE" in metrics_src
        assert "UIW_CHART" in metrics_src

    # --- Runtime bindings ---

    def test_settings_has_bind_contrast(self, pair):
        src, _ = pair
        assert "bind=contrast" in src

    def test_settings_has_bind_invert(self, pair):
        src, _ = pair
        assert "bind=invert" in src

    def test_settings_has_bind_col_offset(self, pair):
        src, _ = pair
        assert "bind=col_offset" in src


# ===========================================================================
# Synthetic multi-scene E2E — structural validation
# ===========================================================================
class TestMultiSceneSyntheticStructure:
    """Synthetic tests for structural properties of multi-scene codegen."""

    def test_scene_count_matches_input(self, tmp_path):
        p = _write_json(tmp_path, {
            "a": {"width": 64, "height": 32, "widgets": [_w()]},
            "b": {"width": 64, "height": 32, "widgets": [_w()]},
        })
        _, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_COUNT 2" in hdr

    def test_five_scenes(self, tmp_path):
        scenes = {f"s{i}": {"width": 64, "height": 32, "widgets": [_w()]} for i in range(5)}
        p = _write_json(tmp_path, scenes)
        src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_COUNT 5" in hdr
        for i in range(5):
            assert f"#define UI_SCENE_IDX_S{i} {i}" in hdr

    def test_single_scene_still_works(self, tmp_path):
        p = _write_json(tmp_path, {
            "only": {"width": 128, "height": 64, "widgets": [_w(text="Solo")]},
        })
        src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_COUNT 1" in hdr
        assert "Solo" in src
        assert "#define UI_SCENE_DEMO ui_scenes[0]" in hdr

    def test_empty_widgets_produces_null(self, tmp_path):
        p = _write_json(tmp_path, {
            "empty": {"width": 64, "height": 32, "widgets": []},
        })
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert ".widgets = NULL" in src
        assert ".widget_count = 0" in src

    def test_mixed_empty_and_populated(self, tmp_path):
        p = _write_json(tmp_path, {
            "full": {"width": 64, "height": 32, "widgets": [_w(text="Hello")]},
            "empty": {"width": 64, "height": 32, "widgets": []},
        })
        src, hdr = generate_ui_design_multi_pair(p, source_label="t")
        assert "#define UI_SCENE_COUNT 2" in hdr
        assert "Hello" in src
        assert ".widgets = NULL" in src

    def test_widget_sizeof_calculation(self, tmp_path):
        p = _write_json(tmp_path, {
            "sc": {"width": 64, "height": 32, "widgets": [_w(), _w(), _w()]},
        })
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert "sizeof(sc_widgets) / sizeof(sc_widgets[0])" in src

    def test_different_dimensions_per_scene(self, tmp_path):
        p = _write_json(tmp_path, {
            "small": {"width": 64, "height": 32, "widgets": [_w()]},
            "big": {"width": 320, "height": 240, "widgets": [_w()]},
        })
        src, _ = generate_ui_design_multi_pair(p, source_label="t")
        assert ".width = 64" in src
        assert ".height = 32" in src
        assert ".width = 320" in src
        assert ".height = 240" in src


# ===========================================================================
# Load scenes — list vs dict format
# ===========================================================================
class TestLoadScenesFormat:
    def test_dict_format(self, tmp_path):
        p = _write_json(tmp_path, {"a": {"widgets": []}, "b": {"widgets": []}})
        scenes = load_scenes(p)
        assert len(scenes) == 2
        assert "a" in scenes
        assert "b" in scenes

    def test_list_format_uses_name_field(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text(json.dumps({
            "scenes": [
                {"name": "alpha", "widgets": []},
                {"name": "beta", "widgets": []},
            ]
        }), encoding="utf-8")
        scenes = load_scenes(p)
        assert len(scenes) == 2
        assert "alpha" in scenes
        assert "beta" in scenes

    def test_list_format_uses_id_field(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text(json.dumps({
            "scenes": [
                {"id": "first", "widgets": []},
                {"id": "second", "widgets": []},
            ]
        }), encoding="utf-8")
        scenes = load_scenes(p)
        assert "first" in scenes
        assert "second" in scenes

    def test_list_format_fallback_index(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text(json.dumps({
            "scenes": [
                {"widgets": []},
                {"widgets": []},
            ]
        }), encoding="utf-8")
        scenes = load_scenes(p)
        assert "scene_0" in scenes
        assert "scene_1" in scenes

    def test_real_main_scene_loads(self):
        if not MAIN_SCENE_JSON.exists():
            pytest.skip("main_scene.json not found")
        scenes = load_scenes(MAIN_SCENE_JSON)
        assert len(scenes) == 3
        assert "main" in scenes
        assert "settings" in scenes
        assert "metrics" in scenes
