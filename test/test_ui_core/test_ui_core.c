#include <unity.h>

#include "services/ui/ui_core.h"

void setUp(void) {}
void tearDown(void) {}

static void press_and_release(ui_state_t *st)
{
    ui_core_on_button(st, 0, true);
    ui_core_on_button(st, 0, false);
}

void test_button_a_cycles_scenes(void)
{
    ui_state_t st;
    ui_core_init(&st);

    TEST_ASSERT_EQUAL_UINT(UI_SCENE_HOME, st.scene);

    press_and_release(&st);
    TEST_ASSERT_EQUAL_UINT(UI_SCENE_SETTINGS, st.scene);

    press_and_release(&st);
    TEST_ASSERT_EQUAL_UINT(UI_SCENE_METRICS, st.scene);

    press_and_release(&st);
    TEST_ASSERT_EQUAL_UINT(UI_SCENE_HOME, st.scene);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_button_a_cycles_scenes);
    return UNITY_END();
}
