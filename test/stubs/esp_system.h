#pragma once

/* Minimal esp_system.h stub for native/host builds. */

#include <stdint.h>
#include <inttypes.h>

uint32_t esp_get_free_heap_size(void);
uint32_t esp_get_minimum_free_heap_size(void);
