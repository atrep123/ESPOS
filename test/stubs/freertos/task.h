#pragma once

/* Minimal FreeRTOS task stub for native/host builds. */

#include "freertos/FreeRTOS.h"

typedef void *TaskHandle_t;

typedef void (*TaskFunction_t)(void *);

static inline BaseType_t xTaskCreatePinnedToCore(
    TaskFunction_t func, const char *name, uint32_t stack,
    void *param, int prio, TaskHandle_t *handle, int core)
{
    (void)func; (void)name; (void)stack;
    (void)param; (void)prio; (void)handle; (void)core;
    return pdPASS;
}

static inline void vTaskDelete(TaskHandle_t h) { (void)h; }

static inline void vTaskDelay(TickType_t ticks) { (void)ticks; }
