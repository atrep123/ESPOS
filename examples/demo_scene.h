/*
 * Auto-generated UI Design Header
 * Source: demo_scene.json
 * Generated: 2025-11-16 22:13:50
 * DO NOT EDIT MANUALLY
 */

#ifndef DEMO_SCENE_H
#define DEMO_SCENE_H

#include "ui_render.h"


// Scene: Demo
// Size: 128x64, Widgets: 4

static const ui_widget_t demo_widgets[] = {
    { // Widget 0: label
        .type = UI_WIDGET_LABEL,
        .x = 0, .y = 0, .width = 128, .height = 10,
        .text = "Demo",
        .fg_color = UI_COLOR_CYAN, .bg_color = UI_COLOR_BLACK,
        .border = false, .border_style = UI_BORDER_SINGLE,
        .align = UI_ALIGN_CENTER, .valign = UI_VALIGN_MIDDLE,
        .visible = true, .enabled = true,
        .value = 0, .min_value = 0, .max_value = 100,
    },
    { // Widget 1: button
        .type = UI_WIDGET_BUTTON,
        .x = 39, .y = 16, .width = 50, .height = 12,
        .text = "Play",
        .fg_color = UI_COLOR_WHITE, .bg_color = UI_COLOR_BLACK,
        .border = true, .border_style = UI_BORDER_SINGLE,
        .align = UI_ALIGN_LEFT, .valign = UI_VALIGN_MIDDLE,
        .visible = true, .enabled = true,
        .value = 0, .min_value = 0, .max_value = 100,
    },
    { // Widget 2: gauge
        .type = UI_WIDGET_GAUGE,
        .x = 8, .y = 10, .width = 32, .height = 24,
        .text = "",
        .fg_color = UI_COLOR_WHITE, .bg_color = UI_COLOR_BLACK,
        .border = true, .border_style = UI_BORDER_SINGLE,
        .align = UI_ALIGN_LEFT, .valign = UI_VALIGN_MIDDLE,
        .visible = true, .enabled = true,
        .value = 70, .min_value = 0, .max_value = 100,
    },
    { // Widget 3: progressbar
        .type = UI_WIDGET_PROGRESSBAR,
        .x = 8, .y = 52, .width = 112, .height = 8,
        .text = "",
        .fg_color = UI_COLOR_WHITE, .bg_color = UI_COLOR_BLACK,
        .border = true, .border_style = UI_BORDER_SINGLE,
        .align = UI_ALIGN_LEFT, .valign = UI_VALIGN_MIDDLE,
        .visible = true, .enabled = true,
        .value = 40, .min_value = 0, .max_value = 100,
    }
};

static const ui_scene_t demo_scene = {
    .name = "Demo",
    .width = 128,
    .height = 64,
    .bg_color = UI_COLOR_BLACK,
    .widget_count = 4,
    .widgets = demo_widgets,
};

// Scene registry
static const ui_scene_t* all_scenes[] = {
    &demo_scene,
};

#define SCENE_COUNT 1

#endif // DEMO_SCENE_H
