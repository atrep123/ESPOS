#include "unity.h"

#include <limits.h>
#include <stdio.h>
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

/* ------------------------------------------------------------------ */
/* Additional edge-case tests                                         */
/* ------------------------------------------------------------------ */

void test_ui_components_menu_same_index_no_change(void)
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
        .name = "test", .width = 128, .height = 64,
        .widget_count = 2, .widgets = widgets,
    };

    /* Setting the same active index again → no style changes → false */
    TEST_ASSERT_FALSE(ui_components_menu_set_active(&scene, "menu", 0, NULL, NULL));
}

void test_ui_components_menu_many_items(void)
{
    UiWidget widgets[8];
    memset(widgets, 0, sizeof(widgets));
    char ids[8][16];
    for (int i = 0; i < 8; ++i) {
        snprintf(ids[i], sizeof(ids[i]), "menu.item%d", i);
        widgets[i].id = ids[i];
        widgets[i].style = (i == 0) ? UI_STYLE_HIGHLIGHT : 0;
        widgets[i].visible = 1;
        widgets[i].enabled = 1;
    }
    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 8, .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_menu_set_active(&scene, "menu", 7, capture_dirty_add, &cap));
    /* Only item0 lost highlight and item7 gained it, so 2 dirty calls */
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    for (int i = 1; i < 7; ++i) {
        TEST_ASSERT_EQUAL_UINT8(0, widgets[i].style);
    }
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_HIGHLIGHT, widgets[7].style);
}

void test_ui_components_tabs_tab0_not_matched(void)
{
    /* Tab IDs are 1-based (tab1, tab2...). "tab0" should not match active_index=0. */
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "tabs.tab0";
    widgets[0].style = UI_STYLE_HIGHLIGHT;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;
    widgets[1].id = "tabs.tab1";
    widgets[1].style = 0;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 2, .widgets = widgets,
    };

    /* active_index=0 maps to tab number 0+(-1 bias)= tab-1, effectively nothing.
       tab0 has suffix "0" → index_bias=-1 → idx=-1, not matched.
       tab1 has suffix "1" → idx=0, matches active_index=0. */
    TEST_ASSERT_TRUE(ui_components_tabs_set_active(&scene, "tabs", 0, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);  /* tab0: idx=-1, cleared */
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_HIGHLIGHT, widgets[1].style);  /* tab1: idx=0, set */
}

void test_ui_components_sync_empty_root(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = ".item0";  /* leading dot → empty root */
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 1, .widgets = widgets,
    };

    /* dot at start → root is "" → should fail */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}

void test_ui_components_sync_trailing_dot(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.";  /* dot at end → empty role */
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 1, .widgets = widgets,
    };

    /* dot[1]=='\0' → returns false */
    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}

void test_ui_components_prefix_visible_idempotent(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "panel.bg";
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 1, .widgets = widgets,
    };

    /* Already visible → no change → false */
    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(&scene, "panel", true, NULL, NULL));
    /* Hide → true */
    TEST_ASSERT_TRUE(ui_components_set_prefix_visible(&scene, "panel", false, NULL, NULL));
    /* Already hidden → no change → false */
    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(&scene, "panel", false, NULL, NULL));
}

void test_ui_components_menu_preserves_other_styles(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item0";
    widgets[0].style = (uint8_t)(UI_STYLE_BOLD | UI_STYLE_INVERSE);
    widgets[0].visible = 1;
    widgets[0].enabled = 1;
    widgets[1].id = "menu.item1";
    widgets[1].style = UI_STYLE_BOLD;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 2, .widgets = widgets,
    };

    /* Set item1 active → item0 keeps BOLD|INVERSE, item1 gets BOLD|HIGHLIGHT */
    ui_components_menu_set_active(&scene, "menu", 1, NULL, NULL);
    TEST_ASSERT_EQUAL_UINT8((uint8_t)(UI_STYLE_BOLD | UI_STYLE_INVERSE), widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8((uint8_t)(UI_STYLE_BOLD | UI_STYLE_HIGHLIGHT), widgets[1].style);
}

void test_ui_components_empty_widget_count(void)
{
    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 0, .widgets = NULL,
    };

    /* Empty scene (but not NULL) → returns false */
    TEST_ASSERT_FALSE(ui_components_menu_set_active(&scene, "menu", 0, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_set_prefix_visible(&scene, "toast", true, NULL, NULL));
}

