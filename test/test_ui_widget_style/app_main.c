/* Unity test runner for test_ui_widget_style */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* has_extended */
extern void test_has_extended_all_zero(void);
extern void test_has_extended_fg_set(void);
extern void test_has_extended_visible_set(void);
extern void test_has_extended_style_set(void);
extern void test_has_extended_null(void);

/* is_visible */
extern void test_visible_default_widget(void);
extern void test_visible_explicit_visible(void);
extern void test_visible_invisible(void);
extern void test_visible_null(void);

/* is_enabled */
extern void test_enabled_default_widget(void);
extern void test_enabled_explicit_enabled(void);
extern void test_enabled_disabled(void);
extern void test_enabled_null(void);

/* widget_colors */
extern void test_colors_default_widget(void);
extern void test_colors_custom_fg_bg(void);
extern void test_colors_inverse_style(void);
extern void test_colors_highlight_style(void);
extern void test_colors_disabled_dims(void);
extern void test_colors_border_muted_fill(void);
extern void test_colors_null_widget(void);
extern void test_colors_both_fg_bg_zero_uses_theme(void);
extern void test_colors_fg_zero_bg_nonzero(void);
extern void test_colors_inverse_plus_highlight(void);
extern void test_colors_1bpp_theme(void);

/* has_extended — additional fields */
extern void test_has_extended_bg_set(void);
extern void test_has_extended_border_style_set(void);
extern void test_has_extended_text_overflow_and_max_lines(void);

/* colors — combinatorial */
extern void test_colors_custom_fg_bg_inverse(void);
extern void test_colors_disabled_custom_colors(void);

int main(void)
{
    UNITY_BEGIN();

    /* has_extended */
    RUN_TEST(test_has_extended_all_zero);
    RUN_TEST(test_has_extended_fg_set);
    RUN_TEST(test_has_extended_visible_set);
    RUN_TEST(test_has_extended_style_set);
    RUN_TEST(test_has_extended_null);

    /* is_visible */
    RUN_TEST(test_visible_default_widget);
    RUN_TEST(test_visible_explicit_visible);
    RUN_TEST(test_visible_invisible);
    RUN_TEST(test_visible_null);

    /* is_enabled */
    RUN_TEST(test_enabled_default_widget);
    RUN_TEST(test_enabled_explicit_enabled);
    RUN_TEST(test_enabled_disabled);
    RUN_TEST(test_enabled_null);

    /* widget_colors */
    RUN_TEST(test_colors_default_widget);
    RUN_TEST(test_colors_custom_fg_bg);
    RUN_TEST(test_colors_inverse_style);
    RUN_TEST(test_colors_highlight_style);
    RUN_TEST(test_colors_disabled_dims);
    RUN_TEST(test_colors_border_muted_fill);
    RUN_TEST(test_colors_null_widget);
    RUN_TEST(test_colors_both_fg_bg_zero_uses_theme);
    RUN_TEST(test_colors_fg_zero_bg_nonzero);
    RUN_TEST(test_colors_inverse_plus_highlight);
    RUN_TEST(test_colors_1bpp_theme);

    /* has_extended — additional fields */
    RUN_TEST(test_has_extended_bg_set);
    RUN_TEST(test_has_extended_border_style_set);
    RUN_TEST(test_has_extended_text_overflow_and_max_lines);

    /* colors — combinatorial */
    RUN_TEST(test_colors_custom_fg_bg_inverse);
    RUN_TEST(test_colors_disabled_custom_colors);

    return UNITY_END();
}
