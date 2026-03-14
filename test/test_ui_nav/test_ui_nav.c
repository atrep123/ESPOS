#include "unity.h"

#include <string.h>

#include "ui_nav.h"

void setUp(void) {}
void tearDown(void) {}

static UiScene make_scene(UiWidget *widgets, int count)
{
    UiScene s;
    memset(&s, 0, sizeof(s));
    s.name = "test";
    s.width = 128;
    s.height = 64;
    s.widget_count = (uint16_t)count;
    s.widgets = widgets;
    return s;
}

static void init_button(UiWidget *w, const char *id, int x, int y)
{
    memset(w, 0, sizeof(*w));
    w->type = UIW_BUTTON;
    w->x = (uint16_t)x;
    w->y = (uint16_t)y;
    w->width = 10;
    w->height = 10;
    w->id = id;
    w->visible = 1;
    w->enabled = 1;
}

void test_ui_nav_first_focus_in_rect_filters(void)
{
    UiWidget widgets[4];
    init_button(&widgets[0], "w0", 0, 0);
    init_button(&widgets[1], "w1", 20, 0);
    init_button(&widgets[2], "w2", 0, 20);
    init_button(&widgets[3], "w3", 20, 20);

    UiScene scene = make_scene(widgets, 4);

    TEST_ASSERT_EQUAL_INT(0, ui_nav_first_focus_in_rect(&scene, 0, 0, 15, 15));
    TEST_ASSERT_EQUAL_INT(1, ui_nav_first_focus_in_rect(&scene, 15, 0, 30, 15));
    TEST_ASSERT_EQUAL_INT(ui_nav_first_focus(&scene), ui_nav_first_focus_in_rect(&scene, 0, 0, 100, 100));
}

void test_ui_nav_move_focus_in_rect_cycles_inside_bounds(void)
{
    UiWidget widgets[4];
    init_button(&widgets[0], "w0", 0, 0);
    init_button(&widgets[1], "w1", 20, 0);
    init_button(&widgets[2], "w2", 0, 20);
    init_button(&widgets[3], "w3", 20, 20);

    UiScene scene = make_scene(widgets, 4);

    int bounds_x = 0;
    int bounds_y = 0;
    int bounds_w = 40;
    int bounds_h = 15;

    int next = ui_nav_move_focus_in_rect(&scene, 0, UI_NAV_DOWN, bounds_x, bounds_y, bounds_w, bounds_h);
    TEST_ASSERT_EQUAL_INT(1, next);
}

void test_ui_nav_move_focus_in_rect_from_outside_picks_first(void)
{
    UiWidget widgets[4];
    init_button(&widgets[0], "w0", 0, 0);
    init_button(&widgets[1], "w1", 20, 0);
    init_button(&widgets[2], "w2", 0, 20);
    init_button(&widgets[3], "w3", 20, 20);

    UiScene scene = make_scene(widgets, 4);

    int bounds_x = 0;
    int bounds_y = 0;
    int bounds_w = 40;
    int bounds_h = 15;

    int next = ui_nav_move_focus_in_rect(&scene, 2, UI_NAV_UP, bounds_x, bounds_y, bounds_w, bounds_h);
    TEST_ASSERT_EQUAL_INT(0, next);
}

/* --- ui_nav_is_focusable tests --- */

void test_is_focusable_null_returns_false(void)
{
    TEST_ASSERT_FALSE(ui_nav_is_focusable(NULL));
}

