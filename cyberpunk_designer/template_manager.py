"""Template Manager window — browse, preview, and manage real templates.

This is a *functional* management window, not a decorative shell. It is
backed end-to-end by the real :class:`ui_template_manager.TemplateLibrary`
that ``app.template_library`` already owns:

* the list is ``app.template_library.templates`` (the same JSON-persisted
  registry the context-menu picker and ``Ctrl+Shift+T`` read);
* the preview renders each template's *actual* widgets by materializing the
  stored ``scene._raw_data`` into real :class:`WidgetConfig` objects and
  drawing them with the same ``draw_widget_preview`` the canvas uses, so
  what you see is what the scene becomes;
* every mutation goes through the library's real API
  (``add_template`` / ``remove_template`` / ``rename_template`` /
  ``save_scene_as_template``) which persists to ``templates.json``, and
  scene changes go through the designer's undo-safe ``safe_save_state``
  path (so ``Ctrl+Z`` reverts an apply/insert and it survives save/codegen).

Interaction model mirrors :mod:`cyberpunk_designer.icon_palette` (a true
modal: it consumes keys/clicks while open) for consistency with the
just-added Icon Palette window.
"""

from __future__ import annotations

import os
from typing import List, Tuple

import pygame

from ui_designer import WidgetConfig

from .constants import GRID, PALETTE, safe_save_state, snap

# NOTE: drawing helpers are imported lazily inside the draw function for the
# same reason icon_palette does it: importing `.drawing.*` at module load
# pulls in `.drawing.frame`, which imports this module back -> a circular
# import. Lazy import keeps the load-time dependency one-directional.


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #


def _state(app) -> dict:
    st = getattr(app, "_template_manager", None)
    if not isinstance(st, dict):
        st = {
            "visible": False,
            "cursor": 0,
            "scroll": 0,
            "query": "",
            "rows": 1,
            "list_hitboxes": [],
            "button_hitboxes": [],
        }
        app._template_manager = st
    return st


def _all_templates(app) -> list:
    lib = getattr(app, "template_library", None)
    if lib is None:
        return []
    return list(getattr(lib, "templates", []) or [])


def _filtered(app) -> list:
    """Templates matching the live search box (name/category/tags/desc)."""
    st = _state(app)
    templates = _all_templates(app)
    q = str(st.get("query", "")).strip().lower()
    if not q:
        return templates
    out = []
    for t in templates:
        meta = t.metadata
        hay = " ".join(
            [
                str(getattr(meta, "name", "")),
                str(getattr(meta, "category", "")),
                str(getattr(meta, "description", "")),
                " ".join(str(x) for x in getattr(meta, "tags", []) or []),
            ]
        ).lower()
        if q in hay:
            out.append(t)
    return out


def _template_widgets(template) -> List[WidgetConfig]:
    """Materialize a template's stored scene into real WidgetConfig objects.

    Uses the exact same construction (``WidgetConfig(**wdict)``) that
    ``scene_ops.apply_template`` uses, so the preview is faithful to what
    applying actually produces (malformed entries skipped, never crash).
    """
    raw = getattr(getattr(template, "scene", None), "_raw_data", {}) or {}
    widgets: List[WidgetConfig] = []
    for wdict in raw.get("widgets", []) or []:
        if not isinstance(wdict, dict):
            continue
        try:
            widgets.append(WidgetConfig(**wdict))
        except (TypeError, ValueError, KeyError):
            continue
    return widgets


# --------------------------------------------------------------------------- #
# Public API used by app / handlers
# --------------------------------------------------------------------------- #


def open_template_manager(app) -> None:
    """Show the Template Manager modal."""
    st = _state(app)
    st["visible"] = True
    st["query"] = ""
    st["scroll"] = 0
    st["cursor"] = max(0, min(int(st.get("cursor", 0)), max(0, len(_all_templates(app)) - 1)))
    n = len(_all_templates(app))
    app._set_status(
        f"Template Manager: {n} template(s). "
        "Enter=apply  Ins=insert  R=rename  Del=delete  S=save scene  Esc=close",
        ttl_sec=4.0,
    )
    app._mark_dirty()


def close_template_manager(app) -> None:
    st = _state(app)
    if st.get("visible"):
        st["visible"] = False
        app._mark_dirty()


def is_open(app) -> bool:
    return bool(_state(app).get("visible"))


def toggle_template_manager(app) -> None:
    if is_open(app):
        close_template_manager(app)
    else:
        open_template_manager(app)


