/*
 * Pure text-layout helpers — no display backend, no FreeRTOS.
 * Extracted from ui_render.c for testability.
 */

#include "ui_render_text.h"

#include <string.h>

uint8_t ui_gray4_add(uint8_t v, int delta)
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

static int ui_is_space(char ch)
{
    return (ch == ' ') || (ch == '\t') || (ch == '\r');
}

void ui_flatten_one_line(const char *in, char *out, int out_cap)
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

int ui_fit_line_buf(const char *text, int max_chars, int use_ellipsis,
                    char *out, int out_cap)
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

int ui_wrap_next_line(const char **pp, char *out, int out_cap, int max_chars)
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

int ui_count_wrap_lines(const char *text, int max_chars, int max_lines,
                        int *truncated)
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
