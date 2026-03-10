#include "display/ssd1363.h"

#include "driver/gpio.h"
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#include "display_config.h"
#include <string.h>
#include <stdbool.h>

static const char *TAG = "ssd1363";

#define I2C_TIMEOUT_MS 1000

static bool s_i2c_inited = false;
static uint8_t s_col_offset_units = SSD1363_COL_OFFSET;

#define SSD1363_MAX_COL_ADDR 79U

static esp_err_t ssd1363_write_cmd_args(uint8_t cmd, const uint8_t *args, size_t arg_len)
{
    if (args == NULL || arg_len == 0) {
        return ssd1363_write_cmd(cmd);
    }
    if (arg_len > 8) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t buf[1 + 8];
    buf[0] = cmd;
    memcpy(buf + 1, args, arg_len);
    return ssd1363_write_cmd_list(buf, 1 + arg_len);
}

static esp_err_t ssd1363_cmd_unlock(void)
{
    const uint8_t arg = 0x12; /* unlock */
    return ssd1363_write_cmd_args(0xFD, &arg, 1);
}

#if SSD1363_I2C_SCAN_ON_BOOT
static void ssd1363_scan_i2c(void)
{
    ESP_LOGI(TAG, "I2C scan (port=%d) ...", DISPLAY_I2C_PORT);
    int found = 0;
    int found_display = 0;

    for (int addr = 1; addr < 0x7F; ++addr) {
        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        if (cmd == NULL) {
            ESP_LOGE(TAG, "i2c_cmd_link_create failed during scan");
            return;
        }
        esp_err_t err = i2c_master_start(cmd);
        if (err == ESP_OK) {
            err = i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
        }
        if (err == ESP_OK) {
            err = i2c_master_stop(cmd);
        }
        if (err != ESP_OK) {
            i2c_cmd_link_delete(cmd);
            continue;
        }

        err = i2c_master_cmd_begin(DISPLAY_I2C_PORT, cmd, pdMS_TO_TICKS(20));
        i2c_cmd_link_delete(cmd);

        if (err == ESP_OK) {
            found += 1;
            if (addr == DISPLAY_I2C_ADDR) {
                found_display = 1;
            }
            ESP_LOGI(TAG, "I2C device @0x%02X", addr);
        }
    }

    if (found == 0) {
        ESP_LOGW(TAG, "I2C scan: no devices found");
        return;
    }
    if (!found_display) {
        ESP_LOGW(TAG, "I2C scan: DISPLAY_I2C_ADDR=0x%02X not found", DISPLAY_I2C_ADDR);
    }
}
#endif

#if SSD1363_BOOT_TEST_PATTERN
static esp_err_t ssd1363_boot_test_pattern(void)
{
    ESP_LOGI(TAG, "SSD1363 boot test pattern");

    esp_err_t err = ssd1363_begin_frame(0, 0, (uint16_t)(DISPLAY_WIDTH - 1), (uint16_t)(DISPLAY_HEIGHT - 1));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "begin_frame failed: %d", err);
        return err;
    }

#if DISPLAY_COLOR_BITS == 4
    const int row_bytes = (DISPLAY_WIDTH + 1) / 2;
    uint8_t line[(DISPLAY_WIDTH + 1) / 2];
    for (int y = 0; y < DISPLAY_HEIGHT; ++y) {
        for (int bx = 0; bx < row_bytes; ++bx) {
            uint8_t v = 0x0F;
            if (row_bytes > 1) {
                v = (uint8_t)((bx * 15) / (row_bytes - 1));
            }
            if (y & 1) {
                v = (uint8_t)(v ^ 0x0F);
            }
            line[bx] = (uint8_t)((uint8_t)(v << 4) | (v & 0x0F));
        }
        err = ssd1363_write_data(line, (size_t)row_bytes);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "write_data failed (row=%d): %d", y, err);
            return err;
        }
    }
    return ESP_OK;
#else
    const int row_bytes = (DISPLAY_WIDTH + 7) / 8;
    uint8_t line[(DISPLAY_WIDTH + 7) / 8];
    for (int y = 0; y < DISPLAY_HEIGHT; ++y) {
        memset(line, (y & 1) ? 0xAA : 0x55, (size_t)row_bytes);
        err = ssd1363_write_data(line, (size_t)row_bytes);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "write_data failed (row=%d): %d", y, err);
            return err;
        }
    }
    return ESP_OK;
#endif
}
#endif

