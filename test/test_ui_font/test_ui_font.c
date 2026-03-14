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

/* ================================================================== */
/* Additional glyph coverage                                           */
/* ================================================================== */

void test_glyph_colon_has_two_dots(void)
{
    const uint8_t *g = ui_font6x8_glyph(':');
    TEST_ASSERT_NOT_NULL(g);
    /* row 1 and row 4 should have pixels */
    TEST_ASSERT_NOT_EQUAL(0, g[1]);
    TEST_ASSERT_NOT_EQUAL(0, g[4]);
    /* row 0 and row 3 should be empty */
    TEST_ASSERT_EQUAL_UINT8(0, g[0]);
    TEST_ASSERT_EQUAL_UINT8(0, g[3]);
}

void test_glyph_minus_only_middle_row(void)
{
    const uint8_t *g = ui_font6x8_glyph('-');
    TEST_ASSERT_NOT_NULL(g);
    /* Only row 3 should have pixels */
    TEST_ASSERT_EQUAL_UINT8(0, g[0]);
    TEST_ASSERT_EQUAL_UINT8(0, g[1]);
    TEST_ASSERT_EQUAL_UINT8(0, g[2]);
    TEST_ASSERT_NOT_EQUAL(0, g[3]);
    TEST_ASSERT_EQUAL_UINT8(0, g[4]);
}

void test_glyph_exclamation_not_null(void)
{
    const uint8_t *g = ui_font6x8_glyph('!');
    TEST_ASSERT_NOT_NULL(g);
    int any = 0;
    for (int i = 0; i < 8; i++) {
        if (g[i] != 0) any = 1;
    }
    TEST_ASSERT_TRUE(any);
}

void test_glyph_punctuation_all_distinct(void)
{
    /* All supported punctuation should produce distinct glyphs */
    const char chars[] = ".:-_/?%+<>!=(),#*";
    int n = (int)strlen(chars);
    const uint8_t *glyphs[20];
    for (int i = 0; i < n; i++) {
        glyphs[i] = ui_font6x8_glyph(chars[i]);
        TEST_ASSERT_NOT_NULL(glyphs[i]);
    }
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            int same = (memcmp(glyphs[i], glyphs[j], 8) == 0);
            TEST_ASSERT_FALSE_MESSAGE(same, "Two punctuation glyphs are identical");
        }
    }
}

void test_glyph_null_char_maps_to_qmark(void)
{
    /* '\0' is unsupported; should fallback to '?' */
    const uint8_t *qmark = ui_font6x8_glyph('?');
    const uint8_t *nul = ui_font6x8_glyph('\0');
    TEST_ASSERT_EQUAL_UINT8_ARRAY(qmark, nul, 8);
}

void test_glyph_high_ascii_maps_to_qmark(void)
{
    /* Characters > 127 are unsupported */
    const uint8_t *qmark = ui_font6x8_glyph('?');
    const uint8_t *hi = ui_font6x8_glyph((char)0x80);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(qmark, hi, 8);
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_glyph_slash_top_five_rows(void)
{
    const uint8_t *g = ui_font6x8_glyph('/');
    TEST_ASSERT_NOT_NULL(g);
    /* First 5 rows should have pixels (ascending diagonal) */
    for (int i = 0; i < 5; i++) {
        TEST_ASSERT_NOT_EQUAL(0, g[i]);
    }
    /* Rows 5-7 should be empty */
    TEST_ASSERT_EQUAL_UINT8(0, g[5]);
    TEST_ASSERT_EQUAL_UINT8(0, g[6]);
    TEST_ASSERT_EQUAL_UINT8(0, g[7]);
}

void test_glyph_underscore_only_row_6(void)
{
    const uint8_t *g = ui_font6x8_glyph('_');
    TEST_ASSERT_NOT_NULL(g);
    /* Only row 6 should have pixels */
    for (int i = 0; i < 6; i++) {
        TEST_ASSERT_EQUAL_UINT8(0, g[i]);
    }
    TEST_ASSERT_NOT_EQUAL(0, g[6]);
    TEST_ASSERT_EQUAL_UINT8(0, g[7]);
}

void test_glyph_same_char_returns_same_pointer(void)
{
    const uint8_t *g1 = ui_font6x8_glyph('X');
    const uint8_t *g2 = ui_font6x8_glyph('X');
    TEST_ASSERT_TRUE(g1 == g2);
}

void test_glyph_row7_always_zero(void)
{
    /* Space glyph should be all-zero (no visible pixels) */
    const uint8_t *sp = ui_font6x8_glyph(' ');
    for (int r = 0; r < 8; r++) {
        TEST_ASSERT_EQUAL_UINT8_MESSAGE(0, sp[r], "Space glyph row should be zero");
    }
}

void test_glyph_digit_symmetry_0_and_8(void)
{
    /* '0' and '8' should be different (8 has middle bar) */
    const uint8_t *g0 = ui_font6x8_glyph('0');
    const uint8_t *g8 = ui_font6x8_glyph('8');
    TEST_ASSERT_FALSE(memcmp(g0, g8, 8) == 0);
}
