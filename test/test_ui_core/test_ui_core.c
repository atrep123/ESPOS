#include "unity.h"

#include <limits.h>
#include <string.h>

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

void test_ui_core_on_rpc_bg_sets_rgb565(void)
{
    ui_state_t st;
    ui_core_init(&st);

    /* Pure white 0xFFFFFF → RGB565 = 0xFFFF */
    ui_core_on_rpc_bg(&st, 0xFFFFFF);
    TEST_ASSERT_EQUAL_UINT16(0xFFFF, st.bg);

    /* Pure red 0xFF0000 → RGB565 = (0xF8<<8) | 0 | 0 = 0xF800 */
    ui_core_on_rpc_bg(&st, 0xFF0000);
    TEST_ASSERT_EQUAL_UINT16(0xF800, st.bg);

    /* Pure green 0x00FF00 → RGB565 = 0 | (0xFC<<3) | 0 = 0x07E0 */
    ui_core_on_rpc_bg(&st, 0x00FF00);
    TEST_ASSERT_EQUAL_UINT16(0x07E0, st.bg);

    /* Pure blue 0x0000FF → RGB565 = 0 | 0 | (0xFF>>3) = 0x001F */
    ui_core_on_rpc_bg(&st, 0x0000FF);
    TEST_ASSERT_EQUAL_UINT16(0x001F, st.bg);

    /* Black 0x000000 → RGB565 = 0x0000 */
    ui_core_on_rpc_bg(&st, 0x000000);
    TEST_ASSERT_EQUAL_UINT16(0x0000, st.bg);
}

void test_ui_core_on_rpc_bg_null_no_crash(void)
{
    ui_core_on_rpc_bg(NULL, 0xFF0000);
}

void test_ui_core_init_null_no_crash(void)
{
    ui_core_init(NULL);
}

void test_ui_core_on_tick_null_no_crash(void)
{
    ui_core_on_tick(NULL);
}

void test_ui_core_on_button_null_no_crash(void)
{
    ui_core_on_button(NULL, 0, true);
}

void test_ui_core_button_b_tracks_state(void)
{
    ui_state_t st;
    ui_core_init(&st);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnB);

    ui_core_on_button(&st, 1, true);
    TEST_ASSERT_EQUAL_UINT8(1, st.btnB);

    ui_core_on_button(&st, 1, false);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnB);
}

void test_ui_core_button_c_tracks_state(void)
{
    ui_state_t st;
    ui_core_init(&st);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnC);

    ui_core_on_button(&st, 2, true);
    TEST_ASSERT_EQUAL_UINT8(1, st.btnC);

    ui_core_on_button(&st, 2, false);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnC);
}

void test_ui_core_button_unknown_id_no_change(void)
{
    ui_state_t st;
    ui_core_init(&st);

    ui_core_on_button(&st, 99, true);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnA);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnB);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnC);
}

void test_ui_core_scene_wraps_after_metrics(void)
{
    ui_state_t st;
    ui_core_init(&st);

    ui_core_on_button(&st, 0, true);  /* HOME → SETTINGS */
    ui_core_on_button(&st, 0, false);
    ui_core_on_button(&st, 0, true);  /* SETTINGS → METRICS */
    ui_core_on_button(&st, 0, false);
    ui_core_on_button(&st, 0, true);  /* METRICS → HOME (wraps) */
    TEST_ASSERT_EQUAL(UI_SCENE_HOME, st.scene);
}

void test_ui_core_init_sets_bg_dark(void)
{
    ui_state_t st;
    ui_core_init(&st);
    /* RGB(8,8,8) → RGB565 = (0x08&0xF8)<<8 | (0x08&0xFC)<<3 | 0x08>>3 */
    uint16_t expected = ((uint16_t)(0x08 & 0xF8) << 8) |
                        ((uint16_t)(0x08 & 0xFC) << 3) |
                        (uint16_t)(0x08 >> 3);
    TEST_ASSERT_EQUAL_UINT16(expected, st.bg);
}