esp_err_t ssd1363_bus_init(void)
{
    if (s_i2c_inited) {
        return ESP_OK;
    }

    if (DISPLAY_I2C_SDA_GPIO < 0 || DISPLAY_I2C_SCL_GPIO < 0) {
        ESP_LOGE(TAG, "DISPLAY_I2C_SDA_GPIO / DISPLAY_I2C_SCL_GPIO are not set");
        return ESP_ERR_INVALID_STATE;
    }

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = DISPLAY_I2C_SDA_GPIO,
        .scl_io_num = DISPLAY_I2C_SCL_GPIO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = DISPLAY_I2C_FREQ_HZ,
        .clk_flags = 0,
    };

    esp_err_t err = i2c_param_config(DISPLAY_I2C_PORT, &conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_param_config failed: %d", err);
        return err;
    }

    err = i2c_driver_install(DISPLAY_I2C_PORT, conf.mode, 0, 0, 0);
    if (err == ESP_ERR_INVALID_STATE) {
        /* Driver already installed, treat as success. */
        s_i2c_inited = true;
        return ESP_OK;
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_driver_install failed: %d", err);
        return err;
    }

    s_i2c_inited = true;
    ESP_LOGI(TAG, "I2C bus initialised on SDA=%d SCL=%d freq=%d Hz",
             DISPLAY_I2C_SDA_GPIO, DISPLAY_I2C_SCL_GPIO, DISPLAY_I2C_FREQ_HZ);
    return ESP_OK;
}

esp_err_t ssd1363_reset(void)
{
    /* If reset pin is not configured, nothing to do. */
#if DISPLAY_RST_GPIO < 0
    return ESP_OK;
#else
    gpio_config_t io_conf = {
        .pin_bit_mask = 1ULL << DISPLAY_RST_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&io_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "gpio_config(reset) failed: %d", err);
        return err;
    }

    gpio_set_level(DISPLAY_RST_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(DISPLAY_RST_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(10));

    ESP_LOGI(TAG, "Panel reset pulse sent on GPIO %d", DISPLAY_RST_GPIO);
    return ESP_OK;
#endif
}

