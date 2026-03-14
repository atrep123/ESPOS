/*
 * Unit tests for pure widget style helpers (ui_widget_style.c):
 * - ui_widget_has_extended: detect non-default extended fields
 * - ui_widget_is_visible: visibility query
 * - ui_widget_is_enabled: enabled query
 * - ui_widget_colors: resolved color palette computation
 */

#include "unity.h"
#include <string.h>
#include "ui_widget_style.h"

void setUp(void) {}
void tearDown(void) {}

/* Helper: create a zeroed widget with a specific type. */
static UiWidget make_widget(UiWidgetType type)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = (uint8_t)type;
    return w;
}

/* ================================================================== */
/* ui_widget_has_extended                                               */
/* ================================================================== */

void test_has_extended_all_zero(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    TEST_ASSERT_EQUAL_INT(0, ui_widget_has_extended(&w));
}

void test_has_extended_fg_set(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.fg = 10;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w));
}

void test_has_extended_visible_set(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.visible = 1;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w));
}

void test_has_extended_style_set(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.style = UI_STYLE_INVERSE;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w));
}

void test_has_extended_null(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_widget_has_extended(NULL));
}

/* ================================================================== */
/* ui_widget_is_visible                                                */
/* ================================================================== */

void test_visible_default_widget(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    /* No extended fields → visible by default */
    TEST_ASSERT_EQUAL_INT(1, ui_widget_is_visible(&w));
}

void test_visible_explicit_visible(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_is_visible(&w));
}

void test_visible_invisible(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.enabled = 1;  /* has_extended triggers */
    w.visible = 0;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_is_visible(&w));
}

void test_visible_null(void)
{
    /* NULL → has_extended returns 0 → visible by default */
    TEST_ASSERT_EQUAL_INT(1, ui_widget_is_visible(NULL));
}

/* ================================================================== */
/* ui_widget_is_enabled                                                */
/* ================================================================== */

void test_enabled_default_widget(void)
{
    UiWidget w = make_widget(UIW_SLIDER);
    TEST_ASSERT_EQUAL_INT(1, ui_widget_is_enabled(&w));
}

void test_enabled_explicit_enabled(void)
{
    UiWidget w = make_widget(UIW_SLIDER);
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_is_enabled(&w));
}

void test_enabled_disabled(void)
{
    UiWidget w = make_widget(UIW_SLIDER);
    w.visible = 1;
    w.enabled = 0;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_is_enabled(&w));
}

void test_enabled_null(void)
{
    TEST_ASSERT_EQUAL_INT(1, ui_widget_is_enabled(NULL));
}

/* ================================================================== */
/* ui_widget_colors                                                    */
/* ================================================================== */

/* Theme constants for tests (same as 4bpp theme) */
#define COL_TEXT 15
#define COL_BG   0

void test_colors_default_widget(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, &border, &muted, &fill);
    TEST_ASSERT_EQUAL_UINT8(COL_TEXT, fg);
    TEST_ASSERT_EQUAL_UINT8(COL_BG, bg);
}

void test_colors_custom_fg_bg(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.fg = 12;
    w.bg = 3;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8(12, fg);
    TEST_ASSERT_EQUAL_UINT8(3, bg);
}

void test_colors_inverse_style(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.style = UI_STYLE_INVERSE;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    /* Inverse swaps fg/bg */
    TEST_ASSERT_EQUAL_UINT8(COL_BG, fg);
    TEST_ASSERT_EQUAL_UINT8(COL_TEXT, bg);
}

void test_colors_highlight_style(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.style = UI_STYLE_HIGHLIGHT;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8(COL_TEXT, fg);
    /* bg bumped +2 from 0 → clamped to 2 */
    TEST_ASSERT_EQUAL_UINT8(2, bg);
}

void test_colors_disabled_dims(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.visible = 1;
    w.enabled = 0;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    /* fg = gray4_add(15, -6) = 9 */
    TEST_ASSERT_EQUAL_UINT8(9, fg);
    /* bg = gray4_add(0, -2) = 0 (clamped) */
    TEST_ASSERT_EQUAL_UINT8(0, bg);
}

