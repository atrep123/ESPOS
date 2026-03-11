#include "ui_render.h"

#include <string.h>
#include "display_config.h"
#include "icons_registry.h"

#if DISPLAY_COLOR_BITS == 4
enum {
    UI_COL_BG = 0,
    UI_COL_PANEL_BG = 2,
    UI_COL_BORDER = 12,
    UI_COL_TEXT = 15,
    UI_COL_MUTED = 8,
    UI_COL_FILL = 10,
};
#else
enum {
    UI_COL_BG = 0,
    UI_COL_PANEL_BG = 0,
    UI_COL_BORDER = 1,
    UI_COL_TEXT = 1,
    UI_COL_MUTED = 1,
    UI_COL_FILL = 1,
};
#endif

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

static uint8_t ui_gray4_add(uint8_t v, int delta)
{
    int out = (int)(v & 0x0F) + delta;
    if (out < 0) {
        out = 0;
    }
    if (out > 15) {
        out = 15;
    }
    return (uint8_t)out;
}

static void ui_widget_colors(
    const UiWidget *w,
    uint8_t *fg,
    uint8_t *bg,
    uint8_t *border,
    uint8_t *muted,
    uint8_t *fill
)
{
    uint8_t base_fg = UI_COL_TEXT;
    uint8_t base_bg = UI_COL_BG;
    if (w != NULL && (w->fg != 0 || w->bg != 0)) {
        base_fg = (uint8_t)(w->fg & 0x0F);
        base_bg = (uint8_t)(w->bg & 0x0F);
        if (base_fg == 0 && base_bg == 0) {
            base_fg = UI_COL_TEXT;
            base_bg = UI_COL_BG;
        } else if (base_fg == 0) {
            base_fg = UI_COL_TEXT;
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

static int ui_is_space(char ch)
{
    return (ch == ' ') || (ch == '\t') || (ch == '\r');
}

static void ui_flatten_one_line(const char *in, char *out, int out_cap)
{
    if (out == NULL || out_cap <= 0) {
        return;
    }
    out[0] = '\0';
    if (in == NULL || *in == '\0') {
        return;
    }

    int w = 0;
    int prev_space = 1;
    for (const char *p = in; *p && w < out_cap - 1; ++p) {
        char ch = *p;
        if (ch == '\n' || ch == '\r' || ch == '\t') {
            ch = ' ';
        }
        if (ch == ' ') {
            if (prev_space) {
                continue;
            }
            prev_space = 1;
            out[w++] = ' ';
            continue;
        }
        prev_space = 0;
        out[w++] = ch;
    }
    while (w > 0 && out[w - 1] == ' ') {
        w -= 1;
    }
    out[w] = '\0';
}

static int ui_fit_line_buf(const char *text, int max_chars, int use_ellipsis, char *out, int out_cap)
{
    if (out == NULL || out_cap <= 0) {
        return 0;
    }
    out[0] = '\0';
    if (text == NULL || *text == '\0' || max_chars <= 0) {
        return 0;
    }

    if (max_chars >= out_cap) {
        max_chars = out_cap - 1;
    }

    size_t len = strlen(text);
    if ((int)len <= max_chars) {
        memcpy(out, text, len + 1);
        return (int)len;
    }

    if (!use_ellipsis) {
        memcpy(out, text, (size_t)max_chars);
        out[max_chars] = '\0';
        return max_chars;
    }

    const char *ellipsis = "...";
    const int ell_len = 3;
    if (max_chars <= ell_len) {
        memcpy(out, text, (size_t)max_chars);
        out[max_chars] = '\0';
        return max_chars;
    }

    int copy = max_chars - ell_len;
    memcpy(out, text, (size_t)copy);
    memcpy(out + copy, ellipsis, (size_t)ell_len);
    out[copy + ell_len] = '\0';
    return copy + ell_len;
}

static void ui_draw_text_line_in_rect(
    const UiDrawOps *ops,
    int x,
    int y,
    int w_px,
    const char *text,
    uint8_t fg,
    uint8_t align,
    int use_ellipsis
)
{
    if (ops == NULL || ops->draw_text == NULL || text == NULL || *text == '\0') {
        return;
    }
    if (w_px <= 0) {
        return;
    }

    int max_chars = w_px / UI_FONT_CHAR_W;
    if (max_chars <= 0) {
        return;
    }

    char buf[96];
    int n = ui_fit_line_buf(text, max_chars, use_ellipsis, buf, (int)sizeof(buf));
    if (n <= 0) {
        return;
    }

    int text_px = n * UI_FONT_CHAR_W;
    int xx = x;
    if (align == UI_ALIGN_CENTER) {
        if (text_px < w_px) {
            xx = x + (w_px - text_px) / 2;
        }
    } else if (align == UI_ALIGN_RIGHT) {
        if (text_px < w_px) {
            xx = x + (w_px - text_px);
        }
    }
    ops->draw_text(ops->ctx, xx, y, buf, fg);
}

static int ui_wrap_next_line(const char **pp, char *out, int out_cap, int max_chars)
{
    if (pp == NULL || *pp == NULL || out == NULL || out_cap <= 0) {
        return 0;
    }
    if (max_chars <= 0) {
        return 0;
    }
    if (max_chars >= out_cap) {
        max_chars = out_cap - 1;
    }

    const char *p = *pp;
    while (*p && (ui_is_space(*p) || *p == '\n')) {
        p++;
    }
    if (*p == '\0') {
        *pp = p;
        out[0] = '\0';
        return 0;
    }

    int len = 0;
    while (*p) {
        while (*p && ui_is_space(*p)) {
            p++;
        }
        if (*p == '\n') {
            p++;
            break;
        }
        if (*p == '\0') {
            break;
        }

        const char *ws = p;
        int wl = 0;
        while (*p && !ui_is_space(*p) && *p != '\n') {
            p++;
            wl++;
        }

        if (len == 0) {
            if (wl <= max_chars) {
                memcpy(out, ws, (size_t)wl);
                len = wl;
            } else {
                memcpy(out, ws, (size_t)max_chars);
                len = max_chars;
                p = ws + max_chars;
                break;
            }
        } else {
            if (len + 1 + wl <= max_chars) {
                out[len] = ' ';
                memcpy(out + len + 1, ws, (size_t)wl);
                len += 1 + wl;
            } else {
                p = ws;
                break;
            }
        }
    }
    out[len] = '\0';
    *pp = p;
    return len;
}

static int ui_count_wrap_lines(const char *text, int max_chars, int max_lines, int *truncated)
{
    if (truncated) {
        *truncated = 0;
    }
    if (text == NULL || *text == '\0' || max_chars <= 0 || max_lines <= 0) {
        return 0;
    }

    const char *p = text;
    int lines = 0;
    int trunc = 0;
    char buf[96];

    for (;;) {
        int n = ui_wrap_next_line(&p, buf, (int)sizeof(buf), max_chars);
        if (n <= 0) {
            break;
        }
        lines += 1;
        if (lines >= max_lines) {
            const char *q = p;
            while (*q && (ui_is_space(*q) || *q == '\n')) {
                q++;
            }
            if (*q) {
                trunc = 1;
            }
            break;
        }
    }

    if (truncated) {
        *truncated = trunc;
    }
    return lines;
}

static void ui_draw_text_block(
    const UiDrawOps *ops,
    int x,
    int y,
    int w_px,
    int h_px,
    const char *text,
    uint8_t fg,
    uint8_t align,
    uint8_t valign,
    uint8_t overflow,
    int max_lines
)
{
    if (ops == NULL || ops->draw_text == NULL) {
        return;
    }
    if (text == NULL || *text == '\0') {
        return;
    }
    if (w_px <= 0 || h_px <= 0) {
        return;
    }

    int max_chars = w_px / UI_FONT_CHAR_W;
    int max_lines_by_h = h_px / UI_FONT_CHAR_H;
    if (max_chars <= 0 || max_lines_by_h <= 0) {
        return;
    }

    int use_wrap = 0;
    if (overflow == UI_TEXT_OVERFLOW_WRAP) {
        use_wrap = 1;
    } else if (overflow == UI_TEXT_OVERFLOW_AUTO) {
        if (max_lines_by_h >= 2) {
            int has_nl = (strchr(text, '\n') != NULL);
            char flat[160];
            ui_flatten_one_line(text, flat, (int)sizeof(flat));
            use_wrap = has_nl || ((int)strlen(flat) > max_chars);
        } else {
            use_wrap = 0;
        }
    }

    int ml = max_lines;
    if (ml <= 0) {
        ml = max_lines_by_h;
    }
    if (ml > max_lines_by_h) {
        ml = max_lines_by_h;
    }

    if (!use_wrap) {
        char flat[160];
        ui_flatten_one_line(text, flat, (int)sizeof(flat));
        int ty = y;
        if (valign == UI_VALIGN_MIDDLE) {
            ty = y + (h_px - UI_FONT_CHAR_H) / 2;
        } else if (valign == UI_VALIGN_BOTTOM) {
            ty = y + (h_px - UI_FONT_CHAR_H);
        }
        int use_ellipsis = (overflow != UI_TEXT_OVERFLOW_CLIP);
        ui_draw_text_line_in_rect(ops, x, ty, w_px, flat, fg, align, use_ellipsis);
        return;
    }

    int truncated = 0;
    int lines = ui_count_wrap_lines(text, max_chars, ml, &truncated);
    if (lines <= 0) {
        return;
    }

    int total_h = lines * UI_FONT_CHAR_H;
    int start_y = y;
    if (valign == UI_VALIGN_MIDDLE) {
        start_y = y + (h_px - total_h) / 2;
    } else if (valign == UI_VALIGN_BOTTOM) {
        start_y = y + (h_px - total_h);
    }

    const char *p = text;
    char line[96];
    for (int i = 0; i < lines; ++i) {
        int n = ui_wrap_next_line(&p, line, (int)sizeof(line), max_chars);
        if (n <= 0) {
            break;
        }
        if (truncated && (i == lines - 1)) {
            int want = max_chars;
            if (want >= (int)sizeof(line)) {
                want = (int)sizeof(line) - 1;
            }
            if (want > 3) {
                if (n > want - 3) {
                    n = want - 3;
                }
                line[n] = '\0';
                memcpy(line + n, "...", 4); /* includes NUL */
            } else {
                line[want] = '\0';
            }
        }
        ui_draw_text_line_in_rect(
            ops,
            x,
            start_y + i * UI_FONT_CHAR_H,
            w_px,
            line,
            fg,
            align,
            0
        );
    }
}

static inline void _draw_rect(const UiDrawOps *ops, int x, int y, int w, int h, uint8_t c)
{
    if (w <= 0 || h <= 0) return;
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
    if (w <= 0 || h <= 0) return;
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

static void _draw_border_style(const UiDrawOps *ops, int x, int y, int w, int h, uint8_t style, uint8_t c)
{
    if (w <= 0 || h <= 0) {
        return;
    }
    if (style == UI_BORDER_NONE) {
        return;
    }
    if (style == UI_BORDER_SINGLE) {
        _draw_rect(ops, x, y, w, h, c);
        return;
    }
    if (style == UI_BORDER_DOUBLE) {
        _draw_rect(ops, x, y, w, h, c);
        if (w > 4 && h > 4) {
            _draw_rect(ops, x + 2, y + 2, w - 4, h - 4, c);
        } else if (w > 2 && h > 2) {
            _draw_rect(ops, x + 1, y + 1, w - 2, h - 2, c);
        }
        return;
    }
    if (style == UI_BORDER_BOLD) {
        _draw_rect(ops, x, y, w, h, c);
        if (w > 2 && h > 2) {
            _draw_rect(ops, x + 1, y + 1, w - 2, h - 2, c);
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

    _draw_rect(ops, x, y, w, h, c);
}

static void _render_progressbar(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    int inner_w = w->width - 2;
    int inner_h = w->height - 2;
    if (inner_w <= 0 || inner_h <= 0) return;

    int span = inner_w;
    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int val = w->value - w->min_value;
    if (val < 0) val = 0;
    if (val > range) val = range;
    int filled = (int)(((int64_t)val * span) / range);

    if (filled > 0) {
        _fill_rect(ops, w->x + 1, w->y + 1, filled, inner_h, fill);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            w->text,
            fg,
            w->align,
            w->valign,
            w->text_overflow,
            (int)w->max_lines
        );
    }
}

static void _render_checkbox(const UiWidget *w, const UiDrawOps *ops)
{
    if (w->height < 4 || w->width < 4) return;

    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    int box = (w->height > 6) ? 6 : (w->height - 2);
    if (box < 4) box = w->height - 2;
    if (box < 2) box = 2;
    int bx = w->x + 1;
    int by = w->y + (w->height - box) / 2;
    _fill_rect(ops, bx, by, box, box, bg);
    _draw_rect(ops, bx, by, box, box, border);

    if (w->checked && box >= 4) {
        /* Simple X mark inside the box */
        if (ops->draw_hline) {
            for (int i = 1; i < box - 1; ++i) {
                int x1 = bx + 1 + i - 1;
                int y1 = by + 1 + i - 1;
                ops->draw_hline(ops->ctx, x1, y1, 1, fg);
                int x2 = bx + box - 2 - (i - 1);
                int y2 = by + 1 + i - 1;
                ops->draw_hline(ops->ctx, x2, y2, 1, fg);
            }
        }
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int tx = bx + box + 2;
        int max_w = (w->x + w->width) - tx - 1;
        if (max_w > 0) {
            ui_draw_text_block(
                ops,
                tx,
                w->y,
                max_w,
                w->height,
                w->text,
                fg,
                UI_ALIGN_LEFT,
                w->valign,
                w->text_overflow,
                (int)w->max_lines
            );
        }
    }
}

static void _render_label(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }
    if (w->border) {
        _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }
    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        if (iw > 0 && ih >= UI_FONT_CHAR_H) {
            ui_draw_text_block(
                ops,
                ix,
                iy,
                iw,
                ih,
                w->text,
                fg,
                w->align,
                w->valign,
                w->text_overflow,
                (int)w->max_lines
            );
        }
    }
}

static void _render_button(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            w->text,
            fg,
            w->align,
            w->valign,
            w->text_overflow,
            (int)w->max_lines
        );
    }
}

static void _render_panel(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            w->text,
            fg,
            w->align,
            w->valign,
            w->text_overflow,
            (int)w->max_lines
        );
    }
}

