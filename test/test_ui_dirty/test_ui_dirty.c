/*
 * Unit tests for pure UI state helpers (ui_dirty.c):
 * - UiDirty: dirty rectangle tracking (clear, add, merge, clamp)
 * - ui_text_equals: null-safe string comparison
 * - ui_widget_toggle_checked: checkbox toggle
 * - ui_widget_clamp_value: slider value clamping
 */

#include "unity.h"
#include <string.h>
#include "services/ui/ui_dirty.h"

void setUp(void) {}
void tearDown(void) {}

/* ================================================================== */
/* ui_dirty_clear                                                      */
/* ================================================================== */

void test_dirty_clear_zeroes_all(void)
{
    UiDirty d = { .dirty = 1, .x0 = 10, .y0 = 20, .x1 = 100, .y1 = 50 };
    ui_dirty_clear(&d);
    TEST_ASSERT_EQUAL_INT(0, d.dirty);
    TEST_ASSERT_EQUAL_INT(0, d.x0);
    TEST_ASSERT_EQUAL_INT(0, d.y0);
    TEST_ASSERT_EQUAL_INT(0, d.x1);
    TEST_ASSERT_EQUAL_INT(0, d.y1);
}

void test_dirty_clear_null_safe(void)
{
    ui_dirty_clear(NULL); /* must not crash */
}

/* ================================================================== */
/* ui_dirty_add                                                        */
/* ================================================================== */

void test_dirty_add_first_region(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 10, 20, 30, 40, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(10, d.x0);
    TEST_ASSERT_EQUAL_INT(20, d.y0);
    TEST_ASSERT_EQUAL_INT(40, d.x1);
    TEST_ASSERT_EQUAL_INT(60, d.y1);
}

void test_dirty_add_merge_expands(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 10, 10, 20, 20, 256, 128);
    ui_dirty_add(&d, 50, 50, 30, 30, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(10, d.x0);
    TEST_ASSERT_EQUAL_INT(10, d.y0);
    TEST_ASSERT_EQUAL_INT(80, d.x1);
    TEST_ASSERT_EQUAL_INT(80, d.y1);
}

void test_dirty_add_clamp_to_display(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 240, 120, 100, 100, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(240, d.x0);
    TEST_ASSERT_EQUAL_INT(120, d.y0);
    TEST_ASSERT_EQUAL_INT(256, d.x1);
    TEST_ASSERT_EQUAL_INT(128, d.y1);
}

void test_dirty_add_negative_origin(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, -10, -5, 30, 20, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(0, d.x0);
    TEST_ASSERT_EQUAL_INT(0, d.y0);
    TEST_ASSERT_EQUAL_INT(20, d.x1);
    TEST_ASSERT_EQUAL_INT(15, d.y1);
}

void test_dirty_add_zero_size_ignored(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 10, 10, 0, 0, 256, 128);
    TEST_ASSERT_EQUAL_INT(0, d.dirty);
}

void test_dirty_add_negative_size_ignored(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 10, 10, -5, 10, 256, 128);
    TEST_ASSERT_EQUAL_INT(0, d.dirty);
}

void test_dirty_add_null_safe(void)
{
    ui_dirty_add(NULL, 0, 0, 10, 10, 256, 128); /* must not crash */
}

void test_dirty_add_fully_offscreen(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 300, 200, 10, 10, 256, 128);
    TEST_ASSERT_EQUAL_INT(0, d.dirty);
}

void test_dirty_add_merge_overlapping(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 10, 10, 50, 50, 256, 128);
    ui_dirty_add(&d, 30, 30, 50, 50, 256, 128);
    TEST_ASSERT_EQUAL_INT(10, d.x0);
    TEST_ASSERT_EQUAL_INT(10, d.y0);
    TEST_ASSERT_EQUAL_INT(80, d.x1);
    TEST_ASSERT_EQUAL_INT(80, d.y1);
}

void test_dirty_add_small_display(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 0, 0, 100, 100, 32, 16);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(0, d.x0);
    TEST_ASSERT_EQUAL_INT(0, d.y0);
    TEST_ASSERT_EQUAL_INT(32, d.x1);
    TEST_ASSERT_EQUAL_INT(16, d.y1);
}

/* ================================================================== */
/* ui_text_equals                                                      */
/* ================================================================== */

void test_text_equals_same(void)
{
    TEST_ASSERT_EQUAL_INT(1, ui_text_equals("hello", "hello"));
}

void test_text_equals_different(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_text_equals("hello", "world"));
}

void test_text_equals_null_null(void)
{
    TEST_ASSERT_EQUAL_INT(1, ui_text_equals(NULL, NULL));
}

void test_text_equals_null_empty(void)
{
    TEST_ASSERT_EQUAL_INT(1, ui_text_equals(NULL, ""));
}

void test_text_equals_empty_null(void)
{
    TEST_ASSERT_EQUAL_INT(1, ui_text_equals("", NULL));
}

void test_text_equals_null_nonempty(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_text_equals(NULL, "abc"));
}

/* ================================================================== */
/* ui_widget_toggle_checked                                            */
/* ================================================================== */

void test_toggle_checkbox_unchecked_to_checked(void)
{
    UiWidget w = {0};
    w.type = UIW_CHECKBOX;
    w.checked = 0;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_toggle_checked(&w));
    TEST_ASSERT_EQUAL_UINT8(1, w.checked);
}

