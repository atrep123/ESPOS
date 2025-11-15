#pragma once

#include "esp_lcd_panel_ops.h"

#include "ui.h"

uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b);

void render_frame_striped(esp_lcd_panel_handle_t panel, const ui_state_t *st);
