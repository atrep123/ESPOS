from __future__ import annotations

import time

import pygame

from ..constants import PALETTE
from .primitives import draw_pixel_frame, draw_pixel_panel_bg, render_pixel_text
from .text import draw_text_clipped
from .widgets import draw_scrollbar


def draw_palette(app) -> None:
    r = app.layout.palette_rect
    draw_pixel_panel_bg(app, r)
    title = render_pixel_text(app, "Widgets", PALETTE["text"], shadow=app._shade(PALETTE["panel_border"], -24))
    app.logical_surface.blit(title, (r.x + app.pixel_padding, r.y + (app.pixel_padding // 2)))

    row_h = int(app.pixel_row_height)
    content_rect = pygame.Rect(r.x, r.y + row_h, r.width, max(0, r.height - row_h))

    try:
        content_h = int(app._palette_content_height())
    except Exception:
        content_h = 0
    view_h = max(0, int(content_rect.height))
    max_scroll = max(0, content_h - view_h)
    try:
        app.state.palette_scroll = max(0, min(max_scroll, int(getattr(app.state, "palette_scroll", 0) or 0)))
    except Exception:
        app.state.palette_scroll = 0

    y = content_rect.y - int(getattr(app.state, "palette_scroll", 0) or 0)
    app.palette_hitboxes = []
    app.palette_section_hitboxes = []
    app.palette_widget_hitboxes = []

    collapsed = getattr(app, "palette_collapsed", set())
    pad = app.pixel_padding

    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(content_rect)
    try:
        for sec_name, items in getattr(app, "palette_sections", []):
            is_collapsed = sec_name in collapsed
            # Section header
            hdr_rect = pygame.Rect(r.x, y, r.width, row_h)
            hdr_hit = hdr_rect.clip(content_rect)
            is_hover = app._is_pointer_over(hdr_hit)
            hdr_fill = app._shade(PALETTE["panel_border"], -20)
            if is_hover:
                hdr_fill = app._shade(hdr_fill, 12)
            pygame.draw.rect(app.logical_surface, hdr_fill, hdr_rect)
            arrow = ">" if is_collapsed else "v"
            hdr_label = f"{arrow} {sec_name} ({len(items)})"
            draw_text_clipped(
                app,
                surface=app.logical_surface,
                text=hdr_label,
                rect=hdr_rect,
                fg=PALETTE["accent_cyan"] if not is_collapsed else PALETTE["muted"],
                padding=pad // 2,
                align="left",
                valign="middle",
                max_lines=1,
            )
            app.palette_section_hitboxes.append((hdr_hit, sec_name))
            y += row_h

            if is_collapsed:
                continue

            # Section items
            alt_stride = False
            for label, action in items:
                rect = pygame.Rect(r.x + pad, y, r.width - 2 * pad, row_h)
                rect = app._snap_rect(rect)
                hit_rect = rect.clip(content_rect)
                is_hover = app._is_pointer_over(hit_rect)
                is_pressed = is_hover and app.pointer_down
                fill = app._shade(PALETTE["panel"], -8 if alt_stride else -4)
                if is_hover:
                    fill = app._shade(fill, 10)
                pygame.draw.rect(app.logical_surface, fill, rect)
                draw_rect = rect.move(0, (1 if is_pressed else 0))
                draw_text_clipped(
                    app,
                    surface=app.logical_surface,
                    text=label,
                    rect=draw_rect,
                    fg=PALETTE["text"],
                    padding=pad // 2,
                    align="left",
                    valign="middle",
                    max_lines=1,
                )
                app.palette_hitboxes.append((hit_rect, label.lower(), bool(action)))
                alt_stride = not alt_stride
                y += row_h

        sc = app.state.current_scene()
        y += pad
        for idx, w in enumerate(sc.widgets):
            rect = pygame.Rect(r.x + pad, y, r.width - 2 * pad, row_h)
            rect = app._snap_rect(rect)
            hit_rect = rect.clip(content_rect)
            is_hover = app._is_pointer_over(hit_rect)
            is_pressed = is_hover and app.pointer_down
            fill = app._shade(PALETTE["panel"], -14 if idx % 2 else -10)
            if idx in app.state.selected:
                fill = app._shade(PALETTE["selection"], -80)
            if is_hover:
                fill = app._shade(fill, 8)
            pygame.draw.rect(app.logical_surface, fill, rect)
            label = f"[{idx}] {w.type}"
            draw_rect = rect.move(0, (1 if is_pressed else 0))
            draw_text_clipped(
                app,
                surface=app.logical_surface,
                text=label,
                rect=draw_rect,
                fg=PALETTE["text"],
                padding=pad // 2,
                align="left",
                valign="middle",
                max_lines=1,
            )
            app.palette_widget_hitboxes.append((hit_rect, idx))
            y += row_h

        draw_scrollbar(
            app,
            content_rect,
            scroll=int(getattr(app.state, "palette_scroll", 0) or 0),
            max_scroll=max_scroll,
            content_h=content_h,
        )
    finally:
        app.logical_surface.set_clip(old_clip)


def draw_inspector(app) -> None:
    """Inspector panel with cached hitboxes (click row to edit)."""
    r = app.layout.inspector_rect
    draw_pixel_panel_bg(app, r)
    rows, warning, _sel = app._compute_inspector_rows()

    row_h = int(app.pixel_row_height)
    content_rect = pygame.Rect(r.x, r.y + row_h, r.width, max(0, r.height - row_h))

    try:
        content_h = int(app._inspector_content_height())
    except Exception:
        content_h = 0
    view_h = max(0, int(content_rect.height))
    max_scroll = max(0, content_h - view_h)
    try:
        app.state.inspector_scroll = max(0, min(max_scroll, int(getattr(app.state, "inspector_scroll", 0) or 0)))
    except Exception:
        app.state.inspector_scroll = 0

    y = content_rect.y - int(getattr(app.state, "inspector_scroll", 0) or 0)
    app.inspector_hitboxes = []
    alt_stride = False

    title = render_pixel_text(app, "Inspector", PALETTE["text"], shadow=app._shade(PALETTE["panel_border"], -24))
    app.logical_surface.blit(title, (r.x + app.pixel_padding, r.y + (app.pixel_padding // 2)))

    edit_key = app.state.inspector_selected_field
    edit_buf = app.state.inspector_input_buffer

    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(content_rect)
    try:
        collapsed = getattr(app, "inspector_collapsed", set())
        app.inspector_section_hitboxes = []
        current_section: str | None = None
        pad = app.pixel_padding

        for key, text in rows:
            # Section header
            if isinstance(key, str) and key.startswith("_section:"):
                sec_name = key[len("_section:"):]
                current_section = sec_name
                is_collapsed = sec_name in collapsed
                hdr_rect = pygame.Rect(r.x, y, r.width, row_h)
                hdr_hit = hdr_rect.clip(content_rect)
                is_hover = app._is_pointer_over(hdr_hit)
                hdr_fill = app._shade(PALETTE["panel_border"], -20)
                if is_hover:
                    hdr_fill = app._shade(hdr_fill, 12)
                pygame.draw.rect(app.logical_surface, hdr_fill, hdr_rect)
                arrow = ">" if is_collapsed else "v"
                hdr_label = f"{arrow} {text}"
                draw_text_clipped(
                    app,
                    surface=app.logical_surface,
                    text=hdr_label,
                    rect=hdr_rect,
                    fg=PALETTE["accent_cyan"] if not is_collapsed else PALETTE["muted"],
                    padding=pad // 2,
                    align="left",
                    valign="middle",
                    max_lines=1,
                )
                app.inspector_section_hitboxes.append((hdr_hit, sec_name))
                y += row_h
                alt_stride = False
                continue

            # Skip rows in collapsed sections
            if current_section and current_section in collapsed:
                continue

            rect = pygame.Rect(r.x + pad, y, r.width - 2 * pad, row_h)
            rect = app._snap_rect(rect)
            hit_rect = rect.clip(content_rect)
            is_hover = app._is_pointer_over(hit_rect)
            is_pressed = is_hover and app.pointer_down
            is_editing = bool(edit_key) and key == edit_key
            fill = app._shade(PALETTE["panel"], -8 if alt_stride else -4)
            if key == "resources" and warning:
                fill = app._shade(PALETTE["locked"], -80)
            if is_editing:
                fill = app._shade(PALETTE["accent_cyan"], -210)
            # Layer drag highlight
            layer_drag = getattr(app, "_layer_drag_idx", None)
            if layer_drag is not None and key.startswith("layer:") and is_hover:
                try:
                    target = int(key.split(":", 1)[1])
                except Exception:  # pragma: no cover — key always "layer:N"
                    target = -1
                if target != layer_drag and target >= 0:
                    fill = app._shade(PALETTE["accent_cyan"], -180)
            if is_hover:
                fill = app._shade(fill, 10)
            pygame.draw.rect(app.logical_surface, fill, rect)
            draw_pixel_frame(app, rect, pressed=is_pressed, hover=is_hover)
            display = str(text)
            if is_editing:
                display = f"{key}: {edit_buf}_"
            draw_rect = rect.move(0, (1 if is_pressed else 0))
            draw_text_clipped(
                app,
                surface=app.logical_surface,
                text=display,
                rect=draw_rect,
                fg=PALETTE["text"],
                padding=pad // 2,
                align="left",
                valign="middle",
                max_lines=1,
            )
            app.inspector_hitboxes.append((hit_rect, str(key)))
            alt_stride = not alt_stride
            y += row_h

        draw_scrollbar(
            app,
            content_rect,
            scroll=int(getattr(app.state, "inspector_scroll", 0) or 0),
            max_scroll=max_scroll,
            content_h=content_h,
        )
    finally:
        app.logical_surface.set_clip(old_clip)


def draw_status(app) -> None:
    """Status bar with file/selection info."""
    r = app.layout.status_rect
    fill = app._shade(PALETTE["panel"], -6)
    pygame.draw.rect(app.logical_surface, fill, r)
    draw_pixel_frame(app, r)
    try:
        sc = app.state.current_scene()
    except Exception:
        sc = None

    dirty_mark = "*" if app._dirty else ""
    file_label = getattr(app.json_path, "name", "scene.json")
    dim = ""
    wcount = ""
    scene_label = ""
    if sc is not None:
        dim = f"{int(getattr(sc, 'width', 0))}x{int(getattr(sc, 'height', 0))}"
        wcount = f"({len(sc.widgets)}w)"
    # Show scene name when multiple scenes exist
    try:
        scene_names = list((getattr(app, 'designer', None) or app).scenes.keys())
        if len(scene_names) > 1:
            cur = getattr(app.designer, 'current_scene', '')
            idx = scene_names.index(cur) + 1 if cur in scene_names else 0
            scene_label = f"[{idx}/{len(scene_names)}:{cur}]"
    except Exception:  # pragma: no cover — defensive
        pass
    left = f"{dirty_mark}{file_label}  {dim} {wcount} {scene_label}".strip()

    # Mouse position on canvas
    mouse_label = ""
    sr = getattr(app, "scene_rect", None)
    if isinstance(sr, pygame.Rect) and sr.collidepoint(app.pointer_pos[0], app.pointer_pos[1]):
        mx = int(app.pointer_pos[0]) - sr.x
        my = int(app.pointer_pos[1]) - sr.y
        mouse_label = f"({mx},{my})"
        # Show hovered widget type in status
        if sc is not None:
            hover_idx = app.state.hit_test_at(app.pointer_pos, sr)
            if hover_idx is not None and 0 <= hover_idx < len(sc.widgets):
                hw = sc.widgets[hover_idx]
                mouse_label += f" [{hover_idx}]{hw.type}"

    w = app.state.selected_widget()
    n_sel = len(getattr(app.state, "selected", []) or [])
    if n_sel > 1:
        sel = f"sel: {n_sel} widgets"
    elif w is None:
        sel = "sel: -"
    else:
        flags = ""
        if bool(getattr(w, "locked", False)):
            flags += "L"
        if not bool(getattr(w, "visible", True)):
            flags += "H"
        if not bool(getattr(w, "enabled", True)):
            flags += "D"
        style_val = str(getattr(w, "style", "default") or "default")
        if style_val != "default":
            flags += f":{style_val}"
        flag_str = f" [{flags}]" if flags else ""
        sel = f"sel: {w.type} {int(w.x)},{int(w.y)} {int(w.width)}x{int(w.height)}{flag_str}"
    mode = "IN" if app.sim_input_mode else "ED"
    focus = ""
    if app.sim_input_mode and sc is not None:
        app._ensure_focus()
        if app.focus_idx is not None and 0 <= int(app.focus_idx) < len(sc.widgets):
            fw = sc.widgets[int(app.focus_idx)]
            focus = f" focus:{int(app.focus_idx)}:{fw.type}"
            if app.focus_edit_value:
                focus += ":edit"
    right = f"{sel}  snap:{int(app.snap_enabled)} grid:{int(app.show_grid)} mode:{mode}{focus}"
    # Zoom level
    scale_val = int(getattr(app, "scale", 2) or 2)
    right += f" {scale_val}x"
    # Undo/redo count
    try:
        undo_n = len(getattr(app.designer, "undo_stack", []) or [])
        redo_n = len(getattr(app.designer, "redo_stack", []) or [])
        if undo_n or redo_n:
            right += f" u:{undo_n}/r:{redo_n}"
    except Exception:
        pass

    msg = ""
    if app.dialog_message and time.time() < float(getattr(app, "_status_until_ts", 0.0)):
        msg = app.dialog_message
    elif mouse_label:
        msg = mouse_label

    pad = max(2, app.pixel_padding // 2)
    x0 = r.x + pad
    x1 = r.right - pad
    content_w = max(0, x1 - x0)
    third = max(1, content_w // 3)
    left_rect = pygame.Rect(x0, r.y, third, r.height)
    msg_rect = pygame.Rect(x0 + third, r.y, third, r.height)
    right_rect = pygame.Rect(x0 + (2 * third), r.y, max(0, content_w - (2 * third)), r.height)

    draw_text_clipped(
        app,
        surface=app.logical_surface,
        text=left,
        rect=left_rect,
        fg=PALETTE["text"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
    )
    if msg:
        draw_text_clipped(
            app,
            surface=app.logical_surface,
            text=str(msg),
            rect=msg_rect,
            fg=PALETTE["accent_yellow"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
        )
    draw_text_clipped(
        app,
        surface=app.logical_surface,
        text=right,
        rect=right_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
    )
