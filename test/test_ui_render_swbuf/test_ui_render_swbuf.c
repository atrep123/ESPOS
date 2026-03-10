#include "unity.h"

#include <string.h>

#include "ui_render.h"
#include "ui_render_swbuf.h"
#ifndef ESP_PLATFORM
#include "ssd1363_stub_capture.h"
#endif

void setUp(void) {}
void tearDown(void) {}

void test_swbuf_clear_marks_full_dirty(void)
{
    uint8_t backing[128];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 32, 8);
    ui_swbuf_clear(&b, 0);

#if DISPLAY_COLOR_BITS == 4
    TEST_ASSERT_EQUAL_INT(16, b.stride_bytes);
#else
    TEST_ASSERT_EQUAL_INT(4, b.stride_bytes);
#endif

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    TEST_ASSERT_EQUAL_INT(0, x);
    TEST_ASSERT_EQUAL_INT(0, y);
    TEST_ASSERT_EQUAL_INT(32, w);
    TEST_ASSERT_EQUAL_INT(8, h);
}

void test_swbuf_mark_dirty_merges_regions(void)
{
    uint8_t backing[128];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 32, 8);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_mark_dirty(&b, 1, 1, 2, 2);
    ui_swbuf_mark_dirty(&b, 10, 3, 2, 2);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    TEST_ASSERT_EQUAL_INT(1, x);
    TEST_ASSERT_EQUAL_INT(1, y);
    TEST_ASSERT_EQUAL_INT(11, w);
    TEST_ASSERT_EQUAL_INT(4, h);
}

#ifndef ESP_PLATFORM
typedef struct {
    int count;
    char text[8][96];
} TextCapture;

static void noop_fill_rect(void *ctx, int x, int y, int w, int h, uint8_t color)
{
    (void)ctx; (void)x; (void)y; (void)w; (void)h; (void)color;
}

static void noop_hline(void *ctx, int x, int y, int w, uint8_t color)
{
    (void)ctx; (void)x; (void)y; (void)w; (void)color;
}

static void noop_vline(void *ctx, int x, int y, int h, uint8_t color)
{
    (void)ctx; (void)x; (void)y; (void)h; (void)color;
}

static void noop_rect(void *ctx, int x, int y, int w, int h, uint8_t color)
{
    (void)ctx; (void)x; (void)y; (void)w; (void)h; (void)color;
}

static void capture_text(void *ctx, int x, int y, const char *text, uint8_t color)
{
    (void)x; (void)y; (void)color;
    TextCapture *cap = (TextCapture *)ctx;
    if (cap == NULL) {
        return;
    }
    if (cap->count < (int)(sizeof(cap->text) / sizeof(cap->text[0]))) {
        strncpy(cap->text[cap->count], text ? text : "", sizeof(cap->text[cap->count]) - 1);
        cap->text[cap->count][sizeof(cap->text[cap->count]) - 1] = '\0';
    }
    cap->count += 1;
}

static UiDrawOps make_capture_ops(TextCapture *cap)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.ctx = cap;
    ops.fill_rect = noop_fill_rect;
    ops.draw_hline = noop_hline;
    ops.draw_vline = noop_vline;
    ops.draw_rect = noop_rect;
    ops.draw_text = capture_text;
    return ops;
}

void test_render_label_overflow_ellipsis_truncates(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.x = 0;
    w.y = 0;
    w.width = 32;
    w.height = 10;
    w.border = 0;
    w.text = "ABCDEFGHIJ";
    w.text_overflow = UI_TEXT_OVERFLOW_ELLIPSIS;
    w.align = UI_ALIGN_LEFT;
    w.valign = UI_VALIGN_TOP;
    w.visible = 1;
    w.enabled = 1;

    ui_render_widget(&w, &ops);

    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("AB...", cap.text[0]);
}

void test_render_label_overflow_clip_truncates_without_ellipsis(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.x = 0;
    w.y = 0;
    w.width = 32;
    w.height = 10;
    w.border = 0;
    w.text = "ABCDEFGHIJ";
    w.text_overflow = UI_TEXT_OVERFLOW_CLIP;
    w.align = UI_ALIGN_LEFT;
    w.valign = UI_VALIGN_TOP;
    w.visible = 1;
    w.enabled = 1;

    ui_render_widget(&w, &ops);

    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("ABCDE", cap.text[0]);
}

