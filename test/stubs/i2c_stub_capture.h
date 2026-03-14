#pragma once

/* Capture/control API for the I2C master stub. */

#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

/* Reset all stub state. Call in setUp(). */
void i2c_stub_reset(void);

/* Configure the error returned by write/read calls. */
void i2c_stub_set_write_err(esp_err_t err);
void i2c_stub_set_read_err(esp_err_t err);

/* Stage bytes that the next i2c_master_read_from_device will copy out. */
void i2c_stub_set_read_data(const uint8_t *data, size_t len);

/* Query the last write: how many total write calls, and the payload. */
size_t i2c_stub_write_call_count(void);
size_t i2c_stub_last_write_len(void);
size_t i2c_stub_copy_last_write(uint8_t *out, size_t max_out);
uint8_t i2c_stub_last_write_addr(void);

/* Make the first n writes succeed (ESP_OK), then apply s_write_err.
 * Pass 0 to disable (default: all writes use s_write_err). */
void i2c_stub_set_write_fail_after(size_t n);

/* Query the last read request size. */
size_t i2c_stub_read_call_count(void);
