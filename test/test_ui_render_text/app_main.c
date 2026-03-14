/* Unity test runner for test_ui_render_text */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* gray4_add */
extern void test_gray4_add_normal(void);
extern void test_gray4_add_clamp_high(void);
extern void test_gray4_add_clamp_low(void);
extern void test_gray4_add_zero_delta(void);
extern void test_gray4_add_max_input(void);
extern void test_gray4_add_negative_to_zero(void);
extern void test_gray4_add_masks_upper_bits(void);

/* flatten_one_line */
extern void test_flatten_simple(void);
extern void test_flatten_newlines(void);
extern void test_flatten_tabs(void);
extern void test_flatten_multi_spaces(void);
extern void test_flatten_leading_space(void);
extern void test_flatten_trailing_space(void);
extern void test_flatten_null_in(void);
extern void test_flatten_empty_in(void);
extern void test_flatten_null_out(void);
extern void test_flatten_zero_cap(void);
extern void test_flatten_mixed_whitespace(void);

/* fit_line_buf */
extern void test_fit_text_fits(void);
extern void test_fit_exact_length(void);
extern void test_fit_truncate_with_ellipsis(void);
extern void test_fit_truncate_without_ellipsis(void);
extern void test_fit_max_chars_le_3_no_ellipsis(void);
extern void test_fit_null_text(void);
extern void test_fit_empty_text(void);
extern void test_fit_null_out(void);
extern void test_fit_zero_max(void);

/* wrap_next_line */
extern void test_wrap_single_word(void);
extern void test_wrap_two_words_fit(void);
extern void test_wrap_two_words_break(void);
extern void test_wrap_long_word_forced_break(void);
extern void test_wrap_newline_break(void);
extern void test_wrap_empty_text(void);
extern void test_wrap_null_pp(void);
extern void test_wrap_leading_spaces(void);

/* count_wrap_lines */
extern void test_count_single_line(void);
extern void test_count_multi_lines(void);
extern void test_count_truncated(void);
extern void test_count_empty_text(void);
extern void test_count_null_text(void);
extern void test_count_null_truncated_ptr(void);
extern void test_count_exact_fit(void);

/* round-8 additions */
extern void test_gray4_add_large_positive_clamp(void);
extern void test_flatten_cr_newline(void);
extern void test_fit_negative_max_chars(void);
extern void test_wrap_consecutive_newlines(void);
extern void test_count_max_lines_one_truncated(void);

int main(void)
{
    UNITY_BEGIN();

    /* gray4_add */
    RUN_TEST(test_gray4_add_normal);
    RUN_TEST(test_gray4_add_clamp_high);
    RUN_TEST(test_gray4_add_clamp_low);
    RUN_TEST(test_gray4_add_zero_delta);
    RUN_TEST(test_gray4_add_max_input);
    RUN_TEST(test_gray4_add_negative_to_zero);
    RUN_TEST(test_gray4_add_masks_upper_bits);

    /* flatten_one_line */
    RUN_TEST(test_flatten_simple);
    RUN_TEST(test_flatten_newlines);
    RUN_TEST(test_flatten_tabs);
    RUN_TEST(test_flatten_multi_spaces);
    RUN_TEST(test_flatten_leading_space);
    RUN_TEST(test_flatten_trailing_space);
    RUN_TEST(test_flatten_null_in);
    RUN_TEST(test_flatten_empty_in);
    RUN_TEST(test_flatten_null_out);
    RUN_TEST(test_flatten_zero_cap);
    RUN_TEST(test_flatten_mixed_whitespace);

    /* fit_line_buf */
    RUN_TEST(test_fit_text_fits);
    RUN_TEST(test_fit_exact_length);
    RUN_TEST(test_fit_truncate_with_ellipsis);
    RUN_TEST(test_fit_truncate_without_ellipsis);
    RUN_TEST(test_fit_max_chars_le_3_no_ellipsis);
    RUN_TEST(test_fit_null_text);
    RUN_TEST(test_fit_empty_text);
    RUN_TEST(test_fit_null_out);
    RUN_TEST(test_fit_zero_max);

    /* wrap_next_line */
    RUN_TEST(test_wrap_single_word);
    RUN_TEST(test_wrap_two_words_fit);
    RUN_TEST(test_wrap_two_words_break);
    RUN_TEST(test_wrap_long_word_forced_break);
    RUN_TEST(test_wrap_newline_break);
    RUN_TEST(test_wrap_empty_text);
    RUN_TEST(test_wrap_null_pp);
    RUN_TEST(test_wrap_leading_spaces);

    /* count_wrap_lines */
    RUN_TEST(test_count_single_line);
    RUN_TEST(test_count_multi_lines);
    RUN_TEST(test_count_truncated);
    RUN_TEST(test_count_empty_text);
    RUN_TEST(test_count_null_text);
    RUN_TEST(test_count_null_truncated_ptr);
    RUN_TEST(test_count_exact_fit);

    /* round-8 additions */
    RUN_TEST(test_gray4_add_large_positive_clamp);
    RUN_TEST(test_flatten_cr_newline);
    RUN_TEST(test_fit_negative_max_chars);
    RUN_TEST(test_wrap_consecutive_newlines);
    RUN_TEST(test_count_max_lines_one_truncated);

    return UNITY_END();
}
