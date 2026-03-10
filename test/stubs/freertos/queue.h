#pragma once

/* Minimal FreeRTOS queue stub for native/host builds. */

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

typedef void *QueueHandle_t;

/* Simple ring-buffer queue implementation for testing. */
typedef struct {
    uint8_t *buf;
    size_t item_size;
    size_t capacity;
    size_t head;
    size_t count;
} FakeQueue;

static inline QueueHandle_t xQueueCreate(size_t depth, size_t item_size)
{
    FakeQueue *q = (FakeQueue *)calloc(1, sizeof(FakeQueue));
    if (!q) return NULL;
    q->buf = (uint8_t *)calloc(depth, item_size);
    if (!q->buf) { free(q); return NULL; }
    q->item_size = item_size;
    q->capacity = depth;
    q->head = 0;
    q->count = 0;
    return (QueueHandle_t)q;
}

static inline int xQueueSend(QueueHandle_t handle, const void *item, uint32_t timeout)
{
    (void)timeout;
    FakeQueue *q = (FakeQueue *)handle;
    if (!q || q->count >= q->capacity) return 0;
    size_t pos = (q->head + q->count) % q->capacity;
    memcpy(q->buf + pos * q->item_size, item, q->item_size);
    q->count++;
    return 1;
}

static inline int xQueueReceive(QueueHandle_t handle, void *item, uint32_t timeout)
{
    (void)timeout;
    FakeQueue *q = (FakeQueue *)handle;
    if (!q || q->count == 0) return 0;
    memcpy(item, q->buf + q->head * q->item_size, q->item_size);
    q->head = (q->head + 1) % q->capacity;
    q->count--;
    return 1;
}

static inline void vQueueDelete(QueueHandle_t handle)
{
    FakeQueue *q = (FakeQueue *)handle;
    if (q) {
        free(q->buf);
        free(q);
    }
}
