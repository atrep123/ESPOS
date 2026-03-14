/*
 * Unit tests for pure border-style drawing (ui_border.c):
 * - ui_draw_border_style: dispatches NONE/SINGLE/DOUBLE/BOLD/ROUNDED/DASHED
 * - ui_draw_rect_outline: rect outline via draw_rect or h/vline fallback
 *
 * Uses a mock UiDrawOps that records calls into a log buffer.
 */

#include "unity.h"
#include <string.h>
#include <stdio.h>
#include "ui_border.h"

/* ================================================================== */
/* Mock draw ops — record calls as "type:x,y,w,h,c" strings           */
/* ================================================================== */

enum { LOG_MAX = 64, LOG_ENTRY_SZ = 48 };

typedef struct {
    char entries[LOG_MAX][LOG_ENTRY_SZ];
    int count;
} DrawLog;

static DrawLog s_log;

static void log_reset(void) {
    memset(&s_log, 0, sizeof(s_log));
}

static void mock_hline(void *ctx, int x, int y, int w, uint8_t c)
{
    (void)ctx;
    if (s_log.count < LOG_MAX) {
        snprintf(s_log.entries[s_log.count], LOG_ENTRY_SZ,
                 "H:%d,%d,%d,%d", x, y, w, (int)c);
        s_log.count++;
    }
}

static void mock_vline(void *ctx, int x, int y, int h, uint8_t c)
{
    (void)ctx;
    if (s_log.count < LOG_MAX) {
        snprintf(s_log.entries[s_log.count], LOG_ENTRY_SZ,
                 "V:%d,%d,%d,%d", x, y, h, (int)c);
        s_log.count++;
    }
}

static void mock_rect(void *ctx, int x, int y, int w, int h, uint8_t c)
{
    (void)ctx;
    if (s_log.count < LOG_MAX) {
        snprintf(s_log.entries[s_log.count], LOG_ENTRY_SZ,
                 "R:%d,%d,%d,%d,%d", x, y, w, h, (int)c);
        s_log.count++;
    }
}

static void mock_fill(void *ctx, int x, int y, int w, int h, uint8_t c)
{
    (void)ctx;
    if (s_log.count < LOG_MAX) {
        snprintf(s_log.entries[s_log.count], LOG_ENTRY_SZ,
                 "F:%d,%d,%d,%d,%d", x, y, w, h, (int)c);
        s_log.count++;
    }
}

/* Ops with draw_rect available */
static UiDrawOps ops_with_rect(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_hline = mock_hline;
    ops.draw_vline = mock_vline;
    ops.draw_rect = mock_rect;
    return ops;
}

/* Ops with only h/vline (no draw_rect) — tests fallback path */
static UiDrawOps ops_hv_only(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_hline = mock_hline;
    ops.draw_vline = mock_vline;
    return ops;
}

void setUp(void) { log_reset(); }
void tearDown(void) {}

/* ================================================================== */
/* ui_draw_rect_outline                                                */
/* ================================================================== */

void test_rect_outline_uses_draw_rect(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_rect_outline(&ops, 5, 10, 20, 15, 12);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:5,10,20,15,12", s_log.entries[0]);
}

void test_rect_outline_fallback_hv(void)
{
    UiDrawOps ops = ops_hv_only();
    ui_draw_rect_outline(&ops, 0, 0, 10, 8, 7);
    /* 2 hlines (top + bottom) + 2 vlines (left + right) */
    TEST_ASSERT_EQUAL_INT(4, s_log.count);
    TEST_ASSERT_EQUAL_STRING("H:0,0,10,7", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("H:0,7,10,7", s_log.entries[1]);
    TEST_ASSERT_EQUAL_STRING("V:0,0,8,7", s_log.entries[2]);
    TEST_ASSERT_EQUAL_STRING("V:9,0,8,7", s_log.entries[3]);
}

void test_rect_outline_zero_size_no_draw(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_rect_outline(&ops, 0, 0, 0, 10, 5);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);

    ui_draw_rect_outline(&ops, 0, 0, 10, 0, 5);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

/* ================================================================== */
/* NONE                                                                */
/* ================================================================== */

void test_border_none_no_draw(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 50, 30, UI_BORDER_NONE, 10);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

/* ================================================================== */
/* SINGLE                                                              */
/* ================================================================== */

void test_border_single_one_rect(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 5, 10, 40, 20, UI_BORDER_SINGLE, 12);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:5,10,40,20,12", s_log.entries[0]);
}

