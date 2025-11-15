#pragma once

#include <stddef.h>
#include <stdint.h>

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
 * This currently sends only a placeholder sequence
 * (e.g. display OFF) and logs a warning so you remember
 * to adjust it based on the SSD1363 datasheet.
 */
esp_err_t ssd1363_init_panel(void);

/* Send a single command byte. */
esp_err_t ssd1363_write_cmd(uint8_t cmd);

/* Send a list of command bytes. */
esp_err_t ssd1363_write_cmd_list(const uint8_t *cmds, size_t len);

/* Send raw data bytes (e.g. pixel data). */
esp_err_t ssd1363_write_data(const uint8_t *data, size_t len);

