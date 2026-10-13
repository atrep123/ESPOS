"""Common backend geometry, not renderer/panel proof."""

import pytest

from ui_models import WidgetConfig, widget_fits_in_bounds


@pytest.mark.parametrize(
    ("x", "y", "w", "h", "expected"),
    [
        (10, 10, 50, 30, True),
        (80, 70, 20, 30, True),
        (90, 10, 20, 30, False),
        (10, 90, 20, 20, False),
        (-1, 10, 20, 30, False),
        (10, -1, 20, 30, False),
    ],
)
def test_complete_box_bounds(x, y, w, h, expected):
    widget = WidgetConfig(type="label", x=x, y=y, width=w, height=h)
    assert widget_fits_in_bounds(widget, 100, 100) is expected
