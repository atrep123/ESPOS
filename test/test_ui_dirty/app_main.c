/* Unity test runner for test_ui_dirty */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* dirty_clear */
extern void test_dirty_clear_zeroes_all(void);
extern void test_dirty_clear_null_safe(void);

/* dirty_add */
extern void test_dirty_add_first_region(void);
extern void test_dirty_add_merge_expands(void);
extern void test_dirty_add_clamp_to_display(void);
extern void test_dirty_add_negative_origin(void);
extern void test_dirty_add_zero_size_ignored(void);
extern void test_dirty_add_negative_size_ignored(void);
extern void test_dirty_add_null_safe(void);
extern void test_dirty_add_fully_offscreen(void);
extern void test_dirty_add_merge_overlapping(void);
extern void test_dirty_add_small_display(void);

/* text_equals */
extern void test_text_equals_same(void);
extern void test_text_equals_different(void);
extern void test_text_equals_null_null(void);
extern void test_text_equals_null_empty(void);
extern void test_text_equals_empty_null(void);
extern void test_text_equals_null_nonempty(void);

/* toggle_checked */
extern void test_toggle_checkbox_unchecked_to_checked(void);
extern void test_toggle_checkbox_checked_to_unchecked(void);
extern void test_toggle_not_checkbox_noop(void);
extern void test_toggle_null_safe(void);
extern void test_toggle_double_flip(void);
extern void test_toggle_radiobutton_rejected(void);

/* clamp_value */
extern void test_clamp_increment(void);
extern void test_clamp_decrement(void);
extern void test_clamp_at_max(void);
extern void test_clamp_at_min(void);
extern void test_clamp_no_change_returns_zero(void);
extern void test_clamp_zero_delta(void);
extern void test_clamp_not_slider_rejected(void);
extern void test_clamp_gauge_accepted(void);
extern void test_clamp_progressbar_accepted(void);
extern void test_clamp_null_safe(void);
extern void test_clamp_negative_range(void);
extern void test_dirty_add_single_pixel(void);
extern void test_dirty_add_full_screen(void);
extern void test_text_equals_case_sensitive(void);
extern void test_clamp_both_bounds_equal(void);
extern void test_dirty_clear_then_add(void);

int main(void)
{
    UNITY_BEGIN();

    /* dirty_clear */
    RUN_TEST(test_dirty_clear_zeroes_all);
    RUN_TEST(test_dirty_clear_null_safe);

    /* dirty_add */
    RUN_TEST(test_dirty_add_first_region);
    RUN_TEST(test_dirty_add_merge_expands);
    RUN_TEST(test_dirty_add_clamp_to_display);
    RUN_TEST(test_dirty_add_negative_origin);
    RUN_TEST(test_dirty_add_zero_size_ignored);
    RUN_TEST(test_dirty_add_negative_size_ignored);
    RUN_TEST(test_dirty_add_null_safe);
    RUN_TEST(test_dirty_add_fully_offscreen);
    RUN_TEST(test_dirty_add_merge_overlapping);
    RUN_TEST(test_dirty_add_small_display);

    /* text_equals */
    RUN_TEST(test_text_equals_same);
    RUN_TEST(test_text_equals_different);
    RUN_TEST(test_text_equals_null_null);
    RUN_TEST(test_text_equals_null_empty);
    RUN_TEST(test_text_equals_empty_null);
    RUN_TEST(test_text_equals_null_nonempty);

    /* toggle_checked */
    RUN_TEST(test_toggle_checkbox_unchecked_to_checked);
    RUN_TEST(test_toggle_checkbox_checked_to_unchecked);
    RUN_TEST(test_toggle_not_checkbox_noop);
    RUN_TEST(test_toggle_null_safe);
    RUN_TEST(test_toggle_double_flip);
    RUN_TEST(test_toggle_radiobutton_rejected);

    /* clamp_value */
    RUN_TEST(test_clamp_increment);
    RUN_TEST(test_clamp_decrement);
    RUN_TEST(test_clamp_at_max);
    RUN_TEST(test_clamp_at_min);
    RUN_TEST(test_clamp_no_change_returns_zero);
    RUN_TEST(test_clamp_zero_delta);
    RUN_TEST(test_clamp_not_slider_rejected);
    RUN_TEST(test_clamp_gauge_accepted);
    RUN_TEST(test_clamp_progressbar_accepted);
    RUN_TEST(test_clamp_null_safe);
    RUN_TEST(test_clamp_negative_range);

    /* new edge-case tests */
    RUN_TEST(test_dirty_add_single_pixel);
    RUN_TEST(test_dirty_add_full_screen);
    RUN_TEST(test_text_equals_case_sensitive);
    RUN_TEST(test_clamp_both_bounds_equal);
    RUN_TEST(test_dirty_clear_then_add);

    return UNITY_END();
}
