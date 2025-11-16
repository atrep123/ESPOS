#include "ui_render.h"

#include <string.h>

static inline void _draw_rect(const UiDrawOps *ops, int x, int y, int w, int h, uint8_t c)
{
    if (ops->draw_rect) {
        ops->draw_rect(ops->ctx, x, y, w, h, c);
        return;
    }
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, x, y, w, c);
        ops->draw_hline(ops->ctx, x, y + h - 1, w, c);
    }
    if (ops->draw_vline) {
        ops->draw_vline(ops->ctx, x, y, h, c);
        ops->draw_vline(ops->ctx, x + w - 1, y, h, c);
    }
}

static inline void _fill_rect(const UiDrawOps *ops, int x, int y, int w, int h, uint8_t c)
{
    if (ops->fill_rect) {
        ops->fill_rect(ops->ctx, x, y, w, h, c);
        return;
    }
    /* Fallback fill using hlines if fill_rect not provided */
    if (ops->draw_hline) {
        for (int yy = 0; yy < h; ++yy) {
            ops->draw_hline(ops->ctx, x, y + yy, w, c);
        }
    }
}

static void _render_progressbar(const UiWidget *w, const UiDrawOps *ops)
{
    /* Bar background */
    _draw_rect(ops, w->x, w->y, w->width, w->height, 1);

    int inner_w = w->width - 2;
    int inner_h = w->height - 2;
    if (inner_w <= 0 || inner_h <= 0) return;

    int span = inner_w;
    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int val = w->value - w->min_value;
    if (val < 0) val = 0;
    if (val > range) val = range;
    int filled = (val * span) / range;

    if (filled > 0) {
        _fill_rect(ops, w->x + 1, w->y + 1, filled, inner_h, 1);
    }
}

static void _render_checkbox(const UiWidget *w, const UiDrawOps *ops)
{
    int box = (w->height > 6) ? 6 : (w->height - 2);
    if (box < 4) box = w->height - 2;
    if (box < 2) box = 2;
    int bx = w->x + 1;
    int by = w->y + (w->height - box) / 2;
    _draw_rect(ops, bx, by, box, box, 1);

    if (w->checked && box >= 4) {
        /* Simple X mark inside the box */
        if (ops->draw_hline) {
            for (int i = 1; i < box - 1; ++i) {
                int x1 = bx + 1 + i - 1;
                int y1 = by + 1 + i - 1;
                ops->draw_hline(ops->ctx, x1, y1, 1, 1);
                int x2 = bx + box - 2 - (i - 1);
                int y2 = by + 1 + i - 1;
                ops->draw_hline(ops->ctx, x2, y2, 1, 1);
            }
        }
    }

    if (w->text && ops->draw_text) {
        ops->draw_text(ops->ctx, bx + box + 2, w->y + (w->height / 2), w->text, 1);
    }
}

static void _render_label_or_button(const UiWidget *w, const UiDrawOps *ops)
{
    if (w->border) {
        _draw_rect(ops, w->x, w->y, w->width, w->height, 1);
    }
    if (w->text && ops->draw_text) {
        /* Approximate vertical center */
        int ty = w->y + (w->height / 2);
        int tx = w->x + 2;
        ops->draw_text(ops->ctx, tx, ty, w->text, 1);
    }
}

static void _render_box(const UiWidget *w, const UiDrawOps *ops)
{
    if (w->border) {
        _draw_rect(ops, w->x, w->y, w->width, w->height, 1);
    } else {
        _fill_rect(ops, w->x, w->y, w->width, w->height, 0);
    }
}

void ui_render_widget(const UiWidget *w, const UiDrawOps *ops)
{
    if (!w || !ops) return;

    switch (w->type) {
        case UIW_LABEL:
            _render_label_or_button(w, ops);
            break;
        case UIW_BUTTON:
            _render_label_or_button(w, ops);
            break;
        case UIW_BOX:
            _render_box(w, ops);
            break;
        case UIW_PROGRESSBAR:
            _render_progressbar(w, ops);
            break;
        case UIW_CHECKBOX:
            _render_checkbox(w, ops);
            break;
        /* Simple stubs for unimplemented widgets: draw a rectangle */
        case UIW_GAUGE:
        case UIW_RADIOBUTTON:
        case UIW_SLIDER:
        case UIW_TEXTBOX:
        case UIW_PANEL:
        case UIW_ICON:
        case UIW_CHART:
        default:
            _draw_rect(ops, w->x, w->y, w->width, w->height, 1);
            break;
    }
}

void ui_render_scene(const UiScene *scene, const UiDrawOps *ops)
{
    if (!scene || !ops) return;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        ui_render_widget(&scene->widgets[i], ops);
    }
}
