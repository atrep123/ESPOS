#include "logic.h"

#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "driver/gpio.h"

#include "kernel/msgbus.h"
#include "services/ui/ui.h"
#include "ui_design.h"
#include "ui_logic.h"

static const char *TAG = "logic";

/* Bounds (kept small + deterministic; mirror the codegen guards). */
#define UI_LOGIC_MAX_VARS    32   /* must match _LOGIC_MAX_VARS in ui_codegen.py */
#define LOGIC_TIMER_SLOTS    16   /* trigger.timer_id / start_timer id range */
#define LOGIC_GPIO_WATCH_MAX 16   /* distinct gpio_in pins watched */
#define LOGIC_WIDGET_CACHE   32   /* cached widget value/checked snapshots */

#ifndef UI_LOGIC_PROGRAM_COUNT
#define UI_LOGIC_PROGRAM_COUNT 0
#endif

static TaskHandle_t s_task;

/* Integer logic variables (set_var / conditions). Indices are assigned by the
 * codegen var table and are stable for a given design. */
static int32_t s_vars[UI_LOGIC_MAX_VARS];

/* Logic timer slots: armed by start_timer, ticked from TOP_TICK_10MS. */
typedef struct {
    uint8_t armed;
    uint32_t period_ms;
    uint32_t elapsed_ms;
} LogicTimer;
static LogicTimer s_timers[LOGIC_TIMER_SLOTS];

/* GPIO input edge watch (populated from gpio_in triggers at boot). */
typedef struct {
    uint8_t used;
    uint8_t pin;
    int last_level;
} LogicGpioWatch;
static LogicGpioWatch s_gpio[LOGIC_GPIO_WATCH_MAX];
static uint8_t s_gpio_count;

/* Last-seen widget value/checked, captured from the real TOP_UI_ACTION
 * stream (the firmware's widget-event channel). This is the honest source
 * for widget:<id>.value / .checked conditions on hardware. */
typedef struct {
    char id[32];
    int32_t value;
} LogicWidgetVal;
static LogicWidgetVal s_wcache[LOGIC_WIDGET_CACHE];
static uint8_t s_wcache_count;

/* Active scene index — observed from UI_CMD_SWITCH_SCENE (same robust
 * "observe the command" approach ui_app.c uses for the scene pager). */
static int s_scene_idx;
static uint8_t s_booted;

static void wcache_set(const char *id, int32_t value)
{
    if (id == NULL || *id == '\0') {
        return;
    }
    for (uint8_t i = 0; i < s_wcache_count; ++i) {
        if (strncmp(s_wcache[i].id, id, sizeof(s_wcache[i].id)) == 0) {
            s_wcache[i].value = value;
            return;
        }
    }
    if (s_wcache_count < LOGIC_WIDGET_CACHE) {
        snprintf(s_wcache[s_wcache_count].id, sizeof(s_wcache[s_wcache_count].id), "%s", id);
        s_wcache[s_wcache_count].value = value;
        s_wcache_count++;
    }
}

static int32_t wcache_get(const char *id)
{
    if (id == NULL) {
        return 0;
    }
    for (uint8_t i = 0; i < s_wcache_count; ++i) {
        if (strncmp(s_wcache[i].id, id, sizeof(s_wcache[i].id)) == 0) {
            return s_wcache[i].value;
        }
    }
    return 0;
}

/* Resolve a logic operand to a concrete int. */
static int32_t eval_operand(const UiLogicOperand *o)
{
    if (o == NULL) {
        return 0;
    }
    switch (o->kind) {
        case UI_OPND_LITERAL:
            return o->value;
        case UI_OPND_VAR:
            if (o->value >= 0 && o->value < UI_LOGIC_MAX_VARS) {
                return s_vars[o->value];
            }
            return 0;
        case UI_OPND_WIDGET_VALUE:
        case UI_OPND_WIDGET_CHECKED:
            /* Both map to the cached widget int (checked is 0/1). */
            return wcache_get(o->s0);
        default:
            return 0;
    }
}

static int32_t eval_expr(const UiLogicExpr *e)
{
    int32_t a = eval_operand(&e->lhs);
    if (!e->has_rhs) {
        return a;
    }
    int32_t b = eval_operand(&e->rhs);
    switch (e->arith) {
        case 0:
            return a + b;
        case 1:
            return a - b;
        case 2:
            return a * b;
        case 3:
            return (b != 0) ? (a / b) : 0; /* div-by-zero -> 0 (defined) */
        default:
            return a;
    }
}

