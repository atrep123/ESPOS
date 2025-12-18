from types import SimpleNamespace

import pytest

from ui_designer import UIDesigner, WidgetConfig
from ui_models import _make_baseline


def test_apply_best_offset_handles_missing_hline_bounds():
    designer = UIDesigner(20, 20)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    base_widget = WidgetConfig(type="box", x=2, y=2, width=4, height=4)
    scene.widgets.append(base_widget)

    x, y = designer._apply_best_offset(
        5,
        5,
        scene,
        best_dx=None,
        best_dy=0,
        best_vline=None,
        best_hline=(0, None, None, "h"),  # type: ignore[arg-type]
    )

    assert (x, y) == (5, 5)
    assert designer.last_guides[-1]["x1"] == 0
    assert designer.last_guides[-1]["x2"] == scene.width - 1 or designer.last_guides[-1]["x2"] == 0


def test_clone_template_missing_raises_keyerror():
    designer = UIDesigner(10, 10)
    designer.create_scene("main")
    with pytest.raises(KeyError):
        designer._clone_template_with_overrides("missing", 0, 0, {})


def test_clone_template_applies_overrides():
    designer = UIDesigner(10, 10)
    designer.create_scene("main")
    tpl_name = next(iter(designer.templates))
    cloned = designer._clone_template_with_overrides(
        tpl_name,
        1,
        2,
        {"width": 99, "height": 77, "text": "X"},
    )

    assert cloned.x == 1 and cloned.y == 2
    assert cloned.width == 99 and cloned.height == 77
    assert cloned.text == "X"


def test_make_baseline_coerces_optional_ints():
    b = _make_baseline(None, "2", 3.7, None, "5", None)  # type: ignore[arg-type]
    assert b["x"] == 0
    assert b["y"] == 2
    assert b["width"] == 3
    assert b["height"] == 0
    assert b["bw"] == 5
    assert b["bh"] == 0


def test_draw_border_clamps_optional_dimensions():
    designer = UIDesigner(8, 8)
    canvas = [[" " for _ in range(8)] for _ in range(8)]
    widget = SimpleNamespace(x=-2, y=-2, width=None, height=None, border=True, border_style="single")
    border_chars = designer._get_border_chars(widget.border_style)

    designer._draw_border(canvas, widget, border_chars, 8, 8)

    assert canvas[0][0] == border_chars["tl"]


def test_layout_clamps_when_widget_larger_than_scene():
    designer = UIDesigner(4, 4)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    scene.widgets.append(WidgetConfig(type="box", x=0, y=0, width=10, height=10))

    designer.auto_layout(layout_type="vertical", spacing=0, scene_name=scene.name)

    w = scene.widgets[0]
    assert w.x == 0 and w.y == 0
