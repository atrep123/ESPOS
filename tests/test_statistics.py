import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetConfig


def _widgets():
    return [
        WidgetConfig(type="box", x=0, y=0, width=10, height=10),
        WidgetConfig(type="box", x=10, y=10, width=10, height=10),
    ]


def test_calculate_center_x():
    designer = UIDesigner()
    widgets = _widgets()
    avg = designer._calculate_center(widgets, axis="x")
    assert avg == (5 + 15) // 2


def test_calculate_center_y():
    designer = UIDesigner()
    widgets = _widgets()
    avg = designer._calculate_center(widgets, axis="y")
    assert avg == (5 + 15) // 2


def test_calculate_center_empty_returns_zero():
    designer = UIDesigner()
    assert designer._calculate_center([], axis="x") == 0


def test_align_center_no_crash_single():
    designer = UIDesigner()
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    scene.widgets.append(WidgetConfig(type="box", x=2, y=3, width=4, height=6))
    designer.align_widgets("center_h", [0])
    w = scene.widgets[0]
    assert isinstance(w.x, int) and isinstance(w.y, int)