def _current_template(app):
    st = _state(app)
    items = _filtered(app)
    if not items:
        return None
    idx = max(0, min(len(items) - 1, int(st.get("cursor", 0))))
    return items[idx]


def _apply_selected(app, *, insert: bool) -> None:
    """Apply (replace) or insert the focused template into the current scene.

    Both paths go through the designer's undo-safe ``safe_save_state`` so the
    whole operation is a single Ctrl+Z and persists through save/codegen.
    """
    tpl = _current_template(app)
    if tpl is None:
        app._set_status("No template selected.", ttl_sec=2.0)
        return
    widgets = _template_widgets(tpl)
    if not widgets:
        app._set_status(f"'{tpl.metadata.name}' has no usable widgets.", ttl_sec=2.5)
        return
    try:
        sc = app.state.current_scene()
    except (AttributeError, TypeError, KeyError):
        sc = None
    if sc is None:
        return

    safe_save_state(app.designer)
    if insert:
        base = len(sc.widgets)
        sc.widgets.extend(widgets)
        new_sel = list(range(base, len(sc.widgets)))
        app.state.selected = new_sel
        app.state.selected_idx = new_sel[0] if new_sel else None
        verb = "Inserted"
    else:
        sc.widgets.clear()
        sc.widgets.extend(widgets)
        app.state.selected = [0] if sc.widgets else []
        app.state.selected_idx = 0 if sc.widgets else None
        verb = "Applied"
    app.designer.selected_widget = app.state.selected_idx
    app._set_status(
        f"{verb} '{tpl.metadata.name}' ({len(widgets)} widget(s)). Ctrl+Z to undo.",
        ttl_sec=2.5,
    )
    app._mark_dirty()
    close_template_manager(app)


def _delete_selected(app) -> None:
    tpl = _current_template(app)
    if tpl is None:
        app._set_status("No template selected.", ttl_sec=2.0)
        return
    name = tpl.metadata.name
    lib = app.template_library
    lib.remove_template(tpl)
    # Keep cursor in range after the list shrank.
    st = _state(app)
    st["cursor"] = max(0, min(int(st.get("cursor", 0)), max(0, len(_filtered(app)) - 1)))
    _refresh_picker_actions(app)
    app._set_status(f"Deleted template '{name}'.", ttl_sec=2.5)
    app._mark_dirty()


def _begin_rename(app) -> None:
    """Reuse the inspector text-input field to rename the focused template."""
    tpl = _current_template(app)
    if tpl is None:
        app._set_status("No template selected.", ttl_sec=2.0)
        return
    app._template_rename_target = tpl
    app.state.inspector_selected_field = "_template_rename"
    app.state.inspector_input_buffer = str(tpl.metadata.name)
    try:
        pygame.key.start_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status(
        f"Rename '{tpl.metadata.name}' (Enter=save Esc=cancel)", ttl_sec=4.0
    )
    app._mark_dirty()


def _save_scene_as_template(app) -> None:
    """Save the current selection (or whole scene) as a new template.

    Goes through ``scene_ops.save_selection_as_template`` when something is
    selected (so the existing, tested name-prompt flow is reused), otherwise
    captures the entire scene. Either way the new template is persisted via
    the library's real ``save_scene_as_template`` API by the name handler.
    """
    try:
        sc = app.state.current_scene()
    except (AttributeError, TypeError, KeyError):
        sc = None
    if sc is None or not getattr(sc, "widgets", None):
        app._set_status("Save template: scene is empty.", ttl_sec=2.5)
        return

    from dataclasses import asdict

    selected = list(getattr(app.state, "selected", []) or [])
    if selected:
        idxs = [i for i in selected if 0 <= i < len(sc.widgets)]
        scope = "selection"
    else:
        idxs = list(range(len(sc.widgets)))
        scope = "scene"
    widgets = [asdict(sc.widgets[i]) for i in idxs]
    if not widgets:
        app._set_status("Save template: nothing to save.", ttl_sec=2.5)
        return

    app._pending_template_widgets = widgets
    app.state.inspector_selected_field = "_template_name"
    app.state.inspector_input_buffer = ""
    try:
        pygame.key.start_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status(
        f"New template from {scope} ({len(widgets)} widget(s)) — "
        "name then Enter (Esc=cancel)",
        ttl_sec=4.0,
    )
    # Close the modal so the inspector name prompt is usable; the new
    # template shows up next time the manager is opened.
    close_template_manager(app)


