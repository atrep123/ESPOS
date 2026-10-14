#pragma once
#include <stdint.h>
#include <stddef.h>
typedef void *QueueHandle_t;
QueueHandle_t xQueueCreate(size_t depth, size_t item_size);
int xQueueSend(QueueHandle_t q, const void *item, uint32_t timeout);
int xQueueReceive(QueueHandle_t q, void *item, uint32_t timeout);
void vQueueDelete(QueueHandle_t q);
