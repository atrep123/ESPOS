/*
 * Unit tests for pure scene query/manipulation (ui_scene_util.c):
 * - ui_scene_widget_rect: extract widget bounds
 * - ui_scene_find_by_id: linear search by ID
 * - ui_scene_count_item_slots: count sequential item widgets
 * - ui_scene_modal_find_rect: find modal dialog/panel bounding rect
 */

#include "unity.h"
#include <string.h>
#include <stdio.h>
#include "services/ui/ui_scene_util.h"

void setUp(void) {}
void tearDown(void) {}

/* Helper: build a minimal widget with an ID and position. */
static UiWidget make_widget(const char *id, uint16_t x, uint16_t y, uint16_t w, uint16_t h)
{
    UiWidget ww;
    memset(&ww, 0, sizeof(ww));
    ww.id = id;
    ww.x = x;
    ww.y = y;
    ww.width = w;
    ww.height = h;
    return ww;
}

/* ================================================================== */
/* ui_scene_widget_rect                                                */
/* ================================================================== */

void test_widget_rect_basic(void)
{
    UiWidget widgets[2] = {
        make_widget("a", 10, 20, 100, 50),
        make_widget("b", 30, 40, 60, 80),
    };
    UiScene scene = { .name = "test", .widget_count = 2, .widgets = widgets };

    int x, y, w, h;
    ui_scene_widget_rect(&scene, 0, &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(10, x);
    TEST_ASSERT_EQUAL_INT(20, y);
    TEST_ASSERT_EQUAL_INT(100, w);
    TEST_ASSERT_EQUAL_INT(50, h);

    ui_scene_widget_rect(&scene, 1, &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(30, x);
    TEST_ASSERT_EQUAL_INT(40, y);
    TEST_ASSERT_EQUAL_INT(60, w);
    TEST_ASSERT_EQUAL_INT(80, h);
}

void test_widget_rect_null_scene(void)
{
    int x = 99, y = 99, w = 99, h = 99;
    ui_scene_widget_rect(NULL, 0, &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(0, x);
    TEST_ASSERT_EQUAL_INT(0, y);
    TEST_ASSERT_EQUAL_INT(0, w);
    TEST_ASSERT_EQUAL_INT(0, h);
}

void test_widget_rect_oob_negative(void)
{
    UiWidget widgets[1] = { make_widget("a", 5, 6, 7, 8) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x = 99, y, w, h;
    ui_scene_widget_rect(&scene, -1, &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(0, x);
}

void test_widget_rect_oob_too_large(void)
{
    UiWidget widgets[1] = { make_widget("a", 5, 6, 7, 8) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x = 99, y, w, h;
    ui_scene_widget_rect(&scene, 5, &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(0, x);
}

void test_widget_rect_partial_null_out(void)
{
    UiWidget widgets[1] = { make_widget("a", 10, 20, 30, 40) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x;
    ui_scene_widget_rect(&scene, 0, &x, NULL, NULL, NULL);
    TEST_ASSERT_EQUAL_INT(10, x);
}

/* ================================================================== */
/* ui_scene_find_by_id                                                 */
/* ================================================================== */

void test_find_by_id_found(void)
{
    UiWidget widgets[3] = {
        make_widget("alpha", 0, 0, 10, 10),
        make_widget("beta",  0, 0, 10, 10),
        make_widget("gamma", 0, 0, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 3, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(1, ui_scene_find_by_id(&scene, "beta"));
}

void test_find_by_id_not_found(void)
{
    UiWidget widgets[2] = {
        make_widget("a", 0, 0, 10, 10),
        make_widget("b", 0, 0, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(-1, ui_scene_find_by_id(&scene, "xxx"));
}

void test_find_by_id_null_scene(void)
{
    TEST_ASSERT_EQUAL_INT(-1, ui_scene_find_by_id(NULL, "a"));
}

void test_find_by_id_null_id(void)
{
    UiWidget widgets[1] = { make_widget("a", 0, 0, 10, 10) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(-1, ui_scene_find_by_id(&scene, NULL));
}

void test_find_by_id_empty_id(void)
{
    UiWidget widgets[1] = { make_widget("a", 0, 0, 10, 10) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(-1, ui_scene_find_by_id(&scene, ""));
}

void test_find_by_id_widget_null_id_skipped(void)
{
    UiWidget widgets[2] = {
        make_widget(NULL, 0, 0, 10, 10),
        make_widget("ok", 0, 0, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(1, ui_scene_find_by_id(&scene, "ok"));
}

void test_find_by_id_first_duplicate(void)
{
    UiWidget widgets[3] = {
        make_widget("dup", 0, 0, 10, 10),
        make_widget("dup", 5, 5, 20, 20),
        make_widget("other", 0, 0, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 3, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(0, ui_scene_find_by_id(&scene, "dup"));
}

/* ================================================================== */
/* ui_scene_count_item_slots                                           */
/* ================================================================== */

void test_count_items_three(void)
{
    UiWidget widgets[4] = {
        make_widget("menu.item0", 0, 0, 10, 10),
        make_widget("menu.item1", 0, 10, 10, 10),
        make_widget("menu.item2", 0, 20, 10, 10),
        make_widget("other", 0, 30, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 4, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(3, ui_scene_count_item_slots(&scene, "menu"));
}

void test_count_items_zero(void)
{
    UiWidget widgets[1] = { make_widget("x", 0, 0, 10, 10) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(0, ui_scene_count_item_slots(&scene, "menu"));
}

void test_count_items_gap_stops(void)
{
    /* item0 and item2 exist but not item1 → count stops at 1 */
    UiWidget widgets[2] = {
        make_widget("list.item0", 0, 0, 10, 10),
        make_widget("list.item2", 0, 20, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(1, ui_scene_count_item_slots(&scene, "list"));
}

void test_count_items_null_scene(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_scene_count_item_slots(NULL, "x"));
}

void test_count_items_null_root(void)
{
    UiWidget widgets[1] = { make_widget("a.item0", 0, 0, 10, 10) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(0, ui_scene_count_item_slots(&scene, NULL));
}

void test_count_items_empty_root(void)
{
    UiWidget widgets[1] = { make_widget("a.item0", 0, 0, 10, 10) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(0, ui_scene_count_item_slots(&scene, ""));
}

/* ================================================================== */
/* ui_scene_modal_find_rect                                            */
/* ================================================================== */

void test_modal_find_dialog(void)
{
    UiWidget widgets[2] = {
        make_widget("settings.dialog", 10, 20, 200, 100),
        make_widget("other", 0, 0, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };
    int x, y, w, h;
    int ok = ui_scene_modal_find_rect(&scene, "settings", &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_INT(10, x);
    TEST_ASSERT_EQUAL_INT(20, y);
    TEST_ASSERT_EQUAL_INT(200, w);
    TEST_ASSERT_EQUAL_INT(100, h);
}

void test_modal_find_panel_fallback(void)
{
    /* No .dialog, but .panel exists */
    UiWidget widgets[2] = {
        make_widget("cfg.panel", 5, 15, 150, 80),
        make_widget("other", 0, 0, 10, 10),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };
    int x, y, w, h;
    int ok = ui_scene_modal_find_rect(&scene, "cfg", &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_INT(5, x);
    TEST_ASSERT_EQUAL_INT(150, w);
}

void test_modal_find_prefers_dialog(void)
{
    /* Both .dialog and .panel exist — should find .dialog */
    UiWidget widgets[2] = {
        make_widget("m.dialog", 10, 20, 100, 50),
        make_widget("m.panel",  30, 40, 200, 80),
    };
    UiScene scene = { .name = "t", .widget_count = 2, .widgets = widgets };
    int x, y, w, h;
    ui_scene_modal_find_rect(&scene, "m", &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(10, x);
    TEST_ASSERT_EQUAL_INT(100, w);
}

void test_modal_find_not_found(void)
{
    UiWidget widgets[1] = { make_widget("other", 5, 5, 50, 50) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x = 99, y, w, h;
    int ok = ui_scene_modal_find_rect(&scene, "nope", &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(0, ok);
    TEST_ASSERT_EQUAL_INT(0, x);
}

/* ================================================================== */
/* ui_scene_clone                                                      */
/* ================================================================== */

void test_clone_basic(void)
{
    UiWidget src_widgets[3] = {
        make_widget("a", 0, 0, 10, 10),
        make_widget("b", 20, 0, 10, 10),
        make_widget("c", 40, 0, 10, 10),
    };
    UiScene src = { .name = "original", .width = 128, .height = 64,
                    .widget_count = 3, .widgets = src_widgets };
    UiWidget dst_widgets[8];
    UiScene dst;
    memset(&dst, 0, sizeof(dst));
    memset(dst_widgets, 0, sizeof(dst_widgets));

    int ok = ui_scene_clone(&src, &dst, dst_widgets, 8);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_STRING("original", dst.name);
    TEST_ASSERT_EQUAL_UINT16(3, dst.widget_count);
    TEST_ASSERT_TRUE(dst.widgets == dst_widgets);
    TEST_ASSERT_EQUAL_STRING("a", dst_widgets[0].id);
    TEST_ASSERT_EQUAL_STRING("c", dst_widgets[2].id);
}

void test_clone_truncates_to_max(void)
{
    UiWidget src_widgets[4] = {
        make_widget("w0", 0, 0, 10, 10),
        make_widget("w1", 10, 0, 10, 10),
        make_widget("w2", 20, 0, 10, 10),
        make_widget("w3", 30, 0, 10, 10),
    };
    UiScene src = { .name = "big", .width = 256, .height = 128,
                    .widget_count = 4, .widgets = src_widgets };

    UiWidget dst_widgets[2];
    UiScene dst;
    memset(&dst, 0, sizeof(dst));

    int ok = ui_scene_clone(&src, &dst, dst_widgets, 2);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_UINT16(2, dst.widget_count);
    TEST_ASSERT_EQUAL_STRING("w0", dst_widgets[0].id);
    TEST_ASSERT_EQUAL_STRING("w1", dst_widgets[1].id);
}

void test_clone_preserves_width_height(void)
{
    UiWidget src_widgets[1] = { make_widget("x", 0, 0, 10, 10) };
    UiScene src = { .name = "s", .width = 256, .height = 128,
                    .widget_count = 1, .widgets = src_widgets };
    UiWidget dst_widgets[1];
    UiScene dst;

    ui_scene_clone(&src, &dst, dst_widgets, 1);
    TEST_ASSERT_EQUAL_UINT16(256, dst.width);
    TEST_ASSERT_EQUAL_UINT16(128, dst.height);
}

void test_clone_null_src_returns_zero(void)
{
    UiWidget buf[1];
    UiScene dst;
    TEST_ASSERT_EQUAL_INT(0, ui_scene_clone(NULL, &dst, buf, 1));
}

void test_clone_null_dst_returns_zero(void)
{
    UiWidget src_widgets[1] = { make_widget("x", 0, 0, 10, 10) };
    UiScene src = { .name = "s", .widget_count = 1, .widgets = src_widgets };
    TEST_ASSERT_EQUAL_INT(0, ui_scene_clone(&src, NULL, src_widgets, 1));
}

void test_clone_null_dst_widgets_returns_zero(void)
{
    UiWidget src_widgets[1] = { make_widget("x", 0, 0, 10, 10) };
    UiScene src = { .name = "s", .widget_count = 1, .widgets = src_widgets };
    UiScene dst;
    TEST_ASSERT_EQUAL_INT(0, ui_scene_clone(&src, &dst, NULL, 1));
}

void test_clone_src_null_widgets_returns_zero(void)
{
    UiScene src = { .name = "s", .widget_count = 0, .widgets = NULL };
    UiWidget buf[1];
    UiScene dst;
    TEST_ASSERT_EQUAL_INT(0, ui_scene_clone(&src, &dst, buf, 1));
}

void test_clone_exact_fit(void)
{
    UiWidget src_widgets[3] = {
        make_widget("a", 0, 0, 10, 10),
        make_widget("b", 10, 0, 10, 10),
        make_widget("c", 20, 0, 10, 10),
    };
    UiScene src = { .name = "exact", .widget_count = 3, .widgets = src_widgets };
    UiWidget dst_widgets[3];
    UiScene dst;

    int ok = ui_scene_clone(&src, &dst, dst_widgets, 3);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_UINT16(3, dst.widget_count);
}

void test_clone_zero_max_widgets(void)
{
    UiWidget src_widgets[2] = {
        make_widget("a", 0, 0, 10, 10),
        make_widget("b", 10, 0, 10, 10),
    };
    UiScene src = { .name = "z", .widget_count = 2, .widgets = src_widgets };
    UiWidget dst_widgets[1];
    UiScene dst;

    int ok = ui_scene_clone(&src, &dst, dst_widgets, 0);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_UINT16(0, dst.widget_count);
}

void test_clone_dst_points_to_buffer(void)
{
    UiWidget src_widgets[1] = { make_widget("only", 5, 10, 20, 30) };
    UiScene src = { .name = "ptr", .widget_count = 1, .widgets = src_widgets };
    UiWidget dst_buf[4];
    UiScene dst;

    ui_scene_clone(&src, &dst, dst_buf, 4);
    /* dst.widgets must point to dst_buf, NOT to src_widgets */
    TEST_ASSERT_TRUE(dst.widgets == dst_buf);
    TEST_ASSERT_TRUE(dst.widgets != src_widgets);
}

void test_modal_find_zero_size_returns_zero(void)
{
    /* Widget found but has zero dimensions */
    UiWidget widgets[1] = { make_widget("z.dialog", 10, 20, 0, 0) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x, y, w, h;
    int ok = ui_scene_modal_find_rect(&scene, "z", &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(0, ok);
}

void test_modal_find_null_scene(void)
{
    int x, y, w, h;
    TEST_ASSERT_EQUAL_INT(0, ui_scene_modal_find_rect(NULL, "x", &x, &y, &w, &h));
}

void test_modal_find_null_root(void)
{
    UiWidget widgets[1] = { make_widget("a.dialog", 0, 0, 50, 50) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x, y, w, h;
    TEST_ASSERT_EQUAL_INT(0, ui_scene_modal_find_rect(&scene, NULL, &x, &y, &w, &h));
}

void test_modal_find_partial_null_out(void)
{
    UiWidget widgets[1] = { make_widget("p.dialog", 10, 20, 100, 50) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int w;
    int ok = ui_scene_modal_find_rect(&scene, "p", NULL, NULL, &w, NULL);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_INT(100, w);
}

/* ================================================================== */
/* Round-8 additions                                                   */
/* ================================================================== */

void test_find_by_id_single_widget_match(void)
{
    UiWidget widgets[1] = { make_widget("only", 0, 0, 10, 10) };
    UiScene scene = { .name = "s", .widget_count = 1, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(0, ui_scene_find_by_id(&scene, "only"));
}

void test_count_item_slots_many_sequential(void)
{
    /* Fill slots root.item0 .. root.item9 (10 sequential) */
    UiWidget widgets[10];
    char ids[10][16];
    for (int i = 0; i < 10; ++i) {
        snprintf(ids[i], sizeof(ids[i]), "root.item%d", i);
        widgets[i] = make_widget(ids[i], 0, 0, 10, 10);
    }
    UiScene scene = { .name = "s", .widget_count = 10, .widgets = widgets };
    TEST_ASSERT_EQUAL_INT(10, ui_scene_count_item_slots(&scene, "root"));
}

void test_clone_preserves_widget_type_and_visible(void)
{
    UiWidget src_widgets[1] = { make_widget("t", 5, 10, 20, 30) };
    src_widgets[0].type = 3;
    src_widgets[0].visible = 1;
    src_widgets[0].enabled = 1;
    src_widgets[0].border = 1;
    UiScene src = { .name = "fields", .widget_count = 1,
                    .widgets = src_widgets };
    UiWidget dst_widgets[1];
    UiScene dst;
    ui_scene_clone(&src, &dst, dst_widgets, 1);
    TEST_ASSERT_EQUAL_UINT8(3, dst_widgets[0].type);
    TEST_ASSERT_EQUAL_UINT8(1, dst_widgets[0].visible);
    TEST_ASSERT_EQUAL_UINT8(1, dst_widgets[0].enabled);
    TEST_ASSERT_EQUAL_UINT8(1, dst_widgets[0].border);
}

void test_modal_find_zero_height_only(void)
{
    /* Dialog widget with w>0 but h=0 → should return 0 (invalid size) */
    UiWidget widgets[1] = { make_widget("m.dialog", 10, 20, 50, 0) };
    UiScene scene = { .name = "t", .widget_count = 1, .widgets = widgets };
    int x, y, w, h;
    int ok = ui_scene_modal_find_rect(&scene, "m", &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(0, ok);
}

void test_widget_rect_last_valid_index(void)
{
    UiWidget widgets[3] = {
        make_widget("a", 0, 0, 10, 10),
        make_widget("b", 10, 0, 20, 20),
        make_widget("c", 30, 0, 40, 50),
    };
    UiScene scene = { .name = "s", .widget_count = 3, .widgets = widgets };
    int x, y, w, h;
    ui_scene_widget_rect(&scene, 2, &x, &y, &w, &h);
    TEST_ASSERT_EQUAL_INT(30, x);
    TEST_ASSERT_EQUAL_INT(0, y);
    TEST_ASSERT_EQUAL_INT(40, w);
    TEST_ASSERT_EQUAL_INT(50, h);
}

void test_widget_rect_uint16_max_coords(void)
{
    UiWidget w = make_widget("big", 65535, 65535, 65535, 65535);
    UiScene scene = { .name = "s", .widget_count = 1, .widgets = &w };
    int x, y, ww, hh;
    ui_scene_widget_rect(&scene, 0, &x, &y, &ww, &hh);
    TEST_ASSERT_EQUAL_INT(65535, x);
    TEST_ASSERT_EQUAL_INT(65535, y);
    TEST_ASSERT_EQUAL_INT(65535, ww);
    TEST_ASSERT_EQUAL_INT(65535, hh);
}

void test_clone_empty_scene(void)
{
    UiWidget src_w[1];
    memset(src_w, 0, sizeof(src_w));
    UiScene src = { .name = "empty", .widget_count = 0, .widgets = src_w,
                    .width = 256, .height = 128 };
    UiWidget dst_w[4];
    UiScene dst;
    int ok = ui_scene_clone(&src, &dst, dst_w, 4);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_UINT16(0, dst.widget_count);
    TEST_ASSERT_EQUAL_UINT16(256, dst.width);
}

void test_find_by_id_empty_scene(void)
{
    UiWidget w[1];
    memset(w, 0, sizeof(w));
    UiScene scene = { .name = "e", .widget_count = 0, .widgets = w };
    TEST_ASSERT_EQUAL_INT(-1, ui_scene_find_by_id(&scene, "anything"));
}
