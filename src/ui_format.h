#pragma once

#include <stddef.h>
#include "services/ui/ui_meta.h"

/*
 * Pure value formatting for bound widgets.
 * Given metadata (kind, prefix/suffix, precision, scale, etc.) and
 * the raw value from a binding, format it into a display string.
 * No FreeRTOS, binding lookups, or scene dependencies.
 */

/* Format a raw value based on meta->kind into buf.
 *   int_val   — used for KIND_INT, KIND_ENUM, KIND_FLOAT
 *   bool_val  — used for KIND_BOOL (0 or 1)
 *   str_val   — used for KIND_STR (may be NULL)
 * Returns 1 on success, 0 if kind is NONE or unknown. */
int ui_format_meta_value(const ui_meta_t *meta,
                         int int_val, int bool_val,
                         const char *str_val,
                         char *buf, size_t buf_sz);

/* Compose "label: value" into buf.
 * Returns the number of characters written (excluding NUL). */
int ui_format_label_value(const char *label, const char *value,
                          char *buf, size_t buf_sz);
