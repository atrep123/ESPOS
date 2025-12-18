#include "ui_app.h"

#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kernel/msgbus.h"
#include "services/input/input.h"
#include "services/ui/ui.h"
#include "services/ui/ui_bindings.h"

static const char *TAG = "ui_app";

typedef enum {
    UI_APP_SCREEN_MENU = 0,
    UI_APP_SCREEN_DISPLAY_LIST = 1,
    UI_APP_SCREEN_EDIT_CONTRAST = 2,
    UI_APP_SCREEN_EDIT_INVERT = 3,
    UI_APP_SCREEN_EDIT_COL_OFFSET = 4,
} ui_app_screen_t;

static TaskHandle_t s_ui_app_task = NULL;
static ui_app_screen_t s_screen = UI_APP_SCREEN_MENU;

static void ui_app_show_menu(void)
{
    ui_cmd_set_prefix_visible("menu", true);
    ui_cmd_set_prefix_visible("list", false);
    ui_cmd_set_prefix_visible("edit", false);
    ui_cmd_set_prefix_visible("edit_contrast", false);
    ui_cmd_set_prefix_visible("edit_invert", false);
    ui_cmd_set_prefix_visible("edit_col_offset", false);

    ui_cmd_listmodel_set_len("menu", 3);
    ui_cmd_listmodel_set_item("menu", 0, "Display", "");
    ui_cmd_listmodel_set_item("menu", 1, "Inputs", "");
    ui_cmd_listmodel_set_item("menu", 2, "About", "");
    ui_cmd_listmodel_set_active("menu", 0);

    s_screen = UI_APP_SCREEN_MENU;
}

static void ui_app_build_display_list(void)
{
    int contrast = 0;
    int col_offset = 0;
    bool invert = false;
    (void)ui_bind_get_int("contrast", &contrast);
    (void)ui_bind_get_int("col_offset", &col_offset);
    (void)ui_bind_get_bool("invert", &invert);

    ui_cmd_set_prefix_visible("menu", false);
    ui_cmd_set_prefix_visible("edit", false);
    ui_cmd_set_prefix_visible("edit_contrast", false);
    ui_cmd_set_prefix_visible("edit_invert", false);
    ui_cmd_set_prefix_visible("edit_col_offset", false);
    ui_cmd_set_prefix_visible("list", true);

    ui_cmd_set_text("list.title", "Display");
    ui_cmd_listmodel_set_len("list", 12);

    char buf[16];
    snprintf(buf, sizeof(buf), "%d", contrast);
    ui_cmd_listmodel_set_item("list", 0, "Contrast", buf);
    ui_cmd_listmodel_set_item("list", 1, "Invert", invert ? "on" : "off");
    snprintf(buf, sizeof(buf), "%d", col_offset);
    ui_cmd_listmodel_set_item("list", 2, "ColOffset", buf);

    ui_cmd_listmodel_set_item("list", 3, "UI FPS", "20");
    ui_cmd_listmodel_set_item("list", 4, "Theme", "mono");
    ui_cmd_listmodel_set_item("list", 5, "Font", "6x8");
    ui_cmd_listmodel_set_item("list", 6, "Network", "todo");
    ui_cmd_listmodel_set_item("list", 7, "Bluetooth", "todo");
    ui_cmd_listmodel_set_item("list", 8, "Sensors", "todo");
    ui_cmd_listmodel_set_item("list", 9, "Storage", "todo");
    ui_cmd_listmodel_set_item("list", 10, "Debug", "todo");
    ui_cmd_listmodel_set_item("list", 11, "Reset", "todo");

    ui_cmd_listmodel_set_active("list", 0);
    s_screen = UI_APP_SCREEN_DISPLAY_LIST;
}

