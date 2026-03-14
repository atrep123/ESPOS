#include "unity.h"

#ifdef ESP_PLATFORM

void test_glyph_space_is_all_zero(void);
void test_glyph_A_is_not_all_zero(void);
void test_glyph_lowercase_maps_to_uppercase(void);
void test_glyph_digit_0_not_null(void);
void test_glyph_unknown_returns_qmark(void);
void test_glyph_dot_has_pixel_near_bottom(void);
void test_glyph_all_digits_are_distinct(void);
void test_glyph_all_letters_are_distinct(void);
void test_glyph_colon_has_two_dots(void);
void test_glyph_minus_only_middle_row(void);
void test_glyph_exclamation_not_null(void);
void test_glyph_punctuation_all_distinct(void);
void test_glyph_null_char_maps_to_qmark(void);
void test_glyph_high_ascii_maps_to_qmark(void);
void test_glyph_slash_top_five_rows(void);
void test_glyph_underscore_only_row_6(void);
void test_glyph_same_char_returns_same_pointer(void);
void test_glyph_row7_always_zero(void);
void test_glyph_digit_symmetry_0_and_8(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_glyph_space_is_all_zero);
    RUN_TEST(test_glyph_A_is_not_all_zero);
    RUN_TEST(test_glyph_lowercase_maps_to_uppercase);
    RUN_TEST(test_glyph_digit_0_not_null);
    RUN_TEST(test_glyph_unknown_returns_qmark);
    RUN_TEST(test_glyph_dot_has_pixel_near_bottom);
    RUN_TEST(test_glyph_all_digits_are_distinct);
    RUN_TEST(test_glyph_all_letters_are_distinct);
    RUN_TEST(test_glyph_colon_has_two_dots);
    RUN_TEST(test_glyph_minus_only_middle_row);
    RUN_TEST(test_glyph_exclamation_not_null);
    RUN_TEST(test_glyph_punctuation_all_distinct);
    RUN_TEST(test_glyph_null_char_maps_to_qmark);
    RUN_TEST(test_glyph_high_ascii_maps_to_qmark);
    RUN_TEST(test_glyph_slash_top_five_rows);
    RUN_TEST(test_glyph_underscore_only_row_6);
    RUN_TEST(test_glyph_same_char_returns_same_pointer);
    RUN_TEST(test_glyph_row7_always_zero);
    RUN_TEST(test_glyph_digit_symmetry_0_and_8);
    UNITY_END();
}

#else

void test_glyph_space_is_all_zero(void);
void test_glyph_A_is_not_all_zero(void);
void test_glyph_lowercase_maps_to_uppercase(void);
void test_glyph_digit_0_not_null(void);
void test_glyph_unknown_returns_qmark(void);
void test_glyph_dot_has_pixel_near_bottom(void);
void test_glyph_all_digits_are_distinct(void);
void test_glyph_all_letters_are_distinct(void);
void test_glyph_colon_has_two_dots(void);
void test_glyph_minus_only_middle_row(void);
void test_glyph_exclamation_not_null(void);
void test_glyph_punctuation_all_distinct(void);
void test_glyph_null_char_maps_to_qmark(void);
void test_glyph_high_ascii_maps_to_qmark(void);
void test_glyph_slash_top_five_rows(void);
void test_glyph_underscore_only_row_6(void);
void test_glyph_same_char_returns_same_pointer(void);
void test_glyph_row7_always_zero(void);
void test_glyph_digit_symmetry_0_and_8(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_glyph_space_is_all_zero);
    RUN_TEST(test_glyph_A_is_not_all_zero);
    RUN_TEST(test_glyph_lowercase_maps_to_uppercase);
    RUN_TEST(test_glyph_digit_0_not_null);
    RUN_TEST(test_glyph_unknown_returns_qmark);
    RUN_TEST(test_glyph_dot_has_pixel_near_bottom);
    RUN_TEST(test_glyph_all_digits_are_distinct);
    RUN_TEST(test_glyph_all_letters_are_distinct);
    RUN_TEST(test_glyph_colon_has_two_dots);
    RUN_TEST(test_glyph_minus_only_middle_row);
    RUN_TEST(test_glyph_exclamation_not_null);
    RUN_TEST(test_glyph_punctuation_all_distinct);
    RUN_TEST(test_glyph_null_char_maps_to_qmark);
    RUN_TEST(test_glyph_high_ascii_maps_to_qmark);
    RUN_TEST(test_glyph_slash_top_five_rows);
    RUN_TEST(test_glyph_underscore_only_row_6);
    RUN_TEST(test_glyph_same_char_returns_same_pointer);
    RUN_TEST(test_glyph_row7_always_zero);
    RUN_TEST(test_glyph_digit_symmetry_0_and_8);
    return UNITY_END();
}

#endif
