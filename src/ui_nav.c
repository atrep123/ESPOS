#include "ui_nav.h"

#include <stddef.h>

typedef struct {
    int x;
    int y;
    int w;
    int h;
} UiRect;

static int ui_widget_has_extended(const UiWidget *w)
{
    if (w == NULL) {
        return 0;
    }
    return (w->fg != 0) ||
           (w->bg != 0) ||
           (w->border_style != 0) ||
           (w->text_overflow != 0) ||
           (w->max_lines != 0) ||
           (w->style != 0) ||
           (w->visible != 0) ||
           (w->enabled != 0);
}

static int ui_widget_is_visible(const UiWidget *w)
{
    if (!ui_widget_has_extended(w)) {
        return 1;
    }
    return (w->visible != 0);
}

static int ui_widget_is_enabled(const UiWidget *w)
{
    if (!ui_widget_has_extended(w)) {
        return 1;
    }
    return (w->enabled != 0);
}

static UiRect ui_rect_from_widget(const UiWidget *w)
{
    UiRect r = {0, 0, 0, 0};
    if (!w) {
        return r;
    }
    r.x = (int)w->x;
    r.y = (int)w->y;
    r.w = (int)w->width;
    r.h = (int)w->height;
    return r;
}

static int ui_rect_center_x(UiRect r)
{
    return r.x + (r.w / 2);
}

static int ui_rect_center_y(UiRect r)
{
    return r.y + (r.h / 2);
}

static int ui_rect_right(UiRect r)
{
    return r.x + r.w;
}

static int ui_rect_bottom(UiRect r)
{
    return r.y + r.h;
}

static int ui_rect_overlap(int a0, int a1, int b0, int b1)
{
    int lo = (a0 > b0) ? a0 : b0;
    int hi = (a1 < b1) ? a1 : b1;
    int span = hi - lo;
    return (span > 0) ? span : 0;
}

bool ui_nav_is_focusable(const UiWidget *w)
{
    if (!w) {
        return false;
    }
    if (!ui_widget_is_visible(w) || !ui_widget_is_enabled(w)) {
        return false;
    }
    switch ((UiWidgetType)w->type) {
        case UIW_BUTTON:
        case UIW_CHECKBOX:
        case UIW_RADIOBUTTON:
        case UIW_SLIDER:
            return true;
        default:
            return false;
    }
}

static int ui_rect_contains_point(UiRect r, int x, int y)
{
    return (x >= r.x) && (y >= r.y) && (x < ui_rect_right(r)) && (y < ui_rect_bottom(r));
}

static int ui_nav_is_focusable_in_rect(const UiWidget *w, UiRect bounds)
{
    if (!ui_nav_is_focusable(w)) {
        return 0;
    }
    UiRect r = ui_rect_from_widget(w);
    int cx = ui_rect_center_x(r);
    int cy = ui_rect_center_y(r);
    return ui_rect_contains_point(bounds, cx, cy);
}

int ui_nav_first_focus(const UiScene *scene)
{
    if (!scene || !scene->widgets || scene->widget_count == 0) {
        return -1;
    }

    int best = -1;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        const UiWidget *w = &scene->widgets[i];
        if (!ui_nav_is_focusable(w)) {
            continue;
        }
        if (best < 0) {
            best = (int)i;
            continue;
        }
        const UiWidget *bw = &scene->widgets[(uint16_t)best];
        if (w->y < bw->y) {
            best = (int)i;
            continue;
        }
        if (w->y == bw->y && w->x < bw->x) {
            best = (int)i;
            continue;
        }
    }
    return best;
}

int ui_nav_first_focus_in_rect(const UiScene *scene, int x, int y, int w, int h)
{
    if (!scene || !scene->widgets || scene->widget_count == 0) {
        return -1;
    }
    if (w <= 0 || h <= 0) {
        return ui_nav_first_focus(scene);
    }

    UiRect bounds = {x, y, w, h};

    int best = -1;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        const UiWidget *ww = &scene->widgets[i];
        if (!ui_nav_is_focusable_in_rect(ww, bounds)) {
            continue;
        }
        if (best < 0) {
            best = (int)i;
            continue;
        }
        const UiWidget *bw = &scene->widgets[(uint16_t)best];
        if (ww->y < bw->y) {
            best = (int)i;
            continue;
        }
        if (ww->y == bw->y && ww->x < bw->x) {
            best = (int)i;
            continue;
        }
    }
    return best;
}

