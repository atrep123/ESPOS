#pragma once
#include "freertos/FreeRTOS.h"
typedef void *TaskHandle_t;
typedef void (*TaskFunction_t)(void *);
#ifndef SIM_APP
static inline BaseType_t xTaskCreatePinnedToCore(TaskFunction_t fn, const char *name, uint32_t stack,
    void *arg, int priority, TaskHandle_t *handle, int core)
{
    (void)fn; (void)name; (void)stack; (void)arg; (void)priority; (void)handle; (void)core;
    return pdPASS;
}
static inline void vTaskDelete(TaskHandle_t handle) { (void)handle; }
static inline void vTaskDelay(TickType_t ticks) { (void)ticks; }
#else
BaseType_t xTaskCreatePinnedToCore(TaskFunction_t fn, const char *name, uint32_t stack,
    void *arg, int priority, TaskHandle_t *handle, int core);
void vTaskDelete(TaskHandle_t handle);
void vTaskDelay(TickType_t ticks);
#endif