static esp_err_t ssd1363_send_bytes(bool is_cmd, const uint8_t *data, size_t len)
{
    if (!s_i2c_inited) {
        ESP_LOGE(TAG, "I2C bus not initialised, call ssd1363_bus_init() first");
        return ESP_ERR_INVALID_STATE;
    }
    if (data == NULL || len == 0) {
        return ESP_OK;
    }

    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    if (cmd == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = i2c_master_start(cmd);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_write_byte(cmd, (DISPLAY_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    /* Control byte: Co=0, D/C# = 0 for command, 1 for data.
     * This matches the typical SSD13xx I2C protocol.
     */
    uint8_t control = is_cmd ? 0x00 : 0x40;
    err = i2c_master_write_byte(cmd, control, true);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_write(cmd, (uint8_t *)data, len, true);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_stop(cmd);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_cmd_begin(DISPLAY_I2C_PORT,
                               cmd,
                               pdMS_TO_TICKS(I2C_TIMEOUT_MS));
    i2c_cmd_link_delete(cmd);

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_master_cmd_begin failed: %d", err);
    }
    return err;
}

esp_err_t ssd1363_write_cmd(uint8_t cmd_byte)
{
    return ssd1363_send_bytes(true, &cmd_byte, 1);
}

esp_err_t ssd1363_write_cmd_list(const uint8_t *cmds, size_t len)
{
    return ssd1363_send_bytes(true, cmds, len);
}

esp_err_t ssd1363_write_data(const uint8_t *data, size_t len)
{
    return ssd1363_send_bytes(false, data, len);
}

esp_err_t ssd1363_init_panel(void)
{
    esp_err_t err = ssd1363_bus_init();
    if (err != ESP_OK) {
        return err;
    }

    err = ssd1363_reset();
    if (err != ESP_OK) {
        return err;
    }

#if SSD1363_I2C_SCAN_ON_BOOT
    ssd1363_scan_i2c();
#endif

    /* Clamp runtime column offset against current DISPLAY_WIDTH. */
    err = ssd1363_set_col_offset_units(ssd1363_get_col_offset_units());
    if (err != ESP_OK) {
        return err;
    }

    /* Default init sequence (based on U8g2's SSD1363 256x128 driver). */
#if SSD1363_USE_DEFAULT_INIT
    err = ssd1363_cmd_unlock();
    if (err != ESP_OK) {
        return err;
    }

    err = ssd1363_display_off();
    if (err != ESP_OK) {
        return err;
    }

    /* Set Display Clock Divide/Oscillator Frequency (B3h, 1 byte). */
    err = ssd1363_write_cmd_args(0xB3, (const uint8_t[]){ SSD1363_INIT_CLOCK }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* Set Multiplex Ratio (CAh, 1 byte). Value is MUX-1. */
    err = ssd1363_set_multiplex_ratio((uint8_t)(DISPLAY_HEIGHT - 1));
    if (err != ESP_OK) {
        return err;
    }

    /* Display offset and start line. */
    err = ssd1363_set_display_offset(SSD1363_INIT_DISPLAY_OFFSET);
    if (err != ESP_OK) {
        return err;
    }
    err = ssd1363_set_start_line(SSD1363_INIT_START_LINE);
    if (err != ESP_OK) {
        return err;
    }

    /* Set Re-Map / Dual COM Line Mode (A0h, 2 bytes). */
    err = ssd1363_write_cmd_args(0xA0, (const uint8_t[]){ SSD1363_INIT_REMAP_A, SSD1363_INIT_REMAP_B }, 2);
    if (err != ESP_OK) {
        return err;
    }

    /* Display Enhancement A (B4h, 2 bytes). */
    err = ssd1363_write_cmd_args(0xB4, (const uint8_t[]){ SSD1363_INIT_ENH_A0, SSD1363_INIT_ENH_A1 }, 2);
    if (err != ESP_OK) {
        return err;
    }

    /* Contrast (C1h). */
    err = ssd1363_set_contrast(SSD1363_INIT_CONTRAST);
    if (err != ESP_OK) {
        return err;
    }

    /* Set voltage config: Vp pin (BAh). */
    err = ssd1363_write_cmd_args(0xBA, (const uint8_t[]){ SSD1363_INIT_VOLTAGE_CONFIG }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* Linear grayscale table (B9h). */
    err = ssd1363_write_cmd(0xB9);
    if (err != ESP_OK) {
        return err;
    }

    /* IREF selection (ADh). */
    err = ssd1363_write_cmd_args(0xAD, (const uint8_t[]){ SSD1363_INIT_IREF }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* Phase length / precharge timing (B1h). */
    err = ssd1363_set_precharge(SSD1363_INIT_PHASE_LENGTH);
    if (err != ESP_OK) {
        return err;
    }

    /* Precharge voltage (BBh). */
    err = ssd1363_write_cmd_args(0xBB, (const uint8_t[]){ SSD1363_INIT_PRECHARGE_VOLTAGE }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* Second precharge period (B6h). */
    err = ssd1363_write_cmd_args(0xB6, (const uint8_t[]){ SSD1363_INIT_SECOND_PRECHARGE }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* VCOMH (BEh). */
    err = ssd1363_set_vcomh(SSD1363_INIT_VCOMH);
    if (err != ESP_OK) {
        return err;
    }

    /* Normal display. */
    err = ssd1363_invert_display(false);
    if (err != ESP_OK) {
        return err;
    }

    /* Exit partial display (A9h). */
    err = ssd1363_write_cmd(0xA9);
    if (err != ESP_OK) {
        return err;
    }
#else
    /* Minimal init for custom bring-up: unlock + display off. */
    (void)ssd1363_cmd_unlock();
    (void)ssd1363_display_off();
#endif

    /* Set a default full-frame address window so subsequent writes cover the panel. */
    err = ssd1363_set_addr_window(0, DISPLAY_WIDTH - 1, 0, DISPLAY_HEIGHT - 1);
    if (err != ESP_OK) {
        return err;
    }

    /* Finally, turn the display ON. */
    err = ssd1363_display_on();
    if (err != ESP_OK) {
        return err;
    }

#if SSD1363_BOOT_TEST_PATTERN
    err = ssd1363_boot_test_pattern();
    if (err != ESP_OK) {
        return err;
    }
#endif

    ESP_LOGI(TAG, "SSD1363 init OK (addr=0x%02X, col_offset=%u)", DISPLAY_I2C_ADDR, (unsigned)ssd1363_get_col_offset_units());
    return ESP_OK;
}

esp_err_t ssd1363_display_on(void)
{
    return ssd1363_write_cmd(0xAF); /* Display ON */
}

esp_err_t ssd1363_display_off(void)
{
    return ssd1363_write_cmd(0xAE); /* Display OFF */
}

uint8_t ssd1363_get_col_offset_units(void)
{
    return s_col_offset_units;
}

esp_err_t ssd1363_set_col_offset_units(uint8_t offset_units)
{
#if DISPLAY_COLOR_BITS == 4
    uint16_t cols = (uint16_t)((DISPLAY_WIDTH - 1) >> 2);
    if (cols > SSD1363_MAX_COL_ADDR) {
        return ESP_ERR_INVALID_STATE;
    }
    uint16_t max_off = (uint16_t)(SSD1363_MAX_COL_ADDR - cols);
    if ((uint16_t)offset_units > max_off) {
        offset_units = (uint8_t)max_off;
    }
#else
    (void)offset_units;
    offset_units = 0;
#endif
    s_col_offset_units = offset_units;
    return ESP_OK;
}

esp_err_t ssd1363_set_addr_window(uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1)
{
    /* Common SSD13xx style addressing; verify with SSD1363 datasheet for final use.
     *
     * For SSD1363 in 4bpp mode, column address units are groups of 4 pixels
     * (2 bytes per column per row). Most 256x128 panels require a horizontal
     * column offset because the controller has 320 segments.
     */
#if DISPLAY_COLOR_BITS == 4
    uint16_t col0 = (uint16_t)(ssd1363_get_col_offset_units() + (x0 >> 2));
    uint16_t col1 = (uint16_t)(ssd1363_get_col_offset_units() + (x1 >> 2));
    if (col0 > SSD1363_MAX_COL_ADDR || col1 > SSD1363_MAX_COL_ADDR) {
        return ESP_ERR_INVALID_ARG;
    }
    x0 = col0;
    x1 = col1;
#endif
    if (y0 > 255 || y1 > 255) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t cmds[6];
    cmds[0] = 0x15; /* Set Column Address */
    cmds[1] = (uint8_t)x0;
    cmds[2] = (uint8_t)x1;
    cmds[3] = 0x75; /* Set Row Address */
    cmds[4] = (uint8_t)y0;
    cmds[5] = (uint8_t)y1;
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_write_ram_start(void)
{
    return ssd1363_write_cmd(0x5C); /* Write RAM */
}

/* Optional configuration helpers (verify codes for SSD1363 specifically). */
esp_err_t ssd1363_set_contrast(uint8_t contrast)
{
    uint8_t cmds[2] = { 0xC1, contrast };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_multiplex_ratio(uint8_t ratio)
{
    uint8_t cmds[2] = { 0xCA, ratio };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_display_offset(uint8_t offset)
{
    uint8_t cmds[2] = { 0xA2, offset };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_start_line(uint8_t line)
{
    uint8_t cmds[2] = { 0xA1, line };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_remap(uint8_t config)
{
    /* SSD1363: "Set Re-map and Dual COM Line mode" (A0h) takes 2 bytes.
     * Keep legacy signature and send a zeroed second byte by default.
     */
    uint8_t cmds[3] = { 0xA0, config, 0x00 };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_display_clock(uint8_t divide, uint8_t freq)
{
    /* 0xB3: upper nibble freq, lower nibble divide */
    uint8_t val = (uint8_t)(((freq & 0x0F) << 4) | (divide & 0x0F));
    uint8_t cmds[2] = { 0xB3, val };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_precharge(uint8_t period)
{
    uint8_t cmds[2] = { 0xB1, period };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_vcomh(uint8_t level)
{
    uint8_t cmds[2] = { 0xBE, level };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_entire_display_on(bool on)
{
    return ssd1363_write_cmd(on ? 0xA5 : 0xA4);
}

esp_err_t ssd1363_invert_display(bool invert)
{
    return ssd1363_write_cmd(invert ? 0xA7 : 0xA6);
}

esp_err_t ssd1363_begin_frame(uint16_t x0, uint16_t y0, uint16_t x1_incl, uint16_t y1_incl)
{
    if (x0 > x1_incl || y0 > y1_incl) {
        return ESP_ERR_INVALID_ARG;
    }
    /* Clip to panel bounds */
    if (x0 >= DISPLAY_WIDTH || y0 >= DISPLAY_HEIGHT) {
        return ESP_ERR_INVALID_ARG;
    }
    if (x1_incl >= DISPLAY_WIDTH)  x1_incl = (uint16_t)(DISPLAY_WIDTH - 1);
    if (y1_incl >= DISPLAY_HEIGHT) y1_incl = (uint16_t)(DISPLAY_HEIGHT - 1);

    esp_err_t err = ssd1363_set_addr_window(x0, x1_incl, y0, y1_incl);
    if (err != ESP_OK) return err;
    return ssd1363_write_ram_start();
}
