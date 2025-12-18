#pragma once

#include <stdint.h>

/* Optional local overrides (wiring, address, etc.). */
#include "user_config.h"

/* Configuration for the SER2.7I-256128 (SSD1363, 256x128, I2C).
 *
 * Fill these values with real GPIO numbers and address
 * once the display is wired to the ESP32-S3.
 */

/* Logical display resolution in pixels. */
#ifndef DISPLAY_WIDTH
#define DISPLAY_WIDTH   256
#endif
#ifndef DISPLAY_HEIGHT
#define DISPLAY_HEIGHT  128
#endif

/* I2C controller index (0 or 1 for ESP32-S3). */
#ifndef DISPLAY_I2C_PORT
#define DISPLAY_I2C_PORT         0  /* I2C_NUM_0 */
#endif

/* I2C SDA/SCL GPIOs. Use -1 as placeholder until wired. */
#ifndef DISPLAY_I2C_SDA_GPIO
#define DISPLAY_I2C_SDA_GPIO    (-1)
#endif
#ifndef DISPLAY_I2C_SCL_GPIO
#define DISPLAY_I2C_SCL_GPIO    (-1)
#endif

/* I2C bus frequency in Hz. */
#ifndef DISPLAY_I2C_FREQ_HZ
#define DISPLAY_I2C_FREQ_HZ      400000
#endif

/* 7-bit I2C address of the SSD1363 display. */
#ifndef DISPLAY_I2C_ADDR
#define DISPLAY_I2C_ADDR         0x3C
#endif

/* Optional reset GPIO for the panel. Set to -1 if not used
 * or if the display reset is tied to ESP reset. */
#ifndef DISPLAY_RST_GPIO
#define DISPLAY_RST_GPIO        (-1)
#endif

/* Pixel format for flush helpers (editor->firmware). Set to 1 for 1bpp or 4 for 4bpp grayscale. */
#ifndef DISPLAY_COLOR_BITS
#define DISPLAY_COLOR_BITS 4
#endif

/* Use a conservative built-in SSD1363 init sequence (set to 1 to enable).
 * Leave disabled until verified against your module's datasheet.
 */
#ifndef SSD1363_USE_DEFAULT_INIT
#define SSD1363_USE_DEFAULT_INIT 1
#endif

/* Optional bring-up diagnostics (off by default). */
#ifndef SSD1363_I2C_SCAN_ON_BOOT
#define SSD1363_I2C_SCAN_ON_BOOT 0
#endif
#ifndef SSD1363_BOOT_TEST_PATTERN
#define SSD1363_BOOT_TEST_PATTERN 0
#endif

/* SSD1363 addressing (4bpp):
 * - Column address units are groups of 4 pixels (2 bytes per row).
 * - Most 256x128 panels use a horizontal offset because SSD1363 has 320 segments:
 *   (320 - 256) / 2 = 32 px -> 32/4 = 8 column units.
 */
#ifndef SSD1363_COL_OFFSET
#define SSD1363_COL_OFFSET 8
#endif

/* Default init params (based on U8g2's SSD1363 256x128 sequence). */
#ifndef SSD1363_INIT_CLOCK
#define SSD1363_INIT_CLOCK 0x30
#endif
#ifndef SSD1363_INIT_DISPLAY_OFFSET
#define SSD1363_INIT_DISPLAY_OFFSET 0x20
#endif
#ifndef SSD1363_INIT_START_LINE
#define SSD1363_INIT_START_LINE 0x00
#endif
#ifndef SSD1363_INIT_REMAP_A
#define SSD1363_INIT_REMAP_A 0x32
#endif
#ifndef SSD1363_INIT_REMAP_B
#define SSD1363_INIT_REMAP_B 0x00
#endif
#ifndef SSD1363_INIT_ENH_A0
#define SSD1363_INIT_ENH_A0 0x32
#endif
#ifndef SSD1363_INIT_ENH_A1
#define SSD1363_INIT_ENH_A1 0x0C
#endif
#ifndef SSD1363_INIT_CONTRAST
#define SSD1363_INIT_CONTRAST 0xFF
#endif
#ifndef SSD1363_INIT_VOLTAGE_CONFIG
#define SSD1363_INIT_VOLTAGE_CONFIG 0x03
#endif
#ifndef SSD1363_INIT_IREF
#define SSD1363_INIT_IREF 0x90
#endif
#ifndef SSD1363_INIT_PHASE_LENGTH
#define SSD1363_INIT_PHASE_LENGTH 0x74
#endif
#ifndef SSD1363_INIT_PRECHARGE_VOLTAGE
#define SSD1363_INIT_PRECHARGE_VOLTAGE 0x0C
#endif
#ifndef SSD1363_INIT_SECOND_PRECHARGE
#define SSD1363_INIT_SECOND_PRECHARGE 0xC8
#endif
#ifndef SSD1363_INIT_VCOMH
#define SSD1363_INIT_VCOMH 0x04
#endif
