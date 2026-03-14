#include "unity.h"

#include <stdio.h>
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

/* ------------------------------------------------------------------ */
/* Edge-case tests for listmodel                                      */
/* ------------------------------------------------------------------ */

void test_ui_listmodel_set_len_negative(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "neg", true);
    TEST_ASSERT_NOT_NULL(m);
    ui_listmodel_set_len(m, -5);
    TEST_ASSERT_EQUAL_UINT16(0, m->count);
}

void test_ui_listmodel_set_len_above_max(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "big", true);
    TEST_ASSERT_NOT_NULL(m);
    ui_listmodel_set_len(m, 9999);
    TEST_ASSERT_EQUAL_UINT16(UI_LISTMODEL_MAX_ITEMS, m->count);
}

void test_ui_listmodel_move_active_clamps_at_bounds(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "clamp", true);
    ui_listmodel_set_len(m, 5);

    /* Move far negative — clamps to 0 */
    ui_listmodel_set_active(m, 2, 3);
    ui_listmodel_move_active(m, -100, 3);
    TEST_ASSERT_EQUAL_UINT16(0, m->active);

    /* Move far positive — clamps to count-1 */
    ui_listmodel_move_active(m, 1000, 3);
    TEST_ASSERT_EQUAL_UINT16(4, m->active);
}

void test_ui_listmodel_active_slot_basic(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "slot", true);
    ui_listmodel_set_len(m, 10);
    ui_listmodel_set_active(m, 5, 4);

    int slot = ui_listmodel_active_slot(m);
    /* active_slot = active - offset; offset is clamped so active is visible */
    TEST_ASSERT_TRUE(slot >= 0 && slot < 4);
}

void test_ui_listmodel_active_slot_null(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_listmodel_active_slot(NULL));
}

void test_ui_listmodel_max_models_exceeded(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);

    /* Allocate all slots */
    for (int i = 0; i < UI_LISTMODEL_MAX_MODELS; ++i) {
        char name[8];
        snprintf(name, sizeof(name), "m%d", i);
        TEST_ASSERT_NOT_NULL(ui_listmodels_get(&lists, name, true));
    }

    /* Next allocation should fail */
    TEST_ASSERT_NULL(ui_listmodels_get(&lists, "overflow", true));
}

void test_ui_listmodel_set_active_empty_list(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "empty", true);
    TEST_ASSERT_NOT_NULL(m);

    /* set_active on empty count=0 list */
    bool changed = ui_listmodel_set_active(m, 5, 3);
    TEST_ASSERT_TRUE(changed || (m->active == 0 && m->offset == 0));
    TEST_ASSERT_EQUAL_UINT16(0, m->active);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
}

void test_ui_listmodel_move_on_empty_list(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "mt", true);
    TEST_ASSERT_NOT_NULL(m);

    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, 1, 3));
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, -1, 3));
}

void test_ui_listmodel_set_len_null(void)
{
    /* Must not crash */
    ui_listmodel_set_len(NULL, 5);
    ui_listmodel_move_active(NULL, 1, 3);
}

/* ------------------------------------------------------------------ */
/* Additional edge-case tests                                         */
/* ------------------------------------------------------------------ */

void test_ui_listmodel_single_visible_slot(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "sv", true);
    ui_listmodel_set_len(m, 5);

    /* visible_slots=1: offset must always equal active */
    ui_listmodel_set_active(m, 0, 1);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
    TEST_ASSERT_EQUAL_INT(0, ui_listmodel_active_slot(m));

    ui_listmodel_set_active(m, 3, 1);
    TEST_ASSERT_EQUAL_UINT16(3, m->offset);
    TEST_ASSERT_EQUAL_INT(0, ui_listmodel_active_slot(m));

    ui_listmodel_set_active(m, 4, 1);
    TEST_ASSERT_EQUAL_UINT16(4, m->offset);
    TEST_ASSERT_EQUAL_INT(0, ui_listmodel_active_slot(m));
}

void test_ui_listmodel_visible_slots_zero(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "vs0", true);
    ui_listmodel_set_len(m, 5);

    /* visible_slots=0: should not crash, offset stays at 0 */
    ui_listmodel_set_active(m, 3, 0);
    TEST_ASSERT_EQUAL_UINT16(3, m->active);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
}

