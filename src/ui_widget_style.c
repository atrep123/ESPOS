#include "ui_widget_style.h"
#include "ui_render_text.h"   /* ui_gray4_add */

/* ── Widget state queries ── */

int ui_widget_has_extended(const UiWidget *w)
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

int ui_widget_is_visible(const UiWidget *w)
{
    if (!ui_widget_has_extended(w)) {
        return 1;
    }
    return (w->visible != 0);
}

int ui_widget_is_enabled(const UiWidget *w)
{
    if (!ui_widget_has_extended(w)) {
        return 1;
    }
    return (w->enabled != 0);
}

/* ── Color computation ── */

void ui_widget_colors(const UiWidget *w,
                      uint8_t col_text, uint8_t col_bg,
                      uint8_t *fg, uint8_t *bg,
                      uint8_t *border, uint8_t *muted, uint8_t *fill)
{
    uint8_t base_fg = col_text;
    uint8_t base_bg = col_bg;
    if (w != NULL && (w->fg != 0 || w->bg != 0)) {
        base_fg = (uint8_t)(w->fg & 0x0F);
        base_bg = (uint8_t)(w->bg & 0x0F);
        if (base_fg == 0 && base_bg == 0) {
            base_fg = col_text;
            base_bg = col_bg;
        } else if (base_fg == 0) {
            base_fg = col_text;
        }
    }

    uint8_t out_fg = base_fg;
    uint8_t out_bg = base_bg;

    uint8_t st = (w != NULL) ? w->style : 0;
    if (st & UI_STYLE_INVERSE) {
        uint8_t tmp = out_fg;
        out_fg = out_bg;
        out_bg = tmp;
    }
    if (st & UI_STYLE_HIGHLIGHT) {
        out_bg = ui_gray4_add(out_bg, 2);
    }

    int enabled = ui_widget_is_enabled(w);
    if (!enabled) {
        out_fg = ui_gray4_add(out_fg, -6);
        out_bg = ui_gray4_add(out_bg, -2);
    }

    if (fg) *fg = out_fg;
    if (bg) *bg = out_bg;
    if (border) *border = ui_gray4_add(out_fg, -4);
    if (muted) *muted = ui_gray4_add(out_fg, -7);
    if (fill) *fill = ui_gray4_add(out_fg, -2);
}
