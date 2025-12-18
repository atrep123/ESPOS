from constants import DEFAULT_WIDGET_SIZE
from ui_designer import UIDesigner
from ui_models import WidgetConfig


def test_widget_defaults_to_minimum_dimensions_on_none():
    w = WidgetConfig(type="box", x=0, y=0, width=None, height=None)
    assert w.width == DEFAULT_WIDGET_SIZE
    assert w.height == DEFAULT_WIDGET_SIZE


def test_widget_dimensions_coerce_non_positive_to_minimum():
    w = WidgetConfig(type="box", x=0, y=0, width=0, height=-5)
    assert w.width == 1
    assert w.height == 1
    w.width = -1
    w.height = 0
    assert w.width == 1
    assert w.height == 1


def test_snap_to_grid_type_guard_handles_edge_values():
    d = UIDesigner()
    d.snap_to_grid = None
    assert d.snap_to_grid is False
    d.snap_to_grid = 0
    assert d.snap_to_grid is False
    d.snap_to_grid = -1
    assert d.snap_to_grid is True
    d.snap_to_grid = "yes"
    assert d.snap_to_grid is True
