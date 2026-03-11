#include "ui_render_swbuf.h"

#include <string.h>
#include "display/ssd1363.h"
#include "display_config.h"
#include "ui_font_6x8.h"

#if DISPLAY_COLOR_BITS == 4
static inline uint8_t _gray4_level(uint8_t c)
{
    uint8_t v = (uint8_t)(c & 0x0F);
    if (v == 0) {
        return 0;
    }
    /* Keep legacy "1 = on" call sites (UI renderer uses 0/1) visually bright. */
    if (v == 1) {
        return 0x0F;
    }
    return v;
}

static inline void set_px_raw_gray4(UiSwBuf *b, int x, int y, uint8_t v)
{
    if ((unsigned)x >= (unsigned)b->width || (unsigned)y >= (unsigned)b->height) return;
    int byte_index = y * b->stride_bytes + (x >> 1);
    uint8_t cur = b->data[byte_index];
    v = (uint8_t)(v & 0x0F);
    if ((x & 1) == 0) {
        /* even x: high nibble */
        b->data[byte_index] = (uint8_t)((cur & 0x0F) | (uint8_t)(v << 4));
    } else {
        /* odd x: low nibble */
        b->data[byte_index] = (uint8_t)((cur & 0xF0) | v);
    }
}

static inline void set_px(UiSwBuf *b, int x, int y, uint8_t c)
{
    set_px_raw_gray4(b, x, y, _gray4_level(c));
}

static inline uint8_t get_px_gray4_row(const uint8_t *row, int x)
{
    uint8_t byte = row[x >> 1];
    if (x & 1) {
        return (uint8_t)(byte & 0x0F);
    }
    return (uint8_t)((byte >> 4) & 0x0F);
}
#else
static inline void set_px(UiSwBuf *b, int x, int y, uint8_t c)
{
    if ((unsigned)x >= (unsigned)b->width || (unsigned)y >= (unsigned)b->height) return;
    int byte_index = y * b->stride_bytes + (x >> 3);
    uint8_t mask = (uint8_t)(0x80u >> (x & 7));
    if (c) b->data[byte_index] |= mask; else b->data[byte_index] &= (uint8_t)~mask;
}

static inline uint8_t get_px_1bpp_row(const uint8_t *row, int x)
{
    uint8_t byte = row[x >> 3];
    uint8_t mask = (uint8_t)(0x80u >> (x & 7));
    return (byte & mask) ? 1 : 0;
}
#endif

void ui_swbuf_init(UiSwBuf *b, void *mem, int width, int height)
{
    b->width = width;
    b->height = height;
#if DISPLAY_COLOR_BITS == 4
    b->stride_bytes = (width + 1) >> 1;
#else
    b->stride_bytes = (width + 7) >> 3;
#endif
    b->data = (uint8_t *)mem;
    b->dirty = 0;
    b->d_x0 = b->d_y0 = 0;
    b->d_x1 = b->d_y1 = 0;
}

void ui_swbuf_clear(UiSwBuf *b, uint8_t color)
{
#if DISPLAY_COLOR_BITS == 4
    uint8_t v = _gray4_level(color);
    uint8_t byte = (uint8_t)((v << 4) | v);
    memset(b->data, byte, (size_t)b->stride_bytes * (size_t)b->height);
#else
    memset(b->data, color ? 0xFF : 0x00, (size_t)b->stride_bytes * (size_t)b->height);
#endif
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
    if (w <= 0 || h <= 0) return;
    ui_swbuf_hline(ctx, x, y, w, color);
    ui_swbuf_hline(ctx, x, y + h - 1, w, color);
    ui_swbuf_vline(ctx, x, y, h, color);
    ui_swbuf_vline(ctx, x + w - 1, y, h, color);
}

