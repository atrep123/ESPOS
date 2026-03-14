#include "unity.h"

#include <string.h>
#include "ui_render.h"
#include "ui_scene.h"

/* ------------------------------------------------------------------ */
/* Draw-call capturing infrastructure                                  */
/* ------------------------------------------------------------------ */

#define CAP_MAX 8192

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

static int all_fills_nonneg_dims(void)
{
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT) {
            if (s_calls[i].w < 0 || s_calls[i].h < 0) return 0;
        }
    }
    return 1;
}

static UiWidget make_chart(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                           int16_t val, int16_t min_v, int16_t max_v,
                           const char *text)
{
    UiWidget wgt;
    memset(&wgt, 0, sizeof(wgt));
    wgt.type = UIW_CHART;
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
/* Basic rendering                                                     */
/* ================================================================== */

void test_chart_renders_bars_and_axes(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, "EQ");
    ui_render_widget(&w, &ops);
    /* Chart draws bg, border, axes, grid lines, bars */
    TEST_ASSERT_TRUE(s_call_count > 10);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
    /* Axes use hline/vline */
    TEST_ASSERT_TRUE(has_call_type(DRAW_HLINE));
    TEST_ASSERT_TRUE(has_call_type(DRAW_VLINE));
}

void test_chart_shows_label(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, "EQ");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("EQ"));
}

void test_chart_no_label(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_FALSE(has_call_type(DRAW_TEXT));
    /* Still renders bars */
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
}

void test_chart_bars_nonneg_dims(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

/* ================================================================== */
/* Value range edge cases                                              */
/* ================================================================== */

void test_chart_zero_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 0, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_max_value(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 100, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_negative_range(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, -10, -50, 50, "NEG");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_large_range_no_overflow(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 200, 60, 25000, -30000, 30000, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_zero_range(void)
{
    /* min == max → range forced to 1 */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 0, 0, 0, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_chart_inverted_range(void)
{
    /* min > max */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 100, 0, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

/* ================================================================== */
/* Size edge cases                                                     */
/* ================================================================== */

void test_chart_tiny_no_crash(void)
{
    /* 2×2 → inner 0×0 → early return */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 2, 2, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1);
}

void test_chart_small_inner_returns_early(void)
{
    /* inner < 8px → second early return */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 8, 8, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Should have bg fill + border at minimum, but no bars */
    int fills = count_call_type(DRAW_FILL_RECT);
    /* inner 6×6 < 8 requirement → returns early */
    TEST_ASSERT_TRUE(fills <= 3);
}

void test_chart_narrow_single_bar(void)
{
    /* Very narrow chart → should render at least 1 bar */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 20, 30, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 3);
}

void test_chart_wide_renders_bars(void)
{
    /* Wide chart → 6 bars fit easily */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 200, 60, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    /* Dithered bars use hline pixel calls + fill_rects for bg/cap */
    int fills = count_call_type(DRAW_FILL_RECT);
    int hlines = count_call_type(DRAW_HLINE);
    TEST_ASSERT_TRUE(fills + hlines > 50);
}

/* ================================================================== */
/* Styling & visibility                                                */
/* ================================================================== */

void test_chart_no_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, NULL);
    w.border = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_chart_border_styles(void)
{
    uint8_t styles[] = {
        UI_BORDER_SINGLE, UI_BORDER_DOUBLE, UI_BORDER_ROUNDED,
        UI_BORDER_BOLD, UI_BORDER_DASHED
    };
    for (int i = 0; i < 5; ++i) {
        cap_reset();
        UiDrawOps ops = make_ops();
        UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, NULL);
        w.border_style = styles[i];
        ui_render_widget(&w, &ops);
        TEST_ASSERT_TRUE(s_call_count > 0);
    }
}

void test_chart_disabled_still_renders(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, "D");
    w.enabled = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_chart_invisible_skipped(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, "I");
    w.visible = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

/* ================================================================== */
/* Additional edge cases                                               */
/* ================================================================== */

void test_chart_value_above_max(void)
{
    /* Value exceeds max_value — base clamped, no negative heights */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 200, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_value_below_min(void)
{
    /* Value below min_value — base < 0, clamped to 0 */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, -50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_empty_label_string(void)
{
    /* Empty (not NULL) text — should attempt to draw, not crash */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, "");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_chart_large_offset_coords(void)
{
    /* Chart at extreme coordinates — no crash, bars still nonneg */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(30000, 30000, 90, 42, 50, 0, 100, NULL);
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(all_fills_nonneg_dims());
}

void test_chart_no_border_no_rect(void)
{
    /* border=0 should skip border draw but still render bars */
    UiDrawOps ops = make_ops();
    UiWidget w = make_chart(0, 0, 90, 42, 50, 0, 100, NULL);
    w.border = 0;
    ui_render_widget(&w, &ops);
    int fills = count_call_type(DRAW_FILL_RECT);
    int rects = count_call_type(DRAW_RECT);
    /* Should have fill_rects (background + bars) but no border rects */
    TEST_ASSERT_TRUE(fills > 0);
    /* No explicit rect calls for border when border=0 */
    TEST_ASSERT_EQUAL_INT(0, rects);
}
