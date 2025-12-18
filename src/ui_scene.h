#pragma once

#include <stddef.h>
#include <stdint.h>

/* Shared UI scene schema used by:
 *  - generated designs (ui_design.*),
 *  - the renderer (ui_render.*),
 *  - navigation (ui_nav.*),
 *  - demos/sim.
 */

/* Widget type enumeration (keep values stable for exporter/runtime). */
typedef enum {
    UIW_LABEL = 0,
    UIW_BOX = 1,
    UIW_BUTTON = 2,
    UIW_GAUGE = 3,
    UIW_PROGRESSBAR = 4,
    UIW_CHECKBOX = 5,
    UIW_RADIOBUTTON = 6,
    UIW_SLIDER = 7,
    UIW_TEXTBOX = 8,
    UIW_PANEL = 9,
    UIW_ICON = 10,
    UIW_CHART = 11,
} UiWidgetType;

/* Border style (keep values stable; used by exporter/runtime). */
typedef enum {
    UI_BORDER_NONE = 0,
    UI_BORDER_SINGLE = 1,
    UI_BORDER_DOUBLE = 2,
    UI_BORDER_ROUNDED = 3,
    UI_BORDER_BOLD = 4,
    UI_BORDER_DASHED = 5,
} UiBorderStyle;

/* Text alignment in widget rect. */
typedef enum {
    UI_ALIGN_LEFT = 0,
    UI_ALIGN_CENTER = 1,
    UI_ALIGN_RIGHT = 2,
} UiAlign;

typedef enum {
    UI_VALIGN_TOP = 0,
    UI_VALIGN_MIDDLE = 1,
    UI_VALIGN_BOTTOM = 2,
} UiVAlign;

/* Text overflow behavior. */
typedef enum {
    UI_TEXT_OVERFLOW_ELLIPSIS = 0,
    UI_TEXT_OVERFLOW_WRAP = 1,
    UI_TEXT_OVERFLOW_CLIP = 2,
    UI_TEXT_OVERFLOW_AUTO = 3,
} UiTextOverflow;

enum {
    UI_STYLE_NONE = 0,
    UI_STYLE_INVERSE = 1 << 0,
    UI_STYLE_HIGHLIGHT = 1 << 1,
    UI_STYLE_BOLD = 1 << 2,
};

/* Widget structure (packed for embedded; exporter fills the styling fields). */
typedef struct {
    uint8_t  type;      /* UiWidgetType */
    uint16_t x, y;
    uint16_t width, height;
    uint8_t  border;
    uint8_t  checked;
    int16_t  value, min_value, max_value;
    const char *id;   /* optional stable widget identifier (e.g. "menu.item0") */
    const char *text;
    const char *constraints_json; /* optional constraints metadata */
    const char *animations_csv;   /* optional animations list */

    /* Extended styling/state */
    uint8_t  fg;            /* 0..15 (4bpp gray); 0/1 also OK for 1bpp */
    uint8_t  bg;            /* 0..15 */
    uint8_t  border_style;  /* UiBorderStyle */
    uint8_t  align;         /* UiAlign */
    uint8_t  valign;        /* UiVAlign */
    uint8_t  text_overflow; /* UiTextOverflow */
    uint8_t  max_lines;     /* 0 = auto/unlimited */
    uint8_t  style;         /* UI_STYLE_* bitset */
    uint8_t  visible;       /* 0/1 */
    uint8_t  enabled;       /* 0/1 */
} UiWidget;

/* Scene structure */
typedef struct {
    const char *name;
    uint16_t width, height;
    uint16_t widget_count;
    const UiWidget *widgets;
} UiScene;
