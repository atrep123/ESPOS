#include "unity.h"

#include <string.h>
#include "ui_render.h"
#include "ui_scene.h"

/* ------------------------------------------------------------------ */
/* Mock draw-ops capturing infrastructure                              */
/* ------------------------------------------------------------------ */

#define CAP_MAX 64

typedef enum {
    DRAW_FILL_RECT,
    DRAW_HLINE,
    DRAW_VLINE,
    DRAW_RECT,
    DRAW_TEXT,
    DRAW_BLIT_MONO,
} DrawCallType;

typedef struct {
    DrawCallType type;
    int x, y, w, h;
    uint8_t color;
    char text[64];
} DrawCall;

static DrawCall s_calls[CAP_MAX];
static int s_call_count;

static void cap_reset(void)
{
    memset(s_calls, 0, sizeof(s_calls));
    s_call_count = 0;
}

static void cap_fill_rect(void *ctx, int x, int y, int w, int h, uint8_t c)
{
    (void)ctx;
    if (s_call_count < CAP_MAX) {
        DrawCall *dc = &s_calls[s_call_count++];
        dc->type = DRAW_FILL_RECT;
        dc->x = x; dc->y = y; dc->w = w; dc->h = h; dc->color = c;
    }
}

static void cap_draw_hline(void *ctx, int x, int y, int w, uint8_t c)
{
    (void)ctx;
    if (s_call_count < CAP_MAX) {
        DrawCall *dc = &s_calls[s_call_count++];
        dc->type = DRAW_HLINE;
        dc->x = x; dc->y = y; dc->w = w; dc->h = 0; dc->color = c;
    }
}

static void cap_draw_vline(void *ctx, int x, int y, int h, uint8_t c)
{
    (void)ctx;
    if (s_call_count < CAP_MAX) {
        DrawCall *dc = &s_calls[s_call_count++];
        dc->type = DRAW_VLINE;
        dc->x = x; dc->y = y; dc->w = 0; dc->h = h; dc->color = c;
    }
}

static void cap_draw_rect(void *ctx, int x, int y, int w, int h, uint8_t c)
{
    (void)ctx;
    if (s_call_count < CAP_MAX) {
        DrawCall *dc = &s_calls[s_call_count++];
        dc->type = DRAW_RECT;
        dc->x = x; dc->y = y; dc->w = w; dc->h = h; dc->color = c;
    }
}

static void cap_draw_text(void *ctx, int x, int y, const char *text, uint8_t c)
{
    (void)ctx;
    if (s_call_count < CAP_MAX) {
        DrawCall *dc = &s_calls[s_call_count++];
        dc->type = DRAW_TEXT;
        dc->x = x; dc->y = y; dc->color = c;
        if (text != NULL) {
            strncpy(dc->text, text, sizeof(dc->text) - 1);
            dc->text[sizeof(dc->text) - 1] = '\0';
        }
    }
}

static void cap_blit_mono(void *ctx, int x, int y, int w, int h, int stride,
                          const uint8_t *data, uint8_t color, uint8_t mode)
{
    (void)ctx; (void)data; (void)stride; (void)mode;
    if (s_call_count < CAP_MAX) {
        DrawCall *dc = &s_calls[s_call_count++];
        dc->type = DRAW_BLIT_MONO;
        dc->x = x; dc->y = y; dc->w = w; dc->h = h; dc->color = color;
    }
}

static UiDrawOps make_ops(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.fill_rect = cap_fill_rect;
    ops.draw_hline = cap_draw_hline;
    ops.draw_vline = cap_draw_vline;
    ops.draw_rect = cap_draw_rect;
    ops.draw_text = cap_draw_text;
    ops.blit_mono = cap_blit_mono;
    return ops;
}

/* Helper to check if any captured call was a specific type. */
static int has_call_type(DrawCallType t)
{
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == t) {
            return 1;
        }
    }
    return 0;
}

/* Helper to check if any draw_text call contains a substring. */
static int has_text_containing(const char *substr)
{
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_TEXT && strstr(s_calls[i].text, substr) != NULL) {
            return 1;
        }
    }
    return 0;
}

/* Helper to build a simple extended widget (visible + enabled). */
static UiWidget make_widget(UiWidgetType type, uint16_t x, uint16_t y,
                            uint16_t w, uint16_t h)
{
    UiWidget wgt;
    memset(&wgt, 0, sizeof(wgt));
    wgt.type = (uint8_t)type;
    wgt.x = x;
    wgt.y = y;
    wgt.width = w;
    wgt.height = h;
    wgt.visible = 1;
    wgt.enabled = 1;
    return wgt;
}

void setUp(void) { cap_reset(); }
void tearDown(void) {}

/* ------------------------------------------------------------------ */
/* NULL / edge-case guard tests                                        */
/* ------------------------------------------------------------------ */

