#include "ui.h"

#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <inttypes.h>

#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "display/ssd1363.h"
#include "display_config.h"
#include "kernel/msgbus.h"
#include "services/input/input.h"
#include "services/store/store.h"

#include "ui_design.h"
#include "ui_bindings.h"
#include "ui_meta.h"
#include "ui_nav.h"
#include "ui_render.h"
#include "ui_render_swbuf.h"
#include "ui_components.h"
#include "ui_listmodel.h"

static const char *TAG = "ui";

static TaskHandle_t s_ui_task = NULL;

enum { UI_MAX_WIDGETS = 128 };
static UiWidget s_widgets[UI_MAX_WIDGETS];
static UiScene s_scene;

static UiListModels s_listmodels;

enum { UI_TEXT_OVERRIDE_LEN = 64 };
static const char *s_text_original[UI_MAX_WIDGETS];
static char s_text_override[UI_MAX_WIDGETS][UI_TEXT_OVERRIDE_LEN];

typedef struct {
    int dirty;
    int x0, y0;
    int x1, y1; /* exclusive */
} UiDirty;

typedef enum {
    UI_EDIT_NONE = 0,
    UI_EDIT_SLIDER = 1,
    UI_EDIT_BIND_INT = 2,
    UI_EDIT_BIND_ENUM = 3,
} UiEditKind;

typedef struct {
    UiEditKind kind;
    int idx;
    uint8_t saved_style;
    ui_meta_t meta;
} UiEdit;

typedef struct {
    uint8_t active;
    int focus_before;
    int x, y;
    int w, h;
    char root[32];
} UiModal;

typedef enum {
    UI_ACT_NONE = 0,
    UI_ACT_EDIT_ENTERED = 1,
    UI_ACT_ACTION_PUBLISHED = 2,
} UiActivateResult;

enum { UI_TOAST_QUEUE_LEN = 4 };

typedef struct {
    char message[UI_TEXT_OVERRIDE_LEN];
    uint32_t duration_ms;
} UiToastItem;

typedef struct {
    uint8_t active;
    int64_t expires_us;
    char root[32];
    UiToastItem q[UI_TOAST_QUEUE_LEN];
    uint8_t head;
    uint8_t count;
} UiToast;

static void ui_dirty_clear(UiDirty *d)
{
    if (d == NULL) {
        return;
    }
    d->dirty = 0;
    d->x0 = d->y0 = 0;
    d->x1 = d->y1 = 0;
}

static void ui_dirty_add(UiDirty *d, int x, int y, int w, int h)
{
    if (d == NULL) {
        return;
    }
    if (w <= 0 || h <= 0) {
        return;
    }

    int x0 = x;
    int y0 = y;
    int x1 = x + w;
    int y1 = y + h;

    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > DISPLAY_WIDTH) x1 = DISPLAY_WIDTH;
    if (y1 > DISPLAY_HEIGHT) y1 = DISPLAY_HEIGHT;
    if (x0 >= x1 || y0 >= y1) {
        return;
    }

    if (!d->dirty) {
        d->dirty = 1;
        d->x0 = x0;
        d->y0 = y0;
        d->x1 = x1;
        d->y1 = y1;
        return;
    }

    if (x0 < d->x0) d->x0 = x0;
    if (y0 < d->y0) d->y0 = y0;
    if (x1 > d->x1) d->x1 = x1;
    if (y1 > d->y1) d->y1 = y1;
}

static void ui_dirty_add_adapter(void *ctx, int x, int y, int w, int h)
{
    ui_dirty_add((UiDirty *)ctx, x, y, w, h);
}

static void ui_dirty_full(UiDirty *d)
{
    ui_dirty_add(d, 0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT);
}

static void ui_widget_rect(const UiScene *scene, int idx, int *x, int *y, int *w, int *h)
{
    if (x) *x = 0;
    if (y) *y = 0;
    if (w) *w = 0;
    if (h) *h = 0;
    if (scene == NULL || scene->widgets == NULL) {
        return;
    }
    if (idx < 0 || (uint16_t)idx >= scene->widget_count) {
        return;
    }
    const UiWidget *ww = &scene->widgets[(uint16_t)idx];
    if (x) *x = (int)ww->x;
    if (y) *y = (int)ww->y;
    if (w) *w = (int)ww->width;
    if (h) *h = (int)ww->height;
}

static void ui_draw_focus(UiDrawOps *ops, const UiScene *scene, int idx)
{
    if (ops == NULL || ops->draw_rect == NULL || scene == NULL || scene->widgets == NULL) {
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

static int ui_scene_clone(const UiScene *src, UiScene *dst, UiWidget *dst_widgets, int max_widgets)
{
    if (src == NULL || dst == NULL || dst_widgets == NULL || src->widgets == NULL) {
        return 0;
    }

    uint16_t count = src->widget_count;
    if (count > (uint16_t)max_widgets) {
        ESP_LOGE(TAG, "scene too large: %" PRIu16 " widgets (max %d)", count, max_widgets);
        count = (uint16_t)max_widgets;
    }

    memcpy(dst_widgets, src->widgets, (size_t)count * sizeof(UiWidget));
    *dst = *src;
    dst->widget_count = count;
    dst->widgets = dst_widgets;
    return 1;
}

static UiWidget *ui_scene_widget_mut(UiScene *scene, int idx)
{
    if (scene == NULL || scene->widgets == NULL) {
        return NULL;
    }
    if (idx < 0 || (uint16_t)idx >= scene->widget_count) {
        return NULL;
    }
    return (UiWidget *)&scene->widgets[(uint16_t)idx];
}

static int ui_scene_find_by_id(const UiScene *scene, const char *id)
{
    if (scene == NULL || scene->widgets == NULL || id == NULL || *id == '\0') {
        return -1;
    }
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        const UiWidget *w = &scene->widgets[i];
        if (w->id != NULL && strcmp(w->id, id) == 0) {
            return (int)i;
        }
    }
    return -1;
}

static void ui_scene_set_text(UiScene *scene, int idx, const char *text)
{
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return;
    }
    if (idx < 0 || idx >= UI_MAX_WIDGETS) {
        return;
    }

    if (text == NULL) {
        w->text = NULL;
        s_text_override[idx][0] = '\0';
        return;
    }

    size_t n = strlen(text);
    if (n >= UI_TEXT_OVERRIDE_LEN) {
        n = UI_TEXT_OVERRIDE_LEN - 1;
    }
    memcpy(s_text_override[idx], text, n);
    s_text_override[idx][n] = '\0';
    w->text = s_text_override[idx];
}

static int ui_text_equals(const char *a, const char *b)
{
    if (a == NULL) {
        a = "";
    }
    if (b == NULL) {
        b = "";
    }
    return (strcmp(a, b) == 0) ? 1 : 0;
}

static void ui_scene_set_text_if_changed(UiScene *scene, int idx, const char *text, UiDirty *dirty)
{
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return;
    }
    const char *cur = (w->text != NULL) ? w->text : "";
    const char *desired = (text != NULL) ? text : "";
    if (ui_text_equals(cur, desired)) {
        return;
    }
    ui_scene_set_text(scene, idx, desired);
    if (dirty != NULL) {
        int x, y, ww, hh;
        ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
        ui_dirty_add(dirty, x, y, ww, hh);
    }
}

