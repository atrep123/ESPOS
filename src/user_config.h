#pragma once

/*
 * Local overrides for wiring / module addresses.
 *
 * This file is included automatically by `display_config.h` and `input_config.h`.
 * Edit the macros below (or override via PlatformIO `build_flags`).
 *
 * Note: every define is guarded with `#ifndef` so `-D...` build flags can still win.
 */

/* ----------------------------- Display (SSD1363) -------------------------- */

/* Example (Arduino Nano ESP32 default I2C pins):
 *   SDA = GPIO11, SCL = GPIO12
 */
#ifndef DISPLAY_I2C_SDA_GPIO
/* #define DISPLAY_I2C_SDA_GPIO 11 */
#endif

#ifndef DISPLAY_I2C_SCL_GPIO
/* #define DISPLAY_I2C_SCL_GPIO 12 */
#endif

/* Common I2C addresses are 0x3C / 0x3D. */
#ifndef DISPLAY_I2C_ADDR
/* #define DISPLAY_I2C_ADDR 0x3C */
#endif

/* Optional reset pin (-1 = not used). */
#ifndef DISPLAY_RST_GPIO
/* #define DISPLAY_RST_GPIO (-1) */
#endif

/* 1 = 1bpp mono, 4 = 4bpp gray. */
#ifndef DISPLAY_COLOR_BITS
/* #define DISPLAY_COLOR_BITS 4 */
#endif

/* Set to 1 to use the conservative built-in init sequence (see `ssd1363.c`). */
#ifndef SSD1363_USE_DEFAULT_INIT
/* #define SSD1363_USE_DEFAULT_INIT 1 */
#endif

/* Bring-up diagnostics (off by default). */
#ifndef SSD1363_I2C_SCAN_ON_BOOT
/* #define SSD1363_I2C_SCAN_ON_BOOT 1 */
#endif

#ifndef SSD1363_BOOT_TEST_PATTERN
/* #define SSD1363_BOOT_TEST_PATTERN 1 */
#endif

/* SSD1363 addressing: column offset (units of 4 pixels). */
#ifndef SSD1363_COL_OFFSET
/* #define SSD1363_COL_OFFSET 8 */
#endif

/* SSD1363 default init knobs (advanced; tweak only if needed). */
#ifndef SSD1363_INIT_CLOCK
/* #define SSD1363_INIT_CLOCK 0x30 */
#endif
#ifndef SSD1363_INIT_DISPLAY_OFFSET
/* #define SSD1363_INIT_DISPLAY_OFFSET 0x20 */
#endif
#ifndef SSD1363_INIT_START_LINE
/* #define SSD1363_INIT_START_LINE 0x00 */
#endif
#ifndef SSD1363_INIT_REMAP_A
/* #define SSD1363_INIT_REMAP_A 0x32 */
#endif
#ifndef SSD1363_INIT_REMAP_B
/* #define SSD1363_INIT_REMAP_B 0x00 */
#endif
#ifndef SSD1363_INIT_ENH_A0
/* #define SSD1363_INIT_ENH_A0 0x32 */
#endif
#ifndef SSD1363_INIT_ENH_A1
/* #define SSD1363_INIT_ENH_A1 0x0C */
#endif
#ifndef SSD1363_INIT_CONTRAST
/* #define SSD1363_INIT_CONTRAST 0xFF */
#endif
#ifndef SSD1363_INIT_VOLTAGE_CONFIG
/* #define SSD1363_INIT_VOLTAGE_CONFIG 0x03 */
#endif
#ifndef SSD1363_INIT_IREF
/* #define SSD1363_INIT_IREF 0x90 */
#endif
#ifndef SSD1363_INIT_PHASE_LENGTH
/* #define SSD1363_INIT_PHASE_LENGTH 0x74 */
#endif
#ifndef SSD1363_INIT_PRECHARGE_VOLTAGE
/* #define SSD1363_INIT_PRECHARGE_VOLTAGE 0x0C */
#endif
#ifndef SSD1363_INIT_SECOND_PRECHARGE
/* #define SSD1363_INIT_SECOND_PRECHARGE 0xC8 */
#endif
#ifndef SSD1363_INIT_VCOMH
/* #define SSD1363_INIT_VCOMH 0x04 */
#endif

/* ------------------------------ Inputs (GPIO) ----------------------------- */

/* GPIO mapping (-1 = not used).
 *
 * Example:
 *   #define INPUT_PIN_A 0
 *   #define INPUT_PIN_B 1
 *   #define INPUT_PIN_UP 2
 *   ...
 */

/* --------------------------- Inputs (I2C seesaw) -------------------------- */

/* Enable polling of Adafruit seesaw-based I2C controllers (gamepad/encoders). */
#ifndef INPUT_SEESAW_ENABLE
/* #define INPUT_SEESAW_ENABLE 1 */
#endif

/* Addresses (adjust if you changed address jumpers). */
#ifndef INPUT_SEESAW_GAMEPAD_BASE_ADDR
/* #define INPUT_SEESAW_GAMEPAD_BASE_ADDR 0x50 */
#endif

#ifndef INPUT_SEESAW_ROTARY_ADDR
/* #define INPUT_SEESAW_ROTARY_ADDR 0x36 */
#endif

#ifndef INPUT_SEESAW_QUAD_ADDR
/* #define INPUT_SEESAW_QUAD_ADDR 0x49 */
#endif