def _refresh_picker_actions(app) -> None:
    """Keep the legacy palette/context picker lists in sync after a mutation."""
    try:
        app.template_actions = app._build_template_actions()
    except (AttributeError, TypeError):
        pass


def _move_cursor(app, delta: int) -> None:
    st = _state(app)
    items = _filtered(app)
    if not items:
        st["cursor"] = 0
        return
    cur = int(st.get("cursor", 0))
    st["cursor"] = max(0, min(len(items) - 1, cur + delta))
    app._mark_dirty()


# --------------------------------------------------------------------------- #
# Event handling (modal — mirrors icon_palette)
# --------------------------------------------------------------------------- #


def handle_key(app, event: pygame.event.Event) -> bool:
    """Consume a key while the manager is open. Returns True if handled.

    Wired from key_handlers.on_key_down *before* global dispatch (and after
    the inspector text-field check, so the rename/save name prompt still
    works while the modal logically remains the active surface)."""
    st = _state(app)
    if not st.get("visible"):
        return False

    # While a rename/save name prompt is active the inspector text field
    # owns the keyboard — let on_key_down's inspector branch handle it.
    if getattr(app.state, "inspector_selected_field", None):
        return False

    key = event.key
    if key == pygame.K_ESCAPE:
        close_template_manager(app)
        return True

    items = _filtered(app)
    rows = max(1, int(st.get("rows", 1)))

    if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        _apply_selected(app, insert=False)
        return True
    if key == pygame.K_INSERT:
        _apply_selected(app, insert=True)
        return True
    if key == pygame.K_DELETE:
        _delete_selected(app)
        return True
    if key == pygame.K_r and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
        _begin_rename(app)
        return True
    if key == pygame.K_s and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
        _save_scene_as_template(app)
        return True
    if key == pygame.K_BACKSPACE:
        st["query"] = str(st.get("query", ""))[:-1]
        st["cursor"] = 0
        st["scroll"] = 0
        app._mark_dirty()
        return True
    if key in (pygame.K_UP, pygame.K_LEFT):
        _move_cursor(app, -1)
        return True
    if key in (pygame.K_DOWN, pygame.K_RIGHT):
        _move_cursor(app, 1)
        return True
    if key == pygame.K_PAGEUP:
        _move_cursor(app, -rows)
        return True
    if key == pygame.K_PAGEDOWN:
        _move_cursor(app, rows)
        return True
    if key == pygame.K_HOME:
        st["cursor"] = 0
        app._mark_dirty()
        return True
    if key == pygame.K_END:
        st["cursor"] = max(0, len(items) - 1)
        app._mark_dirty()
        return True

    ch = event.unicode
    if ch and (ch.isalnum() or ch in ("_", " ", "-")):
        st["query"] = str(st.get("query", "")) + ch.lower()
        st["cursor"] = 0
        st["scroll"] = 0
        app._mark_dirty()
        return True

    # Swallow everything else so global shortcuts don't fire under the modal.
    return True


def handle_click(app, pos: Tuple[int, int]) -> bool:
    """Consume a click while the manager is open. Returns True if handled."""
    st = _state(app)
    if not st.get("visible"):
        return False

    for rect, action in st.get("button_hitboxes", []):
        if rect.collidepoint(pos[0], pos[1]):
            if action == "apply":
                _apply_selected(app, insert=False)
            elif action == "insert":
                _apply_selected(app, insert=True)
            elif action == "rename":
                _begin_rename(app)
            elif action == "delete":
                _delete_selected(app)
            elif action == "save":
                _save_scene_as_template(app)
            elif action == "close":
                close_template_manager(app)
            return True

    for rect, idx in st.get("list_hitboxes", []):
        if rect.collidepoint(pos[0], pos[1]):
            items = _filtered(app)
            if 0 <= idx < len(items):
                prev = int(st.get("cursor", 0))
                st["cursor"] = idx
                if prev == idx:
                    # Second click on the already-focused row = apply.
                    _apply_selected(app, insert=False)
                else:
                    app._mark_dirty()
            return True

    # Click outside any hot region dismisses the modal (icon_palette parity).
    close_template_manager(app)
    return True


def handle_wheel(app, dy: int) -> bool:
    """Consume a wheel event while the manager is open."""
    st = _state(app)
    if not st.get("visible"):
        return False
    _move_cursor(app, -int(dy))
    return True


