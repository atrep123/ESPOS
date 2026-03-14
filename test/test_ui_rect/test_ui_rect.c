/*
 * Unit tests for pure rectangle geometry helpers (ui_rect.c):
 * - ui_rect_from_widget: widget → rect conversion
 * - ui_rect_center_x/y: center point calculation
 * - ui_rect_right/bottom: edge calculation
 * - ui_rect_overlap: 1-D interval overlap
 * - ui_rect_contains_point: point-in-rect test
 */

#include "unity.h"
#include <string.h>
#include "ui_rect.h"

void setUp(void) {}
void tearDown(void) {}

/* Helper: create a zeroed widget with position and size. */
static UiWidget make_widget(uint16_t x, uint16_t y, uint16_t w, uint16_t h)
{
    UiWidget ww;
    memset(&ww, 0, sizeof(ww));
    ww.type = UIW_BUTTON;
    ww.x = x;
    ww.y = y;
    ww.width = w;
    ww.height = h;
    return ww;
}

/* ================================================================== */
/* ui_rect_from_widget                                                 */
/* ================================================================== */

void test_rect_from_widget_basic(void)
{
    UiWidget w = make_widget(10, 20, 100, 50);
    UiRect r = ui_rect_from_widget(&w);
    TEST_ASSERT_EQUAL_INT(10, r.x);
    TEST_ASSERT_EQUAL_INT(20, r.y);
    TEST_ASSERT_EQUAL_INT(100, r.w);
    TEST_ASSERT_EQUAL_INT(50, r.h);
}

void test_rect_from_widget_null(void)
{
    UiRect r = ui_rect_from_widget(NULL);
    TEST_ASSERT_EQUAL_INT(0, r.x);
    TEST_ASSERT_EQUAL_INT(0, r.y);
    TEST_ASSERT_EQUAL_INT(0, r.w);
    TEST_ASSERT_EQUAL_INT(0, r.h);
}

void test_rect_from_widget_zero_size(void)
{
    UiWidget w = make_widget(5, 5, 0, 0);
    UiRect r = ui_rect_from_widget(&w);
    TEST_ASSERT_EQUAL_INT(5, r.x);
    TEST_ASSERT_EQUAL_INT(5, r.y);
    TEST_ASSERT_EQUAL_INT(0, r.w);
    TEST_ASSERT_EQUAL_INT(0, r.h);
}

/* ================================================================== */
/* ui_rect_center_x / ui_rect_center_y                                 */
/* ================================================================== */

void test_center_x_even(void)
{
    UiRect r = {10, 0, 20, 10};
    TEST_ASSERT_EQUAL_INT(20, ui_rect_center_x(r));
}

void test_center_x_odd(void)
{
    UiRect r = {10, 0, 21, 10};
    /* 10 + 21/2 = 10 + 10 = 20 (integer division floors) */
    TEST_ASSERT_EQUAL_INT(20, ui_rect_center_x(r));
}

void test_center_y_even(void)
{
    UiRect r = {0, 30, 10, 40};
    TEST_ASSERT_EQUAL_INT(50, ui_rect_center_y(r));
}

void test_center_y_zero_height(void)
{
    UiRect r = {0, 10, 10, 0};
    TEST_ASSERT_EQUAL_INT(10, ui_rect_center_y(r));
}

/* ================================================================== */
/* ui_rect_right / ui_rect_bottom                                      */
/* ================================================================== */

void test_right(void)
{
    UiRect r = {10, 0, 50, 10};
    TEST_ASSERT_EQUAL_INT(60, ui_rect_right(r));
}

void test_bottom(void)
{
    UiRect r = {0, 20, 10, 30};
    TEST_ASSERT_EQUAL_INT(50, ui_rect_bottom(r));
}

void test_right_zero_width(void)
{
    UiRect r = {15, 0, 0, 10};
    TEST_ASSERT_EQUAL_INT(15, ui_rect_right(r));
}

void test_bottom_zero_height(void)
{
    UiRect r = {0, 25, 10, 0};
    TEST_ASSERT_EQUAL_INT(25, ui_rect_bottom(r));
}

/* ================================================================== */
/* ui_rect_overlap                                                     */
/* ================================================================== */

void test_overlap_full(void)
{
    /* [10,30) and [10,30) → 20 */
    TEST_ASSERT_EQUAL_INT(20, ui_rect_overlap(10, 30, 10, 30));
}