void test_toggle_checkbox_checked_to_unchecked(void)
{
    UiWidget w = {0};
    w.type = UIW_CHECKBOX;
    w.checked = 1;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_toggle_checked(&w));
    TEST_ASSERT_EQUAL_UINT8(0, w.checked);
}

void test_toggle_not_checkbox_noop(void)
{
    UiWidget w = {0};
    w.type = UIW_BUTTON;
    w.checked = 0;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_toggle_checked(&w));
    TEST_ASSERT_EQUAL_UINT8(0, w.checked);
}

void test_toggle_null_safe(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_widget_toggle_checked(NULL));
}

void test_toggle_double_flip(void)
{
    UiWidget w = {0};
    w.type = UIW_CHECKBOX;
    w.checked = 0;
    ui_widget_toggle_checked(&w);
    ui_widget_toggle_checked(&w);
    TEST_ASSERT_EQUAL_UINT8(0, w.checked);
}

void test_toggle_radiobutton_rejected(void)
{
    UiWidget w = {0};
    w.type = UIW_RADIOBUTTON;
    w.checked = 0;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_toggle_checked(&w));
    TEST_ASSERT_EQUAL_UINT8(0, w.checked);
}

/* ================================================================== */
/* ui_widget_clamp_value                                               */
/* ================================================================== */

void test_clamp_increment(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, 10));
    TEST_ASSERT_EQUAL_INT16(60, w.value);
}

void test_clamp_decrement(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, -20));
    TEST_ASSERT_EQUAL_INT16(30, w.value);
}

void test_clamp_at_max(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 95;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, 50));
    TEST_ASSERT_EQUAL_INT16(100, w.value);
}

void test_clamp_at_min(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 5;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, -50));
    TEST_ASSERT_EQUAL_INT16(0, w.value);
}

void test_clamp_no_change_returns_zero(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 100;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_clamp_value(&w, 10));
    TEST_ASSERT_EQUAL_INT16(100, w.value);
}

void test_clamp_zero_delta(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_clamp_value(&w, 0));
    TEST_ASSERT_EQUAL_INT16(50, w.value);
}

void test_clamp_not_slider_rejected(void)
{
    UiWidget w = {0};
    w.type = UIW_LABEL;
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(0, ui_widget_clamp_value(&w, 10));
    TEST_ASSERT_EQUAL_INT16(50, w.value);
}

void test_clamp_gauge_accepted(void)
{
    UiWidget w = {0};
    w.type = UIW_GAUGE;
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, 10));
    TEST_ASSERT_EQUAL_INT16(60, w.value);
}

void test_clamp_progressbar_accepted(void)
{
    UiWidget w = {0};
    w.type = UIW_PROGRESSBAR;
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, 10));
    TEST_ASSERT_EQUAL_INT16(60, w.value);
}

void test_clamp_null_safe(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_widget_clamp_value(NULL, 5));
}

void test_clamp_negative_range(void)
{
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = -50;
    w.min_value = -100;
    w.max_value = 0;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, 30));
    TEST_ASSERT_EQUAL_INT16(-20, w.value);
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_dirty_add_single_pixel(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 100, 50, 1, 1, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(100, d.x0);
    TEST_ASSERT_EQUAL_INT(50, d.y0);
    TEST_ASSERT_EQUAL_INT(101, d.x1);
    TEST_ASSERT_EQUAL_INT(51, d.y1);
}

void test_dirty_add_full_screen(void)
{
    UiDirty d = {0};
    ui_dirty_add(&d, 0, 0, 256, 128, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(0, d.x0);
    TEST_ASSERT_EQUAL_INT(0, d.y0);
    TEST_ASSERT_EQUAL_INT(256, d.x1);
    TEST_ASSERT_EQUAL_INT(128, d.y1);
}

void test_text_equals_case_sensitive(void)
{
    /* text_equals is case-sensitive */
    TEST_ASSERT_EQUAL_INT(0, ui_text_equals("Hello", "hello"));
    TEST_ASSERT_EQUAL_INT(0, ui_text_equals("ABC", "abc"));
}

void test_clamp_both_bounds_equal(void)
{
    /* min == max: value is forced to that single value */
    UiWidget w = {0};
    w.type = UIW_SLIDER;
    w.value = 50;
    w.min_value = 42;
    w.max_value = 42;
    TEST_ASSERT_EQUAL_INT(1, ui_widget_clamp_value(&w, 10));
    TEST_ASSERT_EQUAL_INT16(42, w.value);
}

void test_dirty_clear_then_add(void)
{
    /* Clear existing dirty, then add new region — should work fresh */
    UiDirty d = {0};
    ui_dirty_add(&d, 10, 10, 50, 50, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    ui_dirty_clear(&d);
    TEST_ASSERT_EQUAL_INT(0, d.dirty);
    ui_dirty_add(&d, 200, 100, 20, 20, 256, 128);
    TEST_ASSERT_EQUAL_INT(1, d.dirty);
    TEST_ASSERT_EQUAL_INT(200, d.x0);
    TEST_ASSERT_EQUAL_INT(100, d.y0);
    TEST_ASSERT_EQUAL_INT(220, d.x1);
    TEST_ASSERT_EQUAL_INT(120, d.y1);
}