void test_is_focusable_button_returns_true(void)
{
    UiWidget w;
    init_button(&w, "b", 0, 0);
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_label_returns_false(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

void test_is_focusable_checkbox_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_CHECKBOX;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_radiobutton_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_RADIOBUTTON;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_slider_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_SLIDER;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_invisible_button_returns_false(void)
{
    UiWidget w;
    init_button(&w, "b", 0, 0);
    w.visible = 0;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

void test_is_focusable_disabled_button_returns_false(void)
{
    UiWidget w;
    init_button(&w, "b", 0, 0);
    w.enabled = 0;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

void test_is_focusable_panel_returns_false(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_PANEL;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

void test_is_focusable_box_returns_false(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_BOX;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

/* --- ui_nav_first_focus tests --- */

void test_first_focus_null_scene_returns_neg1(void)
{
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_first_focus(NULL));
}

void test_first_focus_empty_scene_returns_neg1(void)
{
    UiScene s = make_scene(NULL, 0);
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_first_focus(&s));
}

void test_first_focus_single_button(void)
{
    UiWidget w;
    init_button(&w, "b0", 10, 20);
    UiScene s = make_scene(&w, 1);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_first_focus(&s));
}

void test_first_focus_picks_top_left(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 50, 50);
    init_button(&widgets[1], "b1", 10, 10);
    init_button(&widgets[2], "b2", 30, 10);
    UiScene s = make_scene(widgets, 3);
    /* b1 at (10,10) is top-left */
    TEST_ASSERT_EQUAL_INT(1, ui_nav_first_focus(&s));
}

void test_first_focus_no_focusables_returns_neg1(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LABEL;
    w.visible = 1;
    w.enabled = 1;
    UiScene s = make_scene(&w, 1);
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_first_focus(&s));
}

void test_first_focus_same_y_picks_leftmost(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "b0", 40, 5);
    init_button(&widgets[1], "b1", 10, 5);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_first_focus(&s));
}

/* --- ui_nav_cycle_focus tests --- */

void test_cycle_focus_forward(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    init_button(&widgets[1], "b1", 20, 0);
    init_button(&widgets[2], "b2", 40, 0);
    UiScene s = make_scene(widgets, 3);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_cycle_focus(&s, 0, 1));
}

void test_cycle_focus_backward(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    init_button(&widgets[1], "b1", 20, 0);
    init_button(&widgets[2], "b2", 40, 0);
    UiScene s = make_scene(widgets, 3);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_cycle_focus(&s, 1, -1));
}

void test_cycle_focus_wraps_forward(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    init_button(&widgets[1], "b1", 20, 0);
    init_button(&widgets[2], "b2", 40, 0);
    UiScene s = make_scene(widgets, 3);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_cycle_focus(&s, 2, 1));
}

void test_cycle_focus_wraps_backward(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    init_button(&widgets[1], "b1", 20, 0);
    init_button(&widgets[2], "b2", 40, 0);
    UiScene s = make_scene(widgets, 3);
    TEST_ASSERT_EQUAL_INT(2, ui_nav_cycle_focus(&s, 0, -1));
}

void test_cycle_focus_invalid_current_returns_first(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "b0", 10, 10);
    init_button(&widgets[1], "b1", 30, 10);
    UiScene s = make_scene(widgets, 2);
    /* index -1 is invalid → returns first focus */
    TEST_ASSERT_EQUAL_INT(0, ui_nav_cycle_focus(&s, -1, 1));
}

void test_cycle_focus_null_scene_returns_neg1(void)
{
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_cycle_focus(NULL, 0, 1));
}

void test_cycle_focus_skips_non_focusable(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    memset(&widgets[1], 0, sizeof(widgets[1]));
    widgets[1].type = UIW_LABEL;
    widgets[1].x = 20; widgets[1].y = 0;
    widgets[1].visible = 1; widgets[1].enabled = 1;
    init_button(&widgets[2], "b2", 40, 0);
    UiScene s = make_scene(widgets, 3);
    /* Forward from b0 should skip label and land on b2 */
    TEST_ASSERT_EQUAL_INT(2, ui_nav_cycle_focus(&s, 0, 1));
}

void test_cycle_focus_single_widget_stays(void)
{
    UiWidget w;
    init_button(&w, "b0", 5, 5);
    UiScene s = make_scene(&w, 1);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_cycle_focus(&s, 0, 1));
}

/* --- ui_nav_move_focus tests --- */

void test_move_focus_down_beam(void)
{
    /* Two widgets vertically aligned (beam = x overlap) */
    UiWidget widgets[2];
    init_button(&widgets[0], "top", 20, 0);
    init_button(&widgets[1], "bot", 20, 30);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 0, UI_NAV_DOWN));
}

void test_move_focus_up_beam(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "top", 20, 0);
    init_button(&widgets[1], "bot", 20, 30);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 1, UI_NAV_UP));
}

void test_move_focus_right_beam(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "left", 0, 20);
    init_button(&widgets[1], "right", 40, 20);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 0, UI_NAV_RIGHT));
}

void test_move_focus_left_beam(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "left", 0, 20);
    init_button(&widgets[1], "right", 40, 20);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 1, UI_NAV_LEFT));
}

