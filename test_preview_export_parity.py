#!/usr/bin/env python3
"""Parity test between in-memory render and PNG export."""

import io
import pytest
from PIL import Image

from ui_designer import UIDesigner, WidgetType
from ui_designer_preview import VisualPreviewWindow, HEADLESS, TK_AVAILABLE


@pytest.mark.skipif(not (HEADLESS or TK_AVAILABLE), reason="Preview requires headless or Tk available")
def test_preview_export_center_pixel_parity():
    d = UIDesigner(32, 16)
    d.create_scene("s")
    d.add_widget(WidgetType.BOX, x=4, y=4, width=12, height=6, text="", border=True)
    d.add_widget(WidgetType.LABEL, x=6, y=6, width=8, height=3, text="X", border=False, color_fg="white", color_bg="black")

    vp = VisualPreviewWindow(d)
    scene = d.scenes[d.current_scene]

    img = vp._render_scene_image(
        scene,
        include_grid=False,
        use_overlays=False,
        highlight_selection=False,
    )
    cx, cy = scene.width // 2, scene.height // 2
    center_mem = img.getpixel((cx, cy))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    img_png = Image.open(buf)
    center_png = img_png.getpixel((cx, cy))

    assert center_mem == center_png
