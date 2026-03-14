/*
 * Unit tests for text layout functions (ui_text_layout.c):
 * - ui_draw_text_line_in_rect: single-line fit/align/ellipsis
 * - ui_draw_text_block: multi-line wrap/clip/auto + vertical alignment
 *
 * Uses a mock UiDrawOps that records draw_text calls.
 */

#include "unity.h"
#include <string.h>
#include <stdio.h>
#include "ui_text_layout.h"

/* ================================================================== */
/* Mock draw ops — record draw_text(x, y, text, fg) calls             */
/* ================================================================== */

enum { LOG_MAX = 32, LOG_TEXT_SZ = 96 };

typedef struct {
    int x, y;
    uint8_t fg;
    char text[LOG_TEXT_SZ];
} TextCall;

typedef struct {
    TextCall entries[LOG_MAX];
    int count;
} DrawLog;

static DrawLog s_log;

static void log_reset(void)
{
    memset(&s_log, 0, sizeof(s_log));
}

static void mock_draw_text(void *ctx, int x, int y,
                           const char *text, uint8_t color)
{
    (void)ctx;
    if (s_log.count < LOG_MAX) {
        TextCall *e = &s_log.entries[s_log.count];
        e->x = x;
        e->y = y;
        e->fg = color;
        if (text) {
            snprintf(e->text, LOG_TEXT_SZ, "%s", text);
        } else {
            e->text[0] = '\0';
        }
        s_log.count++;
    }
}

static UiDrawOps make_ops(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_text = mock_draw_text;
    return ops;
}

void setUp(void) { log_reset(); }
void tearDown(void) {}

/* ================================================================== */
/* ui_draw_text_line_in_rect — guards                                  */
/* ================================================================== */

