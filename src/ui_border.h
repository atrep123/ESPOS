#pragma once

#include <stdint.h>
#include "ui_render.h"  /* UiDrawOps, UiBorderStyle */

/*
 * Pure border-style drawing — no scene state, no hardware.
 * Uses UiDrawOps callbacks for all output.
 */

/* Draw an outlined rectangle via UiDrawOps (rect or h/vline fallback). */
static inline void ui_draw_rect_outline(
    const UiDrawOps *ops, int x, int y, int w, int h, uint8_t c)
{
    if (w <= 0 || h <= 0) return;
    if (ops->draw_rect) {
        ops->draw_rect(ops->ctx, x, y, w, h, c);
        return;
    }
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, x, y, w, c);
        ops->draw_hline(ops->ctx, x, y + h - 1, w, c);
    }
    if (ops->draw_vline) {
        ops->draw_vline(ops->ctx, x, y, h, c);
        ops->draw_vline(ops->ctx, x + w - 1, y, h, c);
    }
}

/* Fill a rectangle via UiDrawOps (fill_rect or hline fallback). */
static inline void ui_fill_rect(
    const UiDrawOps *ops, int x, int y, int w, int h, uint8_t c)
{
    if (w <= 0 || h <= 0) return;
    if (ops->fill_rect) {
        ops->fill_rect(ops->ctx, x, y, w, h, c);
        return;
    }
    if (ops->draw_hline) {
        for (int yy = 0; yy < h; ++yy) {
            ops->draw_hline(ops->ctx, x, y + yy, w, c);
        }
    }
}

/* Draw a styled border around (x, y, w, h).
 * style: UI_BORDER_NONE/SINGLE/DOUBLE/BOLD/ROUNDED/DASHED.
 * c: grayscale color (0..15 for 4bpp, 0/1 for 1bpp). */
void ui_draw_border_style(
    const UiDrawOps *ops, int x, int y, int w, int h,
    uint8_t style, uint8_t c);