void test_move_focus_loose_fallback_diagonal(void)
{
    /* Two widgets: no beam overlap (different row & column) → loose fallback */
    UiWidget widgets[2];
    init_button(&widgets[0], "tl", 0, 0);
    init_button(&widgets[1], "br", 60, 40);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 0, UI_NAV_DOWN));
}

void test_move_focus_no_candidate_wraps(void)
{
    /* Grid of 2 buttons, moving DOWN from bottom → wraps to top */
    UiWidget widgets[2];
    init_button(&widgets[0], "top", 20, 0);
    init_button(&widgets[1], "bot", 20, 30);
    UiScene s = make_scene(widgets, 2);
    /* From bottom, moving DOWN: no candidate below → cycle wraps to top */
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 1, UI_NAV_DOWN));
}

void test_move_focus_2x2_grid(void)
{
    UiWidget widgets[4];
    init_button(&widgets[0], "tl", 0, 0);
    init_button(&widgets[1], "tr", 30, 0);
    init_button(&widgets[2], "bl", 0, 30);
    init_button(&widgets[3], "br", 30, 30);
    UiScene s = make_scene(widgets, 4);

    /* From top-left, RIGHT → top-right */
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 0, UI_NAV_RIGHT));
    /* From top-left, DOWN → bottom-left */
    TEST_ASSERT_EQUAL_INT(2, ui_nav_move_focus(&s, 0, UI_NAV_DOWN));
    /* From bottom-right, LEFT → bottom-left */
    TEST_ASSERT_EQUAL_INT(2, ui_nav_move_focus(&s, 3, UI_NAV_LEFT));
    /* From bottom-right, UP → top-right */
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 3, UI_NAV_UP));
}

void test_move_focus_null_scene_returns_neg1(void)
{
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_move_focus(NULL, 0, UI_NAV_DOWN));
}

void test_move_focus_invalid_current_returns_first(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "b0", 10, 10);
    init_button(&widgets[1], "b1", 50, 10);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, -1, UI_NAV_RIGHT));
}

void test_move_focus_beam_prefers_closer(void)
{
    /* Three widgets in a column; from top, DOWN should pick middle (closer) */
    UiWidget widgets[3];
    init_button(&widgets[0], "top", 20, 0);
    init_button(&widgets[1], "mid", 20, 20);
    init_button(&widgets[2], "far", 20, 60);
    UiScene s = make_scene(widgets, 3);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 0, UI_NAV_DOWN));
}

void test_first_focus_in_rect_null_scene(void)
{
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_first_focus_in_rect(NULL, 0, 0, 100, 100));
}

void test_move_focus_in_rect_null_scene(void)
{
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_move_focus_in_rect(NULL, 0, UI_NAV_DOWN, 0, 0, 100, 100));
}

void test_first_focus_in_rect_empty_rect_returns_neg1(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "b0", 50, 50);
    init_button(&widgets[1], "b1", 80, 50);
    UiScene s = make_scene(widgets, 2);
    /* Rect that covers nothing (0,0,1,1) while widgets are at 50,50+ */
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_first_focus_in_rect(&s, 0, 0, 1, 1));
}

void test_cycle_focus_delta_zero_stays(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "b0", 0, 0);
    init_button(&widgets[1], "b1", 20, 0);
    UiScene s = make_scene(widgets, 2);
    /* delta=0 should return first focus (same behavior as invalid) */
    int result = ui_nav_cycle_focus(&s, 0, 0);
    /* With delta=0 the cycle logic may return first or current; just ensure no crash */
    TEST_ASSERT_TRUE(result >= -1 && result < 2);
}

/* --- move_focus_in_rect directional tests --- */

void test_move_focus_in_rect_right(void)
{
    /* 2x2 grid inside a rect; RIGHT from top-left → top-right */
    UiWidget widgets[4];
    init_button(&widgets[0], "tl", 10, 10);
    init_button(&widgets[1], "tr", 40, 10);
    init_button(&widgets[2], "bl", 10, 40);
    init_button(&widgets[3], "br", 40, 40);
    UiScene s = make_scene(widgets, 4);
    int next = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_RIGHT, 0, 0, 60, 60);
    TEST_ASSERT_EQUAL_INT(1, next);
}