void test_ui_listmodel_parse_separator_only(void)
{
    char label[16] = "prev";
    char value[16] = "prev";

    /* Tab only → empty label, empty value */
    ui_listmodel_parse_item_text("\t", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("", label);
    TEST_ASSERT_EQUAL_STRING("", value);

    /* Pipe only → empty label, empty value */
    ui_listmodel_parse_item_text("|", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("", label);
    TEST_ASSERT_EQUAL_STRING("", value);
}

void test_ui_listmodel_parse_multiple_separators(void)
{
    char label[16];
    char value[16];

    /* First separator wins: "a\tb\tc" → label="a", value="b\tc" */
    ui_listmodel_parse_item_text("a\tb\tc", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("a", label);
    TEST_ASSERT_EQUAL_STRING("b\tc", value);

    /* Tab has priority over pipe: "x\ty|z" → split on \t → label="x", value="y|z" */
    ui_listmodel_parse_item_text("x\ty|z", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("x", label);
    TEST_ASSERT_EQUAL_STRING("y|z", value);
}

void test_ui_listmodel_parse_label_truncation(void)
{
    char label[4];   /* cap=4 → max 3 chars */
    char value[4];

    /* "ABCDEFGH\tVAL" → label truncated to "ABC" */
    ui_listmodel_parse_item_text("ABCDEFGH\tVAL", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("ABC", label);
    TEST_ASSERT_EQUAL_STRING("VAL", value);

    /* "X|LONGVALUE" → value truncated to "LON" */
    ui_listmodel_parse_item_text("X|LONGVALUE", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("X", label);
    TEST_ASSERT_EQUAL_STRING("LON", value);
}

void test_ui_listmodel_set_active_same_position(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "same", true);
    ui_listmodel_set_len(m, 10);

    ui_listmodel_set_active(m, 5, 4);
    /* Do it again → no change → false */
    TEST_ASSERT_FALSE(ui_listmodel_set_active(m, 5, 4));
}

void test_ui_listmodel_offset_stable(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "stab", true);
    ui_listmodel_set_len(m, 10);

    /* Put active at 3 with 6 visible → offset stays 0 */
    ui_listmodel_set_active(m, 3, 6);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);

    /* Move to 4 → still within [0..5] → offset stays 0 */
    ui_listmodel_move_active(m, 1, 6);
    TEST_ASSERT_EQUAL_UINT16(4, m->active);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);
}

void test_ui_listmodel_reinit_after_use(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);

    UiListModel *m = ui_listmodels_get(&lists, "reuse", true);
    ui_listmodel_set_len(m, 10);
    ui_listmodel_set_active(m, 5, 4);
    ui_listmodel_set_item(m, 0, "First", "1");

    /* Re-init clears everything */
    ui_listmodels_init(&lists);
    TEST_ASSERT_NULL(ui_listmodels_get(&lists, "reuse", false));

    /* Can create fresh */
    UiListModel *m2 = ui_listmodels_get(&lists, "reuse", true);
    TEST_ASSERT_NOT_NULL(m2);
    TEST_ASSERT_EQUAL_UINT16(0, m2->count);
    TEST_ASSERT_EQUAL_UINT16(0, m2->active);
}

void test_ui_listmodel_root_at_boundary(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);

    /* Root string of exactly ROOT_LEN-1 chars (max that fits) */
    char long_root[UI_LISTMODEL_ROOT_LEN];
    memset(long_root, 'A', UI_LISTMODEL_ROOT_LEN - 1);
    long_root[UI_LISTMODEL_ROOT_LEN - 1] = '\0';

    UiListModel *m = ui_listmodels_get(&lists, long_root, true);
    TEST_ASSERT_NOT_NULL(m);
    TEST_ASSERT_EQUAL_STRING(long_root, m->root);

    /* Retrieve it back */
    UiListModel *m2 = ui_listmodels_get(&lists, long_root, false);
    TEST_ASSERT_TRUE(m == m2);
}

void test_ui_listmodel_format_scroll_small_buffer(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "sb", true);
    ui_listmodel_set_len(m, 5);
    ui_listmodel_set_active(m, 2, 3);

    /* Buffer of size 1 → only null terminator fits */
    char buf[1];
    ui_listmodel_format_scroll(m, buf, 1);
    TEST_ASSERT_EQUAL_STRING("", buf);

    /* Buffer of size 3 → "3/" fits (truncated "3/5") */
    char buf2[3];
    ui_listmodel_format_scroll(m, buf2, (int)sizeof(buf2));
    TEST_ASSERT_EQUAL_STRING("3/", buf2);
}

void test_ui_listmodel_move_at_boundary_returns_false(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "bnd", true);
    ui_listmodel_set_len(m, 5);

    /* At position 0, move -1 → clamps to 0 → no change → false */
    ui_listmodel_set_active(m, 0, 3);
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, -1, 3));

    /* At last position, move +1 → clamps to 4 → no change → false */
    ui_listmodel_set_active(m, 4, 3);
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, 1, 3));
}

/* ------------------------------------------------------------------ */
/* New edge-case tests                                                 */
/* ------------------------------------------------------------------ */