void ui_swbuf_text(void *ctx, int x, int y, const char *text, uint8_t color)
{
    UiSwBuf *b = (UiSwBuf *)ctx;
    if (b == NULL || text == NULL || *text == '\0') {
        return;
    }

    int cursor_x = x;
    int line_y = y;
    int min_x = cursor_x;
    int min_y = line_y;
    int max_x = cursor_x;
    int max_y = line_y;
    int any = 0;

    for (const char *p = text; *p; ++p) {
        char ch = *p;
        if (ch == '\n') {
            line_y += UI_FONT_CHAR_H;
            cursor_x = x;
            continue;
        }

        const uint8_t *glyph = ui_font6x8_glyph(ch);
        for (int row = 0; row < UI_FONT_CHAR_H; ++row) {
            uint8_t bits = glyph[row];
            int yy = line_y + row;
            for (int col = 0; col < UI_FONT_CHAR_W; ++col) {
                int shift = (UI_FONT_CHAR_W - 1) - col;
                if (bits & (uint8_t)(1u << shift)) {
                    set_px(b, cursor_x + col, yy, color);
                }
            }
        }

        any = 1;
        if (cursor_x + UI_FONT_CHAR_W > max_x) {
            max_x = cursor_x + UI_FONT_CHAR_W;
        }
        if (line_y + UI_FONT_CHAR_H > max_y) {
            max_y = line_y + UI_FONT_CHAR_H;
        }
        cursor_x += UI_FONT_CHAR_W;
    }

    if (any) {
        ui_swbuf_mark_dirty(b, min_x, min_y, max_x - min_x, max_y - min_y);
    }
}

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
)
{
    UiSwBuf *b = (UiSwBuf *)ctx;
    if (b == NULL || data == NULL) {
        return;
    }
    if (w <= 0 || h <= 0 || stride_bytes <= 0) {
        return;
    }
    if (stride_bytes < ((w + 7) >> 3)) {
        return;  /* stride too small for declared width */
    }
    if (stride_bytes > 1024) {
        return;  /* unreasonably large stride */
    }

    int x0 = (x < 0) ? 0 : x;
    int y0 = (y < 0) ? 0 : y;
    int x1 = x + w; if (x1 > b->width)  x1 = b->width;
    int y1 = y + h; if (y1 > b->height) y1 = b->height;
    if (x0 >= x1 || y0 >= y1) {
        return;
    }

    const int src_x0 = x0 - x;
    const int src_y0 = y0 - y;

#if DISPLAY_COLOR_BITS == 4
    const uint8_t xor_mask = _gray4_level(color);
#else
    const uint8_t xor_mask = (color != 0) ? 1 : 0;
#endif

    for (int yy = y0; yy < y1; ++yy) {
        const uint8_t *src_row = data + (size_t)stride_bytes * (size_t)(src_y0 + (yy - y0));
#if DISPLAY_COLOR_BITS == 4
        uint8_t *dst_row = b->data + (size_t)b->stride_bytes * (size_t)yy;
#else
        const uint8_t *dst_row = b->data + (size_t)b->stride_bytes * (size_t)yy;
#endif
        for (int xx = x0; xx < x1; ++xx) {
            int sx = src_x0 + (xx - x0);
            uint8_t m = (uint8_t)(0x80u >> (sx & 7));
            if ((src_row[sx >> 3] & m) == 0) {
                continue;
            }

            switch (mode) {
                case 1: /* invert */
#if DISPLAY_COLOR_BITS == 4
                {
                    uint8_t cur = get_px_gray4_row(dst_row, xx);
                    set_px_raw_gray4(b, xx, yy, (uint8_t)(cur ^ 0x0F));
                }
#else
                {
                    uint8_t cur = get_px_1bpp_row(dst_row, xx);
                    set_px(b, xx, yy, (uint8_t)(cur ? 0 : 1));
                }
#endif
                    break;
                case 2: /* xor */
#if DISPLAY_COLOR_BITS == 4
                {
                    uint8_t cur = get_px_gray4_row(dst_row, xx);
                    set_px_raw_gray4(b, xx, yy, (uint8_t)(cur ^ (xor_mask & 0x0F)));
                }
#else
                {
                    uint8_t cur = get_px_1bpp_row(dst_row, xx);
                    set_px(b, xx, yy, (uint8_t)(cur ^ (xor_mask ? 1 : 0)));
                }
#endif
                    break;
                case 0: /* normal */
                default:
                    set_px(b, xx, yy, color);
                    break;
            }
        }
    }

    ui_swbuf_mark_dirty(b, x0, y0, x1 - x0, y1 - y0);
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
    ops->blit_mono  = ui_swbuf_blit_mono; /* optional */
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
    if (ssd1363_begin_frame(0, 0, (uint16_t)(b->width - 1), (uint16_t)(b->height - 1)) != ESP_OK) {
        return;
    }

    /* Send packed framebuffer as-is (1bpp). If your panel expects different
     * pixel format (e.g., 4-bit grayscale), convert here before sending.
     */
    size_t total = (size_t)b->stride_bytes * (size_t)b->height;
    (void)ssd1363_write_data(b->data, total);
}

