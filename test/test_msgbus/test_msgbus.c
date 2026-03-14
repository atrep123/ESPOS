#include "unity.h"

#include <limits.h>
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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));

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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_INPUT_BTN, q));

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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_RPC_CALL, q1));
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_RPC_CALL, q2));

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
    /* topic value larger than MAX_TOPICS should return error */
    TEST_ASSERT_NOT_EQUAL(ESP_OK, bus_subscribe((topic_t)99, q));
    vQueueDelete(q);
}

void test_bus_ui_cmd_message(void)
{
    QueueHandle_t q = bus_make_queue(4);
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_UI_CMD, q));

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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));

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
    /* MAX_SUBS is 8 — subscribing a 9th should return error */
    QueueHandle_t queues[10];
    for (int i = 0; i < 10; ++i) {
        queues[i] = bus_make_queue(4);
        esp_err_t err = bus_subscribe(TOP_TICK_10MS, queues[i]);
        if (i < 8) {
            TEST_ASSERT_EQUAL_INT(ESP_OK, err);
        } else {
            TEST_ASSERT_NOT_EQUAL(ESP_OK, err);
        }
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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));

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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_INPUT_BTN, q1));
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_UI_ACTION, q2));

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
    /* NULL queue should be rejected with error, not waste a subscriber slot */
    TEST_ASSERT_NOT_EQUAL(ESP_OK, bus_subscribe(TOP_TICK_10MS, NULL));

    QueueHandle_t q = bus_make_queue(4);
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));

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
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_METRICS_RET, q));

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

void test_bus_drop_count_initially_zero(void)
{
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count(TOP_TICK_10MS));
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count(TOP_INPUT_BTN));
}

void test_bus_drop_count_increments_on_full_queue(void)
{
    QueueHandle_t q = bus_make_queue(1);
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 1;
    bus_publish(&m); /* fills the queue */
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count(TOP_TICK_10MS));

    bus_publish(&m); /* dropped */
    TEST_ASSERT_EQUAL_UINT32(1, bus_drop_count(TOP_TICK_10MS));

    bus_publish(&m); /* dropped again */
    TEST_ASSERT_EQUAL_UINT32(2, bus_drop_count(TOP_TICK_10MS));

    vQueueDelete(q);
}

void test_bus_drop_count_reset_on_reinit(void)
{
    QueueHandle_t q = bus_make_queue(1);
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    bus_publish(&m);
    bus_publish(&m); /* dropped */
    TEST_ASSERT_TRUE(bus_drop_count(TOP_TICK_10MS) > 0);

    bus_init(); /* reinit clears everything */
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count(TOP_TICK_10MS));

    vQueueDelete(q);
}

void test_bus_drop_count_invalid_topic_returns_zero(void)
{
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count((topic_t)-1));
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count((topic_t)99));
}

/* ================================================================== */
/* Additional edge cases                                               */
/* ================================================================== */

void test_bus_publish_no_subscribers(void)
{
    /* Publishing to a topic with zero subscribers is a no-op */
    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 42;
    bus_publish(&m); /* no crash */
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count(TOP_TICK_10MS));
}

void test_bus_subscribe_same_queue_twice(void)
{
    /* Subscribing same queue twice → message delivered twice */
    QueueHandle_t q = bus_make_queue(8);
    bus_subscribe(TOP_TICK_10MS, q);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 55;
    bus_publish(&m);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_UINT32(55, recv.u.tick.tick);
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_UINT32(55, recv.u.tick.tick);
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &recv, 0)); /* no more */

    vQueueDelete(q);
}

void test_bus_drop_count_per_subscriber(void)
{
    /* Two subscribers on same topic: one with depth 1, one with depth 4 */
    QueueHandle_t q_small = bus_make_queue(1);
    QueueHandle_t q_big = bus_make_queue(4);
    bus_subscribe(TOP_RPC_CALL, q_small);
    bus_subscribe(TOP_RPC_CALL, q_big);

    msg_t m = {0};
    m.topic = TOP_RPC_CALL;
    bus_publish(&m); /* both receive */
    bus_publish(&m); /* q_small full → drop, q_big receives */

    /* Only 1 drop (from q_small being full) */
    TEST_ASSERT_EQUAL_UINT32(1, bus_drop_count(TOP_RPC_CALL));

    /* q_big should have 2 messages */
    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q_big, &recv, 0));
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q_big, &recv, 0));

    vQueueDelete(q_small);
    vQueueDelete(q_big);
}

