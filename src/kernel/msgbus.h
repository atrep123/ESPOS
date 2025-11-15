#pragma once

#include <stdint.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

typedef enum {
    TOP_TICK_10MS = 1,
    TOP_INPUT_BTN,
    TOP_RPC_CALL,
    TOP_RPC_RET,
    TOP_METRICS_REQ,
    TOP_METRICS_RET,
} topic_t;

typedef struct {
    topic_t topic;
    union {
        struct {
            uint32_t tick;
        } tick;
        struct {
            uint8_t id;
            uint8_t pressed;
        } btn;
        struct {
            char method[16];
            uint32_t arg;
        } rpc;
    } u;
} msg_t;

void bus_init(void);
QueueHandle_t bus_make_queue(size_t depth);
void bus_subscribe(topic_t t, QueueHandle_t q);
void bus_publish(const msg_t *m);

