#pragma once

#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"

/* Runtime binding registry.
 *
 * Two layers:
 *   1. Generic in-RAM store — any service can read/write arbitrary keys.
 *   2. Hardware-backed keys ("contrast", "invert", "col_offset") that
 *      additionally persist to NVS and apply to peripherals.
 */

/* Integer bindings */
bool ui_bind_get_int(const char *key, int *out);
esp_err_t ui_bind_set_int(const char *key, int v);

/* Boolean bindings (stored as int 0/1 in the generic store) */
bool ui_bind_get_bool(const char *key, bool *out);
esp_err_t ui_bind_set_bool(const char *key, bool v);

/* String bindings */
bool ui_bind_get_str(const char *key, char *out, size_t out_cap);
esp_err_t ui_bind_set_str(const char *key, const char *value);

/* Clear all entries in the generic store (e.g. on scene switch). */
void ui_bind_clear_all(void);

/* Initialise the binding subsystem (creates the internal mutex). */
void ui_bind_init(void);

