#include "unity.h"

#include <limits.h>
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

/* ---------------------------------------------------------------------------
 * Edge case tests for ui_components
 * ------------------------------------------------------------------------ */

void test_ui_components_null_scene(void)
{
    /* NULL scene returns false without crash */
    TEST_ASSERT_FALSE(ui_components_menu_set_active(NULL, "menu", 0, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_tabs_set_active(NULL, "tabs", 0, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(NULL, "pfx", true, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(NULL, 0, NULL, NULL));
}

void test_ui_components_null_root(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item0";
    widgets[0].style = 0;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* NULL root → false */
    TEST_ASSERT_FALSE(ui_components_menu_set_active(&scene, NULL, 0, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_menu_set_active(&scene, "", 0, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(&scene, NULL, true, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(&scene, "", true, NULL, NULL));
}

void test_ui_components_sync_no_dot_in_id(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "nodothere";
    widgets[0].style = 0;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* No dot → sync returns false */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}

void test_ui_components_sync_invalid_focus_idx(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item0";
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* Negative index */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, -1, NULL, NULL));
    /* Out of bounds */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 5, NULL, NULL));
}

void test_ui_components_sync_null_widget_id(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = NULL;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* NULL id → returns false */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}

void test_ui_components_sync_unknown_role(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "grp.unknownrole";
    widgets[0].style = 0;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* Unknown role after dot → returns false */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}

void test_ui_components_menu_no_dirty_fn(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item0";
    widgets[0].style = UI_STYLE_HIGHLIGHT;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;
    widgets[1].id = "menu.item1";
    widgets[1].style = 0;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 2,
        .widgets = widgets,
    };

    /* dirty_add = NULL should still work, just no callbacks */
    TEST_ASSERT_TRUE(ui_components_menu_set_active(&scene, "menu", 1, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_HIGHLIGHT, widgets[1].style);
}

void test_ui_components_prefix_visible_null_widget_ids(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = NULL;  /* NULL id should be skipped safely */
    widgets[0].visible = 0;
    widgets[0].enabled = 1;
    widgets[1].id = "toast.msg";
    widgets[1].visible = 0;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 2,
        .widgets = widgets,
    };

    TEST_ASSERT_TRUE(ui_components_set_prefix_visible(&scene, "toast", true, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].visible);  /* NULL id skipped */
    TEST_ASSERT_EQUAL_UINT8(1, widgets[1].visible);
}

void test_ui_components_list_set_active(void)
{
    UiWidget widgets[3];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "mylist.item0";
    widgets[0].style = (uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT);
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    widgets[1].id = "mylist.item1";
    widgets[1].style = UI_STYLE_BOLD;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    widgets[2].id = "mylist.title";
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

    TEST_ASSERT_TRUE(ui_components_list_set_active(&scene, "mylist", 1, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_BOLD, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8((uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT), widgets[1].style);
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
}

void test_ui_components_menu_no_match_returns_false(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "other.item0";
    widgets[0].style = 0;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* No widgets matching "menu" prefix → returns false */
    TEST_ASSERT_FALSE(ui_components_menu_set_active(&scene, "menu", 0, NULL, NULL));
}

void test_ui_components_tabs_out_of_range_clears_all(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));

    widgets[0].id = "tabs.tab1";
    widgets[0].style = UI_STYLE_HIGHLIGHT;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    widgets[1].id = "tabs.tab2";
    widgets[1].style = 0;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 2,
        .widgets = widgets,
    };

    /* Selecting index 99 → clears all highlights */
    TEST_ASSERT_TRUE(ui_components_tabs_set_active(&scene, "tabs", 99, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[1].style);
}

void test_ui_components_sync_extreme_focus_idx(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item0";
    widgets[0].visible = 1;
    widgets[0].enabled = 1;
    widgets[1].id = "menu.item1";
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 2,
        .widgets = widgets,
    };

    /* INT_MIN and INT_MAX must be rejected without UB */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, INT_MIN, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, INT_MAX, NULL, NULL));
}

void test_ui_components_sync_overflow_item_index(void)
{
    /* Widget id with a huge numeric suffix that would overflow int parsing */
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item99999999999";
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test",
        .width = 128,
        .height = 64,
        .widget_count = 1,
        .widgets = widgets,
    };

    /* Overflow in item index parsing → returns false safely */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}
