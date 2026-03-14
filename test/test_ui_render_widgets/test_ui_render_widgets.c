/*
 * Unit tests for widget renderers (ui_render_widgets.c):
 *
 * Tests each of the 12 widget renderer functions using a capture-mock
 * UiDrawOps that records all draw calls into arrays for assertion.
 *
 * Covers: label, button, panel, box, textbox, progressbar, checkbox,
 *         radiobutton, slider, gauge, icon, chart.
 */

#include "unity.h"
#include <string.h>
#include <stdio.h>
#include "ui_render_widgets.h"
#include "ui_scene.h"
#include "ui_theme.h"

/* ================================================================== */
/* Capture-mock draw ops                                               */
/* ================================================================== */

enum { CAP_MAX = 8192 };

typedef enum {
    CAP_FILL_RECT,
    CAP_HLINE,
    CAP_VLINE,
    CAP_RECT,
    CAP_TEXT,
} CapKind;

typedef struct {
    CapKind kind;
    int x, y, w, h;
    uint8_t c;
    char text[64];
} CapEntry;

static CapEntry s_cap[CAP_MAX];
static int s_cap_count;

static void cap_reset(void)
{
    memset(s_cap, 0, sizeof(s_cap));
    s_cap_count = 0;
}

static void cap_fill_rect(void *ctx, int x, int y, int w, int h, uint8_t c)
{
    (void)ctx;
    if (s_cap_count < CAP_MAX) {
        CapEntry *e = &s_cap[s_cap_count++];
        e->kind = CAP_FILL_RECT;
        e->x = x; e->y = y; e->w = w; e->h = h; e->c = c;
    }
}

static void cap_hline(void *ctx, int x, int y, int w, uint8_t c)
{
    (void)ctx;
    if (s_cap_count < CAP_MAX) {
        CapEntry *e = &s_cap[s_cap_count++];
        e->kind = CAP_HLINE;
        e->x = x; e->y = y; e->w = w; e->h = 0; e->c = c;
    }
}

static void cap_vline(void *ctx, int x, int y, int h, uint8_t c)
{
    (void)ctx;
    if (s_cap_count < CAP_MAX) {
        CapEntry *e = &s_cap[s_cap_count++];
        e->kind = CAP_VLINE;
        e->x = x; e->y = y; e->w = 0; e->h = h; e->c = c;
    }
}

static void cap_rect(void *ctx, int x, int y, int w, int h, uint8_t c)
{
    (void)ctx;
    if (s_cap_count < CAP_MAX) {
        CapEntry *e = &s_cap[s_cap_count++];
        e->kind = CAP_RECT;
        e->x = x; e->y = y; e->w = w; e->h = h; e->c = c;
    }
}

static void cap_text(void *ctx, int x, int y, const char *text, uint8_t c)
{
    (void)ctx;
    if (s_cap_count < CAP_MAX) {
        CapEntry *e = &s_cap[s_cap_count++];
        e->kind = CAP_TEXT;
        e->x = x; e->y = y; e->c = c;
        if (text) {
            strncpy(e->text, text, sizeof(e->text) - 1);
            e->text[sizeof(e->text) - 1] = '\0';
        }
    }
}

/* Make full capture ops (all callbacks set). */
static UiDrawOps make_ops(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.fill_rect  = cap_fill_rect;
    ops.draw_hline = cap_hline;
    ops.draw_vline = cap_vline;
    ops.draw_rect  = cap_rect;
    ops.draw_text  = cap_text;
    return ops;
}

/* Make a default zeroed widget with given type, position, and size. */
static UiWidget make_widget(uint8_t type, int x, int y, int w, int h)
{
    UiWidget wgt;
    memset(&wgt, 0, sizeof(wgt));
    wgt.type = type;
    wgt.x = (uint16_t)x;
    wgt.y = (uint16_t)y;
    wgt.width = (uint16_t)w;
    wgt.height = (uint16_t)h;
    wgt.visible = 1;
    wgt.enabled = 1;
    return wgt;
}

/* Count how many captured entries match a given kind. */
static int cap_count_kind(CapKind kind)
{
    int n = 0;
    for (int i = 0; i < s_cap_count; ++i) {
        if (s_cap[i].kind == kind) ++n;
    }
    return n;
}

