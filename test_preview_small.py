#!/usr/bin/env python3
"""Render widgets with very small heights to ensure no PIL y-order errors.

This is a smoke test: if no exception is raised during drawing, it passes.
"""

import sys
sys.path.insert(0, '.')

from PIL import Image, ImageDraw
from ui_designer import UIDesigner, WidgetType, WidgetConfig
from ui_designer_preview import VisualPreviewWindow, PreviewSettings


def render_scene_with_small_heights():
    d = UIDesigner(128, 64)
    d.create_scene('small')
    # Add widgets with tiny heights 0,1,2 to exercise rectangle ordering
    heights = [0, 1, 2]
    x = 4
    y = 4
    for h in heights:
        d.add_widget(WidgetConfig(type=WidgetType.PROGRESSBAR.value, x=x, y=y, width=24, height=h or 1, value=50))
        y += 6
        d.add_widget(WidgetConfig(type=WidgetType.SLIDER.value, x=x, y=y, width=24, height=h or 1, value=50))
        y += 6
        d.add_widget(WidgetConfig(type=WidgetType.CHECKBOX.value, x=x, y=y, width=24, height=h or 1, text='chk', checked=True))
        y += 8

    img = Image.new('RGB', (d.width, d.height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Use VisualPreviewWindow drawing without initializing Tk
    vp = object.__new__(VisualPreviewWindow)
    vp.settings = PreviewSettings()

    scene = d.scenes.get(d.current_scene)
    for w in scene.widgets:
        vp._draw_widget(draw, w, False)

    # Resize and save to ensure image ops are OK
    img2 = img.resize((d.width * 2, d.height * 2), Image.NEAREST)  # type: ignore
    from pathlib import Path
    Path('examples').mkdir(exist_ok=True)
    img2.save('examples/preview_small_heights.png')  # type: ignore
    return True


if __name__ == '__main__':
    ok = render_scene_with_small_heights()
    print('OK' if ok else 'FAIL')
