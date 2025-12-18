#pragma once

#include <stdint.h>

/* Minimal fixed-width 6x8 font for embedded UI.
 *
 * Glyph format: 8 rows, each row is a 6-bit mask stored in bits [5..0]
 * (bit 5 = leftmost pixel, bit 0 = rightmost pixel).
 */

const uint8_t *ui_font6x8_glyph(char c);

