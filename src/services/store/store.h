#pragma once

#include "esp_err.h"

typedef struct {
    uint32_t schema;
    uint32_t bg_rgb;
} store_conf_t;

esp_err_t store_init(store_conf_t *out);
esp_err_t store_get_conf(store_conf_t *out);
esp_err_t store_set_bg_rgb(uint32_t rgb);
