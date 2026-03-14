/* Minimal esp_system stub for native/host builds. */

#include "esp_system.h"

static uint32_t s_free_heap = 128000;
static uint32_t s_min_free_heap = 64000;

uint32_t esp_get_free_heap_size(void) { return s_free_heap; }
uint32_t esp_get_minimum_free_heap_size(void) { return s_min_free_heap; }
