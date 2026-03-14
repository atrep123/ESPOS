#pragma once

#include <stdint.h>
#include "ui_render.h"  /* UiDrawOps, UI_FONT_CHAR_W/H */

/*
 * Ordered-dithering primitives and gradient fills.
 * Pure functions: no hardware, no scene state.
 */

/* 4×4 Bayer ordered-dithering threshold matrix (values 0..15). */
extern const uint8_t ui_bayer4[4][4];

/* Draw a single pixel at (x,y) via ops->draw_hline with width=1. */
static inline void ui_draw_pixel(const UiDrawOps *ops, int x, int y, uint8_t c)
{
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, x, y, 1, c);
    }
}

/* Dithered pixel: select hi or lo based on Bayer threshold.
 * ratio is 0..16 (0 = all lo, 16 = all hi). */
void ui_dither_pixel(const UiDrawOps *ops, int x, int y,
                     uint8_t hi, uint8_t lo, int ratio);

/* Horizontal gradient dithered fill: brightness increases left→right.
 * Fills rectangle (x, y, w, h) with gradient from lo (left) to hi (right). */
void ui_dither_fill_h(const UiDrawOps *ops, int x, int y, int w, int h,
                      uint8_t hi, uint8_t lo);

/* Vertical gradient dithered fill: brightness decreases top→bottom.
 * Fills rectangle (x, y, w, h) from hi (top) to lo (bottom). */
void ui_dither_fill_v(const UiDrawOps *ops, int x, int y, int w, int h,
                      uint8_t hi, uint8_t lo);