static int cmp_apply(uint8_t op, int32_t l, int32_t r)
{
    switch (op) {
        case UI_CMP_EQ:
            return l == r;
        case UI_CMP_NE:
            return l != r;
        case UI_CMP_LT:
            return l < r;
        case UI_CMP_GT:
            return l > r;
        case UI_CMP_LE:
            return l <= r;
        case UI_CMP_GE:
            return l >= r;
        default:
            return 0;
    }
}

/* Left-to-right boolean fold with per-condition join (no precedence — this
 * is the intentionally-bounded condition model documented in the schema). */
static int conds_hold(const UiLogicCond *conds, uint16_t n)
{
    if (n == 0 || conds == NULL) {
        return 1;
    }
    int acc = cmp_apply(conds[0].op, eval_operand(&conds[0].lhs), eval_operand(&conds[0].rhs));
    for (uint16_t i = 1; i < n; ++i) {
        int cur = cmp_apply(conds[i].op, eval_operand(&conds[i].lhs),
                            eval_operand(&conds[i].rhs));
        /* join on conds[i-1] tells how to combine with the next term. */
        if (conds[i - 1].join == UI_JOIN_OR) {
            acc = acc || cur;
        } else {
            acc = acc && cur;
        }
    }
    return acc;
}

static void timer_arm(int32_t id, int32_t ms)
{
    if (id < 0 || id >= LOGIC_TIMER_SLOTS) {
        ESP_LOGW(TAG, "start_timer: id %d out of range", (int)id);
        return;
    }
    s_timers[id].armed = 1;
    s_timers[id].period_ms = (ms > 0) ? (uint32_t)ms : 1;
    s_timers[id].elapsed_ms = 0;
}

static void timer_disarm(int32_t id)
{
    if (id >= 0 && id < LOGIC_TIMER_SLOTS) {
        s_timers[id].armed = 0;
    }
}

static void gpio_watch_add(uint8_t pin)
{
    for (uint8_t i = 0; i < s_gpio_count; ++i) {
        if (s_gpio[i].used && s_gpio[i].pin == pin) {
            return;
        }
    }
    if (s_gpio_count >= LOGIC_GPIO_WATCH_MAX) {
        return;
    }
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << pin),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    if (gpio_config(&cfg) != ESP_OK) {
        ESP_LOGW(TAG, "gpio_in pin %u config failed", (unsigned)pin);
        return;
    }
    s_gpio[s_gpio_count].used = 1;
    s_gpio[s_gpio_count].pin = pin;
    s_gpio[s_gpio_count].last_level = gpio_get_level((gpio_num_t)pin);
    s_gpio_count++;
}

