/* Auto-generated implementation for demo */
#include "ui_design.h"


/* String pool */
static const char str_0[] = "UI Demo";
static const char str_1[] = "OK";
static const char str_2[] = "Enable";

/* Widget definitions */
static const UiWidget widgets[] = {
    { // [0] label "UI Demo"
        .type = UIW_LABEL,
        .x = 0, .y = 0,
        .width = 124, .height = 10,
        .border = 0,
        .checked = 0,
        .value = 0, .min_value = 0, .max_value = 100,
        .text = str_0,
        .constraints_json = NULL,
        .animations_csv = NULL
    },
    { // [1] box ""
        .type = UIW_BOX,
        .x = 0, .y = 8,
        .width = 124, .height = 46,
        .border = 1,
        .checked = 0,
        .value = 0, .min_value = 0, .max_value = 100,
        .text = NULL,
        .constraints_json = NULL,
        .animations_csv = NULL
    },
    { // [2] button "OK"
        .type = UIW_BUTTON,
        .x = 8, .y = 16,
        .width = 40, .height = 12,
        .border = 1,
        .checked = 0,
        .value = 0, .min_value = 0, .max_value = 100,
        .text = str_1,
        .constraints_json = NULL,
        .animations_csv = NULL
    },
    { // [3] progressbar ""
        .type = UIW_PROGRESSBAR,
        .x = 8, .y = 32,
        .width = 108, .height = 8,
        .border = 1,
        .checked = 0,
        .value = 70, .min_value = 0, .max_value = 100,
        .text = NULL,
        .constraints_json = NULL,
        .animations_csv = NULL
    },
    { // [4] checkbox "Enable"
        .type = UIW_CHECKBOX,
        .x = 56, .y = 26,
        .width = 60, .height = 10,
        .border = 0,
        .checked = 1,
        .value = 0, .min_value = 0, .max_value = 100,
        .text = str_2,
        .constraints_json = NULL,
        .animations_csv = NULL
    },
};

/* Scene definition */
const UiScene ui_design = {
    .name = "demo",
    .width = 128,
    .height = 64,
    .widget_count = 5,
    .widgets = widgets
};