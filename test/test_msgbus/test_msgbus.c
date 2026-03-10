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

void test_bus_publish_queue_full_silent_drop(void)
{
    /* Create a queue with depth 1, publish 2 messages — second is silently dropped */
    QueueHandle_t q = bus_make_queue(1);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t m1 = {0};
    m1.topic = TOP_TICK_10MS;
    m1.u.tick.tick = 1;
    bus_publish(&m1);

    msg_t m2 = {0};
    m2.topic = TOP_TICK_10MS;
    m2.u.tick.tick = 2;
    bus_publish(&m2); /* should not crash, dropped silently */

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_UINT32(1, recv.u.tick.tick); /* only first message */
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &recv, 0)); /* empty */

    vQueueDelete(q);
}

void test_bus_subscribe_max_subs_exceeded_no_crash(void)
{
    /* MAX_SUBS is 8 — subscribing a 9th should be silently ignored */
    QueueHandle_t queues[10];
    for (int i = 0; i < 10; ++i) {
        queues[i] = bus_make_queue(4);
        bus_subscribe(TOP_TICK_10MS, queues[i]);
    }

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 77;
    bus_publish(&m);

    /* First 8 subscribers should receive the message */
    for (int i = 0; i < 8; ++i) {
        msg_t recv;
        TEST_ASSERT_EQUAL_INT(1, xQueueReceive(queues[i], &recv, 0));
        TEST_ASSERT_EQUAL_UINT32(77, recv.u.tick.tick);
    }
    /* 9th and 10th should NOT receive (silent subscriber limit) */
    for (int i = 8; i < 10; ++i) {
        msg_t recv;
        TEST_ASSERT_EQUAL_INT(0, xQueueReceive(queues[i], &recv, 0));
    }

    for (int i = 0; i < 10; ++i) {
        vQueueDelete(queues[i]);
    }
}

void test_bus_publish_negative_topic_no_crash(void)
{
    msg_t m = {0};
    m.topic = (topic_t)(-1);
    bus_publish(&m); /* should not crash or corrupt */
}

void test_bus_reinit_clears_subscriptions(void)
{
    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_TICK_10MS, q);

    /* Re-init should clear all subscriptions */
    bus_init();

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 55;
    bus_publish(&m);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &recv, 0)); /* not delivered */

    vQueueDelete(q);
}

void test_bus_subscribe_multiple_topics(void)
{
    QueueHandle_t q1 = bus_make_queue(4);
    QueueHandle_t q2 = bus_make_queue(4);
    bus_subscribe(TOP_INPUT_BTN, q1);
    bus_subscribe(TOP_UI_ACTION, q2);

    msg_t m1 = {0};
    m1.topic = TOP_INPUT_BTN;
    m1.u.btn.id = 3;
    m1.u.btn.pressed = 1;
    bus_publish(&m1);

    msg_t m2 = {0};
    m2.topic = TOP_UI_ACTION;
    strncpy(m2.u.ui_action.id, "btn_ok", sizeof(m2.u.ui_action.id) - 1);
    bus_publish(&m2);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q1, &recv, 0));
    TEST_ASSERT_EQUAL_INT(TOP_INPUT_BTN, recv.topic);
    TEST_ASSERT_EQUAL_UINT(3, recv.u.btn.id);

    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q1, &recv, 0)); /* q1 didn't get q2's msg */

    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q2, &recv, 0));
    TEST_ASSERT_EQUAL_INT(TOP_UI_ACTION, recv.topic);
    TEST_ASSERT_EQUAL_STRING("btn_ok", recv.u.ui_action.id);

    vQueueDelete(q1);
    vQueueDelete(q2);
}

void test_bus_subscribe_null_queue_ignored(void)
{
    /* NULL queue should be silently rejected, not waste a subscriber slot */
    bus_subscribe(TOP_TICK_10MS, NULL);

    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 88;
    bus_publish(&m);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_UINT32(88, recv.u.tick.tick);

    vQueueDelete(q);
}

void test_bus_metrics_union_delivery(void)
{
    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_METRICS_RET, q);

    msg_t m = {0};
    m.topic = TOP_METRICS_RET;
    m.u.metrics.free_heap = 123456;
    m.u.metrics.min_free_heap = 65432;
    bus_publish(&m);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_INT(TOP_METRICS_RET, recv.topic);
    TEST_ASSERT_EQUAL_UINT32(123456, recv.u.metrics.free_heap);
    TEST_ASSERT_EQUAL_UINT32(65432, recv.u.metrics.min_free_heap);

    vQueueDelete(q);
}