void test_move_focus_in_rect_left(void)
{
    /* 2x2 grid inside a rect; LEFT from top-right → top-left */
    UiWidget widgets[4];
    init_button(&widgets[0], "tl", 10, 10);
    init_button(&widgets[1], "tr", 40, 10);
    init_button(&widgets[2], "bl", 10, 40);
    init_button(&widgets[3], "br", 40, 40);
    UiScene s = make_scene(widgets, 4);
    int next = ui_nav_move_focus_in_rect(&s, 1, UI_NAV_LEFT, 0, 0, 60, 60);
    TEST_ASSERT_EQUAL_INT(0, next);
}

void test_move_focus_in_rect_up(void)
{
    /* 2x2 grid inside a rect; UP from bottom-left → top-left */
    UiWidget widgets[4];
    init_button(&widgets[0], "tl", 10, 10);
    init_button(&widgets[1], "tr", 40, 10);
    init_button(&widgets[2], "bl", 10, 40);
    init_button(&widgets[3], "br", 40, 40);
    UiScene s = make_scene(widgets, 4);
    int next = ui_nav_move_focus_in_rect(&s, 2, UI_NAV_UP, 0, 0, 60, 60);
    TEST_ASSERT_EQUAL_INT(0, next);
}

void test_move_focus_in_rect_down(void)
{
    /* 2x2 grid inside a rect; DOWN from top-left → bottom-left */
    UiWidget widgets[4];
    init_button(&widgets[0], "tl", 10, 10);
    init_button(&widgets[1], "tr", 40, 10);
    init_button(&widgets[2], "bl", 10, 40);
    init_button(&widgets[3], "br", 40, 40);
    UiScene s = make_scene(widgets, 4);
    int next = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_DOWN, 0, 0, 60, 60);
    TEST_ASSERT_EQUAL_INT(2, next);
}

void test_move_focus_in_rect_wraps_forward(void)
{
    /* Two buttons in a vertical column inside rect; DOWN from bottom wraps to top */
    UiWidget widgets[2];
    init_button(&widgets[0], "top", 10, 10);
    init_button(&widgets[1], "bot", 10, 40);
    UiScene s = make_scene(widgets, 2);
    int next = ui_nav_move_focus_in_rect(&s, 1, UI_NAV_DOWN, 0, 0, 60, 60);
    TEST_ASSERT_EQUAL_INT(0, next);
}

void test_move_focus_in_rect_wraps_backward(void)
{
    /* Two buttons in a vertical column inside rect; UP from top wraps to bottom */
    UiWidget widgets[2];
    init_button(&widgets[0], "top", 10, 10);
    init_button(&widgets[1], "bot", 10, 40);
    UiScene s = make_scene(widgets, 2);
    int next = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_UP, 0, 0, 60, 60);
    TEST_ASSERT_EQUAL_INT(1, next);
}

void test_move_focus_in_rect_excludes_outside(void)
{
    /* Widget outside rect must not be navigated to */
    UiWidget widgets[3];
    init_button(&widgets[0], "inside1", 10, 10);
    init_button(&widgets[1], "outside", 80, 10);  /* outside rect */
    init_button(&widgets[2], "inside2", 10, 30);
    UiScene s = make_scene(widgets, 3);
    /* RIGHT from inside1: outside widget excluded, wraps within rect */
    int next = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_RIGHT, 0, 0, 50, 50);
    TEST_ASSERT(next == 0 || next == 2);  /* must not be 1 (outside) */
}

void test_move_focus_left_wraps(void)
{
    /* Two buttons horizontally; LEFT from leftmost wraps to right */
    UiWidget widgets[2];
    init_button(&widgets[0], "left", 0, 20);
    init_button(&widgets[1], "right", 50, 20);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 0, UI_NAV_LEFT));
}

void test_move_focus_right_wraps(void)
{
    /* Two buttons horizontally; RIGHT from rightmost wraps to left */
    UiWidget widgets[2];
    init_button(&widgets[0], "left", 0, 20);
    init_button(&widgets[1], "right", 50, 20);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 1, UI_NAV_RIGHT));
}

void test_move_focus_invalid_dir_above_range(void)
{
    /* dir=4 is out of range (UI_NAV_RIGHT=3); should return current_idx */
    UiWidget widgets[2];
    init_button(&widgets[0], "a", 0, 0);
    init_button(&widgets[1], "b", 30, 0);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 0, (ui_nav_dir_t)4));
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 1, (ui_nav_dir_t)255));
}

