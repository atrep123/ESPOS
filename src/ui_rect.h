#pragma once

#include "ui_scene.h"

/*
 * Pure rectangle geometry helpers for widget layout and navigation.
 * No FreeRTOS, display driver, or msgbus dependencies.
 */

typedef struct {
    int x;
    int y;
    int w;
    int h;
} UiRect;

/* Build a rect from a widget's position and size. */
UiRect ui_rect_from_widget(const UiWidget *w);

int ui_rect_center_x(UiRect r);
int ui_rect_center_y(UiRect r);
int ui_rect_right(UiRect r);
int ui_rect_bottom(UiRect r);

/* Returns the overlap length between two 1-D intervals [a0,a1) and [b0,b1).
 * Returns 0 if they don't overlap. */
int ui_rect_overlap(int a0, int a1, int b0, int b1);

/* Returns 1 if point (x,y) is inside rect (exclusive right/bottom edge). */
int ui_rect_contains_point(UiRect r, int x, int y);