void test_render_label_overflow_wrap_wraps_and_ellipsizes_last_line(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.x = 0;
    w.y = 0;
    w.width = 32;
    w.height = 18;
    w.border = 0;
    w.text = "one two three";
    w.text_overflow = UI_TEXT_OVERFLOW_WRAP;
    w.align = UI_ALIGN_LEFT;
    w.valign = UI_VALIGN_TOP;
    w.max_lines = 2;
    w.visible = 1;
    w.enabled = 1;

    ui_render_widget(&w, &ops);

    TEST_ASSERT_EQUAL_INT(2, cap.count);
    TEST_ASSERT_EQUAL_STRING("one", cap.text[0]);
    TEST_ASSERT_EQUAL_STRING("tw...", cap.text[1]);
}

void test_render_checkbox_overflow_clip_truncates_without_ellipsis(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_CHECKBOX;
    w.x = 0;
    w.y = 0;
    w.width = 40;
    w.height = 16;
    w.border = 0;
    w.text = "ABCDEFGHIJ";
    w.text_overflow = UI_TEXT_OVERFLOW_CLIP;
    w.visible = 1;
    w.enabled = 1;

    ui_render_widget(&w, &ops);

    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("ABCDE", cap.text[0]);
}
#endif /* !ESP_PLATFORM */

#if !defined(ESP_PLATFORM) && DISPLAY_COLOR_BITS == 4
void test_swbuf_flush_dirty_gray4_aligns_x_to_columns(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 16, 2);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* Prime a known even/odd pixel pair. */
    ui_swbuf_fill_rect(&b, 0, 0, 1, 1, 2);
    ui_swbuf_clear_dirty(&b);
    ui_swbuf_fill_rect(&b, 1, 0, 1, 1, 3);

    ssd1363_stub_reset();
    ui_swbuf_flush_dirty_gray4_ssd1363(&b);

    /* x must be aligned to 4px columns for SSD1363 4bpp windows. */
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_x0());
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_y0());
    TEST_ASSERT_EQUAL_UINT16(3, ssd1363_stub_last_x1());
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_y1());

    uint8_t first[4] = {0};
    size_t n = ssd1363_stub_copy_first_write(first, sizeof(first));
    TEST_ASSERT_EQUAL_UINT32(2, (uint32_t)n);
    TEST_ASSERT_EQUAL_UINT8(0x23, first[0]);
    TEST_ASSERT_EQUAL_UINT8(0x00, first[1]);
}

void test_swbuf_flush_gray4_full_sends_all_rows(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);

    ssd1363_stub_reset();
    ui_swbuf_flush_gray4_ssd1363(&b);

    /* Full flush: begin_frame covers entire buffer. */
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_x0());
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_y0());
    TEST_ASSERT_EQUAL_UINT16(7, ssd1363_stub_last_x1());
    TEST_ASSERT_EQUAL_UINT16(3, ssd1363_stub_last_y1());

    /* 4 rows, each ceil(8/2)=4 bytes = 16 bytes total. */
    TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)ssd1363_stub_write_calls());
    TEST_ASSERT_EQUAL_UINT32(16, (uint32_t)ssd1363_stub_total_bytes());
}

void test_swbuf_flush_gray4_full_preserves_pixel_data(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 4, 1);
    ui_swbuf_clear(&b, 0);

    /* Set first two pixels: px0=0xA, px1=0x5 → byte = 0xA5 */
    ui_swbuf_fill_rect(&b, 0, 0, 1, 1, 0xA);
    ui_swbuf_fill_rect(&b, 1, 0, 1, 1, 0x5);

    ssd1363_stub_reset();
    ui_swbuf_flush_gray4_ssd1363(&b);

    uint8_t first[4] = {0};
    size_t n = ssd1363_stub_copy_first_write(first, sizeof(first));
    TEST_ASSERT_EQUAL_UINT32(2, (uint32_t)n); /* ceil(4/2) = 2 bytes */
    TEST_ASSERT_EQUAL_UINT8(0xA5, first[0]);
    TEST_ASSERT_EQUAL_UINT8(0x00, first[1]);
}

