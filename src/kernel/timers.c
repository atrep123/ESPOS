#include "timers.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "msgbus.h"

static const char *TAG = "timers";
static TaskHandle_t s_tick_task = NULL;

#ifndef ESPOS_NATIVE
static portMUX_TYPE s_tick_mux = portMUX_INITIALIZER_UNLOCKED;
#define TICK_LOCK()   taskENTER_CRITICAL(&s_tick_mux)
#define TICK_UNLOCK() taskEXIT_CRITICAL(&s_tick_mux)
#else
#define TICK_LOCK()   ((void)0)
#define TICK_UNLOCK() ((void)0)
#endif

static void tick_task(void *arg)
{
    (void)arg;
    uint32_t t = 0; /* wraps every ~49.7 days at 10 ms tick — safe, used as
                        sequence number not absolute time */
    while (1) {
        msg_t m = {
            .topic = TOP_TICK_10MS,
            .u.tick = {
                .tick = t++,
            },
        };
        bus_publish(&m);
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void kernel_start_ticker(void)
{
    TICK_LOCK();
    if (s_tick_task != NULL) {
        TICK_UNLOCK();
        return;
    }

    /* 2048 bytes: minimal task — increments a counter and posts to msgbus */
    BaseType_t rc = xTaskCreatePinnedToCore(tick_task, "tick", 2048, NULL, 5, &s_tick_task, 1);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "tick task creation failed");
        s_tick_task = NULL;
    }
    TICK_UNLOCK();
}

void kernel_stop_ticker(void)
{
    TICK_LOCK();
    if (s_tick_task != NULL) {
        vTaskDelete(s_tick_task);
        s_tick_task = NULL;
    }
    TICK_UNLOCK();
}