static int ui_nav_next_focusable_sorted(const UiScene *scene, int current_idx, int dir)
{
    if (!scene || !scene->widgets || scene->widget_count == 0) {
        return -1;
    }
    if (dir == 0) {
        return current_idx;
    }

    int order[128];
    int n = 0;
    int truncated = 0;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        if (ui_nav_is_focusable(&scene->widgets[i])) {
            if (n < (int)(sizeof(order) / sizeof(order[0]))) {
                order[n++] = (int)i;
            } else {
                truncated = 1;
            }
        }
    }
    if (n == 0) {
        return -1;
    }
    (void)truncated;  /* logged once if needed; focus chain is capped */

    for (int i = 0; i < n - 1; ++i) {
        for (int j = i + 1; j < n; ++j) {
            const UiWidget *a = &scene->widgets[(uint16_t)order[i]];
            const UiWidget *b = &scene->widgets[(uint16_t)order[j]];
            if (b->y < a->y || (b->y == a->y && b->x < a->x)) {
                int tmp = order[i];
                order[i] = order[j];
                order[j] = tmp;
            }
        }
    }

    int pos = -1;
    for (int i = 0; i < n; ++i) {
        if (order[i] == current_idx) {
            pos = i;
            break;
        }
    }
    if (pos < 0) {
        return order[0];
    }

    int step = (dir > 0) ? 1 : -1;
    int next = pos + step;
    if (next < 0) {
        next = n - 1;
    } else if (next >= n) {
        next = 0;
    }
    return order[next];
}

static int ui_nav_next_focusable_sorted_in_rect(const UiScene *scene, int current_idx, int dir, UiRect bounds)
{
    if (!scene || !scene->widgets || scene->widget_count == 0) {
        return -1;
    }
    if (dir == 0) {
        return current_idx;
    }

    int order[128];
    int n = 0;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        if (ui_nav_is_focusable_in_rect(&scene->widgets[i], bounds)) {
            if (n < (int)(sizeof(order) / sizeof(order[0]))) {
                order[n++] = (int)i;
            }
        }
    }
    if (n == 0) {
        return -1;
    }

    for (int i = 0; i < n - 1; ++i) {
        for (int j = i + 1; j < n; ++j) {
            const UiWidget *a = &scene->widgets[(uint16_t)order[i]];
            const UiWidget *b = &scene->widgets[(uint16_t)order[j]];
            if (b->y < a->y || (b->y == a->y && b->x < a->x)) {
                int tmp = order[i];
                order[i] = order[j];
                order[j] = tmp;
            }
        }
    }

    int pos = -1;
    for (int i = 0; i < n; ++i) {
        if (order[i] == current_idx) {
            pos = i;
            break;
        }
    }
    if (pos < 0) {
        return order[0];
    }

    int step = (dir > 0) ? 1 : -1;
    int next = pos + step;
    if (next < 0) {
        next = n - 1;
    } else if (next >= n) {
        next = 0;
    }
    return order[next];
}

int ui_nav_cycle_focus(const UiScene *scene, int current_idx, int delta)
{
    if (!scene) {
        return -1;
    }
    if (current_idx < 0 || (uint16_t)current_idx >= scene->widget_count) {
        return ui_nav_first_focus(scene);
    }
    if (!ui_nav_is_focusable(&scene->widgets[(uint16_t)current_idx])) {
        return ui_nav_first_focus(scene);
    }
    return ui_nav_next_focusable_sorted(scene, current_idx, delta);
}

