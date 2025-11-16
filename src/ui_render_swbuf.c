#include "ui_render_swbuf.h"

#include <string.h>
#include "display/ssd1363.h"
#include "display_config.h"

static inline void set_px(UiSwBuf *b, int x, int y, uint8_t c)
{
    if ((unsigned)x >= (unsigned)b->width || (unsigned)y >= (unsigned)b->height) return;
    int byte_index = y * b->stride_bytes + (x >> 3);
    uint8_t mask = (uint8_t)(0x80u >> (x & 7));
    if (c) b->data[byte_index] |= mask; else b->data[byte_index] &= (uint8_t)~mask;
}

void ui_swbuf_init(UiSwBuf *b, void *mem, int width, int height)
{
    b->width = width;
    b->height = height;
    b->stride_bytes = (width + 7) >> 3;
    b->data = (uint8_t *)mem;
    b->dirty = 0;
    b->d_x0 = b->d_y0 = 0;
    b->d_x1 = b->d_y1 = 0;
}

void ui_swbuf_clear(UiSwBuf *b, uint8_t color)
{
    memset(b->data, color ? 0xFF : 0x00, (size_t)b->stride_bytes * (size_t)b->height);
    /* After a full clear, the whole frame needs sending once. */
    ui_swbuf_mark_dirty(b, 0, 0, b->width, b->height);
}

void ui_swbuf_fill_rect(void *ctx, int x, int y, int w, int h, uint8_t color)
{
    UiSwBuf *b = (UiSwBuf *)ctx;
    if (w <= 0 || h <= 0) return;
    int x0 = (x < 0) ? 0 : x;
    int y0 = (y < 0) ? 0 : y;
    int x1 = x + w; if (x1 > b->width)  x1 = b->width;
    int y1 = y + h; if (y1 > b->height) y1 = b->height;
    if (x0 >= x1 || y0 >= y1) return;

    for (int yy = y0; yy < y1; ++yy) {
        for (int xx = x0; xx < x1; ++xx) {
            set_px(b, xx, yy, color);
        }
    }
    ui_swbuf_mark_dirty(b, x0, y0, x1 - x0, y1 - y0);
}

void ui_swbuf_hline(void *ctx, int x, int y, int w, uint8_t color)
{
    UiSwBuf *b = (UiSwBuf *)ctx;
    if ((unsigned)y >= (unsigned)b->height || w <= 0) return;
    int x0 = x; if (x0 < 0) x0 = 0;
    int x1 = x + w; if (x1 > b->width) x1 = b->width;
    for (int xx = x0; xx < x1; ++xx) set_px(b, xx, y, color);
    ui_swbuf_mark_dirty(b, x0, y, x1 - x0, 1);
}

void ui_swbuf_vline(void *ctx, int x, int y, int h, uint8_t color)
{
    UiSwBuf *b = (UiSwBuf *)ctx;
    if ((unsigned)x >= (unsigned)b->width || h <= 0) return;
    int y0 = y; if (y0 < 0) y0 = 0;
    int y1 = y + h; if (y1 > b->height) y1 = b->height;
    for (int yy = y0; yy < y1; ++yy) set_px(b, x, yy, color);
    ui_swbuf_mark_dirty(b, x, y0, 1, y1 - y0);
}

void ui_swbuf_rect(void *ctx, int x, int y, int w, int h, uint8_t color)
{
    ui_swbuf_hline(ctx, x, y, w, color);
    ui_swbuf_hline(ctx, x, y + h - 1, w, color);
    ui_swbuf_vline(ctx, x, y, h, color);
    ui_swbuf_vline(ctx, x + w - 1, y, h, color);
}

void ui_swbuf_text(void *ctx, int x, int y, const char *text, uint8_t color)
{
    /* Placeholder: draw a short horizontal line approximating text length */
    if (!text) return;
    int len = (int)strlen(text);
    if (len <= 0) return;
    ui_swbuf_hline(ctx, x, y, len, color);
}

