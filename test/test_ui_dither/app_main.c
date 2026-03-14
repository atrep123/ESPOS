/* Unity test runner for test_ui_dither */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* bayer4 matrix */
extern void test_bayer4_all_values_in_range(void);
extern void test_bayer4_corner_values(void);

/* ui_draw_pixel */
extern void test_pixel_single_draw(void);
extern void test_pixel_no_hline_no_crash(void);

/* ui_dither_pixel */
extern void test_dither_pixel_ratio_16_always_hi(void);
extern void test_dither_pixel_ratio_0_always_lo(void);
extern void test_dither_pixel_ratio_8_half_pattern(void);
extern void test_dither_pixel_wraps_coords(void);
extern void test_dither_pixel_ratio_1_single_pixel(void);

/* ui_dither_fill_h */
extern void test_fill_h_zero_size_no_draw(void);
extern void test_fill_h_negative_size_no_draw(void);
extern void test_fill_h_1x1_draws_single_pixel(void);
extern void test_fill_h_pixel_count(void);
extern void test_fill_h_left_column_all_lo(void);
extern void test_fill_h_right_column_all_hi(void);
extern void test_fill_h_gradient_monotonic(void);

/* ui_dither_fill_v */
extern void test_fill_v_zero_size_no_draw(void);
extern void test_fill_v_1x1_draws_single_pixel(void);
extern void test_fill_v_pixel_count(void);
extern void test_fill_v_top_row_all_hi(void);
extern void test_fill_v_bottom_row_all_lo(void);
extern void test_fill_v_gradient_monotonic(void);
extern void test_fill_v_coords_offset(void);
extern void test_fill_v_negative_size_no_draw(void);
extern void test_dither_pixel_same_hi_lo(void);
extern void test_fill_h_same_colors(void);
extern void test_fill_h_coords_offset(void);
extern void test_fill_h_width_1_all_hi(void);

int main(void)
{
    UNITY_BEGIN();

    /* bayer4 */
    RUN_TEST(test_bayer4_all_values_in_range);
    RUN_TEST(test_bayer4_corner_values);

    /* ui_draw_pixel */
    RUN_TEST(test_pixel_single_draw);
    RUN_TEST(test_pixel_no_hline_no_crash);

    /* ui_dither_pixel */
    RUN_TEST(test_dither_pixel_ratio_16_always_hi);
    RUN_TEST(test_dither_pixel_ratio_0_always_lo);
    RUN_TEST(test_dither_pixel_ratio_8_half_pattern);
    RUN_TEST(test_dither_pixel_wraps_coords);
    RUN_TEST(test_dither_pixel_ratio_1_single_pixel);

    /* ui_dither_fill_h */
    RUN_TEST(test_fill_h_zero_size_no_draw);
    RUN_TEST(test_fill_h_negative_size_no_draw);
    RUN_TEST(test_fill_h_1x1_draws_single_pixel);
    RUN_TEST(test_fill_h_pixel_count);
    RUN_TEST(test_fill_h_left_column_all_lo);
    RUN_TEST(test_fill_h_right_column_all_hi);
    RUN_TEST(test_fill_h_gradient_monotonic);

    /* ui_dither_fill_v */
    RUN_TEST(test_fill_v_zero_size_no_draw);
    RUN_TEST(test_fill_v_1x1_draws_single_pixel);
    RUN_TEST(test_fill_v_pixel_count);
    RUN_TEST(test_fill_v_top_row_all_hi);
    RUN_TEST(test_fill_v_bottom_row_all_lo);
    RUN_TEST(test_fill_v_gradient_monotonic);
    RUN_TEST(test_fill_v_coords_offset);

    /* new edge-case tests */
    RUN_TEST(test_fill_v_negative_size_no_draw);
    RUN_TEST(test_dither_pixel_same_hi_lo);
    RUN_TEST(test_fill_h_same_colors);
    RUN_TEST(test_fill_h_coords_offset);
    RUN_TEST(test_fill_h_width_1_all_hi);

    return UNITY_END();
}
