#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "ui_scene.h"

typedef enum {
    UI_NAV_UP = 0,
    UI_NAV_DOWN = 1,
    UI_NAV_LEFT = 2,
    UI_NAV_RIGHT = 3,
} ui_nav_dir_t;

bool ui_nav_is_focusable(const UiWidget *w);

/* Return first focusable widget index (top-to-bottom, left-to-right), or -1. */
int ui_nav_first_focus(const UiScene *scene);

/* Cycle focus through focusable widgets (delta +/-1). Returns new index or -1. */
int ui_nav_cycle_focus(const UiScene *scene, int current_idx, int delta);

/* Move focus in a direction using geometry-based auto-navigation. */
int ui_nav_move_focus(const UiScene *scene, int current_idx, ui_nav_dir_t dir);

/* Modal focus-trap helpers: restrict focus candidates to a rectangle. */
int ui_nav_first_focus_in_rect(const UiScene *scene, int x, int y, int w, int h);
int ui_nav_move_focus_in_rect(const UiScene *scene, int current_idx, ui_nav_dir_t dir, int x, int y, int w, int h);
