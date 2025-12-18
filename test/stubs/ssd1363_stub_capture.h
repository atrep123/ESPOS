#pragma once

#include <stddef.h>
#include <stdint.h>

/* Helpers for native/unit tests to observe what the SSD1363 stub receives. */

void ssd1363_stub_reset(void);

uint16_t ssd1363_stub_last_x0(void);
uint16_t ssd1363_stub_last_y0(void);
uint16_t ssd1363_stub_last_x1(void);
uint16_t ssd1363_stub_last_y1(void);

size_t ssd1363_stub_write_calls(void);
size_t ssd1363_stub_first_write_len(void);
size_t ssd1363_stub_copy_first_write(uint8_t *out, size_t max_out);

