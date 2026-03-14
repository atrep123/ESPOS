#include "ui_app.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include "display_config.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kernel/msgbus.h"
#include "services/input/input.h"
#include "services/store/store.h"
#include "services/ui/ui.h"
#include "services/ui/ui_bindings.h"
#include "ui_design.h"

static const char *TAG = "ui_app";

typedef enum {
    UI_APP_SCREEN_MENU = 0,
    UI_APP_SCREEN_DISPLAY_LIST = 1,
    UI_APP_SCREEN_INPUTS_LIST = 2,
    UI_APP_SCREEN_ABOUT_LIST = 3,
    UI_APP_SCREEN_EDIT_CONTRAST = 4,
    UI_APP_SCREEN_EDIT_COL_OFFSET = 5,
} ui_app_screen_t;

static TaskHandle_t s_ui_app_task = NULL;
static ui_app_screen_t s_screen = UI_APP_SCREEN_MENU;
static uint32_t s_last_free_heap = 0;
static uint32_t s_last_min_free_heap = 0;
static bool s_have_metrics = false;
static uint8_t s_last_input_id = 0;
static uint8_t s_last_input_pressed = 0;
static bool s_have_input = false;

#ifdef UI_SCENE_COUNT
static int s_scene_index = 0;
#endif

static void ui_app_hide_all_roots(void)
{
    ui_cmd_set_prefix_visible("menu", false);
    ui_cmd_set_prefix_visible("list", false);
    ui_cmd_set_prefix_visible("edit", false);
    ui_cmd_set_prefix_visible("edit_contrast", false);
    ui_cmd_set_prefix_visible("edit_invert", false);
    ui_cmd_set_prefix_visible("edit_col_offset", false);
}

static void ui_app_show_list_root(const char *title)
{
    ui_app_hide_all_roots();
    ui_cmd_set_prefix_visible("list", true);
    ui_cmd_set_text("list.title", title);
}

/* ui_app_format_heap, ui_app_input_name, ui_app_input_state,
 * and ui_app_is_back_button live in ui_app_logic.c (testable
 * without FreeRTOS). Declared in ui_app.h. */

static void ui_app_update_display_list_items(void)
{
    int contrast = 0;
    int col_offset = 0;
    bool invert = false;
    char buf[24];

    if (ui_bind_get_int("contrast", &contrast)) {
        snprintf(buf, sizeof(buf), "%d", contrast);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 0, "Contrast", buf);

    if (ui_bind_get_bool("invert", &invert)) {
        ui_cmd_listmodel_set_item("list", 1, "Invert", invert ? "on" : "off");
    } else {
        ui_cmd_listmodel_set_item("list", 1, "Invert", "n/a");
    }

    if (ui_bind_get_int("col_offset", &col_offset)) {
        snprintf(buf, sizeof(buf), "%d", col_offset);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 2, "ColOffset", buf);

    ui_cmd_listmodel_set_item("list", 3, "Driver", "SSD1363");

    snprintf(buf, sizeof(buf), "%ux%u", (unsigned)DISPLAY_WIDTH, (unsigned)DISPLAY_HEIGHT);
    ui_cmd_listmodel_set_item("list", 4, "Display", buf);

#if DISPLAY_COLOR_BITS == 4
    ui_cmd_listmodel_set_item("list", 5, "Format", "gray4");
#else
    snprintf(buf, sizeof(buf), "%ubpp", (unsigned)DISPLAY_COLOR_BITS);
    ui_cmd_listmodel_set_item("list", 5, "Format", buf);
#endif

    if (s_have_metrics) {
        ui_app_format_heap(buf, sizeof(buf), s_last_free_heap);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 6, "Heap", buf);

    if (s_have_metrics) {
        ui_app_format_heap(buf, sizeof(buf), s_last_min_free_heap);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 7, "MinHeap", buf);

    ui_cmd_listmodel_set_item("list", 8, "Persist", "NVS");
    ui_cmd_listmodel_set_item("list", 9, "Reset", "defaults");
}

