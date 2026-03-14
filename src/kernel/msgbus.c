#include "msgbus.h"

#include <string.h>

#include "esp_log.h"

#define MAX_TOPICS 16
#define MAX_SUBS   8

static const char *TAG = "msgbus";

static QueueHandle_t subs[MAX_TOPICS][MAX_SUBS];
static uint8_t subc[MAX_TOPICS];
static uint32_t s_drops[MAX_TOPICS];

/* Thread safety: bus_subscribe() uses a critical section to protect subc[]
 * and subs[][] writes.  bus_publish() is safe from any task once
 * subscriptions are set up, because it only reads stable subc[]/subs[][].
 * The s_drops[] counter may experience benign races (lost increments) in
 * the publish path — acceptable for a diagnostic counter. */
#ifndef ESPOS_NATIVE
#include "freertos/FreeRTOS.h"
static portMUX_TYPE s_bus_mux = portMUX_INITIALIZER_UNLOCKED;
#define BUS_LOCK()   taskENTER_CRITICAL(&s_bus_mux)
#define BUS_UNLOCK() taskEXIT_CRITICAL(&s_bus_mux)
#else
#define BUS_LOCK()   ((void)0)
#define BUS_UNLOCK() ((void)0)
#endif

void bus_init(void)
{
    memset(subs, 0, sizeof(subs));
    memset(subc, 0, sizeof(subc));
    memset(s_drops, 0, sizeof(s_drops));
}

void bus_deinit(void)
{
    BUS_LOCK();
    for (int t = 0; t < MAX_TOPICS; t++) {
        for (uint8_t i = 0; i < subc[t]; i++) {
            if (subs[t][i] != NULL) {
                vQueueDelete(subs[t][i]);
                subs[t][i] = NULL;
            }
        }
        subc[t] = 0;
        s_drops[t] = 0;
    }
    BUS_UNLOCK();
}

QueueHandle_t bus_make_queue(size_t depth)
{
    QueueHandle_t q = xQueueCreate(depth, sizeof(msg_t));
    if (q == NULL) {
        ESP_LOGE(TAG, "bus_make_queue: OOM, depth=%u", (unsigned)depth);
    }
    return q;
}

esp_err_t bus_subscribe(topic_t t, QueueHandle_t q)
{
    if ((int)t < 0 || (int)t >= MAX_TOPICS) {
        return ESP_ERR_INVALID_ARG;
    }
    if (q == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    BUS_LOCK();
    uint8_t *n = &subc[t];
    if (*n < MAX_SUBS) {
        subs[t][(*n)++] = q;
    } else {
        BUS_UNLOCK();
        ESP_LOGE(TAG, "bus_subscribe: topic %d full (%d subs)", (int)t, MAX_SUBS);
        return ESP_ERR_NO_MEM;
    }
    BUS_UNLOCK();
    return ESP_OK;
}

void bus_publish(const msg_t *m)
{
    if (!m || (int)m->topic < 0 || (int)m->topic >= MAX_TOPICS) {
        return;
    }

    QueueHandle_t *arr = subs[m->topic];
    uint8_t n = subc[m->topic];
    for (uint8_t i = 0; i < n; i++) {
        if (arr[i] != NULL) {
            if (xQueueSend(arr[i], m, 0) != pdTRUE) {
                s_drops[m->topic]++;
                ESP_LOGW(TAG, "queue full, topic %d sub %u (drops=%lu)",
                         (int)m->topic, (unsigned)i,
                         (unsigned long)s_drops[m->topic]);
            }
        }
    }
}

uint32_t bus_drop_count(topic_t t)
{
    if ((int)t < 0 || (int)t >= MAX_TOPICS) {
        return 0;
    }
    return s_drops[t];
}

