#include "unity.h"

#include <string.h>

#include "kernel/msgbus.h"

void setUp(void) { bus_init(); }
void tearDown(void) {}

void test_bus_init_no_crash(void)
{
    bus_init();
}

void test_bus_make_queue_returns_handle(void)
{
    QueueHandle_t q = bus_make_queue(4);
    TEST_ASSERT_NOT_NULL(q);
    vQueueDelete(q);
}

void test_bus_subscribe_and_publish_delivers(void)
{
    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t out;
    memset(&out, 0, sizeof(out));
    out.topic = TOP_TICK_10MS;
    out.u.tick.tick = 42;
    bus_publish(&out);

    msg_t recv;
    memset(&recv, 0, sizeof(recv));
    int ok = xQueueReceive(q, &recv, 0);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_INT(TOP_TICK_10MS, recv.topic);
    TEST_ASSERT_EQUAL_UINT32(42, recv.u.tick.tick);

    vQueueDelete(q);
}

void test_bus_publish_null_msg_no_crash(void)
{
    bus_publish(NULL);
}

void test_bus_publish_wrong_topic_not_delivered(void)
{
    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_INPUT_BTN, q);

    msg_t out;
    memset(&out, 0, sizeof(out));
    out.topic = TOP_TICK_10MS;
    out.u.tick.tick = 99;
    bus_publish(&out);

    msg_t recv;
    int ok = xQueueReceive(q, &recv, 0);
    TEST_ASSERT_EQUAL_INT(0, ok); /* nothing received */

    vQueueDelete(q);
}

void test_bus_multiple_subscribers(void)
{
    QueueHandle_t q1 = bus_make_queue(4);
    QueueHandle_t q2 = bus_make_queue(4);
    bus_subscribe(TOP_RPC_CALL, q1);
    bus_subscribe(TOP_RPC_CALL, q2);

    msg_t out;
    memset(&out, 0, sizeof(out));
    out.topic = TOP_RPC_CALL;
    strncpy(out.u.rpc.method, "test", sizeof(out.u.rpc.method) - 1);
    bus_publish(&out);

    msg_t recv1, recv2;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q1, &recv1, 0));
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q2, &recv2, 0));
    TEST_ASSERT_EQUAL_STRING("test", recv1.u.rpc.method);
    TEST_ASSERT_EQUAL_STRING("test", recv2.u.rpc.method);

    vQueueDelete(q1);
    vQueueDelete(q2);
}

void test_bus_subscribe_out_of_range_topic_no_crash(void)
{
    QueueHandle_t q = bus_make_queue(4);
    /* topic value larger than MAX_TOPICS should be silently ignored */
    bus_subscribe((topic_t)99, q);
    vQueueDelete(q);
}

void test_bus_ui_cmd_message(void)
{
    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_UI_CMD, q);

    msg_t out;
    memset(&out, 0, sizeof(out));
    out.topic = TOP_UI_CMD;
    out.u.ui_cmd.kind = UI_CMD_SET_TEXT;
    strncpy(out.u.ui_cmd.id, "lbl1", sizeof(out.u.ui_cmd.id) - 1);
    strncpy(out.u.ui_cmd.text, "Hello", sizeof(out.u.ui_cmd.text) - 1);
    bus_publish(&out);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_TEXT, recv.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("lbl1", recv.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_STRING("Hello", recv.u.ui_cmd.text);

    vQueueDelete(q);
}