static int ui_parse_uint_dec(const char *s, int *out_value)
{
    if (out_value != NULL) {
        *out_value = 0;
    }
    if (s == NULL || *s < '0' || *s > '9') {
        return 0;
    }
    int v = 0;
    const char *p = s;
    while (*p >= '0' && *p <= '9') {
        int next = v * 10 + (*p - '0');
        if (next < v) {
            break;
        }
        v = next;
        p += 1;
    }
    if (out_value != NULL) {
        *out_value = v;
    }
    return 1;
}

static int ui_parse_item_root_slot(const char *id, char *root_out, size_t root_cap, int *out_slot)
{
    if (out_slot != NULL) {
        *out_slot = 0;
    }
    if (root_out != NULL && root_cap > 0) {
        root_out[0] = '\0';
    }
    if (id == NULL || *id == '\0' || root_out == NULL || root_cap == 0) {
        return 0;
    }

    const char *dot = strchr(id, '.');
    if (dot == NULL || dot == id || dot[1] == '\0') {
        return 0;
    }

    size_t root_len = (size_t)(dot - id);
    if (root_len >= root_cap) {
        root_len = root_cap - 1;
    }
    memcpy(root_out, id, root_len);
    root_out[root_len] = '\0';

    const char *role = dot + 1;
    if (strncmp(role, "item", 4) != 0) {
        return 0;
    }
    int slot = 0;
    if (!ui_parse_uint_dec(role + 4, &slot)) {
        return 0;
    }
    if (out_slot != NULL) {
        *out_slot = slot;
    }
    return 1;
}

static int ui_scene_count_item_slots(const UiScene *scene, const char *root)
{
    if (scene == NULL || root == NULL || *root == '\0') {
        return 0;
    }

    char id[48];
    int count = 0;
    for (int i = 0; i < 32; ++i) {
        snprintf(id, sizeof(id), "%s.item%d", root, i);
        if (ui_scene_find_by_id(scene, id) < 0) {
            break;
        }
        count += 1;
    }
    return count;
}

static void ui_listmodel_apply_to_scene(UiScene *scene, UiListModel *m, UiDirty *dirty)
{
    if (scene == NULL || m == NULL || !m->used || m->root[0] == '\0') {
        return;
    }

    int visible = ui_scene_count_item_slots(scene, m->root);
    if (visible <= 0) {
        return;
    }

    (void)ui_listmodel_set_active(m, (int)m->active, visible);

    char scroll_text[16];
    ui_listmodel_format_scroll(m, scroll_text, (int)sizeof(scroll_text));

    char scroll_id[48];
    snprintf(scroll_id, sizeof(scroll_id), "%s.scroll", m->root);
    int scroll_idx = ui_scene_find_by_id(scene, scroll_id);
    if (scroll_idx >= 0) {
        ui_scene_set_text_if_changed(scene, scroll_idx, scroll_text, dirty);
    }

    for (int slot = 0; slot < visible; ++slot) {
        int abs = (int)m->offset + slot;

        char item_id[48];
        snprintf(item_id, sizeof(item_id), "%s.item%d", m->root, slot);
        int item_idx = ui_scene_find_by_id(scene, item_id);
        if (item_idx < 0) {
            continue;
        }

        UiWidget *btn = ui_scene_widget_mut(scene, item_idx);
        if (btn == NULL) {
            continue;
        }

        uint8_t before_visible = btn->visible;
        uint8_t before_enabled = btn->enabled;
        int16_t before_value = btn->value;

        const char *label = "";
        const char *value = "";
        if (abs >= 0 && abs < (int)m->count) {
            const UiListItem *it = &m->items[abs];
            label = it->label;
            value = it->value;
            btn->enabled = 1;
            btn->visible = 1;
            btn->value = (int16_t)abs;
        } else {
            btn->enabled = 0;
            btn->visible = 1;
            btn->value = 0;
        }

        if (dirty != NULL && (btn->visible != before_visible || btn->enabled != before_enabled || btn->value != before_value)) {
            int x, y, ww, hh;
            ui_widget_rect(scene, item_idx, &x, &y, &ww, &hh);
            ui_dirty_add(dirty, x, y, ww, hh);
        }

        char label_id[64];
        snprintf(label_id, sizeof(label_id), "%s.item%d.label", m->root, slot);
        int label_idx = ui_scene_find_by_id(scene, label_id);
        if (label_idx >= 0) {
            ui_scene_set_text_if_changed(scene, label_idx, label, dirty);
        } else {
            ui_scene_set_text_if_changed(scene, item_idx, label, dirty);
        }

        char value_id[64];
        snprintf(value_id, sizeof(value_id), "%s.item%d.value", m->root, slot);
        int value_idx = ui_scene_find_by_id(scene, value_id);
        if (value_idx >= 0) {
            ui_scene_set_text_if_changed(scene, value_idx, value, dirty);
        }
    }

    int active_slot = ui_listmodel_active_slot(m);
    (void)ui_components_menu_set_active(scene, m->root, active_slot, ui_dirty_add_adapter, dirty);
}

static void ui_listmodel_sync_from_focus(UiScene *scene, UiListModels *lists, int focus_idx, UiDirty *dirty)
{
    if (scene == NULL || lists == NULL || scene->widgets == NULL) {
        return;
    }
    if (focus_idx < 0 || (uint16_t)focus_idx >= scene->widget_count) {
        return;
    }

    const UiWidget *w = &scene->widgets[(uint16_t)focus_idx];
    if (w->id == NULL || w->id[0] == '\0') {
        return;
    }

    char root[32];
    int slot = 0;
    if (!ui_parse_item_root_slot(w->id, root, sizeof(root), &slot)) {
        return;
    }

    UiListModel *m = ui_listmodels_get(lists, root, false);
    if (m == NULL || m->count == 0) {
        return;
    }

    int visible = ui_scene_count_item_slots(scene, root);
    if (visible <= 0) {
        return;
    }

    int abs = (int)w->value;
    if (abs < 0 || abs >= (int)m->count) {
        abs = (int)m->offset + slot;
    }

    if (ui_listmodel_set_active(m, abs, visible)) {
        ui_listmodel_apply_to_scene(scene, m, dirty);
    }
}

static void ui_toggle_checkbox(UiScene *scene, int idx, UiDirty *dirty)
{
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return;
    }
    if ((UiWidgetType)w->type != UIW_CHECKBOX) {
        return;
    }
    w->checked = (uint8_t)(w->checked ? 0 : 1);
    int x, y, ww, hh;
    ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
    ui_dirty_add(dirty, x, y, ww, hh);
}

static void ui_select_radiobutton(UiScene *scene, int idx, UiDirty *dirty)
{
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return;
    }
    if ((UiWidgetType)w->type != UIW_RADIOBUTTON) {
        return;
    }

    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        UiWidget *rw = ui_scene_widget_mut(scene, (int)i);
        if (rw == NULL) {
            continue;
        }
        if ((UiWidgetType)rw->type != UIW_RADIOBUTTON) {
            continue;
        }
        uint8_t desired = (i == (uint16_t)idx) ? 1 : 0;
        if (rw->checked == desired) {
            continue;
        }
        rw->checked = desired;
        int x, y, ww, hh;
        ui_widget_rect(scene, (int)i, &x, &y, &ww, &hh);
        ui_dirty_add(dirty, x, y, ww, hh);
    }
}

static void ui_adjust_slider(UiScene *scene, int idx, int delta, UiDirty *dirty)
{
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return;
    }
    if ((UiWidgetType)w->type != UIW_SLIDER) {
        return;
    }

    int v = (int)w->value + delta;
    int vmin = (int)w->min_value;
    int vmax = (int)w->max_value;
    if (v < vmin) v = vmin;
    if (v > vmax) v = vmax;
    if (v == (int)w->value) {
        return;
    }
    w->value = (int16_t)v;

    int x, y, ww, hh;
    ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
    ui_dirty_add(dirty, x, y, ww, hh);
}