/* Find first captured entry of given kind. Returns NULL if not found. */
static const CapEntry *cap_find_first(CapKind kind)
{
    for (int i = 0; i < s_cap_count; ++i) {
        if (s_cap[i].kind == kind) return &s_cap[i];
    }
    return NULL;
}

/* Check if any captured fill_rect starts at (x,y) with (w,h). */
static int cap_has_fill(int x, int y, int w, int h)
{
    for (int i = 0; i < s_cap_count; ++i) {
        if (s_cap[i].kind == CAP_FILL_RECT &&
            s_cap[i].x == x && s_cap[i].y == y &&
            s_cap[i].w == w && s_cap[i].h == h)
            return 1;
    }
    return 0;
}

/* Check if any captured draw_rect starts at (x,y) with (w,h). */
static int cap_has_rect(int x, int y, int w, int h)
{
    for (int i = 0; i < s_cap_count; ++i) {
        if (s_cap[i].kind == CAP_RECT &&
            s_cap[i].x == x && s_cap[i].y == y &&
            s_cap[i].w == w && s_cap[i].h == h)
            return 1;
    }
    return 0;
}

void setUp(void) { cap_reset(); }
void tearDown(void) {}

/* ================================================================== */
/* Label                                                               */
/* ================================================================== */

void test_label_no_border_no_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 10, 20, 60, 12);
    ui_render_label(&w, &ops);
    /* No border, no text → no draw calls except possibly nothing */
    TEST_ASSERT_EQUAL_INT(0, s_cap_count);
}

void test_label_with_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 10, 20, 60, 12);
    w.border = 1;
    ui_render_label(&w, &ops);
    /* Should fill rect + draw border */
    TEST_ASSERT_TRUE(s_cap_count > 0);
    TEST_ASSERT_TRUE(cap_has_fill(10, 20, 60, 12));
}

void test_label_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 12);
    w.border = 1;
    w.text = "Hello";
    ui_render_label(&w, &ops);
    /* Should produce at least one text call */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

void test_label_text_needs_min_height(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 4);
    w.border = 1;
    w.text = "Small";
    ui_render_label(&w, &ops);
    /* Height < UI_FONT_CHAR_H (8), no text drawn */
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_TEXT));
}

/* ================================================================== */
/* Button                                                              */
/* ================================================================== */

void test_button_always_fills(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 5, 5, 40, 14);
    ui_render_button(&w, &ops);
    /* Button always fills its rect (even without border) */
    TEST_ASSERT_TRUE(cap_has_fill(5, 5, 40, 14));
}

void test_button_with_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 5, 5, 40, 14);
    w.border = 1;
    ui_render_button(&w, &ops);
    /* Fill + border rect calls */
    TEST_ASSERT_TRUE(cap_has_fill(5, 5, 40, 14));
    TEST_ASSERT_TRUE(s_cap_count >= 2);
}

void test_button_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 50, 12);
    w.text = "OK";
    ui_render_button(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

/* ================================================================== */
/* Panel                                                               */
/* ================================================================== */

void test_panel_fills_background(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PANEL, 0, 0, 80, 40);
    ui_render_panel(&w, &ops);
    TEST_ASSERT_TRUE(cap_has_fill(0, 0, 80, 40));
}

void test_panel_with_border_and_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PANEL, 0, 0, 80, 40);
    w.border = 1;
    w.text = "Panel Title";
    ui_render_panel(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
    /* Fill + border + text */
    TEST_ASSERT_TRUE(s_cap_count >= 3);
}

/* ================================================================== */
/* Box (delegates to panel)                                            */
/* ================================================================== */

void test_box_delegates_to_panel(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BOX, 10, 10, 30, 30);
    w.border = 1;
    ui_render_box(&w, &ops);
    /* Should produce same output as panel */
    int box_count = s_cap_count;

    cap_reset();
    UiWidget w2 = make_widget(UIW_PANEL, 10, 10, 30, 30);
    w2.border = 1;
    ui_render_panel(&w2, &ops);
    TEST_ASSERT_EQUAL_INT(box_count, s_cap_count);
}

/* ================================================================== */
/* Textbox                                                             */
/* ================================================================== */

