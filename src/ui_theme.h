#pragma once

/*
 * Default theme color palette for 4-bit grayscale and 1-bit displays.
 * These constants are used by widget renderers to resolve colors
 * when no per-widget overrides are set.
 */

#include "display_config.h"

#if DISPLAY_COLOR_BITS == 4
enum {
    UI_COL_BG       = 0,
    UI_COL_PANEL_BG = 2,
    UI_COL_BORDER   = 12,
    UI_COL_TEXT     = 15,
    UI_COL_MUTED    = 8,
    UI_COL_FILL     = 10,
};
#else
enum {
    UI_COL_BG       = 0,
    UI_COL_PANEL_BG = 0,
    UI_COL_BORDER   = 1,
    UI_COL_TEXT     = 1,
    UI_COL_MUTED    = 1,
    UI_COL_FILL     = 1,
};
#endif
