#include "unity.h"

#ifdef ESP_PLATFORM

/* ESP builds: minimal set (avoid pulling math.h overhead) */
void test_gauge_arc_renders_draw_calls(void);
void test_gauge_tiny_falls_back_to_bar(void);
void test_gauge_zero_range(void);
void test_gauge_invisible_skipped(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_gauge_arc_renders_draw_calls);
    RUN_TEST(test_gauge_tiny_falls_back_to_bar);
    RUN_TEST(test_gauge_zero_range);
    RUN_TEST(test_gauge_invisible_skipped);
    UNITY_END();
}

#else

/* Native builds: full test suite */
void test_gauge_arc_renders_draw_calls(void);
void test_gauge_arc_shows_value_text(void);
void test_gauge_arc_shows_label(void);
void test_gauge_arc_at_zero(void);
void test_gauge_arc_at_max(void);
void test_gauge_arc_no_label_no_text(void);
void test_gauge_arc_value_clamped_above_max(void);
void test_gauge_arc_value_clamped_below_min(void);
void test_gauge_arc_negative_range(void);
void test_gauge_compact_no_value_text(void);
void test_gauge_compact_renders_arc(void);
void test_gauge_compact_no_label_fits_better(void);
void test_gauge_tiny_falls_back_to_bar(void);
void test_gauge_tiny_with_label_stays_bar(void);
void test_gauge_bar_zero_value(void);
void test_gauge_bar_full_value(void);
void test_gauge_zero_range(void);
void test_gauge_inverted_range(void);
void test_gauge_large_range_no_overflow(void);
void test_gauge_minimal_inner_returns_early(void);
void test_gauge_no_border(void);
void test_gauge_border_styles(void);
void test_gauge_disabled_still_renders(void);
void test_gauge_invisible_skipped(void);
void test_gauge_wide_short_uses_bar(void);
void test_gauge_arc_threshold_boundary(void);
void test_gauge_arc_large_value_snprintf_no_crash(void);
void test_gauge_zero_width_no_crash(void);
void test_gauge_zero_height_no_crash(void);
void test_gauge_bar_mode_draws_label_text(void);
void test_gauge_compact_narrow_column(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_gauge_arc_renders_draw_calls);
    RUN_TEST(test_gauge_arc_shows_value_text);
    RUN_TEST(test_gauge_arc_shows_label);
    RUN_TEST(test_gauge_arc_at_zero);
    RUN_TEST(test_gauge_arc_at_max);
    RUN_TEST(test_gauge_arc_no_label_no_text);
    RUN_TEST(test_gauge_arc_value_clamped_above_max);
    RUN_TEST(test_gauge_arc_value_clamped_below_min);
    RUN_TEST(test_gauge_arc_negative_range);
    RUN_TEST(test_gauge_compact_no_value_text);
    RUN_TEST(test_gauge_compact_renders_arc);
    RUN_TEST(test_gauge_compact_no_label_fits_better);
    RUN_TEST(test_gauge_tiny_falls_back_to_bar);
    RUN_TEST(test_gauge_tiny_with_label_stays_bar);
    RUN_TEST(test_gauge_bar_zero_value);
    RUN_TEST(test_gauge_bar_full_value);
    RUN_TEST(test_gauge_zero_range);
    RUN_TEST(test_gauge_inverted_range);
    RUN_TEST(test_gauge_large_range_no_overflow);
    RUN_TEST(test_gauge_minimal_inner_returns_early);
    RUN_TEST(test_gauge_no_border);
    RUN_TEST(test_gauge_border_styles);
    RUN_TEST(test_gauge_disabled_still_renders);
    RUN_TEST(test_gauge_invisible_skipped);
    RUN_TEST(test_gauge_wide_short_uses_bar);
    RUN_TEST(test_gauge_arc_threshold_boundary);
    RUN_TEST(test_gauge_arc_large_value_snprintf_no_crash);
    RUN_TEST(test_gauge_zero_width_no_crash);
    RUN_TEST(test_gauge_zero_height_no_crash);
    RUN_TEST(test_gauge_bar_mode_draws_label_text);
    RUN_TEST(test_gauge_compact_narrow_column);
    return UNITY_END();
}

#endif
