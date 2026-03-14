#pragma once

/* Minimal FreeRTOS semaphore/mutex stub for native/host builds. */

#include "FreeRTOS.h"

typedef void *SemaphoreHandle_t;

static inline SemaphoreHandle_t xSemaphoreCreateMutex(void)
{
    /* Return non-NULL so NULL-guard macros (STORE_LOCK etc.) enter the body. */
    return (SemaphoreHandle_t)1;
}

static inline BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t t)
{
    (void)s; (void)t;
    return pdPASS;
}

static inline BaseType_t xSemaphoreGive(SemaphoreHandle_t s)
{
    (void)s;
    return pdPASS;
}

static inline void vSemaphoreDelete(SemaphoreHandle_t s)
{
    (void)s;
}
