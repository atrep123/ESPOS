#pragma once

#include <stdbool.h>
#include "esp_err.h"

/* Runtime binding registry (UI value editors). Keys are small stable strings,
 * e.g. "contrast", "invert", "col_offset".
 */

bool ui_bind_get_int(const char *key, int *out);
esp_err_t ui_bind_set_int(const char *key, int v);

bool ui_bind_get_bool(const char *key, bool *out);
esp_err_t ui_bind_set_bool(const char *key, bool v);

