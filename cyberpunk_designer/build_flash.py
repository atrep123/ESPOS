"""Build / Flash modal — drive the real PlatformIO toolchain from the designer.

This makes espos a one-app embedded workflow: the same window that designs the
UI can compile it for the selected board and flash it to hardware. It is a
*functional* surface, not a fake progress bar — it shells out to
``tools.build`` which runs the genuine ``python -m platformio run`` and streams
the real compiler output into this modal's scrollable log.

Pattern note: this mirrors ``icon_palette.py`` / ``template_manager.py`` /
``logic_editor.py`` exactly — a state dict on ``app._build_flash``;
``open/close/toggle/is_open``; ``handle_key/handle_click/handle_wheel`` wired
modal-first from the key/mouse handlers; ``draw_build_flash`` in the overlay
draw order. The pio work runs on a worker thread so the UI is not hard-frozen
(a real subprocess + thread, not an invented framework — output is pumped to a
thread-safe line buffer the draw loop reads).

Build  = regenerate codegen for the current design + compile the active
         board's firmware.
Flash  = the above, then the real ``-t upload`` (UNVERIFIED-ON-HARDWARE when
         no board is attached — see tools/build.py).
"""

from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional, Tuple

import pygame

from .constants import GRID, PALETTE, snap

# `draw_text_clipped` is imported lazily inside `draw_build_flash` for the same
# reason icon_palette does it: importing `.drawing.text` at module load pulls
# in `.drawing/__init__` -> `.drawing.frame` -> back here (circular).

_MAX_LOG_LINES = 600  # ring-buffer cap; pio output can be long


def _state(app) -> dict:
    st = getattr(app, "_build_flash", None)
    if not isinstance(st, dict):
        st = {
            "visible": False,
            "running": False,
            "action": "",          # "build" | "flash"
            "lines": deque(maxlen=_MAX_LOG_LINES),  # ring buffer of pio output
            "scroll": 0,           # rows scrolled up from the bottom
            "follow": True,        # auto-stick to tail while running
            "thread": None,
            "result": None,        # str summary once finished
            "lock": threading.Lock(),
            "rows": 1,
        }
        app._build_flash = st
    return st


def _append(app, line: str) -> None:
    """Thread-safe append from the pio worker (the sink callback)."""
    st = _state(app)
    with st["lock"]:
        st["lines"].append(str(line))
    # Best-effort repaint request; _mark_dirty is cheap and thread-tolerant.
    try:
        app._mark_dirty()
    except Exception:  # pragma: no cover - defensive (never crash the worker)
        pass


def _active_board(app) -> Optional[str]:
    """The board id the designer currently targets (None -> reference env)."""
    bid = getattr(app, "active_board", None)
    return str(bid) if bid else None


# --------------------------------------------------------------------------- #
# Public API used by app / handlers
# --------------------------------------------------------------------------- #


def is_open(app) -> bool:
    return bool(_state(app).get("visible"))


def close_build_flash(app) -> None:
    st = _state(app)
    if st.get("visible"):
        st["visible"] = False
        app._mark_dirty()


def open_build_flash(app) -> None:
    """Show the Build/Flash modal (does not start anything yet)."""
    st = _state(app)
    st["visible"] = True
    if not st.get("running"):
        st["scroll"] = 0
        st["follow"] = True
    board = _active_board(app) or "reference (esp32-s3-devkitm-1-nohw)"
    app._set_status(
        f"Build/Flash [{board}] — B = build, F = flash, Esc = close",
        ttl_sec=4.0,
    )
    app._mark_dirty()


def toggle_build_flash(app) -> None:
    if is_open(app):
        close_build_flash(app)
    else:
        open_build_flash(app)


def _worker(app, action: str) -> None:
    """Run the real pio build/flash on a worker thread, streaming to the log."""
    st = _state(app)

    def sink(line: str) -> None:
        _append(app, line)

    try:
        from tools.build import BuildError, build_board, flash_board

        if action == "flash":
            res = flash_board(_active_board(app), sink=sink)
        else:
            res = build_board(_active_board(app), sink=sink)
        summary = res.summary()
    except BuildError as exc:  # actionable setup failure (missing pio, etc.)
        summary = f"{action.upper()} ERROR: {exc}"
        _append(app, summary)
    except Exception as exc:  # pragma: no cover - last-resort guard
        summary = f"{action.upper()} CRASHED: {exc!r}"
        _append(app, summary)
    finally:
        st["running"] = False
        st["result"] = summary
        try:
            app._set_status(summary.splitlines()[0], ttl_sec=6.0)
            app._mark_dirty()
        except Exception:  # pragma: no cover
            pass