void ui_swbuf_make_ops(UiSwBuf *b, UiDrawOps *ops)
{
    memset(ops, 0, sizeof(*ops));
    ops->ctx = b;
    ops->fill_rect = ui_swbuf_fill_rect;
    ops->draw_hline = ui_swbuf_hline;
    ops->draw_vline = ui_swbuf_vline;
    ops->draw_rect  = ui_swbuf_rect;
    ops->draw_text  = ui_swbuf_text; /* optional */
}

void ui_swbuf_flush_ssd1363(const UiSwBuf *b)
{
    /*
     * Placeholder full-frame flush assuming RAM write mode is set.
     * Many SSD13xx controllers use:
     *   0x15: Set Column Address (start, end)
     *   0x75: Set Row Address (start, end)
     *   0x5C: Write RAM
     * Adjust for SSD1363 specifics as needed.
     */
    (void)ssd1363_begin_frame(0, 0, (uint16_t)(b->width - 1), (uint16_t)(b->height - 1));

    /* Send packed framebuffer as-is (1bpp). If your panel expects different
     * pixel format (e.g., 4-bit grayscale), convert here before sending.
     */
    size_t total = (size_t)b->stride_bytes * (size_t)b->height;
    (void)ssd1363_write_data(b->data, total);
}

void ui_swbuf_flush_gray4_ssd1363(const UiSwBuf *b)
{
    /* Convert 1bpp packed buffer to 4bpp grayscale (0x0 or 0xF nibbles). */
    (void)ssd1363_begin_frame(0, 0, (uint16_t)(b->width - 1), (uint16_t)(b->height - 1));

    const int W = b->width;
    const int H = b->height;
    /* Each row becomes ceil(W/2) bytes at 4bpp. */
    int out_row_bytes = (W + 1) / 2;
    uint8_t line[(DISPLAY_WIDTH + 1) / 2]; /* bound by configured display width */
    if (out_row_bytes > (int)sizeof(line)) {
        return; /* display width misconfigured vs buffer stride, abort to avoid overflow */
    }
    for (int y = 0; y < H; ++y) {
        const uint8_t *src = b->data + (size_t)b->stride_bytes * (size_t)y;
        int out_idx = 0;
        uint8_t byte = 0;
        for (int x = 0; x < W; x += 2) {
            /* Read two pixels */
            int b0 = (src[x >> 3] & (0x80u >> (x & 7))) ? 0xF : 0x0;
            int b1 = 0x0;
            if (x + 1 < W) {
                b1 = (src[(x + 1) >> 3] & (0x80u >> ((x + 1) & 7))) ? 0xF : 0x0;
            }
            byte = (uint8_t)((b0 << 4) | (b1 & 0xF));
            line[out_idx++] = byte;
        }
        (void)ssd1363_write_data(line, out_row_bytes);
    }
}

void ui_swbuf_flush_auto_ssd1363(const UiSwBuf *b)
{
#if DISPLAY_COLOR_BITS == 4
    ui_swbuf_flush_gray4_ssd1363(b);
#else
    ui_swbuf_flush_ssd1363(b);
#endif
}

void ui_swbuf_mark_dirty(UiSwBuf *b, int x, int y, int w, int h)
{
    if (w <= 0 || h <= 0) return;
    int x0 = x < 0 ? 0 : x;
    int y0 = y < 0 ? 0 : y;
    int x1 = x + w; if (x1 > b->width)  x1 = b->width;
    int y1 = y + h; if (y1 > b->height) y1 = b->height;
    if (x0 >= x1 || y0 >= y1) return;
    if (!b->dirty) {
        b->dirty = 1; b->d_x0 = x0; b->d_y0 = y0; b->d_x1 = x1; b->d_y1 = y1;
    } else {
        if (x0 < b->d_x0) b->d_x0 = x0;
        if (y0 < b->d_y0) b->d_y0 = y0;
        if (x1 > b->d_x1) b->d_x1 = x1;
        if (y1 > b->d_y1) b->d_y1 = y1;
    }
}

int ui_swbuf_get_dirty(const UiSwBuf *b, int *x, int *y, int *w, int *h)
{
    if (!b->dirty) return 0;
    if (x) *x = b->d_x0;
    if (y) *y = b->d_y0;
    if (w) *w = b->d_x1 - b->d_x0;
    if (h) *h = b->d_y1 - b->d_y0;
    return 1;
}