void test_textbox_underline(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TEXTBOX, 5, 5, 60, 14);
    ui_render_textbox(&w, &ops);
    /* Should have an hline for the underline (muted color line near bottom) */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_HLINE) > 0);
}

void test_textbox_fills_and_draws_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TEXTBOX, 0, 0, 60, 14);
    w.text = "Input";
    ui_render_textbox(&w, &ops);
    TEST_ASSERT_TRUE(cap_has_fill(0, 0, 60, 14));
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

/* ================================================================== */
/* Progressbar                                                         */
/* ================================================================== */

void test_progressbar_zero_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 60, 12);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 0;
    ui_render_progressbar(&w, &ops);
    /* Should fill background + draw inner rect, but no fill bar */
    TEST_ASSERT_TRUE(cap_has_fill(0, 0, 60, 12));
    /* Inner rect at (1,1, 58, 10) */
    TEST_ASSERT_TRUE(cap_has_rect(1, 1, 58, 10));
}

void test_progressbar_full_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 60, 12);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 100;
    ui_render_progressbar(&w, &ops);
    /* At full value, should have dither fill calls (many hline) */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_HLINE) > 0);
}

void test_progressbar_half_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 102, 12);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_progressbar(&w, &ops);
    /* Should produce draw calls for partial fill */
    TEST_ASSERT_TRUE(s_cap_count > 2);
}

void test_progressbar_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 60, 12);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    w.text = "50%";
    ui_render_progressbar(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

void test_progressbar_clamped_over_max(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 60, 12);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 200;  /* exceeds max */
    ui_render_progressbar(&w, &ops);
    TEST_ASSERT_TRUE(s_cap_count > 0);
}

void test_progressbar_tiny_widget(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 2, 2);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_progressbar(&w, &ops);
    /* inner_w/inner_h <= 0, should return early after fill */
    TEST_ASSERT_TRUE(s_cap_count >= 1);
}

/* ================================================================== */
/* Checkbox                                                            */
/* ================================================================== */

void test_checkbox_unchecked(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 40, 10);
    w.checked = 0;
    ui_render_checkbox(&w, &ops);
    /* Should draw the check box outline */
    TEST_ASSERT_TRUE(s_cap_count > 0);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_RECT) > 0);
}

void test_checkbox_checked_draws_checkmark(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 40, 10);
    w.checked = 1;
    ui_render_checkbox(&w, &ops);

    /* Checked checkbox should produce more hline calls (for X mark) */
    int checked_count = s_cap_count;

    cap_reset();
    w.checked = 0;
    ui_render_checkbox(&w, &ops);
    int unchecked_count = s_cap_count;

    TEST_ASSERT_TRUE(checked_count > unchecked_count);
}

void test_checkbox_too_small(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 3, 3);
    ui_render_checkbox(&w, &ops);
    /* height < 4 || width < 4 → early return */
    TEST_ASSERT_EQUAL_INT(0, s_cap_count);
}

void test_checkbox_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 60, 10);
    w.text = "Opt";
    ui_render_checkbox(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

/* ================================================================== */
/* Radiobutton                                                         */
/* ================================================================== */

void test_radiobutton_unchecked(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_RADIOBUTTON, 0, 0, 40, 10);
    w.checked = 0;
    ui_render_radiobutton(&w, &ops);
    /* Should draw the radio circle outline */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_RECT) > 0);
}

void test_radiobutton_checked_draws_fill(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_RADIOBUTTON, 0, 0, 40, 10);
    w.checked = 1;
    ui_render_radiobutton(&w, &ops);

    /* Checked: extra fill_rect for the inner dot */
    int checked_count = s_cap_count;

    cap_reset();
    w.checked = 0;
    ui_render_radiobutton(&w, &ops);
    int unchecked_count = s_cap_count;

    TEST_ASSERT_TRUE(checked_count > unchecked_count);
}

void test_radiobutton_too_small(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_RADIOBUTTON, 0, 0, 3, 3);
    ui_render_radiobutton(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_cap_count);
}

void test_radiobutton_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_RADIOBUTTON, 0, 0, 60, 10);
    w.text = "Choice";
    ui_render_radiobutton(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

/* ================================================================== */
/* Slider                                                              */
/* ================================================================== */

void test_slider_draws_track_and_knob(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 16);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_slider(&w, &ops);
    /* Background fill + track fill + track rect + knob fill + knob rect */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) >= 3);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_RECT) >= 2);
}

