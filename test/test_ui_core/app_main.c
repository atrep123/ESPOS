#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_core_init_sets_defaults(void);
void test_ui_core_tick_increments_time(void);
void test_ui_core_button_a_cycles_scene_on_press(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_core_init_sets_defaults);
    RUN_TEST(test_ui_core_tick_increments_time);
    RUN_TEST(test_ui_core_button_a_cycles_scene_on_press);
    UNITY_END();
}

#else

void test_ui_core_init_sets_defaults(void);
void test_ui_core_tick_increments_time(void);
void test_ui_core_button_a_cycles_scene_on_press(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_core_init_sets_defaults);
    RUN_TEST(test_ui_core_tick_increments_time);
    RUN_TEST(test_ui_core_button_a_cycles_scene_on_press);
    return UNITY_END();
}

#endif
