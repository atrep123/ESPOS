#include "unity.h"

#include <string.h>
#include "ui_render.h"
#include "ui_scene.h"

/* ------------------------------------------------------------------ */
/* Draw-call capturing infrastructure (same pattern as test_ui_render) */
/* ------------------------------------------------------------------ */

#define CAP_MAX 16384

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

/* Helpers */
static int has_call_type(DrawCallType t)
{
    for (int i = 0; i < s_call_count; ++i)
        if (s_calls[i].type == t) return 1;
    return 0;
}

static int count_call_type(DrawCallType t)
{
    int n = 0;
    for (int i = 0; i < s_call_count; ++i)
        if (s_calls[i].type == t) n++;
    return n;
}

static int has_text_containing(const char *substr)
{
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_TEXT && strstr(s_calls[i].text, substr))
            return 1;
    }
    return 0;
}

static int all_coords_nonneg(void)
{
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT) {
            if (s_calls[i].w < 0 || s_calls[i].h < 0) return 0;
        }
    }
    return 1;
}

static UiWidget make_gauge(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                           int16_t val, int16_t min_v, int16_t max_v,
                           const char *text)
{
    UiWidget wgt;
    memset(&wgt, 0, sizeof(wgt));
    wgt.type = UIW_GAUGE;
    wgt.x = x; wgt.y = y;
    wgt.width = w; wgt.height = h;
    wgt.border = 1;
    wgt.value = val;
    wgt.min_value = min_v;
    wgt.max_value = max_v;
    wgt.text = text;
    wgt.visible = 1;
    wgt.enabled = 1;
    wgt.fg = 15;
    wgt.bg = 0;
    return wgt;
}

void setUp(void) { cap_reset(); }
void tearDown(void) {}

/* ================================================================== */
/* ARC MODE — Large gauge (>= 30px inner height)                      */
/* ================================================================== */

void test_gauge_arc_renders_draw_calls(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 50, 0, 100, "SPEED");
    ui_render_widget(&w, &ops);
    /* Arc mode produces many fill_rect calls for pixel drawing + text */
    TEST_ASSERT_TRUE(s_call_count > 20);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_gauge_arc_shows_value_text(void)
{
    UiDrawOps ops = make_ops();
    /* Use larger gauge to ensure value text fits and cap doesn't overflow */
    UiWidget w = make_gauge(0, 0, 80, 60, 72, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Normal arc mode shows value text */
    TEST_ASSERT_TRUE(has_text_containing("72"));
}

void test_gauge_arc_shows_label(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 80, 60, 50, 0, 100, "SPEED");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("SPEED"));
}

void test_gauge_arc_at_zero(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 0, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Should still render (inactive arc, no label/value text) */
    TEST_ASSERT_TRUE(s_call_count > 5);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_arc_at_max(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 100, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 5);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_arc_no_label_no_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 80, 60, 75, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* No label text, but value IS drawn in normal arc mode */
    TEST_ASSERT_TRUE(has_text_containing("75"));
    TEST_ASSERT_TRUE(s_call_count > 5);
}

void test_gauge_arc_value_clamped_above_max(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 200, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Value clamped to max — should not crash or overflow */
    TEST_ASSERT_TRUE(s_call_count > 5);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_arc_value_clamped_below_min(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, -50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 5);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_arc_negative_range(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 80, 60, -10, -30, 30, "TEMP");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("TEMP"));
    TEST_ASSERT_TRUE(s_call_count > 5);
}

/* ================================================================== */
/* COMPACT MODE — Small gauge (< 30px inner height, >= 5px radius)    */
/* ================================================================== */

void test_gauge_compact_no_value_text(void)
{
    /* Compact gauge (20px inner height): label below arc, no value text */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 44, 22, 45, 0, 100, "CPU");
    ui_render_widget(&w, &ops);
    /* Should NOT show value "45", only label "CPU" */
    TEST_ASSERT_TRUE(has_text_containing("CPU"));
    TEST_ASSERT_FALSE(has_text_containing("45"));
}

void test_gauge_compact_renders_arc(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 44, 22, 88, 0, 100, "MEM");
    ui_render_widget(&w, &ops);
    /* Compact arc still produces many draw calls */
    TEST_ASSERT_TRUE(s_call_count > 10);
}

void test_gauge_compact_no_label_fits_better(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 44, 22, 60, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Without label, compact gauge has more arc space */
    TEST_ASSERT_TRUE(s_call_count > 5);
    TEST_ASSERT_FALSE(has_call_type(DRAW_TEXT));
}

/* ================================================================== */
/* FALLBACK BAR — Tiny gauge (radius < 5 or viability check fails)    */
/* ================================================================== */

