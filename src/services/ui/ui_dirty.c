#include "ui_dirty.h"
#include <string.h>

/* ── Dirty-rectangle tracking ── */

void ui_dirty_clear(UiDirty *d)
{
    if (d == NULL) {
        return;
    }
    d->dirty = 0;
    d->x0 = d->y0 = 0;
    d->x1 = d->y1 = 0;
}

void ui_dirty_add(UiDirty *d, int x, int y, int w, int h,
                  int disp_w, int disp_h)
{
    if (d == NULL) {
        return;
    }
    if (w <= 0 || h <= 0) {
        return;
    }

    int x0 = x;
    int y0 = y;
    int x1 = x + w;
    int y1 = y + h;

    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > disp_w) x1 = disp_w;
    if (y1 > disp_h) y1 = disp_h;
    if (x0 >= x1 || y0 >= y1) {
        return;
    }

    if (!d->dirty) {
        d->dirty = 1;
        d->x0 = x0;
        d->y0 = y0;
        d->x1 = x1;
        d->y1 = y1;
        return;
    }

    if (x0 < d->x0) d->x0 = x0;
    if (y0 < d->y0) d->y0 = y0;
    if (x1 > d->x1) d->x1 = x1;
    if (y1 > d->y1) d->y1 = y1;
}

/* ── Null-safe string comparison ── */

int ui_text_equals(const char *a, const char *b)
{
    if (a == NULL) {
        a = "";
    }
    if (b == NULL) {
        b = "";
    }
    return (strcmp(a, b) == 0) ? 1 : 0;
}

/* ── Pure widget operations ── */

int ui_widget_toggle_checked(UiWidget *w)
{
    if (w == NULL) {
        return 0;
    }
    if ((UiWidgetType)w->type != UIW_CHECKBOX) {
        return 0;
    }
    w->checked = (uint8_t)(w->checked ? 0 : 1);
    return 1;
}

int ui_widget_clamp_value(UiWidget *w, int delta)
{
    if (w == NULL) {
        return 0;
    }
    UiWidgetType t = (UiWidgetType)w->type;
    if (t != UIW_SLIDER && t != UIW_GAUGE && t != UIW_PROGRESSBAR) {
        return 0;
    }

    int v = (int)w->value + delta;
    int vmin = (int)w->min_value;
    int vmax = (int)w->max_value;
    if (v < vmin) v = vmin;
    if (v > vmax) v = vmax;
    if (v == (int)w->value) {
        return 0;
    }
    w->value = (int16_t)v;
    return 1;
}