/* ================================================================== */
/* DOUBLE                                                              */
/* ================================================================== */

void test_border_double_large(void)
{
    /* w>4, h>4 → outer + inner at offset 2 */
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 20, 20, UI_BORDER_DOUBLE, 8);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:0,0,20,20,8", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("R:2,2,16,16,8", s_log.entries[1]);
}

void test_border_double_small(void)
{
    /* w=4, h=4 → outer + inner at offset 1 (fallback) */
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 4, 4, UI_BORDER_DOUBLE, 8);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:0,0,4,4,8", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("R:1,1,2,2,8", s_log.entries[1]);
}

void test_border_double_tiny(void)
{
    /* w=2, h=2 → only outer, no inner */
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 2, 2, UI_BORDER_DOUBLE, 8);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
}

/* ================================================================== */
/* BOLD                                                                */
/* ================================================================== */

void test_border_bold_large(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 10, 10, UI_BORDER_BOLD, 15);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:0,0,10,10,15", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("R:1,1,8,8,15", s_log.entries[1]);
}

void test_border_bold_tiny(void)
{
    /* w=2, h=2 → only outer */
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 2, 2, UI_BORDER_BOLD, 15);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
}

/* ================================================================== */
/* ROUNDED                                                             */
/* ================================================================== */

void test_border_rounded(void)
{
    UiDrawOps ops = ops_hv_only();
    ui_draw_border_style(&ops, 0, 0, 10, 8, UI_BORDER_ROUNDED, 5);
    /* hlines: top(x+1, w-2) + bottom(x+1, w-2) = 2 */
    /* vlines: left(y+1, h-2) + right(y+1, h-2) = 2 */
    TEST_ASSERT_EQUAL_INT(4, s_log.count);
    TEST_ASSERT_EQUAL_STRING("H:1,0,8,5", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("H:1,7,8,5", s_log.entries[1]);
    TEST_ASSERT_EQUAL_STRING("V:0,1,6,5", s_log.entries[2]);
    TEST_ASSERT_EQUAL_STRING("V:9,1,6,5", s_log.entries[3]);
}

void test_border_rounded_tiny_w2(void)
{
    /* w=2 → no hlines, but still vlines if h>2 */
    UiDrawOps ops = ops_hv_only();
    ui_draw_border_style(&ops, 0, 0, 2, 6, UI_BORDER_ROUNDED, 5);
    /* No hlines (w ≤ 2), 2 vlines */
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_STRING("V:0,1,4,5", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("V:1,1,4,5", s_log.entries[1]);
}

void test_border_rounded_tiny_h2(void)
{
    /* h=2 → no vlines, but hlines if w>2 */
    UiDrawOps ops = ops_hv_only();
    ui_draw_border_style(&ops, 0, 0, 8, 2, UI_BORDER_ROUNDED, 5);
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_STRING("H:1,0,6,5", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("H:1,1,6,5", s_log.entries[1]);
}

/* ================================================================== */
/* DASHED                                                              */
/* ================================================================== */

void test_border_dashed_hlines(void)
{
    /* 12px wide → segments at x=0(2px), skip 2, x=4(2px), skip 2, x=8(2px), x=12 is past end */
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_hline = mock_hline;
    /* No vline — only test h segments */

    ui_draw_border_style(&ops, 0, 0, 12, 6, UI_BORDER_DASHED, 3);
    /* 3 seg positions × 2 (top+bottom) = 6 hline calls */
    TEST_ASSERT_EQUAL_INT(6, s_log.count);
    /* top: x=0, x=4, x=8 */
    TEST_ASSERT_EQUAL_STRING("H:0,0,2,3", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("H:0,5,2,3", s_log.entries[1]);
    TEST_ASSERT_EQUAL_STRING("H:4,0,2,3", s_log.entries[2]);
    TEST_ASSERT_EQUAL_STRING("H:4,5,2,3", s_log.entries[3]);
    TEST_ASSERT_EQUAL_STRING("H:8,0,2,3", s_log.entries[4]);
    TEST_ASSERT_EQUAL_STRING("H:8,5,2,3", s_log.entries[5]);
}

void test_border_dashed_vlines(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_vline = mock_vline;

    ui_draw_border_style(&ops, 0, 0, 8, 10, UI_BORDER_DASHED, 4);
    /* y segments: 0(2), 4(2), 8(2 clamped to 2) → 3 positions × 2 sides = 6 */
    /* Actually: y=0 seg=2, y=4 seg=2, y=8 seg=min(2, 10-8)=2 → 3 × 2 = 6 */
    TEST_ASSERT_EQUAL_INT(6, s_log.count);
    TEST_ASSERT_EQUAL_STRING("V:0,0,2,4", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("V:7,0,2,4", s_log.entries[1]);
}

void test_border_dashed_clamp_segment(void)
{
    /* width=3 → first segment 2px (x=0..1), no more segments */
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_hline = mock_hline;

    ui_draw_border_style(&ops, 0, 0, 3, 4, UI_BORDER_DASHED, 1);
    /* 1 position × 2 (top+bottom) = 2 hline calls */
    TEST_ASSERT_EQUAL_INT(2, s_log.count);
    TEST_ASSERT_EQUAL_STRING("H:0,0,2,1", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("H:0,3,2,1", s_log.entries[1]);
}

/* ================================================================== */
/* Edge cases                                                          */
/* ================================================================== */

void test_border_zero_size_no_draw(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 0, 10, UI_BORDER_SINGLE, 5);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);

    ui_draw_border_style(&ops, 0, 0, 10, 0, UI_BORDER_SINGLE, 5);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_border_negative_size_no_draw(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, -5, 10, UI_BORDER_SINGLE, 5);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_border_null_ops_no_crash(void)
{
    ui_draw_border_style(NULL, 0, 0, 50, 30, UI_BORDER_SINGLE, 10);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_border_unknown_style_fallback(void)
{
    /* Unknown style falls back to single rect */
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 20, 10, 99, 7);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:0,0,20,10,7", s_log.entries[0]);
}

void test_border_1x1(void)
{
    UiDrawOps ops = ops_with_rect();
    ui_draw_border_style(&ops, 0, 0, 1, 1, UI_BORDER_SINGLE, 15);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("R:0,0,1,1,15", s_log.entries[0]);
}

/* ================================================================== */
/* ui_fill_rect                                                        */
/* ================================================================== */

void test_fill_rect_dispatches_to_fill_rect(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.fill_rect = mock_fill;
    ui_fill_rect(&ops, 3, 5, 10, 8, 9);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_STRING("F:3,5,10,8,9", s_log.entries[0]);
}

void test_fill_rect_fallback_hline_loop(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_hline = mock_hline;
    /* fill_rect is NULL → falls back to hline per row */
    ui_fill_rect(&ops, 2, 10, 6, 3, 4);
    TEST_ASSERT_EQUAL_INT(3, s_log.count); /* one hline per row */
    TEST_ASSERT_EQUAL_STRING("H:2,10,6,4", s_log.entries[0]);
    TEST_ASSERT_EQUAL_STRING("H:2,11,6,4", s_log.entries[1]);
    TEST_ASSERT_EQUAL_STRING("H:2,12,6,4", s_log.entries[2]);
}

void test_fill_rect_zero_size_no_draw(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.fill_rect = mock_fill;
    ops.draw_hline = mock_hline;
    ui_fill_rect(&ops, 0, 0, 0, 5, 1);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
    ui_fill_rect(&ops, 0, 0, 5, 0, 1);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_border_rounded_both_wh_le2(void)
{
    /* ROUNDED with w=2, h=2 → both guards hit: no hlines (w<=2) and no vlines (h<=2) */
    UiDrawOps ops = ops_hv_only();
    ui_draw_border_style(&ops, 0, 0, 2, 2, UI_BORDER_ROUNDED, 5);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_border_dashed_no_callbacks_no_crash(void)
{
    /* DASHED with neither draw_hline nor draw_vline → 0 calls, no crash */
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ui_draw_border_style(&ops, 0, 0, 20, 10, UI_BORDER_DASHED, 7);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}
