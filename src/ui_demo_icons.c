#include "ui_demo_icons.h"

#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "icons.h"

static const char *TAG = "ui_icon_demo";

#if HAVE_ICONS
/* Forward declarations for commonly used Material icons (16px). */
extern const icon_t mi_network_wifi_16px;
extern const icon_t mi_bluetooth_16px;
extern const icon_t mi_battery_full_16px;
extern const icon_t mi_folder_16px;
extern const icon_t mi_file_upload_16px;
extern const icon_t mi_search_16px;
extern const icon_t mi_settings_16px;
extern const icon_t mi_power_settings_new_16px;

/* 24px variants */
extern const icon_t mi_network_wifi_24px;
extern const icon_t mi_bluetooth_24px;
extern const icon_t mi_battery_full_24px;
extern const icon_t mi_folder_24px;
extern const icon_t mi_file_upload_24px;
extern const icon_t mi_search_24px;
extern const icon_t mi_settings_24px;
extern const icon_t mi_power_settings_new_24px;
#endif

static uint8_t s_icon_size_px = 16;
static enum display_blit_mode s_icon_mode = BLIT_NORMAL;

typedef struct {
    const icon_t *icon_16;
    const icon_t *icon_24;
} icon_pair_t;

#if HAVE_ICONS
static const icon_pair_t k_demo_icons[] = {
    { &mi_network_wifi_16px,        &mi_network_wifi_24px },
    { &mi_bluetooth_16px,           &mi_bluetooth_24px },
    { &mi_battery_full_16px,        &mi_battery_full_24px },
    { &mi_folder_16px,              &mi_folder_24px },
    { &mi_file_upload_16px,         &mi_file_upload_24px },
    { &mi_search_16px,              &mi_search_24px },
    { &mi_settings_16px,            &mi_settings_24px },
    { &mi_power_settings_new_16px,  &mi_power_settings_new_24px },
};
#endif

#if HAVE_ICONS
static const icon_t *pick_icon(const icon_pair_t *p, uint8_t size_px)
{
    if (size_px >= 24 && p->icon_24) {
        return p->icon_24;
    }
    if (p->icon_16) {
        return p->icon_16;
    }
    return p->icon_24;
}
#endif

void ui_icon_set_size(uint8_t px)
{
    s_icon_size_px = (px == 24) ? 24 : 16;
}

void ui_icon_set_mode(enum display_blit_mode mode)
{
    switch (mode) {
        case BLIT_NORMAL:
        case BLIT_INVERT:
        case BLIT_XOR:
            s_icon_mode = mode;
            break;
        default:
            s_icon_mode = BLIT_NORMAL;
            break;
    }
}

#if HAVE_ICONS
static void render_icon_grid(display_t *d, uint8_t size_px, enum display_blit_mode mode)
{
    if (!d || !d->buf) {
        return;
    }
    const int spacing = (int)size_px + 4;
    const int start_x = 4;
    const int start_y = 4;
    const size_t count = sizeof(k_demo_icons) / sizeof(k_demo_icons[0]);

    for (size_t i = 0; i < count; ++i) {
        const int16_t gx = (int16_t)(start_x + (int)(i % 4) * spacing);
        const int16_t gy = (int16_t)(start_y + (int)(i / 4) * spacing);
        const icon_t *ic = pick_icon(&k_demo_icons[i], size_px);
        if (ic) {
            display_blit_icon_mode(d, ic, gx, gy, mode);
        }
    }
}
#endif

void ui_icon_bench(display_t *d, uint32_t count, uint8_t size_px, enum display_blit_mode mode, char *out_json, size_t out_len)
{
#if HAVE_ICONS
    if (!d || !d->buf || count == 0 || out_json == NULL || out_len == 0) {
        return;
    }

    ui_swbuf_clear(d->buf, 0);

    const uint64_t t0 = (uint64_t)esp_timer_get_time();
    for (uint32_t i = 0; i < count; ++i) {
        render_icon_grid(d, size_px, mode);
    }
    const uint64_t t1 = (uint64_t)esp_timer_get_time();

    const double usec = (double)(t1 - t0);
    const double draws = (double)count;
    const double us_per_draw = (draws > 0.0) ? (usec / draws) : 0.0;
    const double fps = (us_per_draw > 0.0) ? (1000000.0 / us_per_draw) : 0.0;

    int sret = snprintf(out_json, out_len,
                   "{\"count\":%lu,\"size\":%u,\"mode\":\"%s\",\"us_per_draw\":%.3f,\"fps\":%.2f}",
                   (unsigned long)count,
                   (unsigned int)size_px,
                   (mode == BLIT_INVERT) ? "invert" : (mode == BLIT_XOR ? "xor" : "normal"),
                   us_per_draw,
                   fps);
    if (sret < 0 || (size_t)sret >= out_len) {
        ESP_LOGW(TAG, "icon bench JSON truncated");
    }
#else
    (void)d; (void)count; (void)size_px; (void)mode;
    if (out_json && out_len) {
        snprintf(out_json, out_len, "{\"count\":0,\"size\":0,\"mode\":\"none\",\"us_per_draw\":0,\"fps\":0}");
    }
#endif
}

void ui_scene_icon_demo(display_t *d)
{
    if (!d || !d->buf) {
        ESP_LOGW(TAG, "display buffer not provided; icon demo skipped");
        return;
    }

#if HAVE_ICONS
    render_icon_grid(d, s_icon_size_px, s_icon_mode);
#else
    ESP_LOGW(TAG, "HAVE_ICONS=0, icon demo not rendered");
    (void)d;
#endif
}
