#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Auto-generated, do not edit

typedef struct { const char* name; const uint8_t* data; unsigned int size; } asset_entry_t;

extern const asset_entry_t g_assets[];
extern const unsigned int g_assets_count;

#ifdef __cplusplus
}
#endif
