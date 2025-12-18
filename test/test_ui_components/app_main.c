#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_components_prefix_visible_marks_dirty(void);
void test_ui_components_menu_active_sets_highlight(void);
void test_ui_components_tabs_active_sets_highlight(void);
void test_ui_components_sync_active_from_focus_updates_menu_highlight(void);
void test_ui_components_sync_active_from_focus_updates_tabs_highlight(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_components_prefix_visible_marks_dirty);
    RUN_TEST(test_ui_components_menu_active_sets_highlight);
    RUN_TEST(test_ui_components_tabs_active_sets_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_menu_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_tabs_highlight);
    UNITY_END();
}

#else

void test_ui_components_prefix_visible_marks_dirty(void);
void test_ui_components_menu_active_sets_highlight(void);
void test_ui_components_tabs_active_sets_highlight(void);
void test_ui_components_sync_active_from_focus_updates_menu_highlight(void);
void test_ui_components_sync_active_from_focus_updates_tabs_highlight(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_components_prefix_visible_marks_dirty);
    RUN_TEST(test_ui_components_menu_active_sets_highlight);
    RUN_TEST(test_ui_components_tabs_active_sets_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_menu_highlight);
    RUN_TEST(test_ui_components_sync_active_from_focus_updates_tabs_highlight);
    return UNITY_END();
}

#endif