static void _render_box(const UiWidget *w, const UiDrawOps *ops)
{
    /* UIW_BOX behaves like a panel/container. */
    _render_panel(w, ops);
}

static void _render_textbox(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }
    if (ops->draw_hline && w->height > 2) {
        ops->draw_hline(ops->ctx, w->x + 1, w->y + w->height - 2, w->width - 2, muted);
    }
    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            w->text,
            fg,
            w->align,
            w->valign,
            w->text_overflow,
            (int)w->max_lines
        );
    }
}

static void _render_slider(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    int inner_x = w->x + 2;
    int inner_w = w->width - 4;
    if (inner_w <= 0) return;

    int cy = w->y + (w->height / 2);
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, inner_x, cy, inner_w, muted);
    }

    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int val = w->value - w->min_value;
    if (val < 0) val = 0;
    if (val > range) val = range;
    int knob_x = inner_x + (int)(((int64_t)val * (inner_w - 1)) / range);

    int knob_w = 5;
    int knob_h = w->height - 4;
    if (knob_h < 3) knob_h = 3;
    int kx = knob_x - (knob_w / 2);
    if (kx < inner_x) kx = inner_x;
    if (kx + knob_w > inner_x + inner_w) kx = inner_x + inner_w - knob_w;
    int ky = w->y + (w->height - knob_h) / 2;
    _fill_rect(ops, kx, ky, knob_w, knob_h, fill);
    _draw_rect(ops, kx, ky, knob_w, knob_h, border);
}

