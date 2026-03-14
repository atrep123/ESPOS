#include "seesaw.h"

#include <string.h>

#include "driver/i2c.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"

#include "display_config.h"
#include "input_config.h"

static inline TickType_t seesaw_timeout_ticks(void)
{
    int ms = INPUT_SEESAW_I2C_TIMEOUT_MS;
    if (ms < 1) {
        ms = 1;
    }
    return pdMS_TO_TICKS(ms);
}

esp_err_t seesaw_read(uint8_t addr, uint8_t base, uint8_t reg, uint8_t *out, size_t len)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (len == 0) {
        return ESP_OK;
    }

    uint8_t prefix[2] = { base, reg };
    esp_err_t err = i2c_master_write_to_device(
        DISPLAY_I2C_PORT,
        addr,
        prefix,
        sizeof(prefix),
        seesaw_timeout_ticks()
    );
    if (err != ESP_OK) {
        return err;
    }

    if (INPUT_SEESAW_READ_DELAY_US > 0) {
        esp_rom_delay_us((uint32_t)INPUT_SEESAW_READ_DELAY_US);
    }

    return i2c_master_read_from_device(
        DISPLAY_I2C_PORT,
        addr,
        out,
        len,
        seesaw_timeout_ticks()
    );
}

esp_err_t seesaw_write(uint8_t addr, uint8_t base, uint8_t reg, const uint8_t *data, size_t len)
{
    if (len > 64) {
        /* Defensive limit: keeps stack usage reasonable. */
        ESP_LOGW("seesaw", "seesaw_write: len %u exceeds max 64", (unsigned)len);
        return ESP_ERR_INVALID_SIZE;
    }

    uint8_t buf[2 + 64];
    buf[0] = base;
    buf[1] = reg;
    if (data && len) {
        memcpy(&buf[2], data, len);
    } else {
        len = 0;
    }

    return i2c_master_write_to_device(
        DISPLAY_I2C_PORT,
        addr,
        buf,
        (size_t)(2 + len),
        seesaw_timeout_ticks()
    );
}

esp_err_t seesaw_read_u8(uint8_t addr, uint8_t base, uint8_t reg, uint8_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    return seesaw_read(addr, base, reg, out, 1);
}

esp_err_t seesaw_read_u16(uint8_t addr, uint8_t base, uint8_t reg, uint16_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t buf[2] = { 0 };
    esp_err_t err = seesaw_read(addr, base, reg, buf, sizeof(buf));
    if (err != ESP_OK) {
        return err;
    }
    *out = (uint16_t)(((uint16_t)buf[0] << 8) | (uint16_t)buf[1]);
    return ESP_OK;
}

esp_err_t seesaw_read_u32(uint8_t addr, uint8_t base, uint8_t reg, uint32_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t buf[4] = { 0 };
    esp_err_t err = seesaw_read(addr, base, reg, buf, sizeof(buf));
    if (err != ESP_OK) {
        return err;
    }
    *out = ((uint32_t)buf[0] << 24) | ((uint32_t)buf[1] << 16) | ((uint32_t)buf[2] << 8) | (uint32_t)buf[3];
    return ESP_OK;
}

esp_err_t seesaw_read_i32(uint8_t addr, uint8_t base, uint8_t reg, int32_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    uint32_t v = 0;
    esp_err_t err = seesaw_read_u32(addr, base, reg, &v);
    if (err != ESP_OK) {
        return err;
    }
    *out = (int32_t)v;
    return ESP_OK;
}

esp_err_t seesaw_pin_mode_bulk(uint8_t addr, uint32_t pins_mask, seesaw_pin_mode_t mode)
{
    /* Port A bulk operations use a 32-bit mask, big-endian. */
    uint8_t cmd[4] = {
        (uint8_t)((pins_mask >> 24) & 0xFF),
        (uint8_t)((pins_mask >> 16) & 0xFF),
        (uint8_t)((pins_mask >> 8) & 0xFF),
        (uint8_t)(pins_mask & 0xFF),
    };

    switch (mode) {
        case SEESAW_PIN_INPUT:
            return seesaw_write(addr, SEESAW_GPIO_BASE, SEESAW_GPIO_DIRCLR_BULK, cmd, sizeof(cmd));

        case SEESAW_PIN_INPUT_PULLUP: {
            esp_err_t err = seesaw_write(addr, SEESAW_GPIO_BASE, SEESAW_GPIO_DIRCLR_BULK, cmd, sizeof(cmd));
            if (err != ESP_OK) {
                return err;
            }
            err = seesaw_write(addr, SEESAW_GPIO_BASE, SEESAW_GPIO_PULLENSET, cmd, sizeof(cmd));
            if (err != ESP_OK) {
                return err;
            }
            return seesaw_write(addr, SEESAW_GPIO_BASE, SEESAW_GPIO_BULK_SET, cmd, sizeof(cmd));
        }

        default:
            break;
    }
    return ESP_ERR_INVALID_ARG;
}

bool seesaw_hw_id_supported(uint8_t hw_id)
{
    switch (hw_id) {
        case SEESAW_HW_ID_CODE_SAMD09:
        case SEESAW_HW_ID_CODE_TINY817:
        case SEESAW_HW_ID_CODE_TINY1616:
        case SEESAW_HW_ID_CODE_TINY1617:
            return true;
        default:
            break;
    }
    return false;
}