static int ui_update_bound_text(UiScene *scene, int idx)
{
    if (scene == NULL) {
        return 0;
    }
    if (idx < 0 || idx >= UI_MAX_WIDGETS) {
        return 0;
    }
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return 0;
    }
    if (w->constraints_json == NULL || *w->constraints_json == '\0') {
        return 0;
    }

    ui_meta_t meta;
    if (!ui_meta_parse(w->constraints_json, &meta)) {
        return 0;
    }

    const char *base = s_text_original[idx];
    if (base == NULL || *base == '\0') {
        base = meta.bind_key;
    }

    char vbuf[32];
    vbuf[0] = '\0';

    if (meta.kind == UI_META_KIND_BOOL) {
        bool cur = false;
        if (!ui_bind_get_bool(meta.bind_key, &cur)) {
            return 0;
        }
        if (meta.values[0] != '\0' && ui_meta_values_count(meta.values) >= 2) {
            (void)ui_meta_values_get(meta.values, cur ? 1 : 0, vbuf, sizeof(vbuf));
        } else {
            snprintf(vbuf, sizeof(vbuf), "%s", cur ? "on" : "off");
        }
    } else if (meta.kind == UI_META_KIND_INT) {
        int cur = 0;
        if (!ui_bind_get_int(meta.bind_key, &cur)) {
            return 0;
        }
        snprintf(vbuf, sizeof(vbuf), "%d", cur);
    } else if (meta.kind == UI_META_KIND_ENUM) {
        int cur = 0;
        if (!ui_bind_get_int(meta.bind_key, &cur)) {
            return 0;
        }
        int cnt = ui_meta_values_count(meta.values);
        if (cnt <= 0) {
            snprintf(vbuf, sizeof(vbuf), "%d", cur);
        } else {
            if (cur < 0) cur = 0;
            if (cur >= cnt) cur = cnt - 1;
            if (!ui_meta_values_get(meta.values, cur, vbuf, sizeof(vbuf))) {
                snprintf(vbuf, sizeof(vbuf), "%d", cur);
            }
        }
    } else {
        return 0;
    }

    char out[UI_TEXT_OVERRIDE_LEN];
    snprintf(out, sizeof(out), "%s: %s", base, vbuf);

    const char *cur_txt = (w->text != NULL) ? w->text : "";
    if (strcmp(cur_txt, out) == 0) {
        return 0;
    }

    ui_scene_set_text(scene, idx, out);
    return 1;
}

static void ui_update_status_bar(UiScene *scene, uint32_t free_heap, uint32_t min_free_heap, UiDirty *dirty)
{
    if (scene == NULL || dirty == NULL) {
        return;
    }

    const int left = ui_scene_find_by_id(scene, "status_bar.left");
    const int right = ui_scene_find_by_id(scene, "status_bar.right");

    if (left >= 0) {
        char buf[UI_TEXT_OVERRIDE_LEN];
        snprintf(buf, sizeof(buf), "HEAP %luk", (unsigned long)(free_heap / 1024U));
        ui_scene_set_text(scene, left, buf);
        int x, y, w, h;
        ui_widget_rect(scene, left, &x, &y, &w, &h);
        ui_dirty_add(dirty, x, y, w, h);
    }
    if (right >= 0) {
        char buf[UI_TEXT_OVERRIDE_LEN];
        snprintf(buf, sizeof(buf), "MIN %luk", (unsigned long)(min_free_heap / 1024U));
        ui_scene_set_text(scene, right, buf);
        int x, y, w, h;
        ui_widget_rect(scene, right, &x, &y, &w, &h);
        ui_dirty_add(dirty, x, y, w, h);
    }
}

static void ui_edit_exit(UiScene *scene, UiEdit *edit, UiDirty *dirty)
{
    if (edit == NULL || edit->kind == UI_EDIT_NONE) {
        return;
    }

    UiWidget *w = ui_scene_widget_mut(scene, edit->idx);
    if (w != NULL) {
        w->style = edit->saved_style;
        if (dirty != NULL) {
            int x, y, ww, hh;
            ui_widget_rect(scene, edit->idx, &x, &y, &ww, &hh);
            ui_dirty_add(dirty, x, y, ww, hh);
        }
    }

    edit->kind = UI_EDIT_NONE;
    edit->idx = -1;
    memset(&edit->meta, 0, sizeof(edit->meta));
    edit->saved_style = 0;
}

static size_t ui_estimate_flush_bytes(const UiSwBuf *sw)
{
    if (sw == NULL) {
        return 0;
    }
    int dx, dy, dw, dh;
    if (!ui_swbuf_get_dirty(sw, &dx, &dy, &dw, &dh)) {
        return 0;
    }
#if DISPLAY_COLOR_BITS == 4
    int ax0 = dx & ~3;
    int ax1 = (dx + dw - 1) | 3;
    if (ax0 < 0) ax0 = 0;
    if (ax1 >= DISPLAY_WIDTH) ax1 = DISPLAY_WIDTH - 1;
    int w_aligned = (ax1 >= ax0) ? (ax1 - ax0 + 1) : 0;
    int out_row_bytes = (w_aligned + 1) / 2;
    return (size_t)out_row_bytes * (size_t)dh;
#else
    size_t start_byte = (size_t)(dx >> 3);
    size_t end_byte = (size_t)((dx + dw + 7) >> 3);
    size_t bytes_per_row = end_byte - start_byte;
    return bytes_per_row * (size_t)dh;
#endif
}

static void ui_modal_reset(UiModal *modal)
{
    if (modal == NULL) {
        return;
    }
    modal->active = 0;
    modal->focus_before = -1;
    modal->x = 0;
    modal->y = 0;
    modal->w = 0;
    modal->h = 0;
    modal->root[0] = '\0';
}

static void ui_publish_action(const UiWidget *w)
{
    if (w == NULL || w->id == NULL || *w->id == '\0') {
        return;
    }
    msg_t out = {0};
    out.topic = TOP_UI_ACTION;
    snprintf(out.u.ui_action.id, sizeof(out.u.ui_action.id), "%s", w->id);
    out.u.ui_action.arg = (uint32_t)w->value;
    bus_publish(&out);
}

