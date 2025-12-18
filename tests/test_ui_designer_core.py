import pytest

from ui_designer import UIDesigner, WidgetConfig


def test_set_hardware_profile_invalid_keeps_dimensions():
    d = UIDesigner(100, 50)
    before = (d.width, d.height)
    result = d.set_hardware_profile("unknown-profile")
    assert result is None
    assert (d.width, d.height) == before


def test_snap_position_respects_grid():
    d = UIDesigner(100, 100)
    d.grid_enabled = True
    d.grid_size = 8
    x, y = d.snap_position(13, 17)
    assert (x, y) == (8, 16)


def test_add_widget_requires_dimensions_when_type_given():
    d = UIDesigner(100, 100)
    d.create_scene("main")
    d.current_scene = "main"
    with pytest.raises(TypeError):
        d.add_widget("label", scene_name="main")  # missing x/y/width/height


def test_apply_responsive_without_base_no_change():
    d = UIDesigner(100, 100)
    sc = d.create_scene("main")
    d.current_scene = sc.name
    w = WidgetConfig(type="box", x=10, y=10, width=20, height=20)
    sc.widgets.append(w)

    sc.width, sc.height = 200, 200
    d.apply_responsive("main")  # no base set

    assert (w.x, w.y, w.width, w.height) == (10, 10, 20, 20)


def test_apply_responsive_with_base_and_left_anchor():
    d = UIDesigner(100, 100)
    sc = d.create_scene("main")
    d.current_scene = sc.name
    w = WidgetConfig(type="box", x=10, y=10, width=20, height=20)
    w.constraints = {"ax": "left", "ay": "top", "sx": True, "sy": True}
    sc.widgets.append(w)

    d.set_responsive_base("main")
    sc.width, sc.height = 200, 100
    d.apply_responsive("main")

    # Left/top anchor scales size but keeps origin on edge
    assert (w.x, w.y, w.width, w.height) == (10, 10, 40, 20)
