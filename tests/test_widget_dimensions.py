import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetConfig


@pytest.mark.parametrize("width,height", [(None, None), (0, 0), (-1, -2), (5, 7)])
def test_widget_bounds_handles_optional(width, height):
    d = UIDesigner(20, 20)
    sc = d.create_scene("main")
    widget = WidgetConfig(type="box", x=1, y=2, width=width, height=height)
    sc.widgets.append(widget)
    bounds = d._widget_bounds(widget, widget.x, widget.y)
    assert bounds["right"] > bounds["left"]
    assert bounds["bottom"] > bounds["top"]


def test_clamp_to_scene_with_none_dimensions():
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    w = WidgetConfig(type="box", x=15, y=15, width=None, height=None)
    clamped = d._clamp_to_scene(15, 15, w, sc)
    assert clamped[0] <= sc.width
    assert clamped[1] <= sc.height


def test_count_overlaps_with_missing_sizes():
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=None, height=None))
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=None, height=None))
    assert d._count_overlaps(sc) >= 1
