import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetConfig


def test_distribute_axis_handles_negative_width():
    designer = UIDesigner(20, 20)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    w1 = WidgetConfig(type="box", x=-5, y=0, width=None, height=4)
    w2 = WidgetConfig(type="box", x=10, y=0, width=5, height=4)
    scene.widgets.extend([w1, w2])
    designer.distribute_widgets("horizontal", [0, 1], scene_name=scene.name)
    assert scene.widgets[0].x <= scene.widgets[1].x


@pytest.mark.parametrize("width", [None, 0, -1, 5])
def test_negative_width_clamped_in_distribution(width):
    designer = UIDesigner(10, 10)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    w = WidgetConfig(type="box", x=-2, y=0, width=width, height=2)
    scene.widgets.append(w)
    designer.distribute_widgets("horizontal", [0], scene_name=scene.name)
    assert isinstance(scene.widgets[0].x, int)

