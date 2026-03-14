/* Unity test runner for test_ui_app */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* format_heap tests */
extern void test_format_heap_zero(void);
extern void test_format_heap_bytes(void);
extern void test_format_heap_1023_bytes(void);
extern void test_format_heap_1024_kilobytes(void);
extern void test_format_heap_kilobytes(void);
extern void test_format_heap_megabytes(void);
extern void test_format_heap_megabyte_boundary(void);
extern void test_format_heap_null_out(void);
extern void test_format_heap_zero_cap(void);
extern void test_format_heap_small_buffer(void);

/* input_name tests */
extern void test_input_name_a(void);
extern void test_input_name_b(void);
extern void test_input_name_up(void);
extern void test_input_name_enc_cw(void);
extern void test_input_name_enc_hold(void);
extern void test_input_name_select(void);
extern void test_input_name_enc3_press(void);
extern void test_input_name_enc5_ccw(void);
extern void test_input_name_unknown(void);

/* input_state tests */
extern void test_input_state_enc_press(void);
extern void test_input_state_enc2_hold(void);
extern void test_input_state_enc_cw(void);
extern void test_input_state_enc4_ccw(void);
extern void test_input_state_button_pressed(void);
extern void test_input_state_button_released(void);
extern void test_input_state_dpad_down_pressed(void);
extern void test_input_state_enc3_press(void);

/* is_back_button tests */
extern void test_back_button_b(void);
extern void test_back_button_enc_hold(void);
extern void test_back_button_enc2_hold(void);
extern void test_back_button_enc5_hold(void);
extern void test_not_back_button_a(void);
extern void test_not_back_button_enc_press(void);
extern void test_not_back_button_up(void);
extern void test_not_back_button_enc_cw(void);
extern void test_input_name_c(void);
extern void test_input_name_down(void);
extern void test_input_state_enc_ccw(void);
extern void test_back_button_enc3_hold(void);
extern void test_format_heap_large_value(void);

int main(void)
{
    UNITY_BEGIN();

    /* format_heap */
    RUN_TEST(test_format_heap_zero);
    RUN_TEST(test_format_heap_bytes);
    RUN_TEST(test_format_heap_1023_bytes);
    RUN_TEST(test_format_heap_1024_kilobytes);
    RUN_TEST(test_format_heap_kilobytes);
    RUN_TEST(test_format_heap_megabytes);
    RUN_TEST(test_format_heap_megabyte_boundary);
    RUN_TEST(test_format_heap_null_out);
    RUN_TEST(test_format_heap_zero_cap);
    RUN_TEST(test_format_heap_small_buffer);

    /* input_name */
    RUN_TEST(test_input_name_a);
    RUN_TEST(test_input_name_b);
    RUN_TEST(test_input_name_up);
    RUN_TEST(test_input_name_enc_cw);
    RUN_TEST(test_input_name_enc_hold);
    RUN_TEST(test_input_name_select);
    RUN_TEST(test_input_name_enc3_press);
    RUN_TEST(test_input_name_enc5_ccw);
    RUN_TEST(test_input_name_unknown);

    /* input_state */
    RUN_TEST(test_input_state_enc_press);
    RUN_TEST(test_input_state_enc2_hold);
    RUN_TEST(test_input_state_enc_cw);
    RUN_TEST(test_input_state_enc4_ccw);
    RUN_TEST(test_input_state_button_pressed);
    RUN_TEST(test_input_state_button_released);
    RUN_TEST(test_input_state_dpad_down_pressed);
    RUN_TEST(test_input_state_enc3_press);

    /* is_back_button */
    RUN_TEST(test_back_button_b);
    RUN_TEST(test_back_button_enc_hold);
    RUN_TEST(test_back_button_enc2_hold);
    RUN_TEST(test_back_button_enc5_hold);
    RUN_TEST(test_not_back_button_a);
    RUN_TEST(test_not_back_button_enc_press);
    RUN_TEST(test_not_back_button_up);
    RUN_TEST(test_not_back_button_enc_cw);

    /* new edge-case tests */
    RUN_TEST(test_input_name_c);
    RUN_TEST(test_input_name_down);
    RUN_TEST(test_input_state_enc_ccw);
    RUN_TEST(test_back_button_enc3_hold);
    RUN_TEST(test_format_heap_large_value);

    return UNITY_END();
}
