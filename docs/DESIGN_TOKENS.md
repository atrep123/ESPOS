# Design Tokens System

Centralized design tokens registry for ESP32OS UI components.

## Overview

The `design_tokens.py` module provides a single source of truth for:

- **Colors** – Semantic color roles (primary, surface, status colors)
- **Spacing** – Consistent 4px-based scale
- **Typography** – Font sizes, weights, families, line heights
- **Elevation** – Shadow depths and ASCII shading characters
- **Animation** – Durations and easing curves
- **Responsive** – Breakpoints + evaluator for width-based tiers

## Usage

```python
from design_tokens import tokens, responsive_evaluator, responsive_scalars

# Colors
bg_color = tokens.colors.surface  # (30, 30, 30)
hex_color = tokens.colors.to_hex(tokens.colors.primary)  # "#007acc"

# Spacing
padding = tokens.spacing.md  # 16px
button_padding_x = tokens.spacing.button_padding_x  # 16px

# Typography
font_size = tokens.typography.size_base  # 14px
font_family = tokens.typography.family_monospace  # "Courier New, monospace"

# Elevation
shadow_blur = tokens.elevation.shadow_blur[2]  # 4px
ascii_char = tokens.elevation.ascii_shading[3]  # '▓'

# Animation
transition_time = tokens.animation.base  # 160ms
easing = tokens.animation.ease_out  # "cubic-bezier(0.0, 0.0, 0.2, 1.0)"

# Responsive
tier = responsive_evaluator.classify(width=100).name  # "medium"
scales = responsive_scalars(100)  # {"tier": "medium", "spacing_scale": 1.0, "font_scale": 1.0}
```

## Token Categories

### Colors (ColorTokens)

Semantic color roles using RGB tuples:

- **Primary**: `primary`, `primary_dark`, `primary_light`
- **Surface**: `surface`, `surface_raised`, `surface_overlay`
- **Text**: `text_primary`, `text_secondary`, `text_disabled`
- **Status**: `success`, `warning`, `error`, `info`
- **Components**: `border`, `border_focus`, `shadow`

### Spacing (SpacingTokens)

4px-based scale:

- `xs`: 4px
- `sm`: 8px
- `md`: 16px (base)
- `lg`: 24px
- `xl`: 32px
- `xxl`: 48px

Component-specific: `button_padding_x`, `button_padding_y`, `dialog_padding`, `list_item_padding`

### Typography (TypographyTokens)

- **Families**: `family_monospace`, `family_sans`
- **Sizes**: `size_xs` (10px) to `size_xxl` (24px)
- **Weights**: `weight_normal` (400), `weight_medium` (500), `weight_bold` (700)
- **Line heights**: `line_height_tight` (1.2), `line_height_base` (1.5), `line_height_relaxed` (1.8)

### Elevation (ElevationTokens)

Depth levels (0-4) with shadow blur and ASCII shading:

- `level_0`: Flat (no shadow, `''`)
- `level_1`: Raised (2px blur, `'░'`)
- `level_2`: Card (4px blur, `'▒'`)
- `level_3`: Dialog (8px blur, `'▓'`)
- `level_4`: Overlay (12px blur, `'█'`)

### Animation (AnimationTokens)

- **Durations**: `fast` (80ms), `base` (160ms), `slow` (240ms)
- **Easing**: `ease_in`, `ease_out`, `ease_in_out` (cubic-bezier values)
- **Frame budgets**: `frame_budget_60fps` (16.67ms), `frame_budget_30fps` (33.33ms)

### Responsive (ResponsiveBreakpoints / ResponsiveEvaluator)

- Breakpoints: `tiny` (<40), `small` (<80), `medium` (<120), `wide` (>=120) — configurable
- `responsive_evaluator.classify(width)` → tier with flags (`is_tiny`, `is_small`, `is_medium`, `is_wide`)
- `responsive_scalars(width)` → lightweight `spacing_scale` / `font_scale` for adjusting layout without touching scene data

## Immutability

All tokens are **frozen dataclasses** – they cannot be modified after initialization:

```python
# This will raise an error:
tokens.colors.primary = (255, 0, 0)
```

## Testing

Run tests with:

```bash
pytest test_design_tokens.py -v
```

## Migration Plan

See `DESIGN_ENHANCEMENT_PLAN.md` for gradual migration strategy:

1. Token registry (✅ complete)
2. Migrate 2-3 components to use tokens
3. Add responsive evaluator
4. Integrate animation tokens
5. Build export parity tests

## Related Files

- `design_tokens.py` – Token definitions
- `test_design_tokens.py` – Unit tests
- `DESIGN_ENHANCEMENT_PLAN.md` – Overall UX roadmap
- `ui_themes.py` – Theme system (to be refactored to use tokens)
