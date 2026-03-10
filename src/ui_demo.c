#include "ui_demo.h"

#include <string.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"

#include "display_config.h"
#include "display/ssd1363.h"
#include "input_config.h"
#include "kernel/msgbus.h"
#include "services/input/input.h"
#include "ui_nav.h"

#include "ui_design.h"
#include "ui_render.h"
#include "ui_render_swbuf.h"

static const char *TAG = "ui_demo";
static TaskHandle_t s_demo_task = NULL;
static struct { uint32_t frames; uint64_t bytes; int64_t us_accum; } s_perf = {0};

static int ui_demo_has_direct_nav(void)
{
#if (INPUT_PIN_UP >= 0) || (INPUT_PIN_DOWN >= 0) || (INPUT_PIN_LEFT >= 0) || (INPUT_PIN_RIGHT >= 0)
    return 1;
#elif (INPUT_PIN_ENC_A >= 0) && (INPUT_PIN_ENC_B >= 0)
    return 1;
#else
    return 0;
#endif
}

static void ui_demo_draw_focus(UiDrawOps *ops, const UiScene *scene, int idx)
{
    if (!ops || !ops->draw_rect || !scene || !scene->widgets) {
        return;
    }
    if (idx < 0 || (uint16_t)idx >= scene->widget_count) {
        return;
    }
    const UiWidget *w = &scene->widgets[(uint16_t)idx];
    if (!ui_nav_is_focusable(w)) {
        return;
    }
    int x = (int)w->x;
    int y = (int)w->y;
    int ww = (int)w->width;
    int hh = (int)w->height;
    if (ww <= 0 || hh <= 0) {
        return;
    }
#if DISPLAY_COLOR_BITS == 4
    uint8_t outer = 15;
    uint8_t inner = 8;
#else
    uint8_t outer = 1;
    uint8_t inner = 1;
#endif
    ops->draw_rect(ops->ctx, x, y, ww, hh, outer);
    if (ww > 2 && hh > 2) {
        ops->draw_rect(ops->ctx, x + 1, y + 1, ww - 2, hh - 2, inner);
    }
}

void ui_demo_render_once(void)
{
    /* Ensure bus/panel are at least initialized. */
    esp_err_t err = ssd1363_init_panel();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ssd1363_init_panel failed: %s", esp_err_to_name(err));
        return;
    }

    /* Allocate a static framebuffer (layout depends on DISPLAY_COLOR_BITS). */
    enum { W = DISPLAY_WIDTH, H = DISPLAY_HEIGHT };
    static uint8_t fb[UI_SWBUF_BYTES(W, H)];
    UiSwBuf sw;
    ui_swbuf_init(&sw, fb, W, H);
    ui_swbuf_clear(&sw, 0);

    /* Build draw ops and render the exported demo scene. */
    UiDrawOps ops;
    ui_swbuf_make_ops(&sw, &ops);

    /* If the exported scene size is smaller than display, it's okay; we draw at (0,0). */
    ui_render_scene(&UI_SCENE_DEMO, &ops);

    /* Flush the framebuffer to SSD1363 (full-frame for first draw). */
    ESP_LOGI(TAG, "Flushing demo scene to panel (%dx%d)", W, H);
    ui_swbuf_flush_auto_ssd1363(&sw);

    /* Example: draw a small dirty update and flush only that region. */
    ui_swbuf_fill_rect(&sw, 2, 2, 20, 10, 1);
    ui_swbuf_flush_dirty_auto_ssd1363(&sw);
    ui_swbuf_clear_dirty(&sw);
}

