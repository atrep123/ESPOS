#include "metrics.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_system.h"
#include "esp_log.h"

#include "kernel/msgbus.h"

static const char *TAG = "metrics";

/* Ticks between metric reports: 100 × 10 ms = 1 second. */
#define METRICS_REPORT_TICKS 100U

static QueueHandle_t q;
static TaskHandle_t s_metrics_task = NULL;

int metrics_process_tick(uint32_t *tick_count)
{
    if (!tick_count) return 0;

    (*tick_count)++;
    if (*tick_count >= METRICS_REPORT_TICKS) {
        *tick_count = 0;

        msg_t out = {0};
        out.topic = TOP_METRICS_RET;
        out.u.metrics.free_heap = esp_get_free_heap_size();
        out.u.metrics.min_free_heap = esp_get_minimum_free_heap_size();

        ESP_LOGD(TAG, "heap=%" PRIu32 " min=%" PRIu32,
                 out.u.metrics.free_heap,
                 out.u.metrics.min_free_heap);

        bus_publish(&out);
        return 1;
    }
    return 0;
}

static void metrics_task(void *arg)
{
    (void)arg;

    msg_t m;
    uint32_t tick_count = 0;

    if (bus_subscribe(TOP_TICK_10MS, q) != ESP_OK) {
        ESP_LOGE(TAG, "bus_subscribe failed");
        vTaskDelete(NULL);
        return;
    }

    while (1) {
        if (xQueueReceive(q, &m, portMAX_DELAY) == pdTRUE) {
            if (m.topic == TOP_TICK_10MS) {
                metrics_process_tick(&tick_count);
            }
        }
    }
}

esp_err_t metrics_start(void)
{
    if (s_metrics_task != NULL) {
        return ESP_OK;
    }

    q = bus_make_queue(8);
    if (q == NULL) {
        ESP_LOGE(TAG, "bus_make_queue failed");
        return ESP_ERR_NO_MEM;
    }
    /* 4096 bytes: receives metrics events, formats log strings */
    BaseType_t rc = xTaskCreatePinnedToCore(metrics_task, "metrics", 4096, NULL, 4, &s_metrics_task, 0);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "metrics task creation failed");
        s_metrics_task = NULL;
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}

void metrics_stop(void)
{
    if (s_metrics_task != NULL) {
        vTaskDelete(s_metrics_task);
        s_metrics_task = NULL;
    }
}
