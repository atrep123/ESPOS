#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_nav_first_focus_in_rect_filters(void);
void test_ui_nav_move_focus_in_rect_cycles_inside_bounds(void);
void test_ui_nav_move_focus_in_rect_from_outside_picks_first(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_nav_first_focus_in_rect_filters);
    RUN_TEST(test_ui_nav_move_focus_in_rect_cycles_inside_bounds);
    RUN_TEST(test_ui_nav_move_focus_in_rect_from_outside_picks_first);
    UNITY_END();
}

#else

void test_ui_nav_first_focus_in_rect_filters(void);
void test_ui_nav_move_focus_in_rect_cycles_inside_bounds(void);
void test_ui_nav_move_focus_in_rect_from_outside_picks_first(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_nav_first_focus_in_rect_filters);
    RUN_TEST(test_ui_nav_move_focus_in_rect_cycles_inside_bounds);
    RUN_TEST(test_ui_nav_move_focus_in_rect_from_outside_picks_first);
    return UNITY_END();
}

#endif

