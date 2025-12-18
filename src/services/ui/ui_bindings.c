#include "ui_bindings.h"

#include <string.h>

#include "display/ssd1363.h"
#include "services/store/store.h"

bool ui_bind_get_int(const char *key, int *out)
{
    if (out == NULL) {
        return false;
    }
    *out = 0;
    if (key == NULL || *key == '\0') {
        return false;
    }

    store_conf_t conf;
    if (store_get_conf(&conf) != ESP_OK) {
        return false;
    }

    if (strcmp(key, "contrast") == 0) {
        *out = (int)conf.display_contrast;
        return true;
    }
    if (strcmp(key, "col_offset") == 0) {
        *out = (int)conf.display_col_offset;
        return true;
    }

    return false;
}

esp_err_t ui_bind_set_int(const char *key, int v)
{
    if (key == NULL || *key == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    if (strcmp(key, "contrast") == 0) {
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        esp_err_t err = store_set_display_contrast((uint8_t)v);
        if (err != ESP_OK) {
            return err;
        }
        return ssd1363_set_contrast((uint8_t)v);
    }

    if (strcmp(key, "col_offset") == 0) {
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        (void)ssd1363_set_col_offset_units((uint8_t)v);
        uint8_t actual = ssd1363_get_col_offset_units();
        esp_err_t err = store_set_display_col_offset(actual);
        if (err != ESP_OK) {
            return err;
        }
        return ESP_OK;
    }

    return ESP_ERR_NOT_FOUND;
}

bool ui_bind_get_bool(const char *key, bool *out)
{
    if (out == NULL) {
        return false;
    }
    *out = false;
    if (key == NULL || *key == '\0') {
        return false;
    }

    store_conf_t conf;
    if (store_get_conf(&conf) != ESP_OK) {
        return false;
    }

    if (strcmp(key, "invert") == 0) {
        *out = (conf.display_invert != 0);
        return true;
    }

    return false;
}

esp_err_t ui_bind_set_bool(const char *key, bool v)
{
    if (key == NULL || *key == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    if (strcmp(key, "invert") == 0) {
        esp_err_t err = store_set_display_invert(v);
        if (err != ESP_OK) {
            return err;
        }
        return ssd1363_invert_display(v);
    }

    return ESP_ERR_NOT_FOUND;
}

