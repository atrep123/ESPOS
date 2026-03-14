#include "rpc.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kernel/msgbus.h"

#define UARTN UART_NUM_0
#define RPC_UART_BAUD_RATE  115200
#define RPC_LINE_BUF_SIZE   64

static const char *TAG = "rpc";
static TaskHandle_t s_rpc_task = NULL;

int rpc_parse_line(const char *line, msg_t *m)
{
    if (!line || !m) return 0;

    memset(m, 0, sizeof(*m));
    m->topic = TOP_RPC_CALL;

    if (strncmp(line, "set_bg ", 7) == 0) {
        char *end = NULL;
        unsigned long val = strtoul(line + 7, &end, 16);
        if (end != line + 7 && (*end == '\0' || *end == ' ') && val <= 0xFFFFFFUL) {
            m->u.rpc.arg = (uint32_t)val;
            snprintf(m->u.rpc.method, sizeof(m->u.rpc.method), "set_bg");
        } else {
            snprintf(m->u.rpc.method, sizeof(m->u.rpc.method), "noop");
        }
    } else {
        snprintf(m->u.rpc.method, sizeof(m->u.rpc.method), "noop");
    }

    return 1;
}

static void rpc_task(void *arg)
{
    (void)arg;

    uart_config_t cfg = {
        .baud_rate = RPC_UART_BAUD_RATE,
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

    char buf[RPC_LINE_BUF_SIZE];
    int n = 0;
    int discard = 0;

    while (1) {
        uint8_t ch;
        int r = uart_read_bytes(UARTN, &ch, 1, portMAX_DELAY);
        if (r < 0) {
            ESP_LOGE(TAG, "uart_read_bytes error");
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }
        if (r == 1) {
            if (ch == '\n') {
                if (!discard) {
                    buf[n] = 0;

                    msg_t m;
                    rpc_parse_line(buf, &m);
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

esp_err_t rpc_start(void)
{
    if (s_rpc_task != NULL) {
        return ESP_OK;
    }
    /* 4096 bytes: reads UART line buffer + parses RPC commands */
    BaseType_t rc = xTaskCreatePinnedToCore(rpc_task, "rpc", 4096, NULL, 5, &s_rpc_task, 0);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "rpc task creation failed");
        s_rpc_task = NULL;
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}

void rpc_stop(void)
{
    if (s_rpc_task != NULL) {
        vTaskDelete(s_rpc_task);
        s_rpc_task = NULL;
    }
}
