/* Include the unchanged production task to retain its private state machine. */
#include <setjmp.h>
#include <stdlib.h>
#include <string.h>
#include "services/ui/ui.c"

/* Mirror the Python ingress contract before starting any task or writing a frame. */
#define SIM_MAX_EVENTS 256
#define SIM_MAX_STEP_TICKS 1000
#define SIM_MAX_ADVANCE_TICKS 6000
/* Stable simulator wire codes, shared with initial CLI/Python configuration.
 * Host unit-test esp_err aliases are not the display transport protocol. */
#define SIM_DISPLAY_CONNECTED 0
#define SIM_DISPLAY_DISCONNECTED 0x105
#define SIM_DISPLAY_ERROR (-1)
typedef struct {
    msg_t message;
    unsigned advance_ticks;
    int tick_only;
    int display_change;
    int display_status;
} SimStep;
static SimStep steps[SIM_MAX_EVENTS];
static int event_count;

static int sim_decimal(const char *text, size_t length, unsigned maximum, unsigned *value)
{
    unsigned number = 0;
    if (!length || length > 9) return 0;
    for (size_t i = 0; i < length; i++) {
        if (text[i] < '0' || text[i] > '9') return 0;
        number = number * 10 + (unsigned)(text[i] - '0');
    }
    if (number > maximum) return 0;
    *value = number;
    return 1;
}

#ifdef SIM_APP
static int sim_identifier(const char *text, size_t length)
{
    if (!length || length > 31) return 0;
    for (size_t i = 0; i < length; i++) {
        char c = text[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '-')) return 0;
    }
    return 1;
}
#endif

static int sim_parse_step(const char *text, SimStep *step)
{
    unsigned value;
    size_t length = strlen(text);
    if (!length || length > 48) return 0;
    memset(step, 0, sizeof(*step));
    step->advance_ticks = 5;
    step->message.topic = TOP_INPUT_BTN;
    if (length <= 3 && sim_decimal(text, length, 255, &value)) {
        step->message.u.btn.id = (uint8_t)value;
        step->message.u.btn.pressed = 1;
        return 1;
    }
    if (strncmp(text, "button:", 7) == 0) {
        const char *edge = strchr(text + 7, ':');
        size_t id_length = edge ? (size_t)(edge - (text + 7)) : 0;
        if (!edge || id_length > 3 || (id_length > 1 && text[7] == '0') ||
            !sim_decimal(text + 7, id_length, 255, &value)) return 0;
        if (strcmp(edge + 1, "press") != 0 && strcmp(edge + 1, "release") != 0) return 0;
        step->message.u.btn.id = (uint8_t)value;
        step->message.u.btn.pressed = strcmp(edge + 1, "press") == 0;
        return 1;
    }
    if (strncmp(text, "tick:", 5) == 0) {
        if (length > 9 || text[5] == '0' ||
            !sim_decimal(text + 5, length - 5, SIM_MAX_STEP_TICKS, &value) || !value) return 0;
        step->tick_only = 1;
        step->advance_ticks = value;
        return 1;
    }
    if (strncmp(text, "display:", 8) == 0) {
        if (strcmp(text + 8, "connected") == 0) step->display_status = SIM_DISPLAY_CONNECTED;
        else if (strcmp(text + 8, "disconnected") == 0) step->display_status = SIM_DISPLAY_DISCONNECTED;
        else if (strcmp(text + 8, "error") == 0) step->display_status = SIM_DISPLAY_ERROR;
        else return 0;
        step->display_change = 1;
        return 1;
    }
#ifdef SIM_APP
    if (strncmp(text, "action:", 7) == 0) {
        const char *sep = strchr(text + 7, ':');
        size_t id_length = sep ? (size_t)(sep - (text + 7)) : 0;
        if (!sep || !sim_identifier(text + 7, id_length) ||
            id_length >= sizeof(step->message.u.ui_action.id) ||
            !sim_decimal(sep + 1, strlen(sep + 1), 999999999, &value)) return 0;
        step->message.topic = TOP_UI_ACTION;
        memcpy(step->message.u.ui_action.id, text + 7, id_length);
        step->message.u.ui_action.arg = (uint32_t)value;
        return 1;
    }
    if (strncmp(text, "cmd:", 4) == 0) {
        const char *id = strchr(text + 4, ':');
        const char *sep = id ? strchr(id + 1, ':') : NULL;
        size_t kind_length = id ? (size_t)(id - (text + 4)) : 0;
        size_t id_length = sep ? (size_t)(sep - (id + 1)) : 0;
        unsigned kind;
        if (!id || !sep || kind_length > 2 || text[4] == '0' ||
            !sim_decimal(text + 4, kind_length, 20, &kind) ||
            (kind != 2 && kind != 3 && kind != 20) ||
            !sim_identifier(id + 1, id_length) || id_length >= sizeof(step->message.u.ui_cmd.id) ||
            !sim_decimal(sep + 1, strlen(sep + 1), 999999999, &value)) return 0;
        step->message.topic = TOP_UI_CMD;
        step->message.u.ui_cmd.kind = (uint8_t)kind;
        memcpy(step->message.u.ui_cmd.id, id + 1, id_length);
        step->message.u.ui_cmd.value = (int32_t)value;
        return 1;
    }
#endif
    return 0;
}

