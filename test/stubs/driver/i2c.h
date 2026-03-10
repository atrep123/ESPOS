#pragma once

/* Minimal I2C master stub for native/host builds. */

#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

typedef int i2c_port_t;

esp_err_t i2c_master_write_to_device(i2c_port_t port, uint8_t addr,
                                     const uint8_t *write_buffer, size_t write_size,
                                     uint32_t timeout_ticks);

esp_err_t i2c_master_read_from_device(i2c_port_t port, uint8_t addr,
                                      uint8_t *read_buffer, size_t read_size,
                                      uint32_t timeout_ticks);
