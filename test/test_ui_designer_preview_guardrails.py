import importlib
import re
from pathlib import Path

import pytest


def test_all_color_roles_are_defined():
    """Every color_hex(...) role used in ui_designer_preview must exist in design_tokens."""
    text = Path("ui_designer_preview.py").read_text(encoding="utf-8")
    roles = set(re.findall(r'color_hex\(["\']([^"\']+)["\']\)', text))
    from design_tokens import COLOR_HEX

    missing = sorted(r for r in roles if r not in COLOR_HEX)
    assert not missing, f"Missing color roles in design_tokens: {missing}"


def test_selection_handles_render_headless(monkeypatch):
    """Headless smoke: selection handles drawing should not crash."""
    monkeypatch.setenv("ESP32OS_HEADLESS", "1")
    # Reload module so HEADLESS is recomputed with the env var set.
    import ui_designer_preview as udp

    udp = importlib.reload(udp)
    from ui_designer import UIDesigner, WidgetType

    designer = UIDesigner(width=120, height=80)
    designer.create_scene("demo")
    designer.add_widget(WidgetType.LABEL, x=10, y=10, width=40, height=12, text="Label")

    class DummyCanvas:
        def __init__(self):
            self.rects = []

        def winfo_width(self):
            return 200

        def winfo_height(self):
            return 160

        def create_rectangle(self, *args, **kwargs):
            self.rects.append((args, kwargs))
            return len(self.rects)

    vp = udp.VisualPreviewWindow(designer)
    vp.canvas = DummyCanvas()
    vp.selected_widget_idx = 0
    vp.selected_widgets = [0]
    vp.dragging = False
    vp.resize_handle = None
    vp.hovered_handle = None

    vp._draw_selection_handles()
    assert vp.canvas.rects, "Selection handles were not drawn"
