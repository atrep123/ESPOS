#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

typedef struct {
    uint32_t schema;
    uint32_t bg_rgb;
    uint8_t display_contrast;   /* 0..255 */
    uint8_t display_invert;     /* 0/1 */
    uint8_t display_col_offset; /* SSD1363 column offset (units of 4px) */
    uint8_t _reserved0;
} store_conf_t;

esp_err_t store_init(store_conf_t *out);
void store_deinit(void);
esp_err_t store_get_conf(store_conf_t *out);
esp_err_t store_set_bg_rgb(uint32_t rgb);

esp_err_t store_set_display_contrast(uint8_t contrast);
esp_err_t store_set_display_invert(bool invert);
esp_err_t store_set_display_col_offset(uint8_t offset_units);
