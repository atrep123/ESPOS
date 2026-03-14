#include "unity.h"

#ifdef ESP_PLATFORM

void test_icon_text_fallback_renders_first_char(void);
void test_icon_null_text_renders_question_mark(void);
void test_icon_invisible_skipped(void);
void test_icon_tiny_no_text_fits(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_icon_text_fallback_renders_first_char);
    RUN_TEST(test_icon_null_text_renders_question_mark);
    RUN_TEST(test_icon_invisible_skipped);
    RUN_TEST(test_icon_tiny_no_text_fits);
    UNITY_END();
}

#else

void test_icon_text_fallback_renders_first_char(void);
void test_icon_null_text_renders_question_mark(void);
void test_icon_empty_text_renders_question_mark(void);
void test_icon_with_border_renders_bg_and_border(void);
void test_icon_no_border(void);
void test_icon_border_styles(void);
void test_icon_tiny_no_text_fits(void);
void test_icon_tall_enough_for_text(void);
void test_icon_zero_width(void);
void test_icon_zero_height(void);
void test_icon_invisible_skipped(void);
void test_icon_disabled_still_renders(void);
void test_icon_long_text_uses_first_char(void);
void test_icon_highlighted_renders(void);
void test_icon_custom_fg_bg(void);
void test_icon_at_offset_position(void);
void test_icon_no_border_no_rect(void);
void test_icon_single_char_text(void);
void test_icon_inverse_style_renders(void);
void test_icon_large_offset_no_crash(void);
void test_icon_whitespace_text_renders(void);
void test_icon_wide_narrow_aspect(void);
void test_icon_all_valign_options(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_icon_text_fallback_renders_first_char);
    RUN_TEST(test_icon_null_text_renders_question_mark);
    RUN_TEST(test_icon_empty_text_renders_question_mark);
    RUN_TEST(test_icon_with_border_renders_bg_and_border);
    RUN_TEST(test_icon_no_border);
    RUN_TEST(test_icon_border_styles);
    RUN_TEST(test_icon_tiny_no_text_fits);
    RUN_TEST(test_icon_tall_enough_for_text);
    RUN_TEST(test_icon_zero_width);
    RUN_TEST(test_icon_zero_height);
    RUN_TEST(test_icon_invisible_skipped);
    RUN_TEST(test_icon_disabled_still_renders);
    RUN_TEST(test_icon_long_text_uses_first_char);
    RUN_TEST(test_icon_highlighted_renders);
    RUN_TEST(test_icon_custom_fg_bg);
    RUN_TEST(test_icon_at_offset_position);
    RUN_TEST(test_icon_no_border_no_rect);
    RUN_TEST(test_icon_single_char_text);
    RUN_TEST(test_icon_inverse_style_renders);
    RUN_TEST(test_icon_large_offset_no_crash);
    RUN_TEST(test_icon_whitespace_text_renders);
    RUN_TEST(test_icon_wide_narrow_aspect);
    RUN_TEST(test_icon_all_valign_options);
    return UNITY_END();
}

#endif
