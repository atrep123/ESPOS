/*
 * Pure-logic input helpers (no hardware dependencies).
 *
 * Extracted from input.c so they can be independently tested in native builds
 * without requiring GPIO, FreeRTOS, or msgbus stubs.
 */

#include "services/input/input.h"
#include <stddef.h>

int input_debounce_update(input_btn_state_t *st, int raw_level, int threshold)
{
    if (st == NULL || threshold < 1) {
        return 0;
    }
    if (raw_level != st->stable) {
        st->cnt += 1;
        if (st->cnt >= threshold) {
            st->stable = raw_level;
            st->cnt = 0;
        }
    } else {
        st->cnt = 0;
    }
    int changed = (st->stable != st->last);
    if (changed) {
        st->last = st->stable;
    }
    return changed;
}

int input_encoder_step(uint8_t *prev_ab, int *accum, int a, int b)
{
    static const int8_t trans[16] = {
        0, -1, +1, 0,
        +1, 0, 0, -1,
        -1, 0, 0, +1,
        0, +1, -1, 0,
    };
    if (prev_ab == NULL || accum == NULL) {
        return 0;
    }
    uint8_t ab = (uint8_t)(((a ? 1 : 0) << 1) | (b ? 1 : 0));
    uint8_t idx = (uint8_t)(((*prev_ab & 0x03) << 2) | (ab & 0x03));
    int8_t step = trans[idx];
    *prev_ab = ab;
    if (step != 0) {
        *accum += (int)step;
        if (*accum >= 4) {
            *accum = 0;
            return 1;
        } else if (*accum <= -4) {
            *accum = 0;
            return -1;
        }
    }
    return 0;
}

int input_axis_update(int value, int center, int deadzone, int hyst, int *state)
{
    if (state == NULL) {
        return 0;
    }
    int s = *state;
    if (s < 0) {
        if (value >= (center - deadzone + hyst)) {
            s = 0;
        }
    } else if (s > 0) {
        if (value <= (center + deadzone - hyst)) {
            s = 0;
        }
    } else {
        if (value <= (center - deadzone)) {
            s = -1;
        } else if (value >= (center + deadzone)) {
            s = 1;
        }
    }
    int changed = (s != *state);
    *state = s;
    return changed;
}
