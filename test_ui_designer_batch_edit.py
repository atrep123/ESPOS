#!/usr/bin/env python3
"""Headless test for batch edit (multi-select position/size deltas)."""

import os

import pytest

from ui_designer import UIDesigner, WidgetConfig
from ui_designer_preview import VisualPreviewWindow


def _make_widget(x: int, y: int, w: int, h: int, type_: str = "box") -> WidgetConfig:
    return WidgetConfig(type=type_, x=x, y=y, width=w, height=h)


def test_batch_apply_deltas():
    os.environ["ESP32OS_HEADLESS"] = "1"
    designer = UIDesigner(width=120, height=120)
    designer.create_scene("main")
    designer.current_scene = "main"
    scene = designer.scenes["main"]
    scene.widgets.append(_make_widget(10, 10, 20, 20))
    scene.widgets.append(_make_widget(40, 15, 30, 25))

    vp = VisualPreviewWindow(designer)
    vp.selected_widgets = [0, 1]
    vp.selected_widget_idx = 0

    vp._batch_apply_deltas(dx=5, dy=-3, dw=2, dh=-1)

    w0 = scene.widgets[0]
    w1 = scene.widgets[1]
    assert (w0.x, w0.y, w0.width, w0.height) == (15, 7, 22, 19)
    assert (w1.x, w1.y, w1.width, w1.height) == (45, 12, 32, 24)


if __name__ == "__main__":
    pytest.main([__file__])