void test_gauge_tiny_falls_back_to_bar(void)
{
    /* 16x12: inner 14x10, too small for arc */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 16, 12, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Bar mode: bg fill + bar fill = few fill_rect calls */
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
    int fills = count_call_type(DRAW_FILL_RECT);
    /* Bar mode produces far fewer calls than arc mode */
    TEST_ASSERT_TRUE(fills < 20);
}

void test_gauge_tiny_with_label_stays_bar(void)
{
    /* Very small with label → compact fails viability → falls back to bar */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 16, 14, 50, 0, 100, "X");
    ui_render_widget(&w, &ops);
    /* Bar fallback with label text should still render text */
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_gauge_bar_zero_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 16, 12, 0, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Zero value → no filled portion beyond bg */
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_gauge_bar_full_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 16, 12, 100, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

/* ================================================================== */
/* EDGE CASES                                                         */
/* ================================================================== */

void test_gauge_zero_range(void)
{
    /* min == max → range forced to 1 */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 50, 50, 50, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_inverted_range(void)
{
    /* min > max → range forced to 1 */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 0, 100, 0, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_large_range_no_overflow(void)
{
    /* int64 math prevents overflow */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 200, 50, 0, -30000, 30000, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 1);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_minimal_inner_returns_early(void)
{
    /* width=2, height=2 → inner 0×0 → returns after border */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 2, 2, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Should draw bg + border but no gauge internals */
    int fills = count_call_type(DRAW_FILL_RECT);
    TEST_ASSERT_TRUE(fills <= 2);
}

void test_gauge_no_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 50, 0, 100, "NB");
    w.border = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_gauge_border_styles(void)
{
    /* Verify each border style doesn't crash */
    uint8_t styles[] = {
        UI_BORDER_SINGLE, UI_BORDER_DOUBLE, UI_BORDER_ROUNDED,
        UI_BORDER_BOLD, UI_BORDER_DASHED
    };
    for (int i = 0; i < 5; ++i) {
        cap_reset();
        UiDrawOps ops = make_ops();
        UiWidget w = make_gauge(0, 0, 60, 42, 50, 0, 100, NULL);
        w.border_style = styles[i];
        ui_render_widget(&w, &ops);
        TEST_ASSERT_TRUE(s_call_count > 0);
    }
}

void test_gauge_disabled_still_renders(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 50, 0, 100, "D");
    w.enabled = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_gauge_invisible_skipped(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 42, 50, 0, 100, "I");
    w.visible = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

void test_gauge_wide_short_uses_bar(void)
{
    /* Very wide but short — use height that forces bar with label */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 200, 14, 50, 0, 100, "X");
    /* inner_h=12 < 30 → compact, bottom_reserve=9, natural_gauge_h=3 < 5
     * → use_arc=0 → fallback bar */
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
    /* Bar mode produces far fewer calls than arc mode */
    TEST_ASSERT_TRUE(s_call_count < 100);
}

void test_gauge_arc_threshold_boundary(void)
{
    /* inner_h exactly 30 → not compact (compact = inner_h < 30) */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 80, 32, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Normal arc mode produces many draw calls */
    TEST_ASSERT_TRUE(s_call_count > 50);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

/* ================================================================== */
/* Additional edge cases                                               */
/* ================================================================== */

void test_gauge_arc_large_value_snprintf_no_crash(void)
{
    /* value=32767 (int16_t max) → snprintf produces "32767" (5 chars), fits vbuf[8] */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 80, 60, 32767, 0, 32767, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 5);
    TEST_ASSERT_TRUE(all_coords_nonneg());
    /* Verify the value text is rendered */
    TEST_ASSERT_TRUE(has_text_containing("32767"));
}

void test_gauge_zero_width_no_crash(void)
{
    /* width=0 → fill_rect no-op, border no-op, inner_w=-2 early return */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 0, 42, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* bg fill_rect(w=0) handled by guard; no gauge internals */
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_zero_height_no_crash(void)
{
    /* height=0 → inner_h=-2, early return */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 60, 0, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}

void test_gauge_bar_mode_draws_label_text(void)
{
    /* Bar fallback with text="BAR" → text should be rendered */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 40, 14, 50, 0, 100, "BAR");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("BAR"));
}

void test_gauge_compact_narrow_column(void)
{
    /* Compact mode: inner_w=6 (narrow) — very small radius */
    UiDrawOps ops = make_ops();
    UiWidget w = make_gauge(0, 0, 8, 22, 80, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Should render without crash; radius_check = 6/2-1 = 2 < 5 → bar fallback */
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_coords_nonneg());
}
