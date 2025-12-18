from __future__ import annotations

import pygame


class Layout:
    """Logical layout rectangles for toolbar/panels/canvas/status."""

    def __init__(
        self,
        width: int,
        height: int,
        palette_w: int = 112,
        inspector_w: int = 200,
        toolbar_h: int = 24,
        status_h: int = 18,
    ):
        self.toolbar_h = toolbar_h
        self.status_h = status_h
        self.palette_w = palette_w
        self.inspector_w = inspector_w
        self.width = width
        self.height = height

    @property
    def canvas_rect(self) -> pygame.Rect:
        x = self.palette_w
        y = self.toolbar_h
        w = self.width - self.palette_w - self.inspector_w
        h = self.height - self.toolbar_h - self.status_h
        return pygame.Rect(x, y, w, h)

    @property
    def palette_rect(self) -> pygame.Rect:
        return pygame.Rect(0, self.toolbar_h, self.palette_w, self.height - self.toolbar_h - self.status_h)

    @property
    def inspector_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.width - self.inspector_w,
            self.toolbar_h,
            self.inspector_w,
            self.height - self.toolbar_h - self.status_h,
        )

    @property
    def toolbar_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.width, self.toolbar_h)

    @property
    def status_rect(self) -> pygame.Rect:
        return pygame.Rect(0, self.height - self.status_h, self.width, self.status_h)