void test_slider_min_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 16);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 0;
    ui_render_slider(&w, &ops);
    /* At min: no dither fill for track (fill_w == 0) */
    TEST_ASSERT_TRUE(s_cap_count > 0);
}

void test_slider_max_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 16);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 100;
    ui_render_slider(&w, &ops);
    /* At max: knob at far right, dither fill covers full track */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_HLINE) > 0);
}

void test_slider_grip_line(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 16);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_slider(&w, &ops);
    /* Should have a grip vline on the knob */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_VLINE) > 0);
}

void test_slider_narrow_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 6, 16);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    /* inner_w = 6 - 4 = 2, should not crash */
    ui_render_slider(&w, &ops);
    TEST_ASSERT_TRUE(s_cap_count > 0);
}

/* ================================================================== */
/* Gauge                                                               */
/* ================================================================== */

void test_gauge_large_draws_arc(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 60, 40);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_gauge(&w, &ops);
    /* Arc gauge draws many pixels via hline(w=1), should be substantial */
    TEST_ASSERT_TRUE(s_cap_count > 20);
}

void test_gauge_small_fallback_bar(void)
{
    UiDrawOps ops = make_ops();
    /* Small gauge with text → compact mode → if gauge_h < 5 with label → fallback bar */
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 20, 12);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    w.text = "G";
    ui_render_gauge(&w, &ops);
    /* Should still produce output (fill + maybe bar) */
    TEST_ASSERT_TRUE(s_cap_count > 0);
}

void test_gauge_zero_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 60, 40);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 0;
    ui_render_gauge(&w, &ops);
    /* Arc with 0 pct — still draws inactive arc + needle + scale */
    TEST_ASSERT_TRUE(s_cap_count > 10);
}

void test_gauge_with_label(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 80, 60);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 75;
    w.text = "Speed";
    ui_render_gauge(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

void test_gauge_tiny_widget(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 4, 4);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_gauge(&w, &ops);
    /* inner_w/inner_h very small → fallback or minimal draws */
    TEST_ASSERT_TRUE(s_cap_count >= 1);
}

/* ================================================================== */
/* Icon                                                                */
/* ================================================================== */

void test_icon_text_fallback(void)
{
    /* HAVE_ICONS is 0 in this build, so icon always falls back to text */
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 0, 0, 20, 12);
    w.text = "W";
    ui_render_icon(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

void test_icon_null_text_shows_question(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 0, 0, 20, 12);
    w.text = NULL;
    ui_render_icon(&w, &ops);
    /* Fallback: first char of "?" */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
    const CapEntry *t = cap_find_first(CAP_TEXT);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL_STRING("?", t->text);
}

void test_icon_empty_text_shows_question(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 0, 0, 20, 12);
    w.text = "";
    ui_render_icon(&w, &ops);
    const CapEntry *t = cap_find_first(CAP_TEXT);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL_STRING("?", t->text);
}

void test_icon_with_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 5, 5, 24, 16);
    w.border = 1;
    w.text = "X";
    ui_render_icon(&w, &ops);
    /* Border → fill + border style + text */
    TEST_ASSERT_TRUE(cap_has_fill(5, 5, 24, 16));
}

void test_icon_too_short_for_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 0, 0, 20, 4);
    w.text = "X";
    ui_render_icon(&w, &ops);
    /* height < UI_FONT_CHAR_H (8), no text */
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_TEXT));
}

/* ================================================================== */
/* Chart                                                               */
/* ================================================================== */

void test_chart_draws_axes(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 80, 40);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_chart(&w, &ops);
    /* Axes drawn with hline + vline */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_HLINE) > 0);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_VLINE) > 0);
}

void test_chart_too_small(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 8, 8);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_chart(&w, &ops);
    /* inner 6×6, chart area = 1×1 < 4 → early return after fill + border check */
    /* Should still have fill_rect at minimum */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) > 0);
}