void test_render_widget_null_widget(void)
{
    UiDrawOps ops = make_ops();
    ui_render_widget(NULL, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

void test_render_widget_null_ops(void)
{
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 10);
    w.text = "hi";
    ui_render_widget(&w, NULL);
    /* No crash = pass */
    TEST_PASS();
}

void test_render_scene_null_scene(void)
{
    UiDrawOps ops = make_ops();
    ui_render_scene(NULL, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

void test_render_scene_null_ops(void)
{
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 10);
    w.text = "scene";
    UiScene scene = { .name = "t", .width = 256, .height = 128,
                      .widget_count = 1, .widgets = &w };
    ui_render_scene(&scene, NULL);
    TEST_PASS();
}

void test_render_scene_empty(void)
{
    UiDrawOps ops = make_ops();
    UiScene scene = { .name = "empty", .width = 256, .height = 128,
                      .widget_count = 0, .widgets = NULL };
    ui_render_scene(&scene, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

/* ------------------------------------------------------------------ */
/* Visibility tests                                                    */
/* ------------------------------------------------------------------ */

void test_render_invisible_widget_no_draw(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 10);
    w.text = "hidden";
    w.visible = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

void test_render_widget_no_extended_fields_is_visible(void)
{
    /* A widget with all extended fields zero is treated as visible
     * (has_extended returns false → visible defaults to true). */
    UiDrawOps ops = make_ops();
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BOX;
    w.width = 20;
    w.height = 10;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Label                                                               */
/* ------------------------------------------------------------------ */

void test_render_label_draws_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 10, 20, 60, 10);
    w.text = "Hello";
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_TEXT));
    TEST_ASSERT_TRUE(has_text_containing("Hello"));
}

void test_render_label_no_text_no_draw(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 10);
    w.text = NULL;
    ui_render_widget(&w, &ops);
    /* Labels without text should produce no draw_text calls */
    TEST_ASSERT_FALSE(has_call_type(DRAW_TEXT));
}

void test_render_label_empty_text_no_draw(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 60, 10);
    w.text = "";
    ui_render_widget(&w, &ops);
    TEST_ASSERT_FALSE(has_call_type(DRAW_TEXT));
}

/* ------------------------------------------------------------------ */
/* Box                                                                 */
/* ------------------------------------------------------------------ */

void test_render_box_draws_rect(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BOX, 5, 5, 30, 20);
    ui_render_widget(&w, &ops);
    /* Box should draw at least a rect or fill */
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Button                                                              */
/* ------------------------------------------------------------------ */

void test_render_button_draws_border_and_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 10, 5, 60, 14);
    w.text = "Click";
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Click"));
    /* Button draws a border (via fill_rect or draw_rect) */
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT) || has_call_type(DRAW_RECT));
}

void test_render_button_no_text_still_draws_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 10, 5, 60, 14);
    w.text = NULL;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT) || has_call_type(DRAW_RECT));
}

/* ------------------------------------------------------------------ */
/* Progressbar                                                         */
/* ------------------------------------------------------------------ */

void test_render_progressbar_zero(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 80, 10);
    w.value = 0;
    w.max_value = 100;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT) || has_call_type(DRAW_RECT));
}

void test_render_progressbar_full(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 80, 10);
    w.value = 100;
    w.max_value = 100;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

/* ------------------------------------------------------------------ */
/* Checkbox                                                            */
/* ------------------------------------------------------------------ */

void test_render_checkbox_unchecked(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 80, 12);
    w.text = "Option";
    w.checked = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Option"));
}

void test_render_checkbox_checked(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 80, 12);
    w.text = "Done";
    w.checked = 1;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Done"));
}

/* ------------------------------------------------------------------ */
/* Radiobutton                                                         */
/* ------------------------------------------------------------------ */

void test_render_radiobutton_selected(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_RADIOBUTTON, 0, 0, 80, 12);
    w.text = "Choice";
    w.checked = 1;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Choice"));
}

/* ------------------------------------------------------------------ */
/* Gauge                                                               */
/* ------------------------------------------------------------------ */

void test_render_gauge(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 40, 40);
    w.value = 50;
    w.min_value = 0;
    w.max_value = 100;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Slider                                                              */
/* ------------------------------------------------------------------ */

void test_render_slider(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 14);
    w.value = 25;
    w.min_value = 0;
    w.max_value = 100;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_render_slider_at_min(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 14);
    w.value = 0;
    w.min_value = 0;
    w.max_value = 100;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_render_slider_at_max(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 80, 14);
    w.value = 100;
    w.min_value = 0;
    w.max_value = 100;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Textbox                                                             */
/* ------------------------------------------------------------------ */

