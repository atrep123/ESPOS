#include "metrics.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_system.h"
#include "esp_log.h"

#include "kernel/msgbus.h"

static const char *TAG = "metrics";

static QueueHandle_t q;
static TaskHandle_t s_metrics_task;

static void metrics_task(void *arg)
{
    (void)arg;

    msg_t m;
    uint32_t tick_count = 0;

    bus_subscribe(TOP_TICK_10MS, q);

    while (1) {
        if (xQueueReceive(q, &m, portMAX_DELAY) == pdTRUE) {
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
    if (s_metrics_task != NULL) {
        return;
    }

    q = bus_make_queue(8);
    if (q == NULL) {
        ESP_LOGE(TAG, "bus_make_queue failed");
        return;
    }
    BaseType_t rc = xTaskCreatePinnedToCore(metrics_task, "metrics", 4096, NULL, 4, &s_metrics_task, 0);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "metrics task creation failed");
        s_metrics_task = NULL;
    }
}
