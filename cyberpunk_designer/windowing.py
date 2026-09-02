"""Window management: zoom, pan, resize, hit-testing."""

from __future__ import annotations

from typing import Optional, Tuple

import pygame

from .constants import GRID, PALETTE, SCALE, snap
from .layout import Layout


def screen_to_logical(app, x: int, y: int) -> Tuple[int, int]:
    """Convert physical window coordinates to logical (1:1 editor) coordinates."""
    sx = app._render_scale_x if app._render_scale_x > 0 else 1.0
    sy = app._render_scale_y if app._render_scale_y > 0 else 1.0
    ox = app._render_offset_x
    oy = app._render_offset_y
    lx = int((x - ox) / sx)
    ly = int((y - oy) / sy)
    return lx, ly


def _base_layout_size(app, palette_w: int, inspector_w: int) -> Tuple[int, int]:
    """Return minimum (width,height) needed for the editor UI at 1:1 logical scale."""
    canvas_w = int(getattr(app.designer, "width", 0) or 0)
    canvas_h = int(getattr(app.designer, "height", 0) or 0)
    base_w = max(1, canvas_w + int(palette_w) + int(inspector_w))
    base_h = max(
        1,
        canvas_h
        + int(getattr(app, "toolbar_h", 0) or 0)
        + int(getattr(app, "scene_tabs_h", 0) or 0)
        + int(getattr(app, "status_h", 0) or 0),
    )
    return base_w, base_h


def _fit_scale(app, max_w: int, max_h: int, base_w: int, base_h: int) -> int:
    """Compute best-effort integer scale that fits base editor UI into (max_w,max_h)."""
    max_w = max(1, int(max_w))
    max_h = max(1, int(max_h))
    base_w = max(1, int(base_w))
    base_h = max(1, int(base_h))
    fit_w = max_w // base_w
    fit_h = max_h // base_h
    return max(1, min(int(getattr(app, "max_auto_scale", 4) or 4), fit_w, fit_h))


def hardware_accelerated_scale(app) -> None:
    """Use hardware acceleration for scaling if available."""
    win_w, win_h = app.window.get_size()
    render_scale = max(1, min(app.scale, app.max_auto_scale))

    # Check window bounds
    max_scale_w = max(1, win_w // max(1, app.layout.width))
    max_scale_h = max(1, win_h // max(1, app.layout.height))
    render_scale = min(render_scale, max_scale_w, max_scale_h)

    scaled_w = app.layout.width * render_scale
    scaled_h = app.layout.height * render_scale
    app._render_scale_x = float(render_scale)
    app._render_scale_y = float(render_scale)

    # Try hardware accelerated scaling
    try:
        # Use SDL2 hardware acceleration if available
        scaled = pygame.transform.scale(app.logical_surface, (scaled_w, scaled_h))
    except pygame.error:
        # Fallback to software scaling
        scaled = pygame.transform.scale(app.logical_surface, (scaled_w, scaled_h))

    # Center in window
    offset_x = max(0, (win_w - scaled_w) // 2)
    offset_y = max(0, (win_h - scaled_h) // 2)
    app._render_offset_x = offset_x
    app._render_offset_y = offset_y

    app.window.fill(PALETTE["bg"])
    app.window.blit(scaled, (offset_x, offset_y))


def handle_video_resize(app, win_w: int, win_h: int) -> None:
    """Respond to a window resize event by recalculating layout and scale."""
    lock = None
    try:
        if bool(getattr(app, "_scale_locked", False)):
            lock = int(getattr(app, "scale", 1) or 1)
    except (TypeError, ValueError):
        lock = None
    rebuild_layout(app, window_size=(win_w, win_h), force_scene_size=False, lock_scale=lock)


def toggle_fullscreen(app) -> None:
    """Toggle fullscreen."""
    app.fullscreen = not app.fullscreen
    if app.fullscreen:
        info = pygame.display.Info()
        win_w, win_h = (
            int(getattr(info, "current_w", 0) or 0),
            int(getattr(info, "current_h", 0) or 0),
        )
        if win_w <= 0 or win_h <= 0:
            win_w, win_h = app.window.get_size()
    else:
        # Restore to a reasonable windowed size based on current layout/scale.
        base_w, base_h = _base_layout_size(app, app._default_palette_w, app._default_inspector_w)
        scale = max(
            1,
            min(
                int(getattr(app, "scale", SCALE) or SCALE),
                int(getattr(app, "max_auto_scale", 4) or 4),
            ),
        )
        win_w, win_h = base_w * scale, base_h * scale

    lock = None
    try:
        if bool(getattr(app, "_scale_locked", False)):
            lock = int(getattr(app, "scale", 1) or 1)
    except (TypeError, ValueError):
        lock = None
    rebuild_layout(
        app, window_size=(int(win_w), int(win_h)), force_scene_size=False, lock_scale=lock
    )


def compute_scale(app, force_window: Optional[Tuple[int, int]] = None) -> int:
    """Compute the best integer scale factor to fit the editor in the window."""
    palette_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_palette_w", 0)
    )
    inspector_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_inspector_w", 0)
    )
    base_w, base_h = _base_layout_size(app, int(palette_w), int(inspector_w))
    margin_w, margin_h = 24, 64
    if force_window:
        max_w, max_h = force_window
    else:
        info = pygame.display.Info()
        max_w = max(1, info.current_w - margin_w)
        max_h = max(1, info.current_h - margin_h)
    return _fit_scale(app, max_w, max_h, base_w, base_h)


def set_scale(app, new_scale: int) -> None:
    """Set the editor zoom level and rebuild layout to match."""
    app.scale = max(1, min(new_scale, app.max_auto_scale))
    try:
        win_size = app.window.get_size() if app.window is not None else None
    except (AttributeError, pygame.error):
        win_size = None
    if win_size:
        rebuild_layout(app, window_size=win_size, force_scene_size=False, lock_scale=app.scale)
        return
    app._mark_dirty()


def recompute_scale_for_window(app, win_w: int, win_h: int) -> None:
    """Recalculate `app.scale` to fit the current base layout in a *win_w* x *win_h* window."""
    palette_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_palette_w", 0)
    )
    inspector_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_inspector_w", 0)
    )
    base_w, base_h = _base_layout_size(app, int(palette_w), int(inspector_w))
    app.scale = _fit_scale(app, int(win_w), int(win_h), base_w, base_h)


