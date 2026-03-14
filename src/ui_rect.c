#include "ui_rect.h"

UiRect ui_rect_from_widget(const UiWidget *w)
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

int ui_rect_center_x(UiRect r)
{
    return r.x + (r.w / 2);
}

int ui_rect_center_y(UiRect r)
{
    return r.y + (r.h / 2);
}

int ui_rect_right(UiRect r)
{
    return r.x + r.w;
}

int ui_rect_bottom(UiRect r)
{
    return r.y + r.h;
}

int ui_rect_overlap(int a0, int a1, int b0, int b1)
{
    int lo = (a0 > b0) ? a0 : b0;
    int hi = (a1 < b1) ? a1 : b1;
    int span = hi - lo;
    return (span > 0) ? span : 0;
}

int ui_rect_contains_point(UiRect r, int x, int y)
{
    return (x >= r.x) && (y >= r.y) && (x < ui_rect_right(r)) && (y < ui_rect_bottom(r));
}
