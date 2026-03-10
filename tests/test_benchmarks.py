"""Performance benchmarks for critical Python paths.

Run with: pytest tests/test_benchmarks.py --benchmark-only
"""

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.ui_codegen import (
    build_string_pool,
    escape_c_string,
    generate_ui_design_pair,
    parse_gray4,
    style_expr,
)
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_scene_json(tmp_path):
    """5-widget scene JSON."""
    d = UIDesigner(128, 64)
    s = d.create_scene("bench")
    d.current_scene = s.name
    for i in range(5):
        s.widgets.append(WidgetConfig(
            type="button", x=i * 20, y=10, width=18, height=10, text=f"Btn{i}",
        ))
    path = tmp_path / "small.json"
    d.save_to_json(str(path))
    return path


@pytest.fixture
def medium_scene_json(tmp_path):
    """50-widget scene JSON."""
    d = UIDesigner(256, 128)
    s = d.create_scene("bench")
    d.current_scene = s.name
    types = ["label", "button", "box", "gauge", "progressbar", "checkbox", "slider"]
    for i in range(50):
        wtype = types[i % len(types)]
        s.widgets.append(WidgetConfig(
            type=wtype,
            x=(i % 10) * 24,
            y=(i // 10) * 20,
            width=22,
            height=18,
            text=f"W{i:03d}",
        ))
    path = tmp_path / "medium.json"
    d.save_to_json(str(path))
    return path


@pytest.fixture
def large_scene_json(tmp_path):
    """200-widget scene JSON (stress test)."""
    d = UIDesigner(256, 128)
    s = d.create_scene("bench")
    d.current_scene = s.name
    types = ["label", "button", "box", "gauge", "progressbar", "checkbox", "slider", "panel"]
    for i in range(200):
        wtype = types[i % len(types)]
        s.widgets.append(WidgetConfig(
            type=wtype,
            x=(i % 16) * 16,
            y=(i // 16) * 8,
            width=14,
            height=7,
            text=f"Widget{i:04d}",
        ))
    path = tmp_path / "large.json"
    d.save_to_json(str(path))
    return path


# ---------------------------------------------------------------------------
# JSON Save/Load Benchmarks
# ---------------------------------------------------------------------------

class TestJsonBenchmarks:
    def test_save_small(self, benchmark, tmp_path):
        d = UIDesigner(128, 64)
        s = d.create_scene("b")
        d.current_scene = s.name
        for i in range(5):
            s.widgets.append(WidgetConfig(type="button", x=i*20, y=10, width=18, height=10, text=f"B{i}"))
        path = str(tmp_path / "out.json")
        benchmark(d.save_to_json, path)

    def test_load_small(self, benchmark, small_scene_json):
        def _load():
            d = UIDesigner()
            d.load_from_json(str(small_scene_json))
        benchmark(_load)

    def test_save_medium(self, benchmark, tmp_path):
        d = UIDesigner(256, 128)
        s = d.create_scene("b")
        d.current_scene = s.name
        types = ["label", "button", "box", "gauge"]
        for i in range(50):
            s.widgets.append(WidgetConfig(
                type=types[i%len(types)], x=(i%10)*24, y=(i//10)*20,
                width=22, height=18, text=f"W{i}",
            ))
        path = str(tmp_path / "out.json")
        benchmark(d.save_to_json, path)

    def test_load_medium(self, benchmark, medium_scene_json):
        def _load():
            d = UIDesigner()
            d.load_from_json(str(medium_scene_json))
        benchmark(_load)


# ---------------------------------------------------------------------------
# Codegen Benchmarks
# ---------------------------------------------------------------------------

class TestCodegenBenchmarks:
    def test_codegen_small(self, benchmark, small_scene_json):
        benchmark(generate_ui_design_pair, small_scene_json, scene_name="bench", source_label="bench")

    def test_codegen_medium(self, benchmark, medium_scene_json):
        benchmark(generate_ui_design_pair, medium_scene_json, scene_name="bench", source_label="bench")

    def test_codegen_large(self, benchmark, large_scene_json):
        benchmark(generate_ui_design_pair, large_scene_json, scene_name="bench", source_label="bench")


# ---------------------------------------------------------------------------
# Utility Function Benchmarks
# ---------------------------------------------------------------------------

class TestUtilBenchmarks:
    def test_escape_c_string_short(self, benchmark):
        benchmark(escape_c_string, 'Hello "world"')

    def test_escape_c_string_long(self, benchmark):
        s = 'Line with "quotes" and \\backslashes\n' * 100
        benchmark(escape_c_string, s)

    def test_parse_gray4_hex(self, benchmark):
        benchmark(parse_gray4, "#AABBCC", default=0)

    def test_parse_gray4_name(self, benchmark):
        benchmark(parse_gray4, "white", default=0)

    def test_style_expr(self, benchmark):
        benchmark(style_expr, "inverse highlight bold")

    def test_build_string_pool_50(self, benchmark):
        strings = [f"string_{i}" for i in range(50)]
        benchmark(build_string_pool, strings, symbol_prefix="sp")


# ---------------------------------------------------------------------------
# Designer Operations Benchmarks
# ---------------------------------------------------------------------------

class TestDesignerBenchmarks:
    def test_create_scene_with_50_widgets(self, benchmark):
        def _create():
            d = UIDesigner(256, 128)
            s = d.create_scene("b")
            d.current_scene = s.name
            for i in range(50):
                s.widgets.append(WidgetConfig(
                    type="button", x=i*5, y=i*2, width=10, height=8, text=f"B{i}",
                ))
        benchmark(_create)

    def test_full_pipeline_small(self, benchmark, tmp_path):
        """Full pipeline: create → save → load → codegen."""
        json_path = str(tmp_path / "pipeline.json")
        def _pipeline():
            d = UIDesigner(128, 64)
            s = d.create_scene("pipe")
            d.current_scene = s.name
            for i in range(5):
                s.widgets.append(WidgetConfig(
                    type="button", x=i*20, y=10, width=18, height=10, text=f"B{i}",
                ))
            d.save_to_json(json_path)
            d2 = UIDesigner()
            d2.load_from_json(json_path)
            generate_ui_design_pair(Path(json_path), scene_name="pipe", source_label="test")
        benchmark(_pipeline)
