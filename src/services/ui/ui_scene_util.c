#include "ui_scene_util.h"

#include <stdio.h>
#include <string.h>

#include "esp_log.h"

static const char *TAG = "ui_scene_util";

void ui_scene_widget_rect(const UiScene *scene, int idx,
                          int *x, int *y, int *w, int *h)
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

int ui_scene_find_by_id(const UiScene *scene, const char *id)
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

int ui_scene_count_item_slots(const UiScene *scene, const char *root)
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

int ui_scene_modal_find_rect(const UiScene *scene, const char *root,
                             int *x, int *y, int *w, int *h)
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
    ui_scene_widget_rect(scene, idx, &rx, &ry, &rw, &rh);
    if (rw <= 0 || rh <= 0) {
        return 0;
    }
    if (x) *x = rx;
    if (y) *y = ry;
    if (w) *w = rw;
    if (h) *h = rh;
    return 1;
}

/* Clone a scene into caller-owned buffers.  This is a SHALLOW copy:
 * string pointers (name, id, text, constraints_json, animations_csv)
 * alias the source — safe when src points to generated const data. */
int ui_scene_clone(const UiScene *src, UiScene *dst,
                   UiWidget *dst_widgets, int max_widgets)
{
    if (src == NULL || dst == NULL || dst_widgets == NULL || src->widgets == NULL) {
        return 0;
    }

    uint16_t count = src->widget_count;
    if (count > (uint16_t)max_widgets) {
        ESP_LOGW(TAG, "ui_scene_clone: truncating %u widgets to %d",
                 (unsigned)count, max_widgets);
        count = (uint16_t)max_widgets;
    }

    memcpy(dst_widgets, src->widgets, (size_t)count * sizeof(UiWidget));
    *dst = *src;
    dst->widget_count = count;
    dst->widgets = dst_widgets;
    return 1;
}
