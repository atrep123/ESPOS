#include "unity.h"

#ifdef ESP_PLATFORM

void test_chart_renders_bars_and_axes(void);
void test_chart_tiny_no_crash(void);
void test_chart_zero_range(void);
void test_chart_invisible_skipped(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_chart_renders_bars_and_axes);
    RUN_TEST(test_chart_tiny_no_crash);
    RUN_TEST(test_chart_zero_range);
    RUN_TEST(test_chart_invisible_skipped);
    UNITY_END();
}

#else

void test_chart_renders_bars_and_axes(void);
void test_chart_shows_label(void);
void test_chart_no_label(void);
void test_chart_bars_nonneg_dims(void);
void test_chart_zero_value(void);
void test_chart_max_value(void);
void test_chart_negative_range(void);
void test_chart_large_range_no_overflow(void);
void test_chart_zero_range(void);
void test_chart_inverted_range(void);
void test_chart_tiny_no_crash(void);
void test_chart_small_inner_returns_early(void);
void test_chart_narrow_single_bar(void);
void test_chart_wide_renders_bars(void);
void test_chart_no_border(void);
void test_chart_border_styles(void);
void test_chart_disabled_still_renders(void);
void test_chart_invisible_skipped(void);
void test_chart_value_above_max(void);
void test_chart_value_below_min(void);
void test_chart_empty_label_string(void);
void test_chart_large_offset_coords(void);
void test_chart_no_border_no_rect(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_chart_renders_bars_and_axes);
    RUN_TEST(test_chart_shows_label);
    RUN_TEST(test_chart_no_label);
    RUN_TEST(test_chart_bars_nonneg_dims);
    RUN_TEST(test_chart_zero_value);
    RUN_TEST(test_chart_max_value);
    RUN_TEST(test_chart_negative_range);
    RUN_TEST(test_chart_large_range_no_overflow);
    RUN_TEST(test_chart_zero_range);
    RUN_TEST(test_chart_inverted_range);
    RUN_TEST(test_chart_tiny_no_crash);
    RUN_TEST(test_chart_small_inner_returns_early);
    RUN_TEST(test_chart_narrow_single_bar);
    RUN_TEST(test_chart_wide_renders_bars);
    RUN_TEST(test_chart_no_border);
    RUN_TEST(test_chart_border_styles);
    RUN_TEST(test_chart_disabled_still_renders);
    RUN_TEST(test_chart_invisible_skipped);
    RUN_TEST(test_chart_value_above_max);
    RUN_TEST(test_chart_value_below_min);
    RUN_TEST(test_chart_empty_label_string);
    RUN_TEST(test_chart_large_offset_coords);
    RUN_TEST(test_chart_no_border_no_rect);
    return UNITY_END();
}

#endif
