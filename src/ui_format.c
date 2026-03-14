#include "ui_format.h"

#include <stdio.h>
#include <string.h>
#include <stdint.h>

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
            snprintf(buf, buf_sz, "%s", bool_val ? "on" : "off");
        }
    } else if (meta->kind == UI_META_KIND_INT) {
        if (meta->prefix[0] != '\0' || meta->suffix[0] != '\0') {
            snprintf(buf, buf_sz, "%s%d%s",
                     meta->prefix, int_val, meta->suffix);
        } else {
            snprintf(buf, buf_sz, "%d", int_val);
        }
    } else if (meta->kind == UI_META_KIND_ENUM) {
        int cnt = ui_meta_values_count(meta->values);
        if (cnt <= 0) {
            snprintf(buf, buf_sz, "%d", int_val);
        } else {
            int cur = int_val;
            if (cur < 0) cur = 0;
            if (cur >= cnt) cur = cnt - 1;
            if (!ui_meta_values_get(meta->values, cur, buf, buf_sz)) {
                snprintf(buf, buf_sz, "%d", int_val);
            }
        }
    } else if (meta->kind == UI_META_KIND_STR) {
        if (str_val != NULL) {
            snprintf(buf, buf_sz, "%s", str_val);
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
            snprintf(buf, buf_sz, "%s%d%s",
                     meta->prefix, rounded, meta->suffix);
        } else {
            int pow10 = 1;
            for (int i = 0; i < prec; i++) pow10 *= 10;
            int frac_scaled = (int)(((int64_t)frac * pow10) / sc);

            if (int_val < 0 && whole == 0) {
                snprintf(buf, buf_sz, "%s-%d.%0*d%s",
                         meta->prefix, whole, prec, frac_scaled, meta->suffix);
            } else {
                snprintf(buf, buf_sz, "%s%d.%0*d%s",
                         meta->prefix, whole, prec, frac_scaled, meta->suffix);
            }
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
    return snprintf(buf, buf_sz, "%s: %s", label, value);
}
