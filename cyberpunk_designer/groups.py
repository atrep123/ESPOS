"""Group and component logic — extracted from app.py."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .app import CyberpunkEditorApp


def groups_for_index(app: CyberpunkEditorApp, idx: int) -> List[str]:
    """Return sorted list of group names that include *idx*."""
    groups: List[str] = []
    try:
        gdict = getattr(app.designer, "groups", {}) or {}
    except (TypeError, AttributeError):
        gdict = {}
    for gname, members in gdict.items():
        try:
            if idx in members:
                groups.append(str(gname))
        except TypeError:
            continue
    groups.sort()
    return groups


def primary_group_for_index(app: CyberpunkEditorApp, idx: int) -> Optional[str]:
    grps = groups_for_index(app, idx)
    return grps[0] if grps else None


def group_members(app: CyberpunkEditorApp, name: str) -> List[int]:
    """Return validated, sorted member indices for a named group."""
    try:
        members = list((getattr(app.designer, "groups", {}) or {}).get(name, []))
    except (TypeError, AttributeError):
        members = []
    sc = app.state.current_scene()
    valid: List[int] = []
    for m in members:
        try:
            i = int(m)
        except (ValueError, TypeError):
            continue
        if 0 <= i < len(sc.widgets):
            valid.append(i)
    return sorted(set(valid))


def selected_group_exact(app: CyberpunkEditorApp) -> Optional[str]:
    """Return group name when current selection matches it exactly."""
    if not app.state.selected or app.state.selected_idx is None:
        return None
    gname = primary_group_for_index(app, int(app.state.selected_idx))
    if not gname:
        return None
    members = group_members(app, gname)
    return gname if set(members) == set(app.state.selected) else None


def selected_component_group(
    app: CyberpunkEditorApp,
) -> Optional[Tuple[str, str, str, List[int]]]:
    """Return (group_name, component_type, root_prefix, members) when
    selection is inside a component group."""
    if not app.state.selected or app.state.selected_idx is None:
        return None
    try:
        idx = int(app.state.selected_idx)
    except (ValueError, TypeError):
        return None
    selection = [int(i) for i in (app.state.selected or [])]
    for gname in groups_for_index(app, idx):
        info = component_info_from_group(gname)
        if not info:
            continue
        comp_type, root = info
        members = group_members(app, gname)
        if all(i in members for i in selection):
            return str(gname), str(comp_type), str(root), members
    return None


def component_info_from_group(group_name: str) -> Optional[Tuple[str, str]]:
    """Parse ``comp:{type}:{root}:{n}`` or ``comp:{type}:{n}``."""
    g = str(group_name or "")
    if not g.startswith("comp:"):
        return None
    parts = g.split(":")
    # New scheme: comp:{type}:{root}:{n}
    if len(parts) >= 4 and parts[1] and parts[2]:
        return str(parts[1]), str(parts[2])
    # Legacy: comp:{type}:{n} (root == type)
    if len(parts) >= 3 and parts[1]:
        return str(parts[1]), str(parts[1])
    return None


def component_role_index(
    app: CyberpunkEditorApp, indices: List[int], root_prefix: str
) -> Dict[str, int]:
    """Map component role -> widget index within selection."""
    sc = app.state.current_scene()
    roles: Dict[str, int] = {}
    prefix = f"{root_prefix or ''!s}."
    if prefix == ".":
        return roles
    for idx in indices:
        if not (0 <= idx < len(sc.widgets)):
            continue
        wid = str(getattr(sc.widgets[idx], "_widget_id", "") or "")
        if not wid.startswith(prefix):
            continue
        role = wid[len(prefix) :].strip()
        if role and role not in roles:
            roles[role] = idx
    return roles


def format_group_label(group_name: str, members: List[int]) -> str:
    info = component_info_from_group(group_name)
    if info:
        comp_type, root = info
        if root and root != comp_type:
            return f"component: {comp_type} ({root}) ({len(members)})"
        return f"component: {comp_type} ({len(members)})"
    return f"group: {group_name} ({len(members)})"


def tri_state(values: List[bool]) -> str:
    if not values:
        return "off"
    if all(values):
        return "on"
    if not any(values):
        return "off"
    return "mixed"


def next_group_name(app: CyberpunkEditorApp, prefix: str) -> str:
    try:
        existing = set((getattr(app.designer, "groups", {}) or {}).keys())
    except (AttributeError, TypeError):
        existing = set()
    n = 1
    while f"{prefix}{n}" in existing:
        n += 1
    return f"{prefix}{n}"


def group_selection(app: CyberpunkEditorApp) -> None:
    if len(app.state.selected) < 2:
        app._set_status("Group: select 2+ widgets (Ctrl+Click).", ttl_sec=3.0)
        return
    name = next_group_name(app, "group")
    try:
        ok = bool(app.designer.create_group(name, list(app.state.selected)))
    except (TypeError, ValueError, KeyError):
        ok = False
    if ok:
        app._set_status(f"Grouped as {name}.", ttl_sec=3.0)
    else:
        app._set_status("Group failed.", ttl_sec=3.0)


def ungroup_selection(app: CyberpunkEditorApp) -> None:
    if not app.state.selected:
        return
    target: List[str] = []
    if app.state.selected_idx is not None:
        gname = primary_group_for_index(app, int(app.state.selected_idx))
        if gname:
            target = [gname]
    if not target:
        sel = set(app.state.selected)
        try:
            gdict = getattr(app.designer, "groups", {}) or {}
        except (TypeError, AttributeError):
            gdict = {}
        for gname, members in gdict.items():
            try:
                if sel.intersection(set(members)):
                    target.append(str(gname))
            except TypeError:
                continue
    if not target:
        app._set_status("Ungroup: no group.", ttl_sec=2.0)
        return
    removed = 0
    for gname in sorted(set(target)):
        try:
            if app.designer.delete_group(gname):
                removed += 1
        except (TypeError, ValueError, KeyError):
            continue
    app._set_status(f"Ungrouped {removed} group(s).", ttl_sec=3.0)
