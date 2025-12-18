#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

/* Minimal seesaw protocol helpers (for Adafruit QT devices).
 *
 * Seesaw uses a 2-byte register prefix: (module_base, function_reg).
 * Reads are big-endian for multi-byte values.
 */

/* Seesaw module base addresses */
enum {
    SEESAW_STATUS_BASE = 0x00,
    SEESAW_GPIO_BASE = 0x01,
    SEESAW_ADC_BASE = 0x09,
    SEESAW_ENCODER_BASE = 0x11,
};

/* Status module registers */
enum {
    SEESAW_STATUS_HW_ID = 0x01,
    SEESAW_STATUS_VERSION = 0x02,
};

/* GPIO module registers */
enum {
    SEESAW_GPIO_DIRSET_BULK = 0x02,
    SEESAW_GPIO_DIRCLR_BULK = 0x03,
    SEESAW_GPIO_BULK = 0x04,
    SEESAW_GPIO_BULK_SET = 0x05,
    SEESAW_GPIO_BULK_CLR = 0x06,
    SEESAW_GPIO_PULLENSET = 0x0B,
};

/* ADC module registers */
enum {
    SEESAW_ADC_CHANNEL_OFFSET = 0x07,
};

/* Encoder module registers */
enum {
    SEESAW_ENCODER_DELTA = 0x40,
};

/* Common HW ID codes (not exhaustive) */
enum {
    SEESAW_HW_ID_CODE_SAMD09 = 0x55,
    SEESAW_HW_ID_CODE_TINY817 = 0x87,
    SEESAW_HW_ID_CODE_TINY1616 = 0x88,
    SEESAW_HW_ID_CODE_TINY1617 = 0x89,
};

typedef enum {
    SEESAW_PIN_INPUT = 0,
    SEESAW_PIN_INPUT_PULLUP = 1,
} seesaw_pin_mode_t;

esp_err_t seesaw_read(uint8_t addr, uint8_t base, uint8_t reg, uint8_t *out, size_t len);
esp_err_t seesaw_write(uint8_t addr, uint8_t base, uint8_t reg, const uint8_t *data, size_t len);

esp_err_t seesaw_read_u8(uint8_t addr, uint8_t base, uint8_t reg, uint8_t *out);
esp_err_t seesaw_read_u16(uint8_t addr, uint8_t base, uint8_t reg, uint16_t *out);
esp_err_t seesaw_read_u32(uint8_t addr, uint8_t base, uint8_t reg, uint32_t *out);
esp_err_t seesaw_read_i32(uint8_t addr, uint8_t base, uint8_t reg, int32_t *out);

esp_err_t seesaw_pin_mode_bulk(uint8_t addr, uint32_t pins_mask, seesaw_pin_mode_t mode);

bool seesaw_hw_id_supported(uint8_t hw_id);

