#pragma once

#include <stdint.h>

/* Configuration for the SER2.7I-256128 (SSD1363, 256x128, I2C).
 *
 * Fill these values with real GPIO numbers and address
 * once the display is wired to the ESP32-S3.
 */

/* Logical display resolution in pixels. */
#define DISPLAY_WIDTH   256
#define DISPLAY_HEIGHT  128

/* I2C controller index (0 or 1 for ESP32-S3). */
#define DISPLAY_I2C_PORT         0  /* I2C_NUM_0 */

/* I2C SDA/SCL GPIOs. Use -1 as placeholder until wired. */
#define DISPLAY_I2C_SDA_GPIO    (-1)
#define DISPLAY_I2C_SCL_GPIO    (-1)

/* I2C bus frequency in Hz. */
#define DISPLAY_I2C_FREQ_HZ      400000

/* 7-bit I2C address of the SSD1363 display. */
#define DISPLAY_I2C_ADDR         0x3C

/* Optional reset GPIO for the panel. Set to -1 if not used
 * or if the display reset is tied to ESP reset. */
#define DISPLAY_RST_GPIO        (-1)

