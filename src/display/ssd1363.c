#include "display/ssd1363.h"

#include "driver/gpio.h"
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#include "display_config.h"

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
    if (DISPLAY_RST_GPIO < 0) {
        return ESP_OK;
    }

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

    /* Placeholder init sequence – replace with the real one
     * from the SSD1363 datasheet for your module.
     */
    const uint8_t init_seq[] = {
        0xAE, /* Display OFF */
        /* TODO: add contrast, mux ratio, addressing mode, etc. */
    };
    (void)ssd1363_write_cmd_list(init_seq, sizeof(init_seq));

    ESP_LOGW(TAG, "SSD1363 init sequence is placeholder; update for your panel");
    return ESP_OK;
}

