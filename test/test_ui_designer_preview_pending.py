import os

from ui_designer import UIDesigner
from ui_designer_preview import VisualPreviewWindow


def test_pending_preview_cancel(monkeypatch):
    monkeypatch.setenv("ESP32OS_HEADLESS", "1")
    designer = UIDesigner(width=120, height=80)
    vp = VisualPreviewWindow(designer)
    # Simulate quick insert: set pending component
    vp.quick_insert_components = [{"type": "label", "name": "Label", "defaults": {"width": 20, "height": 10}}]
    vp._pending_component = vp.quick_insert_components[0]
    assert vp._pending_component
    vp._cancel_pending_overlay()
    assert vp._pending_component is None
