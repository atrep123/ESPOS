#pragma once

/* Minimal ESP-IDF compatibility stub for native/host builds. */

typedef int esp_err_t;

#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_INVALID_ARG -2
#define ESP_ERR_INVALID_SIZE -3
#define ESP_ERR_INVALID_STATE -4
#define ESP_ERR_NO_MEM -5
#define ESP_ERR_NOT_FOUND -6

/* NVS error codes used by store.c */
#define ESP_ERR_NVS_NO_FREE_PAGES   0x1100
#define ESP_ERR_NVS_NEW_VERSION_FOUND 0x1101
#define ESP_ERR_NVS_NOT_FOUND       0x1102

const char *esp_err_to_name(esp_err_t code);