static void ui_demo_task(void *arg)
{
    esp_err_t err = ssd1363_init_panel();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ssd1363_init_panel failed: %s", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }

    enum { W = DISPLAY_WIDTH, H = DISPLAY_HEIGHT };
    static uint8_t fb[UI_SWBUF_BYTES(W, H)];
    UiSwBuf sw;
    ui_swbuf_init(&sw, fb, W, H);

    UiDrawOps ops;
    ui_swbuf_make_ops(&sw, &ops);

    QueueHandle_t q = bus_make_queue(8);
    if (q) {
        bus_subscribe(TOP_INPUT_BTN, q);
    }

    int t = 0;
    int focus = ui_nav_first_focus(&UI_SCENE_DEMO);
    int flash = 0;
    int direct_nav = ui_demo_has_direct_nav();
    for (;;) {
        /* Drain input events (best effort, non-blocking). */
        msg_t m;
        while (q && xQueueReceive(q, &m, 0) == pdTRUE) {
            if (m.topic != TOP_INPUT_BTN) {
                continue;
            }
            if (!m.u.btn.pressed) {
                continue; /* react only on press */
            }
            switch (m.u.btn.id) {
                case INPUT_ID_UP:
                    direct_nav = 1;
                    focus = ui_nav_move_focus(&UI_SCENE_DEMO, focus, UI_NAV_UP);
                    break;
                case INPUT_ID_DOWN:
                    direct_nav = 1;
                    focus = ui_nav_move_focus(&UI_SCENE_DEMO, focus, UI_NAV_DOWN);
                    break;
                case INPUT_ID_LEFT:
                    direct_nav = 1;
                    focus = ui_nav_move_focus(&UI_SCENE_DEMO, focus, UI_NAV_LEFT);
                    break;
                case INPUT_ID_RIGHT:
                    direct_nav = 1;
                    focus = ui_nav_move_focus(&UI_SCENE_DEMO, focus, UI_NAV_RIGHT);
                    break;
                case INPUT_ID_ENC_CCW:
                case INPUT_ID_ENC2_CCW:
                case INPUT_ID_ENC3_CCW:
                case INPUT_ID_ENC4_CCW:
                case INPUT_ID_ENC5_CCW:
                    direct_nav = 1;
                    focus = ui_nav_move_focus(&UI_SCENE_DEMO, focus, UI_NAV_UP);
                    break;
                case INPUT_ID_ENC_CW:
                case INPUT_ID_ENC2_CW:
                case INPUT_ID_ENC3_CW:
                case INPUT_ID_ENC4_CW:
                case INPUT_ID_ENC5_CW:
                    direct_nav = 1;
                    focus = ui_nav_move_focus(&UI_SCENE_DEMO, focus, UI_NAV_DOWN);
                    break;
                case INPUT_ID_A:
                case INPUT_ID_ENC_PRESS:
                case INPUT_ID_ENC2_PRESS:
                case INPUT_ID_ENC3_PRESS:
                case INPUT_ID_ENC4_PRESS:
                case INPUT_ID_ENC5_PRESS:
                    if (direct_nav) {
                        flash = 6;
                    } else {
                        focus = ui_nav_cycle_focus(&UI_SCENE_DEMO, focus, 1);
                    }
                    break;
                case INPUT_ID_B:
                case INPUT_ID_ENC_HOLD:
                case INPUT_ID_ENC2_HOLD:
                case INPUT_ID_ENC3_HOLD:
                case INPUT_ID_ENC4_HOLD:
                case INPUT_ID_ENC5_HOLD:
                    if (direct_nav) {
                        flash = 0;
                    } else {
                        focus = ui_nav_cycle_focus(&UI_SCENE_DEMO, focus, -1);
                    }
                    break;
                case 2: /* C: reserved */
                default:
                    break;
            }
        }

        /* Full scene render (marks dirty across all draw ops) */
        ui_swbuf_clear(&sw, 0);
        ui_render_scene(&UI_SCENE_DEMO, &ops);

        /* Tiny animated overlay to demonstrate partial updates */
        int bx = 2 + (t % 30);
        ui_swbuf_fill_rect(&sw, bx, 2, 12, 8, 1);

        /* Focus highlight overlay. */
        if (flash > 0) {
#if DISPLAY_COLOR_BITS == 4
            ui_swbuf_fill_rect(&sw, 0, 0, 6, 6, 4);
#else
            ui_swbuf_fill_rect(&sw, 0, 0, 6, 6, 1);
#endif
            flash -= 1;
        }
        ui_demo_draw_focus(&ops, &UI_SCENE_DEMO, focus);

        /* Estimate bytes and time the flush */
        int dx, dy, dw, dh;
        size_t bytes_est = 0;
        if (ui_swbuf_get_dirty(&sw, &dx, &dy, &dw, &dh)) {
    #if DISPLAY_COLOR_BITS == 4
            int ax0 = dx & ~3;
            int ax1 = (dx + dw - 1) | 3;
            if (ax0 < 0) ax0 = 0;
            if (ax1 >= DISPLAY_WIDTH) ax1 = DISPLAY_WIDTH - 1;
            int w_aligned = (ax1 >= ax0) ? (ax1 - ax0 + 1) : 0;
            int out_row_bytes = (w_aligned + 1) / 2;
            bytes_est = (size_t)out_row_bytes * (size_t)dh;
    #else
            size_t start_byte = (size_t)(dx >> 3);
            size_t end_byte = (size_t)((dx + dw + 7) >> 3);
            size_t bytes_per_row = end_byte - start_byte;
            bytes_est = bytes_per_row * (size_t)dh;
    #endif
        } else {
    #if DISPLAY_COLOR_BITS == 4
            bytes_est = (size_t)((DISPLAY_WIDTH + 1) / 2) * (size_t)DISPLAY_HEIGHT;
    #else
            bytes_est = (size_t)(((DISPLAY_WIDTH + 7) / 8) * DISPLAY_HEIGHT);
    #endif
        }
        int64_t t0 = esp_timer_get_time();
        ui_swbuf_flush_dirty_auto_ssd1363(&sw);
        int64_t t1 = esp_timer_get_time();
        int64_t dt_us = t1 - t0;
        s_perf.frames += 1;
        s_perf.bytes  += bytes_est;
        s_perf.us_accum += dt_us;
        if (s_perf.frames % 20 == 0) {
            double ms = (double)s_perf.us_accum / 1000.0;
            double fps = 1000.0 * (double)s_perf.frames / ms;
            ESP_LOGI(TAG, "Perf: %u frames, %.2f fps, %.2f MB/s, avg %.2f ms/flush",
                     (unsigned)s_perf.frames,
                     fps,
                     (double)s_perf.bytes / (ms * 1000.0),
                     ms / (double)s_perf.frames);
            s_perf.frames = 0; s_perf.bytes = 0; s_perf.us_accum = 0;
        }
        ui_swbuf_clear_dirty(&sw);

        t = (t + 1) % 1000;
        vTaskDelay(pdMS_TO_TICKS(50)); /* ~20 FPS */
    }
}

void ui_demo_start(void)
{
    if (s_demo_task != NULL) {
        return;
    }
    xTaskCreate(ui_demo_task, "ui_demo", 4096, NULL, 5, &s_demo_task);
}