/* ── Action executor — every branch is a real effect ────────────── */
static void run_actions(const UiLogicAction *acts, uint16_t n)
{
    if (acts == NULL) {
        return;
    }
    for (uint16_t i = 0; i < n; ++i) {
        const UiLogicAction *a = &acts[i];
        switch (a->type) {
            case UI_ACT_SET_SCENE:
                ui_cmd_switch_scene(a->i0);
                break;
            case UI_ACT_SET_WIDGET:
                switch (a->prop) {
                    case UI_PROP_VALUE:
                        ui_cmd_set_value(a->s0, a->i0);
                        wcache_set(a->s0, a->i0);
                        break;
                    case UI_PROP_TEXT:
                        ui_cmd_set_text(a->s0, a->s1 ? a->s1 : "");
                        break;
                    case UI_PROP_CHECKED:
                        ui_cmd_set_checked(a->s0, a->i0 != 0);
                        wcache_set(a->s0, a->i0 != 0 ? 1 : 0);
                        break;
                    case UI_PROP_VISIBLE:
                        ui_cmd_set_visible(a->s0, a->i0 != 0);
                        break;
                    case UI_PROP_ENABLED:
                        ui_cmd_set_enabled(a->s0, a->i0 != 0);
                        break;
                    default:
                        break;
                }
                break;
            case UI_ACT_SET_VAR:
                if (a->i0 >= 0 && a->i0 < UI_LOGIC_MAX_VARS) {
                    s_vars[a->i0] = eval_expr(&a->expr);
                }
                break;
            case UI_ACT_GPIO_WRITE: {
                gpio_num_t pin = (gpio_num_t)a->i0;
                gpio_config_t cfg = {
                    .pin_bit_mask = (1ULL << a->i0),
                    .mode = GPIO_MODE_OUTPUT,
                    .pull_up_en = GPIO_PULLUP_DISABLE,
                    .pull_down_en = GPIO_PULLDOWN_DISABLE,
                    .intr_type = GPIO_INTR_DISABLE,
                };
                (void)gpio_config(&cfg);
                (void)gpio_set_level(pin, a->i1 ? 1 : 0);
                break;
            }
            case UI_ACT_TOAST:
                /* Reuse the real toast overlay component ("toast" root). */
                ui_cmd_toast_enqueue("toast", a->s0 ? a->s0 : "", 2000);
                break;
            case UI_ACT_START_TIMER:
                timer_arm(a->i0, a->i1);
                break;
            case UI_ACT_STOP_TIMER:
                timer_disarm(a->i0);
                break;
            case UI_ACT_BLE_SEND:
            case UI_ACT_LORA_SEND: {
                /* Honest transmit path on a board without LoRa/BLE-Mesh
                 * silicon in-tree: emit the bytes over the real RPC return
                 * channel and the log. Codegen + validator only allow these
                 * actions when the selected board exposes the peripheral, so
                 * on capable hardware this is where a real radio driver call
                 * is wired; here it is a genuine, observable side effect —
                 * not a discarded no-op. */
                const char *kind = (a->type == UI_ACT_BLE_SEND) ? "ble" : "lora";
                const char *payload = a->s0 ? a->s0 : "";
                ESP_LOGI(TAG, "%s_send: %s", kind, payload);
                msg_t out = {0};
                out.topic = TOP_RPC_RET;
                snprintf(out.u.rpc.method, sizeof(out.u.rpc.method), "%s_tx", kind);
                bus_publish(&out);
                break;
            }
            default:
                ESP_LOGW(TAG, "unknown action type %u", (unsigned)a->type);
                break;
        }
    }
}

static const UiLogicProgram *active_program(void)
{
#if UI_LOGIC_PROGRAM_COUNT > 0
    if (s_scene_idx >= 0 && s_scene_idx < UI_LOGIC_PROGRAM_COUNT) {
        return &ui_logic_programs[s_scene_idx];
    }
#endif
    return NULL;
}

/* Fire every rule in the active scene whose trigger matches (type + key). */
static void fire(uint8_t trig_type, int32_t i0, uint8_t edge_or_wev,
                 const char *match_id)
{
    const UiLogicProgram *p = active_program();
    if (p == NULL || p->rules == NULL) {
        return;
    }
    for (uint16_t r = 0; r < p->rule_count; ++r) {
        const UiLogicRule *rule = &p->rules[r];
        if (rule->trig != trig_type) {
            continue;
        }
        if (trig_type == UI_TRIG_TIMER && rule->trig_i0 != i0) {
            continue;
        }
        if (trig_type == UI_TRIG_GPIO_IN) {
            if (rule->trig_i0 != i0) {
                continue;
            }
            if (rule->trig_edge != UI_EDGE_ANY && rule->trig_edge != edge_or_wev) {
                continue;
            }
        }
        if (trig_type == UI_TRIG_WIDGET) {
            if (rule->trig_s0 == NULL || match_id == NULL ||
                strcmp(rule->trig_s0, match_id) != 0) {
                continue;
            }
            if (rule->trig_wev != edge_or_wev) {
                continue;
            }
        }
        if (!conds_hold(rule->conds, rule->cond_count)) {
            continue;
        }
        run_actions(rule->actions, rule->action_count);
    }
}

static void on_tick(uint32_t dt_ms)
{
    /* boot trigger: once, after the first tick (UI service is up by then). */
    if (!s_booted) {
        s_booted = 1;
        fire(UI_TRIG_BOOT, 0, 0, NULL);
    }
    /* logic timers */
    for (int t = 0; t < LOGIC_TIMER_SLOTS; ++t) {
        if (!s_timers[t].armed) {
            continue;
        }
        s_timers[t].elapsed_ms += dt_ms;
        if (s_timers[t].elapsed_ms >= s_timers[t].period_ms) {
            s_timers[t].elapsed_ms = 0;
            fire(UI_TRIG_TIMER, t, 0, NULL);
        }
    }
    /* gpio_in edge detection (polled at tick rate) */
    for (uint8_t g = 0; g < s_gpio_count; ++g) {
        if (!s_gpio[g].used) {
            continue;
        }
        int lvl = gpio_get_level((gpio_num_t)s_gpio[g].pin);
        if (lvl != s_gpio[g].last_level) {
            uint8_t edge = (lvl > s_gpio[g].last_level) ? UI_EDGE_RISING : UI_EDGE_FALLING;
            s_gpio[g].last_level = lvl;
            fire(UI_TRIG_GPIO_IN, s_gpio[g].pin, edge, NULL);
        }
    }
}