static void ui_app_update_inputs_list_items(void)
{
    ui_cmd_listmodel_set_item("list", 0, "Last", s_have_input ? ui_app_input_name(s_last_input_id) : "n/a");
    ui_cmd_listmodel_set_item("list", 1, "State", s_have_input ? ui_app_input_state(s_last_input_id, s_last_input_pressed) : "n/a");
    ui_cmd_listmodel_set_item("list", 2, "D-pad", "navigate");
    ui_cmd_listmodel_set_item("list", 3, "A / press", "select");
    ui_cmd_listmodel_set_item("list", 4, "B / hold", "back");
    ui_cmd_listmodel_set_item("list", 5, "Encoder", "scroll");
    ui_cmd_listmodel_set_item("list", 6, "Extras", "X Y Start");
}

static void ui_app_update_about_list_items(void)
{
    store_conf_t conf;
    char buf[24];

    ui_cmd_listmodel_set_item("list", 0, "Project", "ESP32OS");
    ui_cmd_listmodel_set_item("list", 1, "Driver", "SSD1363");

    snprintf(buf, sizeof(buf), "%ux%u", (unsigned)DISPLAY_WIDTH, (unsigned)DISPLAY_HEIGHT);
    ui_cmd_listmodel_set_item("list", 2, "Display", buf);

#if DISPLAY_COLOR_BITS == 4
    ui_cmd_listmodel_set_item("list", 3, "Format", "gray4");
#else
    snprintf(buf, sizeof(buf), "%ubpp", (unsigned)DISPLAY_COLOR_BITS);
    ui_cmd_listmodel_set_item("list", 3, "Format", buf);
#endif

    ui_cmd_listmodel_set_item("list", 4, "Storage", "NVS");
    ui_cmd_listmodel_set_item("list", 5, "Bindings", "runtime");

    if (store_get_conf(&conf) == ESP_OK) {
        snprintf(buf, sizeof(buf), "%" PRIu32, conf.schema);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 6, "Schema", buf);

    if (s_have_metrics) {
        ui_app_format_heap(buf, sizeof(buf), s_last_free_heap);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 7, "Heap", buf);

    if (s_have_metrics) {
        ui_app_format_heap(buf, sizeof(buf), s_last_min_free_heap);
    } else {
        snprintf(buf, sizeof(buf), "n/a");
    }
    ui_cmd_listmodel_set_item("list", 8, "MinHeap", buf);
}

static void ui_app_show_display_list(int active_idx)
{
    if (active_idx < 0) {
        active_idx = 0;
    }

    ui_app_show_list_root("Display");
    ui_cmd_listmodel_set_len("list", 10);
    ui_app_update_display_list_items();
    ui_cmd_listmodel_set_active("list", active_idx);
    s_screen = UI_APP_SCREEN_DISPLAY_LIST;
}

static void ui_app_show_inputs_list(int active_idx)
{
    if (active_idx < 0) {
        active_idx = 0;
    }

    ui_app_show_list_root("Inputs");
    ui_cmd_listmodel_set_len("list", 7);
    ui_app_update_inputs_list_items();
    ui_cmd_listmodel_set_active("list", active_idx);
    s_screen = UI_APP_SCREEN_INPUTS_LIST;
}

static void ui_app_show_about_list(int active_idx)
{
    if (active_idx < 0) {
        active_idx = 0;
    }

    ui_app_show_list_root("About");
    ui_cmd_listmodel_set_len("list", 9);
    ui_app_update_about_list_items();
    ui_cmd_listmodel_set_active("list", active_idx);
    s_screen = UI_APP_SCREEN_ABOUT_LIST;
}

static void ui_app_show_menu(void)
{
    ui_app_hide_all_roots();
    ui_cmd_set_prefix_visible("menu", true);

    ui_cmd_listmodel_set_len("menu", 3);
    ui_cmd_listmodel_set_item("menu", 0, "Display", "");
    ui_cmd_listmodel_set_item("menu", 1, "Inputs", "");
    ui_cmd_listmodel_set_item("menu", 2, "About", "");
    ui_cmd_listmodel_set_active("menu", 0);

    s_screen = UI_APP_SCREEN_MENU;
}

