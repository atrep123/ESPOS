#pragma once

#include <stddef.h>
#include "ui_scene.h"

/*
 * Pure scene query and manipulation helpers.
 * No FreeRTOS, no globals, no display hardware — only UiScene/UiWidget.
 */

/* Get bounding rectangle of widget at index idx (safe for NULL/OOB). */
void ui_scene_widget_rect(const UiScene *scene, int idx,
                          int *x, int *y, int *w, int *h);

/* Linear search for widget by ID string.  Returns index or -1. */
int ui_scene_find_by_id(const UiScene *scene, const char *id);

/* Count sequential item slots named "<root>.item0", "<root>.item1", … */
int ui_scene_count_item_slots(const UiScene *scene, const char *root);

/* Find bounding rect of a modal dialog/panel by probing
 * "<root>.dialog" then "<root>.panel".  Returns 1 on success. */
int ui_scene_modal_find_rect(const UiScene *scene, const char *root,
                             int *x, int *y, int *w, int *h);

/* Deep-copy a scene into caller-provided widget buffer.
 * Truncates to max_widgets if the source scene is larger.
 * Returns 1 on success, 0 on bad arguments. */
int ui_scene_clone(const UiScene *src, UiScene *dst,
                   UiWidget *dst_widgets, int max_widgets);
