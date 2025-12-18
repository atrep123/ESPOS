#pragma once

#include <stdint.h>
#include "ui_scene.h"

/* Text rendering assumptions for fit/ellipsis helpers.
 *
 * Override in your build if your renderer uses a different fixed-width font.
 */
#ifndef UI_FONT_CHAR_W
#define UI_FONT_CHAR_W 6
#endif
#ifndef UI_FONT_CHAR_H
#define UI_FONT_CHAR_H 8
#endif

/*
 * Minimal UI renderer for exported scenes.
 *
 * This renderer is backend-agnostic: you pass drawing callbacks
 * (fill rect, lines, text) via UiDrawOps and it renders widgets
 * defined in ui_scene.h (and referenced by generated designs) onto your display/framebuffer.
 */

typedef struct UiDrawOps {
    void *ctx; /* user context passed to all callbacks */

    /* Basic drawing primitives (all optional except fill_rect or h/v lines). */
    void (*fill_rect)(void *ctx, int x, int y, int w, int h, uint8_t color);
    void (*draw_hline)(void *ctx, int x, int y, int w, uint8_t color);
    void (*draw_vline)(void *ctx, int x, int y, int h, uint8_t color);
    void (*draw_rect)(void *ctx, int x, int y, int w, int h, uint8_t color);

    /* Text is positioned by its top-left corner (x,y). */
    void (*draw_text)(void *ctx, int x, int y, const char *text, uint8_t color);

    /*
     * Optional monochrome (1bpp) mask blit, MSB-first in each byte.
     *
     * This is used by UIW_ICON (and icon demos) to draw icons efficiently
     * without requiring the backend to implement text-based fallbacks.
     *
     * mode:
     *   0 = normal  (dst = color where mask=1)
     *   1 = invert  (dst = ~dst where mask=1)
     *   2 = xor     (dst = dst ^ color where mask=1)
     */
    void (*blit_mono)(
        void *ctx,
        int x,
        int y,
        int w,
        int h,
        int stride_bytes,
        const uint8_t *data,
        uint8_t color,
        uint8_t mode
    );
} UiDrawOps;

/* Render entire scene using provided draw ops
 * (color: 0/1 for 1bpp, 0..15 for 4bpp gray). */
void ui_render_scene(const UiScene *scene, const UiDrawOps *ops);

/* Render a single widget (exposed for custom pipelines). */
void ui_render_widget(const UiWidget *w, const UiDrawOps *ops);