# --------------------------------------------------------------------------- #
# Rendering — modeled on icon_palette.draw_icon_palette / overlays
# --------------------------------------------------------------------------- #


def _draw_preview(app, surface, rect: pygame.Rect, template) -> None:
    """Render the template's real scene scaled to fit *rect*."""
    from .drawing.canvas import draw_widget_preview
    from .drawing.text import draw_text_clipped

    pygame.draw.rect(surface, PALETTE["bg"], rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], rect, 1)

    widgets = _template_widgets(template)
    raw = getattr(getattr(template, "scene", None), "_raw_data", {}) or {}

    if not widgets:
        draw_text_clipped(
            app,
            surface=surface,
            text="(empty template)",
            rect=rect,
            fg=PALETTE["muted"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        return

    # Device extent: prefer the active scene size; fall back to the union of
    # widget extents so off-profile templates still preview sensibly.
    try:
        sc = app.state.current_scene()
        dev_w = int(getattr(sc, "width", 0) or 0)
        dev_h = int(getattr(sc, "height", 0) or 0)
    except (AttributeError, TypeError, KeyError):
        dev_w = dev_h = 0
    max_x = max(
        (int(getattr(w, "x", 0) or 0) + int(getattr(w, "width", 0) or 0)) for w in widgets
    )
    max_y = max(
        (int(getattr(w, "y", 0) or 0) + int(getattr(w, "height", 0) or 0)) for w in widgets
    )
    dev_w = max(dev_w, max_x, 1)
    dev_h = max(dev_h, max_y, 1)

    inset = 4
    avail_w = max(1, rect.width - inset * 2)
    avail_h = max(1, rect.height - inset * 2)
    scale = min(avail_w / dev_w, avail_h / dev_h)
    scale = max(0.05, min(scale, 4.0))
    view_w = int(dev_w * scale)
    view_h = int(dev_h * scale)
    ox = rect.x + (rect.width - view_w) // 2
    oy = rect.y + (rect.height - view_h) // 2

    # Draw the device artboard so the preview reads as a screen.
    board = pygame.Rect(ox, oy, max(1, view_w), max(1, view_h))
    pygame.draw.rect(surface, PALETTE.get("canvas", PALETTE["bg"]), board)

    prev_clip = surface.get_clip()
    surface.set_clip(board)
    base_bg = PALETTE.get("canvas", PALETTE["bg"])
    for w in widgets:
        wx = ox + int(int(getattr(w, "x", 0) or 0) * scale)
        wy = oy + int(int(getattr(w, "y", 0) or 0) * scale)
        ww = max(1, int(int(getattr(w, "width", 1) or 1) * scale))
        wh = max(1, int(int(getattr(w, "height", 1) or 1) * scale))
        wrect = pygame.Rect(wx, wy, ww, wh)
        try:
            draw_widget_preview(
                app,
                surface=surface,
                w=w,
                rect=wrect,
                base_bg=base_bg,
                padding=0,
                is_selected=False,
            )
        except (pygame.error, ValueError, TypeError, AttributeError):
            # A single bad widget must never break the whole preview.
            pygame.draw.rect(surface, PALETTE["muted"], wrect, 1)
    surface.set_clip(prev_clip)
    pygame.draw.rect(surface, PALETTE["panel_border"], board, 1)

    # Caption: real scene name + dimensions actually used.
    cap = pygame.Rect(rect.x + 2, rect.bottom - GRID * 2, rect.width - 4, GRID * 2)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"{raw.get('name', '?')}  {dev_w}x{dev_h}  ({len(widgets)} widgets)",
        rect=cap,
        fg=PALETTE["muted"],
        padding=0,
        align="center",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )


def draw_template_manager(app) -> None:
    """Draw the Template Manager modal overlay if open."""
    st = _state(app)
    if not st.get("visible"):
        return
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
    panel_w = max(GRID * 24, min(w - margin * 2, GRID * 72))
    panel_h = max(GRID * 18, min(h - margin * 2, GRID * 48))
    panel_w = max(GRID * 16, snap(panel_w))
    panel_h = max(GRID * 14, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)

    pygame.draw.rect(surface, PALETTE["panel"], panel_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], panel_rect, 1)

    items = _filtered(app)
    total = len(_all_templates(app))

    # Title + hint.
    title_rect = pygame.Rect(x + pad, y + pad, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"Template Manager  ({len(items)}/{total})",
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
        text="Enter=apply  Ins=insert  Esc=close",
        rect=title_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    # Search row.
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

    # Body: left list / right preview.
    body_top = y + pad + row_h * 2 + pad
    btn_h = row_h
    body_bottom = y + panel_h - pad - btn_h - pad
    list_w = max(GRID * 8, int(panel_w * 0.42))
    list_rect = pygame.Rect(x + pad, body_top, list_w, max(1, body_bottom - body_top))
    prev_rect = pygame.Rect(
        list_rect.right + pad,
        body_top,
        max(1, (x + panel_w - pad) - (list_rect.right + pad)),
        max(1, body_bottom - body_top),
    )

    pygame.draw.rect(surface, PALETTE["bg"], list_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], list_rect, 1)

    st["list_hitboxes"] = []
    st["button_hitboxes"] = []

    if not items:
        draw_text_clipped(
            app,
            surface=surface,
            text="No templates." if total == 0 else "No matches for this search.",
            rect=list_rect,
            fg=PALETTE["muted"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
    else:
        cursor = max(0, min(len(items) - 1, int(st.get("cursor", 0))))
        st["cursor"] = cursor
        line_h = row_h + 2
        rows = max(1, list_rect.height // line_h)
        st["rows"] = rows

        scroll = int(st.get("scroll", 0))
        if cursor < scroll:
            scroll = cursor
        elif cursor >= scroll + rows:
            scroll = cursor - rows + 1
        scroll = max(0, min(scroll, max(0, len(items) - rows)))
        st["scroll"] = scroll

        first = scroll
        last = min(len(items), first + rows)
        list_hits: List[Tuple[pygame.Rect, int]] = []
        for li in range(first, last):
            rel = li - first
            row_rect = pygame.Rect(
                list_rect.x + 1,
                list_rect.y + 1 + rel * line_h,
                list_rect.width - 2,
                line_h,
            )
            is_cur = li == cursor
            if is_cur:
                pygame.draw.rect(surface, PALETTE["selection"], row_rect)
            meta = items[li].metadata
            n_w = len(_template_widgets(items[li]))
            draw_text_clipped(
                app,
                surface=surface,
                text=f"{meta.name}",
                rect=pygame.Rect(
                    row_rect.x + pad, row_rect.y, row_rect.width - 2 * pad, row_h
                ),
                fg=PALETTE["bg"] if is_cur else PALETTE["text"],
                padding=0,
                align="left",
                valign="middle",
                max_lines=1,
                use_device_font=False,
            )
            draw_text_clipped(
                app,
                surface=surface,
                text=f"{meta.category} - {n_w}w",
                rect=pygame.Rect(
                    row_rect.x + pad, row_rect.y, row_rect.width - 2 * pad, row_h
                ),
                fg=PALETTE["bg"] if is_cur else PALETTE["muted"],
                padding=0,
                align="right",
                valign="middle",
                max_lines=1,
                use_device_font=False,
            )
            list_hits.append((row_rect, li))
        st["list_hitboxes"] = list_hits

        # Right pane: live, faithful preview of the focused template.
        _draw_preview(app, surface, prev_rect, items[cursor])

    # Action button row.
    btn_y = y + panel_h - pad - btn_h
    labels = [
        ("Apply", "apply"),
        ("Insert", "insert"),
        ("Rename", "rename"),
        ("Delete", "delete"),
        ("Save Scene", "save"),
        ("Close", "close"),
    ]
    avail = panel_w - 2 * pad
    bw = max(GRID * 5, avail // len(labels) - pad)
    bx = x + pad
    btn_hits: List[Tuple[pygame.Rect, str]] = []
    enabled = bool(items)
    for label, action in labels:
        brect = pygame.Rect(bx, btn_y, bw, btn_h)
        is_disabled = (not enabled) and action in {
            "apply",
            "insert",
            "rename",
            "delete",
        }
        pygame.draw.rect(surface, PALETTE["bg"], brect)
        pygame.draw.rect(
            surface,
            PALETTE["muted"] if is_disabled else PALETTE["panel_border"],
            brect,
            1,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text=label,
            rect=brect,
            fg=PALETTE["muted"] if is_disabled else PALETTE["accent_cyan"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        if not is_disabled:
            btn_hits.append((brect, action))
        bx += bw + pad
    st["button_hitboxes"] = btn_hits


# Headless smoke tests run without a display.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