void test_bus_publish_all_topics_isolated(void)
{
    /* Subscribe to two different topics, publish to one — other stays empty */
    QueueHandle_t q_tick = bus_make_queue(4);
    QueueHandle_t q_btn = bus_make_queue(4);
    bus_subscribe(TOP_TICK_10MS, q_tick);
    bus_subscribe(TOP_INPUT_BTN, q_btn);

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 77;
    bus_publish(&m);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q_tick, &recv, 0));
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q_btn, &recv, 0)); /* isolated */

    vQueueDelete(q_tick);
    vQueueDelete(q_btn);
}

void test_bus_burst_publish(void)
{
    /* Burst of messages — queue depth 4, publish 6 → 2 drops */
    QueueHandle_t q = bus_make_queue(4);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    for (int i = 0; i < 6; ++i) {
        m.u.tick.tick = (uint32_t)i;
        bus_publish(&m);
    }

    TEST_ASSERT_EQUAL_UINT32(2, bus_drop_count(TOP_TICK_10MS));

    /* First 4 should be in the queue */
    for (int i = 0; i < 4; ++i) {
        msg_t recv;
        TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
        TEST_ASSERT_EQUAL_UINT32((uint32_t)i, recv.u.tick.tick);
    }
    msg_t recv;
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &recv, 0));

    vQueueDelete(q);
}

void test_bus_make_queue_depth_one(void)
{
    QueueHandle_t q = bus_make_queue(1);
    TEST_ASSERT_NOT_NULL(q);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 1;
    bus_publish(&m);
    m.u.tick.tick = 2;
    bus_publish(&m);

    TEST_ASSERT_EQUAL_UINT32(1, bus_drop_count(TOP_TICK_10MS));

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &recv, 0));
    TEST_ASSERT_EQUAL_UINT32(1, recv.u.tick.tick);
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &recv, 0));
    vQueueDelete(q);
}

void test_bus_publish_extreme_topic_values(void)
{
    /* INT32_MIN and INT32_MAX cast to topic_t should not crash */
    msg_t m = {0};
    m.topic = (topic_t)INT32_MIN;
    bus_publish(&m);
    m.topic = (topic_t)INT32_MAX;
    bus_publish(&m);
    m.topic = (topic_t)(-1);
    bus_publish(&m);
}

void test_bus_subscribe_extreme_topic_values(void)
{
    QueueHandle_t q = bus_make_queue(1);
    TEST_ASSERT_NOT_EQUAL_INT(ESP_OK, bus_subscribe((topic_t)INT32_MIN, q));
    TEST_ASSERT_NOT_EQUAL_INT(ESP_OK, bus_subscribe((topic_t)INT32_MAX, q));
    TEST_ASSERT_NOT_EQUAL_INT(ESP_OK, bus_subscribe((topic_t)(-1), q));
    vQueueDelete(q);
}

void test_bus_drop_count_extreme_topics(void)
{
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count((topic_t)INT32_MIN));
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count((topic_t)INT32_MAX));
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count((topic_t)(-1)));
}

/* ================================================================== */
/* bus_deinit lifecycle tests                                           */
/* ================================================================== */

void test_bus_deinit_no_crash(void)
{
    bus_deinit();
}

void test_bus_deinit_clears_subscriptions(void)
{
    /* Subscribe, deinit frees queues + clears state, reinit works */
    QueueHandle_t q = bus_make_queue(4);
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q));
    /* q is now owned by subs array; deinit will free it */
    bus_deinit();

    /* Reinitialize and verify clean slate */
    bus_init();
    QueueHandle_t q2 = bus_make_queue(4);
    TEST_ASSERT_EQUAL_INT(ESP_OK, bus_subscribe(TOP_TICK_10MS, q2));

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    m.u.tick.tick = 99;
    bus_publish(&m);

    msg_t recv;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q2, &recv, 0));
    TEST_ASSERT_EQUAL_UINT32(99, recv.u.tick.tick);
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q2, &recv, 0)); /* only one subscriber */
    vQueueDelete(q2);
}

void test_bus_deinit_resets_drop_counts(void)
{
    QueueHandle_t q = bus_make_queue(1);
    bus_subscribe(TOP_TICK_10MS, q);

    msg_t m = {0};
    m.topic = TOP_TICK_10MS;
    bus_publish(&m);
    bus_publish(&m); /* 1 drop */
    TEST_ASSERT_EQUAL_UINT32(1, bus_drop_count(TOP_TICK_10MS));

    bus_deinit();
    bus_init();
    TEST_ASSERT_EQUAL_UINT32(0, bus_drop_count(TOP_TICK_10MS));
}
