#include "rpc.h"

#include <string.h>

#include "driver/uart.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kernel/msgbus.h"

#define UARTN UART_NUM_0

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
    uart_param_config(UARTN, &cfg);
    uart_set_pin(UARTN, GPIO_NUM_1, GPIO_NUM_3, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UARTN, 1024, 0, 0, NULL, 0);

    char buf[64];
    int n = 0;

    while (1) {
        uint8_t ch;
        int r = uart_read_bytes(UARTN, &ch, 1, portMAX_DELAY);
        if (r == 1) {
            if (ch == '\n' || n >= (int)(sizeof(buf) - 1)) {
                buf[n] = 0;
                n = 0;

                msg_t m = { .topic = TOP_RPC_CALL };
                unsigned int tmp = 0;
                if (sscanf(buf, "set_bg %x", &tmp) == 1) {
                    m.u.rpc.arg = tmp;
                    strncpy(m.u.rpc.method, "set_bg", sizeof(m.u.rpc.method));
                } else {
                    strncpy(m.u.rpc.method, "noop", sizeof(m.u.rpc.method));
                }
                bus_publish(&m);
            } else {
                buf[n++] = (char)ch;
            }
        }
    }
}

void rpc_start(void)
{
    (void)xTaskCreatePinnedToCore(rpc_task, "rpc", 4096, NULL, 5, NULL, 0);
}
