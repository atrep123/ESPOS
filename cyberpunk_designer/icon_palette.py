"""Icon Palette window — browse real Material icons and apply them.

This is a *functional* picker, not a decorative shell. It enumerates the
exact icon set the firmware ships (the ``*_24px.png`` assets that
``tools/gen_icons.py`` bakes into ``src/icons*.c`` and that the runtime
``icons_find()`` resolves by base name), lets the user search/navigate it,
and assigns the chosen icon's base name to a widget's ``icon_char``.

Why base name (e.g. ``arrow_back``) and not a glyph: the firmware does
``icons_find(w->icon_char, want)`` (``src/ui_render_widgets.c``) and the C
codegen / Python preview both treat ``icon_char`` as the icon key. So the
value written here survives JSON -> C codegen -> ESP32 render unchanged.

Rendering of each thumbnail uses the same alpha/edge -> 1bpp mask logic as
``tools/gen_icons.py`` so the designer preview matches the device.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

from .constants import GRID, PALETTE, safe_save_state, snap

# NOTE: `draw_text_clipped` is imported lazily inside `draw_icon_palette`.
# Importing `.drawing.text` at module load triggers `.drawing/__init__`,
# which imports `.drawing.frame`, which imports this module back -> a
# circular import. The lazy import (same pattern the handlers use for
# widget_factory) keeps the dependency one-directional at load time.

# Repo root = parent of the cyberpunk_designer package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_ASSET_DIR = _REPO_ROOT / "assets" / "icons" / "material" / "filled"
_REGISTRY_C = _REPO_ROOT / "src" / "icons_registry.c"

_ICON_W = 24  # thumbnail render size (px); matches the 24px asset / firmware


def _c_ident(s: str) -> str:
    """Mirror gen_icons._c_ident so palette names match firmware keys."""
    out = []
    for ch in s:
        out.append(ch if (ch.isalnum() or ch == "_") else "_")
    if out and out[0].isdigit():
        out.insert(0, "_")
    return "".join(out)


@lru_cache(maxsize=1)
def discover_icon_names() -> Tuple[str, ...]:
    """Return the sorted list of available icon base names.

    Primary source: the ``*_24px.png`` assets (authoritative — these are
    what gen_icons.py compiles into the firmware). Fallback: parse the
    generated ``src/icons_registry.c`` key table so the palette still works
    in a stripped checkout. Returns an empty tuple only if neither exists.
    """
    names: set[str] = set()

    if _ASSET_DIR.is_dir():
        for fp in sorted(_ASSET_DIR.glob("*_24px.png")):
            stem = fp.stem
            if not stem.endswith("_24px"):
                continue
            base = stem[: -len("_24px")].strip()
            if base:
                names.add(_c_ident(base))

    if not names and _REGISTRY_C.is_file():
        try:
            txt = _REGISTRY_C.read_text(encoding="utf-8", errors="replace")
        except OSError:
            txt = ""
        # Lines look like:  {"arrow_back", &mi_arrow_back_16px, &mi_arrow_back_24px},
        for m in re.finditer(r'\{\s*"([A-Za-z0-9_]+)"\s*,', txt):
            names.add(m.group(1))

    return tuple(sorted(names))


def _asset_path_for(name: str) -> Optional[Path]:
    if not _ASSET_DIR.is_dir():
        return None
    p = _ASSET_DIR / f"{name}_24px.png"
    return p if p.is_file() else None


def _surface_bg_rgba(img: pygame.Surface) -> Tuple[int, int, int, int]:
    """Best-effort background colour from edge pixels (mirrors gen_icons)."""
    w, h = img.get_size()
    samples = [
        img.get_at((0, 0)),
        img.get_at((w - 1, 0)),
        img.get_at((0, h - 1)),
        img.get_at((w - 1, h - 1)),
    ]
    counts: dict[Tuple[int, int, int, int], int] = {}
    for rgba in samples:
        key = (int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]))
        counts[key] = counts.get(key, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


@lru_cache(maxsize=256)
def _render_thumb(name: str, fg: Tuple[int, int, int]) -> Optional[pygame.Surface]:
    """Load + threshold an icon to a 24x24 1bpp-style surface.

    Mirrors gen_icons._surface_to_mask: prefer alpha, else "differs from
    background". Returns a per-pixel-alpha surface where set pixels are *fg*.
    Cached so scrolling is cheap. Returns None when the asset is unavailable.
    """
    fp = _asset_path_for(name)
    if fp is None:
        return None
    try:
        src = pygame.image.load(str(fp)).convert_alpha()
    except (pygame.error, OSError):
        return None
    if src.get_width() != _ICON_W or src.get_height() != _ICON_W:
        src = pygame.transform.smoothscale(src, (_ICON_W, _ICON_W))

    w, h = src.get_size()
    min_a, max_a = 255, 0
    for y in range(h):
        for x in range(w):
            a = int(src.get_at((x, y))[3])
            min_a = min(min_a, a)
            max_a = max(max_a, a)
    use_alpha = min_a < 255
    bg = None if use_alpha else _surface_bg_rgba(src)

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.fill((0, 0, 0, 0))
    col = (int(fg[0]), int(fg[1]), int(fg[2]), 255)
    for y in range(h):
        for x in range(w):
            px = src.get_at((x, y))
            if use_alpha:
                on = int(px[3]) >= 128
            else:
                assert bg is not None
                on = (
                    abs(int(px[0]) - bg[0])
                    + abs(int(px[1]) - bg[1])
                    + abs(int(px[2]) - bg[2])
                ) >= 30
            if on:
                out.set_at((x, y), col)
    return out


def _palette_state(app) -> dict:
    st = getattr(app, "_icon_palette", None)
    if not isinstance(st, dict):
        st = {
            "visible": False,
            "query": "",
            "cursor": 0,
            "scroll": 0,
            "hitboxes": [],
            "cols": 1,
            "rows": 1,
        }
        app._icon_palette = st
    return st


def _filtered_names(query: str) -> List[str]:
    names = discover_icon_names()
    q = query.strip().lower()
    if not q:
        return list(names)
    return [n for n in names if q in n]


# --------------------------------------------------------------------------- #
# Public API used by app / handlers
# --------------------------------------------------------------------------- #


def open_icon_palette(app) -> None:
    """Show the Icon Palette overlay."""
    st = _palette_state(app)
    if not discover_icon_names():
        app._set_status("No icons found (assets/icons/material/filled).", ttl_sec=3.0)
        return
    st["visible"] = True
    st["query"] = ""
    st["cursor"] = 0
    st["scroll"] = 0
    sel = bool(getattr(app.state, "selected", []))
    hint = "apply to selection" if sel else "drop new icon widget"
    app._set_status(
        f"Icon Palette: type to search, arrows move, Enter = {hint}, Esc = close",
        ttl_sec=4.0,
    )
    app._mark_dirty()


def close_icon_palette(app) -> None:
    st = _palette_state(app)
    if st.get("visible"):
        st["visible"] = False
        app._mark_dirty()


def is_open(app) -> bool:
    return bool(_palette_state(app).get("visible"))


def toggle_icon_palette(app) -> None:
    if is_open(app):
        close_icon_palette(app)
    else:
        open_icon_palette(app)


def _apply_icon(app, name: str) -> None:
    """Assign *name* to the selected icon widget, or drop a new one.

    Uses the same undo-safe path (``safe_save_state``) the inspector uses,
    so Ctrl+Z reverts it and the change persists through save/codegen.
    """
    name = str(name or "").strip()
    if not name:
        return
    try:
        sc = app.state.current_scene()
    except (AttributeError, TypeError):
        sc = None
    if sc is None:
        return

    selected = list(getattr(app.state, "selected", []) or [])
    icon_targets = [
        i
        for i in selected
        if 0 <= i < len(sc.widgets)
        and str(getattr(sc.widgets[i], "type", "")).lower() == "icon"
    ]

    if icon_targets:
        safe_save_state(app.designer)
        for i in icon_targets:
            w = sc.widgets[i]
            w.icon_char = name
            # Icon glyphs need >=16px box for icons_find() to bind on device.
            if int(getattr(w, "width", 0) or 0) < 16:
                w.width = 24
            if int(getattr(w, "height", 0) or 0) < 16:
                w.height = 24
        n = len(icon_targets)
        app._set_status(
            f"icon_char = '{name}' on {n} widget{'s' if n != 1 else ''}.",
            ttl_sec=2.5,
        )
        app._mark_dirty()
        return

    # Nothing suitable selected: create a fresh icon widget pre-set with it.
    from . import widget_factory

    safe_save_state(app.designer)
    widget_factory.add_widget(app, "icon")
    try:
        sc = app.state.current_scene()
        if sc.widgets:
            new_w = sc.widgets[-1]
            new_w.icon_char = name
            if int(getattr(new_w, "width", 0) or 0) < 16:
                new_w.width = 24
            if int(getattr(new_w, "height", 0) or 0) < 16:
                new_w.height = 24
    except (AttributeError, IndexError, TypeError):  # pragma: no cover
        pass
    app._set_status(f"Added icon widget '{name}'.", ttl_sec=2.5)
    app._mark_dirty()


def _move_cursor(app, delta: int) -> None:
    st = _palette_state(app)
    names = _filtered_names(st.get("query", ""))
    if not names:
        st["cursor"] = 0
        return
    cur = int(st.get("cursor", 0))
    st["cursor"] = max(0, min(len(names) - 1, cur + delta))
    app._mark_dirty()


def handle_key(app, event: pygame.event.Event) -> bool:
    """Consume a key event while the palette is open. Returns True if handled.

    Wired from key_handlers.on_key_down *before* the global dispatch so the
    palette behaves like a modal (matches help/shortcuts overlay style).
    """
    st = _palette_state(app)
    if not st.get("visible"):
        return False

    key = event.key
    if key == pygame.K_ESCAPE:
        close_icon_palette(app)
        return True

    names = _filtered_names(st.get("query", ""))
    cols = max(1, int(st.get("cols", 1)))

    if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if names:
            idx = max(0, min(len(names) - 1, int(st.get("cursor", 0))))
            _apply_icon(app, names[idx])
            close_icon_palette(app)
        return True
    if key == pygame.K_BACKSPACE:
        st["query"] = str(st.get("query", ""))[:-1]
        st["cursor"] = 0
        st["scroll"] = 0
        app._mark_dirty()
        return True
    if key == pygame.K_LEFT:
        _move_cursor(app, -1)
        return True
    if key == pygame.K_RIGHT:
        _move_cursor(app, 1)
        return True
    if key == pygame.K_UP:
        _move_cursor(app, -cols)
        return True
    if key == pygame.K_DOWN:
        _move_cursor(app, cols)
        return True
    if key == pygame.K_PAGEUP:
        _move_cursor(app, -cols * max(1, int(st.get("rows", 1))))
        return True
    if key == pygame.K_PAGEDOWN:
        _move_cursor(app, cols * max(1, int(st.get("rows", 1))))
        return True
    if key == pygame.K_HOME:
        st["cursor"] = 0
        app._mark_dirty()
        return True
    if key == pygame.K_END:
        st["cursor"] = max(0, len(names) - 1)
        app._mark_dirty()
        return True

    # Printable search input (letters, digits, underscore/space).
    ch = event.unicode
    if ch and (ch.isalnum() or ch in ("_", " ")):
        st["query"] = str(st.get("query", "")) + ch.lower()
        st["cursor"] = 0
        st["scroll"] = 0
        app._mark_dirty()
        return True

    # Swallow every other key so global shortcuts don't fire under the modal.
    return True


def handle_click(app, pos: Tuple[int, int]) -> bool:
    """Consume a mouse click while the palette is open. Returns True if handled."""
    st = _palette_state(app)
    if not st.get("visible"):
        return False
    for rect, idx in st.get("hitboxes", []):
        if rect.collidepoint(pos[0], pos[1]):
            names = _filtered_names(st.get("query", ""))
            if 0 <= idx < len(names):
                st["cursor"] = idx
                _apply_icon(app, names[idx])
                close_icon_palette(app)
            return True
    # Click anywhere else (including outside the panel) dismisses the modal.
    close_icon_palette(app)
    return True


def handle_wheel(app, dy: int) -> bool:
    """Consume a mouse-wheel event while the palette is open."""
    st = _palette_state(app)
    if not st.get("visible"):
        return False
    cols = max(1, int(st.get("cols", 1)))
    # Wheel scrolls a row at a time without moving the keyboard cursor.
    st["scroll"] = max(0, int(st.get("scroll", 0)) - dy * cols)
    app._mark_dirty()
    return True


# --------------------------------------------------------------------------- #
# Rendering — modeled on drawing/overlays.draw_help_overlay
# --------------------------------------------------------------------------- #


def draw_icon_palette(app) -> None:
    """Draw the Icon Palette modal overlay if open."""
    st = _palette_state(app)
    if not st.get("visible"):
        return
    # Lazy import breaks the icon_palette <-> drawing.frame import cycle.
    from .drawing.text import draw_text_clipped

    surface = getattr(app, "logical_surface", None)
    layout = getattr(app, "layout", None)
    if surface is None or layout is None:
        return
    w = int(getattr(layout, "width", 0) or 0)
    h = int(getattr(layout, "height", 0) or 0)
    if w <= 0 or h <= 0:
        return

    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 170))
    surface.blit(dim, (0, 0))

    pad = max(2, int(getattr(app, "pixel_padding", 0) or 0))
    row_h = max(1, int(getattr(app, "pixel_row_height", 0) or 0))

    margin = GRID * 2
    panel_w = max(GRID * 20, min(w - margin * 2, GRID * 60))
    panel_h = max(GRID * 16, min(h - margin * 2, GRID * 44))
    panel_w = max(GRID * 12, snap(panel_w))
    panel_h = max(GRID * 12, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)

    pygame.draw.rect(surface, PALETTE["panel"], panel_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], panel_rect, 1)

    names = _filtered_names(st.get("query", ""))
    total = len(discover_icon_names())

    # Title + search row.
    title_rect = pygame.Rect(x + pad, y + pad, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"Icon Palette  ({len(names)}/{total})",
        rect=title_rect,
        fg=PALETTE["accent_yellow"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )
    draw_text_clipped(
        app,
        surface=surface,
        text="Enter=apply  Esc=close",
        rect=title_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    query = str(st.get("query", ""))
    search_rect = pygame.Rect(x + pad, y + pad + row_h, panel_w - 2 * pad, row_h)
    pygame.draw.rect(surface, PALETTE["bg"], search_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], search_rect, 1)
    draw_text_clipped(
        app,
        surface=surface,
        text=("Search: " + query + "_") if query else "Search: (type to filter)",
        rect=pygame.Rect(
            search_rect.x + pad, search_rect.y, search_rect.width - 2 * pad, row_h
        ),
        fg=PALETTE["text"] if query else PALETTE["muted"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    # Grid area.
    grid_top = y + pad + row_h * 2 + pad
    grid_rect = pygame.Rect(
        x + pad,
        grid_top,
        panel_w - 2 * pad,
        (y + panel_h - pad) - grid_top,
    )
    if grid_rect.width <= 0 or grid_rect.height <= 0:
        st["hitboxes"] = []
        return

    cell = max(GRID * 4, _ICON_W + pad * 2)
    label_h = row_h
    cell_h = cell + label_h
    cols = max(1, grid_rect.width // cell)
    rows = max(1, grid_rect.height // cell_h)
    st["cols"] = cols
    st["rows"] = rows

    if not names:
        draw_text_clipped(
            app,
            surface=surface,
            text="No icons match this search.",
            rect=grid_rect,
            fg=PALETTE["muted"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        st["hitboxes"] = []
        return

    cursor = max(0, min(len(names) - 1, int(st.get("cursor", 0))))

    # Keep the keyboard cursor visible: clamp scroll so cursor's row is shown.
    cur_row = cursor // cols
    scroll = int(st.get("scroll", 0)) // cols
    if cur_row < scroll:
        scroll = cur_row
    elif cur_row >= scroll + rows:
        scroll = cur_row - rows + 1
    max_scroll = max(0, ((len(names) + cols - 1) // cols) - rows)
    scroll = max(0, min(scroll, max_scroll))
    st["scroll"] = scroll * cols

    hitboxes: List[Tuple[pygame.Rect, int]] = []
    first = scroll * cols
    last = min(len(names), first + rows * cols)
    for n_i in range(first, last):
        rel = n_i - first
        cx = grid_rect.x + (rel % cols) * cell
        cy = grid_rect.y + (rel // cols) * cell_h
        cell_rect = pygame.Rect(cx, cy, cell, cell_h)
        is_cur = n_i == cursor
        is_hover = cell_rect.collidepoint(*getattr(app, "pointer_pos", (0, 0)))
        if is_cur:
            pygame.draw.rect(surface, PALETTE["selection"], cell_rect, 1)
        if is_hover and not is_cur:
            pygame.draw.rect(surface, PALETTE["panel_border"], cell_rect, 1)

        name = names[n_i]
        fg = PALETTE["text"]
        thumb = _render_thumb(name, fg)
        if thumb is not None:
            tw, th = thumb.get_size()
            surface.blit(
                thumb,
                (cx + (cell - tw) // 2, cy + (cell - th) // 2),
            )
        else:
            # Asset unavailable (registry-only fallback): show a glyph box.
            draw_text_clipped(
                app,
                surface=surface,
                text="[?]",
                rect=pygame.Rect(cx, cy, cell, cell),
                fg=PALETTE["muted"],
                padding=0,
                align="center",
                valign="middle",
                max_lines=1,
                use_device_font=False,
            )
        draw_text_clipped(
            app,
            surface=surface,
            text=name,
            rect=pygame.Rect(cx, cy + cell, cell, label_h),
            fg=PALETTE["accent_cyan"] if is_cur else PALETTE["muted"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        hitboxes.append((cell_rect, n_i))

    st["hitboxes"] = hitboxes

    # Footer: name of the focused icon + scroll position.
    foot_rect = pygame.Rect(
        x + pad, y + panel_h - row_h, panel_w - 2 * pad, row_h
    )
    page = scroll // max(1, rows) + 1
    pages = max(1, ((len(names) + cols - 1) // cols + rows - 1) // rows)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"> {names[cursor]}",
        rect=foot_rect,
        fg=PALETTE["accent_yellow"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )
    draw_text_clipped(
        app,
        surface=surface,
        text=f"page {page}/{pages}",
        rect=foot_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )


# Keep an explicit env hint so headless smoke tests don't need a display.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
