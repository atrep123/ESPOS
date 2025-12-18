#pragma once

#include <stdint.h>

#include "icons.h"
#include "ui_render_swbuf.h"

/* Minimal display wrapper used by the icon demo.
 * Points at a software buffer so the demo can render in firmware builds
 * even without a full display abstraction layer.
 */
typedef struct display {
    UiSwBuf *buf;
} display_t;

enum display_blit_mode {
    BLIT_NORMAL = 0,
    BLIT_INVERT = 1,
    BLIT_XOR    = 2,
};

static inline void display_blit_icon_mode(display_t *d, const icon_t *ic, int16_t x, int16_t y, enum display_blit_mode mode)
{
    if (!d || !d->buf || !ic) {
        return;
    }
    /* Real 1bpp icon mask blit into the software framebuffer. */
    ui_swbuf_blit_mono(
        d->buf,
        x,
        y,
        (int)ic->width,
        (int)ic->height,
        (int)ic->stride_bytes,
        ic->data,
        1,
        (uint8_t)mode
    );
}

void ui_scene_icon_demo(display_t *d);
void ui_icon_set_size(uint8_t px);
void ui_icon_set_mode(enum display_blit_mode mode);
void ui_icon_bench(display_t *d, uint32_t count, uint8_t size_px, enum display_blit_mode mode, char *out_json, size_t out_len);
