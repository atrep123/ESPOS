#pragma once

#include <stdint.h>

/*
 * Pure text-layout helpers extracted from ui_render.c so they can be
 * unit-tested on the native platform without any display backend.
 */

/* Clamped 4-bit grayscale arithmetic: (v + delta) clamped to [0, 15]. */
uint8_t ui_gray4_add(uint8_t v, int delta);

/* Collapse multiline text to a single line: \n,\r,\t → space,
 * duplicate spaces removed, trailing spaces stripped. */
void ui_flatten_one_line(const char *in, char *out, int out_cap);

/* Truncate text to max_chars.  If use_ellipsis && text is too long,
 * append "..." within the budget.  Returns chars written (excl. NUL). */
int ui_fit_line_buf(const char *text, int max_chars, int use_ellipsis,
                    char *out, int out_cap);

/* Word-wrap: extract the next line from *pp (advancing the pointer).
 * Returns chars written (0 = end-of-text). */
int ui_wrap_next_line(const char **pp, char *out, int out_cap, int max_chars);

/* Count how many wrapped lines the text occupies (up to max_lines).
 * If truncated != NULL, sets *truncated = 1 when text overflows. */
int ui_count_wrap_lines(const char *text, int max_chars, int max_lines,
                        int *truncated);
