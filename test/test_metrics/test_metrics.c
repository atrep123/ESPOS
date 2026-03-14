/*
 * Unit tests for metrics_process_tick() — the tick-driven metrics publisher.
 *
 * Tests cover: counter increment, 100-tick publish cycle, null safety,
 * counter reset, message content, and multiple cycles.
 */

#include "unity.h"

#include <string.h>

#include "kernel/msgbus.h"
#include "services/metrics/metrics.h"

static QueueHandle_t q;

void setUp(void)
{
    bus_init();
    q = bus_make_queue(4);
    bus_subscribe(TOP_METRICS_RET, q);
}

void tearDown(void)
{
    vQueueDelete(q);
}

/* ======================== Counter behavior ======================== */

void test_metrics_tick_increments_counter(void)
{
    uint32_t cnt = 0;
    int published = metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(0, published);
    TEST_ASSERT_EQUAL_UINT32(1, cnt);
}

void test_metrics_tick_publishes_at_100(void)
{
    uint32_t cnt = 99;
    int published = metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(1, published);
    TEST_ASSERT_EQUAL_UINT32(0, cnt); /* reset after publish */
}

void test_metrics_tick_not_at_99(void)
{
    uint32_t cnt = 98;
    int published = metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(0, published);
    TEST_ASSERT_EQUAL_UINT32(99, cnt);
}

void test_metrics_tick_full_cycle(void)
{
    uint32_t cnt = 0;
    for (int i = 0; i < 99; ++i) {
        TEST_ASSERT_EQUAL_INT(0, metrics_process_tick(&cnt));
    }
    TEST_ASSERT_EQUAL_INT(1, metrics_process_tick(&cnt));
    TEST_ASSERT_EQUAL_UINT32(0, cnt);
}

void test_metrics_tick_multiple_cycles(void)
{
    uint32_t cnt = 0;
    int cycles = 0;
    for (int i = 0; i < 300; ++i) {
        if (metrics_process_tick(&cnt)) cycles++;
    }
    TEST_ASSERT_EQUAL_INT(3, cycles);
}

/* ======================== Published message ======================== */

void test_metrics_publishes_correct_topic(void)
{
    uint32_t cnt = 99;
    metrics_process_tick(&cnt);

    msg_t m;
    int ok = xQueueReceive(q, &m, 0);
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_EQUAL_INT(TOP_METRICS_RET, m.topic);
}

void test_metrics_publishes_heap_values(void)
{
    uint32_t cnt = 99;
    metrics_process_tick(&cnt);

    msg_t m;
    int ok = xQueueReceive(q, &m, 0);
    TEST_ASSERT_EQUAL_INT(1, ok);
    /* Stub returns known values: 128000 / 64000 */
    TEST_ASSERT_EQUAL_UINT32(128000, m.u.metrics.free_heap);
    TEST_ASSERT_EQUAL_UINT32(64000, m.u.metrics.min_free_heap);
}

void test_metrics_no_publish_no_message(void)
{
    uint32_t cnt = 0;
    metrics_process_tick(&cnt);

    msg_t m;
    int ok = xQueueReceive(q, &m, 0);
    TEST_ASSERT_EQUAL_INT(0, ok); /* nothing on queue */
}

/* ======================== Null safety ======================== */

void test_metrics_tick_null_counter(void)
{
    TEST_ASSERT_EQUAL_INT(0, metrics_process_tick(NULL));
}

/* ======================== Additional coverage ======================== */

void test_metrics_tick_large_initial_counter(void)
{
    /* Counter well beyond 100 should still wrap and publish correctly */
    uint32_t cnt = 199;
    int published = metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(1, published);
    TEST_ASSERT_EQUAL_UINT32(0, cnt);
}

void test_metrics_tick_consecutive_publishes(void)
{
    /* Two back-to-back cycles should each publish independently */
    uint32_t cnt = 0;
    int pub1 = 0, pub2 = 0;
    for (int i = 0; i < 100; ++i) {
        pub1 += metrics_process_tick(&cnt);
    }
    for (int i = 0; i < 100; ++i) {
        pub2 += metrics_process_tick(&cnt);
    }
    TEST_ASSERT_EQUAL_INT(1, pub1);
    TEST_ASSERT_EQUAL_INT(1, pub2);
}

