# Animation Timeline Editor Guide

Complete guide for creating and editing animations with keyframes using the Visual Timeline Editor.

## Overview

The Animation Timeline Editor provides a visual interface for creating complex animations with keyframe support. Access it by clicking the **✏ Edit** button in the UI Designer Preview window.

## Features

### Animation Management

- **➕ New** - Create new animation with custom name
- **🗑️ Delete** - Remove selected animation
- **Animation Selector** - Dropdown to choose active animation
- **▶️⏸⏹ Preview Controls** - Play, pause, and stop animation in main window

### Animation Properties

Configure global animation settings:

- **Type** - Animation effect (fade, slide, move, scale, pulse, bounce)
- **Duration** - Animation length in milliseconds (100-5000ms)
- **Easing** - Timing function for smooth motion
- **Loop** - Enable infinite repetition (iterations = -1)

### Easing Functions

Visual preview curve shows the timing function:

- `linear` - Constant speed
- `ease_in` - Slow start, fast end
- `ease_out` - Fast start, slow end
- `ease_in_out` - Slow start and end
- `ease_in_quad` - Quadratic acceleration
- `ease_out_quad` - Quadratic deceleration

### Timeline Canvas

Visual representation of animation timeline:

- **Timeline Bar** - Shows 0-100% progress
- **Keyframe Markers** - Orange circles on timeline
- **Selected Keyframe** - Green highlight
- **Time Labels** - 0%, 25%, 50%, 75%, 100%

### Keyframe Editor

Create precise animation keyframes:

- **➕ Add** - Create new keyframe at specified time
- **🗑️ Delete** - Remove selected keyframe
- **Time** - Position on timeline (0.0 - 1.0)
- **Property** - Animated attribute (opacity, x, y, width, height, scale, rotation)
- **Value** - Target value at this time
- **Update** - Apply changes to selected keyframe

## Workflow

### Creating an Animation

1. Click **➕ New** and enter animation name
2. Select animation **Type** (e.g., "fade")
3. Set **Duration** (e.g., 1000ms = 1 second)
4. Choose **Easing** function
5. Click **Apply Changes**

### Adding Keyframes

1. Select animation from dropdown
2. Set **Time** (0.0 = start, 1.0 = end)
3. Choose **Property** (e.g., "opacity")
4. Enter **Value** (e.g., 0.0 for transparent)
5. Click **➕ Add**

### Editing Keyframes

1. Click keyframe marker on timeline (turns green)
2. Modify **Time**, **Property**, or **Value**
3. Click **Update Keyframe**

Timeline automatically re-sorts keyframes by time.

### Deleting Keyframes

1. Click keyframe marker to select it
2. Click **🗑️ Delete**

### Preview Animation

1. Select widget in main preview window
2. Select animation from dropdown
3. Click **▶** in timeline editor
4. Use **⏹** to stop and reset

## Examples

### Fade In Animation

```python
Animation:
  name: "fade_in"
  type: fade
  duration: 500ms
  easing: ease_in_out

Keyframes:
  - time: 0.0, opacity: 0.0
  - time: 1.0, opacity: 1.0
```

### Slide and Fade

```python
Animation:
  name: "slide_fade"
  type: move
  duration: 800ms
  easing: ease_out

Keyframes:
  - time: 0.0, x: -100, opacity: 0.0
  - time: 0.3, x: 0, opacity: 0.5
  - time: 1.0, x: 0, opacity: 1.0
```

### Bounce Effect

```python
Animation:
  name: "bounce"
  type: bounce
  duration: 1200ms
  easing: ease_out_bounce
  loop: true

Keyframes:
  - time: 0.0, y: 0, scale: 1.0
  - time: 0.5, y: 50, scale: 0.8
  - time: 1.0, y: 0, scale: 1.0
```

## Keyframe Properties

Supported animated properties:

| Property | Description | Example Values |
|----------|-------------|----------------|
| `opacity` | Transparency | 0.0 (invisible) - 1.0 (opaque) |
| `x` | Horizontal position | 0, 100, 240 (pixels) |
| `y` | Vertical position | 0, 50, 320 (pixels) |
| `width` | Widget width | 50, 100, 200 (pixels) |
| `height` | Widget height | 20, 40, 100 (pixels) |
| `scale` | Size multiplier | 0.5 (half), 1.0 (normal), 2.0 (double) |
| `rotation` | Rotation angle | 0, 90, 180, 360 (degrees) |

## Tips and Tricks

### Smooth Animations

- Use `ease_in_out` for natural motion
- Add keyframes at 0%, 50%, and 100% for complex paths
- Keep duration between 300-800ms for UI responsiveness

### Performance

- Limit keyframes to 5-10 per animation
- Use `linear` easing for simple animations (less CPU)
- Avoid animating too many properties simultaneously

### Timing

- `time: 0.0` = animation start
- `time: 0.5` = halfway through
- `time: 1.0` = animation end
- Values outside 0.0-1.0 are clamped

### Common Patterns

**Fade In/Out:**

```text
0.0: opacity = 0.0
1.0: opacity = 1.0
```

**Slide from Left:**

```text
0.0: x = -100
1.0: x = 0
```

**Pulse Effect:**

```text
0.0: scale = 1.0
0.5: scale = 1.2
1.0: scale = 1.0
```

## Troubleshooting

### Keyframes Not Visible

- Ensure animation is selected from dropdown
- Check timeline canvas has loaded (resize window if needed)
- Click timeline area to refresh

### Animation Not Playing

- Select a widget in main preview window
- Ensure animation has duration > 0
- Check keyframes exist and are sorted

### Easing Curve Not Updating

- Reselect easing function from dropdown
- Window may need focus - click easing dropdown

### Keyframe Values Not Applying

- Click **Update Keyframe** after changes
- Ensure property name matches exactly
- Check value is numeric for numeric properties

## Keyboard Shortcuts

Currently, the timeline editor is mouse-driven. Future versions will add:

- `Ctrl+K` - Add keyframe
- `Delete` - Delete selected keyframe
- `Space` - Play/pause preview
- Arrow keys - Navigate keyframes

## Export

Animations can be exported to JSON format using the main UI Designer export function. C code export for ESP32 firmware is planned.

## See Also

- [UI Designer Pro README](UI_DESIGNER_PRO_README.md) - Main UI Designer features
- [UI Designer Guide](UI_DESIGNER_GUIDE.md) - Complete designer documentation
- [Shortcuts Reference](UI_DESIGNER_SHORTCUTS.md) - Keyboard shortcuts
