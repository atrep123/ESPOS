#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

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
size_t ssd1363_stub_total_bytes(void) { return s_total_bytes; }
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

/* Additional stubs for ssd1363 functions used by ui_bindings */
static uint8_t s_contrast = 0;
static uint8_t s_col_offset = 0;
static uint8_t s_invert = 0;

esp_err_t ssd1363_set_contrast(uint8_t contrast)
{
    s_contrast = contrast;
    return ESP_OK;
}

uint8_t ssd1363_get_col_offset_units(void)
{
    return s_col_offset;
}

esp_err_t ssd1363_set_col_offset_units(uint8_t offset_units)
{
    s_col_offset = offset_units;
    return ESP_OK;
}

esp_err_t ssd1363_invert_display(bool invert)
{
    s_invert = invert ? 1 : 0;
    return ESP_OK;
}

/* Remaining SSD1363 stubs — not yet exercised by tests but required
 * for linking if any test includes a source file that calls them. */

esp_err_t ssd1363_bus_init(void) { return ESP_OK; }
esp_err_t ssd1363_reset(void) { return ESP_OK; }
esp_err_t ssd1363_init_panel(void) { return ESP_OK; }
esp_err_t ssd1363_write_cmd(uint8_t cmd) { (void)cmd; return ESP_OK; }
esp_err_t ssd1363_write_cmd_list(const uint8_t *cmds, size_t len) { (void)cmds; (void)len; return ESP_OK; }
esp_err_t ssd1363_display_on(void) { return ESP_OK; }
esp_err_t ssd1363_display_off(void) { return ESP_OK; }
esp_err_t ssd1363_set_addr_window(uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1) { (void)x0; (void)x1; (void)y0; (void)y1; return ESP_OK; }
esp_err_t ssd1363_write_ram_start(void) { return ESP_OK; }
esp_err_t ssd1363_set_multiplex_ratio(uint8_t ratio) { (void)ratio; return ESP_OK; }
esp_err_t ssd1363_set_display_offset(uint8_t offset) { (void)offset; return ESP_OK; }
esp_err_t ssd1363_set_start_line(uint8_t line) { (void)line; return ESP_OK; }
esp_err_t ssd1363_set_remap(uint8_t config) { (void)config; return ESP_OK; }
esp_err_t ssd1363_set_display_clock(uint8_t divide, uint8_t freq) { (void)divide; (void)freq; return ESP_OK; }
esp_err_t ssd1363_set_precharge(uint8_t period) { (void)period; return ESP_OK; }
esp_err_t ssd1363_set_vcomh(uint8_t level) { (void)level; return ESP_OK; }
esp_err_t ssd1363_entire_display_on(bool on) { (void)on; return ESP_OK; }

#endif