void test_swbuf_flush_auto_delegates_to_gray4(void)
{
    /* In 4bpp mode, flush_auto should behave identically to flush_gray4. */
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 2);
    ui_swbuf_clear(&b, 0);

    ssd1363_stub_reset();
    ui_swbuf_flush_auto_ssd1363(&b);

    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_x0());
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_y0());
    TEST_ASSERT_EQUAL_UINT16(7, ssd1363_stub_last_x1());
    TEST_ASSERT_EQUAL_UINT16(1, ssd1363_stub_last_y1());
    TEST_ASSERT_EQUAL_UINT32(2, (uint32_t)ssd1363_stub_write_calls());
}

void test_swbuf_flush_dirty_auto_delegates_to_gray4(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 2);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* Mark a single pixel dirty. */
    ui_swbuf_fill_rect(&b, 2, 0, 1, 1, 7);

    ssd1363_stub_reset();
    ui_swbuf_flush_dirty_auto_ssd1363(&b);

    /* Should flush aligned 4px dirty region, same as dirty_gray4. */
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_x0());
    TEST_ASSERT_EQUAL_UINT16(3, ssd1363_stub_last_x1());
    TEST_ASSERT_TRUE(ssd1363_stub_write_calls() > 0);
}

void test_swbuf_flush_dirty_gray4_clean_falls_back_to_full(void)
{
    /* When dirty flag is clear, flush_dirty_gray4 should fall back to full flush. */
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 2);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ssd1363_stub_reset();
    ui_swbuf_flush_dirty_gray4_ssd1363(&b);

    /* Falls back to full flush — covers entire frame. */
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_x0());
    TEST_ASSERT_EQUAL_UINT16(0, ssd1363_stub_last_y0());
    TEST_ASSERT_EQUAL_UINT16(7, ssd1363_stub_last_x1());
    TEST_ASSERT_EQUAL_UINT16(1, ssd1363_stub_last_y1());
    TEST_ASSERT_TRUE(ssd1363_stub_write_calls() > 0);
}

void test_swbuf_flush_dirty_gray4_multi_row_region(void)
{
    uint8_t backing[128];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 16, 8);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* Dirty a 3-row region at x=5..6, y=2..4. */
    ui_swbuf_fill_rect(&b, 5, 2, 2, 3, 0xF);

    ssd1363_stub_reset();
    ui_swbuf_flush_dirty_gray4_ssd1363(&b);

    /* Region x=5..6: aligned to 4px → x0=4, x1=7. */
    TEST_ASSERT_EQUAL_UINT16(4, ssd1363_stub_last_x0());
    TEST_ASSERT_EQUAL_UINT16(2, ssd1363_stub_last_y0());
    TEST_ASSERT_EQUAL_UINT16(7, ssd1363_stub_last_x1());
    TEST_ASSERT_EQUAL_UINT16(4, ssd1363_stub_last_y1());
    /* 3 rows, each ceil(4/2)=2 bytes = 6 bytes. */
    TEST_ASSERT_EQUAL_UINT32(3, (uint32_t)ssd1363_stub_write_calls());
    TEST_ASSERT_EQUAL_UINT32(6, (uint32_t)ssd1363_stub_total_bytes());
}