void test_line_null_ops_no_crash(void)
{
    ui_draw_text_line_in_rect(NULL, 0, 0, 60, "Hi", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_line_null_draw_text_no_crash(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    /* draw_text is NULL */
    ui_draw_text_line_in_rect(&ops, 0, 0, 60, "Hi", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_line_null_text_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_line_in_rect(&ops, 0, 0, 60, NULL, 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_line_empty_text_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_line_in_rect(&ops, 0, 0, 60, "", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_line_zero_width_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_line_in_rect(&ops, 0, 0, 0, "Hi", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_line_negative_width_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_line_in_rect(&ops, 0, 0, -10, "Hi", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_line_width_less_than_char_no_draw(void)
{
    UiDrawOps ops = make_ops();
    /* width=5, char_w=6 → max_chars=0 → no draw */
    ui_draw_text_line_in_rect(&ops, 0, 0, 5, "Hi", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

/* ================================================================== */
/* ui_draw_text_line_in_rect — alignment                               */
/* ================================================================== */

void test_line_left_align(void)
{
    UiDrawOps ops = make_ops();
    /* "AB" → 2 chars → 12 px, w_px=60 → left: x stays at 10 */
    ui_draw_text_line_in_rect(&ops, 10, 20, 60, "AB", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(10, s_log.entries[0].x);
    TEST_ASSERT_EQUAL_INT(20, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_STRING("AB", s_log.entries[0].text);
    TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[0].fg);
}

void test_line_center_align(void)
{
    UiDrawOps ops = make_ops();
    /* "AB" → 12 px, w_px=60 → center: x = 10 + (60-12)/2 = 10+24 = 34 */
    ui_draw_text_line_in_rect(&ops, 10, 20, 60, "AB", 15, UI_ALIGN_CENTER, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(34, s_log.entries[0].x);
}

void test_line_right_align(void)
{
    UiDrawOps ops = make_ops();
    /* "AB" → 12 px, w_px=60 → right: x = 10 + 60 - 12 = 58 */
    ui_draw_text_line_in_rect(&ops, 10, 20, 60, "AB", 15, UI_ALIGN_RIGHT, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(58, s_log.entries[0].x);
}

/* ================================================================== */
/* ui_draw_text_line_in_rect — truncation / ellipsis                   */
/* ================================================================== */

void test_line_ellipsis_truncation(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEFGHIJ" (10 chars), w_px=36 → max_chars=6
     * fit with ellipsis → "ABC..." (6 chars) */
    ui_draw_text_line_in_rect(&ops, 0, 0, 36, "ABCDEFGHIJ", 15, UI_ALIGN_LEFT, 1);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("ABC...", s_log.entries[0].text);
}

void test_line_no_ellipsis_clip(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEFGHIJ" (10 chars), w_px=36 → max_chars=6
     * clip (no ellipsis) → "ABCDEF" (6 chars) */
    ui_draw_text_line_in_rect(&ops, 0, 0, 36, "ABCDEFGHIJ", 15, UI_ALIGN_LEFT, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("ABCDEF", s_log.entries[0].text);
}

void test_line_text_exact_fit(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEF" (6 chars), w_px=36 → max_chars=6 → fits exactly */
    ui_draw_text_line_in_rect(&ops, 0, 0, 36, "ABCDEF", 15, UI_ALIGN_LEFT, 1);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("ABCDEF", s_log.entries[0].text);
}

void test_line_center_when_text_fills_width(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEF" exactly fills 36 px → center does nothing, x stays 0 */
    ui_draw_text_line_in_rect(&ops, 0, 0, 36, "ABCDEF", 15, UI_ALIGN_CENTER, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(0, s_log.entries[0].x);
}

/* ================================================================== */
/* ui_draw_text_block — guards                                         */
/* ================================================================== */

void test_block_null_ops_no_crash(void)
{
    ui_draw_text_block(NULL, 0, 0, 60, 32, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_block_null_text_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_block(&ops, 0, 0, 60, 32, NULL, 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_block_empty_text_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_block(&ops, 0, 0, 60, 32, "", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_block_zero_width_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_block(&ops, 0, 0, 0, 32, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_block_zero_height_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_text_block(&ops, 0, 0, 60, 0, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

/* ================================================================== */
/* ui_draw_text_block — ELLIPSIS overflow (non-wrap, single line)      */
/* ================================================================== */

void test_block_ellipsis_short_text(void)
{
    UiDrawOps ops = make_ops();
    /* "Hi" fits in 60 px (10 chars), h=16 (2 lines but no wrap) */
    ui_draw_text_block(&ops, 5, 10, 60, 16, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("Hi", s_log.entries[0].text);
    TEST_ASSERT_EQUAL_INT(5, s_log.entries[0].x);
    TEST_ASSERT_EQUAL_INT(10, s_log.entries[0].y);
}

void test_block_ellipsis_truncates(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEFGHIJ" (10 chars), w_px=36 → max_chars=6
     * ELLIPSIS mode, single-line → "ABC..." */
    ui_draw_text_block(&ops, 0, 0, 36, 8, "ABCDEFGHIJ", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("ABC...", s_log.entries[0].text);
}

/* ================================================================== */
/* ui_draw_text_block — CLIP overflow                                  */
/* ================================================================== */

void test_block_clip_truncates_no_ellipsis(void)
{
    UiDrawOps ops = make_ops();
    /* CLIP: truncate without adding "..." */
    ui_draw_text_block(&ops, 0, 0, 36, 8, "ABCDEFGHIJ", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_CLIP, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("ABCDEF", s_log.entries[0].text);
}

/* ================================================================== */
/* ui_draw_text_block — WRAP overflow                                  */
/* ================================================================== */

void test_block_wrap_two_lines(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEF GHIJ" → 11 chars, w_px=36 → max_chars=6
     * WRAP mode, h=16 →2 lines: "ABCDEF", "GHIJ" */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "ABCDEF GHIJ", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_GREATER_OR_EQUAL(2, s_log.count);
    /* first line at y=0, second at y=8 */
    TEST_ASSERT_EQUAL_INT(0, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(8, s_log.entries[1].y);
}

void test_block_wrap_valign_middle(void)
{
    UiDrawOps ops = make_ops();
    /* "AB CD" wraps to 2 lines (6-char width): "AB CD" fits? 5 chars fits.
     * Actually let's use a narrower width. w_px=18 → 3 chars.
     * "ABCDEF" → wraps to "ABC","DEF". h=32 →4 lines.
     * 2 lines * 8 = 16 px. MIDDLE: start_y = 0+(32-16)/2 = 8 */
    ui_draw_text_block(&ops, 0, 0, 18, 32, "ABCDEF", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_MIDDLE,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_INT(8, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(16, s_log.entries[1].y);
}

void test_block_wrap_valign_bottom(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEF" wraps to 2 lines at w_px=18 (3 chars). h=32.
     * 2 lines * 8 = 16. BOTTOM: start_y = 32-16 = 16 */
    ui_draw_text_block(&ops, 0, 0, 18, 32, "ABCDEF", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_BOTTOM,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_INT(16, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(24, s_log.entries[1].y);
}

void test_block_wrap_truncated_with_dots(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEFGHIJKLMNOP" (16 chars), w_px=36 →6 chars/line, h=16 →2 lines
     * WRAP: 3 lines needed but only 2 fit → truncated, last line gets "..." */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "ABCDEFGHIJKLMNOP", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    /* last line should end with "..." */
    const char *last = s_log.entries[1].text;
    int len = (int)strlen(last);
    TEST_ASSERT_GREATER_OR_EQUAL(3, len);
    TEST_ASSERT_EQUAL_STRING("...", last + len - 3);
}

/* ================================================================== */
/* ui_draw_text_block — AUTO overflow                                  */
/* ================================================================== */

void test_block_auto_short_stays_single_line(void)
{
    UiDrawOps ops = make_ops();
    /* "Hi" (2 chars), w_px=60 →10 chars → fits single line.
     * AUTO with h=16 but text is short → no wrap → 1 draw */
    ui_draw_text_block(&ops, 0, 0, 60, 16, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_AUTO, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("Hi", s_log.entries[0].text);
}

void test_block_auto_long_wraps(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEFGH" (8 chars), w_px=36 → 6 chars → doesn't fit.
     * AUTO with h=16 (2 lines) → decides to wrap → 2 lines */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "ABCDEFGH", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_AUTO, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
}

void test_block_auto_newline_wraps(void)
{
    UiDrawOps ops = make_ops();
    /* "AB\nCD" has newline → AUTO decides wrap. h=16 (2 lines) */
    ui_draw_text_block(&ops, 0, 0, 60, 16, "AB\nCD", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_AUTO, 0);
    TEST_ASSERT_GREATER_OR_EQUAL(2, s_log.count);
}

void test_block_auto_single_line_height_no_wrap(void)
{
    UiDrawOps ops = make_ops();
    /* h=8 →1 line → AUTO can't wrap even if text is long */
    ui_draw_text_block(&ops, 0, 0, 36, 8, "ABCDEFGHIJ", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_AUTO, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    /* should be ellipsis-truncated since auto uses ellipsis for non-wrap */
    TEST_ASSERT_EQUAL_STRING("ABC...", s_log.entries[0].text);
}

/* ================================================================== */
/* ui_draw_text_block — vertical alignment (non-wrap)                  */
/* ================================================================== */

void test_block_valign_top_default(void)
{
    UiDrawOps ops = make_ops();
    /* TOP: single line at y=0 in a 32px tall block */
    ui_draw_text_block(&ops, 0, 0, 60, 32, "AB", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(0, s_log.entries[0].y);
}

void test_block_valign_middle_single(void)
{
    UiDrawOps ops = make_ops();
    /* MIDDLE: single line in 32px → ty = (32-8)/2 = 12 */
    ui_draw_text_block(&ops, 0, 0, 60, 32, "AB", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_MIDDLE,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(12, s_log.entries[0].y);
}

void test_block_valign_bottom_single(void)
{
    UiDrawOps ops = make_ops();
    /* BOTTOM: single line in 32px → ty = 32-8 = 24 */
    ui_draw_text_block(&ops, 0, 0, 60, 32, "AB", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_BOTTOM,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(24, s_log.entries[0].y);
}

/* ================================================================== */
/* ui_draw_text_block — max_lines clamping                             */
/* ================================================================== */

void test_block_max_lines_clamps(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEFGHIJKLMNOP" (16 chars), w_px=36 → 6 chars/line.
     * h=32 →4 lines. max_lines=1 → only 1 line output.
     * WRAP mode with max_lines=1 */
    ui_draw_text_block(&ops, 0, 0, 36, 32, "ABCDEFGHIJKLMNOP", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 1);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
}

void test_block_max_lines_zero_uses_height(void)
{
    UiDrawOps ops = make_ops();
    /* max_lines=0 should use height-based limit (h=16 → 2 lines) */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "ABCDEFGHIJKLMNOP", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
}

/* ================================================================== */
/* ui_draw_text_block — horizontal alignment in wrap mode              */
/* ================================================================== */

void test_block_wrap_center_align(void)
{
    UiDrawOps ops = make_ops();
    /* "AB" → 2 chars → 12 px. w_px=36. center: x = (36-12)/2 = 12
     * WRAP mode, text fits on one line */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "AB", 15,
                       UI_ALIGN_CENTER, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(12, s_log.entries[0].x);
}

void test_block_wrap_right_align(void)
{
    UiDrawOps ops = make_ops();
    /* "AB" → 12 px. w_px=36. right: x = 36 - 12 = 24 */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "AB", 15,
                       UI_ALIGN_RIGHT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(24, s_log.entries[0].x);
}

/* ================================================================== */
/* ui_draw_text_block — newline flattening in non-wrap mode            */
/* ================================================================== */

void test_block_ellipsis_flattens_newlines(void)
{
    UiDrawOps ops = make_ops();
    /* "AB\nCD" in ELLIPSIS mode → flattened to "AB CD" (single line) */
    ui_draw_text_block(&ops, 0, 0, 60, 8, "AB\nCD", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("AB CD", s_log.entries[0].text);
}

/* ================================================================== */
/* ui_draw_text_block — tiny rect                                      */
/* ================================================================== */

void test_block_tiny_height_less_than_char(void)
{
    UiDrawOps ops = make_ops();
    /* h=4 < CHAR_H=8 → max_lines_by_h=0 → early return */
    ui_draw_text_block(&ops, 0, 0, 60, 4, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_ELLIPSIS, 0);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

/* ================================================================== */
/* Round-8 additions                                                   */
/* ================================================================== */

void test_line_right_align_exact_fit(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDE" = 5*6 = 30 px, w_px=30 → exact fit → right align x stays at 0 */
    ui_draw_text_line_in_rect(&ops, 0, 0, 30, "ABCDE", 15,
                              UI_ALIGN_RIGHT, 1);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    /* text_px == w_px → xx stays at x (no shift) */
    TEST_ASSERT_EQUAL_INT(0, s_log.entries[0].x);
}

void test_block_wrap_newline_forces_break(void)
{
    UiDrawOps ops = make_ops();
    /* "AB\nCD" in WRAP mode with plenty of width → newline forces two lines */
    ui_draw_text_block(&ops, 0, 0, 60, 16, "AB\nCD", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_INT(0, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(8, s_log.entries[1].y);
}

void test_block_clip_short_text_no_truncation(void)
{
    UiDrawOps ops = make_ops();
    /* "Hi" = 2 chars, w_px=60 → fits → CLIP outputs without truncation */
    ui_draw_text_block(&ops, 0, 0, 60, 8, "Hi", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_CLIP, 0);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("Hi", s_log.entries[0].text);
}

void test_block_max_lines_clamped_by_height(void)
{
    UiDrawOps ops = make_ops();
    /* max_lines=10 but h=16 → only 2 lines by height.
     * "ABCDEFGHIJKLMNOP" wraps at w_px=36 (6 chars/line) → 3+ lines needed.
     * Clamped to 2. */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "ABCDEFGHIJKLMNOP", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 10);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
}

void test_block_wrap_exact_lines_no_dots(void)
{
    UiDrawOps ops = make_ops();
    /* "ABCDEF GHIJ" at w_px=36 (6 chars/line), h=16 (2 lines).
     * WRAP: "ABCDEF" (6), "GHIJ" (4) → exactly 2 lines, no truncation.
     * Last line should NOT have "..." */
    ui_draw_text_block(&ops, 0, 0, 36, 16, "ABCDEF GHIJ", 15,
                       UI_ALIGN_LEFT, UI_VALIGN_TOP,
                       UI_TEXT_OVERFLOW_WRAP, 0);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    /* second line should be "GHIJ" without ellipsis */
    const char *last = s_log.entries[1].text;
    TEST_ASSERT_FALSE(strstr(last, "...") != NULL);
}
