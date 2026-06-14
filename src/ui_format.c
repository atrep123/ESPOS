#include "ui_format.h"

#include <stdio.h>
#include <string.h>
#include <stdint.h>

static size_t ui_format_append_trunc(char *dst, size_t dst_cap, size_t pos, const char *src)
{
    if (dst == NULL || dst_cap == 0) {
        return pos;
    }
    if (pos >= dst_cap) {
        dst[dst_cap - 1U] = '\0';
        return dst_cap - 1U;
    }
    if (src != NULL) {
        while (*src != '\0' && (pos + 1U) < dst_cap) {
            dst[pos] = *src;
            pos++;
            src++;
        }
    }
    dst[pos] = '\0';
    return pos;
}

static size_t ui_format_copy_trunc(char *dst, size_t dst_cap, const char *src)
{
    if (dst == NULL || dst_cap == 0) {
        return 0;
    }
    dst[0] = '\0';
    return ui_format_append_trunc(dst, dst_cap, 0, src);
}

static void ui_format_writef(char *dst, size_t dst_cap, const char *fmt,
                             const char *prefix, int value, const char *suffix)
{
    char tmp[64];

    tmp[0] = '\0';
    (void)snprintf(tmp, sizeof(tmp), fmt, prefix, value, suffix);
    (void)ui_format_copy_trunc(dst, dst_cap, tmp);
}

static void ui_format_write_float(char *dst, size_t dst_cap, const char *prefix,
                                  int whole, int precision, int frac_scaled,
                                  const char *suffix, int force_negative_zero)
{
    char tmp[80];

    tmp[0] = '\0';
    if (force_negative_zero) {
        (void)snprintf(tmp, sizeof(tmp), "%s-%d.%0*d%s",
                       prefix, whole, precision, frac_scaled, suffix);
    } else {
        (void)snprintf(tmp, sizeof(tmp), "%s%d.%0*d%s",
                       prefix, whole, precision, frac_scaled, suffix);
    }
    (void)ui_format_copy_trunc(dst, dst_cap, tmp);
}

int ui_format_meta_value(const ui_meta_t *meta,
                         int int_val, int bool_val,
                         const char *str_val,
                         char *buf, size_t buf_sz)
{
    if (meta == NULL || buf == NULL || buf_sz == 0) {
        return 0;
    }
    buf[0] = '\0';

    if (meta->kind == UI_META_KIND_BOOL) {
        if (meta->values[0] != '\0' && ui_meta_values_count(meta->values) >= 2) {
            (void)ui_meta_values_get(meta->values, bool_val ? 1 : 0, buf, buf_sz);
        } else {
            (void)ui_format_copy_trunc(buf, buf_sz, bool_val ? "on" : "off");
        }
    } else if (meta->kind == UI_META_KIND_INT) {
        if (meta->prefix[0] != '\0' || meta->suffix[0] != '\0') {
            ui_format_writef(buf, buf_sz, "%s%d%s", meta->prefix, int_val, meta->suffix);
        } else {
            ui_format_writef(buf, buf_sz, "%s%d%s", "", int_val, "");
        }
    } else if (meta->kind == UI_META_KIND_ENUM) {
        int cnt = ui_meta_values_count(meta->values);
        if (cnt <= 0) {
            ui_format_writef(buf, buf_sz, "%s%d%s", "", int_val, "");
        } else {
            int cur = int_val;
            if (cur < 0) cur = 0;
            if (cur >= cnt) cur = cnt - 1;
            if (!ui_meta_values_get(meta->values, cur, buf, buf_sz)) {
                ui_format_writef(buf, buf_sz, "%s%d%s", "", int_val, "");
            }
        }
    } else if (meta->kind == UI_META_KIND_STR) {
        if (str_val != NULL) {
            (void)ui_format_copy_trunc(buf, buf_sz, str_val);
        }
    } else if (meta->kind == UI_META_KIND_FLOAT) {
        int sc = (meta->scale > 0) ? meta->scale : 100;
        int prec = (meta->precision >= 0) ? meta->precision : 2;
        if (prec > 9) prec = 9;
        int whole = int_val / sc;
        int frac = int_val % sc;
        if (frac < 0) frac = -frac;

        if (prec == 0) {
            int rounded = whole;
            if (int_val >= 0 && frac >= sc / 2) rounded++;
            else if (int_val < 0 && frac >= sc / 2) rounded--;
            ui_format_writef(buf, buf_sz, "%s%d%s", meta->prefix, rounded, meta->suffix);
        } else {
            int pow10 = 1;
            for (int i = 0; i < prec; i++) pow10 *= 10;
            int frac_scaled = (int)(((int64_t)frac * pow10) / sc);

            ui_format_write_float(buf, buf_sz, meta->prefix, whole, prec, frac_scaled,
                                  meta->suffix, int_val < 0 && whole == 0);
        }
    } else {
        return 0;
    }

    return 1;
}

int ui_format_label_value(const char *label, const char *value,
                          char *buf, size_t buf_sz)
{
    if (buf == NULL || buf_sz == 0) {
        return 0;
    }
    if (label == NULL) label = "";
    if (value == NULL) value = "";
    buf[0] = '\0';
    size_t pos = 0;
    pos = ui_format_append_trunc(buf, buf_sz, pos, label);
    pos = ui_format_append_trunc(buf, buf_sz, pos, ": ");
    pos = ui_format_append_trunc(buf, buf_sz, pos, value);
    return (int)pos;
}