void test_swbuf_blit_mono_gray4_sets_pixels(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 3);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* 4x2 mask, MSB-first: row0=1010, row1=0110 */
    static const uint8_t mask[] = { 0xA0, 0x60 };
    ui_swbuf_blit_mono(&b, 2, 1, 4, 2, 1, mask, 5, 0);

    /* Each byte contains two pixels: hi nibble = even x, lo nibble = odd x. */
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[0 * b.stride_bytes + 0]);
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[0 * b.stride_bytes + 1]);

    /* y=1: pixels at x=2 and x=4 are set to 5 -> bytes 1 and 2 are 0x50 */
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[1 * b.stride_bytes + 0]);
    TEST_ASSERT_EQUAL_UINT8(0x50, b.data[1 * b.stride_bytes + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x50, b.data[1 * b.stride_bytes + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[1 * b.stride_bytes + 3]);

    /* y=2: pixels at x=3 and x=4 are set -> byte1=0x05, byte2=0x50 */
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[2 * b.stride_bytes + 0]);
    TEST_ASSERT_EQUAL_UINT8(0x05, b.data[2 * b.stride_bytes + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x50, b.data[2 * b.stride_bytes + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[2 * b.stride_bytes + 3]);
}

void test_swbuf_hline_sets_pixels_and_marks_dirty(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_hline(&b, 0, 1, 4, 5);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    TEST_ASSERT_EQUAL_INT(0, x);
    TEST_ASSERT_EQUAL_INT(1, y);
    TEST_ASSERT_EQUAL_INT(4, w);
    TEST_ASSERT_EQUAL_INT(1, h);

    /* pixels at y=1, x=0..3 should be set to gray4 level 5 */
    TEST_ASSERT_EQUAL_UINT8(0x55, b.data[1 * b.stride_bytes + 0]); /* nibbles: 5,5 */
    TEST_ASSERT_EQUAL_UINT8(0x55, b.data[1 * b.stride_bytes + 1]); /* nibbles: 5,5 */
}

void test_swbuf_vline_sets_pixels_and_marks_dirty(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_vline(&b, 2, 0, 3, 7);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    TEST_ASSERT_EQUAL_INT(2, x);
    TEST_ASSERT_EQUAL_INT(0, y);
    TEST_ASSERT_EQUAL_INT(1, w);
    TEST_ASSERT_EQUAL_INT(3, h);
}

void test_swbuf_fill_rect_marks_dirty(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_fill_rect(&b, 1, 1, 3, 2, 10);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    TEST_ASSERT_EQUAL_INT(1, x);
    TEST_ASSERT_EQUAL_INT(1, y);
    TEST_ASSERT_EQUAL_INT(3, w);
    TEST_ASSERT_EQUAL_INT(2, h);
}

void test_swbuf_text_marks_dirty(void)
{
    uint8_t backing[256];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 32, 16);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_text(&b, 0, 0, "AB", 1);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    /* "AB" = 2 chars × 6px wide = 12px, 8px tall */
    TEST_ASSERT_EQUAL_INT(0, x);
    TEST_ASSERT_EQUAL_INT(0, y);
    TEST_ASSERT_EQUAL_INT(12, w);
    TEST_ASSERT_EQUAL_INT(8, h);
}

void test_swbuf_text_null_no_crash(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* Should not crash */
    ui_swbuf_text(&b, 0, 0, NULL, 1);
    ui_swbuf_text(NULL, 0, 0, "A", 1);

    TEST_ASSERT_FALSE(ui_swbuf_get_dirty(&b, NULL, NULL, NULL, NULL));
}

void test_swbuf_text_empty_no_dirty(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_text(&b, 0, 0, "", 1);
    TEST_ASSERT_FALSE(ui_swbuf_get_dirty(&b, NULL, NULL, NULL, NULL));
}

void test_swbuf_rect_marks_dirty(void)
{
    uint8_t backing[128];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 16, 8);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    ui_swbuf_rect(&b, 2, 2, 6, 4, 1);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    /* rect draws outline: top hline, bottom hline, left vline, right vline */
    TEST_ASSERT_EQUAL_INT(2, x);
    TEST_ASSERT_EQUAL_INT(2, y);
}

void test_swbuf_make_ops_fills_all(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);

    UiDrawOps ops;
    ui_swbuf_make_ops(&b, &ops);

    TEST_ASSERT_NOT_NULL(ops.fill_rect);
    TEST_ASSERT_NOT_NULL(ops.draw_hline);
    TEST_ASSERT_NOT_NULL(ops.draw_vline);
    TEST_ASSERT_NOT_NULL(ops.draw_rect);
    TEST_ASSERT_NOT_NULL(ops.draw_text);
    TEST_ASSERT_NOT_NULL(ops.blit_mono);
    TEST_ASSERT_EQUAL_PTR(&b, ops.ctx);
}

void test_swbuf_fill_rect_sets_pixels(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* Fill 2x2 rect at (2,1) with color 7 */
    ui_swbuf_fill_rect(&b, 2, 1, 2, 2, 7);

    /* y=1: byte 1 covers x=2 (high nibble=7) and x=3 (low nibble=7) */
    TEST_ASSERT_EQUAL_UINT8(0x77, b.data[1 * b.stride_bytes + 1]);
    /* y=2: same pattern */
    TEST_ASSERT_EQUAL_UINT8(0x77, b.data[2 * b.stride_bytes + 1]);
    /* Surrounding bytes should still be 0 */
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[1 * b.stride_bytes + 0]);
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[1 * b.stride_bytes + 2]);
}

