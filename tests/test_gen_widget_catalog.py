"""Tests for gen_widget_catalog.py — helper functions and scene generators."""

import gen_widget_catalog as gwc

# ── text_w ─────────────────────────────────────────────────────────────


def test_text_w_one_char():
    assert gwc.text_w(1) == 1 * gwc.CHAR_W + gwc.PAD * 2


def test_text_w_zero():
    assert gwc.text_w(0) == gwc.PAD * 2


def test_text_w_ten():
    assert gwc.text_w(10) == 10 * gwc.CHAR_W + gwc.PAD * 2


# ── _wid ───────────────────────────────────────────────────────────────


def test_wid_returns_prefixed_string():
    wid = gwc._wid("test")
    assert wid.startswith("test.")
    # numeric suffix
    suffix = wid.split(".")[-1]
    assert suffix.isdigit()


def test_wid_increments():
    a = gwc._wid("x")
    b = gwc._wid("x")
    na = int(a.split(".")[-1])
    nb = int(b.split(".")[-1])
    assert nb == na + 1


# ── widget ─────────────────────────────────────────────────────────────


def test_widget_returns_dict():
    w = gwc.widget("label", 0, 0, 60, 12, "HI", wid="w.1")
    assert isinstance(w, dict)
    assert w["type"] == "label"
    assert w["text"] == "HI"
    assert w["_widget_id"] == "w.1"


def test_widget_default_values():
    w = gwc.widget("box", 0, 0, 20, 20, wid="w.2")
    assert w["style"] == "default"
    assert w["color_fg"] == "#f0f0f0"
    assert w["color_bg"] == "black"
    assert w["border"] is False
    assert w["enabled"] is True
    assert w["visible"] is True
    assert w["data_points"] == []


def test_widget_custom_text_overflow():
    w = gwc.widget("label", 0, 0, 60, 12, wid="w.3", text_overflow="wrap")
    assert w["text_overflow"] == "wrap"


def test_widget_checked_kwarg():
    w = gwc.widget("checkbox", 0, 0, 14, 14, wid="w.4", checked=True)
    assert w["checked"] is True


# ── scene generators ───────────────────────────────────────────────────


def _check_scene(scene):
    """Basic structural checks for a generated scene."""
    assert "width" in scene
    assert "height" in scene
    assert scene["width"] == gwc.W
    assert scene["height"] == gwc.H
    assert "widgets" in scene
    assert len(scene["widgets"]) > 0
    for w in scene["widgets"]:
        assert "type" in w
        assert "x" in w
        assert "y" in w
        assert "width" in w
        assert "height" in w
        assert w["_widget_id"] is not None


def test_scene_catalog_text():
    _check_scene(gwc.scene_catalog_text())


def test_scene_catalog_controls():
    _check_scene(gwc.scene_catalog_controls())


def test_scene_catalog_data():
    _check_scene(gwc.scene_catalog_data())


def test_scene_catalog_dashboard():
    _check_scene(gwc.scene_catalog_dashboard())


def test_all_scenes_unique_ids():
    """All widget IDs across all scenes must be unique."""
    all_ids = []
    for gen in [
        gwc.scene_catalog_text,
        gwc.scene_catalog_controls,
        gwc.scene_catalog_data,
        gwc.scene_catalog_dashboard,
    ]:
        scene = gen()
        for w in scene["widgets"]:
            all_ids.append(w["_widget_id"])
    assert len(all_ids) == len(set(all_ids)), "duplicate _widget_id across scenes"


def test_all_scenes_widgets_inside_bounds():
    """All widgets should fit within scene dimensions."""
    for gen in [
        gwc.scene_catalog_text,
        gwc.scene_catalog_controls,
        gwc.scene_catalog_data,
        gwc.scene_catalog_dashboard,
    ]:
        scene = gen()
        for w in scene["widgets"]:
            assert w["x"] >= 0, f"{w['_widget_id']} x={w['x']}"
            assert w["y"] >= 0, f"{w['_widget_id']} y={w['y']}"
            assert w["x"] + w["width"] <= scene["width"], (
                f"{w['_widget_id']} right edge {w['x'] + w['width']} > {scene['width']}"
            )
            assert w["y"] + w["height"] <= scene["height"], (
                f"{w['_widget_id']} bottom edge {w['y'] + w['height']} > {scene['height']}"
            )