static void ui_app_show_edit(const char *title, const char *root, const char *hint)
{
    ui_app_hide_all_roots();
    ui_cmd_set_prefix_visible("edit", true);
    ui_cmd_set_text("edit.title", title);
    ui_cmd_set_text("edit.hint", (hint != NULL) ? hint : "");

    ui_cmd_set_prefix_visible(root, true);
}

static void ui_app_reset_display_defaults(void)
{
    esp_err_t err;
    err = ui_bind_set_int("contrast", SSD1363_INIT_CONTRAST);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "bind_set_int(contrast) failed: %s", esp_err_to_name(err));
    }
    err = ui_bind_set_bool("invert", false);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "bind_set_bool(invert) failed: %s", esp_err_to_name(err));
    }
    err = ui_bind_set_int("col_offset", SSD1363_COL_OFFSET);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "bind_set_int(col_offset) failed: %s", esp_err_to_name(err));
    }
}

static void ui_app_handle_menu_action(uint32_t idx)
{
    switch ((int)idx) {
        case 0:
            ui_app_show_display_list(0);
            break;
        case 1:
            ui_app_show_inputs_list(0);
            break;
        case 2:
            ui_app_show_about_list(0);
            break;
        default:
            break;
    }
}

static void ui_app_handle_display_list_action(uint32_t idx)
{
    switch ((int)idx) {
        case 0:
            ui_app_show_edit("Contrast", "edit_contrast", "Up/Down or encoder to adjust");
            s_screen = UI_APP_SCREEN_EDIT_CONTRAST;
            break;
        case 1: {
            bool cur = false;
            if (ui_bind_get_bool("invert", &cur)) {
                (void)ui_bind_set_bool("invert", !cur);
            }
            ui_app_update_display_list_items();
            ui_cmd_listmodel_set_active("list", 1);
            break;
        }
        case 2:
            ui_app_show_edit("ColOffset", "edit_col_offset", "Up/Down or encoder to adjust");
            s_screen = UI_APP_SCREEN_EDIT_COL_OFFSET;
            break;
        case 9:
            ui_app_reset_display_defaults();
            ui_app_show_display_list(9);
            ui_cmd_toast_enqueue("toast", "Display defaults restored", 1200);
            break;
        default:
            ui_cmd_toast_enqueue("toast", "Info only", 900);
            break;
    }
}

static void ui_app_handle_info_list_action(void)
{
    ui_cmd_toast_enqueue("toast", "Read-only", 900);
}

static void ui_app_handle_action(const msg_t *m)
{
    if (m == NULL) {
        return;
    }
    const char *id = m->u.ui_action.id;
    if (id == NULL || *id == '\0') {
        return;
    }

    if (strncmp(id, "menu.item", 9) == 0) {
        if (s_screen == UI_APP_SCREEN_MENU) {
            ui_app_handle_menu_action(m->u.ui_action.arg);
        }
        return;
    }

    if (strncmp(id, "list.item", 9) == 0) {
        switch (s_screen) {
            case UI_APP_SCREEN_DISPLAY_LIST:
                ui_app_handle_display_list_action(m->u.ui_action.arg);
                break;
            case UI_APP_SCREEN_INPUTS_LIST:
            case UI_APP_SCREEN_ABOUT_LIST:
                ui_app_handle_info_list_action();
                break;
            default:
                break;
        }
        return;
    }
}

static void ui_app_handle_metrics(const msg_t *m)
{
    if (m == NULL) {
        return;
    }

    /* Refresh live system info when a metrics sample arrives. */
    s_last_free_heap = m->u.metrics.free_heap;
    s_last_min_free_heap = m->u.metrics.min_free_heap;
    s_have_metrics = true;

    if (s_screen == UI_APP_SCREEN_DISPLAY_LIST) {
        ui_app_update_display_list_items();
    } else if (s_screen == UI_APP_SCREEN_ABOUT_LIST) {
        ui_app_update_about_list_items();
    }
}

