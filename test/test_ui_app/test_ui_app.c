/*
 * Unit tests for ui_app pure-logic helpers:
 * - ui_app_format_heap: byte count → human-readable string
 * - ui_app_input_name: INPUT_ID_* → display name
 * - ui_app_input_state: input event → state string
 * - ui_app_is_back_button: back-button ID detection
 *
 * All functions are pure — no FreeRTOS, hardware, or msgbus dependencies.
 */

#include "unity.h"
#include <string.h>
#include "services/ui_app/ui_app.h"
#include "services/input/input.h"

void setUp(void) {}
void tearDown(void) {}

/* ================================================================== */
/* ui_app_format_heap                                                  */
/* ================================================================== */

void test_format_heap_zero(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 0);
    TEST_ASSERT_EQUAL_STRING("0B", buf);
}

void test_format_heap_bytes(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 512);
    TEST_ASSERT_EQUAL_STRING("512B", buf);
}

void test_format_heap_1023_bytes(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 1023);
    TEST_ASSERT_EQUAL_STRING("1023B", buf);
}

void test_format_heap_1024_kilobytes(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 1024);
    TEST_ASSERT_EQUAL_STRING("1K", buf);
}

void test_format_heap_kilobytes(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 48 * 1024);
    TEST_ASSERT_EQUAL_STRING("48K", buf);
}

void test_format_heap_megabytes(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 3 * 1024 * 1024);
    TEST_ASSERT_EQUAL_STRING("3M", buf);
}

void test_format_heap_megabyte_boundary(void)
{
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 1024 * 1024);
    TEST_ASSERT_EQUAL_STRING("1M", buf);
}

void test_format_heap_null_out(void)
{
    /* Should not crash. */
    ui_app_format_heap(NULL, 16, 1024);
}

void test_format_heap_zero_cap(void)
{
    char buf[16] = "old";
    ui_app_format_heap(buf, 0, 1024);
    TEST_ASSERT_EQUAL_STRING("old", buf);  /* unchanged */
}

void test_format_heap_small_buffer(void)
{
    char buf[3] = {0};
    ui_app_format_heap(buf, sizeof(buf), 48 * 1024);
    /* snprintf truncates: "48K" → "48" + NUL */
    TEST_ASSERT_EQUAL_STRING("48", buf);
}

/* ================================================================== */
/* ui_app_input_name                                                   */
/* ================================================================== */

void test_input_name_a(void)
{
    TEST_ASSERT_EQUAL_STRING("A", ui_app_input_name(INPUT_ID_A));
}

void test_input_name_b(void)
{
    TEST_ASSERT_EQUAL_STRING("B", ui_app_input_name(INPUT_ID_B));
}

void test_input_name_up(void)
{
    TEST_ASSERT_EQUAL_STRING("Up", ui_app_input_name(INPUT_ID_UP));
}

void test_input_name_enc_cw(void)
{
    TEST_ASSERT_EQUAL_STRING("Enc CW", ui_app_input_name(INPUT_ID_ENC_CW));
}

void test_input_name_enc_hold(void)
{
    TEST_ASSERT_EQUAL_STRING("Enc hold", ui_app_input_name(INPUT_ID_ENC_HOLD));
}

void test_input_name_select(void)
{
    TEST_ASSERT_EQUAL_STRING("Select", ui_app_input_name(INPUT_ID_SELECT));
}

void test_input_name_enc3_press(void)
{
    TEST_ASSERT_EQUAL_STRING("Enc3 press", ui_app_input_name(INPUT_ID_ENC3_PRESS));
}

void test_input_name_enc5_ccw(void)
{
    TEST_ASSERT_EQUAL_STRING("Enc5 CCW", ui_app_input_name(INPUT_ID_ENC5_CCW));
}

void test_input_name_unknown(void)
{
    TEST_ASSERT_EQUAL_STRING("Unknown", ui_app_input_name(255));
}