void test_swbuf_hline_clipping(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* hline starting at negative x — should clip left */
    ui_swbuf_hline(&b, -2, 0, 5, 3);
    /* Should draw x=0..2 (5 pixels starting at -2, clipped to 0) */
    /* byte 0: x=0 high=3, x=1 low=3 → 0x33 */
    TEST_ASSERT_EQUAL_UINT8(0x33, b.data[0]);
    /* byte 1: x=2 high=3, x=3 low=0 → 0x30 */
    TEST_ASSERT_EQUAL_UINT8(0x30, b.data[1]);

    /* hline going beyond right edge — should clip right */
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);
    ui_swbuf_hline(&b, 6, 0, 10, 4);
    /* Should draw x=6..7 only */
    /* byte 3: x=6 high=4, x=7 low=4 → 0x44 */
    TEST_ASSERT_EQUAL_UINT8(0x44, b.data[3]);

    /* hline at out-of-bounds y — should be no-op */
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);
    ui_swbuf_hline(&b, 0, 10, 4, 5);
    TEST_ASSERT_FALSE(ui_swbuf_get_dirty(&b, NULL, NULL, NULL, NULL));
}

void test_swbuf_vline_clipping(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* vline starting at negative y — should clip top */
    ui_swbuf_vline(&b, 0, -1, 3, 6);
    /* Should draw y=0..1 */
    TEST_ASSERT_EQUAL_UINT8(0x60, b.data[0 * b.stride_bytes + 0]);
    TEST_ASSERT_EQUAL_UINT8(0x60, b.data[1 * b.stride_bytes + 0]);
    TEST_ASSERT_EQUAL_UINT8(0x00, b.data[2 * b.stride_bytes + 0]);

    /* vline at out-of-bounds x — should be no-op */
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);
    ui_swbuf_vline(&b, 20, 0, 2, 5);
    TEST_ASSERT_FALSE(ui_swbuf_get_dirty(&b, NULL, NULL, NULL, NULL));
}

void test_swbuf_rect_draws_outline(void)
{
    uint8_t backing[128];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 8);
    ui_swbuf_clear(&b, 0);
    ui_swbuf_clear_dirty(&b);

    /* Draw 4x4 rect outline at (2,2) with color 9 */
    ui_swbuf_rect(&b, 2, 2, 4, 4, 9);

    /* Top edge y=2: x=2..5 should have color 9 */
    TEST_ASSERT_EQUAL_UINT8(0x99, b.data[2 * b.stride_bytes + 1]); /* x=2,3 */
    TEST_ASSERT_EQUAL_UINT8(0x99, b.data[2 * b.stride_bytes + 2]); /* x=4,5 */

    /* Bottom edge y=5 */
    TEST_ASSERT_EQUAL_UINT8(0x99, b.data[5 * b.stride_bytes + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x99, b.data[5 * b.stride_bytes + 2]);

    /* Left edge x=2 at y=3: byte 1 high nibble = 9, low nibble should be 0 */
    TEST_ASSERT_EQUAL_UINT8(0x90, b.data[3 * b.stride_bytes + 1]);
    /* Right edge x=5 at y=3: byte 2 low nibble = 9, high=0 */
    TEST_ASSERT_EQUAL_UINT8(0x09, b.data[3 * b.stride_bytes + 2]);
}

void test_swbuf_clear_sets_all_bytes(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);

    /* Clear with color 0 */
    ui_swbuf_clear(&b, 0);
    for (int i = 0; i < 4 * b.stride_bytes; ++i) {
        TEST_ASSERT_EQUAL_UINT8(0x00, b.data[i]);
    }

    /* Clear with color 1 → gray4 level is 0x0F */
    ui_swbuf_clear(&b, 1);
    for (int i = 0; i < 4 * b.stride_bytes; ++i) {
        TEST_ASSERT_EQUAL_UINT8(0xFF, b.data[i]);
    }
}

