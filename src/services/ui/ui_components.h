#pragma once

#include <stdbool.h>

#include "ui_scene.h"

typedef void (*ui_components_dirty_add_fn_t)(void *ctx, int x, int y, int w, int h);

bool ui_components_menu_set_active(
    UiScene *scene,
    const char *root,
    int active_index,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
);

bool ui_components_list_set_active(
    UiScene *scene,
    const char *root,
    int active_index,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
);

bool ui_components_tabs_set_active(
    UiScene *scene,
    const char *root,
    int active_index,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
);

bool ui_components_set_prefix_visible(
    UiScene *scene,
    const char *root,
    bool visible,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
);

/* Component convenience: when focus moves to a component role (e.g. "menu.item2" or
 * "tabs.tab3"), automatically sync the component's active/highlighted element. */
bool ui_components_sync_active_from_focus(
    UiScene *scene,
    int focus_idx,
    ui_components_dirty_add_fn_t dirty_add,
    void *dirty_ctx
);
