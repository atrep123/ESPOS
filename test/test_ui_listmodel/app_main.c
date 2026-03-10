#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_listmodel_scrolls_viewport(void);
void test_ui_listmodel_parse_item_text_splits_fields(void);
void test_ui_listmodel_manager_creates_and_reuses(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_listmodel_scrolls_viewport);
    RUN_TEST(test_ui_listmodel_parse_item_text_splits_fields);
    RUN_TEST(test_ui_listmodel_manager_creates_and_reuses);
    UNITY_END();
}

#else

void test_ui_listmodel_scrolls_viewport(void);
void test_ui_listmodel_parse_item_text_splits_fields(void);
void test_ui_listmodel_manager_creates_and_reuses(void);
void test_ui_listmodel_format_scroll_basic(void);
void test_ui_listmodel_format_scroll_null(void);
void test_ui_listmodel_set_item_stores_values(void);
void test_ui_listmodel_set_item_bounds(void);
void test_ui_listmodel_set_len_clamps_active(void);
void test_ui_listmodel_move_active_delta_zero_no_change(void);
void test_ui_listmodel_get_nonexistent_returns_null(void);
void test_ui_listmodel_parse_null_and_empty(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_listmodel_scrolls_viewport);
    RUN_TEST(test_ui_listmodel_parse_item_text_splits_fields);
    RUN_TEST(test_ui_listmodel_manager_creates_and_reuses);
    RUN_TEST(test_ui_listmodel_format_scroll_basic);
    RUN_TEST(test_ui_listmodel_format_scroll_null);
    RUN_TEST(test_ui_listmodel_set_item_stores_values);
    RUN_TEST(test_ui_listmodel_set_item_bounds);
    RUN_TEST(test_ui_listmodel_set_len_clamps_active);
    RUN_TEST(test_ui_listmodel_move_active_delta_zero_no_change);
    RUN_TEST(test_ui_listmodel_get_nonexistent_returns_null);
    RUN_TEST(test_ui_listmodel_parse_null_and_empty);
    return UNITY_END();
}

#endif

