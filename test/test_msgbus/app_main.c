#include "unity.h"

#ifdef ESP_PLATFORM

void test_bus_init_no_crash(void);
void test_bus_make_queue_returns_handle(void);
void test_bus_subscribe_and_publish_delivers(void);
void test_bus_publish_null_msg_no_crash(void);
void test_bus_publish_wrong_topic_not_delivered(void);
void test_bus_multiple_subscribers(void);
void test_bus_subscribe_out_of_range_topic_no_crash(void);
void test_bus_ui_cmd_message(void);
void test_bus_publish_queue_full_silent_drop(void);
void test_bus_subscribe_max_subs_exceeded_no_crash(void);
void test_bus_publish_negative_topic_no_crash(void);
void test_bus_reinit_clears_subscriptions(void);
void test_bus_subscribe_multiple_topics(void);
void test_bus_subscribe_null_queue_ignored(void);
void test_bus_metrics_union_delivery(void);
void test_bus_drop_count_initially_zero(void);
void test_bus_drop_count_increments_on_full_queue(void);
void test_bus_drop_count_reset_on_reinit(void);
void test_bus_drop_count_invalid_topic_returns_zero(void);
void test_bus_publish_no_subscribers(void);
void test_bus_subscribe_same_queue_twice(void);
void test_bus_drop_count_per_subscriber(void);
void test_bus_publish_all_topics_isolated(void);
void test_bus_burst_publish(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_bus_init_no_crash);
    RUN_TEST(test_bus_make_queue_returns_handle);
    RUN_TEST(test_bus_subscribe_and_publish_delivers);
    RUN_TEST(test_bus_publish_null_msg_no_crash);
    RUN_TEST(test_bus_publish_wrong_topic_not_delivered);
    RUN_TEST(test_bus_multiple_subscribers);
    RUN_TEST(test_bus_subscribe_out_of_range_topic_no_crash);
    RUN_TEST(test_bus_ui_cmd_message);
    RUN_TEST(test_bus_publish_queue_full_silent_drop);
    RUN_TEST(test_bus_subscribe_max_subs_exceeded_no_crash);
    RUN_TEST(test_bus_publish_negative_topic_no_crash);
    RUN_TEST(test_bus_reinit_clears_subscriptions);
    RUN_TEST(test_bus_subscribe_multiple_topics);
    RUN_TEST(test_bus_subscribe_null_queue_ignored);
    RUN_TEST(test_bus_metrics_union_delivery);
    RUN_TEST(test_bus_drop_count_initially_zero);
    RUN_TEST(test_bus_drop_count_increments_on_full_queue);
    RUN_TEST(test_bus_drop_count_reset_on_reinit);
    RUN_TEST(test_bus_drop_count_invalid_topic_returns_zero);
    RUN_TEST(test_bus_publish_no_subscribers);
    RUN_TEST(test_bus_subscribe_same_queue_twice);
    RUN_TEST(test_bus_drop_count_per_subscriber);
    RUN_TEST(test_bus_publish_all_topics_isolated);
    RUN_TEST(test_bus_burst_publish);
    RUN_TEST(test_bus_make_queue_depth_one);
    RUN_TEST(test_bus_publish_extreme_topic_values);
    RUN_TEST(test_bus_subscribe_extreme_topic_values);
    RUN_TEST(test_bus_drop_count_extreme_topics);
    RUN_TEST(test_bus_deinit_no_crash);
    RUN_TEST(test_bus_deinit_clears_subscriptions);
    RUN_TEST(test_bus_deinit_resets_drop_counts);
    UNITY_END();
}

#else

void test_bus_init_no_crash(void);
void test_bus_make_queue_returns_handle(void);
void test_bus_subscribe_and_publish_delivers(void);
void test_bus_publish_null_msg_no_crash(void);
void test_bus_publish_wrong_topic_not_delivered(void);
void test_bus_multiple_subscribers(void);
void test_bus_subscribe_out_of_range_topic_no_crash(void);
void test_bus_ui_cmd_message(void);
void test_bus_publish_queue_full_silent_drop(void);
void test_bus_subscribe_max_subs_exceeded_no_crash(void);
void test_bus_publish_negative_topic_no_crash(void);
void test_bus_reinit_clears_subscriptions(void);
void test_bus_subscribe_multiple_topics(void);
void test_bus_subscribe_null_queue_ignored(void);
void test_bus_metrics_union_delivery(void);
void test_bus_drop_count_initially_zero(void);
void test_bus_drop_count_increments_on_full_queue(void);
void test_bus_drop_count_reset_on_reinit(void);
void test_bus_drop_count_invalid_topic_returns_zero(void);
void test_bus_publish_no_subscribers(void);
void test_bus_subscribe_same_queue_twice(void);
void test_bus_drop_count_per_subscriber(void);
void test_bus_publish_all_topics_isolated(void);
void test_bus_burst_publish(void);
void test_bus_make_queue_depth_one(void);
void test_bus_publish_extreme_topic_values(void);
void test_bus_subscribe_extreme_topic_values(void);
void test_bus_drop_count_extreme_topics(void);
void test_bus_deinit_no_crash(void);
void test_bus_deinit_clears_subscriptions(void);
void test_bus_deinit_resets_drop_counts(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_bus_init_no_crash);
    RUN_TEST(test_bus_make_queue_returns_handle);
    RUN_TEST(test_bus_subscribe_and_publish_delivers);
    RUN_TEST(test_bus_publish_null_msg_no_crash);
    RUN_TEST(test_bus_publish_wrong_topic_not_delivered);
    RUN_TEST(test_bus_multiple_subscribers);
    RUN_TEST(test_bus_subscribe_out_of_range_topic_no_crash);
    RUN_TEST(test_bus_ui_cmd_message);
    RUN_TEST(test_bus_publish_queue_full_silent_drop);
    RUN_TEST(test_bus_subscribe_max_subs_exceeded_no_crash);
    RUN_TEST(test_bus_publish_negative_topic_no_crash);
    RUN_TEST(test_bus_reinit_clears_subscriptions);
    RUN_TEST(test_bus_subscribe_multiple_topics);
    RUN_TEST(test_bus_subscribe_null_queue_ignored);
    RUN_TEST(test_bus_metrics_union_delivery);
    RUN_TEST(test_bus_drop_count_initially_zero);
    RUN_TEST(test_bus_drop_count_increments_on_full_queue);
    RUN_TEST(test_bus_drop_count_reset_on_reinit);
    RUN_TEST(test_bus_drop_count_invalid_topic_returns_zero);
    RUN_TEST(test_bus_publish_no_subscribers);
    RUN_TEST(test_bus_subscribe_same_queue_twice);
    RUN_TEST(test_bus_drop_count_per_subscriber);
    RUN_TEST(test_bus_publish_all_topics_isolated);
    RUN_TEST(test_bus_burst_publish);
    RUN_TEST(test_bus_make_queue_depth_one);
    RUN_TEST(test_bus_publish_extreme_topic_values);
    RUN_TEST(test_bus_subscribe_extreme_topic_values);
    RUN_TEST(test_bus_drop_count_extreme_topics);
    RUN_TEST(test_bus_deinit_no_crash);
    RUN_TEST(test_bus_deinit_clears_subscriptions);
    RUN_TEST(test_bus_deinit_resets_drop_counts);
    return UNITY_END();
}

#endif
