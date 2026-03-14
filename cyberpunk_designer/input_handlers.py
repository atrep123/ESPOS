"""Mouse and keyboard event processing handlers.

This module re-exports from key_handlers and mouse_handlers for
backward-compatible imports.
"""

from __future__ import annotations

from .key_handlers import _cycle_widget_selection, on_key_down  # noqa: F401
from .mouse_handlers import (  # noqa: F401
    _finish_box_select,
    on_mouse_down,
    on_mouse_move,
    on_mouse_up,
    on_mouse_wheel,
)
