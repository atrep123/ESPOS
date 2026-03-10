#include "unity.h"

#include <string.h>

#include "ui_font_6x8.h"

void setUp(void) {}
void tearDown(void) {}

void test_glyph_space_is_all_zero(void)
{
    const uint8_t *g = ui_font6x8_glyph(' ');
    TEST_ASSERT_NOT_NULL(g);
    for (int i = 0; i < 8; i++) {
        TEST_ASSERT_EQUAL_UINT8(0, g[i]);
    }
}

void test_glyph_A_is_not_all_zero(void)
{
    const uint8_t *g = ui_font6x8_glyph('A');
    TEST_ASSERT_NOT_NULL(g);
    int any = 0;
    for (int i = 0; i < 8; i++) {
        if (g[i] != 0) any = 1;
    }
    TEST_ASSERT_TRUE(any);
}

void test_glyph_lowercase_maps_to_uppercase(void)
{
    const uint8_t *lower = ui_font6x8_glyph('a');
    const uint8_t *upper = ui_font6x8_glyph('A');
    TEST_ASSERT_EQUAL_UINT8_ARRAY(upper, lower, 8);
}

void test_glyph_digit_0_not_null(void)
{
    TEST_ASSERT_NOT_NULL(ui_font6x8_glyph('0'));
}

void test_glyph_unknown_returns_qmark(void)
{
    const uint8_t *qmark = ui_font6x8_glyph('?');
    const uint8_t *unknown = ui_font6x8_glyph('~');
    TEST_ASSERT_EQUAL_UINT8_ARRAY(qmark, unknown, 8);
}

void test_glyph_dot_has_pixel_near_bottom(void)
{
    const uint8_t *g = ui_font6x8_glyph('.');
    /* Rows 0-4 should be zero; rows 5-6 should have a dot */
    for (int i = 0; i < 5; i++) {
        TEST_ASSERT_EQUAL_UINT8(0, g[i]);
    }
    TEST_ASSERT_NOT_EQUAL(0, g[5]);
}

void test_glyph_all_digits_are_distinct(void)
{
    const uint8_t *glyphs[10];
    for (int i = 0; i < 10; i++) {
        glyphs[i] = ui_font6x8_glyph((char)('0' + i));
    }
    for (int i = 0; i < 10; i++) {
        for (int j = i + 1; j < 10; j++) {
            int same = (memcmp(glyphs[i], glyphs[j], 8) == 0);
            TEST_ASSERT_FALSE(same);
        }
    }
}

void test_glyph_all_letters_are_distinct(void)
{
    const uint8_t *glyphs[26];
    for (int i = 0; i < 26; i++) {
        glyphs[i] = ui_font6x8_glyph((char)('A' + i));
    }
    for (int i = 0; i < 26; i++) {
        for (int j = i + 1; j < 26; j++) {
            int same = (memcmp(glyphs[i], glyphs[j], 8) == 0);
            TEST_ASSERT_FALSE(same);
        }
    }
}