def start(app, action: str) -> None:
    """Kick off a build or flash on a background thread (idempotent)."""
    st = _state(app)
    if st.get("running"):
        app._set_status("Build/Flash already running.", ttl_sec=2.0)
        return
    st["visible"] = True
    st["running"] = True
    st["action"] = action
    st["result"] = None
    st["scroll"] = 0
    st["follow"] = True
    with st["lock"]:
        st["lines"].clear()
        board = _active_board(app) or "esp32-s3-devkitm-1-nohw (reference)"
        st["lines"].append(f"=== {action.upper()} :: board {board} ===")
    th = threading.Thread(
        target=_worker, args=(app, action), name=f"espos-{action}", daemon=True
    )
    st["thread"] = th
    th.start()
    app._set_status(f"{action.capitalize()} started…", ttl_sec=2.5)
    app._mark_dirty()


def start_build(app) -> None:
    start(app, "build")


def start_flash(app) -> None:
    start(app, "flash")


def _snapshot(app) -> List[str]:
    st = _state(app)
    with st["lock"]:
        return list(st["lines"])


def handle_key(app, event: pygame.event.Event) -> bool:
    """Consume keys while the modal is open (modal-first, like icon_palette)."""
    st = _state(app)
    if not st.get("visible"):
        return False

    key = event.key
    if key == pygame.K_ESCAPE:
        close_build_flash(app)
        return True
    if key in (pygame.K_b,) and not st.get("running"):
        start_build(app)
        return True
    if key in (pygame.K_f,) and not st.get("running"):
        start_flash(app)
        return True

    rows = max(1, int(st.get("rows", 1)))
    total = len(_snapshot(app))
    if key == pygame.K_UP:
        st["follow"] = False
        st["scroll"] = min(max(0, total - 1), int(st.get("scroll", 0)) + 1)
        app._mark_dirty()
        return True
    if key == pygame.K_DOWN:
        st["scroll"] = max(0, int(st.get("scroll", 0)) - 1)
        if st["scroll"] == 0:
            st["follow"] = True
        app._mark_dirty()
        return True
    if key == pygame.K_PAGEUP:
        st["follow"] = False
        st["scroll"] = min(max(0, total - 1), int(st.get("scroll", 0)) + rows)
        app._mark_dirty()
        return True
    if key == pygame.K_PAGEDOWN:
        st["scroll"] = max(0, int(st.get("scroll", 0)) - rows)
        if st["scroll"] == 0:
            st["follow"] = True
        app._mark_dirty()
        return True
    if key == pygame.K_END:
        st["scroll"] = 0
        st["follow"] = True
        app._mark_dirty()
        return True
    if key == pygame.K_HOME:
        st["follow"] = False
        st["scroll"] = max(0, total - 1)
        app._mark_dirty()
        return True

    # Modal: swallow everything else so global shortcuts don't fire underneath.
    return True


def handle_click(app, pos: Tuple[int, int]) -> bool:
    """Consume a click while open: action buttons, or dismiss outside."""
    st = _state(app)
    if not st.get("visible"):
        return False
    for rect, key in st.get("hitboxes", []):
        if rect.collidepoint(pos[0], pos[1]):
            if key == "build" and not st.get("running"):
                start_build(app)
            elif key == "flash" and not st.get("running"):
                start_flash(app)
            elif key == "close":
                close_build_flash(app)
            return True
    # Click outside the panel dismisses (matches the other modals).
    panel = st.get("panel_rect")
    if panel is not None and not panel.collidepoint(pos[0], pos[1]):
        close_build_flash(app)
    return True


def handle_wheel(app, dy: int) -> bool:
    st = _state(app)
    if not st.get("visible"):
        return False
    total = len(_snapshot(app))
    if dy > 0:  # wheel up -> scroll back in history
        st["follow"] = False
        st["scroll"] = min(max(0, total - 1), int(st.get("scroll", 0)) + dy * 2)
    else:
        st["scroll"] = max(0, int(st.get("scroll", 0)) + dy * 2)
        if st["scroll"] == 0:
            st["follow"] = True
    app._mark_dirty()
    return True


# --------------------------------------------------------------------------- #
# Rendering — modeled on icon_palette.draw_icon_palette
# --------------------------------------------------------------------------- #


