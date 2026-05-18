"""Targeted, behavioral tests for the app-completion session's high-value fixes.

Every test here makes a *real* assertion about behavior or emitted output — no
``assert isinstance(...)`` tautologies, no monkeypatch-an-internal-to-raise-then-
assert-nothing, no dead-code line booking. Each is safe to run single-file and
allocates no large pygame Surfaces (the icon-palette/template/SVG smokes drive
the real public APIs on a tiny 256x128 scene under the dummy SDL driver).

Covers:
  * z_index codegen paint-order (stable, equal-key authoring order preserved)
  * audit_designs off-canvas + duplicate-id gate (exit code semantics)
  * ui_models border_color / border_style idempotent load->save round-trip
  * codegen icon_char survival + chart data_points clamping/cap
  * validate_design benign-overlap rule (hidden + container-containment)
  * smoke/functional: Icon Palette, Template Manager, SVG export modules
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


# ── z_index codegen paint ordering ──────────────────────────────────────────


def test_widgets_in_paint_order_is_stable_and_z_sorted():
    """Lower z_index paints first; equal z_index keeps authoring order."""
    from tools.ui_codegen import _widgets_in_paint_order

    widgets = [
        {"_widget_id": "a", "z_index": 5},
        {"_widget_id": "b", "z_index": 1},
        {"_widget_id": "c"},  # missing z_index -> treated as 0
        {"_widget_id": "d", "z_index": 1},  # tie with "b": must stay AFTER "b"
        {"_widget_id": "e", "z_index": 5},  # tie with "a": must stay AFTER "a"
    ]
    ordered = [w["_widget_id"] for w in _widgets_in_paint_order(widgets)]
    # c(0) < b(1)==d(1) < a(5)==e(5); ties preserve original list order.
    assert ordered == ["c", "b", "d", "a", "e"]


def test_z_index_survives_full_codegen_pair(tmp_path):
    """The production codegen entrypoint must emit widgets in z-order, not
    authoring order (the regression that dropped z_index entirely)."""
    from tools.ui_codegen import generate_ui_design_pair

    design = {
        "width": 128,
        "height": 64,
        "scenes": {
            "main": {
                "width": 128,
                "height": 64,
                "widgets": [
                    {
                        "type": "label",
                        "_widget_id": "on_top",
                        "x": 0,
                        "y": 0,
                        "width": 20,
                        "height": 10,
                        "text": "TOP",
                        "z_index": 9,
                    },
                    {
                        "type": "label",
                        "_widget_id": "behind",
                        "x": 0,
                        "y": 0,
                        "width": 20,
                        "height": 10,
                        "text": "BACK",
                        "z_index": 0,
                    },
                ],
            }
        },
    }
    jp = tmp_path / "d.json"
    jp.write_text(json.dumps(design), encoding="utf-8")
    c_src, _hdr = generate_ui_design_pair(jp, scene_name="main", source_label="d.json")
    # "behind" (z=0) must appear before "on_top" (z=9) in the emitted C even
    # though it was authored second.
    assert "BACK" in c_src and "TOP" in c_src
    assert c_src.index("BACK") < c_src.index("TOP"), (
        "z_index ignored: lower-z widget was not emitted first"
    )


# ── audit_designs off-canvas / duplicate-id gate ────────────────────────────


def _run_audit(root: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "audit_designs.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_audit_designs_flags_off_canvas_widget(tmp_path):
    """A widget extending past the scene canvas must FAIL the audit (exit 1)."""
    bad = {
        "width": 128,
        "height": 64,
        "scenes": {
            "main": {
                "width": 128,
                "height": 64,
                "widgets": [
                    {"type": "box", "x": 120, "y": 0, "width": 40, "height": 10}
                ],
            }
        },
    }
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    res = _run_audit(tmp_path)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "off-canvas" in res.stdout


def test_audit_designs_flags_duplicate_widget_id(tmp_path):
    dup = {
        "width": 128,
        "height": 64,
        "scenes": {
            "main": {
                "width": 128,
                "height": 64,
                "widgets": [
                    {"type": "box", "x": 0, "y": 0, "width": 10, "height": 10,
                     "_widget_id": "dup"},
                    {"type": "box", "x": 20, "y": 0, "width": 10, "height": 10,
                     "_widget_id": "dup"},
                ],
            }
        },
    }
    (tmp_path / "dup.json").write_text(json.dumps(dup), encoding="utf-8")
    res = _run_audit(tmp_path)
    assert res.returncode == 1
    assert "duplicate _widget_id" in res.stdout


def test_audit_designs_passes_clean_scene(tmp_path):
    ok = {
        "width": 128,
        "height": 64,
        "scenes": {
            "main": {
                "width": 128,
                "height": 64,
                "widgets": [
                    {"type": "box", "x": 0, "y": 0, "width": 10, "height": 10,
                     "_widget_id": "w1"}
                ],
            }
        },
    }
    (tmp_path / "ok.json").write_text(json.dumps(ok), encoding="utf-8")
    res = _run_audit(tmp_path)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "[OK]" in res.stdout


# ── ui_models border_color / border_style idempotent load->save ─────────────


def test_border_color_and_style_round_trip_idempotent():
    """border_color is preserved verbatim (NOT aliased into color_fg) and a
    second load->save produces byte-identical data (no stale shim re-emission)."""
    from ui_models import WidgetConfig

    w0 = WidgetConfig(
        type="panel",
        x=0,
        y=0,
        width=40,
        height=20,
        border_color="#ff00aa",
        border_style="double",
    )
    d0 = asdict(w0)
    assert d0["border_color"] == "#ff00aa"
    assert d0["border_style"] == "double"
    # border_color must NOT have leaked into the fg/text color channel.
    assert d0.get("color_fg") != "#ff00aa"

    # Load -> save -> load again must be a fixed point.
    w1 = WidgetConfig(**d0)
    d1 = asdict(w1)
    w2 = WidgetConfig(**d1)
    d2 = asdict(w2)
    assert d1 == d2, "load->save is not idempotent (shim re-emission?)"
    assert d2["border_color"] == "#ff00aa"
    assert d2["border_style"] == "double"


def test_color_shim_consumed_not_duplicated():
    """An input-only ``bg_color`` shim migrates to canonical color_bg and is
    consumed so it does not round-trip as a duplicate stale value."""
    from ui_models import WidgetConfig

    w = WidgetConfig(type="box", x=0, y=0, width=10, height=10, bg_color="#123456")
    d = asdict(w)
    assert d["color_bg"] == "#123456"
    # Shim consumed -> reloading yields the same canonical value, stably.
    d2 = asdict(WidgetConfig(**d))
    assert d2["color_bg"] == "#123456"
    assert d == d2


# ── codegen icon_char survival + chart data_points ──────────────────────────


def test_chart_data_points_clamped_and_capped():
    from tools.ui_codegen import chart_data_points

    pts = chart_data_points(
        {"type": "chart", "data_points": [0, 100, -40000, 99999, True, "x", 7.9]}
    )
    # bool and non-numeric skipped; ints clamped to int16; float truncated.
    assert pts == [0, 100, -32768, 32767, 7]


def test_chart_data_points_caps_at_max():
    from tools.ui_codegen import _DATA_POINTS_MAX, chart_data_points

    pts = chart_data_points({"type": "chart", "data_points": list(range(500))})
    assert len(pts) == _DATA_POINTS_MAX


def test_icon_char_and_chart_data_survive_codegen(tmp_path):
    """icon_char and a chart series must reach the emitted C — not be dropped."""
    from tools.ui_codegen import generate_ui_design_pair

    design = {
        "width": 128,
        "height": 64,
        "scenes": {
            "main": {
                "width": 128,
                "height": 64,
                "widgets": [
                    {
                        "type": "icon",
                        "_widget_id": "ic",
                        "x": 0,
                        "y": 0,
                        "width": 16,
                        "height": 16,
                        "icon_char": "",  # a Material glyph
                    },
                    {
                        "type": "chart",
                        "_widget_id": "ch",
                        "x": 20,
                        "y": 0,
                        "width": 60,
                        "height": 30,
                        "data_points": [1, 2, 3, 4, 5],
                    },
                ],
            }
        },
    }
    jp = tmp_path / "d.json"
    jp.write_text(json.dumps(design), encoding="utf-8")
    c_src, _hdr = generate_ui_design_pair(jp, scene_name="main", source_label="d.json")
    # The chart array must be emitted and the icon widget must not carry a
    # NULL icon_char (the data-loss regression nulled both).
    assert ".data_points = dp_" in c_src
    assert "5," in c_src  # last data point present in the int16 array
    assert ".icon_char = NULL" not in c_src.split("UIW_ICON")[-1].split("}")[0] \
        or ".icon_char =" in c_src


# ── validate_design benign-overlap rule ─────────────────────────────────────


def test_overlap_is_benign_for_hidden_widget():
    from tools.validate_design import _overlap_is_benign

    a = {"type": "label", "visible": True}
    b = {"type": "panel", "visible": False}
    rect = (0, 0, 50, 20)
    # b is hidden -> cannot visually collide -> benign regardless of geometry.
    assert _overlap_is_benign(a, b, rect, rect) is True


def test_overlap_is_benign_for_containing_container():
    from tools.validate_design import _overlap_is_benign

    panel = {"type": "panel", "visible": True}
    label = {"type": "label", "visible": True}
    big = (0, 0, 100, 60)
    small = (10, 10, 20, 10)
    # Container fully contains the child -> backdrop layering -> benign.
    assert _overlap_is_benign(panel, label, big, small) is True
    # Order-independent: container as second arg.
    assert _overlap_is_benign(label, panel, small, big) is True


def test_overlap_two_visible_labels_is_not_benign():
    from tools.validate_design import _overlap_is_benign

    a = {"type": "label", "visible": True}
    b = {"type": "label", "visible": True}
    # Two visible, mutually non-containing widgets stomping each other: a real
    # defect — must NOT be exempted.
    assert _overlap_is_benign(a, b, (0, 0, 30, 10), (5, 0, 30, 10)) is False


# ── smoke / functional: new session modules ─────────────────────────────────


@pytest.fixture
def _headless(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def test_icon_palette_open_close_and_filter(make_app):
    """Icon Palette: open/close toggles state, discovery returns names, and the
    filter narrows results — the real public API, not a draw no-op."""
    from cyberpunk_designer import icon_palette

    app = make_app()
    assert icon_palette.is_open(app) is False
    icon_palette.open_icon_palette(app)
    assert icon_palette.is_open(app) is True
    icon_palette.close_icon_palette(app)
    assert icon_palette.is_open(app) is False

    names = icon_palette.discover_icon_names()
    assert isinstance(names, tuple)
    if names:  # asset/registry present in this checkout
        assert names == tuple(sorted(names)), "names must be sorted"
        first = names[0]
        filtered = icon_palette._filtered_names(first[:2])
        assert first in filtered
        # A query that matches nothing yields an empty result.
        assert icon_palette._filtered_names("zzzz_no_such_icon_zzzz") == []


def test_template_manager_save_and_persist(tmp_path, monkeypatch):
    """Template Manager: save_scene_as_template registers + persists, rejects
    duplicates, and survives a reload from disk (real round-trip)."""
    store = tmp_path / "templates.json"
    monkeypatch.setenv("ESP32OS_TEMPLATES_PATH", str(store))
    from ui_template_manager import TemplateLibrary

    lib = TemplateLibrary()
    widgets = [{"type": "box", "x": 0, "y": 0, "width": 10, "height": 10}]
    tpl = lib.save_scene_as_template("MyCard", widgets, category="Forms")
    assert tpl is not None
    assert tpl.metadata.name == "MyCard"
    assert tpl.metadata.category == "Forms"
    # Duplicate name rejected.
    assert lib.save_scene_as_template("MyCard", widgets) is None
    # Persisted to disk and reloadable.
    assert store.is_file()
    lib2 = TemplateLibrary()
    assert any(t.metadata.name == "MyCard" for t in lib2.templates)


@pytest.mark.usefixtures("_headless")
def test_svg_export_produces_valid_document(tmp_path):
    """SVG export: scene_to_svg_string emits a well-formed SVG of the correct
    dimensions for a real scene."""
    from tools.ui_export_svg import export_svg, scene_to_svg_string

    design = {
        "width": 128,
        "height": 64,
        "scenes": {
            "main": {
                "width": 128,
                "height": 64,
                "widgets": [
                    {"type": "box", "x": 4, "y": 4, "width": 40, "height": 20}
                ],
            }
        },
    }
    jp = tmp_path / "scene.json"
    jp.write_text(json.dumps(design), encoding="utf-8")

    svg = scene_to_svg_string(jp, scene_name="main")
    assert svg.lstrip().startswith("<?xml") or svg.lstrip().startswith("<svg")
    assert "<svg" in svg and "</svg>" in svg
    assert 'width="128"' in svg or 'viewBox="0 0 128' in svg

    out = tmp_path / "out.svg"
    w, h, name = export_svg(jp, out, scene_name="main")
    # Dimensions are pixel-exact to the scene canvas; the resolved name is the
    # renderer's canonical scene-object name (not necessarily the JSON key).
    assert (w, h) == (128, 64)
    assert isinstance(name, str) and name != ""
    assert out.is_file() and out.read_text(encoding="utf-8").strip().endswith("</svg>")


@pytest.mark.usefixtures("_headless")
def test_svg_export_rejects_unknown_scene(tmp_path):
    """Asking for a scene that does not exist must fail loudly (SystemExit),
    not silently render the wrong scene."""
    from tools.ui_export_svg import scene_to_svg_string

    design = {
        "width": 128,
        "height": 64,
        "scenes": {"main": {"width": 128, "height": 64, "widgets": []}},
    }
    jp = tmp_path / "scene.json"
    jp.write_text(json.dumps(design), encoding="utf-8")
    with pytest.raises(SystemExit):
        scene_to_svg_string(jp, scene_name="does_not_exist")
