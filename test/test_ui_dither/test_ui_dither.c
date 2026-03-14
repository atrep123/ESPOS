/*
 * Unit tests for dithering primitives (ui_dither.c):
 * - ui_bayer4: threshold matrix values
 * - ui_draw_pixel: single pixel via draw_hline
 * - ui_dither_pixel: Bayer threshold selection
 * - ui_dither_fill_h: horizontal gradient fill
 * - ui_dither_fill_v: vertical gradient fill
 *
 * Uses mock UiDrawOps that records draw_hline calls.
 */

#include "unity.h"
#include <string.h>
#include <stdio.h>
#include "ui_dither.h"

/* ================================================================== */
/* Mock draw ops — record hline(x, y, w, color) calls                  */
/* ================================================================== */

enum { LOG_MAX = 2048, LOG_ENTRY_SZ = 32 };

typedef struct {
    int x, y, w;
    uint8_t c;
} HlineCall;

typedef struct {
    HlineCall entries[LOG_MAX];
    int count;
} DrawLog;

static DrawLog s_log;

static void log_reset(void)
{
    memset(&s_log, 0, sizeof(s_log));
}

static void mock_hline(void *ctx, int x, int y, int w, uint8_t c)
{
    (void)ctx;
    if (s_log.count < LOG_MAX) {
        HlineCall *e = &s_log.entries[s_log.count];
        e->x = x;
        e->y = y;
        e->w = w;
        e->c = c;
        s_log.count++;
    }
}

static UiDrawOps make_ops(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.draw_hline = mock_hline;
    return ops;
}

void setUp(void) { log_reset(); }
void tearDown(void) {}

/* ================================================================== */
/* ui_bayer4 — matrix sanity                                           */
/* ================================================================== */

void test_bayer4_all_values_in_range(void)
{
    int seen[16];
    memset(seen, 0, sizeof(seen));
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            uint8_t v = ui_bayer4[r][c];
            TEST_ASSERT_LESS_THAN(16, v);
            seen[v]++;
        }
    }
    /* Each value 0..15 appears exactly once */
    for (int i = 0; i < 16; ++i) {
        TEST_ASSERT_EQUAL_INT(1, seen[i]);
    }
}

void test_bayer4_corner_values(void)
{
    TEST_ASSERT_EQUAL_UINT8(0, ui_bayer4[0][0]);
    TEST_ASSERT_EQUAL_UINT8(10, ui_bayer4[0][3]);
    TEST_ASSERT_EQUAL_UINT8(12, ui_bayer4[1][0]);
    TEST_ASSERT_EQUAL_UINT8(5, ui_bayer4[3][3]);
}

/* ================================================================== */
/* ui_draw_pixel                                                       */
/* ================================================================== */

void test_pixel_single_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_draw_pixel(&ops, 10, 20, 7);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_INT(10, s_log.entries[0].x);
    TEST_ASSERT_EQUAL_INT(20, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(1, s_log.entries[0].w);
    TEST_ASSERT_EQUAL_UINT8(7, s_log.entries[0].c);
}

void test_pixel_no_hline_no_crash(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    /* draw_hline is NULL — should not crash */
    ui_draw_pixel(&ops, 0, 0, 15);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

/* ================================================================== */
/* ui_dither_pixel                                                     */
/* ================================================================== */

void test_dither_pixel_ratio_16_always_hi(void)
{
    UiDrawOps ops = make_ops();
    /* ratio=16 > all thresholds (max 15) → always hi */
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 4; ++x) {
            ui_dither_pixel(&ops, x, y, 15, 3, 16);
        }
    }
    TEST_ASSERT_EQUAL_INT(16, s_log.count);
    for (int i = 0; i < 16; ++i) {
        TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[i].c);
    }
}

void test_dither_pixel_ratio_0_always_lo(void)
{
    UiDrawOps ops = make_ops();
    /* ratio=0 <= all thresholds (min 0) → always lo */
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 4; ++x) {
            ui_dither_pixel(&ops, x, y, 15, 3, 0);
        }
    }
    TEST_ASSERT_EQUAL_INT(16, s_log.count);
    for (int i = 0; i < 16; ++i) {
        TEST_ASSERT_EQUAL_UINT8(3, s_log.entries[i].c);
    }
}

void test_dither_pixel_ratio_8_half_pattern(void)
{
    UiDrawOps ops = make_ops();
    /* ratio=8: pixels where bayer4[y&3][x&3] < 8 get hi, else lo */
    int hi_count = 0, lo_count = 0;
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 4; ++x) {
            ui_dither_pixel(&ops, x, y, 10, 5, 8);
        }
    }
    for (int i = 0; i < 16; ++i) {
        if (s_log.entries[i].c == 10) hi_count++;
        else if (s_log.entries[i].c == 5) lo_count++;
    }
    /* 8 values are 0..7, 8 values are 8..15 → 8 hi, 8 lo */
    TEST_ASSERT_EQUAL_INT(8, hi_count);
    TEST_ASSERT_EQUAL_INT(8, lo_count);
}

