#pragma once

#include <stdint.h>
#include "ui_scene.h"

/*
 * Pure UI state helpers extracted from ui.c for testability.
 * No FreeRTOS, display driver, or msgbus dependencies.
 */

/* ── Dirty-rectangle tracking ── */

typedef struct {
    int dirty;
    int x0, y0;
    int x1, y1; /* exclusive */
} UiDirty;

void ui_dirty_clear(UiDirty *d);

/* Merge region (x,y,w,h) into the accumulated dirty rect.
 * Clamps to (0,0)–(disp_w, disp_h). */
void ui_dirty_add(UiDirty *d, int x, int y, int w, int h,
                  int disp_w, int disp_h);

/* ── Null-safe string comparison ── */

/* Returns 1 when both strings are equal (NULL treated as ""). */
int ui_text_equals(const char *a, const char *b);

/* ── Pure widget operations ── */

/* Toggle a checkbox widget's checked state.
 * Returns 1 if toggled, 0 if w is NULL or not a checkbox. */
int ui_widget_toggle_checked(UiWidget *w);

/* Clamp w->value into [w->min_value, w->max_value] after adding delta.
 * Returns 1 if the value changed, 0 otherwise.
 * Only operates on UIW_SLIDER widgets. */
int ui_widget_clamp_value(UiWidget *w, int delta);
