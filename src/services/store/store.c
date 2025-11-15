#include "store.h"

#include "nvs_flash.h"
#include "nvs.h"

#define SCHEMA_VER 1U

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
    err = nvs_get_blob(h, "conf", out, &sz);
    if (err != ESP_OK || out->schema != SCHEMA_VER) {
        out->schema = SCHEMA_VER;
        out->bg_rgb = 0x101010;
        err = nvs_set_blob(h, "conf", out, sizeof(*out));
        if (err == ESP_OK) {
            err = nvs_commit(h);
        }
    }

    nvs_close(h);
    return err;
}

