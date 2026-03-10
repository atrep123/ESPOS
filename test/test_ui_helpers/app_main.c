#include "unity.h"

#ifdef ESP_PLATFORM

void test_parse_uint_dec_simple(void);
void test_parse_uint_dec_zero(void);
void test_parse_uint_dec_trailing_chars(void);
void test_parse_uint_dec_null_string(void);
void test_parse_uint_dec_empty_string(void);
void test_parse_uint_dec_non_digit(void);
void test_parse_uint_dec_null_out(void);
void test_parse_uint_dec_large_number(void);
void test_parse_item_root_slot_basic(void);
void test_parse_item_root_slot_higher_index(void);
void test_parse_item_root_slot_null_id(void);
void test_parse_item_root_slot_empty_id(void);
void test_parse_item_root_slot_no_dot(void);
void test_parse_item_root_slot_not_item_prefix(void);
void test_parse_item_root_slot_dot_at_start(void);
void test_parse_item_root_slot_dot_at_end(void);
void test_parse_item_root_slot_small_root_buffer(void);
void test_parse_item_root_slot_null_root(void);
void test_parse_item_root_slot_null_out_slot(void);
void test_toast_reset(void);
void test_toast_reset_null_safe(void);
void test_toast_push_pop_single(void);
void test_toast_push_pop_fifo_order(void);
void test_toast_pop_empty(void);
void test_toast_pop_null_out(void);
void test_toast_push_overflow_drops_oldest(void);
void test_toast_push_null_message(void);
void test_toast_push_null_toast(void);
void test_toast_pop_null_toast(void);
void test_toast_push_pop_wraparound(void);
void test_toast_long_message_truncation(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_parse_uint_dec_simple);
    RUN_TEST(test_parse_uint_dec_zero);
    RUN_TEST(test_parse_uint_dec_trailing_chars);
    RUN_TEST(test_parse_uint_dec_null_string);
    RUN_TEST(test_parse_uint_dec_empty_string);
    RUN_TEST(test_parse_uint_dec_non_digit);
    RUN_TEST(test_parse_uint_dec_null_out);
    RUN_TEST(test_parse_uint_dec_large_number);
    RUN_TEST(test_parse_item_root_slot_basic);
    RUN_TEST(test_parse_item_root_slot_higher_index);
    RUN_TEST(test_parse_item_root_slot_null_id);
    RUN_TEST(test_parse_item_root_slot_empty_id);
    RUN_TEST(test_parse_item_root_slot_no_dot);
    RUN_TEST(test_parse_item_root_slot_not_item_prefix);
    RUN_TEST(test_parse_item_root_slot_dot_at_start);
    RUN_TEST(test_parse_item_root_slot_dot_at_end);
    RUN_TEST(test_parse_item_root_slot_small_root_buffer);
    RUN_TEST(test_parse_item_root_slot_null_root);
    RUN_TEST(test_parse_item_root_slot_null_out_slot);
    RUN_TEST(test_toast_reset);
    RUN_TEST(test_toast_reset_null_safe);
    RUN_TEST(test_toast_push_pop_single);
    RUN_TEST(test_toast_push_pop_fifo_order);
    RUN_TEST(test_toast_pop_empty);
    RUN_TEST(test_toast_pop_null_out);
    RUN_TEST(test_toast_push_overflow_drops_oldest);
    RUN_TEST(test_toast_push_null_message);
    RUN_TEST(test_toast_push_null_toast);
    RUN_TEST(test_toast_pop_null_toast);
    RUN_TEST(test_toast_push_pop_wraparound);
    RUN_TEST(test_toast_long_message_truncation);
    UNITY_END();
}

#else

void test_parse_uint_dec_simple(void);
void test_parse_uint_dec_zero(void);
void test_parse_uint_dec_trailing_chars(void);
void test_parse_uint_dec_null_string(void);
void test_parse_uint_dec_empty_string(void);
void test_parse_uint_dec_non_digit(void);
void test_parse_uint_dec_null_out(void);
void test_parse_uint_dec_large_number(void);
void test_parse_item_root_slot_basic(void);
void test_parse_item_root_slot_higher_index(void);
void test_parse_item_root_slot_null_id(void);
void test_parse_item_root_slot_empty_id(void);
void test_parse_item_root_slot_no_dot(void);
void test_parse_item_root_slot_not_item_prefix(void);
void test_parse_item_root_slot_dot_at_start(void);
void test_parse_item_root_slot_dot_at_end(void);
void test_parse_item_root_slot_small_root_buffer(void);
void test_parse_item_root_slot_null_root(void);
void test_parse_item_root_slot_null_out_slot(void);
void test_toast_reset(void);
void test_toast_reset_null_safe(void);
void test_toast_push_pop_single(void);
void test_toast_push_pop_fifo_order(void);
void test_toast_pop_empty(void);
void test_toast_pop_null_out(void);
void test_toast_push_overflow_drops_oldest(void);
void test_toast_push_null_message(void);
void test_toast_push_null_toast(void);
void test_toast_pop_null_toast(void);
void test_toast_push_pop_wraparound(void);
void test_toast_long_message_truncation(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_parse_uint_dec_simple);
    RUN_TEST(test_parse_uint_dec_zero);
    RUN_TEST(test_parse_uint_dec_trailing_chars);
    RUN_TEST(test_parse_uint_dec_null_string);
    RUN_TEST(test_parse_uint_dec_empty_string);
    RUN_TEST(test_parse_uint_dec_non_digit);
    RUN_TEST(test_parse_uint_dec_null_out);
    RUN_TEST(test_parse_uint_dec_large_number);
    RUN_TEST(test_parse_item_root_slot_basic);
    RUN_TEST(test_parse_item_root_slot_higher_index);
    RUN_TEST(test_parse_item_root_slot_null_id);
    RUN_TEST(test_parse_item_root_slot_empty_id);
    RUN_TEST(test_parse_item_root_slot_no_dot);
    RUN_TEST(test_parse_item_root_slot_not_item_prefix);
    RUN_TEST(test_parse_item_root_slot_dot_at_start);
    RUN_TEST(test_parse_item_root_slot_dot_at_end);
    RUN_TEST(test_parse_item_root_slot_small_root_buffer);
    RUN_TEST(test_parse_item_root_slot_null_root);
    RUN_TEST(test_parse_item_root_slot_null_out_slot);
    RUN_TEST(test_toast_reset);
    RUN_TEST(test_toast_reset_null_safe);
    RUN_TEST(test_toast_push_pop_single);
    RUN_TEST(test_toast_push_pop_fifo_order);
    RUN_TEST(test_toast_pop_empty);
    RUN_TEST(test_toast_pop_null_out);
    RUN_TEST(test_toast_push_overflow_drops_oldest);
    RUN_TEST(test_toast_push_null_message);
    RUN_TEST(test_toast_push_null_toast);
    RUN_TEST(test_toast_pop_null_toast);
    RUN_TEST(test_toast_push_pop_wraparound);
    RUN_TEST(test_toast_long_message_truncation);
    return UNITY_END();
}

#endif
