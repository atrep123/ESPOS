/* Unity test runner for test_ui_rect */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* rect_from_widget */
extern void test_rect_from_widget_basic(void);
extern void test_rect_from_widget_null(void);
extern void test_rect_from_widget_zero_size(void);

/* center */
extern void test_center_x_even(void);
extern void test_center_x_odd(void);
extern void test_center_y_even(void);
extern void test_center_y_zero_height(void);

/* right / bottom */
extern void test_right(void);
extern void test_bottom(void);
extern void test_right_zero_width(void);
extern void test_bottom_zero_height(void);

/* overlap */
extern void test_overlap_full(void);
extern void test_overlap_partial(void);
extern void test_overlap_none_adjacent(void);
extern void test_overlap_none_gap(void);
extern void test_overlap_b_inside_a(void);
extern void test_overlap_reversed_order(void);

/* contains_point */
extern void test_contains_inside(void);
extern void test_contains_top_left_corner(void);
extern void test_contains_right_edge_exclusive(void);
extern void test_contains_bottom_edge_exclusive(void);
extern void test_contains_outside_left(void);
extern void test_contains_outside_above(void);
extern void test_contains_zero_size_rect(void);
extern void test_center_y_odd(void);
extern void test_contains_just_inside_bottom_right(void);
extern void test_overlap_zero_length_interval(void);
extern void test_overlap_negative_coords(void);
extern void test_from_widget_large_uint16(void);

int main(void)
{
    UNITY_BEGIN();

    /* rect_from_widget */
    RUN_TEST(test_rect_from_widget_basic);
    RUN_TEST(test_rect_from_widget_null);
    RUN_TEST(test_rect_from_widget_zero_size);

    /* center */
    RUN_TEST(test_center_x_even);
    RUN_TEST(test_center_x_odd);
    RUN_TEST(test_center_y_even);
    RUN_TEST(test_center_y_zero_height);

    /* right / bottom */
    RUN_TEST(test_right);
    RUN_TEST(test_bottom);
    RUN_TEST(test_right_zero_width);
    RUN_TEST(test_bottom_zero_height);

    /* overlap */
    RUN_TEST(test_overlap_full);
    RUN_TEST(test_overlap_partial);
    RUN_TEST(test_overlap_none_adjacent);
    RUN_TEST(test_overlap_none_gap);
    RUN_TEST(test_overlap_b_inside_a);
    RUN_TEST(test_overlap_reversed_order);

    /* contains_point */
    RUN_TEST(test_contains_inside);
    RUN_TEST(test_contains_top_left_corner);
    RUN_TEST(test_contains_right_edge_exclusive);
    RUN_TEST(test_contains_bottom_edge_exclusive);
    RUN_TEST(test_contains_outside_left);
    RUN_TEST(test_contains_outside_above);
    RUN_TEST(test_contains_zero_size_rect);

    /* new edge-case tests */
    RUN_TEST(test_center_y_odd);
    RUN_TEST(test_contains_just_inside_bottom_right);
    RUN_TEST(test_overlap_zero_length_interval);
    RUN_TEST(test_overlap_negative_coords);
    RUN_TEST(test_from_widget_large_uint16);

    return UNITY_END();
}
