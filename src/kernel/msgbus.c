#include "msgbus.h"

#include <string.h>

#include "esp_log.h"

#define MAX_TOPICS 16
#define MAX_SUBS   8

static const char *TAG = "msgbus";

static QueueHandle_t subs[MAX_TOPICS][MAX_SUBS];
static uint8_t subc[MAX_TOPICS];
static uint32_t s_drops[MAX_TOPICS];

/* Thread safety: bus_subscribe() must only be called during init (before
 * scheduler or from a single task).  bus_publish() is safe from any task
 * once subscriptions are set up, because it only reads subc[]/subs[][]. */

void bus_init(void)
{
    memset(subs, 0, sizeof(subs));
    memset(subc, 0, sizeof(subc));
    memset(s_drops, 0, sizeof(s_drops));
}

QueueHandle_t bus_make_queue(size_t depth)
{
    return xQueueCreate(depth, sizeof(msg_t));
}

void bus_subscribe(topic_t t, QueueHandle_t q)
{
    if ((int)t < 0 || (int)t >= MAX_TOPICS) {
        return;
    }
    if (q == NULL) {
        return;
    }

    uint8_t *n = &subc[t];
    if (*n < MAX_SUBS) {
        subs[t][(*n)++] = q;
    }
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

