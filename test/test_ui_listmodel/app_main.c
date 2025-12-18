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

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_listmodel_scrolls_viewport);
    RUN_TEST(test_ui_listmodel_parse_item_text_splits_fields);
    RUN_TEST(test_ui_listmodel_manager_creates_and_reuses);
    return UNITY_END();
}

#endif

