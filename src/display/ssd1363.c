#include "display/ssd1363.h"

#include "driver/gpio.h"
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#include "display_config.h"
#include <stdbool.h>

static const char *TAG = "ssd1363";

#define I2C_TIMEOUT_MS 1000

static bool s_i2c_inited = false;

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

    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (DISPLAY_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);

    /* Control byte: Co=0, D/C# = 0 for command, 1 for data.
     * This matches the typical SSD13xx I2C protocol.
     */
    uint8_t control = is_cmd ? 0x00 : 0x40;
    i2c_master_write_byte(cmd, control, true);

    i2c_master_write(cmd, (uint8_t *)data, len, true);
    i2c_master_stop(cmd);

    esp_err_t err = i2c_master_cmd_begin(DISPLAY_I2C_PORT,
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

    /* Placeholder init; optional conservative default below guarded by macro. */
#if SSD1363_USE_DEFAULT_INIT
    /* Oscillator/clock: divide=1, freq=8 (tunable) */
    (void)ssd1363_set_display_clock(1, 8);
    /* Multiplex ratio: height-1 (e.g., 127 for 128 rows) */
    (void)ssd1363_set_multiplex_ratio((uint8_t)(DISPLAY_HEIGHT - 1));
    /* Display offset and start line */
    (void)ssd1363_set_display_offset(0);
    (void)ssd1363_set_start_line(0);
    /* Remap: device-specific bitfields; 0x00 baseline. Adjust for segment/COM scan direction. */
    (void)ssd1363_set_remap(0x00);
    /* Contrast, precharge, VCOMH: conservative mids */
    (void)ssd1363_set_contrast(0x7F);
    (void)ssd1363_set_precharge(0x22);
    (void)ssd1363_set_vcomh(0x34);
    /* Normal display */
    (void)ssd1363_invert_display(false);
#else
    const uint8_t init_seq[] = {
        0xAE, /* Display OFF */
        /*
         * NOTE: Add your panel's required sequence here. Typical SSD13xx bring-up includes:
         *   - Set Display Clock Divide/Oscillator Frequency (0xB3, div|freq)
         *   - Set Multiplex Ratio (0xA8, ratio)
         *   - Set Display Offset (0xA2, offset)
         *   - Set Start Line (0xA1, line)
         *   - Set Remap/Color Depth (device specific; for SSD1363 verify command)
         *   - Set Contrast (0xC1 or device-specific)
         *   - Set Precharge Period (0xB1)
         *   - Set VCOMH (0xBE)
         *   - Normal Display Mode (0xA6) or Invert (0xA7)
         */
    };
    (void)ssd1363_write_cmd_list(init_seq, sizeof(init_seq));
#endif

    /* Set a default full-frame address window so subsequent writes cover the panel. */
    (void)ssd1363_set_addr_window(0, DISPLAY_WIDTH - 1, 0, DISPLAY_HEIGHT - 1);

    /* Finally, turn the display ON. */
    (void)ssd1363_display_on();

    ESP_LOGW(TAG, "SSD1363 init sequence is placeholder; update for your panel");
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

esp_err_t ssd1363_set_addr_window(uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1)
{
    /* Common SSD13xx style addressing; verify with SSD1363 datasheet for final use. */
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
    uint8_t cmds[2] = { 0xA8, ratio };
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
    /* Device-specific; many SSD13xx use 0xA0 with bitfields */
    uint8_t cmds[2] = { 0xA0, config };
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
