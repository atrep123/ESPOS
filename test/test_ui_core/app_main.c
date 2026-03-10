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
void test_ui_core_on_rpc_bg_sets_rgb565(void);
void test_ui_core_on_rpc_bg_null_no_crash(void);
void test_ui_core_init_null_no_crash(void);
void test_ui_core_on_tick_null_no_crash(void);
void test_ui_core_on_button_null_no_crash(void);
void test_ui_core_button_b_tracks_state(void);
void test_ui_core_button_c_tracks_state(void);
void test_ui_core_button_unknown_id_no_change(void);
void test_ui_core_scene_wraps_after_metrics(void);
void test_ui_core_init_sets_bg_dark(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_core_init_sets_defaults);
    RUN_TEST(test_ui_core_tick_increments_time);
    RUN_TEST(test_ui_core_button_a_cycles_scene_on_press);
    RUN_TEST(test_ui_core_on_rpc_bg_sets_rgb565);
    RUN_TEST(test_ui_core_on_rpc_bg_null_no_crash);
    RUN_TEST(test_ui_core_init_null_no_crash);
    RUN_TEST(test_ui_core_on_tick_null_no_crash);
    RUN_TEST(test_ui_core_on_button_null_no_crash);
    RUN_TEST(test_ui_core_button_b_tracks_state);
    RUN_TEST(test_ui_core_button_c_tracks_state);
    RUN_TEST(test_ui_core_button_unknown_id_no_change);
    RUN_TEST(test_ui_core_scene_wraps_after_metrics);
    RUN_TEST(test_ui_core_init_sets_bg_dark);
    return UNITY_END();
}

#endif
