/* Unity test runner for test_ui_text_layout */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* line — guards */
extern void test_line_null_ops_no_crash(void);
extern void test_line_null_draw_text_no_crash(void);
extern void test_line_null_text_no_draw(void);
extern void test_line_empty_text_no_draw(void);
extern void test_line_zero_width_no_draw(void);
extern void test_line_negative_width_no_draw(void);
extern void test_line_width_less_than_char_no_draw(void);

/* line — alignment */
extern void test_line_left_align(void);
extern void test_line_center_align(void);
extern void test_line_right_align(void);

/* line — truncation */
extern void test_line_ellipsis_truncation(void);
extern void test_line_no_ellipsis_clip(void);
extern void test_line_text_exact_fit(void);
extern void test_line_center_when_text_fills_width(void);

/* block — guards */
extern void test_block_null_ops_no_crash(void);
extern void test_block_null_text_no_draw(void);
extern void test_block_empty_text_no_draw(void);
extern void test_block_zero_width_no_draw(void);
extern void test_block_zero_height_no_draw(void);

/* block — ELLIPSIS */
extern void test_block_ellipsis_short_text(void);
extern void test_block_ellipsis_truncates(void);

/* block — CLIP */
extern void test_block_clip_truncates_no_ellipsis(void);

/* block — WRAP */
extern void test_block_wrap_two_lines(void);
extern void test_block_wrap_valign_middle(void);
extern void test_block_wrap_valign_bottom(void);
extern void test_block_wrap_truncated_with_dots(void);

/* block — AUTO */
extern void test_block_auto_short_stays_single_line(void);
extern void test_block_auto_long_wraps(void);
extern void test_block_auto_newline_wraps(void);
extern void test_block_auto_single_line_height_no_wrap(void);

/* block — vertical alignment */
extern void test_block_valign_top_default(void);
extern void test_block_valign_middle_single(void);
extern void test_block_valign_bottom_single(void);

/* block — max_lines */
extern void test_block_max_lines_clamps(void);
extern void test_block_max_lines_zero_uses_height(void);

/* block — horizontal alignment in wrap */
extern void test_block_wrap_center_align(void);
extern void test_block_wrap_right_align(void);

/* block — newline flattening */
extern void test_block_ellipsis_flattens_newlines(void);

/* block — tiny rect */
extern void test_block_tiny_height_less_than_char(void);

/* round-8 additions */
extern void test_line_right_align_exact_fit(void);
extern void test_block_wrap_newline_forces_break(void);
extern void test_block_clip_short_text_no_truncation(void);
extern void test_block_max_lines_clamped_by_height(void);
extern void test_block_wrap_exact_lines_no_dots(void);

int main(void)
{
    UNITY_BEGIN();

    /* line — guards */
    RUN_TEST(test_line_null_ops_no_crash);
    RUN_TEST(test_line_null_draw_text_no_crash);
    RUN_TEST(test_line_null_text_no_draw);
    RUN_TEST(test_line_empty_text_no_draw);
    RUN_TEST(test_line_zero_width_no_draw);
    RUN_TEST(test_line_negative_width_no_draw);
    RUN_TEST(test_line_width_less_than_char_no_draw);

    /* line — alignment */
    RUN_TEST(test_line_left_align);
    RUN_TEST(test_line_center_align);
    RUN_TEST(test_line_right_align);

    /* line — truncation */
    RUN_TEST(test_line_ellipsis_truncation);
    RUN_TEST(test_line_no_ellipsis_clip);
    RUN_TEST(test_line_text_exact_fit);
    RUN_TEST(test_line_center_when_text_fills_width);

    /* block — guards */
    RUN_TEST(test_block_null_ops_no_crash);
    RUN_TEST(test_block_null_text_no_draw);
    RUN_TEST(test_block_empty_text_no_draw);
    RUN_TEST(test_block_zero_width_no_draw);
    RUN_TEST(test_block_zero_height_no_draw);

    /* block — ELLIPSIS */
    RUN_TEST(test_block_ellipsis_short_text);
    RUN_TEST(test_block_ellipsis_truncates);

    /* block — CLIP */
    RUN_TEST(test_block_clip_truncates_no_ellipsis);

    /* block — WRAP */
    RUN_TEST(test_block_wrap_two_lines);
    RUN_TEST(test_block_wrap_valign_middle);
    RUN_TEST(test_block_wrap_valign_bottom);
    RUN_TEST(test_block_wrap_truncated_with_dots);

    /* block — AUTO */
    RUN_TEST(test_block_auto_short_stays_single_line);
    RUN_TEST(test_block_auto_long_wraps);
    RUN_TEST(test_block_auto_newline_wraps);
    RUN_TEST(test_block_auto_single_line_height_no_wrap);

    /* block — vertical alignment */
    RUN_TEST(test_block_valign_top_default);
    RUN_TEST(test_block_valign_middle_single);
    RUN_TEST(test_block_valign_bottom_single);

    /* block — max_lines */
    RUN_TEST(test_block_max_lines_clamps);
    RUN_TEST(test_block_max_lines_zero_uses_height);

    /* block — horizontal alignment in wrap */
    RUN_TEST(test_block_wrap_center_align);
    RUN_TEST(test_block_wrap_right_align);

    /* block — newline flattening */
    RUN_TEST(test_block_ellipsis_flattens_newlines);

    /* block — tiny rect */
    RUN_TEST(test_block_tiny_height_less_than_char);

    /* round-8 additions */
    RUN_TEST(test_line_right_align_exact_fit);
    RUN_TEST(test_block_wrap_newline_forces_break);
    RUN_TEST(test_block_clip_short_text_no_truncation);
    RUN_TEST(test_block_max_lines_clamped_by_height);
    RUN_TEST(test_block_wrap_exact_lines_no_dots);

    return UNITY_END();
}
