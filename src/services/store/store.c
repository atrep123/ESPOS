#include "store.h"

#include <stdbool.h>

#include "display_config.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "store";

#define SCHEMA_VER 2U

static store_conf_t g_conf = {
    .schema = SCHEMA_VER,
    .bg_rgb = 0x101010,
    .display_contrast = 0xFF,
    .display_invert = 0,
    .display_col_offset = SSD1363_COL_OFFSET,
    ._reserved0 = 0,
};
static bool s_inited = false;
static SemaphoreHandle_t s_store_mtx;

#define STORE_LOCK()   do { if (s_store_mtx) xSemaphoreTake(s_store_mtx, portMAX_DELAY); } while (0)
#define STORE_UNLOCK() do { if (s_store_mtx) xSemaphoreGive(s_store_mtx); } while (0)

esp_err_t store_init(store_conf_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    if (s_inited) {
        *out = g_conf;
        return ESP_OK;
    }

    if (s_store_mtx == NULL) {
        s_store_mtx = xSemaphoreCreateMutex();
    }

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        err = nvs_flash_erase();
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "nvs_flash_erase failed: %s", esp_err_to_name(err));
            return err;
        }
        err = nvs_flash_init();
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nvs_flash_init failed: %s", esp_err_to_name(err));
        return err;
    }

    nvs_handle_t h;
    err = nvs_open("app", NVS_READWRITE, &h);
    if (err != ESP_OK) {
        return err;
    }

    size_t sz = sizeof(g_conf);
    err = nvs_get_blob(h, "conf", &g_conf, &sz);
    if (err != ESP_OK || sz != sizeof(g_conf) || g_conf.schema != SCHEMA_VER) {
        g_conf.schema = SCHEMA_VER;
        g_conf.bg_rgb = 0x101010;
        g_conf.display_contrast = 0xFF;
        g_conf.display_invert = 0;
        g_conf.display_col_offset = SSD1363_COL_OFFSET;
        g_conf._reserved0 = 0;
        err = nvs_set_blob(h, "conf", &g_conf, sizeof(g_conf));
        if (err == ESP_OK) {
            err = nvs_commit(h);
        }
    }

    nvs_close(h);
    s_inited = true;
    *out = g_conf;
    return err;
}

esp_err_t store_get_conf(store_conf_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!s_inited) {
        return ESP_ERR_INVALID_STATE;
    }

    STORE_LOCK();
    *out = g_conf;
    STORE_UNLOCK();
    return ESP_OK;
}

esp_err_t store_set_bg_rgb(uint32_t rgb)
{
    if (!s_inited) {
        return ESP_ERR_INVALID_STATE;
    }

    STORE_LOCK();
    g_conf.bg_rgb = rgb;

    nvs_handle_t h;
    esp_err_t err = nvs_open("app", NVS_READWRITE, &h);
    if (err != ESP_OK) {
        STORE_UNLOCK();
        return err;
    }

    err = nvs_set_blob(h, "conf", &g_conf, sizeof(g_conf));
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }

    nvs_close(h);
    STORE_UNLOCK();
    return err;
}

static esp_err_t store_save_conf(void)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open("app", NVS_READWRITE, &h);
    if (err != ESP_OK) {
        return err;
    }

    err = nvs_set_blob(h, "conf", &g_conf, sizeof(g_conf));
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }

    nvs_close(h);
    return err;
}

esp_err_t store_set_display_contrast(uint8_t contrast)
{
    if (!s_inited) {
        return ESP_ERR_INVALID_STATE;
    }

    STORE_LOCK();
    g_conf.display_contrast = contrast;
    esp_err_t err = store_save_conf();
    STORE_UNLOCK();
    return err;
}

esp_err_t store_set_display_invert(bool invert)
{
    if (!s_inited) {
        return ESP_ERR_INVALID_STATE;
    }

    STORE_LOCK();
    g_conf.display_invert = invert ? 1 : 0;
    esp_err_t err = store_save_conf();
    STORE_UNLOCK();
    return err;
}

esp_err_t store_set_display_col_offset(uint8_t offset_units)
{
    if (!s_inited) {
        return ESP_ERR_INVALID_STATE;
    }

    if (offset_units > 79) {
        offset_units = 79;
    }

    STORE_LOCK();
    g_conf.display_col_offset = offset_units;
    esp_err_t err = store_save_conf();
    STORE_UNLOCK();
    return err;
}
