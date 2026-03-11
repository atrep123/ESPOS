#include "ui_meta.h"

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

static void ui_meta_reset(ui_meta_t *m)
{
    if (m == NULL) {
        return;
    }
    memset(m, 0, sizeof(*m));
    m->kind = UI_META_KIND_NONE;
    m->step = 1;
    m->precision = -1;  /* -1 = use default (2 for float) */
    m->scale = 0;       /*  0 = use default (100)         */
}

static const char *skip_ws(const char *p)
{
    while (p && *p && isspace((unsigned char)*p)) {
        p++;
    }
    return p;
}

static void rstrip_ws(const char *start, const char **end_io)
{
    const char *end = (end_io && *end_io) ? *end_io : start;
    while (end > start && isspace((unsigned char)end[-1])) {
        end--;
    }
    if (end_io) {
        *end_io = end;
    }
}

static int key_eq_ci(const char *key, size_t key_len, const char *want)
{
    if (key == NULL || want == NULL) {
        return 0;
    }
    size_t want_len = strlen(want);
    if (key_len != want_len) {
        return 0;
    }
    for (size_t i = 0; i < key_len; ++i) {
        char a = (char)tolower((unsigned char)key[i]);
        char b = (char)tolower((unsigned char)want[i]);
        if (a != b) {
            return 0;
        }
    }
    return 1;
}

static int parse_int_span(const char *s, size_t n, int *out)
{
    if (out == NULL) {
        return 0;
    }
    *out = 0;
    if (s == NULL || n == 0) {
        return 0;
    }

    char buf[24];
    if (n >= sizeof(buf)) {
        n = sizeof(buf) - 1;
    }
    memcpy(buf, s, n);
    buf[n] = '\0';

    char *end = NULL;
    errno = 0;
    long v = strtol(buf, &end, 10);
    if (end == buf || errno == ERANGE || v < INT_MIN || v > INT_MAX) {
        return 0;
    }
    *out = (int)v;
    return 1;
}

static ui_meta_kind_t parse_kind(const char *s, size_t n)
{
    if (s == NULL || n == 0) {
        return UI_META_KIND_NONE;
    }

    if (n >= 16) {
        n = 15;
    }
    char buf[16];
    memcpy(buf, s, n);
    buf[n] = '\0';
    for (size_t i = 0; i < n; ++i) {
        buf[i] = (char)tolower((unsigned char)buf[i]);
    }

    if (strcmp(buf, "bool") == 0 || strcmp(buf, "boolean") == 0) {
        return UI_META_KIND_BOOL;
    }
    if (strcmp(buf, "int") == 0 || strcmp(buf, "i32") == 0 || strcmp(buf, "s32") == 0) {
        return UI_META_KIND_INT;
    }
    if (strcmp(buf, "enum") == 0 || strcmp(buf, "choice") == 0 || strcmp(buf, "list") == 0) {
        return UI_META_KIND_ENUM;
    }
    if (strcmp(buf, "str") == 0 || strcmp(buf, "string") == 0) {
        return UI_META_KIND_STR;
    }
    if (strcmp(buf, "float") == 0 || strcmp(buf, "f32") == 0 || strcmp(buf, "double") == 0) {
        return UI_META_KIND_FLOAT;
    }
    return UI_META_KIND_NONE;
}