void test_chart_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 80, 40);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    w.text = "Data";
    ui_render_chart(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

void test_chart_with_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 80, 40);
    w.border = 1;
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_chart(&w, &ops);
    /* Fill + border + axes + bars → many calls */
    TEST_ASSERT_TRUE(s_cap_count > 10);
}

/* ================================================================== */
/* Cross-cutting: border style propagation                             */
/* ================================================================== */

void test_border_style_single_fallback(void)
{
    /* When border=1 but border_style=NONE, should auto-promote to SINGLE */
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 40, 14);
    w.border = 1;
    w.border_style = UI_BORDER_NONE;
    ui_render_button(&w, &ops);
    /* Should have drawn a border (rect call from _draw_border_style) */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_RECT) > 0 ||
                     cap_count_kind(CAP_HLINE) > 0);
}

void test_border_style_double(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PANEL, 0, 0, 40, 20);
    w.border = 1;
    w.border_style = UI_BORDER_DOUBLE;
    ui_render_panel(&w, &ops);
    /* Double border draws more than single border */
    int double_count = s_cap_count;

    cap_reset();
    w.border_style = UI_BORDER_SINGLE;
    ui_render_panel(&w, &ops);
    int single_count = s_cap_count;

    TEST_ASSERT_TRUE(double_count >= single_count);
}

/* ================================================================== */
/* Cross-cutting: custom fg/bg colors                                  */
/* ================================================================== */

void test_custom_fg_bg(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 40, 12);
    w.fg = 10;
    w.bg = 3;
    w.text = "C";
    ui_render_button(&w, &ops);
    /* Fill rect should use custom bg=3 */
    const CapEntry *f = cap_find_first(CAP_FILL_RECT);
    TEST_ASSERT_NOT_NULL(f);
    TEST_ASSERT_EQUAL_UINT8(3, f->c);
    /* Text should use custom fg=10 */
    const CapEntry *t = cap_find_first(CAP_TEXT);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL_UINT8(10, t->c);
}

/* ================================================================== */
/* Null draw_text: renderer must not crash                             */
/* ================================================================== */

void test_label_null_draw_text(void)
{
    UiDrawOps ops = make_ops();
    ops.draw_text = NULL;
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 12);
    w.border = 1;
    w.text = "nope";
    ui_render_label(&w, &ops);
    /* Should not crash; fill + border but no text */
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_TEXT));
}

/* ================================================================== */
/* Round-8 additions                                                   */
/* ================================================================== */

void test_slider_tiny_height(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 4);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_slider(&w, &ops);
    /* Very small height — should still render without crash */
    TEST_ASSERT_TRUE(s_cap_count > 0);
}

void test_panel_no_border_no_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PANEL, 0, 0, 80, 40);
    w.border = 0;
    w.text = NULL;
    ui_render_panel(&w, &ops);
    /* Should fill background only */
    TEST_ASSERT_TRUE(cap_has_fill(0, 0, 80, 40));
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_RECT));
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_TEXT));
}

void test_button_text_needs_min_height(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 50, 4);
    w.text = "Small";
    ui_render_button(&w, &ops);
    /* Height < UI_FONT_CHAR_H (8), text should not be drawn */
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_TEXT));
}

void test_progressbar_under_min_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 60, 12);
    w.min_value = 10;
    w.max_value = 100;
    w.value = 0;  /* below min */
    ui_render_progressbar(&w, &ops);
    /* Should still render without crash */
    TEST_ASSERT_TRUE(s_cap_count > 0);
    TEST_ASSERT_TRUE(cap_has_fill(0, 0, 60, 12));
}

void test_chart_equal_min_max(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 80, 40);
    w.min_value = 50;
    w.max_value = 50;
    w.value = 50;
    ui_render_chart(&w, &ops);
    /* min == max → should not crash, still draws background/axes */
    TEST_ASSERT_TRUE(s_cap_count > 0);
}

/* ================================================================== */
/* Gauge: NULL fill_rect in ops must not crash                         */
/* ================================================================== */

void test_gauge_null_fill_rect_no_crash(void)
{
    /* Large gauge with value text — triggers the fill_rect path for
       clearing behind the value text. With NULL fill_rect, must not crash. */
    UiDrawOps ops = make_ops();
    ops.fill_rect = NULL;
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 80, 60);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_gauge(&w, &ops);
    /* Should have drawn something (arc pixels, text, etc.) but no fill_rect */
    TEST_ASSERT_EQUAL_INT(0, cap_count_kind(CAP_FILL_RECT));
}