void test_ui_components_sync_tab_zero_returns_false(void)
{
    /* "tab0" → tab_num=0 → tab_num<=0 → returns false */
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "nav.tab0";
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 1, .widgets = widgets,
    };

    TEST_ASSERT_FALSE(ui_components_sync_active_from_focus(&scene, 0, NULL, NULL));
}

void test_ui_components_dirty_coords_match_widget(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "menu.item0";
    widgets[0].x = 10; widgets[0].y = 20;
    widgets[0].width = 50; widgets[0].height = 12;
    widgets[0].style = UI_STYLE_HIGHLIGHT;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;
    widgets[1].id = "menu.item1";
    widgets[1].x = 10; widgets[1].y = 32;
    widgets[1].width = 50; widgets[1].height = 12;
    widgets[1].style = 0;
    widgets[1].visible = 1;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 2, .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    ui_components_menu_set_active(&scene, "menu", 1, capture_dirty_add, &cap);

    /* Dirty rects should match widget geometry */
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
    /* First dirty: widget[0] lost highlight */
    TEST_ASSERT_EQUAL_INT(10, cap.x[0]);
    TEST_ASSERT_EQUAL_INT(20, cap.y[0]);
    TEST_ASSERT_EQUAL_INT(50, cap.w[0]);
    TEST_ASSERT_EQUAL_INT(12, cap.h[0]);
    /* Second dirty: widget[1] gained highlight */
    TEST_ASSERT_EQUAL_INT(10, cap.x[1]);
    TEST_ASSERT_EQUAL_INT(32, cap.y[1]);
    TEST_ASSERT_EQUAL_INT(50, cap.w[1]);
    TEST_ASSERT_EQUAL_INT(12, cap.h[1]);
}

/* ================================================================== */
/* ui_components_select_radiobutton                                    */
/* ================================================================== */

static UiWidget make_radio(const char *id, uint16_t x, uint16_t y,
                           uint16_t w, uint16_t h, uint8_t checked)
{
    UiWidget rw;
    memset(&rw, 0, sizeof(rw));
    rw.id = id;
    rw.type = (uint8_t)UIW_RADIOBUTTON;
    rw.x = x;
    rw.y = y;
    rw.width = w;
    rw.height = h;
    rw.checked = checked;
    rw.visible = 1;
    rw.enabled = 1;
    return rw;
}

void test_radio_select_basic(void)
{
    UiWidget widgets[3] = {
        make_radio("r0", 0, 0, 20, 12, 1),
        make_radio("r1", 0, 12, 20, 12, 0),
        make_radio("r2", 0, 24, 20, 12, 0),
    };
    UiScene scene = { .name = "t", .width = 128, .height = 64,
                      .widget_count = 3, .widgets = widgets };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    bool ok = ui_components_select_radiobutton(&scene, 2, capture_dirty_add, &cap);
    TEST_ASSERT_TRUE(ok);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].checked);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[1].checked);
    TEST_ASSERT_EQUAL_UINT8(1, widgets[2].checked);
    /* Two changes: r0 unchecked, r2 checked */
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
}

void test_radio_select_already_selected(void)
{
    UiWidget widgets[2] = {
        make_radio("r0", 0, 0, 20, 12, 1),
        make_radio("r1", 0, 12, 20, 12, 0),
    };
    UiScene scene = { .name = "t", .width = 128, .height = 64,
                      .widget_count = 2, .widgets = widgets };

    bool ok = ui_components_select_radiobutton(&scene, 0, NULL, NULL);
    /* No change → returns false */
    TEST_ASSERT_FALSE(ok);
    TEST_ASSERT_EQUAL_UINT8(1, widgets[0].checked);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[1].checked);
}

void test_radio_select_null_scene(void)
{
    TEST_ASSERT_FALSE(ui_components_select_radiobutton(NULL, 0, NULL, NULL));
}