void ui_swbuf_clear_dirty(UiSwBuf *b)
{
    b->dirty = 0; b->d_x0 = b->d_y0 = 0; b->d_x1 = b->d_y1 = 0;
}

void ui_swbuf_flush_dirty_ssd1363(const UiSwBuf *b)
{
    if (!b->dirty) { ui_swbuf_flush_ssd1363(b); return; }
    int x, y, w, h;
    if (!ui_swbuf_get_dirty(b, &x, &y, &w, &h)) { ui_swbuf_flush_ssd1363(b); return; }

    (void)ssd1363_begin_frame((uint16_t)x, (uint16_t)y, (uint16_t)(x + w - 1), (uint16_t)(y + h - 1));

    /* Pack the region tightly so bits align to x, avoiding leakage from neighbouring columns. */
    const uint8_t *row = b->data + (size_t)b->stride_bytes * (size_t)y;
    uint8_t line[(DISPLAY_WIDTH + 7) / 8];
    int bits_in_line = w;
    /* number of output bytes for a line of width w */
    size_t out_bytes = (size_t)((bits_in_line + 7) >> 3);
    if (out_bytes > sizeof(line)) {
        return; /* width exceeds configured buffer */
    }

    for (int yy = 0; yy < h; ++yy) {
        memset(line, 0, out_bytes);
        for (int bit = 0; bit < bits_in_line; ++bit) {
            int px = x + bit;
            /* Extract source bit */
            int src_byte = px >> 3;
            int src_bit = 7 - (px & 7);
            int v = (row[src_byte] >> src_bit) & 1;
            /* Pack into output aligned to bit position 0..w-1 */
            int out_byte = bit >> 3;
            int out_bit = 7 - (bit & 7);
            if (v) {
                line[out_byte] |= (uint8_t)(1u << out_bit);
            }
        }
        (void)ssd1363_write_data(line, out_bytes);
        row += b->stride_bytes;
    }
}

void ui_swbuf_flush_dirty_gray4_ssd1363(const UiSwBuf *b)
{
    if (!b->dirty) { ui_swbuf_flush_gray4_ssd1363(b); return; }
    int x, y, w, h;
    if (!ui_swbuf_get_dirty(b, &x, &y, &w, &h)) { ui_swbuf_flush_gray4_ssd1363(b); return; }

    (void)ssd1363_begin_frame((uint16_t)x, (uint16_t)y, (uint16_t)(x + w - 1), (uint16_t)(y + h - 1));

    /* Each row in region: convert [x..x+w) from 1bpp to 4bpp nibble-packed aligned to window. */
    int out_row_bytes = (w + 1) / 2;
    uint8_t line[(DISPLAY_WIDTH + 1) / 2];
    if (out_row_bytes > (int)sizeof(line)) {
        return; /* region width exceeds configured display width */
    }
    for (int yy = 0; yy < h; ++yy) {
        const uint8_t *src_row = b->data + (size_t)b->stride_bytes * (size_t)(y + yy);
        int out_idx = 0;
        for (int xx = 0; xx < w; xx += 2) {
            int px0 = x + xx;
            int px1 = px0 + 1;
            int b0 = (src_row[px0 >> 3] & (0x80u >> (px0 & 7))) ? 0xF : 0x0;
            int b1 = 0x0;
            if (px1 < x + w) {
                b1 = (src_row[px1 >> 3] & (0x80u >> (px1 & 7))) ? 0xF : 0x0;
            }
            line[out_idx++] = (uint8_t)((b0 << 4) | (b1 & 0xF));
        }
        (void)ssd1363_write_data(line, out_row_bytes);
    }
}

void ui_swbuf_flush_dirty_auto_ssd1363(const UiSwBuf *b)
{
#if DISPLAY_COLOR_BITS == 4
    ui_swbuf_flush_dirty_gray4_ssd1363(b);
#else
    ui_swbuf_flush_dirty_ssd1363(b);
#endif
}
