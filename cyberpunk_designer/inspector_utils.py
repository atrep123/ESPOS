from __future__ import annotations

import re
from typing import List, Optional


def format_int_list(values: object, *, max_items: int = 32) -> str:
    """Format a list of ints as a compact comma-separated string for inspector display."""
    try:
        items = [int(v) for v in (values or [])]
    except Exception:
        return ""
    if not items:
        return ""
    max_items = max(1, int(max_items))
    shown = items[:max_items]
    out = ",".join(str(i) for i in shown)
    if len(items) > max_items:
        out += ",..."
    return out


def parse_int_list(
    text: str,
    *,
    max_items: int = 256,
    min_value: int = -1_000_000,
    max_value: int = 1_000_000,
) -> Optional[List[int]]:
    """Parse comma/space-separated ints. Returns None on invalid input.

    Accepts decimal or 0x-prefixed values.
    Empty string returns an empty list.
    """
    s = str(text or "").strip()
    if not s:
        return []
    tokens = [t for t in re.split(r"[,\s;]+", s) if t]
    out: List[int] = []
    max_items = max(1, int(max_items))
    for tok in tokens:
        try:
            v = int(tok, 0)
        except Exception:
            return None
        v = max(int(min_value), min(int(max_value), int(v)))
        out.append(int(v))
        if len(out) > max_items:
            return None
    return out
