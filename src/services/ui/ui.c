#include "ui.h"

#include <string.h>

#include "esp_log.h"
#include "freertos/task.h"

#include "renderer.h"
#include "services/store/store.h"
#include "ui_core.h"

static QueueHandle_t q;
static esp_lcd_panel_handle_t gpanel;
static const char *TAG = "ui";

static void ui_task(void *arg)
{
    (void)arg;

    ui_state_t st;
    ui_core_init(&st);
    msg_t m;

    store_conf_t conf;
    if (store_get_conf(&conf) == ESP_OK) {
        ui_core_on_rpc_bg(&st, conf.bg_rgb);
    } else {
        ESP_LOGW(TAG, "store_get_conf failed; using default UI colors");
    }

    bus_subscribe(TOP_TICK_10MS, q);
    bus_subscribe(TOP_INPUT_BTN, q);
    bus_subscribe(TOP_RPC_CALL, q);
    bus_subscribe(TOP_METRICS_RET, q);

    while (1) {
        if (xQueueReceive(q, &m, portMAX_DELAY)) {
            switch (m.topic) {
                case TOP_TICK_10MS:
                    if ((m.u.tick.tick % 3U) == 0U) {
                        ui_core_on_tick(&st);
                        render_frame_striped(gpanel, &st);
                    }
                    break;
                case TOP_INPUT_BTN:
                    ui_core_on_button(&st, m.u.btn.id, m.u.btn.pressed != 0);
                    break;
                case TOP_RPC_CALL:
                    if (strcmp(m.u.rpc.method, "set_bg") == 0) {
                        ui_core_on_rpc_bg(&st, m.u.rpc.arg);
                        esp_err_t serr = store_set_bg_rgb(m.u.rpc.arg);
                        if (serr != ESP_OK) {
                            ESP_LOGE(TAG, "store_set_bg_rgb failed: %d", serr);
                        }
                    }
                    break;
                case TOP_METRICS_RET:
                    st.metrics_free_heap = m.u.metrics.free_heap;
                    st.metrics_min_free_heap = m.u.metrics.min_free_heap;
                    break;
                default:
                    break;
            }
        }
    }
}

void ui_start(esp_lcd_panel_handle_t panel)
{
    gpanel = panel;
    q = bus_make_queue(16);
    (void)xTaskCreatePinnedToCore(ui_task, "ui", 4096, NULL, 6, NULL, 1);
}
