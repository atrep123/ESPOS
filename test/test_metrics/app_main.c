#include "unity.h"

#ifdef ESP_PLATFORM

void test_metrics_tick_increments_counter(void);
void test_metrics_tick_publishes_at_100(void);
void test_metrics_tick_not_at_99(void);
void test_metrics_tick_full_cycle(void);
void test_metrics_tick_multiple_cycles(void);
void test_metrics_publishes_correct_topic(void);
void test_metrics_publishes_heap_values(void);
void test_metrics_no_publish_no_message(void);
void test_metrics_tick_null_counter(void);
void test_metrics_tick_large_initial_counter(void);
void test_metrics_tick_consecutive_publishes(void);
void test_metrics_counter_at_one_below(void);
void test_metrics_queue_receives_multiple_messages(void);
void test_metrics_heap_values_each_publish(void);
void test_metrics_tick_counter_wraps_from_max(void);
void test_metrics_tick_exactly_at_100(void);
void test_metrics_no_queue_leak(void);
void test_metrics_counter_reset_after_publish(void);
void test_metrics_counter_at_50_no_publish(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_metrics_tick_increments_counter);
    RUN_TEST(test_metrics_tick_publishes_at_100);
    RUN_TEST(test_metrics_tick_not_at_99);
    RUN_TEST(test_metrics_tick_full_cycle);
    RUN_TEST(test_metrics_tick_multiple_cycles);
    RUN_TEST(test_metrics_publishes_correct_topic);
    RUN_TEST(test_metrics_publishes_heap_values);
    RUN_TEST(test_metrics_no_publish_no_message);
    RUN_TEST(test_metrics_tick_null_counter);
    RUN_TEST(test_metrics_tick_large_initial_counter);
    RUN_TEST(test_metrics_tick_consecutive_publishes);
    RUN_TEST(test_metrics_counter_at_one_below);
    RUN_TEST(test_metrics_queue_receives_multiple_messages);
    RUN_TEST(test_metrics_heap_values_each_publish);
    RUN_TEST(test_metrics_tick_counter_wraps_from_max);
    RUN_TEST(test_metrics_tick_exactly_at_100);
    RUN_TEST(test_metrics_no_queue_leak);
    RUN_TEST(test_metrics_counter_reset_after_publish);
    RUN_TEST(test_metrics_counter_at_50_no_publish);
    UNITY_END();
}

#else

void test_metrics_tick_increments_counter(void);
void test_metrics_tick_publishes_at_100(void);
void test_metrics_tick_not_at_99(void);
void test_metrics_tick_full_cycle(void);
void test_metrics_tick_multiple_cycles(void);
void test_metrics_publishes_correct_topic(void);
void test_metrics_publishes_heap_values(void);
void test_metrics_no_publish_no_message(void);
void test_metrics_tick_null_counter(void);
void test_metrics_tick_large_initial_counter(void);
void test_metrics_tick_consecutive_publishes(void);
void test_metrics_counter_at_one_below(void);
void test_metrics_queue_receives_multiple_messages(void);
void test_metrics_heap_values_each_publish(void);
void test_metrics_tick_counter_wraps_from_max(void);
void test_metrics_tick_exactly_at_100(void);
void test_metrics_no_queue_leak(void);
void test_metrics_counter_reset_after_publish(void);
void test_metrics_counter_at_50_no_publish(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_metrics_tick_increments_counter);
    RUN_TEST(test_metrics_tick_publishes_at_100);
    RUN_TEST(test_metrics_tick_not_at_99);
    RUN_TEST(test_metrics_tick_full_cycle);
    RUN_TEST(test_metrics_tick_multiple_cycles);
    RUN_TEST(test_metrics_publishes_correct_topic);
    RUN_TEST(test_metrics_publishes_heap_values);
    RUN_TEST(test_metrics_no_publish_no_message);
    RUN_TEST(test_metrics_tick_null_counter);
    RUN_TEST(test_metrics_tick_large_initial_counter);
    RUN_TEST(test_metrics_tick_consecutive_publishes);
    RUN_TEST(test_metrics_counter_at_one_below);
    RUN_TEST(test_metrics_queue_receives_multiple_messages);
    RUN_TEST(test_metrics_heap_values_each_publish);
    RUN_TEST(test_metrics_tick_counter_wraps_from_max);
    RUN_TEST(test_metrics_tick_exactly_at_100);
    RUN_TEST(test_metrics_no_queue_leak);
    RUN_TEST(test_metrics_counter_reset_after_publish);
    RUN_TEST(test_metrics_counter_at_50_no_publish);
    return UNITY_END();
}

#endif
