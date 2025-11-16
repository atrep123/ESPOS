#include "store.h"

#include <stdbool.h>

#include "nvs_flash.h"
#include "nvs.h"

#define SCHEMA_VER 1U

static store_conf_t g_conf = {
    .schema = SCHEMA_VER,
    .bg_rgb = 0x101010,
};
static bool s_inited = false;

esp_err_t store_init(store_conf_t *out)
{
    if (out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    nvs_handle_t h;
    err = nvs_open("app", NVS_READWRITE, &h);
    if (err != ESP_OK) {
        return err;
    }

    size_t sz = sizeof(*out);
    err = nvs_get_blob(h, "conf", &g_conf, &sz);
    if (err != ESP_OK || g_conf.schema != SCHEMA_VER) {
        g_conf.schema = SCHEMA_VER;
        g_conf.bg_rgb = 0x101010;
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

    *out = g_conf;
    return ESP_OK;
}

esp_err_t store_set_bg_rgb(uint32_t rgb)
{
    if (!s_inited) {
        return ESP_ERR_INVALID_STATE;
    }

    g_conf.bg_rgb = rgb;

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
