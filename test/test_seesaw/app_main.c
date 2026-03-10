#include "unity.h"

void test_read_sends_prefix_and_returns_data(void);
void test_read_null_out_returns_invalid_arg(void);
void test_read_i32_null_returns_invalid_arg(void);
void test_read_zero_len_returns_ok(void);
void test_read_write_error_propagates(void);
void test_read_i2c_read_error_propagates(void);
void test_write_sends_prefix_plus_data(void);
void test_write_null_data_zero_len(void);
void test_write_over_64_returns_invalid_size(void);
void test_read_u8_success(void);
void test_read_u8_null_returns_invalid_arg(void);
void test_read_u16_big_endian(void);
void test_read_u16_null_returns_invalid_arg(void);
void test_read_u16_error_propagates(void);
void test_read_u32_big_endian(void);
void test_read_u32_null_returns_invalid_arg(void);
void test_read_i32_positive(void);
void test_read_i32_negative(void);
void test_read_i32_error_propagates(void);
void test_pin_mode_bulk_input(void);
void test_pin_mode_bulk_input_pullup(void);
void test_pin_mode_bulk_pullup_write_error_aborts(void);
void test_pin_mode_bulk_invalid_mode(void);
void test_hw_id_supported_known(void);
void test_hw_id_supported_unknown(void);

#ifdef ESP_PLATFORM

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_read_sends_prefix_and_returns_data);
    RUN_TEST(test_read_null_out_returns_invalid_arg);
    RUN_TEST(test_read_zero_len_returns_ok);
    RUN_TEST(test_read_write_error_propagates);
    RUN_TEST(test_read_i2c_read_error_propagates);
    RUN_TEST(test_write_sends_prefix_plus_data);
    RUN_TEST(test_write_null_data_zero_len);
    RUN_TEST(test_write_over_64_returns_invalid_size);
    RUN_TEST(test_read_u8_success);
    RUN_TEST(test_read_u8_null_returns_invalid_arg);
    RUN_TEST(test_read_u16_big_endian);
    RUN_TEST(test_read_u16_null_returns_invalid_arg);
    RUN_TEST(test_read_u16_error_propagates);
    RUN_TEST(test_read_u32_big_endian);
    RUN_TEST(test_read_u32_null_returns_invalid_arg);
    RUN_TEST(test_read_i32_positive);
    RUN_TEST(test_read_i32_negative);
    RUN_TEST(test_read_i32_null_returns_invalid_arg);
    RUN_TEST(test_read_i32_error_propagates);
    RUN_TEST(test_pin_mode_bulk_input);
    RUN_TEST(test_pin_mode_bulk_input_pullup);
    RUN_TEST(test_pin_mode_bulk_pullup_write_error_aborts);
    RUN_TEST(test_pin_mode_bulk_invalid_mode);
    RUN_TEST(test_hw_id_supported_known);
    RUN_TEST(test_hw_id_supported_unknown);
    UNITY_END();
}

#else

#include "unity_internals.h"
#include <stdio.h>

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_read_sends_prefix_and_returns_data);
    RUN_TEST(test_read_null_out_returns_invalid_arg);
    RUN_TEST(test_read_zero_len_returns_ok);
    RUN_TEST(test_read_write_error_propagates);
    RUN_TEST(test_read_i2c_read_error_propagates);
    RUN_TEST(test_write_sends_prefix_plus_data);
    RUN_TEST(test_write_null_data_zero_len);
    RUN_TEST(test_write_over_64_returns_invalid_size);
    RUN_TEST(test_read_u8_success);
    RUN_TEST(test_read_u8_null_returns_invalid_arg);
    RUN_TEST(test_read_u16_big_endian);
    RUN_TEST(test_read_u16_null_returns_invalid_arg);
    RUN_TEST(test_read_u16_error_propagates);
    RUN_TEST(test_read_u32_big_endian);
    RUN_TEST(test_read_u32_null_returns_invalid_arg);
    RUN_TEST(test_read_i32_positive);
    RUN_TEST(test_read_i32_negative);
    RUN_TEST(test_read_i32_null_returns_invalid_arg);
    RUN_TEST(test_read_i32_error_propagates);
    RUN_TEST(test_pin_mode_bulk_input);
    RUN_TEST(test_pin_mode_bulk_input_pullup);
    RUN_TEST(test_pin_mode_bulk_pullup_write_error_aborts);
    RUN_TEST(test_pin_mode_bulk_invalid_mode);
    RUN_TEST(test_hw_id_supported_known);
    RUN_TEST(test_hw_id_supported_unknown);
    return UNITY_END();
}

#endif
