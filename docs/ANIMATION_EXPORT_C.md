# Animation Export to C Code

## Overview

Export animations designed in the UI Designer to C code for ESP32 firmware. This enables seamless integration of visually designed animations into embedded applications.

## Features

- **Complete C structures** - Header (.h) and implementation (.c) files
- **Animation player API** - Ready-to-use playback system
- **Easing functions** - All 6 easing curves implemented
- **Keyframe support** - Export complete animation timelines
- **Type-safe enums** - Animation types and easing functions
- **Zero dependencies** - Only requires stdint.h and stdbool.h

## Quick Start

### Export from UI Designer

1. Open Animation Timeline Editor (✏ button)
2. Select animation to export
3. Click **📤 Export to C** button
4. Choose output directory
5. Generated files: `ui_animations.h` and `ui_animations.c`

### Export from Command Line

```powershell
python animation_export_c.py animations.json -o firmware/components/ui
```

Options:

- `-o, --output DIR` - Output directory (default: exported_animations)
- `-n, --name BASE` - Base filename (default: ui_animations)

## Generated Files

### Header File (ui_animations.h)

Contains:

- Animation type enum
- Easing function enum
- Keyframe structure
- Animation structure
- Animation player structure
- API function declarations

### Implementation File (ui_animations.c)

Contains:

- Keyframe arrays
- Animation data structures
- Easing function implementations
- Animation player implementation

## C Structures Reference

### Animation Types

```c
typedef enum {
    UI_ANIM_FADE,
    UI_ANIM_SLIDE_LEFT,
    UI_ANIM_SLIDE_RIGHT,
    UI_ANIM_MOVE,
    UI_ANIM_SCALE,
    UI_ANIM_PULSE,
    UI_ANIM_BOUNCE,
    // ... more types
} ui_animation_type_t;
```

### Easing Functions

```c
typedef enum {
    UI_EASING_LINEAR,
    UI_EASING_EASE_IN,
    UI_EASING_EASE_OUT,
    UI_EASING_EASE_IN_OUT,
    UI_EASING_EASE_IN_QUAD,
    UI_EASING_EASE_OUT_QUAD
} ui_easing_t;
```

### Keyframe Structure

```c
typedef struct {
    float time;           /* 0.0 to 1.0 */
    int16_t x;            /* Position X (or -1 if unused) */
    int16_t y;            /* Position Y (or -1 if unused) */
    uint16_t width;       /* Width (or 0 if unused) */
    uint16_t height;      /* Height (or 0 if unused) */
    uint8_t opacity;      /* 0-255 (or 255 if unused) */
    uint16_t color;       /* RGB565 (or 0 if unused) */
    ui_easing_t easing;   /* Easing to next keyframe */
} ui_keyframe_t;
```

### Animation Structure

```c
typedef struct {
    const char *name;
    ui_animation_type_t type;
    uint16_t duration_ms;
    uint16_t delay_ms;
    int16_t iterations;        /* -1 for infinite */
    ui_easing_t easing;
    const ui_keyframe_t *keyframes;
    uint8_t keyframe_count;
} ui_animation_t;
```

### Animation Player

```c
typedef struct {
    const ui_animation_t *animation;
    uint32_t start_time_ms;
    int16_t current_iteration;
    bool is_playing;
} ui_animation_player_t;
```

## API Functions

### Player Lifecycle

#### ui_animation_player_init

```c
void ui_animation_player_init(ui_animation_player_t *player);
```

Initialize animation player. Call before first use.

#### ui_animation_player_start

```c
void ui_animation_player_start(
    ui_animation_player_t *player,
    const ui_animation_t *anim,
    uint32_t current_time_ms
);
```

Start playing animation. `current_time_ms` is system time in milliseconds.

#### ui_animation_player_stop

```c
void ui_animation_player_stop(ui_animation_player_t *player);
```

Stop animation playback.

### Player Update

#### ui_animation_player_update

```c
bool ui_animation_player_update(
    ui_animation_player_t *player,
    uint32_t current_time_ms
);
```

Update animation state. Call every frame.

Returns:

- `true` - Animation still playing
- `false` - Animation finished

#### ui_animation_player_get_progress

```c
float ui_animation_player_get_progress(
    ui_animation_player_t *player,
    uint32_t current_time_ms
);
```

Get current animation progress (0.0 to 1.0) with easing applied.

### Easing Evaluation

#### ui_easing_evaluate

```c
float ui_easing_evaluate(ui_easing_t easing, float t);
```

Evaluate easing function at time `t` (0.0 to 1.0).

## Usage Examples

### Example 1: Simple Fade Animation

```c
#include "ui_animations.h"

// Animation player instance
static ui_animation_player_t player;

void setup() {
    // Initialize player
    ui_animation_player_init(&player);
    
    // Start fade animation
    ui_animation_player_start(&player, &anim_fade_in, millis());
}

void loop() {
    uint32_t now = millis();
    
    // Update animation
    if (ui_animation_player_update(&player, now)) {
        // Get progress
        float progress = ui_animation_player_get_progress(&player, now);
        
        // Apply to widget
        uint8_t opacity = (uint8_t)(255 * progress);
        widget_set_opacity(my_widget, opacity);
    }
}
```

### Example 2: Looping Pulse

```c
// Exported animation with iterations=-1 (infinite)
extern const ui_animation_t anim_pulse;

void start_pulse() {
    ui_animation_player_start(&player, &anim_pulse, millis());
}

void update_pulse() {
    if (ui_animation_player_update(&player, millis())) {
        float progress = ui_animation_player_get_progress(&player, millis());
        
        // Pulse scale effect
        float scale = 1.0f + (progress * 0.2f); // 1.0 to 1.2
        widget_set_scale(my_widget, scale);
    }
}
```