void test_metrics_counter_at_one_below(void)
{
    /* Counter at 0 → after tick should be 1, no publish */
    uint32_t cnt = 0;
    TEST_ASSERT_EQUAL_INT(0, metrics_process_tick(&cnt));
    TEST_ASSERT_EQUAL_UINT32(1, cnt);
}

void test_metrics_queue_receives_multiple_messages(void)
{
    /* Run 3 full cycles, verify 3 messages on queue */
    uint32_t cnt = 0;
    for (int i = 0; i < 300; ++i) {
        metrics_process_tick(&cnt);
    }
    msg_t m;
    int received = 0;
    while (xQueueReceive(q, &m, 0)) {
        TEST_ASSERT_EQUAL_INT(TOP_METRICS_RET, m.topic);
        received++;
    }
    TEST_ASSERT_EQUAL_INT(3, received);
}

void test_metrics_heap_values_each_publish(void)
{
    /* Every publish should contain the same stub heap values */
    uint32_t cnt = 99;
    metrics_process_tick(&cnt);

    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &m, 0));
    TEST_ASSERT_EQUAL_UINT32(128000, m.u.metrics.free_heap);
    TEST_ASSERT_EQUAL_UINT32(64000, m.u.metrics.min_free_heap);

    /* Second cycle */
    cnt = 99;
    metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &m, 0));
    TEST_ASSERT_EQUAL_UINT32(128000, m.u.metrics.free_heap);
}

/* ======================== New edge-case tests ======================== */

void test_metrics_tick_counter_wraps_from_max(void)
{
    /* UINT32_MAX counter: increment wraps to 0 which != 100, so no publish */
    uint32_t cnt = UINT32_MAX;
    int pub = metrics_process_tick(&cnt);
    /* After increment UINT32_MAX+1 wraps to 0 */
    TEST_ASSERT_EQUAL_UINT32(0, cnt);
    /* 0 < 100 → no publish; BUT the code does ++cnt first then checks >= 100 */
    /* Actually: UINT32_MAX + 1 = 0, 0 < 100 → no publish */
    TEST_ASSERT_EQUAL_INT(0, pub);
}

void test_metrics_tick_exactly_at_100(void)
{
    /* Counter at 100: after ++cnt it's 101, 101 >= 100 → publish */
    uint32_t cnt = 100;
    int pub = metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(1, pub);
    TEST_ASSERT_EQUAL_UINT32(0, cnt);
}

void test_metrics_no_queue_leak(void)
{
    /* Run exactly 100 ticks, verify exactly 1 message, queue is then empty */
    uint32_t cnt = 0;
    for (int i = 0; i < 100; ++i) {
        metrics_process_tick(&cnt);
    }
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &m, 0));
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &m, 0)); /* no extras */
}

void test_metrics_counter_reset_after_publish(void)
{
    /* After publish, counter should restart from 0 and need another 100 ticks */
    uint32_t cnt = 0;
    for (int i = 0; i < 100; ++i) {
        metrics_process_tick(&cnt);
    }
    TEST_ASSERT_EQUAL_UINT32(0, cnt);
    /* Only 50 more ticks → no second publish */
    for (int i = 0; i < 50; ++i) {
        metrics_process_tick(&cnt);
    }
    TEST_ASSERT_EQUAL_UINT32(50, cnt);
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, xQueueReceive(q, &m, 0)); /* first publish */
    TEST_ASSERT_EQUAL_INT(0, xQueueReceive(q, &m, 0)); /* no second */
}

void test_metrics_counter_at_50_no_publish(void)
{
    uint32_t cnt = 50;
    int pub = metrics_process_tick(&cnt);
    TEST_ASSERT_EQUAL_INT(0, pub);
    TEST_ASSERT_EQUAL_UINT32(51, cnt);
}