void test_colors_border_muted_fill(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    uint8_t border, muted, fill;
    ui_widget_colors(&w, COL_TEXT, COL_BG, NULL, NULL, &border, &muted, &fill);
    /* border = gray4_add(15,-4)=11, muted = gray4_add(15,-7)=8, fill = gray4_add(15,-2)=13 */
    TEST_ASSERT_EQUAL_UINT8(11, border);
    TEST_ASSERT_EQUAL_UINT8(8, muted);
    TEST_ASSERT_EQUAL_UINT8(13, fill);
}

void test_colors_null_widget(void)
{
    uint8_t fg, bg;
    ui_widget_colors(NULL, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8(COL_TEXT, fg);
    TEST_ASSERT_EQUAL_UINT8(COL_BG, bg);
}

void test_colors_both_fg_bg_zero_uses_theme(void)
{
    /* If w->fg=0 and w->bg=0, keep theme defaults */
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.fg = 0;
    w.bg = 0;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8(COL_TEXT, fg);
    TEST_ASSERT_EQUAL_UINT8(COL_BG, bg);
}

void test_colors_fg_zero_bg_nonzero(void)
{
    /* w->fg=0, w->bg=5 → fg stays col_text, bg=5 */
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.fg = 0;
    w.bg = 5;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8(COL_TEXT, fg);
    TEST_ASSERT_EQUAL_UINT8(5, bg);
}

void test_colors_inverse_plus_highlight(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.style = UI_STYLE_INVERSE | UI_STYLE_HIGHLIGHT;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    /* Inverse first: fg=0, bg=15, then highlight: bg=gray4_add(15,2)=15 (clamped) */
    TEST_ASSERT_EQUAL_UINT8(0, fg);
    TEST_ASSERT_EQUAL_UINT8(15, bg);
}

void test_colors_1bpp_theme(void)
{
    /* Simulating 1bpp theme: col_text=1, col_bg=0 */
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    uint8_t fg, bg;
    ui_widget_colors(&w, 1, 0, &fg, &bg, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8(1, fg);
    TEST_ASSERT_EQUAL_UINT8(0, bg);
}

/* ================================================================== */
/* has_extended — additional field coverage                             */
/* ================================================================== */

void test_has_extended_bg_set(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.bg = 5;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w));
}

void test_has_extended_border_style_set(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.border_style = UI_BORDER_DOUBLE;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w));
}

void test_has_extended_text_overflow_and_max_lines(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.text_overflow = 1;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w));

    UiWidget w2 = make_widget(UIW_LABEL);
    w2.max_lines = 2;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_has_extended(&w2));
}

/* ================================================================== */
/* colors — combinatorial interactions                                 */
/* ================================================================== */

void test_colors_custom_fg_bg_inverse(void)
{
    UiWidget w = make_widget(UIW_LABEL);
    w.visible = 1;
    w.enabled = 1;
    w.fg = 12;
    w.bg = 3;
    w.style = UI_STYLE_INVERSE;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    /* Custom fg=12, bg=3, then inverse → fg=3, bg=12 */
    TEST_ASSERT_EQUAL_UINT8(3, fg);
    TEST_ASSERT_EQUAL_UINT8(12, bg);
}

void test_colors_disabled_custom_colors(void)
{
    UiWidget w = make_widget(UIW_BUTTON);
    w.visible = 1;
    w.enabled = 0;
    w.fg = 10;
    w.bg = 4;
    uint8_t fg, bg;
    ui_widget_colors(&w, COL_TEXT, COL_BG, &fg, &bg, NULL, NULL, NULL);
    /* custom fg=10, disabled: fg = gray4_add(10,-6)=4, bg = gray4_add(4,-2)=2 */
    TEST_ASSERT_EQUAL_UINT8(4, fg);
    TEST_ASSERT_EQUAL_UINT8(2, bg);
}