static void ui_app_handle_input_telemetry(const msg_t *m)
{
    if (m == NULL) {
        return;
    }

    /* Mirror the most recent input event into the read-only Inputs screen. */
    s_last_input_id = m->u.btn.id;
    s_last_input_pressed = m->u.btn.pressed;
    s_have_input = true;

    if (s_screen == UI_APP_SCREEN_INPUTS_LIST) {
        ui_app_update_inputs_list_items();
    }
}

static void ui_app_handle_back(const msg_t *m)
{
    if (m == NULL) {
        return;
    }
    if (!m->u.btn.pressed) {
        return;
    }

    uint8_t id = m->u.btn.id;
    if (!ui_app_is_back_button(id)) {
        return;
    }

    switch (s_screen) {
        case UI_APP_SCREEN_MENU:
            ui_cmd_toast_hide("toast");
            break;
        case UI_APP_SCREEN_DISPLAY_LIST:
        case UI_APP_SCREEN_INPUTS_LIST:
        case UI_APP_SCREEN_ABOUT_LIST:
            ui_app_show_menu();
            break;
        case UI_APP_SCREEN_EDIT_CONTRAST:
            ui_app_show_display_list(0);
            break;
        case UI_APP_SCREEN_EDIT_COL_OFFSET:
            ui_app_show_display_list(2);
            break;
        default:
            ui_app_show_menu();
            break;
    }
}

#ifdef UI_SCENE_COUNT
static void ui_app_handle_scene_cycle(const msg_t *m)
{
    if (m == NULL || !m->u.btn.pressed) {
        return;
    }
    if (m->u.btn.id != INPUT_ID_C) {
        return;
    }
    int next = (s_scene_index + 1) % UI_SCENE_COUNT;
    s_scene_index = next;
    ui_cmd_switch_scene(next);
    ESP_LOGI(TAG, "scene cycle -> %d", next);

    /* Reset app screen to menu when returning to scene 0. */
    if (next == 0) {
        s_screen = UI_APP_SCREEN_MENU;
    }
}
#endif

static void ui_app_task(void *arg)
{
    (void)arg;

    QueueHandle_t q = bus_make_queue(12);
    if (q == NULL) {
        ESP_LOGE(TAG, "bus_make_queue failed");
        vTaskDelete(NULL);
        return;
    }
    if (bus_subscribe(TOP_UI_ACTION, q) != ESP_OK ||
        bus_subscribe(TOP_INPUT_BTN, q) != ESP_OK ||
        /* The app layer updates list content from runtime telemetry. */
        bus_subscribe(TOP_METRICS_RET, q) != ESP_OK) {
        ESP_LOGE(TAG, "bus_subscribe failed");
        vTaskDelete(NULL);
        return;
    }

    vTaskDelay(pdMS_TO_TICKS(150));
    ui_app_show_menu();

    for (;;) {
        msg_t m;
        if (xQueueReceive(q, &m, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        if (m.topic == TOP_UI_ACTION) {
            ui_app_handle_action(&m);
        } else if (m.topic == TOP_METRICS_RET) {
            ui_app_handle_metrics(&m);
        } else if (m.topic == TOP_INPUT_BTN) {
            ui_app_handle_input_telemetry(&m);
#ifdef UI_SCENE_COUNT
            ui_app_handle_scene_cycle(&m);
#endif
            ui_app_handle_back(&m);
        }
    }
}

void ui_app_start(void)
{
    if (s_ui_app_task != NULL) {
        return;
    }
    /* 4096 bytes: app-level UI logic, binding updates, snprintf formatting */
    if (xTaskCreatePinnedToCore(ui_app_task, "ui_app", 4096, NULL, 5, &s_ui_app_task, 0) != pdPASS) {
        ESP_LOGE(TAG, "xTaskCreatePinnedToCore(ui_app) failed");
        s_ui_app_task = NULL;
    }
}

void ui_app_stop(void)
{
    if (s_ui_app_task != NULL) {
        vTaskDelete(s_ui_app_task);
        s_ui_app_task = NULL;
    }
}

