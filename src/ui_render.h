#pragma once

#include <stdint.h>
#include "ui_design.h"

/*
 * Minimal UI renderer for exported scenes.
 *
 * This renderer is backend-agnostic: you pass drawing callbacks
 * (fill rect, lines, text) via UiDrawOps and it renders widgets
 * defined in ui_design.h onto your display/framebuffer.
 */

typedef struct UiDrawOps {
    void *ctx; /* user context passed to all callbacks */

    /* Basic drawing primitives (all optional except fill_rect or h/v lines). */
    void (*fill_rect)(void *ctx, int x, int y, int w, int h, uint8_t color);
    void (*draw_hline)(void *ctx, int x, int y, int w, uint8_t color);
    void (*draw_vline)(void *ctx, int x, int y, int h, uint8_t color);
    void (*draw_rect)(void *ctx, int x, int y, int w, int h, uint8_t color);
    void (*draw_text)(void *ctx, int x, int y, const char *text, uint8_t color);
} UiDrawOps;

/* Render entire scene using provided draw ops (monochrome color: 0/1). */
void ui_render_scene(const UiScene *scene, const UiDrawOps *ops);

/* Render a single widget (exposed for custom pipelines). */
void ui_render_widget(const UiWidget *w, const UiDrawOps *ops);
