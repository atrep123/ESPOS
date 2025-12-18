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
