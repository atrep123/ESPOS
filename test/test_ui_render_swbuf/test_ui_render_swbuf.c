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
#endif
