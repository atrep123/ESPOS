#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#include "esp_err.h"

/* Low-level I2C driver for the SER2.7I-256128 (SSD1363).
 *
 * This is intentionally minimal: it sets up the I2C bus and
 * provides helpers to send commands and data bytes.
 * The actual init sequence and drawing logic can be refined
 * once the panel is wired and tested.
 */

/* Initialise the I2C bus for the display, using pins and
 * parameters from display_config.h.
 */
esp_err_t ssd1363_bus_init(void);

/* Toggle optional reset GPIO, if configured. Safe to call
 * even when DISPLAY_RST_GPIO is -1.
 */
esp_err_t ssd1363_reset(void);

/* Minimal panel initialisation.
 *
 * Default init sequence is based on U8g2's SSD1363 256x128 driver
 * and can be tweaked via macros in `display_config.h` / `user_config.h`.
 */
esp_err_t ssd1363_init_panel(void);

/* Send a single command byte. */
esp_err_t ssd1363_write_cmd(uint8_t cmd);

/* Send a list of command bytes. */
esp_err_t ssd1363_write_cmd_list(const uint8_t *cmds, size_t len);

/* Send raw data bytes (e.g. pixel data). */
esp_err_t ssd1363_write_data(const uint8_t *data, size_t len);

/* Helpers for addressing and display state. */
esp_err_t ssd1363_display_on(void);
esp_err_t ssd1363_display_off(void);
esp_err_t ssd1363_set_addr_window(uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1);
esp_err_t ssd1363_write_ram_start(void);
/* Begin a frame (sets clipped address window and enters RAM write). Returns error on invalid window. */
esp_err_t ssd1363_begin_frame(uint16_t x0, uint16_t y0, uint16_t x1_incl, uint16_t y1_incl);

/* SSD1363 horizontal column offset (4bpp column units = 4 pixels). */
uint8_t ssd1363_get_col_offset_units(void);
esp_err_t ssd1363_set_col_offset_units(uint8_t offset_units);

/* Optional configuration helpers (common SSD13xx style). Values must be
 * confirmed against SSD1363 datasheet; these functions only emit bytes. */
esp_err_t ssd1363_set_contrast(uint8_t contrast);
esp_err_t ssd1363_set_multiplex_ratio(uint8_t ratio);
esp_err_t ssd1363_set_display_offset(uint8_t offset);
esp_err_t ssd1363_set_start_line(uint8_t line);
esp_err_t ssd1363_set_remap(uint8_t config);
esp_err_t ssd1363_set_display_clock(uint8_t divide, uint8_t freq);
esp_err_t ssd1363_set_precharge(uint8_t period);
esp_err_t ssd1363_set_vcomh(uint8_t level);
esp_err_t ssd1363_entire_display_on(bool on);
esp_err_t ssd1363_invert_display(bool invert);
