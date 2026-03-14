/* Minimal UART stub implementation for native/host builds. */

#include "driver/uart.h"

esp_err_t uart_param_config(uart_port_t uart_num, const uart_config_t *cfg)
{
    (void)uart_num;
    (void)cfg;
    return ESP_OK;
}

esp_err_t uart_set_pin(uart_port_t uart_num, int tx, int rx, int rts, int cts)
{
    (void)uart_num;
    (void)tx;
    (void)rx;
    (void)rts;
    (void)cts;
    return ESP_OK;
}

esp_err_t uart_driver_install(uart_port_t uart_num, int rx_buf, int tx_buf,
                              int queue_size, void *queue, int flags)
{
    (void)uart_num;
    (void)rx_buf;
    (void)tx_buf;
    (void)queue_size;
    (void)queue;
    (void)flags;
    return ESP_OK;
}

int uart_read_bytes(uart_port_t uart_num, void *buf, uint32_t length,
                    uint32_t ticks_to_wait)
{
    (void)uart_num;
    (void)buf;
    (void)length;
    (void)ticks_to_wait;
    return 0;
}
