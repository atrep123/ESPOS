"""Context menu, tooltip, and help overlay rendering."""

from __future__ import annotations

import time

import pygame

from ui_designer import HARDWARE_PROFILES

from ..constants import GRID, PALETTE, snap
from .primitives import draw_pixel_panel_bg, render_pixel_text
from .text import draw_text_clipped, text_width_px

# Toolbar button tooltips (key = lowercased label)
TOOLBAR_TOOLTIPS = {
    "new": "New scene (Ctrl+N)",
    "load": "Load JSON (Ctrl+L)",
    "save": "Save JSON (Ctrl+S)",
    "live": "Live preview serial port",
    "arrange": "Auto-arrange grid (F7)",
    "fit text": "Fit text to widget (Ctrl+F)",
    "fit widget": "Fit widget to text (Ctrl+Shift+F)",
    "warn": "Toggle overflow warnings",
    "refresh ports": "Scan serial ports",
}


def draw_context_menu(app) -> None:
    """Draw right-click context menu if open."""
    menu = getattr(app, "_context_menu", None)
    if not menu or not menu.get("visible"):
        return
    surface = getattr(app, "logical_surface", None)
    if surface is None:
        return
    items = menu.get("items", [])
    if not items:
        return

    pad = max(2, int(getattr(app, "pixel_padding", 0) or 0))
    row_h = max(1, int(getattr(app, "pixel_row_height", 0) or 0))
    sep_h = max(1, row_h // 2)
    mx, my = menu["pos"]

    # Measure width
    max_w = GRID * 14
    for label, _key, action in items:
        if action is None:
            continue
        tw = text_width_px(app, label) + pad * 4
        if tw > max_w:
            max_w = tw
    panel_w = max_w + pad * 2
    panel_h = pad * 2
    for _label, _key, action in items:
        panel_h += sep_h if action is None else row_h

    # Clamp to screen
    sw = surface.get_width()
    sh = surface.get_height()
    if mx + panel_w > sw:
        mx = max(0, sw - panel_w)
    if my + panel_h > sh:
        my = max(0, sh - panel_h)

    panel_rect = pygame.Rect(mx, my, panel_w, panel_h)
    pygame.draw.rect(surface, PALETTE["panel"], panel_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], panel_rect, 1)

    hitboxes = []
    cy = my + pad
    for label, shortcut, action in items:
        if action is None:
            # Draw separator line
            sep_y = cy + sep_h // 2
            sep_color = PALETTE.get("panel_border", (60, 60, 60))
            pygame.draw.line(surface, sep_color, (mx + pad, sep_y), (mx + panel_w - pad, sep_y))
            cy += sep_h
            continue
        item_rect = pygame.Rect(mx + 1, cy, panel_w - 2, row_h)
        is_hover = item_rect.collidepoint(app.pointer_pos[0], app.pointer_pos[1])
        if is_hover:
            pygame.draw.rect(surface, PALETTE.get("accent_cyan", (80, 200, 220)), item_rect)
        text_r = pygame.Rect(mx + pad, cy, panel_w - pad * 2, row_h)
        fg = PALETTE["text"] if not is_hover else PALETTE["panel"]
        draw_text_clipped(
            app,
            surface=surface,
            text=label,
            rect=text_r,
            fg=fg,
            padding=0,
            align="left",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        if shortcut:
            draw_text_clipped(
                app,
                surface=surface,
                text=shortcut,
                rect=text_r,
                fg=fg,
                padding=0,
                align="right",
                valign="middle",
                max_lines=1,
                use_device_font=False,
            )
        hitboxes.append((item_rect, action))
        cy += row_h

    menu["hitboxes"] = hitboxes
    menu["rect"] = panel_rect


def draw_tooltip(app) -> None:
    """Draw hover tooltip near pointer for toolbar buttons and tabs."""
    if app.pointer_down:
        app._tooltip_key = None
        return
    now = time.time()
    lx, ly = getattr(app, "pointer_pos", (0, 0))
    tip_text = None

    # Check toolbar hitboxes
    for rect, key in getattr(app, "toolbar_hitboxes", []):
        if rect.collidepoint(lx, ly):
            tip_text = TOOLBAR_TOOLTIPS.get(key, "")
            break

    # Check tab hitboxes
    if not tip_text:
        for rect, tab_idx, tab_name in getattr(app, "tab_hitboxes", []):
            if rect.collidepoint(lx, ly):
                if tab_idx == -1:
                    tip_text = "Add new scene (Ctrl+N)"
                else:
                    sc = app.designer.scenes.get(tab_name)
                    n_widgets = len(sc.widgets) if sc else 0
                    dirty = tab_name in getattr(app, "_dirty_scenes", set())
                    tip_text = f"{tab_name}: {n_widgets} widgets"
                    if dirty:
                        tip_text += " (modified)"
                    if tab_idx < 9:
                        tip_text += f" (Ctrl+{tab_idx + 1})"
                break

    if not tip_text:
        app._tooltip_key = None
        return

    # Track hover time for delay
    prev_key = getattr(app, "_tooltip_key", None)
    if tip_text != prev_key:
        app._tooltip_key = tip_text
        app._tooltip_start = now
        return
    elapsed = now - getattr(app, "_tooltip_start", now)
    if elapsed < 0.5:
        return

    # Render tooltip
    surface = app.logical_surface
    pad = max(2, app.pixel_padding // 2)
    txt_surf = render_pixel_text(app, tip_text, PALETTE["text"])
    tw = txt_surf.get_width() + pad * 2
    th = txt_surf.get_height() + pad * 2
    tx = min(lx + 8, surface.get_width() - tw - 2)
    ty = ly + 16
    if ty + th > surface.get_height():
        ty = ly - th - 4
    tip_rect = pygame.Rect(tx, ty, tw, th)
    pygame.draw.rect(surface, PALETTE["panel"], tip_rect)
    pygame.draw.rect(surface, PALETTE["accent_cyan"], tip_rect, 1)
    surface.blit(txt_surf, (tx + pad, ty + pad))


def draw_help_overlay(app) -> None:
    """Draw a modal help/self-check overlay (toggle via F1)."""
    if not bool(getattr(app, "show_help_overlay", False)):
        return
    surface = getattr(app, "logical_surface", None)
    if surface is None:
        return
    layout = getattr(app, "layout", None)
    if layout is None:
        return
    w = int(getattr(layout, "width", 0) or 0)
    h = int(getattr(layout, "height", 0) or 0)
    if w <= 0 or h <= 0:
        return

    # Dim background.
    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 160))
    surface.blit(dim, (0, 0))

    pad = max(2, int(getattr(app, "pixel_padding", 0) or 0))
    row_h = max(1, int(getattr(app, "pixel_row_height", 0) or 0))

    margin = GRID * 2
    panel_w = max(GRID * 22, min(w - margin * 2, GRID * 70))
    panel_h = max(GRID * 18, min(h - margin * 2, GRID * 48))
    panel_w = max(GRID * 10, snap(panel_w))
    panel_h = max(GRID * 10, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)

    draw_pixel_panel_bg(app, panel_rect)

    title = "Help / Self-check"
    title_hint = "F1/Esc/click = close"
    title_rect = pygame.Rect(panel_rect.x + pad, panel_rect.y, panel_rect.width - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"{title} ({title_hint})",
        rect=title_rect,
        fg=PALETTE["accent_yellow"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    content_rect = pygame.Rect(
        panel_rect.x + pad,
        panel_rect.y + row_h,
        panel_rect.width - 2 * pad,
        panel_rect.height - row_h - pad,
    )
    if content_rect.width <= 0 or content_rect.height <= 0:
        return

    shortcuts = [
        "Mouse: LMB select/drag | handles resize",
        "Shift+click: range select | Ctrl+click: toggle",
        "Alt+drag: clone and drag | box-select on empty",
        "Double-click: edit widget text",
        "Right-click: context menu",
        "Esc: deselect (quit if empty) | Arrows: nudge",
        "Ctrl+Arrow: 1px precise nudge | Shift+Arrow: 4x",
        "1-9: quick add (label btn panel prog gauge sldr chk chart icon)",
        "Ctrl+S save | Ctrl+L load | Ctrl+E export C",
        "Ctrl+N new scene | Ctrl+Shift+Del delete scene",
        "Ctrl+Tab/Shift+Tab next/prev scene | Ctrl+1-9 jump",
        "Ctrl+PgUp/PgDn switch scene | Drag tab reorder | Wheel on tabs",
        "DblClick tab: rename | MidClick tab: close",
        "Ctrl+Z undo | Ctrl+Shift+Z redo | Ctrl+Y redo",
        "Ctrl+C/X/V/D copy/cut/paste/dup | Del delete",
        "Ctrl+F fit text | Ctrl+Shift+F fit widget",
        "[/] z-order step | Ctrl+[/] front/back",
        "L lock | V show/hide | S cycle style | R rename",
        "T cycle type | B cycle border | Q cycle color",
        "Shift+T text_overflow | Shift+B border_width | Shift+V value range",
        "W border on/off | O overflow | A align | Shift+A valign",
        "M mirror horiz | Shift+M mirror vert",
        "I edit icon | E smart edit | Shift+E edit runtime",
        "F6 arrange row | F7 arrange col | F8 toggle enabled",
        "+/- adjust value (Shift: +/-5) | Ctrl+R rename scene",
        "H set size (WxH) | Shift+H set position (X,Y)",
        "K set padding (Px,Py) | J set margin (Mx,My)",
        "Shift+Q swap fg/bg | C edit fg | Shift+C edit bg",
        "Shift+D array dup | Shift+L select locked | Shift+O select overflow",
        "Shift+S select style | Shift+Y select hidden | Shift+I widget info",
        "Shift+W full width | Shift+F full height | Shift+X swap W/H",
        "Shift+U select z-layer | Shift+K set all spacing",
        "D edit data_points | Y toggle checked",
        "F set max_lines | U set z-index | Shift+U select z-layer",
        "Ctrl+I invert selection | Ctrl+B select same color | Ctrl+W stats",
        "Ctrl+H parent panel | Ctrl+K select children | Ctrl+O copy to scene",
        "Ctrl+M snap to grid | Ctrl+P paste in place | Ctrl+U same size",
        "Ctrl+Q broadcast to scenes | Shift+J clear margins",
        "Shift+R auto-rename | Ctrl+Shift+A same type",
        "Ctrl+Shift+H hide unselected | Ctrl+Shift+B select bordered",
        "Ctrl+Shift+M move to origin | Ctrl+Shift+W fit scene to content",
        "Ctrl+Shift+I show all | Ctrl+Shift+L unlock all",
        "Ctrl+Shift+U select overlapping | Ctrl+Shift+O toggle all borders",
        "Ctrl+Shift+S sort by pos | Ctrl+Shift+X remove degenerate",
        "Ctrl+Shift+Y enable all | Ctrl+Shift+N compact to origin",
        "Ctrl+Shift+T list templates | Ctrl+Shift+J snap pos+size",
        "Ctrl+Shift+P select panels | Ctrl+Shift+Q quick clone",
        "Ctrl+Shift+E extract to scene | Ctrl+Shift+K clear padding",
        "` toggle widget IDs | ~ toggle z-index labels",
        "; stack vertical | ' stack horizontal (layout)",
        "Shift+; equalize heights | Shift+' equalize widths",
        ", swap positions (2 sel) | . center in scene",
        "Shift+, duplicate below | Shift+. duplicate right",
        "\\ cycle gray FG | Shift+\\ cycle gray BG (4-bit)",
        "Ctrl+Alt+S shrink-wrap | Ctrl+Alt+E equalize gaps",
        "Ctrl+Alt+G grid arrange | Ctrl+Alt+R reverse order",
        "Ctrl+Alt+F flip vertical | Ctrl+Alt+N normalize sizes",
        "Ctrl+Alt+A name all scene | Ctrl+Alt+B propagate border",
        "Ctrl+Alt+D remove duplicates | Ctrl+Alt+I increment text #",
        "Ctrl+Alt+P propagate style | Ctrl+Alt+X swap content (2 sel)",
        "Ctrl+Alt+O outline mode | Ctrl+Alt+L clone text",
        "Ctrl+Alt+J propagate align | Ctrl+Alt+K propagate colors",
        "Ctrl+Alt+M flip horizontal | Ctrl+Alt+Q propagate value",
        "Ctrl+Alt+U prop padding | Ctrl+Alt+Y prop margin",
        "Ctrl+Alt+Z propagate full look (style+colors+border+align+pad)",
        "0 add textbox | Shift+0 add radiobutton | Ctrl+Shift+0 flatten z",
        "Ctrl+T save as template | / search widgets | Shift+N/P extend sel",
        "Ctrl+Shift+D duplicate scene | F10/Shift+F10 next/prev scene",
        "F9 clean preview | Ctrl+J go to widget",
        "N next widget | P prev widget",
        "Home/End first/last | Ctrl+Shift+Up/Dn reorder",
        "Ctrl+Shift+C/V copy/paste style",
        "F2 input-mode | F3 overflow warn | F4 zoom-to-fit",
        "G grid | X snap | Tab panels | Shift+G center guides",
        "Ctrl+0 reset zoom | Ctrl+/- zoom | Wheel zoom",
        "Rulers on edges | Distance lines on drag",
        "F11 fullscreen | F12 screenshot",
        "Ctrl+Alt+Arrows align | Ctrl+Alt+H/V distribute",
        "Ctrl+Alt+W/T match size | Ctrl+Alt+C center",
        "Ctrl+1..9 jump to scene | Ctrl+F6 flow layout",
        "Ctrl+F7 measure gaps | Ctrl+F8 space even H",
        "Ctrl+F9 space even V | Ctrl+F5 find/replace text",
        "Ctrl+F3 select same type | Ctrl+F4 zoom to selection",
        "Ctrl+F10 scene overview | Ctrl+F1 type summary",
        "Ctrl+F2 focus order overlay | Ctrl+F11 export sel JSON",
        "Shift+F1 header bar | Shift+F2 nav row | Shift+F3 form pair",
        "Shift+F4 status bar | Shift+F5 toggle grp | Shift+F6 slider+lbl",
        "Shift+F7 gauge panel | Shift+F8 progress row | Shift+F9 icon btns",
        "Shift+F11 card | Shift+F12 dashboard 2x2 | Ctrl+F12 split",
    ]

    sc = None
    try:
        sc = app.state.current_scene()
    except AttributeError:
        sc = None

    profile_label = str(getattr(app, "hardware_profile", "") or "")
    if profile_label and profile_label in HARDWARE_PROFILES:
        try:
            profile_label = str(HARDWARE_PROFILES[profile_label].get("label") or profile_label)
        except (KeyError, TypeError, AttributeError):
            pass
    if not profile_label:
        profile_label = "none"

    scene_dims = "?"
    widgets_count = "?"
    if sc is not None:
        try:
            scene_dims = f"{int(getattr(sc, 'width', 0))}x{int(getattr(sc, 'height', 0))}"
        except (ValueError, TypeError):
            scene_dims = "?"
        try:
            widgets_count = str(len(getattr(sc, "widgets", []) or []))
        except (AttributeError, TypeError):
            widgets_count = "?"

    est = None
    try:
        est = app.designer.estimate_resources(profile=getattr(app, "hardware_profile", None))
    except AttributeError:
        est = None
    res_line = "resources: n/a"
    overlaps = 0
    if est:
        try:
            res_line = f"resources: FB {float(est.get('framebuffer_kb', 0.0)):.1f}KB | Flash {float(est.get('flash_kb', 0.0)):.1f}KB"
        except (ValueError, TypeError, AttributeError):
            res_line = "resources: (error)"
        try:
            overlaps = int(est.get("overlaps", 0) or 0)
        except (ValueError, TypeError):
            overlaps = 0

    sel_count = 0
    try:
        sel_count = len(getattr(app.state, "selected", []) or [])
    except (AttributeError, TypeError):
        sel_count = 0

    info = [
        f"file: {getattr(getattr(app, 'json_path', None), 'name', 'scene.json')}",
        f"profile: {profile_label}",
        f"scene: {scene_dims} | widgets: {widgets_count}",
        res_line,
        f"overlaps: {overlaps}" if overlaps else "overlaps: 0",
        f"scale: {int(getattr(app, 'scale', 1) or 1)} | locked: {int(bool(getattr(app, '_scale_locked', False)))}",
        f"snap: {int(bool(getattr(app, 'snap_enabled', True)))} | grid: {int(bool(getattr(app, 'show_grid', True)))}",
        f"selected: {sel_count} | panels: {'collapsed' if bool(getattr(app, 'panels_collapsed', False)) else 'open'}",
        f"mode: {'IN' if bool(getattr(app, 'sim_input_mode', False)) else 'ED'}",
    ]

    gap = pad
    use_cols = content_rect.width >= GRID * 70
    if use_cols:  # pragma: no cover — panel_w capped at GRID*70, content always narrower
        col_w = max(GRID * 18, (content_rect.width - gap) // 2)
        left = pygame.Rect(content_rect.x, content_rect.y, col_w, content_rect.height)
        right = pygame.Rect(
            content_rect.x + col_w + gap,
            content_rect.y,
            content_rect.width - col_w - gap,
            content_rect.height,
        )

        header_h = min(row_h, max(1, content_rect.height // 6))
        left_header = pygame.Rect(left.x, left.y, left.width, header_h)
        left_body = pygame.Rect(left.x, left.y + header_h, left.width, left.height - header_h)
        right_header = pygame.Rect(right.x, right.y, right.width, header_h)
        right_body = pygame.Rect(right.x, right.y + header_h, right.width, right.height - header_h)

        draw_text_clipped(
            app,
            surface=surface,
            text="Shortcuts",
            rect=left_header,
            fg=PALETTE["accent_cyan"],
            padding=0,
            align="left",
            valign="top",
            max_lines=1,
            use_device_font=False,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text="\n".join(shortcuts),
            rect=left_body,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=999,
            use_device_font=False,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text="Self-check",
            rect=right_header,
            fg=PALETTE["accent_cyan"],
            padding=0,
            align="left",
            valign="top",
            max_lines=1,
            use_device_font=False,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text="\n".join(info),
            rect=right_body,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=999,
            use_device_font=False,
        )
    else:
        combined = "\n".join(["Shortcuts"] + shortcuts + ["", "Self-check"] + info)
        draw_text_clipped(
            app,
            surface=surface,
            text=combined,
            rect=content_rect,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=999,
            use_device_font=False,
        )


# ── Quick-reference shortcuts panel (Ctrl+/) ──────────────────────────


_QUICKREF_SECTIONS = [
    (
        "Selection",
        [
            "LMB  select/drag",
            "Shift+click  range",
            "Ctrl+click  toggle",
            "Ctrl+A  all",
            "Ctrl+I  invert",
            "N/P  next/prev",
            "/  search",
        ],
    ),
    (
        "Edit",
        [
            "Ctrl+Z  undo",
            "Ctrl+Y  redo",
            "Ctrl+C/X/V  copy/cut/paste",
            "Ctrl+D  dup",
            "Del  delete",
            "R  rename",
            "E  smart edit",
        ],
    ),
    (
        "Layout",
        [
            "Arrows  nudge",
            "Ctrl+Arrow  1px",
            ";/' stack V/H",
            ". center",
            "F6/F7  row/col",
            "Ctrl+Alt+G  grid",
        ],
    ),
    (
        "Widgets",
        [
            "1-9  quick add",
            "T  cycle type",
            "S  style",
            "B  border",
            "Q  color",
            "L  lock",
            "V  show/hide",
        ],
    ),
    (
        "Scenes",
        [
            "Ctrl+N  new",
            "Ctrl+1-9  jump",
            "Ctrl+Tab  next",
            "Ctrl+S  save",
            "Ctrl+L  load",
            "Ctrl+E  export C",
        ],
    ),
    (
        "View",
        [
            "G  grid",
            "X  snap",
            "F1  help",
            "F4  zoom-fit",
            "Ctrl+0  reset zoom",
            "F9  preview",
            "F11  fullscreen",
        ],
    ),
]


def draw_shortcuts_panel(app) -> None:
    """Draw a compact categorized quick-reference (toggle via Ctrl+/)."""
    if not bool(getattr(app, "show_shortcuts_panel", False)):
        return
    surface = getattr(app, "logical_surface", None)
    if surface is None:
        return
    layout = getattr(app, "layout", None)
    if layout is None:
        return
    w = int(getattr(layout, "width", 0) or 0)
    h = int(getattr(layout, "height", 0) or 0)
    if w <= 0 or h <= 0:
        return

    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 140))
    surface.blit(dim, (0, 0))

    pad = max(2, int(getattr(app, "pixel_padding", 0) or 0))
    row_h = max(1, int(getattr(app, "pixel_row_height", 0) or 0))

    n_cols = len(_QUICKREF_SECTIONS)
    margin = GRID * 2
    panel_w = max(GRID * 18, min(w - margin * 2, GRID * 56))
    panel_w = max(GRID * 10, snap(panel_w))
    max_rows = max(len(items) for _, items in _QUICKREF_SECTIONS)
    panel_h = max(GRID * 8, min(h - margin * 2, row_h * (max_rows + 2) + pad * 2))
    panel_h = max(GRID * 6, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)

    draw_pixel_panel_bg(app, panel_rect)

    # Title
    title_rect = pygame.Rect(x + pad, y, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text="Quick Reference (Ctrl+/ = close)",
        rect=title_rect,
        fg=PALETTE["accent_yellow"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    col_w = max(1, (panel_w - pad * 2) // max(1, n_cols))
    body_y = y + row_h + pad

    for ci, (header, items) in enumerate(_QUICKREF_SECTIONS):
        cx = x + pad + ci * col_w
        header_rect = pygame.Rect(cx, body_y, col_w - pad, row_h)
        draw_text_clipped(
            app,
            surface=surface,
            text=header,
            rect=header_rect,
            fg=PALETTE["accent_cyan"],
            padding=0,
            align="left",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        for ri, item in enumerate(items):
            iy = body_y + row_h * (ri + 1)
            if iy + row_h > y + panel_h - pad:
                break
            item_rect = pygame.Rect(cx, iy, col_w - pad, row_h)
            draw_text_clipped(
                app,
                surface=surface,
                text=item,
                rect=item_rect,
                fg=PALETTE["text"],
                padding=0,
                align="left",
                valign="middle",
                max_lines=1,
                use_device_font=False,
            )