void test_ui_listmodel_set_item_max_index(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "mx", true);
    ui_listmodel_set_len(m, UI_LISTMODEL_MAX_ITEMS);

    /* Last valid index */
    ui_listmodel_set_item(m, UI_LISTMODEL_MAX_ITEMS - 1, "last", "val");
    TEST_ASSERT_EQUAL_STRING("last", m->items[UI_LISTMODEL_MAX_ITEMS - 1].label);
    TEST_ASSERT_EQUAL_STRING("val", m->items[UI_LISTMODEL_MAX_ITEMS - 1].value);

    /* One past max — should be silently ignored */
    ui_listmodel_set_item(m, UI_LISTMODEL_MAX_ITEMS, "bad", "bad");
}

void test_ui_listmodel_root_truncation(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);

    /* Root longer than ROOT_LEN should be truncated and still retrievable */
    char too_long[UI_LISTMODEL_ROOT_LEN + 10];
    memset(too_long, 'B', sizeof(too_long) - 1);
    too_long[sizeof(too_long) - 1] = '\0';

    UiListModel *m = ui_listmodels_get(&lists, too_long, true);
    TEST_ASSERT_NOT_NULL(m);
    TEST_ASSERT_EQUAL_UINT(UI_LISTMODEL_ROOT_LEN - 1, strlen(m->root));
}

void test_ui_listmodel_parse_pipe_separator(void)
{
    char label[16];
    char value[16];

    /* Pipe separator works like tab */
    ui_listmodel_parse_item_text("Key|Value", label, (int)sizeof(label), value, (int)sizeof(value));
    TEST_ASSERT_EQUAL_STRING("Key", label);
    TEST_ASSERT_EQUAL_STRING("Value", value);
}

void test_ui_listmodel_set_active_beyond_count(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "bc", true);
    ui_listmodel_set_len(m, 3);

    /* active_index=99 should clamp to count-1=2 */
    ui_listmodel_set_active(m, 99, 3);
    TEST_ASSERT_EQUAL_UINT16(2, m->active);

    /* active_index=-5 should clamp to 0 */
    ui_listmodel_set_active(m, -5, 3);
    TEST_ASSERT_EQUAL_UINT16(0, m->active);
}

void test_ui_listmodel_format_scroll_single_item(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "si", true);
    ui_listmodel_set_len(m, 1);

    char buf[16];
    ui_listmodel_format_scroll(m, buf, (int)sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("1/1", buf);
}

/* --- Fuzz: single-item model boundary operations --- */
void test_ui_listmodel_single_item_boundary(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "one", true);
    TEST_ASSERT_NOT_NULL(m);
    ui_listmodel_set_len(m, 1);

    /* Set active to 0 on 1-item list */
    ui_listmodel_set_active(m, 0, 6);
    TEST_ASSERT_EQUAL_UINT16(0, m->active);
    TEST_ASSERT_EQUAL_UINT16(0, m->offset);

    /* Move forward from only item: should stay */
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, 1, 6));
    TEST_ASSERT_EQUAL_UINT16(0, m->active);

    /* Move backward from only item: should stay */
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, -1, 6));
    TEST_ASSERT_EQUAL_UINT16(0, m->active);

    /* active_slot with more visible slots than items */
    TEST_ASSERT_EQUAL_INT(0, ui_listmodel_active_slot(m));
}

/* --- Fuzz: max-capacity model (64 items) --- */
void test_ui_listmodel_max_capacity_boundary(void)
{
    UiListModels lists;
    ui_listmodels_init(&lists);
    UiListModel *m = ui_listmodels_get(&lists, "max", true);
    TEST_ASSERT_NOT_NULL(m);
    ui_listmodel_set_len(m, UI_LISTMODEL_MAX_ITEMS);
    TEST_ASSERT_EQUAL_UINT16(UI_LISTMODEL_MAX_ITEMS, m->count);

    /* Set active to last item */
    ui_listmodel_set_active(m, UI_LISTMODEL_MAX_ITEMS - 1, 6);
    TEST_ASSERT_EQUAL_UINT16(UI_LISTMODEL_MAX_ITEMS - 1, m->active);

    /* Cannot move beyond last */
    TEST_ASSERT_FALSE(ui_listmodel_move_active(m, 1, 6));
    TEST_ASSERT_EQUAL_UINT16(UI_LISTMODEL_MAX_ITEMS - 1, m->active);

    /* Clamp beyond-bounds set_active */
    ui_listmodel_set_active(m, 999, 6);
    TEST_ASSERT_EQUAL_UINT16(UI_LISTMODEL_MAX_ITEMS - 1, m->active);

    /* Format scroll at end */
    char buf[16];
    ui_listmodel_format_scroll(m, buf, (int)sizeof(buf));
    /* Should be "64/64" */
    TEST_ASSERT_EQUAL_STRING("64/64", buf);
}
