#pragma once

#include <stdint.h>

typedef enum {
    INPUT_ID_A = 0,
    INPUT_ID_B = 1,
    INPUT_ID_C = 2, /* reserved */
    INPUT_ID_UP = 3,
    INPUT_ID_DOWN = 4,
    INPUT_ID_LEFT = 5,
    INPUT_ID_RIGHT = 6,
    INPUT_ID_ENC = 7,       /* encoder push button (raw state) */
    INPUT_ID_ENC_PRESS = 8, /* short press action (event) */
    INPUT_ID_ENC_HOLD = 9,  /* hold action (event) */
    INPUT_ID_ENC_CW = 10,   /* encoder clockwise (event) */
    INPUT_ID_ENC_CCW = 11,  /* encoder counter-clockwise (event) */

    /* Extra buttons (e.g. Mini I2C Gamepad QT). */
    INPUT_ID_X = 12,
    INPUT_ID_Y = 13,
    INPUT_ID_SELECT = 14,
    INPUT_ID_START = 15,

    /* Additional encoder groups (e.g. Quad Rotary Encoder QT).
     * Note: INPUT_ID_ENC* refers to the primary encoder group.
     */
    INPUT_ID_ENC2 = 16,
    INPUT_ID_ENC2_PRESS = 17,
    INPUT_ID_ENC2_HOLD = 18,
    INPUT_ID_ENC2_CW = 19,
    INPUT_ID_ENC2_CCW = 20,

    INPUT_ID_ENC3 = 21,
    INPUT_ID_ENC3_PRESS = 22,
    INPUT_ID_ENC3_HOLD = 23,
    INPUT_ID_ENC3_CW = 24,
    INPUT_ID_ENC3_CCW = 25,

    INPUT_ID_ENC4 = 26,
    INPUT_ID_ENC4_PRESS = 27,
    INPUT_ID_ENC4_HOLD = 28,
    INPUT_ID_ENC4_CW = 29,
    INPUT_ID_ENC4_CCW = 30,

    INPUT_ID_ENC5 = 31,
    INPUT_ID_ENC5_PRESS = 32,
    INPUT_ID_ENC5_HOLD = 33,
    INPUT_ID_ENC5_CW = 34,
    INPUT_ID_ENC5_CCW = 35,
} input_id_t;

void input_start(void);
