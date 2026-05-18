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
 *
 * !!! UNVERIFIED-ON-HARDWARE !!! The sequence in ssd1363.c is a per-command
 * transcription of U8g2's u8x8_d_ssd1363.c (the de-facto reference for this
 * controller); it has NOT been confirmed against a real panel here. No
 * Solomon Systech SSD1363 datasheet PDF was publicly retrievable to verify
 * bitfields. Every SSD1363_INIT_* value below is a tuning candidate.
 */
#ifndef SSD1363_USE_DEFAULT_INIT
#define SSD1363_USE_DEFAULT_INIT 1
#endif

/* Refuse to report init success if the panel does not ACK its I2C address
 * (root-cause fix for "blank screen + init returns OK"). Set to 0 only for
 * bring-up behind a bus expander that does not ACK cleanly. */
#ifndef SSD1363_REQUIRE_PROBE
#define SSD1363_REQUIRE_PROBE 1
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
 * - SSD1363 GDDRAM is 320 x 160 (per U8g2 csrc/u8x8_d_ssd1363.c header);
 *   a 256-wide panel is centred: (320 - 256) / 2 = 32 px -> 32/4 = 8
 *   column units. Matches U8g2 default_x_offset = 8. Cross-checked OK.
 */
#ifndef SSD1363_COL_OFFSET
#define SSD1363_COL_OFFSET 8
#endif

/* Multiplex ratio byte for command 0xCA. U8g2 programs the literal
 * active-COM count (127), NOT the SSD13xx "ratio = N-1" convention.
 * UNVERIFIED-ON-HARDWARE. */
#ifndef SSD1363_INIT_MUX_RATIO
#define SSD1363_INIT_MUX_RATIO 127
#endif

/* Default init params. Source of record: olikraus/u8g2 (BSD-2-Clause)
 * csrc/u8x8_d_ssd1363.c -> u8x8_d_ssd1363_256x128_init_seq[], master.
 * Values cross-checked byte-for-byte. UNVERIFIED-ON-HARDWARE: no Solomon
 * Systech SSD1363 datasheet PDF was publicly retrievable to confirm
 * bitfield meanings; treat each as a tuning candidate. */
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
