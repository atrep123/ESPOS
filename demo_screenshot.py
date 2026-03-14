#!/usr/bin/env python3
"""Headless render of demo_scene.json -> demo_screenshot.png"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from cyberpunk_designer import drawing  # noqa: E402
from cyberpunk_designer.app import CyberpunkEditorApp  # noqa: E402
from cyberpunk_designer.constants import GRID  # noqa: E402

PROFILE = "esp32os_256x128_gray4"
JSON = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_scene.json")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("demo_screenshot.png")
UPSCALE = 4

app = CyberpunkEditorApp(JSON, profile=PROFILE)
app.show_grid = False
app.show_overflow_warnings = False

sc = app.state.current_scene()
W, H = int(sc.width), int(sc.height)

surf = pygame.Surface((W, H))
surf.fill((0, 0, 0))

padding = 1

items = list(enumerate(sc.widgets))
items.sort(key=lambda t: int(getattr(t[1], "z_index", 0) or 0))

for _idx, w in items:
    if not getattr(w, "visible", True):
        continue
    ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
    wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
    wx, wy = int(w.x), int(w.y)
    rect = pygame.Rect(wx, wy, ww, wh)
    drawing.draw_widget_preview(app, surf, w, rect, (0, 0, 0), padding, False)

# 4bpp grayscale quantization
gray = pygame.Surface((W, H))
for y in range(H):
    for x in range(W):
        r, g, b, *_ = surf.get_at((x, y))
        lum = int(0.299 * r + 0.587 * g + 0.114 * b)
        lum = (lum >> 4) << 4
        gray.set_at((x, y), (lum, lum, lum))

big = pygame.transform.scale(gray, (W * UPSCALE, H * UPSCALE))
pygame.image.save(big, str(OUT))
print(f"Saved {OUT} ({big.get_width()}x{big.get_height()})")