static UiActivateResult ui_activate_widget(UiScene *scene, int idx, UiEdit *edit, int *flash, UiDirty *dirty)
{
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    if (w == NULL) {
        return UI_ACT_NONE;
    }

    UiWidgetType t = (UiWidgetType)w->type;
    if (t == UIW_CHECKBOX) {
        ui_toggle_checkbox(scene, idx, dirty);
        return UI_ACT_NONE;
    }
    if (t == UIW_RADIOBUTTON) {
        ui_select_radiobutton(scene, idx, dirty);
        return UI_ACT_NONE;
    }
    if (t == UIW_SLIDER) {
        if (edit != NULL) {
            edit->kind = UI_EDIT_SLIDER;
            edit->idx = idx;
            edit->saved_style = w->style;
            w->style = (uint8_t)(w->style | UI_STYLE_HIGHLIGHT);
        }
        if (dirty != NULL) {
            int x, y, ww, hh;
            ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
            ui_dirty_add(dirty, x, y, ww, hh);
        }
        return UI_ACT_EDIT_ENTERED;
    }

    ui_meta_t meta;
    if (w->constraints_json != NULL &&
        ui_meta_parse(w->constraints_json, &meta)) {
        if (meta.kind == UI_META_KIND_BOOL) {
            bool cur = false;
            if (ui_bind_get_bool(meta.bind_key, &cur)) {
                (void)ui_bind_set_bool(meta.bind_key, !cur);
                if (ui_update_bound_text(scene, idx) && dirty != NULL) {
                    int x, y, ww, hh;
                    ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
                    ui_dirty_add(dirty, x, y, ww, hh);
                }
            }
            return UI_ACT_NONE;
        }
        if (edit != NULL) {
            if (meta.kind == UI_META_KIND_ENUM) {
                edit->kind = UI_EDIT_BIND_ENUM;
            } else {
                edit->kind = UI_EDIT_BIND_INT;
            }
            edit->idx = idx;
            edit->saved_style = w->style;
            edit->meta = meta;
            w->style = (uint8_t)(w->style | UI_STYLE_HIGHLIGHT);
        }
        if (dirty != NULL) {
            int x, y, ww, hh;
            ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
            ui_dirty_add(dirty, x, y, ww, hh);
        }
        return UI_ACT_EDIT_ENTERED;
    }

    ui_publish_action(w);
    if (flash != NULL) {
        *flash = 6;
    }
    if (dirty != NULL) {
        ui_dirty_add(dirty, 0, 0, 6, 6);
    }
    return UI_ACT_ACTION_PUBLISHED;
}

static int ui_modal_find_rect(UiScene *scene, const char *root, int *x, int *y, int *w, int *h)
{
    if (x) *x = 0;
    if (y) *y = 0;
    if (w) *w = 0;
    if (h) *h = 0;
    if (scene == NULL || root == NULL || *root == '\0') {
        return 0;
    }

    char id[48];
    snprintf(id, sizeof(id), "%s.dialog", root);
    int idx = ui_scene_find_by_id(scene, id);
    if (idx < 0) {
        snprintf(id, sizeof(id), "%s.panel", root);
        idx = ui_scene_find_by_id(scene, id);
    }
    if (idx < 0) {
        return 0;
    }
    int rx, ry, rw, rh;
    ui_widget_rect(scene, idx, &rx, &ry, &rw, &rh);
    if (rw <= 0 || rh <= 0) {
        return 0;
    }
    if (x) *x = rx;
    if (y) *y = ry;
    if (w) *w = rw;
    if (h) *h = rh;
    return 1;
}

static void ui_modal_show(UiScene *scene, UiModal *modal, const char *root, int *focus, UiEdit *edit, UiDirty *dirty)
{
    if (scene == NULL || modal == NULL || root == NULL || *root == '\0') {
        return;
    }

    if (modal->active) {
        (void)ui_components_set_prefix_visible(scene, modal->root, false, ui_dirty_add_adapter, dirty);
        ui_modal_reset(modal);
    }

    if (edit != NULL) {
        ui_edit_exit(scene, edit, dirty);
    }

    modal->active = 1;
    modal->focus_before = (focus != NULL) ? *focus : -1;
    strncpy(modal->root, root, sizeof(modal->root) - 1);
    modal->root[sizeof(modal->root) - 1] = '\0';

    (void)ui_components_set_prefix_visible(scene, root, true, ui_dirty_add_adapter, dirty);

    if (!ui_modal_find_rect(scene, root, &modal->x, &modal->y, &modal->w, &modal->h)) {
        modal->x = 0;
        modal->y = 0;
        modal->w = DISPLAY_WIDTH;
        modal->h = DISPLAY_HEIGHT;
    }

    if (focus != NULL) {
        int nf = ui_nav_first_focus_in_rect(scene, modal->x, modal->y, modal->w, modal->h);
        *focus = nf;
    }

    ui_dirty_full(dirty);
}

static void ui_modal_hide(UiScene *scene, UiModal *modal, int *focus, UiEdit *edit, UiDirty *dirty)
{
    if (scene == NULL || modal == NULL || !modal->active) {
        return;
    }

    if (edit != NULL) {
        ui_edit_exit(scene, edit, dirty);
    }

    (void)ui_components_set_prefix_visible(scene, modal->root, false, ui_dirty_add_adapter, dirty);

    int restore_focus = modal->focus_before;
    ui_modal_reset(modal);

    if (focus != NULL) {
        int nf = restore_focus;
        if (nf < 0 || (uint16_t)nf >= scene->widget_count || !ui_nav_is_focusable(&scene->widgets[(uint16_t)nf])) {
            nf = ui_nav_first_focus(scene);
        }
        *focus = nf;
    }

    ui_dirty_full(dirty);
}

static void ui_modal_cancel(UiScene *scene, UiModal *modal, int *focus, UiEdit *edit, UiDirty *dirty)
{
    if (scene == NULL || modal == NULL || !modal->active) {
        return;
    }

    char cancel_id[48];
    snprintf(cancel_id, sizeof(cancel_id), "%s.cancel", modal->root);
    int idx = ui_scene_find_by_id(scene, cancel_id);
    UiWidget *w = ui_scene_widget_mut(scene, idx);
    ui_publish_action(w);

    ui_modal_hide(scene, modal, focus, edit, dirty);
}

static void ui_toast_reset(UiToast *toast)
{
    if (toast == NULL) {
        return;
    }
    toast->active = 0;
    toast->expires_us = 0;
    toast->root[0] = '\0';
    toast->head = 0;
    toast->count = 0;
    for (int i = 0; i < UI_TOAST_QUEUE_LEN; ++i) {
        toast->q[i].message[0] = '\0';
        toast->q[i].duration_ms = 0;
    }
}

static void ui_toast_hide(UiScene *scene, UiToast *toast, UiDirty *dirty)
{
    if (scene == NULL || toast == NULL) {
        return;
    }
    if (toast->root[0] != '\0') {
        (void)ui_components_set_prefix_visible(scene, toast->root, false, ui_dirty_add_adapter, dirty);
    }
    ui_toast_reset(toast);
}

static void ui_toast_apply_message(UiScene *scene, const char *root, const char *message, UiDirty *dirty)
{
    if (scene == NULL || root == NULL || *root == '\0') {
        return;
    }

    char id[48];
    snprintf(id, sizeof(id), "%s.message", root);
    int idx = ui_scene_find_by_id(scene, id);
    if (idx >= 0) {
        ui_scene_set_text(scene, idx, message);
        int x, y, ww, hh;
        ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
        ui_dirty_add(dirty, x, y, ww, hh);
    }

    /* Keep toast non-focusable by hiding any optional action button. */
    snprintf(id, sizeof(id), "%s.button", root);
    idx = ui_scene_find_by_id(scene, id);
    UiWidget *btn = ui_scene_widget_mut(scene, idx);
    if (btn != NULL && btn->visible != 0) {
        btn->visible = 0;
        int x, y, ww, hh;
        ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
        ui_dirty_add(dirty, x, y, ww, hh);
    }
}

static void ui_toast_show(UiScene *scene, UiToast *toast, const char *root, const char *message, uint32_t duration_ms, UiDirty *dirty)
{
    if (scene == NULL || toast == NULL || root == NULL || *root == '\0') {
        return;
    }
    if (duration_ms == 0U) {
        duration_ms = 1500U;
    }

    strncpy(toast->root, root, sizeof(toast->root) - 1);
    toast->root[sizeof(toast->root) - 1] = '\0';
    toast->active = 1;
    toast->expires_us = esp_timer_get_time() + ((int64_t)duration_ms * 1000);

    (void)ui_components_set_prefix_visible(scene, toast->root, true, ui_dirty_add_adapter, dirty);
    ui_toast_apply_message(scene, toast->root, message, dirty);
}

