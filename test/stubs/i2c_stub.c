#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifndef ESP_PLATFORM

#include "esp_err.h"
#include "driver/i2c.h"
#include "i2c_stub_capture.h"

#define I2C_STUB_BUF_SIZE 128

static esp_err_t s_write_err = ESP_OK;
static esp_err_t s_read_err = ESP_OK;

static uint8_t s_read_data[I2C_STUB_BUF_SIZE];
static size_t s_read_data_len = 0;

static uint8_t s_last_write[I2C_STUB_BUF_SIZE];
static size_t s_last_write_len = 0;
static uint8_t s_last_write_addr = 0;
static size_t s_write_calls = 0;
static size_t s_read_calls = 0;

void i2c_stub_reset(void)
{
    s_write_err = ESP_OK;
    s_read_err = ESP_OK;
    memset(s_read_data, 0, sizeof(s_read_data));
    s_read_data_len = 0;
    memset(s_last_write, 0, sizeof(s_last_write));
    s_last_write_len = 0;
    s_last_write_addr = 0;
    s_write_calls = 0;
    s_read_calls = 0;
}

void i2c_stub_set_write_err(esp_err_t err) { s_write_err = err; }
void i2c_stub_set_read_err(esp_err_t err) { s_read_err = err; }

void i2c_stub_set_read_data(const uint8_t *data, size_t len)
{
    if (len > I2C_STUB_BUF_SIZE) {
        len = I2C_STUB_BUF_SIZE;
    }
    memcpy(s_read_data, data, len);
    s_read_data_len = len;
}

size_t i2c_stub_write_call_count(void) { return s_write_calls; }
size_t i2c_stub_last_write_len(void) { return s_last_write_len; }
uint8_t i2c_stub_last_write_addr(void) { return s_last_write_addr; }
size_t i2c_stub_read_call_count(void) { return s_read_calls; }

size_t i2c_stub_copy_last_write(uint8_t *out, size_t max_out)
{
    if (out == NULL || max_out == 0 || s_last_write_len == 0) {
        return 0;
    }
    size_t n = s_last_write_len;
    if (n > max_out) {
        n = max_out;
    }
    memcpy(out, s_last_write, n);
    return n;
}

esp_err_t i2c_master_write_to_device(i2c_port_t port, uint8_t addr,
                                     const uint8_t *write_buffer, size_t write_size,
                                     uint32_t timeout_ticks)
{
    (void)port;
    (void)timeout_ticks;
    s_write_calls++;
    s_last_write_addr = addr;
    s_last_write_len = write_size;
    if (write_size > I2C_STUB_BUF_SIZE) {
        s_last_write_len = I2C_STUB_BUF_SIZE;
    }
    if (write_buffer && s_last_write_len > 0) {
        memcpy(s_last_write, write_buffer, s_last_write_len);
    }
    return s_write_err;
}

esp_err_t i2c_master_read_from_device(i2c_port_t port, uint8_t addr,
                                      uint8_t *read_buffer, size_t read_size,
                                      uint32_t timeout_ticks)
{
    (void)port;
    (void)addr;
    (void)timeout_ticks;
    s_read_calls++;
    if (s_read_err != ESP_OK) {
        return s_read_err;
    }
    if (read_buffer && read_size > 0) {
        size_t n = read_size;
        if (n > s_read_data_len) {
            /* Zero-fill bytes beyond what was staged. */
            memset(read_buffer, 0, read_size);
            n = s_read_data_len;
        }
        if (n > 0) {
            memcpy(read_buffer, s_read_data, n);
        }
    }
    return ESP_OK;
}

#endif