/* ================================================================== */
/* Min-size / zero-size widgets — must not crash                       */
/* ================================================================== */

void test_label_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 0, 0);
    ui_render_label(&w, &ops);
    /* Must not crash; may produce zero draw ops */
}

void test_label_1x1(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 1, 1);
    ui_render_label(&w, &ops);
}

void test_button_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 0, 0);
    ui_render_button(&w, &ops);
}

void test_button_1x1(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 1, 1);
    ui_render_button(&w, &ops);
}

void test_slider_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 0, 0);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_slider(&w, &ops);
}

void test_gauge_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 0, 0);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_gauge(&w, &ops);
}

void test_chart_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 0, 0);
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_chart(&w, &ops);
}

void test_panel_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PANEL, 0, 0, 0, 0);
    ui_render_panel(&w, &ops);
}

void test_textbox_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TEXTBOX, 0, 0, 0, 0);
    w.text = "x";
    ui_render_textbox(&w, &ops);
}

/* ------------------------------------------------------------------ */
/*  List                                                               */
/* ------------------------------------------------------------------ */

void test_list_basic_items(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LIST, 0, 0, 100, 40);
    w.border = 1;
    w.text = "One\nTwo\nThree";
    w.value = 0;
    w.min_value = 0;
    ui_render_list(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
}

void test_list_highlight_active(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LIST, 0, 0, 100, 40);
    w.border = 1;
    w.text = "A\nB\nC";
    w.value = 1;
    w.min_value = 0;
    ui_render_list(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) > 0);
}

void test_list_no_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LIST, 0, 0, 80, 40);
    w.text = NULL;
    ui_render_list(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) > 0);
}

void test_list_with_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LIST, 0, 0, 80, 40);
    w.border = 1;
    w.text = "X\nY";
    w.value = 0;
    w.min_value = 0;
    ui_render_list(&w, &ops);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_RECT) > 0 || cap_count_kind(CAP_HLINE) > 0);
}

void test_list_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LIST, 0, 0, 0, 0);
    w.text = "Item";
    ui_render_list(&w, &ops);
    /* Must not crash */
}

/* ================================================================== */
/* Toggle                                                              */
/* ================================================================== */

void test_toggle_unchecked_draws_track(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TOGGLE, 10, 10, 60, 16);
    w.fg = 15;
    w.bg = 0;
    w.checked = 0;
    ui_render_toggle(&w, &ops);
    /* Track background + knob → at least 2 fill_rects */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) >= 2);
}

void test_toggle_checked_draws_track(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TOGGLE, 10, 10, 60, 16);
    w.fg = 15;
    w.bg = 0;
    w.checked = 1;
    ui_render_toggle(&w, &ops);
    /* Track background + knob → at least 2 fill_rects */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) >= 2);
    /* Outline around the track */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_RECT) > 0 || cap_count_kind(CAP_HLINE) > 0);
}

void test_toggle_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TOGGLE, 0, 0, 100, 16);
    w.fg = 15;
    w.bg = 0;
    w.checked = 0;
    w.text = "Wi-Fi";
    ui_render_toggle(&w, &ops);
    /* Label text + track + knob */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_TEXT) > 0);
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) >= 2);
}

void test_toggle_no_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TOGGLE, 0, 0, 40, 12);
    w.fg = 15;
    w.bg = 0;
    w.text = NULL;
    w.checked = 1;
    ui_render_toggle(&w, &ops);
    /* Still draws track + knob */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) >= 2);
}

void test_toggle_zero_size(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TOGGLE, 0, 0, 0, 0);
    w.checked = 0;
    ui_render_toggle(&w, &ops);
    /* Must not crash */
}

void test_toggle_tiny_height(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TOGGLE, 0, 0, 20, 2);
    w.fg = 15;
    w.bg = 0;
    w.checked = 1;
    ui_render_toggle(&w, &ops);
    /* Track forced to min height 4; knob forced to min 2 */
    TEST_ASSERT_TRUE(cap_count_kind(CAP_FILL_RECT) >= 2);
}