void test_radio_select_oob_index(void)
{
    UiWidget widgets[1] = { make_radio("r0", 0, 0, 20, 12, 0) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };

    TEST_ASSERT_FALSE(ui_components_select_radiobutton(&scene, 5, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_select_radiobutton(&scene, -1, NULL, NULL));
}

void test_radio_select_non_radio_idx(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "btn";
    widgets[0].type = (uint8_t)UIW_BUTTON;
    widgets[0].visible = 1;
    widgets[0].enabled = 1;
    widgets[1] = make_radio("r0", 0, 12, 20, 12, 0);

    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };

    /* idx 0 is a button, not a radiobutton */
    TEST_ASSERT_FALSE(ui_components_select_radiobutton(&scene, 0, NULL, NULL));
}

void test_radio_select_mixed_types(void)
{
    UiWidget widgets[4];
    memset(widgets, 0, sizeof(widgets));
    widgets[0] = make_radio("r0", 0, 0, 20, 12, 1);
    widgets[1].id = "lbl";
    widgets[1].type = (uint8_t)UIW_LABEL;
    widgets[1].visible = 1;
    widgets[2] = make_radio("r1", 0, 12, 20, 12, 0);
    widgets[3] = make_radio("r2", 0, 24, 20, 12, 0);

    UiScene scene = { .name = "t", .widget_count = 4, .widgets = widgets };

    bool ok = ui_components_select_radiobutton(&scene, 2, NULL, NULL);
    TEST_ASSERT_TRUE(ok);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].checked);  /* was 1 → 0 */
    TEST_ASSERT_EQUAL_UINT8(0, widgets[1].checked);  /* label, untouched */
    TEST_ASSERT_EQUAL_UINT8(1, widgets[2].checked);  /* selected */
    TEST_ASSERT_EQUAL_UINT8(0, widgets[3].checked);  /* stays 0 */
}

void test_radio_select_dirty_coords(void)
{
    UiWidget widgets[2] = {
        make_radio("r0", 5, 10, 30, 14, 0),
        make_radio("r1", 5, 30, 30, 14, 1),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    ui_components_select_radiobutton(&scene, 0, capture_dirty_add, &cap);
    /* Both changed: r0 checked, r1 unchecked */
    TEST_ASSERT_EQUAL_INT(2, cap.calls);
    TEST_ASSERT_EQUAL_INT(5, cap.x[0]);
    TEST_ASSERT_EQUAL_INT(10, cap.y[0]);
    TEST_ASSERT_EQUAL_INT(30, cap.w[0]);
    TEST_ASSERT_EQUAL_INT(14, cap.h[0]);
    TEST_ASSERT_EQUAL_INT(5, cap.x[1]);
    TEST_ASSERT_EQUAL_INT(30, cap.y[1]);
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_ui_components_list_null_root(void)
{
    UiWidget widgets[1];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "list.item0";
    widgets[0].visible = 1;
    widgets[0].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 1, .widgets = widgets,
    };

    TEST_ASSERT_FALSE(ui_components_list_set_active(&scene, NULL, 0, NULL, NULL));
    TEST_ASSERT_FALSE(ui_components_list_set_active(&scene, "", 0, NULL, NULL));
}

void test_ui_components_tabs_no_dirty_fn(void)
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
        .name = "test", .width = 128, .height = 64,
        .widget_count = 2, .widgets = widgets,
    };

    TEST_ASSERT_TRUE(ui_components_tabs_set_active(&scene, "tabs", 1, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8(UI_STYLE_HIGHLIGHT, widgets[1].style);
}

void test_radio_select_single_widget(void)
{
    UiWidget widgets[1] = { make_radio("r0", 0, 0, 20, 12, 0) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };

    TEST_ASSERT_TRUE(ui_components_select_radiobutton(&scene, 0, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(1, widgets[0].checked);
}

void test_ui_components_prefix_visible_many_widgets(void)
{
    UiWidget widgets[5];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "grp.a";
    widgets[0].visible = 0; widgets[0].enabled = 1;
    widgets[1].id = "grp.b";
    widgets[1].visible = 0; widgets[1].enabled = 1;
    widgets[2].id = "grp.c";
    widgets[2].visible = 0; widgets[2].enabled = 1;
    widgets[3].id = "grp.d";
    widgets[3].visible = 0; widgets[3].enabled = 1;
    widgets[4].id = "other.x";
    widgets[4].visible = 0; widgets[4].enabled = 1;

    UiScene scene = {
        .name = "test", .width = 128, .height = 64,
        .widget_count = 5, .widgets = widgets,
    };

    DirtyCapture cap;
    memset(&cap, 0, sizeof(cap));

    TEST_ASSERT_TRUE(ui_components_set_prefix_visible(&scene, "grp", true, capture_dirty_add, &cap));
    TEST_ASSERT_EQUAL_INT(4, cap.calls);
    for (int i = 0; i < 4; i++) {
        TEST_ASSERT_EQUAL_UINT8(1, widgets[i].visible);
    }
    TEST_ASSERT_EQUAL_UINT8(0, widgets[4].visible);
}

void test_ui_components_menu_negative_index(void)
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
        .name = "test", .width = 128, .height = 64,
        .widget_count = 2, .widgets = widgets,
    };

    /* Negative index — no item matches, clears highlight from item0 */
    TEST_ASSERT_TRUE(ui_components_menu_set_active(&scene, "menu", -1, NULL, NULL));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].style);
    TEST_ASSERT_EQUAL_UINT8(0, widgets[1].style);
}

