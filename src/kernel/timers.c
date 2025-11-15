#include "timers.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "msgbus.h"

static void tick_task(void *arg)
{
    (void)arg;
    uint32_t t = 0;
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
    (void)xTaskCreatePinnedToCore(tick_task, "tick", 2048, NULL, 5, NULL, 1);
}