void test_move_focus_invalid_dir_negative(void)
{
    /* Negative dir cast to enum should return current_idx */
    UiWidget widgets[2];
    init_button(&widgets[0], "a", 0, 0);
    init_button(&widgets[1], "b", 30, 0);
    UiScene s = make_scene(widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 1, (ui_nav_dir_t)-1));
}

void test_cycle_focus_many_focusables_no_crash(void)
{
    /* 140 focusable buttons — exceeds the internal order[128] cap.
       Cycling must still work on the first 128 without crashing. */
    UiWidget widgets[140];
    for (int i = 0; i < 140; ++i) {
        char id[4];
        id[0] = (char)('A' + (i / 26));
        id[1] = (char)('a' + (i % 26));
        id[2] = '\0';
        init_button(&widgets[i], id, (i % 20) * 10, (i / 20) * 10);
    }
    UiScene s = make_scene(widgets, 140);

    int first = ui_nav_first_focus(&s);
    TEST_ASSERT(first >= 0);

    /* Cycle forward through all — must not crash */
    int cur = first;
    for (int i = 0; i < 130; ++i) {
        cur = ui_nav_cycle_focus(&s, cur, 1);
        TEST_ASSERT(cur >= 0);
    }
    /* Cycle backward */
    for (int i = 0; i < 130; ++i) {
        cur = ui_nav_cycle_focus(&s, cur, -1);
        TEST_ASSERT(cur >= 0);
    }
}

/* ------------------------------------------------------------------ */
/* Additional edge-case tests                                         */
/* ------------------------------------------------------------------ */

void test_move_focus_all_non_focusable(void)
{
    /* All widgets are labels (non-focusable) — move_focus falls back to
       first_focus which returns -1 when nothing is focusable. */
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));
    for (int i = 0; i < 3; ++i) {
        widgets[i].type = UIW_LABEL;
        widgets[i].x = (uint16_t)(i * 30);
        widgets[i].y = 0;
        widgets[i].width = 20;
        widgets[i].height = 10;
        widgets[i].id = "lbl";
        widgets[i].visible = 1;
        widgets[i].enabled = 1;
    }
    UiScene s = make_scene(widgets, 3);

    TEST_ASSERT_EQUAL_INT(-1, ui_nav_move_focus(&s, 0, UI_NAV_RIGHT));
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_move_focus(&s, 1, UI_NAV_LEFT));
}

void test_move_focus_overlapping_widgets(void)
{
    /* Two buttons at the exact same position — move_focus should still work */
    UiWidget widgets[3];
    init_button(&widgets[0], "a", 0, 0);
    init_button(&widgets[1], "b", 0, 0);   /* overlapping with a */
    init_button(&widgets[2], "c", 50, 0);
    UiScene s = make_scene(widgets, 3);

    /* From a, moving right should reach c (skipping overlapping b) */
    int result = ui_nav_move_focus(&s, 0, UI_NAV_RIGHT);
    TEST_ASSERT(result == 1 || result == 2);  /* either b or c is valid */
}

void test_move_focus_3x3_grid(void)
{
    /* 3×3 grid of buttons, 20px spacing:
         [0] [1] [2]
         [3] [4] [5]
         [6] [7] [8]   */
    UiWidget widgets[9];
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            char id[4];
            id[0] = (char)('0' + r * 3 + c);
            id[1] = '\0';
            init_button(&widgets[r * 3 + c], id, c * 20, r * 20);
        }
    }
    UiScene s = make_scene(widgets, 9);

    /* Center widget is [4]. Check all four directions. */
    TEST_ASSERT_EQUAL_INT(1, ui_nav_move_focus(&s, 4, UI_NAV_UP));
    TEST_ASSERT_EQUAL_INT(7, ui_nav_move_focus(&s, 4, UI_NAV_DOWN));
    TEST_ASSERT_EQUAL_INT(3, ui_nav_move_focus(&s, 4, UI_NAV_LEFT));
    TEST_ASSERT_EQUAL_INT(5, ui_nav_move_focus(&s, 4, UI_NAV_RIGHT));
}

