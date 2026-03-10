#pragma once

/* Minimal FreeRTOS stub for native/host builds. */

#include <stdint.h>
#include <stddef.h>

typedef uint32_t TickType_t;
typedef int BaseType_t;

#define pdPASS  1
#define pdFAIL  0
#define pdTRUE  1
#define pdFALSE 0

#define portMAX_DELAY 0xFFFFFFFFu

#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
