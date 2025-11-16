#include "ui_demo.h"

#include <string.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"

#include "display_config.h"
#include "display/ssd1363.h"

#include "ui_design.h"
#include "ui_render.h"
#include "ui_render_swbuf.h"

static const char *TAG = "ui_demo";
static TaskHandle_t s_demo_task = NULL;
static struct { uint32_t frames; uint64_t bytes; int64_t us_accum; } s_perf = {0};

void ui_demo_render_once(void)
{
    /* Ensure bus/panel are at least initialized; ignore errors for demo. */
    (void)ssd1363_init_panel();

    /* Allocate a static 1bpp packed framebuffer. */
    enum { W = DISPLAY_WIDTH, H = DISPLAY_HEIGHT };
    static uint8_t fb[((W + 7) / 8) * H];
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
    (void)ssd1363_init_panel();

    enum { W = DISPLAY_WIDTH, H = DISPLAY_HEIGHT };
    static uint8_t fb[((W + 7) / 8) * H];
    UiSwBuf sw;
    ui_swbuf_init(&sw, fb, W, H);

    UiDrawOps ops;
    ui_swbuf_make_ops(&sw, &ops);

    int t = 0;
    for (;;) {
        /* Full scene render (marks dirty across all draw ops) */
        ui_swbuf_clear(&sw, 0);
        ui_render_scene(&UI_SCENE_DEMO, &ops);

        /* Tiny animated overlay to demonstrate partial updates */
        int bx = 2 + (t % 30);
        ui_swbuf_fill_rect(&sw, bx, 2, 12, 8, 1);

        /* Estimate bytes and time the flush */
        int dx, dy, dw, dh;
        size_t bytes_est = 0;
        if (ui_swbuf_get_dirty(&sw, &dx, &dy, &dw, &dh)) {
    #if DISPLAY_COLOR_BITS == 4
            int out_row_bytes = (dw + 1) / 2;
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
            double kbps = (double)s_perf.bytes * 8.0 / (ms); /* kilobits/ms -> Mbps approx */
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
