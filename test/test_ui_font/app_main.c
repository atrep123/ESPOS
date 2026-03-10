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
    return UNITY_END();
}

#endif
