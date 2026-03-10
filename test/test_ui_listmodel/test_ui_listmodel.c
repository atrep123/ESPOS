#include "unity.h"

#include <string.h>

#include "services/ui/ui_listmodel.h"

void setUp(void) {}
void tearDown(void) {}

void test_ui_listmodel_scrolls_viewport(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "menu", true);
    TEST_ASSERT_NOT_NULL(m);

    ui_listmodel_set_len(m, 10);
    TEST_ASSERT_EQUAL_UINT16(10, m->count);

    /* 6 visible rows. */
    TEST_ASSERT_FALSE(ui_listmodel_set_active(m, 0, 6));
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
    TEST_ASSERT_EQUAL_INT(0, ui_listmodel_active_slot(m));

    TEST_ASSERT_TRUE(ui_listmodel_set_active(m, 5, 6));
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
    TEST_ASSERT_EQUAL_INT(5, ui_listmodel_active_slot(m));

    TEST_ASSERT_TRUE(ui_listmodel_set_active(m, 6, 6));
    TEST_ASSERT_EQUAL_UINT16(1, m->offset);
    TEST_ASSERT_EQUAL_INT(5, ui_listmodel_active_slot(m));

    TEST_ASSERT_TRUE(ui_listmodel_set_active(m, 9, 6));
    TEST_ASSERT_EQUAL_UINT16(4, m->offset);
    TEST_ASSERT_EQUAL_INT(5, ui_listmodel_active_slot(m));

    /* Moving beyond bounds clamps and returns false when no change. */
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, 1, 6));
    TEST_ASSERT_FALSE(ui_listmodel_set_active(m, 99, 6));
    TEST_ASSERT_EQUAL_UINT16(9, m->active);

    TEST_ASSERT_TRUE(ui_listmodel_move_active(m, -1, 6));
    TEST_ASSERT_EQUAL_UINT16(8, m->active);
    TEST_ASSERT_EQUAL_UINT16(4, m->offset);
}

void test_ui_listmodel_parse_item_text_splits_fields(void)
{
    char label[16];
    char value[16];

    ui_listmodel_parse_item_text("Speed\t42", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("Speed", label);
    TEST_ASSERT_EQUAL_STRING("42", value);

    ui_listmodel_parse_item_text("Mode|AUTO", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("Mode", label);
    TEST_ASSERT_EQUAL_STRING("AUTO", value);

    ui_listmodel_parse_item_text("Only", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("Only", label);
    TEST_ASSERT_EQUAL_STRING("", value);
}

void test_ui_listmodel_manager_creates_and_reuses(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);

    UiListModel *a1 = ui_listmodels_get(&lists, "list", true);
    UiListModel *a2 = ui_listmodels_get(&lists, "list", false);
    UiListModel *b = ui_listmodels_get(&lists, "other", true);

    TEST_ASSERT_NOT_NULL(a1);
    TEST_ASSERT_NOT_NULL(a2);
    TEST_ASSERT_NOT_NULL(b);
    TEST_ASSERT_TRUE(a1 == a2);
    TEST_ASSERT_FALSE(a1 == b);
    TEST_ASSERT_EQUAL_STRING("list", a1->root);
    TEST_ASSERT_EQUAL_STRING("other", b->root);
}

void test_ui_listmodel_format_scroll_basic(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "m", true);
    TEST_ASSERT_NOT_NULL(m);

    char buf[16];

    /* Empty list */
    ui_listmodel_format_scroll(m, buf, (int)sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("0/0", buf);

    /* 5 items, active=0 → "1/5" */
    ui_listmodel_set_len(m, 5);
    ui_listmodel_format_scroll(m, buf, (int)sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("1/5", buf);

    /* active=3 → "4/5" */
    ui_listmodel_set_active(m, 3, 3);
    ui_listmodel_format_scroll(m, buf, (int)sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("4/5", buf);
}

void test_ui_listmodel_format_scroll_null(void)
{
    char buf[16];
    ui_listmodel_format_scroll(NULL, buf, (int)sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("0/0", buf);

    /* NULL out buffer — should not crash */
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "x", true);
    ui_listmodel_format_scroll(m, NULL, 0);
}

void test_ui_listmodel_set_item_stores_values(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "items", true);
    TEST_ASSERT_NOT_NULL(m);

    ui_listmodel_set_len(m, 3);
    ui_listmodel_set_item(m, 0, "Alpha", "100");
    ui_listmodel_set_item(m, 1, "Beta", NULL);
    ui_listmodel_set_item(m, 2, NULL, "300");

    TEST_ASSERT_EQUAL_STRING("Alpha", m->items[0].label);
    TEST_ASSERT_EQUAL_STRING("100", m->items[0].value);
    TEST_ASSERT_EQUAL_STRING("Beta", m->items[1].label);
    TEST_ASSERT_EQUAL_STRING("", m->items[1].value);
    TEST_ASSERT_EQUAL_STRING("", m->items[2].label);
    TEST_ASSERT_EQUAL_STRING("300", m->items[2].value);
}

void test_ui_listmodel_set_item_bounds(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "b", true);
    TEST_ASSERT_NOT_NULL(m);

    /* Out-of-range indices should not crash */
    ui_listmodel_set_item(m, -1, "bad", "bad");
    ui_listmodel_set_item(m, 9999, "bad", "bad");
    ui_listmodel_set_item(NULL, 0, "bad", "bad");
}

void test_ui_listmodel_set_len_clamps_active(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "c", true);
    TEST_ASSERT_NOT_NULL(m);

    ui_listmodel_set_len(m, 10);
    ui_listmodel_set_active(m, 9, 4);
    TEST_ASSERT_EQUAL_UINT16(9, m->active);

    /* Shrink: active should clamp */
    ui_listmodel_set_len(m, 3);
    TEST_ASSERT_EQUAL_UINT16(2, m->active);

    /* Shrink to 0: active and offset reset */
    ui_listmodel_set_len(m, 0);
    TEST_ASSERT_EQUAL_UINT16(0, m->active);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
}

void test_ui_listmodel_move_active_delta_zero_no_change(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "d", true);
    ui_listmodel_set_len(m, 5);
    ui_listmodel_set_active(m, 2, 3);

    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, 0, 3));
    TEST_ASSERT_EQUAL_UINT16(2, m->active);
}

void test_ui_listmodel_get_nonexistent_returns_null(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    TEST_ASSERT_NULL(ui_listmodels_get(&lists, "nope", false));
    TEST_ASSERT_NULL(ui_listmodels_get(&lists, "", true));
    TEST_ASSERT_NULL(ui_listmodels_get(&lists, NULL, true));
    TEST_ASSERT_NULL(ui_listmodels_get(NULL, "x", true));
}

void test_ui_listmodel_parse_null_and_empty(void)
{
    char label[16] = "prev";
    char value[16] = "prev";

    ui_listmodel_parse_item_text(NULL, label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("", label);
    TEST_ASSERT_EQUAL_STRING("", value);

    ui_listmodel_parse_item_text("", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("", label);
    TEST_ASSERT_EQUAL_STRING("", value);
}
