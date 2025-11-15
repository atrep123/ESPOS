#include "msgbus.h"

#include <string.h>

#define MAX_TOPICS 16
#define MAX_SUBS   8

static QueueHandle_t subs[MAX_TOPICS][MAX_SUBS];
static uint8_t subc[MAX_TOPICS];

void bus_init(void)
{
    memset(subs, 0, sizeof(subs));
    memset(subc, 0, sizeof(subc));
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
            xQueueSend(arr[i], m, 0);
        }
    }
}