void test_dither_pixel_wraps_coords(void)
{
    UiDrawOps ops = make_ops();
    /* Coordinates larger than 3 are masked with & 3 */
    ui_dither_pixel(&ops, 4, 4, 15, 3, 16);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    /* (4&3,4&3) = (0,0) → threshold=0, ratio=16 > 0 → hi=15 */
    TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[0].c);
}

void test_dither_pixel_ratio_1_single_pixel(void)
{
    UiDrawOps ops = make_ops();
    /* ratio=1: only threshold=0 yields hi (at bayer4[0][0]) */
    ui_dither_pixel(&ops, 0, 0, 15, 3, 1);
    TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[0].c);
    log_reset();
    /* bayer4[0][1] = 8 → ratio=1 <= 8 → lo */
    ui_dither_pixel(&ops, 1, 0, 15, 3, 1);
    TEST_ASSERT_EQUAL_UINT8(3, s_log.entries[0].c);
}

/* ================================================================== */
/* ui_dither_fill_h — horizontal gradient                              */
/* ================================================================== */

void test_fill_h_zero_size_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_h(&ops, 0, 0, 0, 10, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
    ui_dither_fill_h(&ops, 0, 0, 10, 0, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_fill_h_negative_size_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_h(&ops, 0, 0, -5, 10, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
    ui_dither_fill_h(&ops, 0, 0, 10, -5, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_fill_h_1x1_draws_single_pixel(void)
{
    UiDrawOps ops = make_ops();
    /* w=1: ratio is 16 (always hi) */
    ui_dither_fill_h(&ops, 5, 10, 1, 1, 15, 3);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[0].c);
    TEST_ASSERT_EQUAL_INT(5, s_log.entries[0].x);
    TEST_ASSERT_EQUAL_INT(10, s_log.entries[0].y);
}

void test_fill_h_pixel_count(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_h(&ops, 0, 0, 8, 4, 15, 3);
    TEST_ASSERT_EQUAL_INT(32, s_log.count); /* 8 * 4 */
}

void test_fill_h_left_column_all_lo(void)
{
    UiDrawOps ops = make_ops();
    /* w=17: col=0 → ratio=0 → all lo for first column */
    ui_dither_fill_h(&ops, 0, 0, 17, 4, 15, 3);
    /* First 4 entries are col=0, rows 0..3 */
    for (int i = 0; i < 4; ++i) {
        TEST_ASSERT_EQUAL_UINT8(3, s_log.entries[i].c);
    }
}

void test_fill_h_right_column_all_hi(void)
{
    UiDrawOps ops = make_ops();
    /* w=17: col=16 → ratio=16 → all hi for last column */
    ui_dither_fill_h(&ops, 0, 0, 17, 4, 15, 3);
    /* Last 4 entries are col=16, rows 0..3 */
    int start = s_log.count - 4;
    for (int i = start; i < s_log.count; ++i) {
        TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[i].c);
    }
}

void test_fill_h_gradient_monotonic(void)
{
    UiDrawOps ops = make_ops();
    /* 17 cols, 4 rows → ratio steps 0,1,2,...,16 */
    ui_dither_fill_h(&ops, 0, 0, 17, 4, 15, 3);
    /* Left half should have fewer hi pixels than right half */
    int left_hi = 0, right_hi = 0;
    for (int col = 0; col < 17; ++col) {
        for (int row = 0; row < 4; ++row) {
            int idx = col * 4 + row;
            if (s_log.entries[idx].c == 15) {
                if (col < 8) left_hi++;
                else right_hi++;
            }
        }
    }
    TEST_ASSERT_LESS_THAN(right_hi, left_hi);
}

/* ================================================================== */
/* ui_dither_fill_v — vertical gradient                                */
/* ================================================================== */

void test_fill_v_zero_size_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_v(&ops, 0, 0, 0, 10, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
    ui_dither_fill_v(&ops, 0, 0, 10, 0, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_fill_v_1x1_draws_single_pixel(void)
{
    UiDrawOps ops = make_ops();
    /* h=1: ratio is 16 (always hi) */
    ui_dither_fill_v(&ops, 5, 10, 1, 1, 15, 3);
    TEST_ASSERT_EQUAL_INT(1, s_log.count);
    TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[0].c);
}

void test_fill_v_pixel_count(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_v(&ops, 0, 0, 4, 8, 15, 3);
    TEST_ASSERT_EQUAL_INT(32, s_log.count); /* 4 * 8 */
}

void test_fill_v_top_row_all_hi(void)
{
    UiDrawOps ops = make_ops();
    /* h=17: row=0 → ratio=16 → all hi for first row */
    ui_dither_fill_v(&ops, 0, 0, 4, 17, 15, 3);
    /* First 4 entries are row=0, cols 0..3 */
    for (int i = 0; i < 4; ++i) {
        TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[i].c);
    }
}

void test_fill_v_bottom_row_all_lo(void)
{
    UiDrawOps ops = make_ops();
    /* h=17: row=16 → ratio=0 → all lo for last row */
    ui_dither_fill_v(&ops, 0, 0, 4, 17, 15, 3);
    /* Last 4 entries are row=16, cols 0..3 */
    int start = s_log.count - 4;
    for (int i = start; i < s_log.count; ++i) {
        TEST_ASSERT_EQUAL_UINT8(3, s_log.entries[i].c);
    }
}

void test_fill_v_gradient_monotonic(void)
{
    UiDrawOps ops = make_ops();
    /* 4 cols, 17 rows → ratio steps 16,15,...,0 (decreasing) */
    ui_dither_fill_v(&ops, 0, 0, 4, 17, 15, 3);
    /* Top half should have more hi pixels than bottom half */
    int top_hi = 0, bot_hi = 0;
    for (int row = 0; row < 17; ++row) {
        for (int col = 0; col < 4; ++col) {
            int idx = row * 4 + col;
            if (s_log.entries[idx].c == 15) {
                if (row < 8) top_hi++;
                else bot_hi++;
            }
        }
    }
    TEST_ASSERT_GREATER_THAN(bot_hi, top_hi);
}

void test_fill_v_coords_offset(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_v(&ops, 20, 30, 2, 2, 15, 3);
    TEST_ASSERT_EQUAL_INT(4, s_log.count);
    /* row=0: (20,30) and (21,30) */
    TEST_ASSERT_EQUAL_INT(20, s_log.entries[0].x);
    TEST_ASSERT_EQUAL_INT(30, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(21, s_log.entries[1].x);
    TEST_ASSERT_EQUAL_INT(30, s_log.entries[1].y);
    /* row=1: (20,31) and (21,31) */
    TEST_ASSERT_EQUAL_INT(20, s_log.entries[2].x);
    TEST_ASSERT_EQUAL_INT(31, s_log.entries[2].y);
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_fill_v_negative_size_no_draw(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_v(&ops, 0, 0, 4, -1, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
    log_reset();
    ui_dither_fill_v(&ops, 0, 0, -1, 4, 15, 3);
    TEST_ASSERT_EQUAL_INT(0, s_log.count);
}

void test_dither_pixel_same_hi_lo(void)
{
    /* When hi == lo, every pixel should be the same regardless of ratio */
    UiDrawOps ops = make_ops();
    for (int ratio = 0; ratio <= 16; ++ratio) {
        ui_dither_pixel(&ops, ratio, 0, 7, 7, ratio);
    }
    TEST_ASSERT_EQUAL_INT(17, s_log.count);
    for (int i = 0; i < 17; ++i) {
        TEST_ASSERT_EQUAL_UINT8(7, s_log.entries[i].c);
    }
}

void test_fill_h_same_colors(void)
{
    /* Gradient with hi==lo: all pixels same color, no dithering variation */
    UiDrawOps ops = make_ops();
    ui_dither_fill_h(&ops, 0, 0, 8, 1, 10, 10);
    TEST_ASSERT_EQUAL_INT(8, s_log.count);
    for (int i = 0; i < 8; ++i) {
        TEST_ASSERT_EQUAL_UINT8(10, s_log.entries[i].c);
    }
}

void test_fill_h_coords_offset(void)
{
    UiDrawOps ops = make_ops();
    ui_dither_fill_h(&ops, 50, 60, 2, 2, 15, 3);
    TEST_ASSERT_EQUAL_INT(4, s_log.count);
    /* col=0: (50,60) and (50,61) */
    TEST_ASSERT_EQUAL_INT(50, s_log.entries[0].x);
    TEST_ASSERT_EQUAL_INT(60, s_log.entries[0].y);
    TEST_ASSERT_EQUAL_INT(50, s_log.entries[1].x);
    TEST_ASSERT_EQUAL_INT(61, s_log.entries[1].y);
    /* col=1: (51,60) and (51,61) */
    TEST_ASSERT_EQUAL_INT(51, s_log.entries[2].x);
    TEST_ASSERT_EQUAL_INT(60, s_log.entries[2].y);
}

void test_fill_h_width_1_all_hi(void)
{
    /* w=1: ratio formula yields 16 → all hi */
    UiDrawOps ops = make_ops();
    ui_dither_fill_h(&ops, 0, 0, 1, 4, 15, 3);
    TEST_ASSERT_EQUAL_INT(4, s_log.count);
    for (int i = 0; i < 4; ++i) {
        TEST_ASSERT_EQUAL_UINT8(15, s_log.entries[i].c);
    }
}