void test_render_scene_draws_all_visible_widgets(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    /* Widget 0: visible label */
    widgets[0].type = UIW_LABEL;
    widgets[0].x = 0; widgets[0].y = 0;
    widgets[0].width = 60; widgets[0].height = 10;
    widgets[0].text = "Hello";
    widgets[0].visible = 1; widgets[0].enabled = 1;

    /* Widget 1: invisible label */
    widgets[1].type = UIW_LABEL;
    widgets[1].x = 0; widgets[1].y = 10;
    widgets[1].width = 60; widgets[1].height = 10;
    widgets[1].text = "Hidden";
    widgets[1].visible = 0; widgets[1].enabled = 1;

    /* Widget 2: visible button */
    widgets[2].type = UIW_BUTTON;
    widgets[2].x = 0; widgets[2].y = 20;
    widgets[2].width = 60; widgets[2].height = 10;
    widgets[2].text = "Click";
    widgets[2].visible = 1; widgets[2].enabled = 1;

    UiScene scene;
    scene.name = "test";
    scene.width = 256; scene.height = 128;
    scene.widget_count = 3;
    scene.widgets = widgets;

    ui_render_scene(&scene, &ops);

    /* 2 visible text-bearing widgets should produce text draws */
    TEST_ASSERT_EQUAL_INT(2, cap.count);
    TEST_ASSERT_EQUAL_STRING("Hello", cap.text[0]);
    TEST_ASSERT_EQUAL_STRING("Click", cap.text[1]);
}

