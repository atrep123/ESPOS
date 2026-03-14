/* Unity test runner for test_ui_border */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* rect_outline */
extern void test_rect_outline_uses_draw_rect(void);
extern void test_rect_outline_fallback_hv(void);
extern void test_rect_outline_zero_size_no_draw(void);

/* NONE */
extern void test_border_none_no_draw(void);

/* SINGLE */
extern void test_border_single_one_rect(void);

/* DOUBLE */
extern void test_border_double_large(void);
extern void test_border_double_small(void);
extern void test_border_double_tiny(void);

/* BOLD */
extern void test_border_bold_large(void);
extern void test_border_bold_tiny(void);

/* ROUNDED */
extern void test_border_rounded(void);
extern void test_border_rounded_tiny_w2(void);
extern void test_border_rounded_tiny_h2(void);

/* DASHED */
extern void test_border_dashed_hlines(void);
extern void test_border_dashed_vlines(void);
extern void test_border_dashed_clamp_segment(void);

/* edge cases */
extern void test_border_zero_size_no_draw(void);
extern void test_border_negative_size_no_draw(void);
extern void test_border_null_ops_no_crash(void);
extern void test_border_unknown_style_fallback(void);
extern void test_border_1x1(void);

/* ui_fill_rect */
extern void test_fill_rect_dispatches_to_fill_rect(void);
extern void test_fill_rect_fallback_hline_loop(void);
extern void test_fill_rect_zero_size_no_draw(void);
extern void test_border_rounded_both_wh_le2(void);
extern void test_border_dashed_no_callbacks_no_crash(void);

int main(void)
{
    UNITY_BEGIN();

    /* rect_outline */
    RUN_TEST(test_rect_outline_uses_draw_rect);
    RUN_TEST(test_rect_outline_fallback_hv);
    RUN_TEST(test_rect_outline_zero_size_no_draw);

    /* NONE */
    RUN_TEST(test_border_none_no_draw);

    /* SINGLE */
    RUN_TEST(test_border_single_one_rect);

    /* DOUBLE */
    RUN_TEST(test_border_double_large);
    RUN_TEST(test_border_double_small);
    RUN_TEST(test_border_double_tiny);

    /* BOLD */
    RUN_TEST(test_border_bold_large);
    RUN_TEST(test_border_bold_tiny);

    /* ROUNDED */
    RUN_TEST(test_border_rounded);
    RUN_TEST(test_border_rounded_tiny_w2);
    RUN_TEST(test_border_rounded_tiny_h2);

    /* DASHED */
    RUN_TEST(test_border_dashed_hlines);
    RUN_TEST(test_border_dashed_vlines);
    RUN_TEST(test_border_dashed_clamp_segment);

    /* edge cases */
    RUN_TEST(test_border_zero_size_no_draw);
    RUN_TEST(test_border_negative_size_no_draw);
    RUN_TEST(test_border_null_ops_no_crash);
    RUN_TEST(test_border_unknown_style_fallback);
    RUN_TEST(test_border_1x1);

    /* ui_fill_rect */
    RUN_TEST(test_fill_rect_dispatches_to_fill_rect);
    RUN_TEST(test_fill_rect_fallback_hline_loop);
    RUN_TEST(test_fill_rect_zero_size_no_draw);
    RUN_TEST(test_border_rounded_both_wh_le2);
    RUN_TEST(test_border_dashed_no_callbacks_no_crash);

    return UNITY_END();
}