void test_ui_core_init_clears_metrics(void)
{
    ui_state_t st;
    /* Fill with garbage */
    memset(&st, 0xFF, sizeof(st));
    ui_core_init(&st);
    TEST_ASSERT_EQUAL_UINT32(0, st.metrics_free_heap);
    TEST_ASSERT_EQUAL_UINT32(0, st.metrics_min_free_heap);
}

void test_ui_core_button_a_press_sets_btnA(void)
{
    ui_state_t st;
    ui_core_init(&st);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnA);

    ui_core_on_button(&st, 0, true);
    TEST_ASSERT_EQUAL_UINT8(1, st.btnA);

    ui_core_on_button(&st, 0, false);
    TEST_ASSERT_EQUAL_UINT8(0, st.btnA);
}

/* ================================================================== */
/* Additional edge cases                                               */
/* ================================================================== */

void test_ui_core_tick_overflow(void)
{
    ui_state_t st;
    ui_core_init(&st);
    st.t = INT32_MAX;
    ui_core_on_tick(&st);
    /* Standard signed overflow wraps to INT32_MIN (undefined in C but
     * this is how the firmware behaves on the target). */
    TEST_ASSERT_EQUAL_INT32(INT32_MIN, st.t);
}

void test_ui_core_rgb565_intermediate(void)
{
    ui_state_t st;
    ui_core_init(&st);
    /* 0x0B1E3A → R=0x0B, G=0x1E, B=0x3A */
    ui_core_on_rpc_bg(&st, 0x0B1E3A);
    uint16_t expected = ((uint16_t)(0x0B & 0xF8) << 8) |
                        ((uint16_t)(0x1E & 0xFC) << 3) |
                        (uint16_t)(0x3A >> 3);
    TEST_ASSERT_EQUAL_UINT16(expected, st.bg);
}

void test_ui_core_rapid_button_repress(void)
{
    ui_state_t st;
    ui_core_init(&st);
    /* Press twice without release — btnA stays 1, scene advances twice */
    ui_core_on_button(&st, 0, true);
    TEST_ASSERT_EQUAL(UI_SCENE_SETTINGS, st.scene);
    ui_core_on_button(&st, 0, true);
    TEST_ASSERT_EQUAL(UI_SCENE_METRICS, st.scene);
    TEST_ASSERT_EQUAL_UINT8(1, st.btnA);
}

void test_ui_core_rpc_bg_preserves_other_fields(void)
{
    ui_state_t st;
    ui_core_init(&st);
    st.t = 42;
    st.btnA = 1;
    st.scene = UI_SCENE_METRICS;
    st.metrics_free_heap = 1234;

    ui_core_on_rpc_bg(&st, 0xFF0000);

    TEST_ASSERT_EQUAL_UINT16(0xF800, st.bg);
    TEST_ASSERT_EQUAL_INT32(42, st.t);
    TEST_ASSERT_EQUAL_UINT8(1, st.btnA);
    TEST_ASSERT_EQUAL(UI_SCENE_METRICS, st.scene);
    TEST_ASSERT_EQUAL_UINT32(1234, st.metrics_free_heap);
}

void test_ui_core_multiple_full_scene_loops(void)
{
    ui_state_t st;
    ui_core_init(&st);
    /* Cycle through all scenes twice (6 presses) */
    for (int i = 0; i < 6; ++i) {
        ui_core_on_button(&st, 0, true);
        ui_core_on_button(&st, 0, false);
    }
    /* 6 presses: HOME→S→M→H→S→M→H → back at HOME */
    TEST_ASSERT_EQUAL(UI_SCENE_HOME, st.scene);
}

/* --- Fuzz: rapid tick stress (large t) --- */
void test_ui_core_rapid_tick_stress(void)
{
    ui_state_t st;
    ui_core_init(&st);
    /* Tick 10000 times - must not overflow or crash */
    for (int i = 0; i < 10000; ++i) {
        ui_core_on_tick(&st);
    }
    TEST_ASSERT_EQUAL_INT32(10000, st.t);
}

