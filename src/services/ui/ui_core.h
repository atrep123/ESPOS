#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Shared UI core state and logic used by both
 * the ESP32 UI task and the desktop simulator.
 *
 * Scenes are intentionally simple for now:
 *  - HOME
 *  - SETTINGS
 *  - METRICS
 */

typedef enum {
    UI_SCENE_HOME = 0,
    UI_SCENE_SETTINGS = 1,
    UI_SCENE_METRICS = 2,
} ui_scene_t;

typedef struct {
    uint16_t bg;      /* background color in RGB565 */
    int32_t t;        /* logical tick counter       */
    uint8_t btnA;     /* button A state             */
    uint8_t btnB;     /* button B state             */
    uint8_t btnC;     /* button C state             */
    ui_scene_t scene; /* current scene              */
} ui_state_t;

/* Initialise UI state with defaults (dark background,
 * HOME scene, all buttons released). */
void ui_core_init(ui_state_t *st);

/* Called on each rendered tick (e.g. every 30–60 FPS). */
void ui_core_on_tick(ui_state_t *st);

/* Handle logical button state change (id = 0,1,2...). */
void ui_core_on_button(ui_state_t *st, uint8_t id, bool pressed);

/* Handle RPC that sets background color from 0xRRGGBB. */
void ui_core_on_rpc_bg(ui_state_t *st, uint32_t rgb);