static void ui_toast_queue_push(UiToast *toast, const char *message, uint32_t duration_ms)
{
    if (toast == NULL) {
        return;
    }
    if (toast->count >= UI_TOAST_QUEUE_LEN) {
        toast->head = (uint8_t)((toast->head + 1U) % UI_TOAST_QUEUE_LEN);
        toast->count = (uint8_t)(toast->count - 1U);
    }
    uint8_t tail = (uint8_t)((toast->head + toast->count) % UI_TOAST_QUEUE_LEN);
    strncpy(toast->q[tail].message, message ? message : "", sizeof(toast->q[tail].message) - 1);
    toast->q[tail].message[sizeof(toast->q[tail].message) - 1] = '\0';
    toast->q[tail].duration_ms = duration_ms;
    toast->count = (uint8_t)(toast->count + 1U);
}

static int ui_toast_queue_pop(UiToast *toast, UiToastItem *out_item)
{
    if (toast == NULL || toast->count == 0) {
        return 0;
    }
    if (out_item != NULL) {
        *out_item = toast->q[toast->head];
    }
    toast->head = (uint8_t)((toast->head + 1U) % UI_TOAST_QUEUE_LEN);
    toast->count = (uint8_t)(toast->count - 1U);
    return 1;
}

static void ui_toast_tick(UiScene *scene, UiToast *toast, int64_t now_us, UiDirty *dirty)
{
    if (scene == NULL || toast == NULL || !toast->active) {
        return;
    }
    if (now_us < toast->expires_us) {
        return;
    }

    UiToastItem next;
    if (ui_toast_queue_pop(toast, &next)) {
        ui_toast_show(scene, toast, toast->root, next.message, next.duration_ms, dirty);
        return;
    }

    ui_toast_hide(scene, toast, dirty);
}

static void ui_toast_enqueue(UiScene *scene, UiToast *toast, const char *root, const char *message, uint32_t duration_ms, UiDirty *dirty)
{
    if (scene == NULL || toast == NULL) {
        return;
    }
    if (root == NULL || *root == '\0') {
        root = "toast";
    }
    if (message == NULL) {
        message = "";
    }

    if (toast->active && toast->root[0] != '\0' && strcmp(toast->root, root) != 0) {
        ui_toast_hide(scene, toast, dirty);
    }
    if (!toast->active) {
        ui_toast_show(scene, toast, root, message, duration_ms, dirty);
        return;
    }

    ui_toast_queue_push(toast, message, duration_ms);
}

static void ui_handle_ui_cmd(
    UiScene *scene,
    const msg_t *m,
    int *focus,
    UiEdit *edit,
    UiModal *modal,
    UiToast *toast,
    UiDirty *dirty
)
{
    if (scene == NULL || m == NULL) {
        return;
    }

    ui_cmd_kind_t kind = (ui_cmd_kind_t)m->u.ui_cmd.kind;
    const char *id = m->u.ui_cmd.id;

    switch (kind) {
        case UI_CMD_SET_TEXT: {
            int idx = ui_scene_find_by_id(scene, id);
            if (idx >= 0) {
                ui_scene_set_text(scene, idx, m->u.ui_cmd.text);
                int x, y, w, h;
                ui_widget_rect(scene, idx, &x, &y, &w, &h);
                ui_dirty_add(dirty, x, y, w, h);
            }
            break;
        }
        case UI_CMD_SET_VISIBLE:
        case UI_CMD_SET_ENABLED:
        case UI_CMD_SET_STYLE:
        case UI_CMD_SET_VALUE:
        case UI_CMD_SET_CHECKED: {
            int idx = ui_scene_find_by_id(scene, id);
            UiWidget *w = ui_scene_widget_mut(scene, idx);
            if (w == NULL) {
                break;
            }

            uint8_t was_focusable = ui_nav_is_focusable(w) ? 1 : 0;
            switch (kind) {
                case UI_CMD_SET_VISIBLE:
                    w->visible = (m->u.ui_cmd.value != 0) ? 1 : 0;
                    break;
                case UI_CMD_SET_ENABLED:
                    w->enabled = (m->u.ui_cmd.value != 0) ? 1 : 0;
                    break;
                case UI_CMD_SET_STYLE:
                    w->style = (uint8_t)m->u.ui_cmd.value;
                    break;
                case UI_CMD_SET_VALUE:
                    w->value = (int16_t)m->u.ui_cmd.value;
                    break;
                case UI_CMD_SET_CHECKED:
                    w->checked = (m->u.ui_cmd.value != 0) ? 1 : 0;
                    break;
                default:
                    break;
            }

            int x, y, ww, hh;
            ui_widget_rect(scene, idx, &x, &y, &ww, &hh);
            ui_dirty_add(dirty, x, y, ww, hh);

            if (focus != NULL && idx == *focus) {
                uint8_t now_focusable = ui_nav_is_focusable(w) ? 1 : 0;
                if (was_focusable && !now_focusable) {
                    if (edit != NULL) {
                        ui_edit_exit(scene, edit, dirty);
                    }
                    *focus = ui_nav_first_focus(scene);
                    (void)ui_components_sync_active_from_focus(scene, *focus, ui_dirty_add_adapter, dirty);
                    ui_listmodel_sync_from_focus(scene, &s_listmodels, *focus, dirty);
                    ui_dirty_full(dirty);
                }
            }
            break;
        }
        case UI_CMD_SET_PREFIX_VISIBLE: {
            bool changed = ui_components_set_prefix_visible(scene, id, (m->u.ui_cmd.value != 0), ui_dirty_add_adapter, dirty);
            if (changed) {
                if (focus != NULL) {
                    UiWidget *fw = ui_scene_widget_mut(scene, *focus);
                    if (fw != NULL && !ui_nav_is_focusable(fw)) {
                        if (edit != NULL) {
                            ui_edit_exit(scene, edit, dirty);
                        }
                        *focus = ui_nav_first_focus(scene);
                        (void)ui_components_sync_active_from_focus(scene, *focus, ui_dirty_add_adapter, dirty);
                        ui_listmodel_sync_from_focus(scene, &s_listmodels, *focus, dirty);
                        ui_dirty_full(dirty);
                    }
                }
            }
            break;
        }
        case UI_CMD_MENU_SET_ACTIVE:
            (void)ui_components_menu_set_active(scene, id, (int)m->u.ui_cmd.value, ui_dirty_add_adapter, dirty);
            break;
        case UI_CMD_LIST_SET_ACTIVE:
            (void)ui_components_list_set_active(scene, id, (int)m->u.ui_cmd.value, ui_dirty_add_adapter, dirty);
            break;
        case UI_CMD_TABS_SET_ACTIVE:
            (void)ui_components_tabs_set_active(scene, id, (int)m->u.ui_cmd.value, ui_dirty_add_adapter, dirty);
            break;
        case UI_CMD_LISTMODEL_SET_LEN: {
            UiListModel *lm = ui_listmodels_get(&s_listmodels, id, true);
            if (lm != NULL) {
                ui_listmodel_set_len(lm, (int)m->u.ui_cmd.value);
                ui_listmodel_apply_to_scene(scene, lm, dirty);

                if (focus != NULL) {
                    UiWidget *fw = ui_scene_widget_mut(scene, *focus);
                    if (fw != NULL && !ui_nav_is_focusable(fw)) {
                        if (edit != NULL) {
                            ui_edit_exit(scene, edit, dirty);
                        }
                        *focus = ui_nav_first_focus(scene);
                        (void)ui_components_sync_active_from_focus(scene, *focus, ui_dirty_add_adapter, dirty);
                        ui_dirty_full(dirty);
                    }
                }
            }
            break;
        }
        case UI_CMD_LISTMODEL_SET_ITEM: {
            UiListModel *lm = ui_listmodels_get(&s_listmodels, id, true);
            if (lm != NULL) {
                char label[UI_LISTMODEL_LABEL_LEN];
                char value[UI_LISTMODEL_VALUE_LEN];
                ui_listmodel_parse_item_text(m->u.ui_cmd.text, label, (int)sizeof(label), value, (int)sizeof(value));
                ui_listmodel_set_item(lm, (int)m->u.ui_cmd.value, label, value);
                ui_listmodel_apply_to_scene(scene, lm, dirty);
            }
            break;
        }
        case UI_CMD_LISTMODEL_SET_ACTIVE: {
            UiListModel *lm = ui_listmodels_get(&s_listmodels, id, true);
            if (lm != NULL) {
                int visible = ui_scene_count_item_slots(scene, id);
                if (visible <= 0) {
                    visible = 1;
                }
                (void)ui_listmodel_set_active(lm, (int)m->u.ui_cmd.value, visible);
                ui_listmodel_apply_to_scene(scene, lm, dirty);

                if (edit == NULL || edit->kind == UI_EDIT_NONE) {
                    int active_slot = ui_listmodel_active_slot(lm);
                    char item_id[48];
                    snprintf(item_id, sizeof(item_id), "%s.item%d", id, active_slot);
                    int nf = ui_scene_find_by_id(scene, item_id);

                    int focus_in_root = 0;
                    if (focus != NULL && *focus >= 0 && (uint16_t)*focus < scene->widget_count) {
                        const UiWidget *fw = &scene->widgets[(uint16_t)*focus];
                        char froot[32];
                        int fslot = 0;
                        if (fw->id != NULL &&
                            ui_parse_item_root_slot(fw->id, froot, sizeof(froot), &fslot) &&
                            strcmp(froot, id) == 0) {
                            focus_in_root = 1;
                        }
                    }

                    if (focus_in_root && focus != NULL && nf >= 0 && nf != *focus) {
                        int x, y, w, h;
                        ui_widget_rect(scene, *focus, &x, &y, &w, &h);
                        ui_dirty_add(dirty, x, y, w, h);
                        ui_widget_rect(scene, nf, &x, &y, &w, &h);
                        ui_dirty_add(dirty, x, y, w, h);
                        *focus = nf;
                    }
                }
            }
            break;
        }
        case UI_CMD_DIALOG_SHOW:
            ui_modal_show(scene, modal, id, focus, edit, dirty);
            break;
        case UI_CMD_DIALOG_HIDE:
            if (modal != NULL && modal->active) {
                if (id[0] == '\0' || strcmp(id, modal->root) == 0) {
                    ui_modal_hide(scene, modal, focus, edit, dirty);
                }
            }
            break;
        case UI_CMD_TOAST_ENQUEUE:
            ui_toast_enqueue(scene, toast, id, m->u.ui_cmd.text, (uint32_t)m->u.ui_cmd.value, dirty);
            break;
        case UI_CMD_TOAST_HIDE:
            if (toast != NULL && toast->active) {
                if (id[0] == '\0' || strcmp(id, toast->root) == 0) {
                    ui_toast_hide(scene, toast, dirty);
                }
            }
            break;
        default:
            break;
    }
}