/* ================================================================== */
/* ui_app_input_state                                                  */
/* ================================================================== */

void test_input_state_enc_press(void)
{
    TEST_ASSERT_EQUAL_STRING("press", ui_app_input_state(INPUT_ID_ENC_PRESS, 1));
}

void test_input_state_enc2_hold(void)
{
    TEST_ASSERT_EQUAL_STRING("hold", ui_app_input_state(INPUT_ID_ENC2_HOLD, 1));
}

void test_input_state_enc_cw(void)
{
    TEST_ASSERT_EQUAL_STRING("cw", ui_app_input_state(INPUT_ID_ENC_CW, 1));
}

void test_input_state_enc4_ccw(void)
{
    TEST_ASSERT_EQUAL_STRING("ccw", ui_app_input_state(INPUT_ID_ENC4_CCW, 1));
}

void test_input_state_button_pressed(void)
{
    TEST_ASSERT_EQUAL_STRING("down", ui_app_input_state(INPUT_ID_A, 1));
}

void test_input_state_button_released(void)
{
    TEST_ASSERT_EQUAL_STRING("up", ui_app_input_state(INPUT_ID_A, 0));
}

void test_input_state_dpad_down_pressed(void)
{
    TEST_ASSERT_EQUAL_STRING("down", ui_app_input_state(INPUT_ID_DOWN, 1));
}

void test_input_state_enc3_press(void)
{
    TEST_ASSERT_EQUAL_STRING("press", ui_app_input_state(INPUT_ID_ENC3_PRESS, 1));
}

/* ================================================================== */
/* ui_app_is_back_button                                               */
/* ================================================================== */

void test_back_button_b(void)
{
    TEST_ASSERT_EQUAL(1, ui_app_is_back_button(INPUT_ID_B));
}

void test_back_button_enc_hold(void)
{
    TEST_ASSERT_EQUAL(1, ui_app_is_back_button(INPUT_ID_ENC_HOLD));
}

void test_back_button_enc2_hold(void)
{
    TEST_ASSERT_EQUAL(1, ui_app_is_back_button(INPUT_ID_ENC2_HOLD));
}

void test_back_button_enc5_hold(void)
{
    TEST_ASSERT_EQUAL(1, ui_app_is_back_button(INPUT_ID_ENC5_HOLD));
}

void test_not_back_button_a(void)
{
    TEST_ASSERT_EQUAL(0, ui_app_is_back_button(INPUT_ID_A));
}

void test_not_back_button_enc_press(void)
{
    TEST_ASSERT_EQUAL(0, ui_app_is_back_button(INPUT_ID_ENC_PRESS));
}

void test_not_back_button_up(void)
{
    TEST_ASSERT_EQUAL(0, ui_app_is_back_button(INPUT_ID_UP));
}

void test_not_back_button_enc_cw(void)
{
    TEST_ASSERT_EQUAL(0, ui_app_is_back_button(INPUT_ID_ENC_CW));
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_input_name_c(void)
{
    TEST_ASSERT_EQUAL_STRING("C", ui_app_input_name(INPUT_ID_C));
}

void test_input_name_down(void)
{
    TEST_ASSERT_EQUAL_STRING("Down", ui_app_input_name(INPUT_ID_DOWN));
}

void test_input_state_enc_ccw(void)
{
    TEST_ASSERT_EQUAL_STRING("ccw", ui_app_input_state(INPUT_ID_ENC_CCW, 1));
}

void test_back_button_enc3_hold(void)
{
    TEST_ASSERT_EQUAL(1, ui_app_is_back_button(INPUT_ID_ENC3_HOLD));
}

void test_format_heap_large_value(void)
{
    /* 4 GB - 1 */
    char buf[16];
    ui_app_format_heap(buf, sizeof(buf), 4294967295U);
    TEST_ASSERT_EQUAL_STRING("4095M", buf);
}
