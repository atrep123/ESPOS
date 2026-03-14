#include "ui_border.h"

void ui_draw_border_style(
    const UiDrawOps *ops, int x, int y, int w, int h,
    uint8_t style, uint8_t c)
{
    if (ops == NULL || w <= 0 || h <= 0) {
        return;
    }
    if (style == UI_BORDER_NONE) {
        return;
    }
    if (style == UI_BORDER_SINGLE) {
        ui_draw_rect_outline(ops, x, y, w, h, c);
        return;
    }
    if (style == UI_BORDER_DOUBLE) {
        ui_draw_rect_outline(ops, x, y, w, h, c);
        if (w > 4 && h > 4) {
            ui_draw_rect_outline(ops, x + 2, y + 2, w - 4, h - 4, c);
        } else if (w > 2 && h > 2) {
            ui_draw_rect_outline(ops, x + 1, y + 1, w - 2, h - 2, c);
        }
        return;
    }
    if (style == UI_BORDER_BOLD) {
        ui_draw_rect_outline(ops, x, y, w, h, c);
        if (w > 2 && h > 2) {
            ui_draw_rect_outline(ops, x + 1, y + 1, w - 2, h - 2, c);
        }
        return;
    }
    if (style == UI_BORDER_ROUNDED) {
        if (ops->draw_hline) {
            if (w > 2) {
                ops->draw_hline(ops->ctx, x + 1, y, w - 2, c);
                ops->draw_hline(ops->ctx, x + 1, y + h - 1, w - 2, c);
            }
        }
        if (ops->draw_vline) {
            if (h > 2) {
                ops->draw_vline(ops->ctx, x, y + 1, h - 2, c);
                ops->draw_vline(ops->ctx, x + w - 1, y + 1, h - 2, c);
            }
        }
        return;
    }
    if (style == UI_BORDER_DASHED) {
        if (ops->draw_hline) {
            int seg = 2;
            int gap = 2;
            for (int xx = x; xx < x + w; xx += seg + gap) {
                int ww = seg;
                if (xx + ww > x + w) {
                    ww = x + w - xx;
                }
                ops->draw_hline(ops->ctx, xx, y, ww, c);
                ops->draw_hline(ops->ctx, xx, y + h - 1, ww, c);
            }
        }
        if (ops->draw_vline) {
            int seg = 2;
            int gap = 2;
            for (int yy = y; yy < y + h; yy += seg + gap) {
                int hh = seg;
                if (yy + hh > y + h) {
                    hh = y + h - yy;
                }
                ops->draw_vline(ops->ctx, x, yy, hh, c);
                ops->draw_vline(ops->ctx, x + w - 1, yy, hh, c);
            }
        }
        return;
    }

    /* Unknown style — fall back to single rect */
    ui_draw_rect_outline(ops, x, y, w, h, c);
}