void test_overlap_partial(void)
{
    /* [10,30) and [20,40) → overlap [20,30) = 10 */
    TEST_ASSERT_EQUAL_INT(10, ui_rect_overlap(10, 30, 20, 40));
}

void test_overlap_none_adjacent(void)
{
    /* [10,20) and [20,30) → 0 */
    TEST_ASSERT_EQUAL_INT(0, ui_rect_overlap(10, 20, 20, 30));
}

void test_overlap_none_gap(void)
{
    /* [10,20) and [25,35) → 0 */
    TEST_ASSERT_EQUAL_INT(0, ui_rect_overlap(10, 20, 25, 35));
}

void test_overlap_b_inside_a(void)
{
    /* [0,100) and [20,30) → 10 */
    TEST_ASSERT_EQUAL_INT(10, ui_rect_overlap(0, 100, 20, 30));
}

void test_overlap_reversed_order(void)
{
    /* [20,40) and [10,30) → 10 */
    TEST_ASSERT_EQUAL_INT(10, ui_rect_overlap(20, 40, 10, 30));
}

/* ================================================================== */
/* ui_rect_contains_point                                              */
/* ================================================================== */

void test_contains_inside(void)
{
    UiRect r = {10, 10, 20, 20};
    TEST_ASSERT_EQUAL_INT(1, ui_rect_contains_point(r, 15, 15));
}

void test_contains_top_left_corner(void)
{
    UiRect r = {10, 10, 20, 20};
    TEST_ASSERT_EQUAL_INT(1, ui_rect_contains_point(r, 10, 10));
}

void test_contains_right_edge_exclusive(void)
{
    UiRect r = {10, 10, 20, 20};
    /* right = 30, bottom = 30 — exclusive */
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 30, 15));
}

void test_contains_bottom_edge_exclusive(void)
{
    UiRect r = {10, 10, 20, 20};
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 15, 30));
}

void test_contains_outside_left(void)
{
    UiRect r = {10, 10, 20, 20};
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 5, 15));
}

void test_contains_outside_above(void)
{
    UiRect r = {10, 10, 20, 20};
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 15, 5));
}

void test_contains_zero_size_rect(void)
{
    UiRect r = {10, 10, 0, 0};
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 10, 10));
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_center_y_odd(void)
{
    UiRect r = {0, 10, 50, 7};
    /* integer division: 10 + 7/2 = 10 + 3 = 13 */
    TEST_ASSERT_EQUAL_INT(13, ui_rect_center_y(r));
}

void test_contains_just_inside_bottom_right(void)
{
    UiRect r = {10, 20, 30, 40};
    /* Just inside: (39, 59) — right=40, bottom=60 are exclusive */
    TEST_ASSERT_EQUAL_INT(1, ui_rect_contains_point(r, 39, 59));
    /* On the exclusive boundary */
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 40, 59));
    TEST_ASSERT_EQUAL_INT(0, ui_rect_contains_point(r, 39, 60));
}

void test_overlap_zero_length_interval(void)
{
    /* Degenerate zero-length interval [5,5) should return 0 against any range */
    TEST_ASSERT_EQUAL_INT(0, ui_rect_overlap(5, 5, 0, 10));
    TEST_ASSERT_EQUAL_INT(0, ui_rect_overlap(0, 10, 5, 5));
}

void test_overlap_negative_coords(void)
{
    /* Both intervals in negative space */
    int ov = ui_rect_overlap(-10, -2, -7, -1);
    /* [-10,-2) ∩ [-7,-1) = [-7,-2) = 5 */
    TEST_ASSERT_EQUAL_INT(5, ov);
}

void test_from_widget_large_uint16(void)
{
    /* Widget with uint16_t max values */
    UiWidget ww = make_widget(65535, 65535, 65535, 65535);
    UiRect r = ui_rect_from_widget(&ww);
    TEST_ASSERT_EQUAL_INT(65535, r.x);
    TEST_ASSERT_EQUAL_INT(65535, r.y);
    TEST_ASSERT_EQUAL_INT(65535, r.w);
    TEST_ASSERT_EQUAL_INT(65535, r.h);
    /* Derived values */
    TEST_ASSERT_EQUAL_INT(65535 + 65535, ui_rect_right(r));
    TEST_ASSERT_EQUAL_INT(65535 + 65535, ui_rect_bottom(r));
}
