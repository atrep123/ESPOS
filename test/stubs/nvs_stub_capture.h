#pragma once

/* Control/capture API for the NVS stub. */

#include <stddef.h>
#include "esp_err.h"

/* Reset all NVS stub state. Call in setUp(). */
void nvs_stub_reset(void);

/* Control nvs_flash_init return value. */
void nvs_stub_set_flash_init_err(esp_err_t err);

/* Control nvs_open return value. */
void nvs_stub_set_open_err(esp_err_t err);

/* Stage blob data that nvs_get_blob will return. Pass NULL to make it return NOT_FOUND. */
void nvs_stub_set_blob(const void *data, size_t len);

/* Query: how many times nvs_set_blob was called and what was written. */
size_t nvs_stub_set_blob_call_count(void);
size_t nvs_stub_copy_last_blob(void *out, size_t max_out);