int ui_nav_move_focus(const UiScene *scene, int current_idx, ui_nav_dir_t dir)
{
    if (!scene || !scene->widgets || scene->widget_count == 0) {
        return -1;
    }
    if ((int)dir < 0 || (int)dir > UI_NAV_RIGHT) {
        return current_idx;
    }

    if (current_idx < 0 || (uint16_t)current_idx >= scene->widget_count) {
        return ui_nav_first_focus(scene);
    }
    if (!ui_nav_is_focusable(&scene->widgets[(uint16_t)current_idx])) {
        return ui_nav_first_focus(scene);
    }

    const UiWidget *cur_w = &scene->widgets[(uint16_t)current_idx];
    UiRect cr = ui_rect_from_widget(cur_w);
    int cx = ui_rect_center_x(cr);
    int cy = ui_rect_center_y(cr);

    int beam_idx = -1;
    int beam_score = 0;
    int loose_idx = -1;
    int loose_score = 0;

    bool vertical = (dir == UI_NAV_UP || dir == UI_NAV_DOWN);

    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        if ((int)i == current_idx) {
            continue;
        }
        const UiWidget *w = &scene->widgets[i];
        if (!ui_nav_is_focusable(w)) {
            continue;
        }

        UiRect r = ui_rect_from_widget(w);
        int tx = ui_rect_center_x(r);
        int ty = ui_rect_center_y(r);
        int dx = tx - cx;
        int dy = ty - cy;

        if (dir == UI_NAV_UP && dy >= 0) {
            continue;
        }
        if (dir == UI_NAV_DOWN && dy <= 0) {
            continue;
        }
        if (dir == UI_NAV_LEFT && dx >= 0) {
            continue;
        }
        if (dir == UI_NAV_RIGHT && dx <= 0) {
            continue;
        }

        int primary = vertical ? (dy < 0 ? -dy : dy) : (dx < 0 ? -dx : dx);
        int secondary = vertical ? (dx < 0 ? -dx : dx) : (dy < 0 ? -dy : dy);
        int dist2 = dx * dx + dy * dy;

        int score;
        if (vertical) {
            int overlap = ui_rect_overlap(cr.x, ui_rect_right(cr), r.x, ui_rect_right(r));
            if (overlap > 0) {
                score = primary * 10000 + secondary * 100 + dist2;
                if (beam_idx < 0 || score < beam_score) {
                    beam_idx = (int)i;
                    beam_score = score;
                }
            } else {
                int gap;
                if (ui_rect_right(r) <= cr.x) {
                    gap = cr.x - ui_rect_right(r);
                } else if (r.x >= ui_rect_right(cr)) {
                    gap = r.x - ui_rect_right(cr);
                } else {
                    gap = 0;
                }
                score = 1000000 + gap * 10000 + primary * 10000 + secondary * 100 + dist2;
                if (loose_idx < 0 || score < loose_score) {
                    loose_idx = (int)i;
                    loose_score = score;
                }
            }
        } else {
            int overlap = ui_rect_overlap(cr.y, ui_rect_bottom(cr), r.y, ui_rect_bottom(r));
            if (overlap > 0) {
                score = primary * 10000 + secondary * 100 + dist2;
                if (beam_idx < 0 || score < beam_score) {
                    beam_idx = (int)i;
                    beam_score = score;
                }
            } else {
                int gap;
                if (ui_rect_bottom(r) <= cr.y) {
                    gap = cr.y - ui_rect_bottom(r);
                } else if (r.y >= ui_rect_bottom(cr)) {
                    gap = r.y - ui_rect_bottom(cr);
                } else {
                    gap = 0;
                }
                score = 1000000 + gap * 10000 + primary * 10000 + secondary * 100 + dist2;
                if (loose_idx < 0 || score < loose_score) {
                    loose_idx = (int)i;
                    loose_score = score;
                }
            }
        }
    }

    if (beam_idx >= 0) {
        return beam_idx;
    }
    if (loose_idx >= 0) {
        return loose_idx;
    }

    return ui_nav_cycle_focus(scene, current_idx, (dir == UI_NAV_DOWN || dir == UI_NAV_RIGHT) ? 1 : -1);
}

