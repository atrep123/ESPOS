#include "metrics.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_system.h"
#include "esp_log.h"

#include "kernel/msgbus.h"

static const char *TAG = "metrics";

static QueueHandle_t q;

static void metrics_task(void *arg)
{
    (void)arg;

    msg_t m;
    uint32_t tick_count = 0;

    bus_subscribe(TOP_TICK_10MS, q);

    while (1) {
        if (xQueueReceive(q, &m, portMAX_DELAY)) {
            if (m.topic == TOP_TICK_10MS) {
                tick_count++;
                /* Roughly once per second (100 * 10ms). */
                if (tick_count >= 100U) {
                    tick_count = 0;

                    msg_t out = {0};
                    out.topic = TOP_METRICS_RET;
                    out.u.metrics.free_heap = esp_get_free_heap_size();
                    out.u.metrics.min_free_heap = esp_get_minimum_free_heap_size();

                    ESP_LOGD(TAG, "heap=%" PRIu32 " min=%" PRIu32,
                             out.u.metrics.free_heap,
                             out.u.metrics.min_free_heap);

                    bus_publish(&out);
                }
            }
        }
    }
}

void metrics_start(void)
{
    q = bus_make_queue(8);
    (void)xTaskCreatePinnedToCore(metrics_task, "metrics", 4096, NULL, 4, NULL, 0);
}
