#pragma once

/* Optional local overrides (pins, I2C addresses, etc.). */
#include "user_config.h"

/*
 * Input configuration (GPIO mappings).
 *
 * Defaults are conservative and keep the devkit "BOOT" button usable as A.
 * Override these macros in your build (e.g. via `build_flags`) once wired.
 */

/* Active-low buttons with internal pull-ups are assumed by default. */
#ifndef INPUT_ACTIVE_LOW
#define INPUT_ACTIVE_LOW 1
#endif

/* GPIO mapping (-1 = not used). */
#ifndef INPUT_PIN_A
#define INPUT_PIN_A 0
#endif
#ifndef INPUT_PIN_B
#define INPUT_PIN_B (-1)
#endif

#ifndef INPUT_PIN_UP
#define INPUT_PIN_UP (-1)
#endif
#ifndef INPUT_PIN_DOWN
#define INPUT_PIN_DOWN (-1)
#endif
#ifndef INPUT_PIN_LEFT
#define INPUT_PIN_LEFT (-1)
#endif
#ifndef INPUT_PIN_RIGHT
#define INPUT_PIN_RIGHT (-1)
#endif

/* Rotary encoder (optional). */
#ifndef INPUT_PIN_ENC_A
#define INPUT_PIN_ENC_A (-1)
#endif
#ifndef INPUT_PIN_ENC_B
#define INPUT_PIN_ENC_B (-1)
#endif
#ifndef INPUT_PIN_ENC_BTN
#define INPUT_PIN_ENC_BTN (-1)
#endif

/* Debounce/poll tuning. */
#ifndef INPUT_POLL_MS
#define INPUT_POLL_MS 5
#endif
#ifndef INPUT_DEBOUNCE_SAMPLES
#define INPUT_DEBOUNCE_SAMPLES 2
#endif

/* Encoder hold threshold. */
#ifndef INPUT_ENC_HOLD_MS
#define INPUT_ENC_HOLD_MS 650
#endif

/* -------------------------------------------------------------------------- */
/* Optional I2C input modules (Adafruit seesaw / STEMMA QT / Qwiic)            */
/* -------------------------------------------------------------------------- */

/* Enable polling of Adafruit seesaw-based I2C controllers (gamepad/encoders). */
#ifndef INPUT_SEESAW_ENABLE
#define INPUT_SEESAW_ENABLE 1
#endif

/* I2C poll cadence (in addition to GPIO poll). */
#ifndef INPUT_SEESAW_POLL_MS
#define INPUT_SEESAW_POLL_MS 10
#endif

/* I2C transaction timeout. */
#ifndef INPUT_SEESAW_I2C_TIMEOUT_MS
#define INPUT_SEESAW_I2C_TIMEOUT_MS 30
#endif

/* Delay between the register write and subsequent read (seesaw needs a short gap). */
#ifndef INPUT_SEESAW_READ_DELAY_US
#define INPUT_SEESAW_READ_DELAY_US 250
#endif

/* Mini I2C Gamepad (Adafruit 5743) default address base; board supports 4 addresses. */
#ifndef INPUT_SEESAW_GAMEPAD_BASE_ADDR
#define INPUT_SEESAW_GAMEPAD_BASE_ADDR 0x50
#endif
#ifndef INPUT_SEESAW_GAMEPAD_ADDR_COUNT
#define INPUT_SEESAW_GAMEPAD_ADDR_COUNT 4
#endif

/* Rotary Encoder (Adafruit 5880 / 4991 firmware) default address. */
#ifndef INPUT_SEESAW_ROTARY_ADDR
#define INPUT_SEESAW_ROTARY_ADDR 0x36
#endif

/* Quad Rotary Encoder (Adafruit 5752) default address. */
#ifndef INPUT_SEESAW_QUAD_ADDR
#define INPUT_SEESAW_QUAD_ADDR 0x49
#endif

/* Joystick mapping (gamepad). */
#ifndef INPUT_GAMEPAD_JOY_X_PIN
#define INPUT_GAMEPAD_JOY_X_PIN 14
#endif
#ifndef INPUT_GAMEPAD_JOY_Y_PIN
#define INPUT_GAMEPAD_JOY_Y_PIN 15
#endif
#ifndef INPUT_GAMEPAD_JOY_MAX
#define INPUT_GAMEPAD_JOY_MAX 1023
#endif
#ifndef INPUT_GAMEPAD_JOY_CENTER
#define INPUT_GAMEPAD_JOY_CENTER 512
#endif
/* Deadzone around center (bigger = less jitter, smaller = more sensitive). */
#ifndef INPUT_GAMEPAD_JOY_DEADZONE
#define INPUT_GAMEPAD_JOY_DEADZONE 180
#endif
/* Hysteresis for releasing direction (prevents chatter around threshold). */
#ifndef INPUT_GAMEPAD_JOY_HYST
#define INPUT_GAMEPAD_JOY_HYST 40
#endif
/* Match Adafruit example orientation (invert axes). */
#ifndef INPUT_GAMEPAD_JOY_INVERT_X
#define INPUT_GAMEPAD_JOY_INVERT_X 1
#endif
#ifndef INPUT_GAMEPAD_JOY_INVERT_Y
#define INPUT_GAMEPAD_JOY_INVERT_Y 1
#endif

/* Encoder direction inversion (to match physical clockwise expectations). */
#ifndef INPUT_SEESAW_ROTARY_INVERT_DIR
#define INPUT_SEESAW_ROTARY_INVERT_DIR 1
#endif
#ifndef INPUT_SEESAW_QUAD_INVERT_DIR
#define INPUT_SEESAW_QUAD_INVERT_DIR 0
#endif
