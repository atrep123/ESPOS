#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_components_prefix_visible_marks_dirty(void);
void test_ui_components_menu_active_sets_highlight(void);
void test_ui_components_tabs_active_sets_highlight(void);
void test_ui_components_sync_active_from_focus_updates_menu_highlight(void);
void test_ui_components_sync_active_from_focus_updates_tabs_highlight(void);
void test_ui_components_null_scene(void);
void test_ui_components_null_root(void);
void test_ui_components_sync_no_dot_in_id(void);
void test_ui_components_sync_invalid_focus_idx(void);
void test_ui_components_sync_null_widget_id(void);
void test_ui_components_sync_unknown_role(void);
void test_ui_components_menu_no_dirty_fn(void);
void test_ui_components_prefix_visible_null_widget_ids(void);
void test_ui_components_list_set_active(void);
void test_ui_components_menu_no_match_returns_false(void);
void test_ui_components_tabs_out_of_range_clears_all(void);
void test_ui_components_sync_extreme_focus_idx(void);
void test_ui_components_sync_overflow_item_index(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_components_prefix_visible_marks_dirty);
    RUN_TEST(test_ui_components_menu_active_sets_highlight);
    RUN_TEST(test_ui_components_tabs_active_sets_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_menu_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_tabs_highlight);
    RUN_TEST(test_ui_components_null_scene);
    RUN_TEST(test_ui_components_null_root);
    RUN_TEST(test_ui_components_sync_no_dot_in_id);
    RUN_TEST(test_ui_components_sync_invalid_focus_idx);
    RUN_TEST(test_ui_components_sync_null_widget_id);
    RUN_TEST(test_ui_components_sync_unknown_role);
    RUN_TEST(test_ui_components_menu_no_dirty_fn);
    RUN_TEST(test_ui_components_prefix_visible_null_widget_ids);
    RUN_TEST(test_ui_components_list_set_active);
    RUN_TEST(test_ui_components_menu_no_match_returns_false);
    RUN_TEST(test_ui_components_tabs_out_of_range_clears_all);
    RUN_TEST(test_ui_components_sync_extreme_focus_idx);
    RUN_TEST(test_ui_components_sync_overflow_item_index);
    UNITY_END();
}

#else

void test_ui_components_prefix_visible_marks_dirty(void);
void test_ui_components_menu_active_sets_highlight(void);
void test_ui_components_tabs_active_sets_highlight(void);
void test_ui_components_sync_active_from_focus_updates_menu_highlight(void);
void test_ui_components_sync_active_from_focus_updates_tabs_highlight(void);
void test_ui_components_null_scene(void);
void test_ui_components_null_root(void);
void test_ui_components_sync_no_dot_in_id(void);
void test_ui_components_sync_invalid_focus_idx(void);
void test_ui_components_sync_null_widget_id(void);
void test_ui_components_sync_unknown_role(void);
void test_ui_components_menu_no_dirty_fn(void);
void test_ui_components_prefix_visible_null_widget_ids(void);
void test_ui_components_list_set_active(void);
void test_ui_components_menu_no_match_returns_false(void);
void test_ui_components_tabs_out_of_range_clears_all(void);
void test_ui_components_sync_extreme_focus_idx(void);
void test_ui_components_sync_overflow_item_index(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_components_prefix_visible_marks_dirty);
    RUN_TEST(test_ui_components_menu_active_sets_highlight);
    RUN_TEST(test_ui_components_tabs_active_sets_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_menu_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_tabs_highlight);
    RUN_TEST(test_ui_components_null_scene);
    RUN_TEST(test_ui_components_null_root);
    RUN_TEST(test_ui_components_sync_no_dot_in_id);
    RUN_TEST(test_ui_components_sync_invalid_focus_idx);
    RUN_TEST(test_ui_components_sync_null_widget_id);
    RUN_TEST(test_ui_components_sync_unknown_role);
    RUN_TEST(test_ui_components_menu_no_dirty_fn);
    RUN_TEST(test_ui_components_prefix_visible_null_widget_ids);
    RUN_TEST(test_ui_components_list_set_active);
    RUN_TEST(test_ui_components_menu_no_match_returns_false);
    RUN_TEST(test_ui_components_tabs_out_of_range_clears_all);
    RUN_TEST(test_ui_components_sync_extreme_focus_idx);
    RUN_TEST(test_ui_components_sync_overflow_item_index);
    return UNITY_END();
}

#endif
