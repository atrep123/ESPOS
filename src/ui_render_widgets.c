#include "ui_render_widgets.h"

#include <math.h>
#include <stdio.h>
#include <string.h>
#include "icons_registry.h"
#include "ui_border.h"
#include "ui_dither.h"
#include "ui_render_text.h"
#include "ui_text_layout.h"
#include "ui_theme.h"
#include "ui_widget_style.h"

/* Resolve widget colors using theme defaults. */
static void widget_colors(
    const UiWidget *w,
    uint8_t *fg,
    uint8_t *bg,
    uint8_t *border,
    uint8_t *muted,
    uint8_t *fill)
{
    ui_widget_colors(w, UI_COL_TEXT, UI_COL_BG, fg, bg, border, muted, fill);
}

/* ------------------------------------------------------------------ */
/*  Label                                                              */
/* ------------------------------------------------------------------ */

void ui_render_label(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }
    if (w->border) {
        ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
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
                ops, ix, iy, iw, ih, w->text, fg,
                w->align, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Button                                                             */
/* ------------------------------------------------------------------ */

void ui_render_button(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
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
                ops, ix, iy, iw, ih, w->text, fg,
                w->align, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Panel                                                              */
/* ------------------------------------------------------------------ */

void ui_render_panel(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
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
                ops, ix, iy, iw, ih, w->text, fg,
                w->align, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Box                                                                */
/* ------------------------------------------------------------------ */

void ui_render_box(const UiWidget *w, const UiDrawOps *ops)
{
    ui_render_panel(w, ops);
}

/* ------------------------------------------------------------------ */
/*  Textbox                                                            */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Textbox — styled read-only text display with underline decoration. */
/*  NOT an editable input field.  Use runtime bindings to update text. */
/* ------------------------------------------------------------------ */

void ui_render_textbox(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }
    if (ops->draw_hline && w->height > 2 && w->width > 2) {
        ops->draw_hline(ops->ctx, w->x + 1, w->y + w->height - 2, w->width - 2, muted);
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
                ops, ix, iy, iw, ih, w->text, fg,
                w->align, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Progressbar                                                        */
/* ------------------------------------------------------------------ */

void ui_render_progressbar(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    int inner_x = w->x + 1;
    int inner_y = w->y + 1;
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
        uint8_t hi_fill = fill;
        uint8_t lo_fill = ui_gray4_add(fill, -4);
        ui_dither_fill_h(ops, inner_x, inner_y, filled, inner_h, hi_fill, lo_fill);
        int edge_x = inner_x + filled - 1;
        for (int row = 0; row < inner_h; ++row) {
            ui_draw_pixel(ops, edge_x, inner_y + row, fg);
        }
    }
    ui_draw_rect_outline(ops, inner_x, inner_y, inner_w, inner_h, ui_gray4_add(bg, 2));

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int inset = w->border ? 1 : 0;
        int pad = 1;
        int ix = w->x + inset + pad;
        int iy = w->y + inset + pad;
        int iw = w->width - (inset + pad) * 2;
        int ih = w->height - (inset + pad) * 2;
        if (iw > 0 && ih >= UI_FONT_CHAR_H) {
            ui_draw_text_block(
                ops, ix, iy, iw, ih, w->text, fg,
                w->align, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Checkbox                                                           */
/* ------------------------------------------------------------------ */

void ui_render_checkbox(const UiWidget *w, const UiDrawOps *ops)
{
    if (w->height < 4 || w->width < 4) return;

    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    int box = (w->height > 6) ? 6 : (w->height - 2);
    if (box < 4) box = w->height - 2;
    if (box < 2) box = 2;
    int bx = w->x + 1;
    int by = w->y + (w->height - box) / 2;
    ui_fill_rect(ops, bx, by, box, box, bg);
    ui_draw_rect_outline(ops, bx, by, box, box, border);

    if (w->checked && box >= 4) {
        if (ops->draw_hline) {
            int inset = 2;
            int xw = box - inset * 2;
            if (xw < 2) { inset = 1; xw = box - 2; }
            for (int i = 0; i < xw; ++i) {
                int y = by + inset + i;
                int xa = bx + inset + i;
                int xb = bx + box - 1 - inset - i;
                ops->draw_hline(ops->ctx, xa, y, 1, fg);
                if (xb != xa)
                    ops->draw_hline(ops->ctx, xb, y, 1, fg);
            }
        }
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int tx = bx + box + 2;
        int max_w = (w->x + w->width) - tx - 1;
        if (max_w > 0) {
            ui_draw_text_block(
                ops, tx, w->y, max_w, w->height, w->text, fg,
                UI_ALIGN_LEFT, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Radiobutton                                                        */
/* ------------------------------------------------------------------ */

void ui_render_radiobutton(const UiWidget *w, const UiDrawOps *ops)
{
    if (w->height < 4 || w->width < 4) return;

    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);
    int box = (w->height > 6) ? 6 : (w->height - 2);
    if (box < 2) box = 2;
    int bx = w->x + 1;
    int by = w->y + (w->height - box) / 2;
    ui_fill_rect(ops, bx, by, box, box, bg);
    ui_draw_rect_outline(ops, bx, by, box, box, border);

    if (w->checked && box >= 4) {
        ui_fill_rect(ops, bx + 2, by + 2, box - 4, box - 4, fg);
    }

    if (w->text && ops->draw_text && w->height >= UI_FONT_CHAR_H) {
        int tx = bx + box + 2;
        int max_w = (w->x + w->width) - tx - 1;
        if (max_w > 0) {
            ui_draw_text_block(
                ops, tx, w->y, max_w, w->height, w->text, fg,
                UI_ALIGN_LEFT, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Slider                                                             */
/* ------------------------------------------------------------------ */

void ui_render_slider(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    int inner_x = w->x + 2;
    int inner_w = w->width - 4;
    if (inner_w <= 0) return;

    int cy = w->y + (w->height / 2);

    int track_h = 2;
    int track_y = cy - track_h / 2;
    ui_fill_rect(ops, inner_x, track_y, inner_w, track_h, ui_gray4_add(bg, -2));
    ui_draw_rect_outline(ops, inner_x, track_y, inner_w, track_h, ui_gray4_add(bg, 1));

    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int val = w->value - w->min_value;
    if (val < 0) val = 0;
    if (val > range) val = range;
    int knob_x = inner_x + (int)(((int64_t)val * (inner_w - 1)) / range);

    int fill_w = knob_x - inner_x;
    if (fill_w > 0 && track_h > 0) {
        uint8_t hi_tr = fill;
        uint8_t lo_tr = ui_gray4_add(fill, -4);
        ui_dither_fill_h(ops, inner_x, track_y, fill_w, track_h, hi_tr, lo_tr);
    }

    int knob_w = 5;
    if (knob_w > inner_w) knob_w = inner_w;
    int knob_h = w->height - 4;
    if (knob_h < 3) knob_h = 3;
    int kx = knob_x - (knob_w / 2);
    if (kx < inner_x) kx = inner_x;
    if (kx + knob_w > inner_x + inner_w) kx = inner_x + inner_w - knob_w;
    int ky = w->y + (w->height - knob_h) / 2;
    ui_fill_rect(ops, kx, ky, knob_w, knob_h, ui_gray4_add(fill, 1));
    ui_draw_rect_outline(ops, kx, ky, knob_w, knob_h, border);

    int grip_x = kx + knob_w / 2;
    if (ops->draw_vline && knob_h > 4) {
        ops->draw_vline(ops->ctx, grip_x, ky + 2, knob_h - 4, ui_gray4_add(bg, 3));
    }
}

/* ------------------------------------------------------------------ */
/*  Gauge                                                              */
/* ------------------------------------------------------------------ */

void ui_render_gauge(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }
    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }

    int inner_w = w->width - 2;
    int inner_h = w->height - 2;
    if (inner_w <= 0 || inner_h <= 0) return;

    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int val = w->value - w->min_value;
    if (val < 0) val = 0;
    if (val > range) val = range;
    int pct256 = (int)(((int64_t)val * 256) / range);

    int compact = (inner_h < 30);
    int label_h = 0;
    int bottom_reserve = 0;
    if (compact) {
        if (w->text) bottom_reserve = UI_FONT_CHAR_H + 1;
    } else {
        if (w->text && inner_h > UI_FONT_CHAR_H * 3) label_h = UI_FONT_CHAR_H + 1;
    }
    int natural_gauge_h = inner_h - label_h - bottom_reserve;
    int use_arc = 1;
    if (compact && bottom_reserve > 0 && natural_gauge_h < 5) {
        use_arc = 0;
    }
    int gauge_h = natural_gauge_h;
    if (gauge_h < 8) gauge_h = 8;

    int radius_check = inner_w / 2 - 1;
    if (radius_check > gauge_h - 1) radius_check = gauge_h - 1;
    if (radius_check < 4) radius_check = 4;

    if (radius_check >= 5 && use_arc) {
        int cx = w->x + w->width / 2;
        int cy = w->y + 1 + label_h + gauge_h - 1;
        int radius = radius_check;
        int arc_thick = compact ? (radius / 4) : (radius / 3);
        if (arc_thick < 2) arc_thick = 2;
        int end_deg = (int)((int64_t)pct256 * 180 / 256);

        /* Outer rim */
        uint8_t rim_c = ui_gray4_add(bg, 3);
        for (int deg = 0; deg <= 180; ++deg) {
            double a = deg * M_PI / 180.0;
            int px = cx + (int)((radius + 1) * cos(M_PI - a));
            int py = cy - (int)((radius + 1) * sin(M_PI - a));
            if (py <= cy) ui_draw_pixel(ops, px, py, rim_c);
        }

        /* Inner rim */
        uint8_t inner_rim_c = ui_gray4_add(bg, 2);
        int inner_r = radius - arc_thick;
        for (int deg = 0; deg <= 180; ++deg) {
            double a = deg * M_PI / 180.0;
            int px = cx + (int)(inner_r * cos(M_PI - a));
            int py = cy - (int)(inner_r * sin(M_PI - a));
            if (py <= cy) ui_draw_pixel(ops, px, py, inner_rim_c);
        }

        /* Inactive arc */
        uint8_t hi_inactive = ui_gray4_add(bg, 3);
        uint8_t lo_inactive = ui_gray4_add(bg, 2);
        for (int r_off = 0; r_off < arc_thick; ++r_off) {
            int r_cur = radius - r_off;
            if (r_cur < 1) break;
            for (int deg = 0; deg <= 180; ++deg) {
                double a = deg * M_PI / 180.0;
                int px = cx + (int)(r_cur * cos(M_PI - a));
                int py = cy - (int)(r_cur * sin(M_PI - a));
                if (py > cy) continue;
                ui_dither_pixel(ops, px, py, hi_inactive, lo_inactive, 8);
            }
        }

        /* Active arc */
        if (end_deg > 0) {
            for (int r_off = 0; r_off < arc_thick; ++r_off) {
                int r_cur = radius - r_off;
                if (r_cur < 1) break;
                int r_ratio = (arc_thick > 1) ? (int)((int64_t)(arc_thick - 1 - r_off) * 16 / (arc_thick - 1)) : 16;
                uint8_t hi = ui_gray4_add(fg, -1 - (int)(3 * r_off / arc_thick));
                uint8_t lo = ui_gray4_add(fg, -4 - (int)(3 * r_off / arc_thick));
                for (int deg = 0; deg <= end_deg; ++deg) {
                    double a = deg * M_PI / 180.0;
                    int px = cx + (int)(r_cur * cos(M_PI - a));
                    int py = cy - (int)(r_cur * sin(M_PI - a));
                    if (py > cy) continue;
                    ui_dither_pixel(ops, px, py, hi, lo, r_ratio);
                }
            }
            for (int deg = 0; deg <= end_deg; ++deg) {
                double a = deg * M_PI / 180.0;
                int px = cx + (int)((radius + 1) * cos(M_PI - a));
                int py = cy - (int)((radius + 1) * sin(M_PI - a));
                if (py <= cy) ui_draw_pixel(ops, px, py, ui_gray4_add(fg, -2));
            }
        }

        /* Scale marks */
        for (int m = 0; m <= 4; ++m) {
            double mark_a = M_PI * (1.0 - m * 0.25);
            int mr = radius + 2;
            int mx = cx + (int)(mr * cos(mark_a));
            int my = cy - (int)(mr * sin(mark_a));
            if (my > cy) my = cy;
            uint8_t tick_c = (m == 2) ? ui_gray4_add(muted, 3) : muted;
            if (my <= cy) ui_draw_pixel(ops, mx, my, tick_c);
        }

        /* Baseline */
        uint8_t base_c = ui_gray4_add(bg, 2);
        int left_x = cx - radius - 1;
        int right_x = cx + radius + 1;
        for (int bx = left_x; bx <= right_x; ++bx) {
            ui_draw_pixel(ops, bx, cy, base_c);
        }

        /* Needle */
        int needle_r = radius - arc_thick - 2;
        if (needle_r < 3) needle_r = 3;
        double needle_a = M_PI * (1.0 - (double)pct256 / 256.0);
        int nx = cx + (int)(needle_r * cos(needle_a));
        int ny = cy - (int)(needle_r * sin(needle_a));
        if (ny > cy) ny = cy;
        {
            int dx = (nx > cx) ? (nx - cx) : (cx - nx);
            int dy = (ny > cy) ? (ny - cy) : (cy - ny);
            int steps = (dx > dy) ? dx : dy;
            if (steps == 0) steps = 1;
            uint8_t needle_c = ui_gray4_add(fg, -1);
            for (int s = 0; s <= steps; ++s) {
                int px = cx + (nx - cx) * s / steps;
                int py = cy + (ny - cy) * s / steps;
                if (py <= cy)
                    ui_draw_pixel(ops, px, py, needle_c);
            }
            if (ny <= cy)
                ui_draw_pixel(ops, nx, ny, fg);
        }
        /* Hub dot */
        ui_draw_pixel(ops, cx, cy, fg);
        ui_draw_pixel(ops, cx - 1, cy, ui_gray4_add(fg, -3));
        ui_draw_pixel(ops, cx + 1, cy, ui_gray4_add(fg, -3));
        ui_draw_pixel(ops, cx, cy - 1, ui_gray4_add(fg, -3));

        /* Value text centered inside arc (skip for compact) */
        if (!compact && ops->draw_text) {
            char vbuf[8];
            int raw_val = (int)w->value;
            int vlen = snprintf(vbuf, sizeof(vbuf), "%d", raw_val);
            if (vlen > 0 && vlen < (int)sizeof(vbuf)) {
                int tw = vlen * UI_FONT_CHAR_W;
                int tx = cx - tw / 2;
                int ty = cy - needle_r * 2 / 5 - UI_FONT_CHAR_H / 2;
                if (ty >= w->y + 1 && ty + UI_FONT_CHAR_H <= w->y + w->height - 1) {
                    int pad_x = 1;
                    int px = tx - pad_x;
                    int pw = tw + pad_x * 2;
                    if (ops->fill_rect) {
                        ops->fill_rect(ops->ctx, px, ty, pw, UI_FONT_CHAR_H, bg);
                    }
                    ops->draw_text(ops->ctx, tx, ty, vbuf, fg);
                }
            }
        }

        /* Label */
        if (w->text && ops->draw_text) {
            if (compact) {
                int ly = cy + 1;
                if (ly + UI_FONT_CHAR_H <= w->y + w->height - (w->border ? 1 : 0)) {
                    ui_draw_text_line_in_rect(
                        ops, w->x + 1, ly, inner_w, w->text, fg,
                        UI_ALIGN_CENTER, 0);
                }
            } else if (label_h > 0) {
                ui_draw_text_line_in_rect(
                    ops, w->x + 1, w->y + 1, inner_w, w->text, fg,
                    UI_ALIGN_CENTER, 0);
            }
        }
    } else {
        /* Fallback: simple fill bar for small gauges */
        int filled = (int)(((int64_t)val * inner_w) / range);
        if (filled > 0) {
            ui_fill_rect(ops, w->x + 1, w->y + 1, filled, inner_h, fill);
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
                    ops, ix, iy, iw, ih, w->text, fg,
                    UI_ALIGN_LEFT, UI_VALIGN_TOP, w->text_overflow, (int)w->max_lines);
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Icon                                                               */
/* ------------------------------------------------------------------ */

void ui_render_icon(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }
    if (w->border) {
        ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
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
                    ops->ctx, dx, dy,
                    (int)ic->width, (int)ic->height, (int)ic->stride_bytes,
                    ic->data, fg, 0);
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
        if (iw > 0 && ih >= UI_FONT_CHAR_H) {
            ui_draw_text_block(
                ops, ix, iy, iw, ih, buf, fg,
                UI_ALIGN_CENTER, UI_VALIGN_MIDDLE, UI_TEXT_OVERFLOW_CLIP, 1);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Chart                                                              */
/* ------------------------------------------------------------------ */

void ui_render_chart(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border, muted, fill;
    widget_colors(w, &fg, &bg, &border, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border);
    }
    int inner_x = w->x + 1;
    int inner_y = w->y + 1;
    int inner_w = w->width - 2;
    int inner_h = w->height - 2;
    if (inner_w <= 0 || inner_h <= 0) return;
    if (inner_w < 8 || inner_h < 8) return;

    int chart_x = inner_x + 3;
    int chart_y = inner_y + 2;
    int chart_w = inner_w - 5;
    int chart_h = inner_h - 5;
    if (chart_w < 4 || chart_h < 4) return;

    /* Dotted horizontal grid lines */
    if (ops->draw_hline) {
        for (int g = 1; g <= 3; ++g) {
            int gy = chart_y + chart_h - (int)((int64_t)chart_h * g * 25 / 100);
            for (int gx = chart_x; gx < chart_x + chart_w; gx += 4) {
                ui_draw_pixel(ops, gx, gy, ui_gray4_add(bg, 1));
            }
        }
    }

    /* Y-axis tick marks */
    for (int g = 0; g <= 4; ++g) {
        int ty = chart_y + chart_h - (int)((int64_t)chart_h * g * 25 / 100);
        ui_draw_pixel(ops, chart_x - 1, ty, muted);
        ui_draw_pixel(ops, chart_x - 2, ty, muted);
    }

    /* Axes */
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, chart_x, chart_y + chart_h, chart_w, muted);
    }
    if (ops->draw_vline) {
        ops->draw_vline(ops->ctx, chart_x, chart_y, chart_h, muted);
    }

    /* Thin top/right border */
    if (ops->draw_hline) {
        ops->draw_hline(ops->ctx, chart_x, chart_y, chart_w, ui_gray4_add(bg, 1));
    }
    if (ops->draw_vline) {
        ops->draw_vline(ops->ctx, chart_x + chart_w, chart_y, chart_h + 1, ui_gray4_add(bg, 1));
    }

    /* Data bars with Bayer-dithered gradient + bright cap */
    int bars = 6;
    int gap = 2;
    int bar_w = (chart_w - (gap * (bars - 1))) / bars;
    if (bar_w < 1) bar_w = 1;
    while (bars > 1 && (bars * bar_w + (bars - 1) * gap) > chart_w) {
        bars--;
    }
    int range = (w->max_value - w->min_value);
    if (range <= 0) range = 1;
    int base = w->value - w->min_value;
    if (base < 0) base = 0;

    int max_bh = 0;
    int max_bi = 0;
    for (int i = 0; i < bars; ++i) {
        int v = (base + i * 11) % (range + 1);
        int bh = (int)(((int64_t)v * (chart_h - 2)) / range);
        int bx = chart_x + 1 + i * (bar_w + gap);
        int by = chart_y + chart_h - 1 - bh;
        if (bh <= 0) continue;

        if (bh > max_bh) {
            max_bh = bh;
            max_bi = i;
        }

        uint8_t hi_bar = fill;
        uint8_t lo_bar = ui_gray4_add(fill, -4);
        ui_dither_fill_v(ops, bx, by, bar_w, bh, hi_bar, lo_bar);
        for (int col = 0; col < bar_w; ++col) {
            ui_draw_pixel(ops, bx + col, by, fg);
        }
        for (int row = 0; row < bh; ++row) {
            ui_draw_pixel(ops, bx, by + row, ui_gray4_add(fill, 1));
        }
    }
    /* Peak indicator dot */
    if (max_bh > 0) {
        int pbx = chart_x + 1 + max_bi * (bar_w + gap) + bar_w / 2;
        int pby = chart_y + chart_h - 1 - max_bh - 2;
        if (pby >= chart_y) {
            ui_draw_pixel(ops, pbx, pby, fg);
        }
    }

    /* X-axis tick marks */
    for (int i = 0; i < bars; ++i) {
        int tx = chart_x + 1 + i * (bar_w + gap) + bar_w / 2;
        ui_draw_pixel(ops, tx, chart_y + chart_h + 1, muted);
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
                ops, ix, iy, iw, ih, w->text, fg,
                w->align, w->valign, w->text_overflow, (int)w->max_lines);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  List (scrollable, newline-separated items)                         */
/* ------------------------------------------------------------------ */

void ui_render_list(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border_c, muted, fill;
    widget_colors(w, &fg, &bg, &border_c, &muted, &fill);

    uint8_t bstyle = w->border_style;
    if (bstyle == UI_BORDER_NONE && w->border) {
        bstyle = UI_BORDER_SINGLE;
    }

    ui_fill_rect(ops, w->x, w->y, w->width, w->height, bg);
    if (w->border) {
        ui_draw_border_style(ops, w->x, w->y, w->width, w->height, bstyle, border_c);
    }

    if (!w->text || !ops->draw_text) return;

    int inset = w->border ? 1 : 0;
    int pad = 1;
    int ix = w->x + inset + pad;
    int iy = w->y + inset + pad;
    int iw = w->width - (inset + pad) * 2;
    int ih = w->height - (inset + pad) * 2;
    if (iw <= 0 || ih < UI_FONT_CHAR_H) return;

    /* Count total items (newline-separated). */
    int total_items = 0;
    {
        const char *p = w->text;
        if (*p) {
            total_items = 1;
            while (*p) {
                if (*p == '\n') total_items++;
                p++;
            }
        }
    }
    if (total_items == 0) return;

    int visible_rows = ih / UI_FONT_CHAR_H;
    if (visible_rows <= 0) return;

    /* Scrollbar width reserved when items overflow. */
    int sb_w = 0;
    if (total_items > visible_rows) {
        sb_w = 3;
        if (sb_w >= iw) sb_w = 0; /* no room for scrollbar */
    }
    int text_w = iw - sb_w;
    if (text_w <= 0) return;
    int max_chars = text_w / UI_FONT_CHAR_W;
    if (max_chars <= 0) return;

    /* Scroll offset from min_value, clamped. */
    int scroll = w->min_value;
    if (scroll < 0) scroll = 0;
    if (scroll > total_items - visible_rows) scroll = total_items - visible_rows;
    if (scroll < 0) scroll = 0;

    /* Active/selected index from value, clamped. */
    int active = w->value;
    if (active < 0) active = 0;
    if (active >= total_items) active = total_items - 1;

    /* Walk text to the scroll offset. */
    const char *p = w->text;
    for (int skip = 0; skip < scroll && *p; skip++) {
        while (*p && *p != '\n') p++;
        if (*p == '\n') p++;
    }

    /* Draw visible rows. */
    char line_buf[64];
    for (int row = 0; row < visible_rows && *p; row++) {
        int item_idx = scroll + row;
        /* Extract item text up to next newline. */
        int len = 0;
        const char *start = p;
        while (*p && *p != '\n') {
            p++;
            len++;
        }
        if (*p == '\n') p++;

        /* Truncate to buffer with optional ellipsis. */
        int copy = len;
        if (copy > max_chars) copy = max_chars;
        if (copy >= (int)sizeof(line_buf)) copy = (int)sizeof(line_buf) - 1;
        for (int c = 0; c < copy; c++) line_buf[c] = start[c];
        line_buf[copy] = '\0';

        int row_y = iy + row * UI_FONT_CHAR_H;

        if (item_idx == active) {
            /* Highlight active item: inverse fill + text. */
            ui_fill_rect(ops, ix, row_y, text_w, UI_FONT_CHAR_H, fg);
            ops->draw_text(ops->ctx, ix + 1, row_y, line_buf, bg);
        } else {
            ops->draw_text(ops->ctx, ix + 1, row_y, line_buf, fg);
        }
    }

    /* Scrollbar (thin track + thumb on right edge). */
    if (sb_w > 0 && total_items > visible_rows) {
        int sb_x = ix + text_w + 1;
        int sb_h = ih;
        /* Track */
        if (ops->draw_vline) {
            ops->draw_vline(ops->ctx, sb_x, iy, sb_h, ui_gray4_add(bg, 2));
        }
        /* Thumb */
        int thumb_h = (int)((int64_t)visible_rows * sb_h / total_items);
        if (thumb_h < 2) thumb_h = 2;
        if (thumb_h > sb_h) thumb_h = sb_h;
        int thumb_y = iy + (int)((int64_t)scroll * (sb_h - thumb_h) /
                                  (total_items - visible_rows));
        if (thumb_y < iy) thumb_y = iy;
        if (thumb_y + thumb_h > iy + sb_h) thumb_y = iy + sb_h - thumb_h;
        if (ops->draw_vline) {
            for (int tx = 0; tx < sb_w - 1; tx++) {
                ops->draw_vline(ops->ctx, sb_x + tx, thumb_y, thumb_h, fill);
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Toggle / Switch                                                    */
/* ------------------------------------------------------------------ */

void ui_render_toggle(const UiWidget *w, const UiDrawOps *ops)
{
    uint8_t fg, bg, border_c, muted, fill;
    widget_colors(w, &fg, &bg, &border_c, &muted, &fill);

    /* Track dimensions: pill shape, height = widget height, width ~ 2*height. */
    int track_h = (int)w->height;
    if (track_h < 4) track_h = 4;
    int track_w = track_h * 2;

    /* If text label present, draw track on the right side. */
    int tx = (int)w->x;
    if (w->text && w->text[0] != '\0' && ops->draw_text) {
        int avail = (int)w->width - track_w - 2;
        if (avail > 0) {
            ui_draw_text_block(
                ops, (int)w->x, (int)w->y, avail, (int)w->height, w->text, fg,
                UI_ALIGN_LEFT, w->valign, w->text_overflow, (int)w->max_lines);
        }
        tx = (int)w->x + (int)w->width - track_w;
    } else {
        /* Center track in widget. */
        if (track_w < (int)w->width) {
            tx = (int)w->x + ((int)w->width - track_w) / 2;
        }
    }

    int ty = (int)w->y + ((int)w->height - track_h) / 2;

    /* Draw track background. */
    uint8_t track_col = w->checked ? fill : ui_gray4_add(bg, 2);
    ui_fill_rect(ops, tx, ty, track_w, track_h, track_col);
    ui_draw_rect_outline(ops, tx, ty, track_w, track_h, border_c);

    /* Draw knob (filled square). */
    int knob_size = track_h - 2;
    if (knob_size < 2) knob_size = 2;
    int knob_y = ty + 1;
    int knob_x;
    if (w->checked) {
        knob_x = tx + track_w - knob_size - 1;
    } else {
        knob_x = tx + 1;
    }
    ui_fill_rect(ops, knob_x, knob_y, knob_size, knob_size, fg);
}