static void ui_app_show_edit(const char *title, const char *root)
{
    ui_cmd_set_prefix_visible("menu", false);
    ui_cmd_set_prefix_visible("list", false);

    ui_cmd_set_prefix_visible("edit", true);
    ui_cmd_set_text("edit.title", title);

    ui_cmd_set_prefix_visible("edit_contrast", false);
    ui_cmd_set_prefix_visible("edit_invert", false);
    ui_cmd_set_prefix_visible("edit_col_offset", false);
    ui_cmd_set_prefix_visible(root, true);
}

static void ui_app_handle_menu_action(uint32_t idx)
{
    switch ((int)idx) {
        case 0:
            ui_app_build_display_list();
            break;
        case 1:
            ui_cmd_toast_enqueue("toast", "Inputs: TODO", 1200);
            break;
        case 2:
            ui_cmd_toast_enqueue("toast", "ESP32OS (demo)", 1200);
            break;
        default:
            break;
    }
}

static void ui_app_handle_display_list_action(uint32_t idx)
{
    switch ((int)idx) {
        case 0:
            ui_app_show_edit("Contrast", "edit_contrast");
            s_screen = UI_APP_SCREEN_EDIT_CONTRAST;
            break;
        case 1: {
            bool cur = false;
            if (ui_bind_get_bool("invert", &cur)) {
                (void)ui_bind_set_bool("invert", !cur);
            }
            ui_app_build_display_list();
            ui_cmd_listmodel_set_active("list", 1);
            break;
        }
        case 2:
            ui_app_show_edit("ColOffset", "edit_col_offset");
            s_screen = UI_APP_SCREEN_EDIT_COL_OFFSET;
            break;
        default:
            ui_cmd_toast_enqueue("toast", "TODO", 900);
            break;
    }
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
        if (s_screen == UI_APP_SCREEN_DISPLAY_LIST) {
            ui_app_handle_display_list_action(m->u.ui_action.arg);
        }
        return;
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
    int is_back = 0;
    if (id == INPUT_ID_B || id == INPUT_ID_ENC_HOLD) {
        is_back = 1;
    }
    if (id == INPUT_ID_ENC2_HOLD || id == INPUT_ID_ENC3_HOLD || id == INPUT_ID_ENC4_HOLD || id == INPUT_ID_ENC5_HOLD) {
        is_back = 1;
    }
    if (!is_back) {
        return;
    }

    switch (s_screen) {
        case UI_APP_SCREEN_MENU:
            ui_cmd_toast_hide("toast");
            break;
        case UI_APP_SCREEN_DISPLAY_LIST:
            ui_app_show_menu();
            break;
        case UI_APP_SCREEN_EDIT_CONTRAST:
        case UI_APP_SCREEN_EDIT_INVERT:
        case UI_APP_SCREEN_EDIT_COL_OFFSET:
            ui_app_build_display_list();
            break;
        default:
            ui_app_show_menu();
            break;
    }
}

static void ui_app_task(void *arg)
{
    (void)arg;

    QueueHandle_t q = bus_make_queue(12);
    if (q != NULL) {
        bus_subscribe(TOP_UI_ACTION, q);
        bus_subscribe(TOP_INPUT_BTN, q);
    }

    vTaskDelay(pdMS_TO_TICKS(150));
    ui_app_show_menu();

    for (;;) {
        msg_t m;
        if (q == NULL) {
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }
        if (xQueueReceive(q, &m, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        if (m.topic == TOP_UI_ACTION) {
            ui_app_handle_action(&m);
        } else if (m.topic == TOP_INPUT_BTN) {
            ui_app_handle_back(&m);
        }
    }
}

void ui_app_start(void)
{
    if (s_ui_app_task != NULL) {
        return;
    }
    if (xTaskCreatePinnedToCore(ui_app_task, "ui_app", 4096, NULL, 5, &s_ui_app_task, 0) != pdPASS) {
        ESP_LOGE(TAG, "xTaskCreatePinnedToCore(ui_app) failed");
        s_ui_app_task = NULL;
    }
}

