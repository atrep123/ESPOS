/*
 * Unit tests for pure text-layout helpers (ui_render_text.c):
 * - ui_gray4_add: clamped 4-bit grayscale arithmetic
 * - ui_flatten_one_line: multiline → single-line normalization
 * - ui_fit_line_buf: truncation with/without ellipsis
 * - ui_wrap_next_line: word-wrap line extraction
 * - ui_count_wrap_lines: wrapped line counting + truncation detection
 */

#include "unity.h"
#include <string.h>
#include "ui_render_text.h"

void setUp(void) {}
void tearDown(void) {}

/* ================================================================== */
/* ui_gray4_add                                                        */
/* ================================================================== */

void test_gray4_add_normal(void)
{
    TEST_ASSERT_EQUAL_UINT8(7, ui_gray4_add(5, 2));
}

void test_gray4_add_clamp_high(void)
{
    TEST_ASSERT_EQUAL_UINT8(15, ui_gray4_add(14, 3));
}

void test_gray4_add_clamp_low(void)
{
    TEST_ASSERT_EQUAL_UINT8(0, ui_gray4_add(2, -5));
}

void test_gray4_add_zero_delta(void)
{
    TEST_ASSERT_EQUAL_UINT8(10, ui_gray4_add(10, 0));
}

void test_gray4_add_max_input(void)
{
    TEST_ASSERT_EQUAL_UINT8(15, ui_gray4_add(15, 0));
}

void test_gray4_add_negative_to_zero(void)
{
    TEST_ASSERT_EQUAL_UINT8(0, ui_gray4_add(0, -1));
}

void test_gray4_add_masks_upper_bits(void)
{
    /* Input 0xFF: lower nibble = 0x0F → 15 + 2 = 17 → clamped to 15 */
    TEST_ASSERT_EQUAL_UINT8(15, ui_gray4_add(0xFF, 2));
}

/* ================================================================== */
/* ui_flatten_one_line                                                 */
/* ================================================================== */