void test_render_textbox_with_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TEXTBOX, 0, 0, 120, 40);
    w.text = "Multi\nline\ntext";
    w.text_overflow = UI_TEXT_OVERFLOW_WRAP;
    w.max_lines = 3;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_TEXT));
}

void test_render_textbox_empty_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TEXTBOX, 0, 0, 120, 40);
    w.text = "";
    ui_render_widget(&w, &ops);
    /* Empty text should still draw the background */
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

/* ------------------------------------------------------------------ */
/* Panel                                                               */
/* ------------------------------------------------------------------ */

void test_render_panel(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PANEL, 0, 0, 100, 60);
    w.border = 1;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT) || has_call_type(DRAW_RECT));
}

/* ------------------------------------------------------------------ */
/* Chart                                                               */
/* ------------------------------------------------------------------ */

void test_render_chart(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 80, 40);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Scene tests                                                         */
/* ------------------------------------------------------------------ */

void test_render_scene_multiple_widgets(void)
{
    UiDrawOps ops = make_ops();
    UiWidget widgets[3];
    widgets[0] = make_widget(UIW_LABEL, 0, 0, 60, 10);
    widgets[0].text = "A";
    widgets[1] = make_widget(UIW_BUTTON, 0, 12, 60, 14);
    widgets[1].text = "B";
    widgets[2] = make_widget(UIW_BOX, 0, 28, 60, 20);

    UiScene scene = { .name = "multi", .width = 256, .height = 128,
                      .widget_count = 3, .widgets = widgets };
    ui_render_scene(&scene, &ops);
    TEST_ASSERT_TRUE(has_text_containing("A"));
    TEST_ASSERT_TRUE(has_text_containing("B"));
    TEST_ASSERT_TRUE(s_call_count >= 3);
}

void test_render_scene_skips_invisible(void)
{
    UiDrawOps ops = make_ops();
    UiWidget widgets[2];
    widgets[0] = make_widget(UIW_LABEL, 0, 0, 60, 10);
    widgets[0].text = "Visible";
    widgets[1] = make_widget(UIW_LABEL, 0, 12, 60, 10);
    widgets[1].text = "Hidden";
    widgets[1].visible = 0;

    UiScene scene = { .name = "vis", .width = 256, .height = 128,
                      .widget_count = 2, .widgets = widgets };
    ui_render_scene(&scene, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Visible"));
    TEST_ASSERT_FALSE(has_text_containing("Hidden"));
}

/* ------------------------------------------------------------------ */
/* Style tests                                                         */
/* ------------------------------------------------------------------ */

void test_render_highlighted_widget_draws(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 60, 14);
    w.text = "Hi";
    w.style = UI_STYLE_HIGHLIGHT;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Hi"));
}

void test_render_inverse_widget_draws(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 60, 14);
    w.text = "Inv";
    w.style = UI_STYLE_INVERSE;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Inv"));
}

void test_render_disabled_widget_still_draws(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BUTTON, 0, 0, 60, 14);
    w.text = "Dis";
    w.enabled = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("Dis"));
}

/* ------------------------------------------------------------------ */
/* Border style tests                                                  */
/* ------------------------------------------------------------------ */

void test_render_box_border_none(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BOX, 0, 0, 30, 20);
    w.border_style = UI_BORDER_NONE;
    ui_render_widget(&w, &ops);
    /* Should still render (the box fill), just no border lines */
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_render_box_border_double(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BOX, 0, 0, 30, 20);
    w.border_style = UI_BORDER_DOUBLE;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Unknown widget type draws default rect                              */
/* ------------------------------------------------------------------ */

void test_render_unknown_type_draws_rect(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 10, 10, 40, 20);
    w.type = 255; /* unknown — rejected by type bounds guard */
    ui_render_widget(&w, &ops);
    /* Out-of-range type is silently rejected, no draw calls */
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

/* ------------------------------------------------------------------ */
/* Minimal ops (only fill_rect, no other callbacks)                    */
/* ------------------------------------------------------------------ */

void test_render_with_minimal_ops(void)
{
    UiDrawOps ops;
    memset(&ops, 0, sizeof(ops));
    ops.fill_rect = cap_fill_rect;
    /* No draw_text, draw_rect, etc. */

    UiWidget w = make_widget(UIW_BOX, 0, 0, 30, 20);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ------------------------------------------------------------------ */
/* Zero-size widget                                                    */
/* ------------------------------------------------------------------ */

void test_render_zero_size_label(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_LABEL, 0, 0, 0, 0);
    w.text = "tiny";
    ui_render_widget(&w, &ops);
    /* Can't fit any text in zero-width widget */
    TEST_ASSERT_FALSE(has_call_type(DRAW_TEXT));
}

/* ------------------------------------------------------------------ */
/* Integer overflow safety — large value * span must not wrap          */
/* ------------------------------------------------------------------ */

