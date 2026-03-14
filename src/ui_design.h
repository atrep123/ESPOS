/* Auto-generated: UI design for ESP32OS (multi-scene) */
/* Source: main_scene.json */
#ifndef UI_DESIGN_H
#define UI_DESIGN_H

#include <stdint.h>
#include "ui_scene.h"

#define UI_ENABLE_CONSTRAINTS 1
#define UI_ENABLE_ANIMATIONS  1

#ifdef __cplusplus
extern "C" {
#endif

#define UI_SCENE_COUNT 3

/* Scene index macros */
#define UI_SCENE_IDX_MAIN 0
#define UI_SCENE_IDX_SETTINGS 1
#define UI_SCENE_IDX_METRICS 2

/* Scene array */
extern const UiScene ui_scenes[];

/* Backward-compatible alias (first scene) */
#define UI_SCENE_DEMO ui_scenes[0]

#ifdef __cplusplus
}
#endif

#endif /* UI_DESIGN_H */
