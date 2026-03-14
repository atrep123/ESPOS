#include "unity.h"

#ifdef ESP_PLATFORM

void test_parse_set_bg_simple(void);
void test_parse_set_bg_lowercase(void);
void test_parse_set_bg_zero(void);
void test_parse_set_bg_max_24bit(void);
void test_parse_set_bg_trailing_space(void);
void test_parse_set_bg_overflow_rejects(void);
void test_parse_set_bg_huge_overflow(void);
void test_parse_set_bg_no_value(void);
void test_parse_set_bg_garbage_value(void);
void test_parse_set_bg_trailing_junk(void);
void test_parse_set_bg_negative(void);
void test_parse_unknown_command(void);
void test_parse_empty_line(void);
void test_parse_set_bg_no_space(void);
void test_parse_null_line(void);
void test_parse_null_msg(void);
void test_parse_both_null(void);
void test_parse_zeroes_msg(void);
void test_parse_set_bg_leading_zeros(void);
void test_parse_set_bg_0x_prefix(void);
void test_parse_whitespace_only_line(void);
void test_parse_very_long_line(void);
void test_parse_set_bg_single_digit(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_parse_set_bg_simple);
    RUN_TEST(test_parse_set_bg_lowercase);
    RUN_TEST(test_parse_set_bg_zero);
    RUN_TEST(test_parse_set_bg_max_24bit);
    RUN_TEST(test_parse_set_bg_trailing_space);
    RUN_TEST(test_parse_set_bg_overflow_rejects);
    RUN_TEST(test_parse_set_bg_huge_overflow);
    RUN_TEST(test_parse_set_bg_no_value);
    RUN_TEST(test_parse_set_bg_garbage_value);
    RUN_TEST(test_parse_set_bg_trailing_junk);
    RUN_TEST(test_parse_set_bg_negative);
    RUN_TEST(test_parse_unknown_command);
    RUN_TEST(test_parse_empty_line);
    RUN_TEST(test_parse_set_bg_no_space);
    RUN_TEST(test_parse_null_line);
    RUN_TEST(test_parse_null_msg);
    RUN_TEST(test_parse_both_null);
    RUN_TEST(test_parse_zeroes_msg);
    RUN_TEST(test_parse_set_bg_leading_zeros);
    RUN_TEST(test_parse_set_bg_0x_prefix);
    RUN_TEST(test_parse_whitespace_only_line);
    RUN_TEST(test_parse_very_long_line);
    RUN_TEST(test_parse_set_bg_single_digit);
    UNITY_END();
}

#else

void test_parse_set_bg_simple(void);
void test_parse_set_bg_lowercase(void);
void test_parse_set_bg_zero(void);
void test_parse_set_bg_max_24bit(void);
void test_parse_set_bg_trailing_space(void);
void test_parse_set_bg_overflow_rejects(void);
void test_parse_set_bg_huge_overflow(void);
void test_parse_set_bg_no_value(void);
void test_parse_set_bg_garbage_value(void);
void test_parse_set_bg_trailing_junk(void);
void test_parse_set_bg_negative(void);
void test_parse_unknown_command(void);
void test_parse_empty_line(void);
void test_parse_set_bg_no_space(void);
void test_parse_null_line(void);
void test_parse_null_msg(void);
void test_parse_both_null(void);
void test_parse_zeroes_msg(void);
void test_parse_set_bg_leading_zeros(void);
void test_parse_set_bg_0x_prefix(void);
void test_parse_whitespace_only_line(void);
void test_parse_very_long_line(void);
void test_parse_set_bg_single_digit(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_parse_set_bg_simple);
    RUN_TEST(test_parse_set_bg_lowercase);
    RUN_TEST(test_parse_set_bg_zero);
    RUN_TEST(test_parse_set_bg_max_24bit);
    RUN_TEST(test_parse_set_bg_trailing_space);
    RUN_TEST(test_parse_set_bg_overflow_rejects);
    RUN_TEST(test_parse_set_bg_huge_overflow);
    RUN_TEST(test_parse_set_bg_no_value);
    RUN_TEST(test_parse_set_bg_garbage_value);
    RUN_TEST(test_parse_set_bg_trailing_junk);
    RUN_TEST(test_parse_set_bg_negative);
    RUN_TEST(test_parse_unknown_command);
    RUN_TEST(test_parse_empty_line);
    RUN_TEST(test_parse_set_bg_no_space);
    RUN_TEST(test_parse_null_line);
    RUN_TEST(test_parse_null_msg);
    RUN_TEST(test_parse_both_null);
    RUN_TEST(test_parse_zeroes_msg);
    RUN_TEST(test_parse_set_bg_leading_zeros);
    RUN_TEST(test_parse_set_bg_0x_prefix);
    RUN_TEST(test_parse_whitespace_only_line);
    RUN_TEST(test_parse_very_long_line);
    RUN_TEST(test_parse_set_bg_single_digit);
    return UNITY_END();
}

#endif