void ui_swbuf_flush_gray4_ssd1363(const UiSwBuf *b)
{
    /* Flush as 4bpp grayscale. For 1bpp builds, convert on the fly (0x0/0xF). */
    if (ssd1363_begin_frame(0, 0, (uint16_t)(b->width - 1), (uint16_t)(b->height - 1)) != ESP_OK) {
        return;
    }

    const int W = b->width;
    const int H = b->height;
    /* Each row becomes ceil(W/2) bytes at 4bpp. */
    int out_row_bytes = (W + 1) / 2;
#if DISPLAY_COLOR_BITS == 4
    for (int y = 0; y < H; ++y) {
        const uint8_t *row = b->data + (size_t)b->stride_bytes * (size_t)y;
        (void)ssd1363_write_data(row, (size_t)out_row_bytes);
    }
    return;
#else
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
#endif
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

    if (ssd1363_begin_frame((uint16_t)x, (uint16_t)y, (uint16_t)(x + w - 1), (uint16_t)(y + h - 1)) != ESP_OK) {
        return;
    }

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

    /*
     * SSD1363 4bpp addressing uses column units of 4 pixels (2 bytes per column),
     * so dirty regions must be aligned to 4-pixel boundaries to avoid misalignment.
     * Expand the dirty window to whole columns and pack from the full framebuffer.
     */
    int x0 = x;
    int x1 = x + w - 1;
    int ax0 = x0 & ~3;
    int ax1 = x1 | 3;
    if (ax0 < 0) ax0 = 0;
    if (ax1 >= b->width) ax1 = b->width - 1;
    int aw = (ax1 >= ax0) ? (ax1 - ax0 + 1) : 0;
    if (aw <= 0) {
        return;
    }

    if (ssd1363_begin_frame((uint16_t)ax0, (uint16_t)y, (uint16_t)ax1, (uint16_t)(y + h - 1)) != ESP_OK) {
        return;
    }

    /* Each row in region: convert [x..x+w) from 1bpp to 4bpp nibble-packed aligned to window. */
    int out_row_bytes = (aw + 1) / 2;
    uint8_t line[(DISPLAY_WIDTH + 1) / 2];
    if (out_row_bytes > (int)sizeof(line)) {
        return; /* region width exceeds configured display width */
    }
    for (int yy = 0; yy < h; ++yy) {
#if DISPLAY_COLOR_BITS == 4
        const uint8_t *src_row = b->data + (size_t)b->stride_bytes * (size_t)(y + yy);
        int out_idx = 0;
        for (int xx = 0; xx < aw; xx += 2) {
            int px0 = ax0 + xx;
            int px1 = px0 + 1;
            uint8_t b0 = get_px_gray4_row(src_row, px0);
            uint8_t b1 = 0;
            if (px1 <= ax1) {
                b1 = get_px_gray4_row(src_row, px1);
            }
            line[out_idx++] = (uint8_t)((uint8_t)(b0 << 4) | (b1 & 0x0F));
        }
        (void)ssd1363_write_data(line, (size_t)out_row_bytes);
#else
        const uint8_t *src_row = b->data + (size_t)b->stride_bytes * (size_t)(y + yy);
        int out_idx = 0;
        for (int xx = 0; xx < aw; xx += 2) {
            int px0 = ax0 + xx;
            int px1 = px0 + 1;
            int b0 = (src_row[px0 >> 3] & (0x80u >> (px0 & 7))) ? 0xF : 0x0;
            int b1 = 0x0;
            if (px1 <= ax1) {
                b1 = (src_row[px1 >> 3] & (0x80u >> (px1 & 7))) ? 0xF : 0x0;
            }
            line[out_idx++] = (uint8_t)((b0 << 4) | (b1 & 0xF));
        }
        (void)ssd1363_write_data(line, out_row_bytes);
#endif
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
