#include "unity.h"

#include <string.h>
#include "ui_render.h"
#include "ui_scene.h"

/* ------------------------------------------------------------------ */
/* Draw-call capturing infrastructure                                  */
/* ------------------------------------------------------------------ */

#define CAP_MAX 256

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

static int has_text_containing(const char *substr)
{
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_TEXT && strstr(s_calls[i].text, substr))
            return 1;
    }
    return 0;
}

static UiWidget make_icon(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                          const char *text)
{
    UiWidget wgt;
    memset(&wgt, 0, sizeof(wgt));
    wgt.type = UIW_ICON;
    wgt.x = x; wgt.y = y;
    wgt.width = w; wgt.height = h;
    wgt.border = 1;
    wgt.text = text;
    wgt.visible = 1;
    wgt.enabled = 1;
    wgt.fg = 15;
    wgt.bg = 0;
    wgt.align = UI_ALIGN_CENTER;
    wgt.valign = UI_VALIGN_MIDDLE;
    return wgt;
}

void setUp(void) { cap_reset(); }
void tearDown(void) {}

/* ================================================================== */
/* Text fallback (no HAVE_ICONS in native)                             */
/* ================================================================== */

void test_icon_text_fallback_renders_first_char(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "W");
    ui_render_widget(&w, &ops);
    /* Without HAVE_ICONS, falls back to rendering first char as text */
    TEST_ASSERT_TRUE(has_text_containing("W"));
}

void test_icon_null_text_renders_question_mark(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, NULL);
    ui_render_widget(&w, &ops);
    /* NULL text → "?" fallback */
    TEST_ASSERT_TRUE(has_text_containing("?"));
}

void test_icon_empty_text_renders_question_mark(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("?"));
}

void test_icon_with_border_renders_bg_and_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "X");
    w.border = 1;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_call_type(DRAW_FILL_RECT));
    TEST_ASSERT_TRUE(has_text_containing("X"));
}

void test_icon_no_border(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "A");
    w.border = 0;
    ui_render_widget(&w, &ops);
    /* Without border, text still renders */
    TEST_ASSERT_TRUE(has_text_containing("A"));
}

void test_icon_border_styles(void)
{
    uint8_t styles[] = {
        UI_BORDER_SINGLE, UI_BORDER_DOUBLE, UI_BORDER_ROUNDED,
        UI_BORDER_BOLD, UI_BORDER_DASHED
    };
    for (int i = 0; i < 5; ++i) {
        cap_reset();
        UiDrawOps ops = make_ops();
        UiWidget w = make_icon(0, 0, 24, 24, "B");
        w.border_style = styles[i];
        ui_render_widget(&w, &ops);
        TEST_ASSERT_TRUE(s_call_count > 0);
    }
}

/* ================================================================== */
/* Size edge cases                                                     */
/* ================================================================== */

void test_icon_tiny_no_text_fits(void)
{
    /* Height < CHAR_H → text doesn't fit, no text drawn */
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 6, 6, "T");
    ui_render_widget(&w, &ops);
    /* Too small for 8px-tall text */
    TEST_ASSERT_FALSE(has_call_type(DRAW_TEXT));
}

void test_icon_tall_enough_for_text(void)
{
    /* Exact minimum height for text: border(1) + pad(1) + 8 + pad(1) + border(1) = 12 */
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 12, 12, "M");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("M"));
}

void test_icon_zero_width(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 0, 24, "Z");
    ui_render_widget(&w, &ops);
    /* Zero width → text area has iw <= 0, no text */
    TEST_ASSERT_TRUE(1); /* no crash */
}

void test_icon_zero_height(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 0, "Z");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(1); /* no crash */
}

/* ================================================================== */
/* Visibility & state                                                  */
/* ================================================================== */

void test_icon_invisible_skipped(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "V");
    w.visible = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_EQUAL_INT(0, s_call_count);
}

void test_icon_disabled_still_renders(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "D");
    w.enabled = 0;
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_icon_long_text_uses_first_char(void)
{
    /* If text is "settings", only first char "s" is rendered */
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "settings");
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("s"));
    /* Should NOT show full "settings" */
    TEST_ASSERT_FALSE(has_text_containing("settings"));
}

/* ================================================================== */
/* Additional icon coverage                                            */
/* ================================================================== */

void test_icon_highlighted_renders(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "H");
    w.style = UI_STYLE_HIGHLIGHT;
    cap_reset();
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    /* Should still render text */
    TEST_ASSERT_TRUE(has_text_containing("H") || has_call_type(DRAW_BLIT_MONO));
}

void test_icon_custom_fg_bg(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "C");
    w.fg = 8;
    w.bg = 4;
    cap_reset();
    ui_render_widget(&w, &ops);
    /* Background fill should use bg color */
    int found_bg = 0;
    for (int i = 0; i < s_call_count; ++i) {
        if (s_calls[i].type == DRAW_FILL_RECT && s_calls[i].color == 4)
            found_bg = 1;
    }
    TEST_ASSERT_TRUE(found_bg);
}

void test_icon_at_offset_position(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(50, 30, 24, 24, "P");
    cap_reset();
    ui_render_widget(&w, &ops);
    /* All draw calls should be at x >= 50, y >= 30 */
    for (int i = 0; i < s_call_count; ++i) {
        TEST_ASSERT_TRUE(s_calls[i].x >= 50);
        TEST_ASSERT_TRUE(s_calls[i].y >= 30);
    }
}

void test_icon_no_border_no_rect(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "N");
    w.border = 0;
    cap_reset();
    ui_render_widget(&w, &ops);
    /* Should not have a rect border call */
    TEST_ASSERT_FALSE(has_call_type(DRAW_RECT));
}

void test_icon_single_char_text(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "X");
    cap_reset();
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(has_text_containing("X") || has_call_type(DRAW_BLIT_MONO));
}

/* ================================================================== */
/* Additional edge cases                                               */
/* ================================================================== */

void test_icon_inverse_style_renders(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, "I");
    w.style = UI_STYLE_INVERSE;
    cap_reset();
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(has_text_containing("I") || has_call_type(DRAW_BLIT_MONO));
}

void test_icon_large_offset_no_crash(void)
{
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(30000, 30000, 24, 24, "L");
    cap_reset();
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_icon_whitespace_text_renders(void)
{
    /* Space character as text — should render something */
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 24, 24, " ");
    cap_reset();
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
}

void test_icon_wide_narrow_aspect(void)
{
    /* Very wide, short icon */
    UiDrawOps ops = make_ops();
    UiWidget w = make_icon(0, 0, 100, 12, "W");
    cap_reset();
    ui_render_widget(&w, &ops);
    TEST_ASSERT_TRUE(s_call_count > 0);
    TEST_ASSERT_TRUE(has_text_containing("W"));
}

void test_icon_all_valign_options(void)
{
    uint8_t valigns[] = { UI_VALIGN_TOP, UI_VALIGN_MIDDLE, UI_VALIGN_BOTTOM };
    for (int i = 0; i < 3; ++i) {
        cap_reset();
        UiDrawOps ops = make_ops();
        UiWidget w = make_icon(0, 0, 24, 40, "V");
        w.valign = valigns[i];
        ui_render_widget(&w, &ops);
        TEST_ASSERT_TRUE(s_call_count > 0);
    }
}
