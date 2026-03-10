#include "ui_helpers.h"

#include <string.h>

/* ---- String parsing ---- */

int ui_parse_uint_dec(const char *s, int *out_value)
{
    if (out_value != NULL) {
        *out_value = 0;
    }
    if (s == NULL || *s < '0' || *s > '9') {
        return 0;
    }
    int v = 0;
    const char *p = s;
    while (*p >= '0' && *p <= '9') {
        int next = v * 10 + (*p - '0');
        if (next < v) {
            break;
        }
        v = next;
        p += 1;
    }
    if (out_value != NULL) {
        *out_value = v;
    }
    return 1;
}

int ui_parse_item_root_slot(const char *id, char *root_out, size_t root_cap, int *out_slot)
{
    if (out_slot != NULL) {
        *out_slot = 0;
    }
    if (root_out != NULL && root_cap > 0) {
        root_out[0] = '\0';
    }
    if (id == NULL || *id == '\0' || root_out == NULL || root_cap == 0) {
        return 0;
    }

    const char *dot = strchr(id, '.');
    if (dot == NULL || dot == id || dot[1] == '\0') {
        return 0;
    }

    size_t root_len = (size_t)(dot - id);
    if (root_len >= root_cap) {
        root_len = root_cap - 1;
    }
    memcpy(root_out, id, root_len);
    root_out[root_len] = '\0';

    const char *role = dot + 1;
    if (strncmp(role, "item", 4) != 0) {
        return 0;
    }
    int slot = 0;
    if (!ui_parse_uint_dec(role + 4, &slot)) {
        return 0;
    }
    if (out_slot != NULL) {
        *out_slot = slot;
    }
    return 1;
}

/* ---- Toast queue ---- */

void ui_toast_reset(UiToast *toast)
{
    if (toast == NULL) {
        return;
    }
    toast->active = 0;
    toast->expires_us = 0;
    toast->root[0] = '\0';
    toast->head = 0;
    toast->count = 0;
    for (int i = 0; i < UI_TOAST_QUEUE_LEN; ++i) {
        toast->q[i].message[0] = '\0';
        toast->q[i].duration_ms = 0;
    }
}

void ui_toast_queue_push(UiToast *toast, const char *message, uint32_t duration_ms)
{
    if (toast == NULL) {
        return;
    }
    if (toast->count >= UI_TOAST_QUEUE_LEN) {
        toast->head = (uint8_t)((toast->head + 1U) % UI_TOAST_QUEUE_LEN);
        toast->count = (uint8_t)(toast->count - 1U);
    }
    uint8_t tail = (uint8_t)(((unsigned)toast->head + (unsigned)toast->count) % UI_TOAST_QUEUE_LEN);
    strncpy(toast->q[tail].message, message ? message : "", sizeof(toast->q[tail].message) - 1);
    toast->q[tail].message[sizeof(toast->q[tail].message) - 1] = '\0';
    toast->q[tail].duration_ms = duration_ms;
    toast->count = (uint8_t)(toast->count + 1U);
}

int ui_toast_queue_pop(UiToast *toast, UiToastItem *out_item)
{
    if (toast == NULL || toast->count == 0) {
        return 0;
    }
    if (out_item != NULL) {
        *out_item = toast->q[toast->head];
    }
    toast->head = (uint8_t)((toast->head + 1U) % UI_TOAST_QUEUE_LEN);
    toast->count = (uint8_t)(toast->count - 1U);
    return 1;
}
