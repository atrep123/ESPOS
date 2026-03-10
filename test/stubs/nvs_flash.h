#pragma once

/* Minimal nvs_flash stub for native/host builds. */

#include "esp_err.h"

esp_err_t nvs_flash_init(void);
esp_err_t nvs_flash_erase(void);
