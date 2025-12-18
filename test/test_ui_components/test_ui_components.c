#include "unity.h"

#include <string.h>

#include "services/ui/ui_components.h"

typedef struct {
    int calls;
    int x[16];
    int y[16];
    int w[16];
    int h[16];
} DirtyCapture;

static void capture_dirty_add(void *ctx, int x, int y, int w, int h)
{
    DirtyCapture *cap = (DirtyCapture *)ctx;
    if (cap == NULL) {
        return;
    }
    if (cap->calls < (int)(sizeof(cap->x) / sizeof(cap->x[0]))) {
        cap->x[cap->calls] = x;
        cap->y[cap->calls] = y;
        cap->w[cap->calls] = w;
        cap->h[cap->calls] = h;
    }
    cap->calls += 1;
}

void setUp(void) {}
void tearDown(void) {}

void test_ui_components_prefix_visible_marks_dirty(void)
{
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "toast.panel";
    widgets[0].x = 1;
    widgets[0].y = 2;
    widgets[0].width = 10;
    widgets[0].height = 11;
    widgets[0].visible = 0;
    widgets[0].enabled = 1;

    widgets[1].id = "toast.message";
    widgets[1].x = 3;
    widgets[1].y = 4;
    widgets[1].width = 12;
    widgets[1].height = 13;
    widgets[1].visible = 0;
    widgets[1].enabled = 1;

    widgets[2].id = "other.panel";
    widgets[2].x = 5;
    widgets[2].y = 6;
    widgets[2].width = 14;
    widgets[2].height = 15;
    widgets[2].visible = 1;
    widgets[2].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 3,
        .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_set_prefix_visible(&scene, "toast", true, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(1, widgets[0].visible);
    TEST_ASSERT_EQUAL_UINT8(1, widgets[1].visible);
    TEST_ASSERT_EQUAL_UINT8(1, widgets[2].visible);
    TEST_ASSERT_EQUAL_INT(2, cap.calls);

    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(&scene, "toast", true, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_INT(2, cap.calls);

    TEST_ASSERT_TRUE(ui_components_set_prefix_visible(&scene, "toast", false, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].visible);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[1].visible);
    TEST_ASSERT_EQUAL_UINT8(1, widgets[2].visible);
    TEST_ASSERT_EQUAL_INT(4, cap.calls);
}

void test_ui_components_menu_active_sets_highlight(void)
{
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "menu.item0";
    widgets[0].style = (uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT);
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    widgets[1].id = "menu.item1";
    widgets[1].style = UI_STYLE_BOLD;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    widgets[2].id = "menu.title";
    widgets[2].style = 0;
    widgets[2].visible = 1;
    widgets[2].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 3,
        .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_menu_set_active(&scene, "menu", 1, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_BOLD, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8((uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT), widgets[1].style);
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
}

void test_ui_components_tabs_active_sets_highlight(void)
{
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "tabs.tab1";
    widgets[0].style = UI_STYLE_HIGHLIGHT;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    widgets[1].id = "tabs.tab2";
    widgets[1].style = 0;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    widgets[2].id = "tabs.tabbar";
    widgets[2].style = 0;
    widgets[2].visible = 1;
    widgets[2].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 3,
        .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_tabs_set_active(&scene, "tabs", 1, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_HIGHLIGHT, widgets[1].style);
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
}

void test_ui_components_sync_active_from_focus_updates_menu_highlight(void)
{
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "menu.item0";
    widgets[0].style = (uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT);
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    widgets[1].id = "menu.item1";
    widgets[1].style = UI_STYLE_BOLD;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    widgets[2].id = "menu.title";
    widgets[2].style = 0;
    widgets[2].visible = 1;
    widgets[2].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 3,
        .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_sync_active_from_focus(&scene, 1, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_BOLD, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8((uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT), widgets[1].style);
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
}

void test_ui_components_sync_active_from_focus_updates_tabs_highlight(void)
{
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "tabs.tab1";
    widgets[0].style = UI_STYLE_HIGHLIGHT;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    widgets[1].id = "tabs.tab2";
    widgets[1].style = 0;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    widgets[2].id = "tabs.content";
    widgets[2].style = 0;
    widgets[2].visible = 1;
    widgets[2].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 3,
        .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_sync_active_from_focus(&scene, 1, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_HIGHLIGHT, widgets[1].style);
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
}
