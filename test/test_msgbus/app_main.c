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
    return UNITY_END();
}

#endif