# Nejmensi rozumny vyrez platna: pod tim uz editor nema co ukazovat a
# canvas_rect by mel zapornou sirku.
MIN_CANVAS_W = 4 * GRID
MIN_CANVAS_H = 4 * GRID


def _min_layout_w(palette_w: int, inspector_w: int) -> int:
    """Nejmensi logicka sirka, ktera necha platnu aspon MIN_CANVAS_W."""
    return int(palette_w) + int(inspector_w) + MIN_CANVAS_W


def _min_layout_h(toolbar_h: int, scene_tabs_h: int, status_h: int) -> int:
    """Nejmensi logicka vyska, ktera necha platnu aspon MIN_CANVAS_H."""
    return int(toolbar_h) + int(scene_tabs_h) + int(status_h) + MIN_CANVAS_H


# --------------------------------------------------------------------------- #
# Posouvani platna (pan)
# --------------------------------------------------------------------------- #
# Editor umi jen CELE meritko >= 1 (_fit_scale) a scenu vetsi nez vyrez do
# ted proste ORIZNUL (drawing/canvas.py) - cast navrhu byla nedostupna.
# Scena 1280x720 (Tab5) se do editoru nevejde ani na monitoru 1920x1080,
# protoze si paleta, inspektor a listy vezmou svoje; bez posouvani by se
# pravy a dolni okraj navrhu nedal editovat vubec.
#
# Posun je ulozeny v app.pan_x / app.pan_y v PIXELECH SCENY a plati jedine
# tehdy, kdyz je scena vetsi nez viditelny vyrez. Kdyz se scena vejde, jsou
# meze nulove, pan je vzdy 0 a chovani editoru se nezmeni ani o pixel.


def _scene_size(app) -> Tuple[int, int]:
    """Rozmer aktualni sceny v pixelech zarizeni."""
    des = getattr(app, "designer", None)
    try:
        w = int(getattr(des, "width", 0) or 0)
        h = int(getattr(des, "height", 0) or 0)
    except (TypeError, ValueError):
        w, h = 0, 0
    try:
        st = getattr(app, "state", None)
        if st is not None:
            sc = st.current_scene()
            w = int(getattr(sc, "width", w) or w)
            h = int(getattr(sc, "height", h) or h)
    except (AttributeError, TypeError, ValueError):
        pass
    return max(1, w), max(1, h)


def _viewport(app) -> pygame.Rect:
    """Viditelny vyrez sceny na platne (scene_rect, nouzove canvas_rect)."""
    sr = getattr(app, "scene_rect", None)
    if not isinstance(sr, pygame.Rect):
        sr = getattr(getattr(app, "layout", None), "canvas_rect", None)
    if not isinstance(sr, pygame.Rect):
        return pygame.Rect(0, 0, 1, 1)
    return sr


