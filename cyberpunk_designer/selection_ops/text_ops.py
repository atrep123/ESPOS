"""Widget text, naming, and ID operations."""

from __future__ import annotations

import re
from collections import Counter

from ..constants import GRID, snap
from .core import save_undo


def auto_rename(app) -> None:
    """Auto-rename selected widgets as type_1, type_2, etc."""
    if not app.state.selected:
        app._set_status("Auto-rename: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    save_undo(app)
    counter: Counter[str] = Counter()
    renamed = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ty = str(getattr(w, "type", "widget") or "widget").lower()
        counter[ty] += 1
        w.id = f"{ty}_{counter[ty]}"
        renamed += 1
    app._set_status(f"Renamed {renamed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def auto_name_scene(app) -> None:
    """Auto-name ALL widgets in the current scene as type_N."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("Scene empty.", ttl_sec=2.0)
        return
    save_undo(app)
    counter: Counter[str] = Counter()
    for w in sc.widgets:
        ty = str(getattr(w, "type", "widget") or "widget").lower()
        counter[ty] += 1
        w.id = f"{ty}_{counter[ty]}"
    app._set_status(f"Named {len(sc.widgets)} widgets in scene.", ttl_sec=2.0)
    app._mark_dirty()


def auto_label_widgets(app) -> None:
    """Auto-set text of selected widgets to Type #N based on their order."""
    if not app.state.selected:
        app._set_status("Auto-label: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for i, idx in enumerate(sorted(app.state.selected)):
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            wtype = str(getattr(w, "type", "widget") or "widget").capitalize()
            w.text = f"{wtype} {i + 1}"
            count += 1
    app._set_status(f"Auto-labeled {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def increment_text(app) -> None:
    """Append sequential numbers to selected widget texts (1, 2, 3...)."""
    if not app.state.selected:
        app._set_status("Inc text: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    save_undo(app)
    for seq, i in enumerate(valid, 1):
        w = sc.widgets[i]
        base = str(getattr(w, "text", "") or "")
        # Strip existing trailing number
        base = re.sub(r"\s*\d+$", "", base)
        w.text = f"{base} {seq}" if base else str(seq)
    app._set_status(f"Numbered {len(valid)} widget text(s).", ttl_sec=2.0)
    app._mark_dirty()


def replace_text_in_scene(app) -> None:
    """Find and replace text across all widgets in the current scene.

    Uses the inspector input buffer mechanism: first call prompts for
    'find|replace' pattern, then applies it.
    """
    sc = app.state.current_scene()
    # Use a simple prompt via status bar
    buf = getattr(app, "_replace_buf", None)
    if buf is None:
        # First call: set a flag so user types find|replace
        app._replace_buf = ""
        app._set_status("Replace: type find|replace then press Ctrl+F5 again", ttl_sec=5.0)
        return
    # Parse the buffer
    parts = buf.split("|", 1)
    app._replace_buf = None  # reset
    if len(parts) != 2 or not parts[0]:
        app._set_status("Replace cancelled (use find|replace format).", ttl_sec=2.0)
        return
    find_str, repl_str = parts
    save_undo(app)
    changed = 0
    for w in sc.widgets:
        txt = str(getattr(w, "text", "") or "")
        if find_str in txt:
            w.text = txt.replace(find_str, repl_str)
            changed += 1
    app._set_status(f"Replaced '{find_str}'→'{repl_str}' in {changed} widget(s).", ttl_sec=3.0)
    app._mark_dirty()


def clear_all_text(app) -> None:
    """Set text to empty string on all selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        if str(getattr(w, "text", "") or ""):
            w.text = ""
            count += 1
    app._set_status(f"Cleared text on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def number_text(app) -> None:
    """Set text to '1', '2', '3'… on selected widgets by position order."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    indices = sorted(
        app.state.selected,
        key=lambda i: (sc.widgets[i].y, sc.widgets[i].x) if 0 <= i < len(sc.widgets) else (0, 0),
    )
    for n, idx in enumerate(indices, 1):
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].text = str(n)
    app._set_status(f"Numbered {len(indices)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def number_widget_ids(app) -> None:
    """Auto-assign _widget_id as 'type_N' for all widgets in the scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    app._save_undo_state()
    counters: dict[str, int] = {}
    for w in sc.widgets:
        wtype = str(getattr(w, "type", "widget") or "widget").lower()
        n = counters.get(wtype, 0)
        counters[wtype] = n + 1
        w._widget_id = f"{wtype}_{n}"
    app._set_status(f"Numbered {len(sc.widgets)} widget ID(s).", ttl_sec=2.0)
    app._mark_dirty()


def size_to_text(app) -> None:
    """Auto-size selected widgets' width to fit their text (6px per char + padding)."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    char_w = 6
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        text = str(getattr(w, "text", "") or "")
        if not text:
            continue
        pad_x = int(getattr(w, "padding_x", 1) or 1)
        new_w = max(GRID, snap(len(text) * char_w + pad_x * 2))
        w.width = new_w
        count += 1
    if count:
        app._set_status(f"Sized {count} widget(s) to text.", ttl_sec=2.0)
    else:
        app._set_status("No widgets with text.", ttl_sec=2.0)
    app._mark_dirty()
