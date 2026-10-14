/* Deliberately simulated display transport, never opens hardware. */
#include "display/ssd1363.h"
#include "display_config.h"
#include <stdio.h>
int sim_display_status;
static uint8_t col_offset;
static unsigned x, y, start_x, end_x;
static unsigned char pixels[DISPLAY_WIDTH * DISPLAY_HEIGHT / 2];
esp_err_t ssd1363_init_panel(void) { return sim_display_status; }
esp_err_t ssd1363_set_contrast(uint8_t v) { (void)v; return sim_display_status; }
esp_err_t ssd1363_invert_display(bool v) { (void)v; return sim_display_status; }
uint8_t ssd1363_get_col_offset_units(void) { return col_offset; }
esp_err_t ssd1363_set_col_offset_units(uint8_t v) { col_offset = v; return sim_display_status; }
esp_err_t ssd1363_begin_frame(uint16_t a, uint16_t b, uint16_t c, uint16_t d)
{
    (void)d; start_x = a / 2; end_x = c / 2; x = start_x; y = b;
    return sim_display_status;
}
esp_err_t ssd1363_write_data(const uint8_t *data, size_t len)
{
    if (sim_display_status) return sim_display_status;
    for (size_t i = 0; i < len; i++) {
        if (y < DISPLAY_HEIGHT && x < DISPLAY_WIDTH / 2)
            pixels[y * (DISPLAY_WIDTH / 2) + x] = data[i];
        if (++x > end_x) { x = start_x; y++; }
    }
    return ESP_OK;
}
int sim_save_frame(const char *path)
{
    FILE *f = fopen(path, "wb");
    if (!f) return 1;
    fprintf(f, "P5\n%d %d\n255\n", DISPLAY_WIDTH, DISPLAY_HEIGHT);
    for (size_t i = 0; i < sizeof(pixels); i++) {
        fputc((pixels[i] >> 4) * 17, f); fputc((pixels[i] & 15) * 17, f);
    }
    return fclose(f) != 0;
}