def pan_limits(app) -> Tuple[int, int]:
    """Nejvetsi pripustny posun vodorovne a svisle; (0, 0) = scena se vejde."""
    scene_w, scene_h = _scene_size(app)
    vp = _viewport(app)
    return (
        max(0, scene_w - max(1, int(vp.width))),
        max(0, scene_h - max(1, int(vp.height))),
    )


def clamp_pan(app) -> None:
    """Orizne pan do platneho rozsahu. Volat po kazde zmene layoutu nebo sceny."""
    max_x, max_y = pan_limits(app)
    try:
        px = int(getattr(app, "pan_x", 0) or 0)
        py = int(getattr(app, "pan_y", 0) or 0)
    except (TypeError, ValueError):
        px, py = 0, 0
    app.pan_x = max(0, min(max_x, px))
    app.pan_y = max(0, min(max_y, py))


def scene_origin(app) -> pygame.Rect:
    """Rect, jehoz levy horni roh je pocatek souradnic sceny na platne.

    Rozmery ma stejne jako viditelny vyrez, jen je posunuty o pan. KAZDE
    misto, ktere prevadi mezi souradnicemi platna a sceny (kresleni, trefeni
    prvku, tazeni, vlozeni na pozici kurzoru), musi pouzit tenhle rect, ne
    scene_rect - jinak se po posunu rozejde mys s obrazem.
    Pri nulovem posunu vraci presne scene_rect.
    """
    vp = _viewport(app)
    try:
        px = int(getattr(app, "pan_x", 0) or 0)
        py = int(getattr(app, "pan_y", 0) or 0)
    except (TypeError, ValueError):
        px, py = 0, 0
    return pygame.Rect(int(vp.x) - px, int(vp.y) - py, int(vp.width), int(vp.height))


def pan_by(app, dx: int, dy: int) -> bool:
    """Posune platno o (dx, dy) pixelu sceny. Vraci True, kdyz se pan zmenil."""
    max_x, max_y = pan_limits(app)
    if max_x <= 0 and max_y <= 0:
        return False
    try:
        px = int(getattr(app, "pan_x", 0) or 0)
        py = int(getattr(app, "pan_y", 0) or 0)
        ddx, ddy = int(dx), int(dy)
    except (TypeError, ValueError):
        return False
    new_x = max(0, min(max_x, px + ddx))
    new_y = max(0, min(max_y, py + ddy))
    if (new_x, new_y) == (px, py):
        return False
    app.pan_x = new_x
    app.pan_y = new_y
    try:
        app._mark_dirty()
    except AttributeError:
        pass
    return True


def reset_pan(app) -> bool:
    """Vrati platno na levy horni roh sceny. Vraci True, kdyz se neco zmenilo."""
    try:
        changed = bool(getattr(app, "pan_x", 0) or getattr(app, "pan_y", 0))
    except (TypeError, ValueError):
        changed = True
    app.pan_x = 0
    app.pan_y = 0
    if changed:
        try:
            app._mark_dirty()
        except AttributeError:
            pass
    return changed


def pan_drag_start(app, pos: Tuple[int, int]) -> bool:
    """Zahaji tazeni platna strednim tlacitkem. Vraci True, kdyz se zacalo."""
    cr = getattr(getattr(app, "layout", None), "canvas_rect", None)
    if not isinstance(cr, pygame.Rect) or not cr.collidepoint(pos):
        return False
    max_x, max_y = pan_limits(app)
    if max_x <= 0 and max_y <= 0:
        return False
    app._pan_drag_from = (int(pos[0]), int(pos[1]))
    return True


def pan_drag_move(app, pos: Tuple[int, int]) -> bool:
    """Pokracuje v tazeni platna. Vraci True, kdyz se pan zmenil."""
    src = getattr(app, "_pan_drag_from", None)
    if not src:
        return False
    # Tazeni "chytne" platno: kurzor doprava = obsah doprava = mensi pan.
    dx = int(src[0]) - int(pos[0])
    dy = int(src[1]) - int(pos[1])
    app._pan_drag_from = (int(pos[0]), int(pos[1]))
    return pan_by(app, dx, dy)


def pan_drag_end(app) -> None:
    """Ukonci tazeni platna."""
    app._pan_drag_from = None


