/*
 * Pure application-layer helpers — no FreeRTOS, hardware, or msgbus
 * dependencies.  Extracted so they can be unit-tested on the native
 * platform without stubs.
 */

#include "ui_app.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include "services/input/input.h"

void ui_app_format_heap(char *out, size_t out_cap, uint32_t bytes)
{
    if (out == NULL || out_cap == 0) {
        return;
    }

    if (bytes >= (1024U * 1024U)) {
        snprintf(out, out_cap, "%" PRIu32 "M", bytes / (1024U * 1024U));
    } else if (bytes >= 1024U) {
        snprintf(out, out_cap, "%" PRIu32 "K", bytes / 1024U);
    } else {
        snprintf(out, out_cap, "%" PRIu32 "B", bytes);
    }
}

const char *ui_app_input_name(uint8_t id)
{
    switch (id) {
        case INPUT_ID_A: return "A";
        case INPUT_ID_B: return "B";
        case INPUT_ID_C: return "C";
        case INPUT_ID_UP: return "Up";
        case INPUT_ID_DOWN: return "Down";
        case INPUT_ID_LEFT: return "Left";
        case INPUT_ID_RIGHT: return "Right";
        case INPUT_ID_ENC: return "Enc";
        case INPUT_ID_ENC_PRESS: return "Enc press";
        case INPUT_ID_ENC_HOLD: return "Enc hold";
        case INPUT_ID_ENC_CW: return "Enc CW";
        case INPUT_ID_ENC_CCW: return "Enc CCW";
        case INPUT_ID_X: return "X";
        case INPUT_ID_Y: return "Y";
        case INPUT_ID_SELECT: return "Select";
        case INPUT_ID_START: return "Start";
        case INPUT_ID_ENC2: return "Enc2";
        case INPUT_ID_ENC2_PRESS: return "Enc2 press";
        case INPUT_ID_ENC2_HOLD: return "Enc2 hold";
        case INPUT_ID_ENC2_CW: return "Enc2 CW";
        case INPUT_ID_ENC2_CCW: return "Enc2 CCW";
        case INPUT_ID_ENC3: return "Enc3";
        case INPUT_ID_ENC3_PRESS: return "Enc3 press";
        case INPUT_ID_ENC3_HOLD: return "Enc3 hold";
        case INPUT_ID_ENC3_CW: return "Enc3 CW";
        case INPUT_ID_ENC3_CCW: return "Enc3 CCW";
        case INPUT_ID_ENC4: return "Enc4";
        case INPUT_ID_ENC4_PRESS: return "Enc4 press";
        case INPUT_ID_ENC4_HOLD: return "Enc4 hold";
        case INPUT_ID_ENC4_CW: return "Enc4 CW";
        case INPUT_ID_ENC4_CCW: return "Enc4 CCW";
        case INPUT_ID_ENC5: return "Enc5";
        case INPUT_ID_ENC5_PRESS: return "Enc5 press";
        case INPUT_ID_ENC5_HOLD: return "Enc5 hold";
        case INPUT_ID_ENC5_CW: return "Enc5 CW";
        case INPUT_ID_ENC5_CCW: return "Enc5 CCW";
        default: return "Unknown";
    }
}

const char *ui_app_input_state(uint8_t id, uint8_t pressed)
{
    switch (id) {
        case INPUT_ID_ENC_PRESS:
        case INPUT_ID_ENC2_PRESS:
        case INPUT_ID_ENC3_PRESS:
        case INPUT_ID_ENC4_PRESS:
        case INPUT_ID_ENC5_PRESS:
            return "press";
        case INPUT_ID_ENC_HOLD:
        case INPUT_ID_ENC2_HOLD:
        case INPUT_ID_ENC3_HOLD:
        case INPUT_ID_ENC4_HOLD:
        case INPUT_ID_ENC5_HOLD:
            return "hold";
        case INPUT_ID_ENC_CW:
        case INPUT_ID_ENC2_CW:
        case INPUT_ID_ENC3_CW:
        case INPUT_ID_ENC4_CW:
        case INPUT_ID_ENC5_CW:
            return "cw";
        case INPUT_ID_ENC_CCW:
        case INPUT_ID_ENC2_CCW:
        case INPUT_ID_ENC3_CCW:
        case INPUT_ID_ENC4_CCW:
        case INPUT_ID_ENC5_CCW:
            return "ccw";
        default:
            return pressed ? "down" : "up";
    }
}

int ui_app_is_back_button(uint8_t id)
{
    if (id == INPUT_ID_B || id == INPUT_ID_ENC_HOLD) {
        return 1;
    }
    if (id == INPUT_ID_ENC2_HOLD || id == INPUT_ID_ENC3_HOLD ||
        id == INPUT_ID_ENC4_HOLD || id == INPUT_ID_ENC5_HOLD) {
        return 1;
    }
    return 0;
}
