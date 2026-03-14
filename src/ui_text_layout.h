#pragma once

#include <stdint.h>
#include "ui_render.h"  /* UiDrawOps */
#include "ui_scene.h"   /* UiAlign, UiVAlign, UiTextOverflow */

/*
 * Text layout and drawing into rectangular areas.
 * Pure functions that compute alignment/wrapping and delegate to UiDrawOps.
 * No scene state, no hardware dependencies.
 */

/* Draw a single line of text within a horizontal extent [x, x+w_px).
 * Fits/truncates with optional ellipsis, aligns left/center/right. */
void ui_draw_text_line_in_rect(
    const UiDrawOps *ops,
    int x, int y, int w_px,
    const char *text,
    uint8_t fg,
    uint8_t align,
    int use_ellipsis);

/* Draw a multi-line text block inside (x,y,w_px,h_px).
 * Handles overflow mode (ellipsis/wrap/clip/auto), vertical
 * alignment (top/middle/bottom), and line clamping. */
void ui_draw_text_block(
    const UiDrawOps *ops,
    int x, int y, int w_px, int h_px,
    const char *text,
    uint8_t fg,
    uint8_t align,
    uint8_t valign,
    uint8_t overflow,
    int max_lines);
