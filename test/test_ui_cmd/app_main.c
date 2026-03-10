#include "unity.h"

#ifdef ESP_PLATFORM

void test_cmd_set_text(void);
void test_cmd_set_text_null_id(void);
void test_cmd_set_text_null_text(void);
void test_cmd_set_visible_true(void);
void test_cmd_set_visible_false(void);
void test_cmd_set_enabled(void);
void test_cmd_set_prefix_visible(void);
void test_cmd_set_style(void);
void test_cmd_set_value(void);
void test_cmd_set_checked(void);
void test_cmd_menu_set_active(void);
void test_cmd_list_set_active(void);
void test_cmd_tabs_set_active(void);
void test_cmd_listmodel_set_len(void);
void test_cmd_listmodel_set_item_label_only(void);
void test_cmd_listmodel_set_item_label_and_value(void);
void test_cmd_listmodel_set_item_null_label(void);
void test_cmd_listmodel_set_active(void);
void test_cmd_dialog_show(void);
void test_cmd_dialog_hide(void);
void test_cmd_toast_enqueue(void);
void test_cmd_toast_hide(void);
void test_cmd_switch_scene(void);
void test_cmd_id_truncation(void);
void test_cmd_text_truncation(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_cmd_set_text);
    RUN_TEST(test_cmd_set_text_null_id);
    RUN_TEST(test_cmd_set_text_null_text);
    RUN_TEST(test_cmd_set_visible_true);
    RUN_TEST(test_cmd_set_visible_false);
    RUN_TEST(test_cmd_set_enabled);
    RUN_TEST(test_cmd_set_prefix_visible);
    RUN_TEST(test_cmd_set_style);
    RUN_TEST(test_cmd_set_value);
    RUN_TEST(test_cmd_set_checked);
    RUN_TEST(test_cmd_menu_set_active);
    RUN_TEST(test_cmd_list_set_active);
    RUN_TEST(test_cmd_tabs_set_active);
    RUN_TEST(test_cmd_listmodel_set_len);
    RUN_TEST(test_cmd_listmodel_set_item_label_only);
    RUN_TEST(test_cmd_listmodel_set_item_label_and_value);
    RUN_TEST(test_cmd_listmodel_set_item_null_label);
    RUN_TEST(test_cmd_listmodel_set_active);
    RUN_TEST(test_cmd_dialog_show);
    RUN_TEST(test_cmd_dialog_hide);
    RUN_TEST(test_cmd_toast_enqueue);
    RUN_TEST(test_cmd_toast_hide);
    RUN_TEST(test_cmd_switch_scene);
    RUN_TEST(test_cmd_id_truncation);
    RUN_TEST(test_cmd_text_truncation);
    RUN_TEST(test_cmd_listmodel_set_item_truncation);
    RUN_TEST(test_cmd_listmodel_set_item_both_null);
    UNITY_END();
}

#else

void test_cmd_set_text(void);
void test_cmd_set_text_null_id(void);
void test_cmd_set_text_null_text(void);
void test_cmd_set_visible_true(void);
void test_cmd_set_visible_false(void);
void test_cmd_set_enabled(void);
void test_cmd_set_prefix_visible(void);
void test_cmd_set_style(void);
void test_cmd_set_value(void);
void test_cmd_set_checked(void);
void test_cmd_menu_set_active(void);
void test_cmd_list_set_active(void);
void test_cmd_tabs_set_active(void);
void test_cmd_listmodel_set_len(void);
void test_cmd_listmodel_set_item_label_only(void);
void test_cmd_listmodel_set_item_label_and_value(void);
void test_cmd_listmodel_set_item_null_label(void);
void test_cmd_listmodel_set_active(void);
void test_cmd_dialog_show(void);
void test_cmd_dialog_hide(void);
void test_cmd_toast_enqueue(void);
void test_cmd_toast_hide(void);
void test_cmd_switch_scene(void);
void test_cmd_id_truncation(void);
void test_cmd_text_truncation(void);
void test_cmd_listmodel_set_item_truncation(void);
void test_cmd_listmodel_set_item_both_null(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_cmd_set_text);
    RUN_TEST(test_cmd_set_text_null_id);
    RUN_TEST(test_cmd_set_text_null_text);
    RUN_TEST(test_cmd_set_visible_true);
    RUN_TEST(test_cmd_set_visible_false);
    RUN_TEST(test_cmd_set_enabled);
    RUN_TEST(test_cmd_set_prefix_visible);
    RUN_TEST(test_cmd_set_style);
    RUN_TEST(test_cmd_set_value);
    RUN_TEST(test_cmd_set_checked);
    RUN_TEST(test_cmd_menu_set_active);
    RUN_TEST(test_cmd_list_set_active);
    RUN_TEST(test_cmd_tabs_set_active);
    RUN_TEST(test_cmd_listmodel_set_len);
    RUN_TEST(test_cmd_listmodel_set_item_label_only);
    RUN_TEST(test_cmd_listmodel_set_item_label_and_value);
    RUN_TEST(test_cmd_listmodel_set_item_null_label);
    RUN_TEST(test_cmd_listmodel_set_active);
    RUN_TEST(test_cmd_dialog_show);
    RUN_TEST(test_cmd_dialog_hide);
    RUN_TEST(test_cmd_toast_enqueue);
    RUN_TEST(test_cmd_toast_hide);
    RUN_TEST(test_cmd_switch_scene);
    RUN_TEST(test_cmd_id_truncation);
    RUN_TEST(test_cmd_text_truncation);
    RUN_TEST(test_cmd_listmodel_set_item_truncation);
    RUN_TEST(test_cmd_listmodel_set_item_both_null);
    return UNITY_END();
}

#endif
