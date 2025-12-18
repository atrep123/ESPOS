#include <stddef.h>
#include <stdint.h>

#ifndef ESP_PLATFORM

#include "esp_err.h"
#include "display/ssd1363.h"
#include "ssd1363_stub_capture.h"

static uint16_t s_last_x0 = 0;
static uint16_t s_last_y0 = 0;
static uint16_t s_last_x1 = 0;
static uint16_t s_last_y1 = 0;
static size_t s_write_calls = 0;
static size_t s_total_bytes = 0;
static uint8_t s_first_write[256];
static size_t s_first_write_len = 0;

void ssd1363_stub_reset(void)
{
    s_last_x0 = s_last_y0 = s_last_x1 = s_last_y1 = 0;
    s_write_calls = 0;
    s_total_bytes = 0;
    s_first_write_len = 0;
}

uint16_t ssd1363_stub_last_x0(void) { return s_last_x0; }
uint16_t ssd1363_stub_last_y0(void) { return s_last_y0; }
uint16_t ssd1363_stub_last_x1(void) { return s_last_x1; }
uint16_t ssd1363_stub_last_y1(void) { return s_last_y1; }

size_t ssd1363_stub_write_calls(void) { return s_write_calls; }
size_t ssd1363_stub_first_write_len(void) { return s_first_write_len; }

size_t ssd1363_stub_copy_first_write(uint8_t *out, size_t max_out)
{
    if (out == NULL || max_out == 0 || s_first_write_len == 0) {
        return 0;
    }
    size_t n = s_first_write_len;
    if (n > max_out) {
        n = max_out;
    }
    for (size_t i = 0; i < n; ++i) {
        out[i] = s_first_write[i];
    }
    return n;
}

esp_err_t ssd1363_begin_frame(uint16_t x0, uint16_t y0, uint16_t x1_incl, uint16_t y1_incl)
{
    s_last_x0 = x0;
    s_last_y0 = y0;
    s_last_x1 = x1_incl;
    s_last_y1 = y1_incl;
    return ESP_OK;
}

esp_err_t ssd1363_write_data(const uint8_t *data, size_t len)
{
    (void)data;
    (void)len;
    if (data != NULL && len > 0) {
        if (s_write_calls == 0) {
            s_first_write_len = len;
            if (s_first_write_len > sizeof(s_first_write)) {
                s_first_write_len = sizeof(s_first_write);
            }
            for (size_t i = 0; i < s_first_write_len; ++i) {
                s_first_write[i] = data[i];
            }
        }
        s_write_calls += 1;
        s_total_bytes += len;
    }
    return ESP_OK;
}

#endif