### Example 3: Keyframe Animation

```c
// Animation with multiple keyframes
extern const ui_animation_t anim_complex_path;

void animate_path() {
    ui_animation_player_start(&player, &anim_complex_path, millis());
}

void update_path() {
    uint32_t now = millis();
    
    if (ui_animation_player_update(&player, now)) {
        float t = ui_animation_player_get_progress(&player, now);
        
        // Interpolate between keyframes
        int16_t x = interpolate_keyframes(&anim_complex_path, t, "x");
        int16_t y = interpolate_keyframes(&anim_complex_path, t, "y");
        
        widget_set_position(my_widget, x, y);
    }
}

// Helper: Linear interpolation between keyframes
int16_t interpolate_keyframes(
    const ui_animation_t *anim,
    float t,
    const char *property
) {
    for (uint8_t i = 0; i < anim->keyframe_count - 1; i++) {
        const ui_keyframe_t *kf1 = &anim->keyframes[i];
        const ui_keyframe_t *kf2 = &anim->keyframes[i + 1];
        
        if (t >= kf1->time && t <= kf2->time) {
            float local_t = (t - kf1->time) / (kf2->time - kf1->time);
            local_t = ui_easing_evaluate(kf1->easing, local_t);
            
            // Get values based on property
            int16_t v1 = (strcmp(property, "x") == 0) ? kf1->x : kf1->y;
            int16_t v2 = (strcmp(property, "x") == 0) ? kf2->x : kf2->y;
            
            return v1 + (int16_t)((v2 - v1) * local_t);
        }
    }
    
    return 0;
}
```

### Example 4: Multiple Animations

```c
#define MAX_ANIMATIONS 4

static ui_animation_player_t players[MAX_ANIMATIONS];

void setup_animations() {
    // Initialize all players
    for (int i = 0; i < MAX_ANIMATIONS; i++) {
        ui_animation_player_init(&players[i]);
    }
    
    // Start different animations
    ui_animation_player_start(&players[0], &anim_fade_in, millis());
    ui_animation_player_start(&players[1], &anim_slide_left, millis() + 100);
    ui_animation_player_start(&players[2], &anim_pulse, millis() + 200);
}

void update_animations() {
    uint32_t now = millis();
    
    for (int i = 0; i < MAX_ANIMATIONS; i++) {
        if (players[i].is_playing) {
            ui_animation_player_update(&players[i], now);
        }
    }
}
```

## Integration Guide

### Step 1: Copy Files to Project

```text
firmware/
├── components/
│   └── ui/
│       ├── ui_animations.h      ← Generated header
│       └── ui_animations.c      ← Generated implementation
└── main/
    └── main.c
```

### Step 2: Include in CMakeLists.txt

```cmake
idf_component_register(
    SRCS 
        "ui_animations.c"
        "main.c"
    INCLUDE_DIRS 
        "."
)
```

### Step 3: Include Header in Code

```c
#include "ui_animations.h"
```

### Step 4: Use Animations

See usage examples above.

## Performance Considerations

### Memory Usage

- **Header overhead**: ~200 bytes (enums, typedefs)
- **Per animation**: ~40 bytes (structure)
- **Per keyframe**: ~16 bytes (keyframe data)
- **Player state**: 16 bytes

Example:

- 10 animations with 3 keyframes each = ~880 bytes total

### CPU Usage

- **Update call**: 50-200 cycles (~1-4 µs @ 80MHz)
- **Easing evaluation**: 10-100 cycles (~0.2-2 µs)
- **Keyframe interpolation**: 100-500 cycles (~2-10 µs)

### Recommendations

- **Max 3-5 simultaneous animations** on ESP32
- **Use simple easing** (linear, ease_in/out) for best performance
- **Limit keyframes** to 2-4 per animation
- **Update at 30-60 FPS** (16-33 ms intervals)

## Easing Functions Reference

### Linear

Constant speed.

```c
UI_EASING_LINEAR
```

Formula: `t`

### Ease In

Slow start, fast end.

```c
UI_EASING_EASE_IN
UI_EASING_EASE_IN_QUAD
```

Formula: `t * t`

### Ease Out

Fast start, slow end.

```c
UI_EASING_EASE_OUT
UI_EASING_EASE_OUT_QUAD
```

Formula: `t * (2 - t)`

### Ease In Out

Slow start and end.

```c
UI_EASING_EASE_IN_OUT
```

Formula: `t * t * (3 - 2 * t)`

## Troubleshooting

### Animation not playing

**Check:**

- Player initialized with `ui_animation_player_init()`
- Animation started with `ui_animation_player_start()`
- Update called every frame
- `current_time_ms` is valid system time

### Jerky animation

**Solutions:**

- Call `ui_animation_player_update()` more frequently
- Use smoother easing function
- Reduce keyframe count

### High memory usage

**Solutions:**

- Reduce number of keyframes
- Share keyframe arrays between similar animations
- Use simple animation types without keyframes

## Advanced Topics

### Custom Easing Functions

Add to `ui_easing_evaluate()`:

```c
case UI_EASING_CUSTOM:
    return custom_easing_function(t);
```

### Animation Chaining

```c
if (!ui_animation_player_update(&player1, now)) {
    // First animation done, start second
    ui_animation_player_start(&player2, &next_anim, now);
}
```

### Reverse Playback

```c
float progress = ui_animation_player_get_progress(&player, now);
float reversed = 1.0f - progress;
```

## See Also

- [Animation Timeline Guide](ANIMATION_TIMELINE_GUIDE.md)
- [UI Designer Guide](UI_DESIGNER_GUIDE.md)
- [ESP32 UI Examples](../SIMULATOR_EXAMPLES.md)