def draw_build_flash(app) -> None:
    """Draw the Build/Flash modal overlay if open."""
    st = _state(app)
    if not st.get("visible"):
        return
    from .drawing.text import draw_text_clipped  # lazy: breaks import cycle

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
    panel_w = max(GRID * 24, min(w - margin * 2, GRID * 70))
    panel_h = max(GRID * 16, min(h - margin * 2, GRID * 46))
    panel_w = max(GRID * 16, snap(panel_w))
    panel_h = max(GRID * 14, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)
    st["panel_rect"] = panel_rect

    pygame.draw.rect(surface, PALETTE["panel"], panel_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], panel_rect, 1)

    board = _active_board(app) or "esp32-s3-devkitm-1-nohw (reference)"
    running = bool(st.get("running"))
    action = str(st.get("action") or "")
    status = (
        f"running {action}…"
        if running
        else (str(st.get("result") or "idle"))
    )

    # Title row.
    title_rect = pygame.Rect(x + pad, y + pad, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"Build / Flash  —  board: {board}",
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
        text="Esc=close",
        rect=title_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    # Action buttons row (Build / Flash / Close) — real hitboxes.
    btn_y = y + pad + row_h
    btn_w = max(GRID * 6, (panel_w - 2 * pad - GRID * 2) // 3)
    hitboxes: List[Tuple[pygame.Rect, str]] = []
    specs = [
        ("build", "Build", not running),
        ("flash", "Flash", not running),
        ("close", "Close", True),
    ]
    bx = x + pad
    for key, label, enabled in specs:
        r = pygame.Rect(bx, btn_y, btn_w, row_h)
        bg = PALETTE["bg"] if enabled else PALETTE["panel"]
        pygame.draw.rect(surface, bg, r)
        pygame.draw.rect(surface, PALETTE["panel_border"], r, 1)
        draw_text_clipped(
            app,
            surface=surface,
            text=label,
            rect=r,
            fg=PALETTE["text"] if enabled else PALETTE["muted"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        hitboxes.append((r, key))
        bx += btn_w + GRID
    st["hitboxes"] = hitboxes

    # Status line.
    stat_rect = pygame.Rect(x + pad, btn_y + row_h, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text=status,
        rect=stat_rect,
        fg=PALETTE["accent_cyan"] if running else PALETTE["text"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    # Log area (the real pio output).
    log_top = btn_y + row_h * 2 + pad
    log_rect = pygame.Rect(
        x + pad,
        log_top,
        panel_w - 2 * pad,
        (y + panel_h - pad) - log_top,
    )
    if log_rect.width <= 0 or log_rect.height <= 0:
        return
    pygame.draw.rect(surface, PALETTE["bg"], log_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], log_rect, 1)

    line_h = max(8, row_h // 2)
    rows = max(1, (log_rect.height - 2 * pad) // line_h)
    st["rows"] = rows

    lines = _snapshot(app)
    total = len(lines)
    if st.get("follow") and running:
        st["scroll"] = 0
    scroll = max(0, min(int(st.get("scroll", 0)), max(0, total - 1)))
    # Bottom-anchored: last visible line = total-1-scroll.
    end = total - scroll
    start_i = max(0, end - rows)
    visible = lines[start_i:end]

    ty = log_rect.y + pad
    for ln in visible:
        low = ln.lower()
        if "success" in low:
            fg = PALETTE.get("accent_green", PALETTE["accent_cyan"])
        elif "fail" in low or "error" in low or "crashed" in low:
            fg = PALETTE.get("accent_red", PALETTE["accent_yellow"])
        elif ln.startswith("$") or ln.startswith("[") or ln.startswith("==="):
            fg = PALETTE["accent_yellow"]
        else:
            fg = PALETTE["text"]
        draw_text_clipped(
            app,
            surface=surface,
            text=ln,
            rect=pygame.Rect(log_rect.x + pad, ty, log_rect.width - 2 * pad, line_h),
            fg=fg,
            padding=0,
            align="left",
            valign="middle",
            max_lines=1,
            use_device_font=False,
        )
        ty += line_h

    # Footer: scrollback position + hint.
    foot_rect = pygame.Rect(x + pad, y + panel_h - row_h, panel_w - 2 * pad, row_h)
    pos_txt = (
        f"tail (live)  {total} lines"
        if scroll == 0
        else f"-{scroll} / {total} lines  (End=jump to tail)"
    )
    draw_text_clipped(
        app,
        surface=surface,
        text=pos_txt,
        rect=foot_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )
    draw_text_clipped(
        app,
        surface=surface,
        text="B=build  F=flash  PgUp/PgDn=scroll",
        rect=foot_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )
