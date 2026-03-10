#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifndef ESP_PLATFORM

#include "esp_err.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "nvs_stub_capture.h"

#define NVS_STUB_BUF_SIZE 256

static esp_err_t s_flash_init_err = ESP_OK;
static esp_err_t s_open_err = ESP_OK;

static uint8_t s_blob[NVS_STUB_BUF_SIZE];
static size_t s_blob_len = 0;
static int s_blob_present = 0; /* 1 = get_blob returns data; 0 = NOT_FOUND */

static uint8_t s_last_set[NVS_STUB_BUF_SIZE];
static size_t s_last_set_len = 0;
static size_t s_set_calls = 0;

void nvs_stub_reset(void)
{
    s_flash_init_err = ESP_OK;
    s_open_err = ESP_OK;
    memset(s_blob, 0, sizeof(s_blob));
    s_blob_len = 0;
    s_blob_present = 0;
    memset(s_last_set, 0, sizeof(s_last_set));
    s_last_set_len = 0;
    s_set_calls = 0;
}

void nvs_stub_set_flash_init_err(esp_err_t err) { s_flash_init_err = err; }
void nvs_stub_set_open_err(esp_err_t err) { s_open_err = err; }

void nvs_stub_set_blob(const void *data, size_t len)
{
    if (data == NULL) {
        s_blob_present = 0;
        s_blob_len = 0;
        return;
    }
    if (len > NVS_STUB_BUF_SIZE) {
        len = NVS_STUB_BUF_SIZE;
    }
    memcpy(s_blob, data, len);
    s_blob_len = len;
    s_blob_present = 1;
}

size_t nvs_stub_set_blob_call_count(void) { return s_set_calls; }

size_t nvs_stub_copy_last_blob(void *out, size_t max_out)
{
    if (out == NULL || max_out == 0 || s_last_set_len == 0) {
        return 0;
    }
    size_t n = s_last_set_len;
    if (n > max_out) {
        n = max_out;
    }
    memcpy(out, s_last_set, n);
    return n;
}

/* ---------- NVS API implementation ---------- */

esp_err_t nvs_flash_init(void)
{
    return s_flash_init_err;
}

esp_err_t nvs_flash_erase(void)
{
    return ESP_OK;
}

esp_err_t nvs_open(const char *namespace_name, nvs_open_mode_t open_mode, nvs_handle_t *out_handle)
{
    (void)namespace_name;
    (void)open_mode;
    if (s_open_err != ESP_OK) {
        return s_open_err;
    }
    if (out_handle) {
        *out_handle = 1; /* dummy handle */
    }
    return ESP_OK;
}

esp_err_t nvs_get_blob(nvs_handle_t handle, const char *key, void *out_value, size_t *length)
{
    (void)handle;
    (void)key;
    if (!s_blob_present) {
        return ESP_ERR_NVS_NOT_FOUND;
    }
    if (out_value && length) {
        size_t n = s_blob_len;
        if (n > *length) {
            n = *length;
        }
        memcpy(out_value, s_blob, n);
        *length = n;
    }
    return ESP_OK;
}

esp_err_t nvs_set_blob(nvs_handle_t handle, const char *key, const void *value, size_t length)
{
    (void)handle;
    (void)key;
    s_set_calls++;
    s_last_set_len = length;
    if (length > NVS_STUB_BUF_SIZE) {
        s_last_set_len = NVS_STUB_BUF_SIZE;
    }
    if (value && s_last_set_len > 0) {
        memcpy(s_last_set, value, s_last_set_len);
    }
    /* Also update the readable blob so get_blob returns updated data. */
    s_blob_present = 1;
    s_blob_len = s_last_set_len;
    if (s_blob_len > 0) {
        memcpy(s_blob, s_last_set, s_blob_len);
    }
    return ESP_OK;
}

esp_err_t nvs_commit(nvs_handle_t handle)
{
    (void)handle;
    return ESP_OK;
}

void nvs_close(nvs_handle_t handle)
{
    (void)handle;
}

#endif