void test_cycle_focus_large_delta(void)
{
    /* cycle_focus delta sign determines direction (+fwd, –bwd), magnitude
       is ignored — always steps by 1 in sorted order. */
    UiWidget widgets[5];
    for (int i = 0; i < 5; ++i) {
        init_button(&widgets[i], "w", i * 15, 0);
    }
    UiScene s = make_scene(widgets, 5);

    /* delta=3 → forward by 1 */
    int cur = ui_nav_cycle_focus(&s, 0, 3);
    TEST_ASSERT_EQUAL_INT(1, cur);

    /* delta=-2 → backward by 1 */
    cur = ui_nav_cycle_focus(&s, 3, -2);
    TEST_ASSERT_EQUAL_INT(2, cur);
}

/* ================================================================== */
/* Integer overflow stress tests (int64_t scoring)                     */
/* ================================================================== */

void test_move_focus_large_coords_no_overflow(void)
{
    /* Widgets at max uint16_t positions — dx*dx would overflow int32.
       With int64_t scoring this must not wrap or produce wrong results. */
    UiWidget widgets[3];
    init_button(&widgets[0], "a", 0, 0);
    widgets[0].width = 10;
    widgets[0].height = 10;
    init_button(&widgets[1], "b", 60000, 0);    /* far right */
    widgets[1].width = 10;
    widgets[1].height = 10;
    init_button(&widgets[2], "c", 30000, 0);    /* middle */
    widgets[2].width = 10;
    widgets[2].height = 10;
    UiScene s = make_scene(widgets, 3);
    s.width = 65535;

    /* From a (x=0), moving right should pick c (x=30000) as closer
       than b (x=60000). Without int64_t, both would overflow. */
    int result = ui_nav_move_focus(&s, 0, UI_NAV_RIGHT);
    TEST_ASSERT_EQUAL_INT(2, result);
}

void test_move_focus_extreme_diagonal_no_overflow(void)
{
    /* Diagonal case: dx=60000, dy=60000 → dx*dx+dy*dy = 7.2e9 > INT32_MAX */
    UiWidget widgets[2];
    init_button(&widgets[0], "a", 0, 0);
    widgets[0].width = 10;
    widgets[0].height = 10;
    init_button(&widgets[1], "b", 60000, 60000);
    widgets[1].width = 10;
    widgets[1].height = 10;
    UiScene s = make_scene(widgets, 2);
    s.width = 65535;
    s.height = 65535;

    /* Should not crash and should pick widget 1 as only option going down-right */
    int result = ui_nav_move_focus(&s, 0, UI_NAV_DOWN);
    TEST_ASSERT_EQUAL_INT(1, result);
}

void test_move_focus_in_rect_large_coords_no_overflow(void)
{
    /* Same as above but via move_focus_in_rect path */
    UiWidget widgets[3];
    init_button(&widgets[0], "a", 100, 100);
    widgets[0].width = 10;
    widgets[0].height = 10;
    init_button(&widgets[1], "b", 60000, 100);
    widgets[1].width = 10;
    widgets[1].height = 10;
    init_button(&widgets[2], "c", 30000, 100);
    widgets[2].width = 10;
    widgets[2].height = 10;
    UiScene s = make_scene(widgets, 3);
    s.width = 65535;

    int result = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_RIGHT, 0, 0, 65535, 65535);
    TEST_ASSERT_EQUAL_INT(2, result);
}

void test_first_focus_in_rect_zero_size(void)
{
    /* Zero-size rect should find nothing useful → fallback behavior */
    UiWidget widgets[2];
    init_button(&widgets[0], "a", 10, 10);
    init_button(&widgets[1], "b", 50, 50);
    UiScene s = make_scene(widgets, 2);

    int result = ui_nav_first_focus_in_rect(&s, 0, 0, 0, 0);
    /* With zero-size rect no widget fits, result should be -1 or fallback */
    TEST_ASSERT(result >= -1 && result < 2);
}

void test_move_focus_single_widget(void)
{
    /* Only one focusable widget — move_focus returns it regardless of direction */
    UiWidget widgets[1];
    init_button(&widgets[0], "solo", 10, 10);
    UiScene s = make_scene(widgets, 1);

    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 0, UI_NAV_UP));
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 0, UI_NAV_DOWN));
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 0, UI_NAV_LEFT));
    TEST_ASSERT_EQUAL_INT(0, ui_nav_move_focus(&s, 0, UI_NAV_RIGHT));
}

/* ------------------------------------------------------------------ */
/* Round 9 additions                                                   */
/* ------------------------------------------------------------------ */