bool ui_meta_parse(const char *s, ui_meta_t *out)
{
    ui_meta_reset(out);
    if (s == NULL || *s == '\0' || out == NULL) {
        return false;
    }

    const char *p = s;
    while (*p) {
        while (*p == ';') {
            p++;
        }
        p = skip_ws(p);
        if (*p == '\0') {
            break;
        }

        const char *seg = p;
        while (*p && *p != ';') {
            p++;
        }
        const char *seg_end = p;

        const char *eq = NULL;
        for (const char *q = seg; q < seg_end; ++q) {
            if (*q == '=') {
                eq = q;
                break;
            }
        }
        if (eq == NULL) {
            continue;
        }

        const char *k0 = seg;
        const char *k1 = eq;
        const char *v0 = eq + 1;
        const char *v1 = seg_end;
        k0 = skip_ws(k0);
        rstrip_ws(k0, &k1);
        if (k0 >= k1) {
            continue;
        }
        size_t klen = (size_t)(k1 - k0);

        /* prefix/suffix: preserve raw value (leading spaces are content) */
        if (key_eq_ci(k0, klen, "suffix") || key_eq_ci(k0, klen, "unit")) {
            size_t n = (size_t)(v1 - v0);
            if (n >= sizeof(out->suffix)) {
                n = sizeof(out->suffix) - 1;
            }
            memcpy(out->suffix, v0, n);
            out->suffix[n] = '\0';
            continue;
        }
        if (key_eq_ci(k0, klen, "prefix")) {
            size_t n = (size_t)(v1 - v0);
            if (n >= sizeof(out->prefix)) {
                n = sizeof(out->prefix) - 1;
            }
            memcpy(out->prefix, v0, n);
            out->prefix[n] = '\0';
            continue;
        }

        /* Strip value whitespace for remaining fields */
        v0 = skip_ws(v0);
        rstrip_ws(v0, &v1);
        if (v0 >= v1) {
            continue;
        }

        size_t vlen = (size_t)(v1 - v0);

        if (key_eq_ci(k0, klen, "bind") || key_eq_ci(k0, klen, "key")) {
            size_t n = vlen;
            if (n >= sizeof(out->bind_key)) {
                n = sizeof(out->bind_key) - 1;
            }
            memcpy(out->bind_key, v0, n);
            out->bind_key[n] = '\0';
            continue;
        }

        if (key_eq_ci(k0, klen, "kind") || key_eq_ci(k0, klen, "type")) {
            ui_meta_kind_t k = parse_kind(v0, vlen);
            if (k != UI_META_KIND_NONE) {
                out->kind = k;
            }
            continue;
        }

        if (key_eq_ci(k0, klen, "min")) {
            int v = 0;
            if (parse_int_span(v0, vlen, &v)) {
                out->min = v;
                out->has_min = 1;
            }
            continue;
        }
        if (key_eq_ci(k0, klen, "max")) {
            int v = 0;
            if (parse_int_span(v0, vlen, &v)) {
                out->max = v;
                out->has_max = 1;
            }
            continue;
        }
        if (key_eq_ci(k0, klen, "step")) {
            int v = 0;
            if (parse_int_span(v0, vlen, &v)) {
                out->step = (v == 0) ? 1 : v;
                out->has_step = 1;
            }
            continue;
        }
        if (key_eq_ci(k0, klen, "values")) {
            size_t n = vlen;
            if (n >= sizeof(out->values)) {
                n = sizeof(out->values) - 1;
            }
            memcpy(out->values, v0, n);
            out->values[n] = '\0';
            continue;
        }
        if (key_eq_ci(k0, klen, "precision") || key_eq_ci(k0, klen, "decimals")) {
            int v = 0;
            if (parse_int_span(v0, vlen, &v)) {
                if (v < 0) v = 0;
                if (v > 6) v = 6;
                out->precision = v;
            }
            continue;
        }
        if (key_eq_ci(k0, klen, "scale") || key_eq_ci(k0, klen, "divisor")) {
            int v = 0;
            if (parse_int_span(v0, vlen, &v)) {
                if (v > 0) {
                    out->scale = v;
                }
            }
            continue;
        }
    }

    if (out->bind_key[0] == '\0') {
        return false;
    }

    if (out->kind == UI_META_KIND_NONE) {
        out->kind = (out->values[0] != '\0') ? UI_META_KIND_ENUM : UI_META_KIND_INT;
    }

    return true;
}

int ui_meta_values_count(const char *values)
{
    if (values == NULL) {
        return 0;
    }
    const char *p = values;
    int count = 0;
    for (;;) {
        p = skip_ws(p);
        if (*p == '\0') {
            break;
        }
        const char *seg = p;
        while (*p && *p != '|') {
            p++;
        }
        const char *seg_end = p;
        rstrip_ws(seg, &seg_end);
        if (seg < seg_end) {
            count += 1;
        }
        if (*p == '|') {
            p++;
            continue;
        }
        break;
    }
    return count;
}

bool ui_meta_values_get(const char *values, int index, char *out, size_t out_cap)
{
    if (out == NULL || out_cap == 0) {
        return false;
    }
    out[0] = '\0';
    if (values == NULL || index < 0) {
        return false;
    }

    const char *p = values;
    int cur = 0;
    for (;;) {
        p = skip_ws(p);
        if (*p == '\0') {
            break;
        }
        const char *seg = p;
        while (*p && *p != '|') {
            p++;
        }
        const char *seg_end = p;
        rstrip_ws(seg, &seg_end);
        if (seg < seg_end) {
            if (cur == index) {
                size_t n = (size_t)(seg_end - seg);
                if (n >= out_cap) {
                    n = out_cap - 1;
                }
                memcpy(out, seg, n);
                out[n] = '\0';
                return true;
            }
            cur += 1;
        }
        if (*p == '|') {
            p++;
            continue;
        }
        break;
    }
    return false;
}
