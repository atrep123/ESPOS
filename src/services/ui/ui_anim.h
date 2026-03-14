#ifndef UI_ANIM_H
#define UI_ANIM_H

#include <stdint.h>
#include "ui_scene.h"
#include "ui_dirty.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Animation runtime: parse animations_csv, tick & apply each frame.
 *
 * Format of animations_csv (semicolon-separated entries):
 *   "blink:500"          – toggle visible every 500 ms
 *   "fade:1000:in"       – fade fg from 0 to original over 1000 ms
 *   "fade:1000:out"      – fade fg to 0 over 1000 ms
 *   "slide:500:left"     – slide in from left over 500 ms
 *   "slide:500:right"    – slide in from right over 500 ms
 *   "slide:500:up"       – slide in from top over 500 ms
 *   "slide:500:down"     – slide in from bottom over 500 ms
 *   "pulse:1000"         – oscillate fg brightness over period (cyclic)
 *   "bounce:500"         – bounce widget vertically over period (cyclic)
 */

typedef enum {
    UI_ANIM_NONE = 0,
    UI_ANIM_BLINK,
    UI_ANIM_FADE_IN,
    UI_ANIM_FADE_OUT,
    UI_ANIM_SLIDE,
    UI_ANIM_PULSE,
    UI_ANIM_BOUNCE,
} UiAnimKind;

typedef enum {
    UI_ANIM_DIR_LEFT = 0,
    UI_ANIM_DIR_RIGHT,
    UI_ANIM_DIR_UP,
    UI_ANIM_DIR_DOWN,
} UiAnimDir;

typedef struct {
    UiAnimKind kind;
    uint16_t   duration_ms;   /* period (blink) or duration (fade/slide) */
    UiAnimDir  dir;           /* direction for slide */
    int16_t    orig_x;        /* saved original x */
    int16_t    orig_y;        /* saved original y */
    uint8_t    orig_fg;       /* saved original fg */
    uint8_t    orig_visible;  /* saved original visible */
    int64_t    start_us;      /* animation start timestamp */
    uint8_t    done;          /* 1 if one-shot animation finished */
} UiAnimSlot;

#define UI_ANIM_MAX_PER_WIDGET 2
#define UI_ANIM_MAX_WIDGETS    128

typedef struct {
    UiAnimSlot slots[UI_ANIM_MAX_WIDGETS][UI_ANIM_MAX_PER_WIDGET];
    int        count;  /* number of widgets with at least one active anim */
    int        active; /* non-zero if any animation is running */
} UiAnimState;

/** Initialize animation state (zeroes everything). */
void ui_anim_init(UiAnimState *st);

/** Parse animations_csv for all widgets in scene, start timestamps. */
void ui_anim_start(UiAnimState *st, const UiScene *scene, int64_t now_us);

/** Tick all running animations, modify widget properties, mark dirty. */
void ui_anim_tick(UiAnimState *st, UiScene *scene, int64_t now_us, UiDirty *dirty);

/** Check if any animation is still running (for timeout scheduling). */
int ui_anim_is_active(const UiAnimState *st);

#ifdef __cplusplus
}
#endif

#endif /* UI_ANIM_H */