void test_is_focusable_textbox_returns_false(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_TEXTBOX;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

void test_first_focus_all_disabled_returns_neg1(void)
{
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    init_button(&widgets[1], "b1", 20, 0);
    init_button(&widgets[2], "b2", 40, 0);
    widgets[0].enabled = 0;
    widgets[1].enabled = 0;
    widgets[2].enabled = 0;
    UiScene s = make_scene(widgets, 3);
    TEST_ASSERT_EQUAL_INT(-1, ui_nav_first_focus(&s));
}

void test_cycle_focus_backward_skips_nonfocusable(void)
{
    /* Layout: button, label, button — backward from idx 2 should skip label */
    UiWidget widgets[3];
    init_button(&widgets[0], "b0", 0, 0);
    memset(&widgets[1], 0, sizeof(widgets[1]));
    widgets[1].type = UIW_LABEL;
    widgets[1].x = 20;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;
    init_button(&widgets[2], "b2", 40, 0);
    UiScene s = make_scene(widgets, 3);

    int next = ui_nav_cycle_focus(&s, 2, -1);
    TEST_ASSERT_EQUAL_INT(0, next);
}

void test_move_focus_up_from_top_wraps(void)
{
    /* Two buttons stacked vertically — UP from top should wrap to bottom */
    UiWidget widgets[2];
    init_button(&widgets[0], "top", 10, 0);
    init_button(&widgets[1], "bot", 10, 40);
    UiScene s = make_scene(widgets, 2);

    int next = ui_nav_move_focus(&s, 0, UI_NAV_UP);
    TEST_ASSERT_EQUAL_INT(1, next);
}

void test_move_focus_in_rect_single_widget_stays(void)
{
    /* Only one button inside the rect — moving in any direction returns it */
    UiWidget widgets[2];
    init_button(&widgets[0], "in", 5, 5);
    init_button(&widgets[1], "out", 100, 100);
    UiScene s = make_scene(widgets, 2);

    int r = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_RIGHT, 0, 0, 30, 30);
    TEST_ASSERT_EQUAL_INT(0, r);
    r = ui_nav_move_focus_in_rect(&s, 0, UI_NAV_DOWN, 0, 0, 30, 30);
    TEST_ASSERT_EQUAL_INT(0, r);
}

void test_move_focus_all_same_position(void)
{
    /* All buttons at exact same coordinates — tie-breaking */
    UiWidget widgets[3];
    init_button(&widgets[0], "a", 10, 10);
    init_button(&widgets[1], "b", 10, 10);
    init_button(&widgets[2], "c", 10, 10);
    UiScene s = make_scene(widgets, 3);

    int r = ui_nav_move_focus(&s, 0, UI_NAV_RIGHT);
    TEST_ASSERT(r >= 0 && r < 3);
}

void test_cycle_focus_empty_scene(void)
{
    UiScene s = make_scene(NULL, 0);
    s.widgets = NULL;
    int r = ui_nav_cycle_focus(&s, 0, 1);
    TEST_ASSERT_EQUAL_INT(-1, r);
}

void test_first_focus_empty_scene(void)
{
    UiScene s = make_scene(NULL, 0);
    s.widgets = NULL;
    int r = ui_nav_first_focus(&s);
    TEST_ASSERT_EQUAL_INT(-1, r);
}

void test_move_focus_negative_current_idx(void)
{
    UiWidget widgets[2];
    init_button(&widgets[0], "a", 0, 0);
    init_button(&widgets[1], "b", 50, 0);
    UiScene s = make_scene(widgets, 2);

    /* -1 as current_idx (no current selection) */
    int r = ui_nav_move_focus(&s, -1, UI_NAV_RIGHT);
    TEST_ASSERT(r >= 0 && r < 2);
}

/* ------------------------------------------------------------------ */
/* New focusable widget types                                          */
/* ------------------------------------------------------------------ */

void test_is_focusable_list_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_LIST;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_toggle_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_TOGGLE;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_gauge_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_GAUGE;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_progressbar_returns_true(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_PROGRESSBAR;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_TRUE(ui_nav_is_focusable(&w));
}

void test_is_focusable_icon_returns_false(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_ICON;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}

void test_is_focusable_chart_returns_false(void)
{
    UiWidget w;
    memset(&w, 0, sizeof(w));
    w.type = UIW_CHART;
    w.visible = 1;
    w.enabled = 1;
    TEST_ASSERT_FALSE(ui_nav_is_focusable(&w));
}
