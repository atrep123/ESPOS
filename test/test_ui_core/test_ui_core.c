#include "unity.h"

#include "services/ui/ui_core.h"

void setUp(void) {}
void tearDown(void) {}

void test_ui_core_init_sets_defaults(void)
{
    ui_state_t st;
    ui_core_init(&st);

    TEST_ASSERT_EQUAL_UINT32(0, st.t);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnA);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnB);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnC);
    TEST_ASSERT_EQUAL(UI_SCENE_HOME, st.scene);
}

void test_ui_core_tick_increments_time(void)
{
    ui_state_t st;
    ui_core_init(&st);
    ui_core_on_tick(&st);
    ui_core_on_tick(&st);
    TEST_ASSERT_EQUAL_INT32(2, st.t);
}

void test_ui_core_button_a_cycles_scene_on_press(void)
{
    ui_state_t st;
    ui_core_init(&st);

    TEST_ASSERT_EQUAL(UI_SCENE_HOME, st.scene);
    ui_core_on_button(&st, 0, true);
    TEST_ASSERT_EQUAL(UI_SCENE_SETTINGS, st.scene);
    ui_core_on_button(&st, 0, false);
    ui_core_on_button(&st, 0, true);
    TEST_ASSERT_EQUAL(UI_SCENE_METRICS, st.scene);
}