void test_render_progressbar_large_range_no_overflow(void)
{
    UiDrawOps ops = make_ops();
    /* Use large min/max to stress the multiplication. */
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 200, 12);
    w.border = 1;
    w.min_value = -30000;
    w.max_value = 30000;
    w.value = 15000; /* 75 % of range */
    ui_render_widget(&w, &ops);
    /* Should produce a filled region without overflow artifacts. */
    int found_fill = 0;
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT && s_calls[i].w > 0 &&
            s_calls[i].w <= 198) {
            found_fill = 1;
        }
    }
    TEST_ASSERT_TRUE(found_fill);
}

void test_render_slider_large_range_no_overflow(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 200, 14);
    w.border = 1;
    w.min_value = -30000;
    w.max_value = 30000;
    w.value = 30000; /* max */
    ui_render_widget(&w, &ops);
    /* Knob should be at right edge, not wrapped negative. */
    int found_fill = 0;
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT && s_calls[i].x >= 0) {
            found_fill = 1;
        }
    }
    TEST_ASSERT_TRUE(found_fill);
}

void test_render_gauge_large_range_no_overflow(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 200, 12);
    w.border = 1;
    w.min_value = -30000;
    w.max_value = 30000;
    w.value = 0; /* 50 % of range */
    ui_render_widget(&w, &ops);
    int found_fill = 0;
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT && s_calls[i].w > 0 &&
            s_calls[i].w <= 198) {
            found_fill = 1;
        }
    }
    TEST_ASSERT_TRUE(found_fill);
}

void test_render_chart_large_range_no_overflow(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_CHART, 0, 0, 200, 60);
    w.border = 1;
    w.min_value = -30000;
    w.max_value = 30000;
    w.value = 25000;
    ui_render_widget(&w, &ops);
    /* Bars must have non-negative heights (no overflow wrap). */
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT) {
            TEST_ASSERT_TRUE(s_calls[i].h >= 0);
        }
    }
}

/* ------------------------------------------------------------------ */
/* Zero-dimension widget types — _draw_rect / _fill_rect guards       */
/* ------------------------------------------------------------------ */

void test_render_box_zero_width_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BOX, 10, 10, 0, 20);
    w.border = 1;
    ui_render_widget(&w, &ops);
    /* Must not crash; drawing with w=0 should be skipped. */
    TEST_ASSERT_TRUE(1);
}

void test_render_box_zero_height_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_BOX, 10, 10, 40, 0);
    w.border = 1;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}

void test_render_progressbar_tiny_no_crash(void)
{
    UiDrawOps ops = make_ops();
    /* Width=2 → inner_w=0 → early return. */
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 2, 2);
    w.border = 1;
    w.min_value = 0;
    w.max_value = 100;
    w.value = 50;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}

/* ------------------------------------------------------------------ */
/* Inverted range (min > max) edge cases — range is forced to 1        */
/* ------------------------------------------------------------------ */

void test_render_progressbar_inverted_range_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_PROGRESSBAR, 0, 0, 60, 10);
    w.border = 1;
    w.min_value = 100;
    w.max_value = 0; /* inverted */
    w.value = 50;
    ui_render_widget(&w, &ops);
    /* Should draw without crashing ("range <= 0" path sets range = 1). */
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_render_slider_inverted_range_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_SLIDER, 0, 0, 60, 14);
    w.border = 1;
    w.min_value = 200;
    w.max_value = -100; /* inverted, negative */
    w.value = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_render_gauge_inverted_range_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_GAUGE, 0, 0, 80, 14);
    w.border = 1;
    w.min_value = 50;
    w.max_value = 50; /* equal = range 0, forced to 1 */
    w.value = 50;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_render_checkbox_tiny_no_crash(void)
{
    UiDrawOps ops = make_ops();
    /* Height=2 → box=0, clamped to 2 → should still not crash. */
    UiWidget w = make_widget(UIW_CHECKBOX, 0, 0, 40, 2);
    w.checked = 1;
    w.text = "X";
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}

void test_render_icon_no_text_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 0, 0, 24, 24);
    w.text = NULL;
    ui_render_widget(&w, &ops);
    /* NULL text: icon falls through to text path with "?" */
    TEST_ASSERT_TRUE(1);
}

void test_render_icon_empty_text_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_ICON, 0, 0, 24, 24);
    w.text = "";
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}

void test_render_chart_tiny_no_crash(void)
{
    UiDrawOps ops = make_ops();
    /* Chart with inner_w=0 after subtracting borders → early return */
    UiWidget w = make_widget(UIW_CHART, 0, 0, 2, 2);
    w.border = 1;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}

void test_render_textbox_null_text_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_widget(UIW_TEXTBOX, 0, 0, 100, 40);
    w.text = NULL;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}
