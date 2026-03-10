#include "rpc.h"

#include <string.h>

#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kernel/msgbus.h"

#define UARTN UART_NUM_0

static const char *TAG = "rpc";

static void rpc_task(void *arg)
{
    (void)arg;

    uart_config_t cfg = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    esp_err_t err;
    err = uart_param_config(UARTN, &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_param_config failed: %s", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }
    err = uart_set_pin(UARTN, GPIO_NUM_1, GPIO_NUM_3, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_set_pin failed: %s", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }
    err = uart_driver_install(UARTN, 1024, 0, 0, NULL, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_driver_install failed: %s", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }

    char buf[64];
    int n = 0;
    int discard = 0;

    while (1) {
        uint8_t ch;
        int r = uart_read_bytes(UARTN, &ch, 1, portMAX_DELAY);
        if (r == 1) {
            if (ch == '\n') {
                if (!discard) {
                    buf[n] = 0;

                    msg_t m = { .topic = TOP_RPC_CALL };
                    unsigned int tmp = 0;
                    /* 24-bit RGB limit: SSD1363 uses 4bpp gray but UI
                     * data model stores colours as 24-bit packed RGB. */
                    if (sscanf(buf, "set_bg %x", &tmp) == 1 && tmp <= 0xFFFFFFU) {
                        m.u.rpc.arg = tmp;
                        strncpy(m.u.rpc.method, "set_bg", sizeof(m.u.rpc.method) - 1);
                        m.u.rpc.method[sizeof(m.u.rpc.method) - 1] = '\0';
                    } else {
                        strncpy(m.u.rpc.method, "noop", sizeof(m.u.rpc.method) - 1);
                        m.u.rpc.method[sizeof(m.u.rpc.method) - 1] = '\0';
                    }
                    bus_publish(&m);
                }
                n = 0;
                discard = 0;
            } else if (n >= (int)(sizeof(buf) - 1)) {
                discard = 1;
            } else {
                buf[n++] = (char)ch;
            }
        }
    }
}

void rpc_start(void)
{
    BaseType_t rc = xTaskCreatePinnedToCore(rpc_task, "rpc", 4096, NULL, 5, NULL, 0);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "rpc task creation failed");
    }
}
