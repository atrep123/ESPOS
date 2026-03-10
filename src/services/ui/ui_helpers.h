#pragma once

/**
 * @file ui_helpers.h
 * Pure-logic helpers extracted from ui.c for testability.
 *
 * Contains: string parsing, toast queue (push/pop/reset).
 */

#include <stddef.h>
#include <stdint.h>

/* ---- String parsing ---- */

/**
 * Parse an unsigned decimal integer from the start of @p s.
 * Returns 1 on success (at least one digit), 0 on failure.
 * Stops at the first non-digit; detects overflow (wrapping).
 */
int ui_parse_uint_dec(const char *s, int *out_value);

/**
 * Parse an ID like "root.itemN" into root prefix + slot index.
 * Returns 1 on success, 0 on malformed input.
 */
int ui_parse_item_root_slot(const char *id, char *root_out, size_t root_cap, int *out_slot);

/* ---- Toast queue ---- */

enum { UI_TOAST_QUEUE_LEN = 4 };
enum { UI_TOAST_MSG_LEN = 64 };

typedef struct {
    char message[UI_TOAST_MSG_LEN];
    uint32_t duration_ms;
} UiToastItem;

typedef struct {
    uint8_t active;
    int64_t expires_us;
    char root[32];
    UiToastItem q[UI_TOAST_QUEUE_LEN];
    uint8_t head;
    uint8_t count;
} UiToast;

void ui_toast_reset(UiToast *toast);
void ui_toast_queue_push(UiToast *toast, const char *message, uint32_t duration_ms);
int  ui_toast_queue_pop(UiToast *toast, UiToastItem *out_item);