void test_render_scene_null_no_crash(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    ui_render_scene(NULL, &ops);
    ui_render_scene(NULL, NULL);
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_widget_progressbar(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_PROGRESSBAR;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 14;
    w.border = 1;
    w.value = 50; w.min_value = 0; w.max_value = 100;
    w.text = "50%";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("50%", cap.text[0]);
}

void test_render_widget_slider(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_SLIDER;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 16;
    w.border = 1;
    w.value = 25; w.min_value = 0; w.max_value = 100;
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    /* Slider doesn't draw text, but should not crash */
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_widget_gauge(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_GAUGE;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 12;
    w.border = 1;
    w.value = 75; w.min_value = 0; w.max_value = 100;
    w.text = "75";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("75", cap.text[0]);
}

void test_render_widget_radiobutton(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_RADIOBUTTON;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 12;
    w.text = "Option 1";
    w.checked = 1;
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Option 1", cap.text[0]);
}

void test_render_widget_textbox(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_TEXTBOX;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 12;
    w.border = 1;
    w.text = "Input";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Input", cap.text[0]);
}

void test_render_widget_chart(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_CHART;
    w.x = 0; w.y = 0;
    w.width = 80; w.height = 40;
    w.border = 1;
    w.value = 50; w.min_value = 0; w.max_value = 100;
    w.text = "Chart";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Chart", cap.text[0]);
}

void test_render_widget_unknown_type(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = 99;
    w.x = 0; w.y = 0;
    w.width = 20; w.height = 10;
    w.visible = 1; w.enabled = 1;

    /* Invalid type >= UIW__COUNT is rejected by bounds guard */
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_widget_sentinel_type_rejected(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW__COUNT;  /* sentinel value — not a valid widget type */
    w.x = 0; w.y = 0;
    w.width = 20; w.height = 10;
    w.visible = 1; w.enabled = 1;

    /* Sentinel type must be rejected by bounds guard */
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_label_center_align(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 10;
    w.text = "Hi";
    w.align = UI_ALIGN_CENTER;
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Hi", cap.text[0]);
}

void test_render_label_text_overflow_auto_wraps(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.x = 0; w.y = 0;
    w.width = 32;
    w.height = 20;
    w.text = "one two three";
    w.text_overflow = UI_TEXT_OVERFLOW_AUTO;
    w.align = UI_ALIGN_LEFT;
    w.valign = UI_VALIGN_TOP;
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    /* AUTO with multi-height should wrap */
    TEST_ASSERT_TRUE(cap.count >= 2);
}

void test_render_widget_disabled_style(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BUTTON;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 10;
    w.text = "Disabled";
    w.visible = 1; w.enabled = 0;

    ui_render_widget(&w, &ops);
    /* Should still render text, just with dimmed color */
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Disabled", cap.text[0]);
}

void test_render_widget_button(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BUTTON;
    w.x = 10; w.y = 5;
    w.width = 80; w.height = 14;
    w.border = 1;
    w.text = "OK";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("OK", cap.text[0]);
}

void test_render_widget_button_no_border(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BUTTON;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 12;
    w.border = 0;
    w.text = "No Border";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("No Border", cap.text[0]);
}

void test_render_widget_button_null_text(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BUTTON;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 14;
    w.border = 1;
    w.text = NULL;
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_widget_panel(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_PANEL;
    w.x = 0; w.y = 0;
    w.width = 100; w.height = 40;
    w.border = 1;
    w.text = "Title";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Title", cap.text[0]);
}

void test_render_widget_panel_no_text(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_PANEL;
    w.x = 0; w.y = 0;
    w.width = 100; w.height = 40;
    w.border = 1;
    w.text = NULL;
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_widget_box(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BOX;
    w.x = 5; w.y = 5;
    w.width = 50; w.height = 30;
    w.border = 1;
    w.text = "Box";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    /* Box delegates to panel renderer */
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("Box", cap.text[0]);
}

void test_render_widget_icon_no_crash(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_ICON;
    w.x = 0; w.y = 0;
    w.width = 24; w.height = 24;
    w.border = 0;
    w.text = "wifi";
    w.visible = 1; w.enabled = 1;

    /* Icon rendering without blit_mono falls back to drawing first char as text */
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("w", cap.text[0]);
}

void test_render_widget_icon_with_border(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_ICON;
    w.x = 0; w.y = 0;
    w.width = 24; w.height = 24;
    w.border = 1;
    w.text = "home";
    w.visible = 1; w.enabled = 1;

    ui_render_widget(&w, &ops);
    /* Icon with border falls back to text rendering of first char */
    TEST_ASSERT_EQUAL_INT(1, cap.count);
    TEST_ASSERT_EQUAL_STRING("h", cap.text[0]);
}

void test_render_widget_invisible_skipped(void)
{
    TextCapture cap;
    memset(&cap, 0, sizeof(cap));
    UiDrawOps ops = make_capture_ops(&cap);

    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BUTTON;
    w.x = 0; w.y = 0;
    w.width = 60; w.height = 14;
    w.text = "Hidden";
    w.visible = 0; w.enabled = 1;

    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, cap.count);
}

void test_render_widget_button_border_styles(void)
{
    /* Verify different border styles don't crash */
    uint8_t styles[] = {
        UI_BORDER_NONE, UI_BORDER_SINGLE, UI_BORDER_DOUBLE,
        UI_BORDER_ROUNDED, UI_BORDER_BOLD, UI_BORDER_DASHED
    };
    for (int i = 0; i < (int)(sizeof(styles) / sizeof(styles[0])); i++) {
        TextCapture cap;
        memset(&cap, 0, sizeof(cap));
        UiDrawOps ops = make_capture_ops(&cap);

        UiWidget w;
        memset(&w, 0, sizeof(w));
        w.type = UIW_BUTTON;
        w.x = 0; w.y = 0;
        w.width = 60; w.height = 14;
        w.border = 1;
        w.border_style = styles[i];
        w.text = "Style";
        w.visible = 1; w.enabled = 1;

        ui_render_widget(&w, &ops);
        TEST_ASSERT_EQUAL_INT(1, cap.count);
    }
}
#endif

/* ------------------------------------------------------------------ */
/* blit_mono: stride too small for width → silently rejected           */
/* ------------------------------------------------------------------ */

void test_swbuf_blit_mono_stride_too_small_rejected(void)
{
    uint8_t backing[64];
    UiSwBuf b;
    ui_swbuf_init(&b, backing, 8, 4);
    ui_swbuf_clear(&b, 0);

    /* w=16 needs stride >= 2, but we pass stride=1 */
    static const uint8_t data[] = { 0xFF, 0xFF };
    ui_swbuf_blit_mono(&b, 0, 0, 16, 1, 1, data, 0x0F, 0);

    /* Buffer should be unchanged — blit was rejected */
    for (int i = 0; i < (int)sizeof(backing); ++i) {
        TEST_ASSERT_EQUAL_UINT8(0, backing[i]);
    }
}