static void _render_radiobutton(const UiWidget *w, const UiDrawOps *ops)
{
    if (w->height < 4 || w->width < 4) return;

    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);
    int box = (w->height > 6) ? 6 : (w->height - 2);
    if (box < 2) box = 2;
    int bx = w->x + 1;
    int by = w->y + (w->height - box) / 2;
    _fill_rect(ops, bx, by, box, box, bg);
    _draw_rect(ops, bx, by, box, box, border);

    if (w->checked && box >= 4) {
        _fill_rect(ops, bx + 2, by + 2, box - 4, box - 4, fg);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int tx = bx + box + 2;
        int max_w = (w->x + w->width) - tx - 1;
        if (max_w > 0) {
            ui_draw_text_block(
                ops,
                tx,
                w->y,
                max_w,
                w->height,
                w->text,
                fg,
                UI_ALIGN_LEFT,
                w->valign,
                w->text_overflow,
                (int)w->max_lines
            );
        }
    }
}

static void _render_gauge(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    /* Simple horizontal gauge with label + numeric value. */
    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }
    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    int inner_w = w->width - 2;
    int inner_h = w->height - 2;
    if (inner_w <= 0 || inner_h <= 0) return;

    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int val = w->value - w->min_value;
    if (val < 0) val = 0;
    if (val > range) val = range;
    int filled = (int)(((int64_t)val * inner_w) / range);
    if (filled > 0) {
        _fill_rect(ops, w->x + 1, w->y + 1, filled, inner_h, fill);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            w->text,
            fg,
            UI_ALIGN_LEFT,
            UI_VALIGN_TOP,
            w->text_overflow,
            (int)w->max_lines
        );
    }
}

