#!/usr/bin/env python3
"""Public entrypoint for the pygame-based UI designer.

The implementation lives in `cyberpunk_designer.app`, while this module stays as a stable
import target for tests and scripts:

`from cyberpunk_editor import GRID, PALETTE, CyberpunkEditorApp`
"""

from __future__ import annotations

from cyberpunk_designer.app import CyberpunkEditorApp, main
from cyberpunk_designer.constants import GRID, PALETTE

__all__ = ["GRID", "PALETTE", "CyberpunkEditorApp", "main"]

if __name__ == "__main__":
    main()