static void ui_task(void *arg)
{
    (void)arg;

    store_conf_t conf;
    esp_err_t conf_err = store_get_conf(&conf);
    if (conf_err == ESP_OK) {
        esp_err_t coerr = ssd1363_set_col_offset_units(conf.display_col_offset);
        if (coerr != ESP_OK) {
            ESP_LOGW(TAG, "ssd1363_set_col_offset_units failed: %s", esp_err_to_name(coerr));
        }
    }

    esp_err_t err = ssd1363_init_panel();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ssd1363_init_panel failed: %d", (int)err);
    }
    if (conf_err == ESP_OK) {
        esp_err_t cerr = ssd1363_set_contrast(conf.display_contrast);
        if (cerr != ESP_OK) {
            ESP_LOGW(TAG, "ssd1363_set_contrast failed: %s", esp_err_to_name(cerr));
        }
        cerr = ssd1363_invert_display(conf.display_invert != 0);
        if (cerr != ESP_OK) {
            ESP_LOGW(TAG, "ssd1363_invert_display failed: %s", esp_err_to_name(cerr));
        }
    }

    enum { W = DISPLAY_WIDTH, H = DISPLAY_HEIGHT };
    static uint8_t fb[UI_SWBUF_BYTES(W, H)];
    UiSwBuf sw;
    ui_swbuf_init(&sw, fb, W, H);

    UiDrawOps ops;
    ui_swbuf_make_ops(&sw, &ops);

    QueueHandle_t q = bus_make_queue(16);
    if (q != NULL) {
        bus_subscribe(TOP_INPUT_BTN, q);
        bus_subscribe(TOP_METRICS_RET, q);
        bus_subscribe(TOP_UI_CMD, q);
    }

    if (!ui_scene_clone(&UI_SCENE_DEMO, &s_scene, s_widgets, (int)UI_MAX_WIDGETS)) {
        ESP_LOGE(TAG, "ui_scene_clone failed");
        vTaskDelete(NULL);
    }
    UiScene *scene = &s_scene;
    ui_listmodels_init(&s_listmodels);

    /* Capture original texts for runtime overrides (bindings, status bar, etc.). */
    for (int i = 0; i < (int)scene->widget_count && i < UI_MAX_WIDGETS; ++i) {
        s_text_original[i] = scene->widgets[(uint16_t)i].text;
        s_text_override[i][0] = '\0';
    }
    for (int i = 0; i < (int)scene->widget_count && i < UI_MAX_WIDGETS; ++i) {
        (void)ui_update_bound_text(scene, i);
    }

    /* Hide overlay-style components by default (shown via UI commands). */
    (void)ui_components_set_prefix_visible(scene, "toast", false, NULL, NULL);
    (void)ui_components_set_prefix_visible(scene, "modal", false, NULL, NULL);
    (void)ui_components_set_prefix_visible(scene, "dialog", false, NULL, NULL);
    (void)ui_components_set_prefix_visible(scene, "dialog_confirm", false, NULL, NULL);
    (void)ui_components_set_prefix_visible(scene, "notification", false, NULL, NULL);

    int focus = ui_nav_first_focus(scene);
    (void)ui_components_sync_active_from_focus(scene, focus, NULL, NULL);
    int flash = 0;
    UiEdit edit;
    memset(&edit, 0, sizeof(edit));
    edit.kind = UI_EDIT_NONE;
    edit.idx = -1;

    UiModal modal;
    memset(&modal, 0, sizeof(modal));
    ui_modal_reset(&modal);

    UiToast toast;
    memset(&toast, 0, sizeof(toast));
    ui_toast_reset(&toast);
    UiDirty dirty;
    ui_dirty_clear(&dirty);
    ui_dirty_full(&dirty);

    /* Perf aggregation (very cheap; logs at INFO occasionally). */
    struct {
        uint32_t frames;
        uint64_t bytes;
        int64_t us_accum;
    } perf = {0};

    for (;;) {
        msg_t m;
        int got = 0;
        TickType_t timeout;

        timeout = portMAX_DELAY;
        if (flash > 0) {
            timeout = pdMS_TO_TICKS(50);
        }
        if (toast.active) {
            int64_t now_us = esp_timer_get_time();
            int64_t rem_us = toast.expires_us - now_us;
            if (rem_us < 0) {
                rem_us = 0;
            }
            uint32_t rem_ms = (uint32_t)((rem_us + 999) / 1000);
            TickType_t toast_ticks = pdMS_TO_TICKS(rem_ms);
            if (toast_ticks < timeout) {
                timeout = toast_ticks;
            }
        }
        if (dirty.dirty) {
            timeout = 0;
        }

        if (q != NULL) {
            got = (xQueueReceive(q, &m, timeout) == pdTRUE) ? 1 : 0;
        } else {
            vTaskDelay(pdMS_TO_TICKS(50));
        }

        /* Timeout tick: animate the flash overlay. */
        if (!got && flash > 0) {
            flash -= 1;
            ui_dirty_add(&dirty, 0, 0, 6, 6);
        }

        if (got && m.topic == TOP_METRICS_RET) {
            ui_update_status_bar(scene, m.u.metrics.free_heap, m.u.metrics.min_free_heap, &dirty);
        }

        if (got && m.topic == TOP_UI_CMD) {
            ui_handle_ui_cmd(scene, &m, &focus, &edit, &modal, &toast, &dirty);
        }

        if (got && m.topic == TOP_INPUT_BTN && m.u.btn.pressed) {
            const uint8_t id = m.u.btn.id;

            if (edit.kind != UI_EDIT_NONE) {
                int delta = 0;
                switch (id) {
                    case INPUT_ID_UP:
                        delta = -1;
                        break;
                    case INPUT_ID_DOWN:
                        delta = 1;
                        break;
                    case INPUT_ID_LEFT:
                        delta = -5;
                        break;
                    case INPUT_ID_RIGHT:
                        delta = 5;
                        break;
                    case INPUT_ID_ENC_CCW:
                    case INPUT_ID_ENC2_CCW:
                    case INPUT_ID_ENC3_CCW:
                    case INPUT_ID_ENC4_CCW:
                    case INPUT_ID_ENC5_CCW:
                        delta = -1;
                        break;
                    case INPUT_ID_ENC_CW:
                    case INPUT_ID_ENC2_CW:
                    case INPUT_ID_ENC3_CW:
                    case INPUT_ID_ENC4_CW:
                    case INPUT_ID_ENC5_CW:
                        delta = 1;
                        break;
                    case INPUT_ID_A:
                    case INPUT_ID_ENC_PRESS:
                    case INPUT_ID_ENC2_PRESS:
                    case INPUT_ID_ENC3_PRESS:
                    case INPUT_ID_ENC4_PRESS:
                    case INPUT_ID_ENC5_PRESS:
                    case INPUT_ID_B:
                    case INPUT_ID_ENC_HOLD:
                    case INPUT_ID_ENC2_HOLD:
                    case INPUT_ID_ENC3_HOLD:
                    case INPUT_ID_ENC4_HOLD:
                    case INPUT_ID_ENC5_HOLD: {
                        ui_edit_exit(scene, &edit, &dirty);
                        break;
                    }
                    default:
                        break;
                }
                if (delta != 0 && edit.idx >= 0) {
                    if (edit.kind == UI_EDIT_SLIDER) {
                        ui_adjust_slider(scene, edit.idx, delta, &dirty);
                    } else if (edit.kind == UI_EDIT_BIND_INT) {
                        int cur = 0;
                        if (ui_bind_get_int(edit.meta.bind_key, &cur)) {
                            int step = edit.meta.has_step ? edit.meta.step : 1;
                            int v = cur + delta * step;
                            if (edit.meta.has_min && v < edit.meta.min) v = edit.meta.min;
                            if (edit.meta.has_max && v > edit.meta.max) v = edit.meta.max;
                            if (v != cur) {
                                (void)ui_bind_set_int(edit.meta.bind_key, v);
                                if (ui_update_bound_text(scene, edit.idx)) {
                                    int x, y, ww, hh;
                                    ui_widget_rect(scene, edit.idx, &x, &y, &ww, &hh);
                                    ui_dirty_add(&dirty, x, y, ww, hh);
                                }
                            }
                        }
                    } else if (edit.kind == UI_EDIT_BIND_ENUM) {
                        int cur = 0;
                        int cnt = ui_meta_values_count(edit.meta.values);
                        if (cnt > 0 && ui_bind_get_int(edit.meta.bind_key, &cur)) {
                            int next = cur + delta;
                            while (next < 0) next += cnt;
                            while (next >= cnt) next -= cnt;
                            if (next != cur) {
                                (void)ui_bind_set_int(edit.meta.bind_key, next);
                                if (ui_update_bound_text(scene, edit.idx)) {
                                    int x, y, ww, hh;
                                    ui_widget_rect(scene, edit.idx, &x, &y, &ww, &hh);
                                    ui_dirty_add(&dirty, x, y, ww, hh);
                                }
                            }
                        }
                    }
                }
            } else {
                int old_focus = focus;

                int handled = 0;
                int list_delta = 0;
                switch (id) {
                    case INPUT_ID_UP:
                    case INPUT_ID_ENC_CCW:
                    case INPUT_ID_ENC2_CCW:
                    case INPUT_ID_ENC3_CCW:
                    case INPUT_ID_ENC4_CCW:
                    case INPUT_ID_ENC5_CCW:
                        list_delta = -1;
                        break;
                    case INPUT_ID_DOWN:
                    case INPUT_ID_ENC_CW:
                    case INPUT_ID_ENC2_CW:
                    case INPUT_ID_ENC3_CW:
                    case INPUT_ID_ENC4_CW:
                    case INPUT_ID_ENC5_CW:
                        list_delta = 1;
                        break;
                    default:
                        break;
                }

                if (list_delta != 0 && focus >= 0 && (uint16_t)focus < scene->widget_count) {
                    const UiWidget *fw = &scene->widgets[(uint16_t)focus];
                    char root[32];
                    int slot = 0;
                    if (fw->id != NULL && ui_parse_item_root_slot(fw->id, root, sizeof(root), &slot)) {
                        UiListModel *lm = ui_listmodels_get(&s_listmodels, root, false);
                        if (lm != NULL && lm->count > 0) {
                            int visible = ui_scene_count_item_slots(scene, root);
                            if (visible > 0) {
                                int abs = (int)fw->value;
                                if (abs < 0 || abs >= (int)lm->count) {
                                    abs = (int)lm->offset + slot;
                                }
                                (void)ui_listmodel_set_active(lm, abs, visible);
                                if (ui_listmodel_move_active(lm, list_delta, visible)) {
                                    ui_listmodel_apply_to_scene(scene, lm, &dirty);

                                    int active_slot = ui_listmodel_active_slot(lm);
                                    char item_id[48];
                                    snprintf(item_id, sizeof(item_id), "%s.item%d", root, active_slot);
                                    int nf = ui_scene_find_by_id(scene, item_id);
                                    if (nf >= 0) {
                                        focus = nf;
                                    }
                                    handled = 1;
                                }
                            }
                        }
                    }
                }

                if (!handled) {
                    if (modal.active) {
                        switch (id) {
                            case INPUT_ID_UP:
                                focus = ui_nav_move_focus_in_rect(scene, focus, UI_NAV_UP, modal.x, modal.y, modal.w, modal.h);
                                break;
                            case INPUT_ID_DOWN:
                                focus = ui_nav_move_focus_in_rect(scene, focus, UI_NAV_DOWN, modal.x, modal.y, modal.w, modal.h);
                                break;
                            case INPUT_ID_LEFT:
                                focus = ui_nav_move_focus_in_rect(scene, focus, UI_NAV_LEFT, modal.x, modal.y, modal.w, modal.h);
                                break;
                            case INPUT_ID_RIGHT:
                                focus = ui_nav_move_focus_in_rect(scene, focus, UI_NAV_RIGHT, modal.x, modal.y, modal.w, modal.h);
                                break;
                            case INPUT_ID_ENC_CCW:
                            case INPUT_ID_ENC2_CCW:
                            case INPUT_ID_ENC3_CCW:
                            case INPUT_ID_ENC4_CCW:
                            case INPUT_ID_ENC5_CCW:
                                focus = ui_nav_move_focus_in_rect(scene, focus, UI_NAV_UP, modal.x, modal.y, modal.w, modal.h);
                                break;
                            case INPUT_ID_ENC_CW:
                            case INPUT_ID_ENC2_CW:
                            case INPUT_ID_ENC3_CW:
                            case INPUT_ID_ENC4_CW:
                            case INPUT_ID_ENC5_CW:
                                focus = ui_nav_move_focus_in_rect(scene, focus, UI_NAV_DOWN, modal.x, modal.y, modal.w, modal.h);
                                break;
                            case INPUT_ID_A:
                            case INPUT_ID_ENC_PRESS:
                            case INPUT_ID_ENC2_PRESS:
                            case INPUT_ID_ENC3_PRESS:
                            case INPUT_ID_ENC4_PRESS:
                            case INPUT_ID_ENC5_PRESS: {
                                UiActivateResult act = ui_activate_widget(scene, focus, &edit, &flash, &dirty);
                                if (act == UI_ACT_ACTION_PUBLISHED) {
                                    ui_modal_hide(scene, &modal, &focus, &edit, &dirty);
                                }
                                break;
                            }
                            case INPUT_ID_B:
                            case INPUT_ID_ENC_HOLD:
                            case INPUT_ID_ENC2_HOLD:
                            case INPUT_ID_ENC3_HOLD:
                            case INPUT_ID_ENC4_HOLD:
                            case INPUT_ID_ENC5_HOLD:
                                flash = 0;
                                ui_modal_cancel(scene, &modal, &focus, &edit, &dirty);
                                break;
                            default:
                                break;
                        }
                    } else {
                        switch (id) {
                            case INPUT_ID_UP:
                                focus = ui_nav_move_focus(scene, focus, UI_NAV_UP);
                                break;
                            case INPUT_ID_DOWN:
                                focus = ui_nav_move_focus(scene, focus, UI_NAV_DOWN);
                                break;
                            case INPUT_ID_LEFT:
                                focus = ui_nav_move_focus(scene, focus, UI_NAV_LEFT);
                                break;
                            case INPUT_ID_RIGHT:
                                focus = ui_nav_move_focus(scene, focus, UI_NAV_RIGHT);
                                break;
                            case INPUT_ID_ENC_CCW:
                            case INPUT_ID_ENC2_CCW:
                            case INPUT_ID_ENC3_CCW:
                            case INPUT_ID_ENC4_CCW:
                            case INPUT_ID_ENC5_CCW:
                                focus = ui_nav_move_focus(scene, focus, UI_NAV_UP);
                                break;
                            case INPUT_ID_ENC_CW:
                            case INPUT_ID_ENC2_CW:
                            case INPUT_ID_ENC3_CW:
                            case INPUT_ID_ENC4_CW:
                            case INPUT_ID_ENC5_CW:
                                focus = ui_nav_move_focus(scene, focus, UI_NAV_DOWN);
                                break;
                            case INPUT_ID_A:
                            case INPUT_ID_ENC_PRESS:
                            case INPUT_ID_ENC2_PRESS:
                            case INPUT_ID_ENC3_PRESS:
                            case INPUT_ID_ENC4_PRESS:
                            case INPUT_ID_ENC5_PRESS:
                                (void)ui_activate_widget(scene, focus, &edit, &flash, &dirty);
                                break;
                            case INPUT_ID_B:
                            case INPUT_ID_ENC_HOLD:
                            case INPUT_ID_ENC2_HOLD:
                            case INPUT_ID_ENC3_HOLD:
                            case INPUT_ID_ENC4_HOLD:
                            case INPUT_ID_ENC5_HOLD:
                                flash = 0;
                                ui_dirty_add(&dirty, 0, 0, 6, 6);
                                break;
                            default:
                                break;
                        }
                    }
                }

                if (focus != old_focus) {
                    int x, y, w, h;
                    ui_widget_rect(scene, old_focus, &x, &y, &w, &h);
                    ui_dirty_add(&dirty, x, y, w, h);
                    ui_widget_rect(scene, focus, &x, &y, &w, &h);
                    ui_dirty_add(&dirty, x, y, w, h);
                    (void)ui_components_sync_active_from_focus(scene, focus, ui_dirty_add_adapter, &dirty);
                    ui_listmodel_sync_from_focus(scene, &s_listmodels, focus, &dirty);
                }
            }
        }

        if (toast.active) {
            ui_toast_tick(scene, &toast, esp_timer_get_time(), &dirty);
        }

        if (!dirty.dirty) {
            continue;
        }

        /* Render and flush only the union dirty region. */
        ui_swbuf_clear(&sw, 0);
        ui_render_scene(scene, &ops);
        if (flash > 0) {
#if DISPLAY_COLOR_BITS == 4
            ui_swbuf_fill_rect(&sw, 0, 0, 6, 6, 4);
#else
            ui_swbuf_fill_rect(&sw, 0, 0, 6, 6, 1);
#endif
        }
        ui_draw_focus(&ops, scene, focus);

        ui_swbuf_clear_dirty(&sw);
        ui_swbuf_mark_dirty(&sw, dirty.x0, dirty.y0, dirty.x1 - dirty.x0, dirty.y1 - dirty.y0);

        size_t bytes_est = ui_estimate_flush_bytes(&sw);
        int64_t t0 = esp_timer_get_time();
        ui_swbuf_flush_dirty_auto_ssd1363(&sw);
        int64_t t1 = esp_timer_get_time();
        int64_t dt_us = t1 - t0;

        perf.frames += 1;
        perf.bytes += bytes_est;
        perf.us_accum += dt_us;
        if (perf.frames % 20U == 0U) {
            double ms = (double)perf.us_accum / 1000.0;
            double fps = (ms > 0.0) ? (1000.0 * (double)perf.frames / ms) : 0.0;
            double mbps = (ms > 0.0) ? ((double)perf.bytes / (ms * 1000.0)) : 0.0;
            ESP_LOGI(TAG, "Perf: %u frames, %.2f fps, %.2f MB/s, avg %.2f ms/flush",
                     (unsigned)perf.frames,
                     fps,
                     mbps,
                     (perf.frames > 0U) ? (ms / (double)perf.frames) : 0.0);
            perf.frames = 0;
            perf.bytes = 0;
            perf.us_accum = 0;
        }

        ui_swbuf_clear_dirty(&sw);
        ui_dirty_clear(&dirty);
    }
}

void ui_start(void)
{
    if (s_ui_task != NULL) {
        return;
    }

    if (xTaskCreatePinnedToCore(ui_task, "ui", 6144, NULL, 6, &s_ui_task, 1) != pdPASS) {
        ESP_LOGE(TAG, "xTaskCreatePinnedToCore(ui) failed");
        s_ui_task = NULL;
    }
}