static void _render_icon(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }
    if (w->border) {
        _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

#if HAVE_ICONS
    if (ops->blit_mono && w->text && w->text[0]) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = (int)w->x + inset + pad;
        int iy = (int)w->y + inset + pad;
        int iw = (int)w->width - (inset + pad) * 2;
        int ih = (int)w->height - (inset + pad) * 2;

        if (iw >= 16 && ih >= 16) {
            uint8_t want = (iw >= 24 && ih >= 24) ? 24 : 16;
            const icon_t *ic = icons_find(w->text, want);
            if (ic != NULL && ic->width <= (uint16_t)iw && ic->height <= (uint16_t)ih) {
                int dx = ix;
                if (w->align == UI_ALIGN_CENTER) {
                    dx = ix + (iw - (int)ic->width) / 2;
                } else if (w->align == UI_ALIGN_RIGHT) {
                    dx = ix + (iw - (int)ic->width);
                }

                int dy = iy;
                if (w->valign == UI_VALIGN_MIDDLE) {
                    dy = iy + (ih - (int)ic->height) / 2;
                } else if (w->valign == UI_VALIGN_BOTTOM) {
                    dy = iy + (ih - (int)ic->height);
                }

                ops->blit_mono(
                    ops->ctx,
                    dx,
                    dy,
                    (int)ic->width,
                    (int)ic->height,
                    (int)ic->stride_bytes,
                    ic->data,
                    fg,
                    0
                );
                return;
            }
        }
    }