#ifdef SIM_APP
#include "scheduler.h"
#include "services/ui_app/ui_app.h"
#include "services/logic/logic.h"
int sim_app_screen(void);
int sim_logic_booted(void);
#else
static jmp_buf done;
static int cursor, initial_repaint;
static unsigned remaining_ticks;
static int64_t sim_time;
int64_t esp_timer_get_time(void) { return sim_time; }
void esp_timer_set_mock_time(int64_t us) { sim_time = us; }
#endif
extern int sim_display_status;
int sim_save_frame(const char *path);

static void sim_apply_display(const SimStep *step, msg_t *repaint)
{
    /* The existing mock driver reads this status on every transport operation. */
    sim_display_status = step->display_status;
    /* Production clears dirty regions even after a failed flush. Its supported
     * same-color RPC requests a full repaint without resetting the current scene,
     * focus, editors or widgets. Store is the existing in-memory host stub. */
    store_conf_t conf;
    memset(&conf, 0, sizeof(conf));
    (void)store_get_conf(&conf);
    memset(repaint, 0, sizeof(*repaint));
    repaint->topic = TOP_RPC_CALL;
    memcpy(repaint->u.rpc.method, "set_bg", sizeof("set_bg"));
    repaint->u.rpc.arg = conf.bg_rgb;
}

