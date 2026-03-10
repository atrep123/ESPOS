#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#ifndef ESP_PLATFORM

#include "esp_err.h"
#include "services/store/store.h"

static store_conf_t s_stub_conf;

esp_err_t store_init(store_conf_t *out)
{
    if (out) memset(out, 0, sizeof(*out));
    return ESP_OK;
}

esp_err_t store_get_conf(store_conf_t *out)
{
    if (out) *out = s_stub_conf;
    return ESP_OK;
}

esp_err_t store_set_bg_rgb(uint32_t rgb)
{
    s_stub_conf.bg_rgb = rgb;
    return ESP_OK;
}

esp_err_t store_set_display_contrast(uint8_t contrast)
{
    s_stub_conf.display_contrast = contrast;
    return ESP_OK;
}

esp_err_t store_set_display_invert(bool invert)
{
    s_stub_conf.display_invert = invert ? 1 : 0;
    return ESP_OK;
}

esp_err_t store_set_display_col_offset(uint8_t offset_units)
{
    s_stub_conf.display_col_offset = offset_units;
    return ESP_OK;
}

#endif
