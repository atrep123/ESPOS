#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#include "esp_lcd_panel_ops.h"

#include "kernel/msgbus.h"
#include "ui_core.h"

void ui_start(esp_lcd_panel_handle_t panel);