void test_flatten_simple(void)
{
    char out[64];
    ui_flatten_one_line("hello world", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello world", out);
}

void test_flatten_newlines(void)
{
    char out[64];
    ui_flatten_one_line("hello\nworld", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello world", out);
}

void test_flatten_tabs(void)
{
    char out[64];
    ui_flatten_one_line("a\tb", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("a b", out);
}

void test_flatten_multi_spaces(void)
{
    char out[64];
    ui_flatten_one_line("a   b", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("a b", out);
}

void test_flatten_leading_space(void)
{
    char out[64];
    ui_flatten_one_line("  hello", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello", out);
}

void test_flatten_trailing_space(void)
{
    char out[64];
    ui_flatten_one_line("hello  ", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello", out);
}

void test_flatten_null_in(void)
{
    char out[16] = "old";
    ui_flatten_one_line(NULL, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("", out);
}

void test_flatten_empty_in(void)
{
    char out[16] = "old";
    ui_flatten_one_line("", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("", out);
}

void test_flatten_null_out(void)
{
    /* Should not crash */
    ui_flatten_one_line("test", NULL, 16);
}

void test_flatten_zero_cap(void)
{
    char out[4] = "old";
    ui_flatten_one_line("test", out, 0);
    TEST_ASSERT_EQUAL_STRING("old", out);  /* unchanged */
}

void test_flatten_mixed_whitespace(void)
{
    char out[64];
    ui_flatten_one_line("a\n\n\tb  \r c", out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("a b c", out);
}

/* ================================================================== */
/* ui_fit_line_buf                                                     */
/* ================================================================== */

void test_fit_text_fits(void)
{
    char out[32];
    int n = ui_fit_line_buf("hello", 10, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello", out);
    TEST_ASSERT_EQUAL(5, n);
}

void test_fit_exact_length(void)
{
    char out[32];
    int n = ui_fit_line_buf("hello", 5, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello", out);
    TEST_ASSERT_EQUAL(5, n);
}

void test_fit_truncate_with_ellipsis(void)
{
    char out[32];
    int n = ui_fit_line_buf("hello world here", 10, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello w...", out);
    TEST_ASSERT_EQUAL(10, n);
}

void test_fit_truncate_without_ellipsis(void)
{
    char out[32];
    int n = ui_fit_line_buf("hello world", 5, 0, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("hello", out);
    TEST_ASSERT_EQUAL(5, n);
}

void test_fit_max_chars_le_3_no_ellipsis(void)
{
    char out[32];
    int n = ui_fit_line_buf("hello", 3, 1, out, sizeof(out));
    /* max_chars <= ell_len: just truncate, no ellipsis */
    TEST_ASSERT_EQUAL_STRING("hel", out);
    TEST_ASSERT_EQUAL(3, n);
}

void test_fit_null_text(void)
{
    char out[16] = "old";
    int n = ui_fit_line_buf(NULL, 10, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("", out);
    TEST_ASSERT_EQUAL(0, n);
}

void test_fit_empty_text(void)
{
    char out[16] = "old";
    int n = ui_fit_line_buf("", 10, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("", out);
    TEST_ASSERT_EQUAL(0, n);
}

void test_fit_null_out(void)
{
    int n = ui_fit_line_buf("hello", 10, 1, NULL, 32);
    TEST_ASSERT_EQUAL(0, n);
}

void test_fit_zero_max(void)
{
    char out[16] = "old";
    int n = ui_fit_line_buf("hello", 0, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("", out);
    TEST_ASSERT_EQUAL(0, n);
}

/* ================================================================== */
/* ui_wrap_next_line                                                   */
/* ================================================================== */

void test_wrap_single_word(void)
{
    const char *p = "hello";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL_STRING("hello", out);
    TEST_ASSERT_EQUAL(5, n);
    /* No more text */
    n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL(0, n);
}

void test_wrap_two_words_fit(void)
{
    const char *p = "hi there";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL_STRING("hi there", out);
    TEST_ASSERT_EQUAL(8, n);
}

void test_wrap_two_words_break(void)
{
    const char *p = "hello world";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 6);
    TEST_ASSERT_EQUAL_STRING("hello", out);
    TEST_ASSERT_EQUAL(5, n);
    n = ui_wrap_next_line(&p, out, sizeof(out), 6);
    TEST_ASSERT_EQUAL_STRING("world", out);
    TEST_ASSERT_EQUAL(5, n);
}

void test_wrap_long_word_forced_break(void)
{
    const char *p = "abcdefghij";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 5);
    TEST_ASSERT_EQUAL_STRING("abcde", out);
    TEST_ASSERT_EQUAL(5, n);
    n = ui_wrap_next_line(&p, out, sizeof(out), 5);
    TEST_ASSERT_EQUAL_STRING("fghij", out);
    TEST_ASSERT_EQUAL(5, n);
}

void test_wrap_newline_break(void)
{
    const char *p = "line1\nline2";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 20);
    TEST_ASSERT_EQUAL_STRING("line1", out);
    TEST_ASSERT_EQUAL(5, n);
    n = ui_wrap_next_line(&p, out, sizeof(out), 20);
    TEST_ASSERT_EQUAL_STRING("line2", out);
    TEST_ASSERT_EQUAL(5, n);
}

void test_wrap_empty_text(void)
{
    const char *p = "";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL(0, n);
}

void test_wrap_null_pp(void)
{
    char out[32];
    int n = ui_wrap_next_line(NULL, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL(0, n);
}

void test_wrap_leading_spaces(void)
{
    const char *p = "   hello";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL_STRING("hello", out);
    TEST_ASSERT_EQUAL(5, n);
}

/* ================================================================== */
/* ui_count_wrap_lines                                                 */
/* ================================================================== */

void test_count_single_line(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines("hello", 10, 5, &trunc);
    TEST_ASSERT_EQUAL(1, n);
    TEST_ASSERT_EQUAL(0, trunc);
}

void test_count_multi_lines(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines("hello world foo bar", 6, 10, &trunc);
    /* "hello" / "world" / "foo" / "bar" = 4 lines */
    TEST_ASSERT_EQUAL(4, n);
    TEST_ASSERT_EQUAL(0, trunc);
}

void test_count_truncated(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines("hello world foo bar", 6, 2, &trunc);
    TEST_ASSERT_EQUAL(2, n);
    TEST_ASSERT_EQUAL(1, trunc);
}

void test_count_empty_text(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines("", 10, 5, &trunc);
    TEST_ASSERT_EQUAL(0, n);
    TEST_ASSERT_EQUAL(0, trunc);
}

void test_count_null_text(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines(NULL, 10, 5, &trunc);
    TEST_ASSERT_EQUAL(0, n);
}

void test_count_null_truncated_ptr(void)
{
    /* Should not crash with NULL truncated pointer */
    int n = ui_count_wrap_lines("hello world", 6, 10, NULL);
    TEST_ASSERT_EQUAL(2, n);
}

void test_count_exact_fit(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines("aaa bbb", 4, 2, &trunc);
    /* "aaa" / "bbb" = exactly 2 lines, no truncation */
    TEST_ASSERT_EQUAL(2, n);
    TEST_ASSERT_EQUAL(0, trunc);
}

/* ================================================================== */
/* Round-8 additions                                                   */
/* ================================================================== */

void test_gray4_add_large_positive_clamp(void)
{
    /* 0 + 100 → clamped to 15 */
    TEST_ASSERT_EQUAL_UINT8(15, ui_gray4_add(0, 100));
}

void test_flatten_cr_newline(void)
{
    char out[64];
    ui_flatten_one_line("\r\n", out, sizeof(out));
    /* \r and \n both become spaces, collapsed, then trailing stripped → empty */
    TEST_ASSERT_EQUAL_STRING("", out);
}

void test_fit_negative_max_chars(void)
{
    char out[16] = "old";
    int n = ui_fit_line_buf("hello", -1, 1, out, sizeof(out));
    TEST_ASSERT_EQUAL_STRING("", out);
    TEST_ASSERT_EQUAL(0, n);
}

void test_wrap_consecutive_newlines(void)
{
    const char *p = "a\n\nb";
    char out[32];
    int n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL_STRING("a", out);
    TEST_ASSERT_EQUAL(1, n);
    n = ui_wrap_next_line(&p, out, sizeof(out), 10);
    TEST_ASSERT_EQUAL_STRING("b", out);
    TEST_ASSERT_EQUAL(1, n);
}

void test_count_max_lines_one_truncated(void)
{
    int trunc = 0;
    int n = ui_count_wrap_lines("hello world", 6, 1, &trunc);
    /* Only 1 line allowed, but "world" remains → truncated */
    TEST_ASSERT_EQUAL(1, n);
    TEST_ASSERT_EQUAL(1, trunc);
}
