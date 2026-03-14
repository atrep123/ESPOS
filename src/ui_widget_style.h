#pragma once

#include <stdint.h>
#include "ui_scene.h"

/*
 * Pure widget state queries and style computation.
 * Shared by ui_nav.c and ui_render.c — eliminates duplicate definitions.
 * No FreeRTOS, display driver, or msgbus dependencies.
 */

/* ── Widget state queries ── */

/* Returns 1 if any extended field (fg/bg/border_style/style/visible/enabled
 * etc.) is set to a non-zero value, meaning the widget uses extended styling. */
int ui_widget_has_extended(const UiWidget *w);

/* Returns 1 if the widget should be drawn (defaults to visible if no
 * extended fields are set). */
int ui_widget_is_visible(const UiWidget *w);

/* Returns 1 if the widget is interactive (defaults to enabled if no
 * extended fields are set). */
int ui_widget_is_enabled(const UiWidget *w);

/* ── Color computation ── */

/* Compute resolved fg/bg/border/muted/fill colors for a widget,
 * given the theme's default text and background colors.
 * Any output pointer may be NULL if that color is not needed.
 * Uses ui_gray4_add from ui_render_text.h for palette adjustments. */
void ui_widget_colors(const UiWidget *w,
                      uint8_t col_text, uint8_t col_bg,
                      uint8_t *fg, uint8_t *bg,
                      uint8_t *border, uint8_t *muted, uint8_t *fill);
