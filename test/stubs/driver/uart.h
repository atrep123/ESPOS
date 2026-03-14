#pragma once

/* Minimal UART stub for native/host builds. */

#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

typedef int uart_port_t;

#define UART_NUM_0 0

#define UART_PIN_NO_CHANGE (-1)

typedef enum {
    UART_DATA_8_BITS = 0x03,
} uart_word_length_t;

typedef enum {
    UART_PARITY_DISABLE = 0,
} uart_parity_t;

typedef enum {
    UART_STOP_BITS_1 = 1,
} uart_stop_bits_t;

typedef enum {
    UART_HW_FLOWCTRL_DISABLE = 0,
} uart_hw_flowcontrol_t;

typedef enum {
    UART_SCLK_APB = 1,
} uart_sclk_t;

typedef struct {
    int baud_rate;
    uart_word_length_t data_bits;
    uart_parity_t parity;
    uart_stop_bits_t stop_bits;
    uart_hw_flowcontrol_t flow_ctrl;
    uart_sclk_t source_clk;
} uart_config_t;

esp_err_t uart_param_config(uart_port_t uart_num, const uart_config_t *cfg);
esp_err_t uart_set_pin(uart_port_t uart_num, int tx, int rx, int rts, int cts);
esp_err_t uart_driver_install(uart_port_t uart_num, int rx_buf, int tx_buf,
                              int queue_size, void *queue, int flags);
int uart_read_bytes(uart_port_t uart_num, void *buf, uint32_t length,
                    uint32_t ticks_to_wait);
