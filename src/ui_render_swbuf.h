#pragma once

#include <stdint.h>
#include <stddef.h>
#include "display_config.h"
#include "ui_render.h"

/*
 * Simple software framebuffer and UiDrawOps adapter.
 *
 * Memory layout depends on DISPLAY_COLOR_BITS:
 *   - 1bpp: rows packed MSB-first, stride = (width + 7) / 8 bytes.
 *   - 4bpp: 2 pixels per byte (hi nibble = even x, lo nibble = odd x),
 *           stride = (width + 1) / 2 bytes.
 */
typedef struct UiSwBuf {
    int width;
    int height;
    int stride_bytes; /* bytes per row */
    uint8_t *data;    /* caller-provided memory, size >= stride * height */
    /* Dirty region tracking */
    int dirty;        /* 0 = clean, 1 = has dirty region */
    int d_x0, d_y0, d_x1, d_y1; /* inclusive/exclusive bounds */
} UiSwBuf;

/* Compile-time helpers for buffer sizing. */
#if DISPLAY_COLOR_BITS == 4
#define UI_SWBUF_STRIDE_BYTES(width_px) (((width_px) + 1) / 2)
#else
#define UI_SWBUF_STRIDE_BYTES(width_px) (((width_px) + 7) / 8)
#endif
#define UI_SWBUF_BYTES(width_px, height_px) (UI_SWBUF_STRIDE_BYTES(width_px) * (height_px))

/* Initialize buffer on caller-provided memory */
void ui_swbuf_init(UiSwBuf *b, void *mem, int width, int height);
void ui_swbuf_clear(UiSwBuf *b, uint8_t color);

/* Drawing primitives operating on the buffer (color: 0/1 for 1bpp, 0..15 for 4bpp). */
void ui_swbuf_fill_rect(void *ctx, int x, int y, int w, int h, uint8_t color);
void ui_swbuf_hline(void *ctx, int x, int y, int w, uint8_t color);
void ui_swbuf_vline(void *ctx, int x, int y, int h, uint8_t color);
void ui_swbuf_rect(void *ctx, int x, int y, int w, int h, uint8_t color);
void ui_swbuf_text(void *ctx, int x, int y, const char *text, uint8_t color);

/* Blit a monochrome (1bpp) mask bitmap into the buffer (MSB-first). */
void ui_swbuf_blit_mono(
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

/* Populate UiDrawOps with software buffer implementations */
void ui_swbuf_make_ops(UiSwBuf *b, UiDrawOps *ops);

/* Flush buffer to SSD1363 (full-frame). Selects 1bpp vs 4bpp by DISPLAY_COLOR_BITS. */
void ui_swbuf_flush_auto_ssd1363(const UiSwBuf *b);
void ui_swbuf_flush_ssd1363(const UiSwBuf *b);       /* 1bpp packed */
void ui_swbuf_flush_gray4_ssd1363(const UiSwBuf *b); /* 4bpp grayscale (two pixels/byte) */

/* Dirty region helpers and partial flush */
void ui_swbuf_mark_dirty(UiSwBuf *b, int x, int y, int w, int h);
int  ui_swbuf_get_dirty(const UiSwBuf *b, int *x, int *y, int *w, int *h);
void ui_swbuf_clear_dirty(UiSwBuf *b);
/* Dirty partial flush (auto-select by DISPLAY_COLOR_BITS). */
void ui_swbuf_flush_dirty_auto_ssd1363(const UiSwBuf *b);
void ui_swbuf_flush_dirty_ssd1363(const UiSwBuf *b);       /* 1bpp */
void ui_swbuf_flush_dirty_gray4_ssd1363(const UiSwBuf *b); /* 4bpp */
