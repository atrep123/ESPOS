"""Inspector field validation and parsing utilities."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from .constants import safe_save_state

# Choice-constrained fields: field → (allowed_values, widget_attr)
_CHOICE_FIELDS: Dict[str, Tuple[Tuple[str, ...], str]] = {
    "align": (("left", "center", "right"), "align"),
    "valign": (("top", "middle", "bottom"), "valign"),
    "border_style": (("none", "single", "double", "rounded", "bold", "dashed"), "border_style"),
    "text_overflow": (("ellipsis", "wrap", "clip", "auto"), "text_overflow"),
}


def _commit_choice(app, f: str, buf: str, targets: List) -> Optional[bool]:
    """Validate and set a choice field. Returns None if not a choice field."""
    spec = _CHOICE_FIELDS.get(f)
    if spec is None:
        return None
    allowed, attr = spec
    val = buf.lower()
    if val not in allowed:
        app._set_status(f"{f} must be: {'|'.join(allowed)}", ttl_sec=4.0)
        return False
    safe_save_state(app.designer)
    for w in targets:
        setattr(w, attr, val)
    return True


def _commit_str_attr(app, f: str, raw: str, targets: List) -> Optional[bool]:
    """Set text/runtime fields directly. Returns None if not applicable."""
    if f not in {"text", "runtime"}:
        return None
    safe_save_state(app.designer)
    for w in targets:
        setattr(w, f, raw)
    return True


def _commit_color(app, f: str, buf: str, targets: List) -> Optional[bool]:
    """Validate and set color fields. Returns None if not applicable."""
    if f not in {"color_fg", "color_bg"}:
        return None
    if not app._is_valid_color_str(buf):
        app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
        return False
    safe_save_state(app.designer)
    for w in targets:
        setattr(w, f, buf)
    return True


def _parse_pair(buf: str, separators: str = ", ") -> Optional[Tuple[int, int]]:
    """Parse 'A,B' or 'A B' into (int, int). Returns None on failure."""
    for sep in separators:
        if sep in buf:
            parts = buf.split(sep, 1)
            break
    else:
        return None
    if len(parts) != 2:  # pragma: no cover
        return None
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except (ValueError, TypeError):
        return None


def _commit_epilogue(app, message: str) -> bool:
    """Common cleanup after a successful inspector commit."""
    app.state.inspector_selected_field = None
    app.state.inspector_input_buffer = ""
    try:
        pygame.key.stop_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status(str(message or "Updated."), ttl_sec=2.0)
    app._mark_dirty()
    return True


def _sorted_role_indices(role_idx: Dict[str, int], prefix: str) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    p = str(prefix or "")
    if not p:
        return out
    for role, idx in (role_idx or {}).items():
        r = str(role or "")
        if not r.startswith(p):
            continue
        suffix = r[len(p) :]
        if suffix.isdigit():
            out.append((int(suffix), int(idx)))
    out.sort(key=lambda t: t[0])
    return out


def _parse_active_count(text: str) -> Optional[Tuple[int, int]]:
    """Parse 'active/count' as (active_0_based, count)."""
    s = str(text or "").strip()
    if not s or "/" not in s:
        return None
    left, right = s.split("/", 1)
    try:
        a = int(left.strip())
        b = int(right.strip())
    except (ValueError, TypeError):
        return None
    if b <= 0:
        return 0, 0
    a = max(1, min(a, b))
    return a - 1, b
