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

