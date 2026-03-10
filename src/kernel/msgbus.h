#pragma once

#include <stdint.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

typedef enum {
    TOP_TICK_10MS = 1,
    TOP_INPUT_BTN,
    TOP_RPC_CALL,
    TOP_RPC_RET,
    TOP_METRICS_REQ,
    TOP_METRICS_RET,
    TOP_UI_ACTION,
    TOP_UI_CMD,
} topic_t;

typedef enum {
    UI_CMD_SET_TEXT = 1,
    UI_CMD_SET_VISIBLE = 2,
    UI_CMD_SET_ENABLED = 3,
    UI_CMD_SET_STYLE = 4,
    UI_CMD_SET_VALUE = 5,
    UI_CMD_SET_CHECKED = 6,
    UI_CMD_SET_PREFIX_VISIBLE = 7,

    UI_CMD_MENU_SET_ACTIVE = 16,
    UI_CMD_LIST_SET_ACTIVE = 17,
    UI_CMD_TABS_SET_ACTIVE = 18,

    /* Virtualized scrolling list/menu model (absolute index + viewport). */
    UI_CMD_LISTMODEL_SET_LEN = 20,
    UI_CMD_LISTMODEL_SET_ITEM = 21,
    UI_CMD_LISTMODEL_SET_ACTIVE = 22,

    UI_CMD_DIALOG_SHOW = 32,
    UI_CMD_DIALOG_HIDE = 33,

    UI_CMD_TOAST_ENQUEUE = 48,
    UI_CMD_TOAST_HIDE = 49,

    UI_CMD_SWITCH_SCENE = 64,
} ui_cmd_kind_t;

typedef struct {
    topic_t topic;
    union {
        struct {
            uint32_t tick;
        } tick;
        struct {
            uint8_t id;
            uint8_t pressed;
        } btn;
        struct {
            char method[16];
            uint32_t arg;
        } rpc;
        struct {
            uint32_t free_heap;
            uint32_t min_free_heap;
        } metrics;
        struct {
            char id[32];
            uint32_t arg;
        } ui_action;
        struct {
            uint8_t kind; /* ui_cmd_kind_t */
            char id[32];  /* widget id or component root */
            char text[64];
            int32_t value;
        } ui_cmd;
    } u;
} msg_t;

void bus_init(void);
QueueHandle_t bus_make_queue(size_t depth);
void bus_subscribe(topic_t t, QueueHandle_t q);
void bus_publish(const msg_t *m);