int ui_nav_move_focus_in_rect(const UiScene *scene, int current_idx, ui_nav_dir_t dir, int x, int y, int w, int h)
{
    if (!scene || !scene->widgets || scene->widget_count == 0) {
        return -1;
    }

    if (w <= 0 || h <= 0) {
        return ui_nav_move_focus(scene, current_idx, dir);
    }

    UiRect bounds = {x, y, w, h};

    if (current_idx < 0 || (uint16_t)current_idx >= scene->widget_count) {
        return ui_nav_first_focus_in_rect(scene, x, y, w, h);
    }
    if (!ui_nav_is_focusable_in_rect(&scene->widgets[(uint16_t)current_idx], bounds)) {
        return ui_nav_first_focus_in_rect(scene, x, y, w, h);
    }

    const UiWidget *cur_w = &scene->widgets[(uint16_t)current_idx];
    UiRect cr = ui_rect_from_widget(cur_w);
    int cx = ui_rect_center_x(cr);
    int cy = ui_rect_center_y(cr);

    int beam_idx = -1;
    int beam_score = 0;
    int loose_idx = -1;
    int loose_score = 0;

    bool vertical = (dir == UI_NAV_UP || dir == UI_NAV_DOWN);

    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        if ((int)i == current_idx) {
            continue;
        }
        const UiWidget *ww = &scene->widgets[i];
        if (!ui_nav_is_focusable_in_rect(ww, bounds)) {
            continue;
        }

        UiRect r = ui_rect_from_widget(ww);
        int tx = ui_rect_center_x(r);
        int ty = ui_rect_center_y(r);
        int dx = tx - cx;
        int dy = ty - cy;

        if (dir == UI_NAV_UP && dy >= 0) {
            continue;
        }
        if (dir == UI_NAV_DOWN && dy <= 0) {
            continue;
        }
        if (dir == UI_NAV_LEFT && dx >= 0) {
            continue;
        }
        if (dir == UI_NAV_RIGHT && dx <= 0) {
            continue;
        }

        int primary = vertical ? (dy < 0 ? -dy : dy) : (dx < 0 ? -dx : dx);
        int secondary = vertical ? (dx < 0 ? -dx : dx) : (dy < 0 ? -dy : dy);
        int dist2 = dx * dx + dy * dy;

        int score;
        if (vertical) {
            int overlap = ui_rect_overlap(cr.x, ui_rect_right(cr), r.x, ui_rect_right(r));
            if (overlap > 0) {
                score = primary * 10000 + secondary * 100 + dist2;
                if (beam_idx < 0 || score < beam_score) {
                    beam_idx = (int)i;
                    beam_score = score;
                }
            } else {
                int gap;
                if (ui_rect_right(r) <= cr.x) {
                    gap = cr.x - ui_rect_right(r);
                } else if (r.x >= ui_rect_right(cr)) {
                    gap = r.x - ui_rect_right(cr);
                } else {
                    gap = 0;
                }
                score = 1000000 + gap * 10000 + primary * 10000 + secondary * 100 + dist2;
                if (loose_idx < 0 || score < loose_score) {
                    loose_idx = (int)i;
                    loose_score = score;
                }
            }
        } else {
            int overlap = ui_rect_overlap(cr.y, ui_rect_bottom(cr), r.y, ui_rect_bottom(r));
            if (overlap > 0) {
                score = primary * 10000 + secondary * 100 + dist2;
                if (beam_idx < 0 || score < beam_score) {
                    beam_idx = (int)i;
                    beam_score = score;
                }
            } else {
                int gap;
                if (ui_rect_bottom(r) <= cr.y) {
                    gap = cr.y - ui_rect_bottom(r);
                } else if (r.y >= ui_rect_bottom(cr)) {
                    gap = r.y - ui_rect_bottom(cr);
                } else {
                    gap = 0;
                }
                score = 1000000 + gap * 10000 + primary * 10000 + secondary * 100 + dist2;
                if (loose_idx < 0 || score < loose_score) {
                    loose_idx = (int)i;
                    loose_score = score;
                }
            }
        }
    }

    if (beam_idx >= 0) {
        return beam_idx;
    }
    if (loose_idx >= 0) {
        return loose_idx;
    }

    return ui_nav_next_focusable_sorted_in_rect(
        scene,
        current_idx,
        (dir == UI_NAV_DOWN || dir == UI_NAV_RIGHT) ? 1 : -1,
        bounds
    );
}
