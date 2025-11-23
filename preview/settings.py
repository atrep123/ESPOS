"""Preview window settings and configuration."""

from dataclasses import dataclass
from typing import Tuple

from design_tokens import color_hex


@dataclass
class PreviewSettings:
    """Preview window settings"""

    zoom: float = 4.0  # 4x zoom by default
    grid_enabled: bool = True
    grid_size: int = 8
    snap_enabled: bool = True
    snap_size: int = 4
    show_bounds: bool = True
    show_handles: bool = True
    background_color: str = color_hex("shadow")
    pixel_perfect: bool = True
    nudge_distance: int = 1  # Normal arrow nudge distance (px)
    nudge_shift_distance: int = 8  # Shift+arrow nudge distance (px)
    # Alignment guides
    snap_to_widgets: bool = True  # Snap to other widget edges
    snap_distance: int = 4  # Snap tolerance in pixels
    show_alignment_guides: bool = True  # Show alignment guide lines
    # Debug overlay
    show_debug_overlay: bool = False
    # Accessibility
    high_contrast_overlays: bool = False
    # Auto JSON hot-reload of last loaded design file
    auto_reload_json: bool = False
    # Performance budgeting
    performance_budget_enabled: bool = True
    performance_budget_ms: float = 16.7  # Target frame time (~60 FPS)
    performance_warn_ms: float = 25.0  # Soft warning threshold
    # Grid aesthetics
    grid_padding_pct: float = 0.10  # Percent of step used as edge padding
    grid_padding_min_px: int = 2  # Minimum pixel padding regardless of step
    grid_color_dark: Tuple[int, int, int] = (36, 36, 36)  # Slightly softer
    grid_color_light: Tuple[int, int, int] = (50, 50, 50)  # High contrast