def rebuild_layout(
    app,
    window_size: Optional[Tuple[int, int]] = None,
    force_scene_size: bool = True,
    lock_scale: Optional[int] = None,
) -> None:
    """Rebuild UI layout."""
    palette_w = (
        0
        if getattr(app, "panels_collapsed", False)
        else int(getattr(app, "_default_palette_w", 0) or 0)
    )
    inspector_w = (
        0
        if getattr(app, "panels_collapsed", False)
        else int(getattr(app, "_default_inspector_w", 0) or 0)
    )

    base_w, base_h = _base_layout_size(app, palette_w, inspector_w)

    if window_size:
        win_w, win_h = int(window_size[0]), int(window_size[1])
        fit = _fit_scale(app, win_w, win_h, base_w, base_h)
        if lock_scale is not None:
            app.scale = max(1, min(int(lock_scale), fit))
        else:
            app.scale = fit
        flags = pygame.FULLSCREEN if getattr(app, "fullscreen", False) else pygame.RESIZABLE
        app.window = pygame.display.set_mode((max(1, win_w), max(1, win_h)), flags)
    else:
        app.scale = compute_scale(app)
        win_w, win_h = base_w * app.scale, base_h * app.scale
        app.window = pygame.display.set_mode((max(1, win_w), max(1, win_h)), pygame.RESIZABLE)

    # Expand logical layout to fill the available window at the chosen integer scale.
    # This removes most of the "black margins" when maximizing the window for small (e.g. 256x128) scenes.
    #
    # A ZAROVEN ho zmensi, kdyz je okno mensi nez base. Drive tu bylo
    # max(base_w, ...), takze logicka plocha nikdy neklesla pod velikost
    # sceny - u sceny 1280x720 tedy vzdy aspon 1600x776. Pri mensim okne se
    # prebytek proste NEVYKRESLIL: hardware_accelerated_scale blitne plochu
    # do leveho horniho rohu a co presahne, je mimo okno. Nesel videt ani
    # kliknout a nesla na nej ani posunout scena, protoze vyrez platna byl
    # porad "cely". Omezenim na to, co se do okna vejde, se vyrez skutecne
    # zmensi - a teprve tim dostane posouvani platna smysl.
    avail_w = max(1, win_w) // max(1, app.scale)
    avail_h = max(1, win_h) // max(1, app.scale)
    layout_w = max(_min_layout_w(palette_w, inspector_w), avail_w)
    layout_h = max(
        _min_layout_h(
            int(getattr(app, "toolbar_h", 24) or 24),
            int(getattr(app, "scene_tabs_h", 0) or 0),
            int(getattr(app, "status_h", 18) or 18),
        ),
        avail_h,
    )

    app.layout = Layout(
        layout_w,
        layout_h,
        palette_w=palette_w,
        inspector_w=inspector_w,
        toolbar_h=int(getattr(app, "toolbar_h", 24) or 24),
        status_h=int(getattr(app, "status_h", 18) or 18),
        scene_tabs_h=int(getattr(app, "scene_tabs_h", 0) or 0),
    )
    app.logical_surface = pygame.Surface((app.layout.width, app.layout.height))

    # Cache a centered "device viewport" rect inside the (potentially larger) canvas.
    # This keeps the artboard centered when the window is maximized while preserving
    # scene coordinates (widgets remain relative to 0,0 of the device).
    try:
        cr = app.layout.canvas_rect
        scene_w = int(getattr(getattr(app, "designer", None), "width", 0) or 0)
        scene_h = int(getattr(getattr(app, "designer", None), "height", 0) or 0)
        try:
            if getattr(app, "state", None) is not None:
                sc = app.state.current_scene()
                scene_w = int(getattr(sc, "width", scene_w) or scene_w)
                scene_h = int(getattr(sc, "height", scene_h) or scene_h)
        except (AttributeError, TypeError, ValueError):
            pass
        scene_w = max(1, int(scene_w))
        scene_h = max(1, int(scene_h))
        view_w = max(1, int(getattr(cr, "width", 1) or 1))
        view_h = max(1, int(getattr(cr, "height", 1) or 1))
        w = max(1, min(scene_w, view_w))
        h = max(1, min(scene_h, view_h))
        x = int(cr.x) + int((view_w - scene_w) // 2) if scene_w <= view_w else int(cr.x)
        y = int(cr.y) + int((view_h - scene_h) // 2) if scene_h <= view_h else int(cr.y)
        x = snap(int(x), GRID)
        y = snap(int(y), GRID)
        x = max(int(cr.x), min(int(cr.right) - w, int(x)))
        y = max(int(cr.y), min(int(cr.bottom) - h, int(y)))
        app.scene_rect = pygame.Rect(int(x), int(y), int(w), int(h))
    except (AttributeError, TypeError, ValueError):
        app.scene_rect = app.layout.canvas_rect

    # Vyrez se zmenil - posun musi zustat v mezich, jinak by po zvetseni okna
    # zbyl pan ukazujici za konec sceny.
    clamp_pan(app)

    try:
        if getattr(app, "state", None) is not None:
            app.state.layout = app.layout
    except AttributeError:
        pass

    try:
        app._mark_dirty()
    except AttributeError:
        pass

    del force_scene_size, lock_scale
