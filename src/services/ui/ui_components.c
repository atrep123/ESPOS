#include "ui_components.h"

#include <stddef.h>
#include <string.h>
#include <stdio.h>

#include "ui_helpers.h"

static int ui_id_starts_with(const char *id, const char *prefix)
{
    if (id == NULL || prefix == NULL) {
        return 0;
    }
    size_t n = strlen(prefix);
    if (n == 0) {
        return 0;
    }
    return (strncmp(id, prefix, n) == 0) ? 1 : 0;
}

static bool ui_set_active_prefix_index(
    UiScene *scene,
    const char *root,
    const char *role_prefix,
    int active_index,
    int role_index_bias,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
)
{
    if (scene == NULL || scene->widgets == NULL) {
        return false;
    }
    if (root == NULL || *root == '\0') {
        return false;
    }
    if (role_prefix == NULL || *role_prefix == '\0') {
        return false;
    }

    char prefix[48];
    snprintf(prefix, sizeof(prefix), "%s.%s", root, role_prefix);
    size_t prefix_len = strlen(prefix);

    bool any = false;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        UiWidget *w = (UiWidget *)&scene->widgets[i];
        if (w->id == NULL) {
            continue;
        }
        if (!ui_id_starts_with(w->id, prefix)) {
            continue;
        }
        const char *suffix = w->id + prefix_len;
        int idx = 0;
        if (!ui_parse_uint_dec(suffix, &idx)) {
            continue;
        }
        idx += role_index_bias;

        uint8_t before = w->style;
        if (idx == active_index) {
            w->style = (uint8_t)(w->style | UI_STYLE_HIGHLIGHT);
        } else {
            w->style = (uint8_t)(w->style & (uint8_t)~UI_STYLE_HIGHLIGHT);
        }
        if (w->style != before) {
            any = true;
            if (dirty_add != NULL) {
                dirty_add(dirty_ctx, (int)w->x, (int)w->y, (int)w->width, (int)w->height);
            }
        }
    }
    return any;
}

bool ui_components_menu_set_active(
    UiScene *scene,
    const char *root,
    int active_index,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
)
{
    return ui_set_active_prefix_index(scene, root, "item", active_index, 0, dirty_add, dirty_ctx);
}

bool ui_components_list_set_active(
    UiScene *scene,
    const char *root,
    int active_index,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
)
{
    return ui_set_active_prefix_index(scene, root, "item", active_index, 0, dirty_add, dirty_ctx);
}

bool ui_components_tabs_set_active(
    UiScene *scene,
    const char *root,
    int active_index,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
)
{
    /* Tabs are named tab1/tab2/... (1-based), map to 0-based active_index. */
    return ui_set_active_prefix_index(scene, root, "tab", active_index, -1, dirty_add, dirty_ctx);
}

bool ui_components_set_prefix_visible(
    UiScene *scene,
    const char *root,
    bool visible,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
)
{
    if (scene == NULL || scene->widgets == NULL) {
        return false;
    }
    if (root == NULL || *root == '\0') {
        return false;
    }

    char prefix[48];
    snprintf(prefix, sizeof(prefix), "%s.", root);

    bool any = false;
    uint8_t desired = visible ? 1 : 0;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        UiWidget *w = (UiWidget *)&scene->widgets[i];
        if (w->id == NULL) {
            continue;
        }
        if (!ui_id_starts_with(w->id, prefix)) {
            continue;
        }
        if (w->visible == desired) {
            continue;
        }
        w->visible = desired;
        any = true;
        if (dirty_add != NULL) {
            dirty_add(dirty_ctx, (int)w->x, (int)w->y, (int)w->width, (int)w->height);
        }
    }
    return any;
}

bool ui_components_sync_active_from_focus(
    UiScene *scene,
    int focus_idx,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
)
{
    if (scene == NULL || scene->widgets == NULL) {
        return false;
    }
    if (focus_idx < 0 || (uint16_t)focus_idx >= scene->widget_count) {
        return false;
    }

    const UiWidget *w = &scene->widgets[(uint16_t)focus_idx];
    if (w->id == NULL || w->id[0] == '\0') {
        return false;
    }

    const char *dot = strchr(w->id, '.');
    if (dot == NULL || dot == w->id || dot[1] == '\0') {
        return false;
    }

    char root[32];
    size_t root_len = (size_t)(dot - w->id);
    if (root_len >= sizeof(root)) {
        root_len = sizeof(root) - 1;
    }
    memcpy(root, w->id, root_len);
    root[root_len] = '\0';

    const char *role = dot + 1;
    if (ui_id_starts_with(role, "item")) {
        int idx = 0;
        if (!ui_parse_uint_dec(role + 4, &idx)) {
            return false;
        }
        return ui_components_menu_set_active(scene, root, idx, dirty_add, dirty_ctx);
    }
    if (ui_id_starts_with(role, "tab")) {
        int tab_num = 0;
        if (!ui_parse_uint_dec(role + 3, &tab_num)) {
            return false;
        }
        if (tab_num <= 0) {
            return false;
        }
        return ui_components_tabs_set_active(scene, root, tab_num - 1, dirty_add, dirty_ctx);
    }
    return false;
}