#ifndef SIM_APP
QueueHandle_t bus_make_queue(size_t depth) { (void)depth; return (void *)1; }
esp_err_t bus_subscribe(topic_t t, QueueHandle_t q) { (void)t; (void)q; return ESP_OK; }
void bus_publish(const msg_t *m) { (void)m; /* app subscriber not simulated */ }
int xQueueReceive(QueueHandle_t q, void *out, uint32_t timeout)
{
    (void)q; (void)timeout;
    if (!initial_repaint) { initial_repaint = 1; return 0; }
    if (!remaining_ticks) {
        if (cursor >= event_count) longjmp(done, 1);
        const SimStep *step = &steps[cursor++];
        if (!step->tick_only) {
            /* Keep legacy numeric input timestamps: first at 100 ms, then +50. */
            if (!sim_time) esp_timer_set_mock_time(50000LL);
            esp_timer_set_mock_time(sim_time + (int64_t)step->advance_ticks * 10000LL);
            if (step->display_change) sim_apply_display(step, out);
            else memcpy(out, &step->message, sizeof(step->message));
            return pdTRUE;
        }
        remaining_ticks = step->advance_ticks;
    }
    remaining_ticks--;
    esp_timer_set_mock_time(sim_time + 10000LL);
    return 0; /* real UI timeout path: flash/toast/animation, no synthetic button */
}
#endif
#ifdef SIM_APP
static void sim_advance_ticks(unsigned count, msg_t *tick)
{
    for (unsigned i = 0; i < count; i++) {
        sim_scheduler_advance(10);
        tick->u.tick.tick++;
        bus_publish(tick);
        sim_scheduler_drain();
    }
}
#endif
int main(int argc, char **argv)
{
    if (argc < 3 || argc > SIM_MAX_EVENTS + 3) return 2;
    if (strcmp(argv[2], "0") == 0) sim_display_status = SIM_DISPLAY_CONNECTED;
    else if (strcmp(argv[2], "261") == 0) sim_display_status = SIM_DISPLAY_DISCONNECTED;
    else if (strcmp(argv[2], "-1") == 0) sim_display_status = SIM_DISPLAY_ERROR;
    else return 2;
    unsigned advance_ticks = 0;
    event_count = argc - 3;
    for (int i = 0; i < event_count; i++) {
        if (!sim_parse_step(argv[i + 3], &steps[i])) return 2;
        advance_ticks += steps[i].advance_ticks;
        if (advance_ticks > SIM_MAX_ADVANCE_TICKS) return 2;
    }
#ifdef SIM_APP
    sim_scheduler_init();
    bus_init();
    ui_start(); ui_app_start(); logic_start();
    sim_scheduler_drain();
    sim_scheduler_advance(150); /* production app startup delay */
    msg_t tick = {0}; tick.topic = TOP_TICK_10MS; tick.u.tick.tick = 15;
    bus_publish(&tick); sim_scheduler_drain();
    for (int i = 0; i < event_count; i++) {
        const SimStep *step = &steps[i];
        if (step->display_change) {
            msg_t repaint;
            sim_apply_display(step, &repaint);
            bus_publish(&repaint);
            sim_scheduler_drain();
            sim_advance_ticks(step->advance_ticks, &tick);
        } else if (!step->tick_only) {
            bus_publish(&step->message);
            sim_scheduler_drain();
            /* Preserve the existing numeric/action/cmd settling policy. */
            tick.u.tick.tick += step->advance_ticks;
            bus_publish(&tick);
            sim_scheduler_advance(step->advance_ticks * 10);
        } else {
            sim_advance_ticks(step->advance_ticks, &tick);
        }
    }
#else
    if (setjmp(done) == 0) ui_task(NULL);
#endif
    int frame_error = sim_save_frame(argv[1]);
    if (!frame_error) {
        printf("{\"runtime_simulation\":true,\"display_status\":%d,\"widgets\":[", sim_display_status);
        for (unsigned i = 0; i < s_scene.widget_count; i++) {
            const UiWidget *w = &s_scene.widgets[i];
            printf("%s{\"index\":%u,\"value\":%d,\"checked\":%u,\"style\":%u,\"visible\":%u}",
                   i ? "," : "", i, w->value, w->checked, w->style, w->visible);
        }
#ifdef SIM_APP
        unsigned drops = 0;
        for (int t = 0; t < 16; t++) drops += bus_drop_count((topic_t)t);
        printf("],\"app_screen\":%d,\"logic_booted\":%d,\"scheduler_steps\":%u,\"bus_drops\":%u,\"texts\":[",
            sim_app_screen(), sim_logic_booted(), sim_scheduler_steps(), drops);
        /* Text bytes encoded as hex for valid JSON without a replacement UI model. */
        for (unsigned i = 0; i < s_scene.widget_count; i++) {
            printf("%s\"", i ? "," : "");
            const unsigned char *p = (const unsigned char *)s_scene.widgets[i].text;
            if (p) for (; *p; p++) printf("%02x", *p);
            printf("\"");
        }
        puts("]}");
#else
        puts("]}");
#endif
    }
#ifdef SIM_APP
    ui_stop(); ui_app_stop(); logic_stop();
    sim_scheduler_destroy(); bus_deinit();
#endif
    return frame_error ? 3 : 0;
}
