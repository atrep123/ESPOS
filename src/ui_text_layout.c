#include "ui_text_layout.h"

#include <string.h>
#include "ui_render_text.h"

void ui_draw_text_line_in_rect(
    const UiDrawOps *ops,
    int x, int y, int w_px,
    const char *text,
    uint8_t fg,
    uint8_t align,
    int use_ellipsis)
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

void ui_draw_text_block(
    const UiDrawOps *ops,
    int x, int y, int w_px, int h_px,
    const char *text,
    uint8_t fg,
    uint8_t align,
    uint8_t valign,
    uint8_t overflow,
    int max_lines)
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
