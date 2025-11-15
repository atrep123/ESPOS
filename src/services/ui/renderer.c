#include "renderer.h"

#include "esp_err.h"
#include "esp_log.h"
#include "esp_lcd_panel_ops.h"

#include "display_config.h"

static const char *TAG = "ui_renderer";

uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((uint16_t)(r & 0xF8) << 8) | ((uint16_t)(g & 0xFC) << 3) | (uint16_t)(b >> 3);
}

void render_frame_striped(esp_lcd_panel_handle_t panel, const ui_state_t *st)
{
    if (st == NULL) {
        return;
    }

    /* If there is no real panel, fall back to a simple
     * text-based simulator over the log/serial output. */
    if (panel == NULL) {
        /* Map background color brightness to a bar. */
        uint8_t r = (uint8_t)((st->bg >> 11) & 0x1F) << 3;
        uint8_t g = (uint8_t)((st->bg >> 5) & 0x3F) << 2;
        uint8_t b = (uint8_t)(st->bg & 0x1F) << 3;
        uint16_t avg = (uint16_t)((r + g + b) / 3U);

        static const char levels[] = " .:-=+*#%@";
        int idx = (avg * (int)(sizeof(levels) - 2)) / 255;
        if (idx < 0) {
            idx = 0;
        }
        if (idx > (int)(sizeof(levels) - 2)) {
            idx = (int)(sizeof(levels) - 2);
        }

        char line[33];
        for (int i = 0; i < 32; ++i) {
            line[i] = levels[idx];
        }
        line[32] = '\0';

        ESP_LOGI(TAG,
                 "[SIM] t=%ld scene=%u btnA=%u bg=0x%04X",
                 (long)st->t,
                 (unsigned)st->scene,
                 (unsigned)st->btnA,
                 (unsigned)st->bg);
        ESP_LOGI(TAG, "[SIM] %s", line);
        return;
    }

    /* Simple placeholder renderer: solid background fill. */
    const int width = DISPLAY_WIDTH;
    const int height = DISPLAY_HEIGHT;

    static uint16_t buffer[DISPLAY_WIDTH * 16];

    int stripe_h = 20;
    for (int y = 0; y < height; y += stripe_h) {
        int h = stripe_h;
        if (y + h > height) {
            h = height - y;
        }

        uint16_t color = st->bg;
        for (int i = 0; i < width * h; ++i) {
            buffer[i] = color;
        }

        esp_err_t err = esp_lcd_panel_draw_bitmap(panel, 0, y, width, y + h, buffer);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "draw_bitmap failed: %d", err);
            break;
        }
    }
}
