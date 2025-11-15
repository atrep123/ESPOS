#include "input.h"

#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kernel/msgbus.h"

#define PIN_BTN 0

static void input_task(void *arg)
{
    (void)arg;

    gpio_config_t c = {
        .pin_bit_mask = 1ULL << PIN_BTN,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = 1,
        .pull_down_en = 0,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&c);

    int stable = 1;
    int last = 1;
    int cnt = 0;

    while (1) {
        int v = gpio_get_level(PIN_BTN);
        if (v != stable) {
            if (++cnt >= 2) {
                stable = v;
                cnt = 0;
            }
        } else {
            cnt = 0;
        }

        if (stable != last) {
            msg_t m = {
                .topic = TOP_INPUT_BTN,
                .u.btn = {
                    .id = 0,
                    .pressed = (uint8_t)(stable == 0),
                },
            };
            bus_publish(&m);
            last = stable;
        }

        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

void input_start(void)
{
    (void)xTaskCreatePinnedToCore(input_task, "in", 2048, NULL, 5, NULL, 0);
}