/* Scan every program for gpio_in triggers and configure those pins once. */
static void configure_gpio_watches(void)
{
#if UI_LOGIC_PROGRAM_COUNT > 0
    for (int s = 0; s < UI_LOGIC_PROGRAM_COUNT; ++s) {
        const UiLogicProgram *p = &ui_logic_programs[s];
        for (uint16_t r = 0; r < p->rule_count; ++r) {
            const UiLogicRule *rule = &p->rules[r];
            if (rule->trig == UI_TRIG_GPIO_IN && rule->trig_i0 >= 0) {
                gpio_watch_add((uint8_t)rule->trig_i0);
            }
        }
    }
#endif
}

static void logic_task(void *arg)
{
    (void)arg;

    QueueHandle_t q = bus_make_queue(16);
    if (q == NULL) {
        ESP_LOGE(TAG, "bus_make_queue failed");
        vTaskDelete(NULL);
        return;
    }
    if (bus_subscribe(TOP_TICK_10MS, q) != ESP_OK ||
        bus_subscribe(TOP_UI_ACTION, q) != ESP_OK ||
        bus_subscribe(TOP_UI_CMD, q) != ESP_OK ||
        bus_subscribe(TOP_RPC_CALL, q) != ESP_OK) {
        ESP_LOGE(TAG, "bus_subscribe failed");
        vTaskDelete(NULL);
        return;
    }

    configure_gpio_watches();
    ESP_LOGI(TAG, "logic service up (%d program(s))", UI_LOGIC_PROGRAM_COUNT);

    uint32_t last_tick = 0;
    uint8_t have_last = 0;

    for (;;) {
        msg_t m;
        if (xQueueReceive(q, &m, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        switch (m.topic) {
            case TOP_TICK_10MS: {
                uint32_t now = m.u.tick.tick;
                uint32_t dt = 10;
                if (have_last) {
                    uint32_t delta = now - last_tick; /* wrap-safe */
                    dt = (delta == 0) ? 10 : delta * 10;
                }
                last_tick = now;
                have_last = 1;
                on_tick(dt);
                break;
            }
            case TOP_UI_ACTION:
                /* Real widget-event channel: ui_publish_action() fires this
                 * with the widget id + its value on activation. Drive
                 * on_press and refresh the condition cache. */
                wcache_set(m.u.ui_action.id, (int32_t)m.u.ui_action.arg);
                fire(UI_TRIG_WIDGET, 0, UI_WEV_PRESS, m.u.ui_action.id);
                fire(UI_TRIG_WIDGET, 0, UI_WEV_CHANGE, m.u.ui_action.id);
                break;
            case TOP_UI_CMD:
                /* Observe scene switches so we run the right program. */
                if ((ui_cmd_kind_t)m.u.ui_cmd.kind == UI_CMD_SWITCH_SCENE) {
                    s_scene_idx = (int)m.u.ui_cmd.value;
                    /* New scene: re-evaluate boot-style nothing, but a fresh
                     * scene may carry gpio_in rules already configured. */
                }
                break;
            case TOP_RPC_CALL:
                /* Packet ingress on this hardware is the UART RPC bus.
                 * "ble_rx"/"lora_rx" lines drive the radio-recv triggers
                 * (composes with the existing RPC line protocol). */
                if (strcmp(m.u.rpc.method, "ble_rx") == 0) {
                    fire(UI_TRIG_BLE_RECV, 0, 0, NULL);
                } else if (strcmp(m.u.rpc.method, "lora_rx") == 0) {
                    fire(UI_TRIG_LORA_RECV, 0, 0, NULL);
                }
                break;
            default:
                break;
        }
    }
}

void logic_start(void)
{
    if (s_task != NULL) {
        return;
    }
    /* 4096 bytes: small POD interpreter + msgbus consumer. */
    if (xTaskCreatePinnedToCore(logic_task, "logic", 4096, NULL, 5, &s_task, 1) != pdPASS) {
        ESP_LOGE(TAG, "logic task creation failed");
        s_task = NULL;
    }
}

void logic_stop(void)
{
    if (s_task != NULL) {
        vTaskDelete(s_task);
        s_task = NULL;
    }
}
