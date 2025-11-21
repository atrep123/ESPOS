#!/usr/bin/env python3
"""Headless test for nudge distances respecting snap/grid."""

import os

import pytest

from ui_designer import UIDesigner, WidgetConfig
from ui_designer_preview import PreviewSettings, VisualPreviewWindow


class DummyRoot:
    """Minimal dummy to satisfy VisualPreviewWindow without Tk mainloop."""

    def __init__(self):
        self._bindings = {}

    def bind(self, *args, **kwargs):
        self._bindings[args[0]] = kwargs

    def after(self, *args, **kwargs):
        return None

    def title(self, *_):
        return None

    def withdraw(self):
        return None


class DummyEvent:
    def __init__(self, state: int = 0):
        self.state = state


def _make_widget() -> WidgetConfig:
    return WidgetConfig(
        type="box",
        x=10,
        y=10,
        width=10,
        height=10,
    )


def test_nudge_respects_snap_grid():
    os.environ["ESP32OS_HEADLESS"] = "1"
    designer = UIDesigner(width=100, height=100)
    designer.create_scene("main")
    designer.current_scene = "main"
    scene = designer.scenes["main"]
    scene.widgets.append(_make_widget())

    vp = VisualPreviewWindow(designer)
    vp.root = DummyRoot()  # bypass tk root usage
    vp.settings = PreviewSettings()
    vp.settings.snap_enabled = True
    vp.settings.snap_size = 5
    vp.settings.nudge_distance = 1
    vp.settings.nudge_shift_distance = 4
    vp.selected_widget_idx = 0
    vp.selected_widgets = [0]

    # Arrow without Shift snaps to grid (5px) even with step=1
    vp._on_nudge(DummyEvent(), dx=1, dy=0)
    w = scene.widgets[0]
    assert (w.x, w.y) == (15, 10)

    # Shift arrow uses larger step, still snaps
    vp._on_nudge(DummyEvent(state=0x0001), dx=1, dy=0)
    assert (w.x, w.y) == (20, 10)

    # Up with shift snaps to y multiple
    vp._on_nudge(DummyEvent(state=0x0001), dx=0, dy=-1)
    assert (w.x, w.y) == (20, 5)


if __name__ == "__main__":
    pytest.main([__file__])
