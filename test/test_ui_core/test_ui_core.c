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

void test_ui_core_init_sets_defaults(void)
{
    ui_state_t st;
    ui_core_init(&st);

    TEST_ASSERT_EQUAL_UINT16(0x0821, st.bg);
    TEST_ASSERT_EQUAL_UINT32(0u, st.t);
    TEST_ASSERT_EQUAL_UINT8(0u, st.btnA);
    TEST_ASSERT_EQUAL_UINT8(0u, st.btnB);
    TEST_ASSERT_EQUAL_UINT8(0u, st.btnC);
    TEST_ASSERT_EQUAL_UINT(UI_SCENE_HOME, st.scene);
}

void test_ui_core_on_rpc_bg_sets_color(void)
{
    ui_state_t st;
    ui_core_init(&st);

    /* Pure red RGB -> expect high bits set in RGB565 (0xF800) */
    ui_core_on_rpc_bg(&st, 0xFF0000u);
    TEST_ASSERT_EQUAL_UINT16(0xF800, st.bg);

    /* Pure green RGB -> 0x07E0 */
    ui_core_on_rpc_bg(&st, 0x00FF00u);
    TEST_ASSERT_EQUAL_UINT16(0x07E0, st.bg);

    /* Pure blue RGB -> 0x001F */
    ui_core_on_rpc_bg(&st, 0x0000FFu);
    TEST_ASSERT_EQUAL_UINT16(0x001F, st.bg);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_button_a_cycles_scenes);
    RUN_TEST(test_ui_core_init_sets_defaults);
    RUN_TEST(test_ui_core_on_rpc_bg_sets_color);
    return UNITY_END();
}