/* --- Fuzz: deeply nested panel hierarchy (10 levels) --- */
void test_ui_components_deeply_nested_panels(void)
{
    /* Build 10 nested panels: p, p.p, p.p.p, ... each with visible=0 */
    UiWidget widgets[10];
    memset(widgets, 0, sizeof(widgets));
    static const char *ids[] = {
        "p", "p.p", "p.p.p", "p.p.p.p", "p.p.p.p.p",
        "p.p.p.p.p.p", "p.p.p.p.p.p.p", "p.p.p.p.p.p.p.p",
        "p.p.p.p.p.p.p.p.p", "p.p.p.p.p.p.p.p.p.p"
    };
    for (int i = 0; i < 10; i++) {
        widgets[i].id = ids[i];
        widgets[i].type = UIW_PANEL;
        widgets[i].x = (uint16_t)i;
        widgets[i].y = (uint16_t)i;
        widgets[i].width = 100;
        widgets[i].height = 50;
        widgets[i].visible = 0;
        widgets[i].enabled = 1;
    }
    UiScene scene = {
        .name = "deep", .width = 256, .height = 128,
        .widget_count = 10, .widgets = widgets,
    };
    DirtyCapture dc;
    memset(&dc, 0, sizeof(dc));
    /* Show all children with prefix "p" (root "p" itself is not matched) */
    TEST_ASSERT_TRUE(
        ui_components_set_prefix_visible(&scene, "p", 1, capture_dirty_add, &dc));
    TEST_ASSERT_EQUAL_UINT8(0, widgets[0].visible); /* root not matched */
    for (int i = 1; i < 10; i++) {
        TEST_ASSERT_EQUAL_UINT8(1, widgets[i].visible);
    }
    TEST_ASSERT_TRUE(dc.calls > 0);
}

/* --- Fuzz: extreme coordinate widgets --- */
void test_ui_components_extreme_coordinates(void)
{
    UiWidget widgets[2];
    memset(widgets, 0, sizeof(widgets));
    widgets[0].id = "far.a";
    widgets[0].type = UIW_BOX;
    widgets[0].x = 65530;
    widgets[0].y = 65530;
    widgets[0].width = 100;
    widgets[0].height = 100;
    widgets[0].visible = 0;
    widgets[0].enabled = 1;
    widgets[1].id = "far.b";
    widgets[1].type = UIW_LABEL;
    widgets[1].x = 0;
    widgets[1].y = 0;
    widgets[1].width = 50;
    widgets[1].height = 20;
    widgets[1].visible = 0;
    widgets[1].enabled = 1;

    UiScene scene = {
        .name = "ext", .width = 256, .height = 128,
        .widget_count = 2, .widgets = widgets,
    };
    DirtyCapture dc;
    memset(&dc, 0, sizeof(dc));
    TEST_ASSERT_TRUE(
        ui_components_set_prefix_visible(&scene, "far", 1, capture_dirty_add, &dc));
    TEST_ASSERT_EQUAL_UINT8(1, widgets[0].visible);
    TEST_ASSERT_EQUAL_UINT8(1, widgets[1].visible);
    /* dirty rects should have been reported for both, no overflow */
    TEST_ASSERT_TRUE(dc.calls >= 2);
}
