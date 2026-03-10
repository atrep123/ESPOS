#pragma once

#include <stdbool.h>
#include <stddef.h>

typedef enum {
    UI_META_KIND_NONE = 0,
    UI_META_KIND_BOOL = 1,
    UI_META_KIND_INT = 2,
    UI_META_KIND_ENUM = 3,
    UI_META_KIND_STR = 4,
    UI_META_KIND_FLOAT = 5,
} ui_meta_kind_t;

typedef struct {
    ui_meta_kind_t kind;
    char bind_key[24];

    int has_min;
    int has_max;
    int has_step;
    int min;
    int max;
    int step;

    char values[64];

    /* Display formatting (optional) */
    char suffix[16];    /* unit suffix, e.g. "°C", "%", "V"  */
    char prefix[16];    /* value prefix, e.g. "$", "#"       */
    int  precision;     /* decimal places for float (-1 = default 2) */
    int  scale;         /* fixed-point divisor for float (0 = default 100) */
} ui_meta_t;

/* Parse a runtime metadata string:
 *   "bind=contrast;kind=int;min=0;max=255;step=8"
 *   "bind=invert;kind=bool;values=off|on"
 *   "bind=mode;kind=enum;values=A|B|C"
 *   "bind=temp;kind=float;scale=10;precision=1;suffix=°C"
 */
bool ui_meta_parse(const char *s, ui_meta_t *out);

int ui_meta_values_count(const char *values);
bool ui_meta_values_get(const char *values, int index, char *out, size_t out_cap);