#endif

    if (ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        const char *s = (w->text && w->text[0]) ? w->text : "?";
        char buf[2] = { s[0], '\0' };
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            buf,
            fg,
            UI_ALIGN_CENTER,
            UI_VALIGN_MIDDLE,
            UI_TEXT_OVERFLOW_CLIP,
            1
        );
    }
}

static void _render_chart(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    ui_widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    _fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        _draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }
    int inner_x = w->x + 1;
    int inner_y = w->y + 1;
    int inner_w = w->width - 2;
    int inner_h = w->height - 2;
    if (inner_w <= 0 || inner_h <= 0) return;
    if (inner_w < 8 || inner_h < 8) return;  /* too small for meaningful chart */

    /* Minimal placeholder "chart": axes + a few bars based on value. */
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, inner_x + 2, inner_y + inner_h - 3, inner_w - 4, muted);
    }
    if (ops->draw_vline) {
        ops->draw_vline(ops->ctx, inner_x + 2, inner_y + 2, inner_h - 5, muted);
    }
    int bars = 6;
    int gap = 2;
    int bar_w = (inner_w - 6 - (gap * (bars - 1))) / bars;
    if (bar_w < 1) bar_w = 1;
    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int base = w->value - w->min_value;
    if (base < 0) base = 0;
    for (int i = 0; i < bars; ++i) {
        int v = (base + i * 11) % (range + 1);
        int bh = (int)(((int64_t)v * (inner_h - 6)) / range);
        int bx = inner_x + 4 + i * (bar_w + gap);
        int by = inner_y + inner_h - 4 - bh;
        _fill_rect(ops, bx, by, bar_w, bh, fill);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        ui_draw_text_block(
            ops,
            ix,
            iy,
            iw,
            ih,
            w->text,
            fg,
            w->align,
            w->valign,
            w->text_overflow,
            (int)w->max_lines
        );
    }
}

void ui_render_widget(const UiWidget *w, const UiDrawOps *ops)
{
    if (!w || !ops) return;
    if (!ui_widget_is_visible(w)) {
        return;
    }
    if (w->type >= UIW__COUNT) {
        return;
    }

    switch (w->type) {
        case UIW_LABEL:
            _render_label(w, ops);
            break;
        case UIW_BUTTON:
            _render_button(w, ops);
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
        case UIW_GAUGE:
            _render_gauge(w, ops);
            break;
        case UIW_RADIOBUTTON:
            _render_radiobutton(w, ops);
            break;
        case UIW_SLIDER:
            _render_slider(w, ops);
            break;
        case UIW_TEXTBOX:
            _render_textbox(w, ops);
            break;
        case UIW_PANEL:
            _render_panel(w, ops);
            break;
        case UIW_ICON:
            _render_icon(w, ops);
            break;
        case UIW_CHART:
            _render_chart(w, ops);
            break;
        default:
            _draw_rect(ops, w->x, w->y, w->width, w->height, UI_COL_BORDER);
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
