from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from ui_designer import WidgetConfig

from .. import font6x8, text_metrics
from .primitives import render_pixel_text


def text_width_px(app, text: str) -> int:
    try:
        return int(app.pixel_font.size(str(text or ""))[0])
    except Exception:
        return 0


def ellipsize_text_px(app, text: str, max_width_px: int, ellipsis: str = "...") -> str:
    s = str(text or "")
    max_width_px = int(max_width_px)
    if max_width_px <= 0 or not s:
        return ""
    if text_width_px(app, s) <= max_width_px:
        return s
    if text_width_px(app, ellipsis) > max_width_px:
        out = ""
        for ch in s:
            if text_width_px(app, out + ch) <= max_width_px:
                out += ch
            else:
                break
        return out

    lo = 0
    hi = len(s)
    while lo < hi:
        mid = (lo + hi) // 2
        candidate = s[:mid] + ellipsis
        if text_width_px(app, candidate) <= max_width_px:
            lo = mid + 1
        else:
            hi = mid
    cut = max(0, lo - 1)
    return s[:cut] + ellipsis


def wrap_text_px(app, text: str, max_width_px: int, max_lines: int, ellipsis: str = "...") -> List[str]:
    s = str(text or "").replace("\t", " ").strip()
    max_width_px = int(max_width_px)
    max_lines = max(1, int(max_lines))
    if not s or max_width_px <= 0:
        return []
    if max_lines == 1:
        return [ellipsize_text_px(app, s, max_width_px, ellipsis=ellipsis)]

    paras = [p.strip() for p in s.splitlines() if p.strip()]

    lines: List[str] = []
    truncated = False

    for pi, para in enumerate(paras):
        words = para.split()
        current = ""
        for wi, word in enumerate(words):
            cand = word if not current else f"{current} {word}"
            if text_width_px(app, cand) <= max_width_px:
                current = cand
                continue
            if current:
                lines.append(current)
                if len(lines) >= max_lines:
                    # 'word' didn't fit on this line → text remains
                    truncated = True
                    break
                current = word
                continue

            chunk = ""
            for ch in word:
                cand2 = chunk + ch
                if text_width_px(app, cand2) <= max_width_px:
                    chunk = cand2
                else:
                    if chunk:
                        lines.append(chunk)
                        if len(lines) >= max_lines:
                            truncated = True
                            break
                    chunk = ch if text_width_px(app, ch) <= max_width_px else ""
            if len(lines) >= max_lines:
                break
            current = chunk

        if len(lines) >= max_lines:
            break
        if current:
            lines.append(current)
        if len(lines) >= max_lines:
            truncated = pi < len(paras) - 1
            break

    if truncated and lines:
        last = lines[-1]
        # Force ellipsis: if the line already fits, append a dummy char
        # so ellipsize_text_px will truncate and add the ellipsis marker.
        if text_width_px(app, last) <= max_width_px:
            last = last + " …"
        lines[-1] = ellipsize_text_px(app, last, max_width_px, ellipsis=ellipsis)
    return lines[:max_lines]


def draw_text_clipped(
    app,
    surface: pygame.Surface,
    text: str,
    rect: pygame.Rect,
    fg: Tuple[int, int, int],
    padding: int,
    align: str = "left",
    valign: str = "middle",
    max_lines: int = 1,
    ellipsis: str = "...",
    use_device_font: Optional[bool] = None,
) -> None:
    s = str(text or "")
    if not s:
        return
    padding = max(0, int(padding))
    clip_rect = rect.inflate(-padding * 2, -padding * 2)
    if clip_rect.width <= 0 or clip_rect.height <= 0:
        return
    if use_device_font is None:
        use_device = text_metrics.is_device_profile(getattr(app, "hardware_profile", None))
    else:
        use_device = bool(use_device_font)

    if use_device:
        line_h = max(1, int(font6x8.CHAR_H))
        max_chars = int(clip_rect.width) // max(1, int(font6x8.CHAR_W))
        if max_chars <= 0:
            return
        max_lines = max(1, int(max_lines))
        max_lines = min(max_lines, max(1, clip_rect.height // line_h))
        if max_lines > 1:
            lines, _trunc = text_metrics.wrap_text_chars(s, max_chars=max_chars, max_lines=max_lines, ellipsis=ellipsis)
        else:
            flat = " ".join(s.replace("\t", " ").replace("\r", "").replace("\n", " ").split())
            lines = [text_metrics.ellipsize_chars(flat, max_chars=max_chars, ellipsis=ellipsis)]
    else:
        line_h = max(1, int(app.pixel_font.get_height()))
        max_lines = max(1, int(max_lines))
        max_lines = min(max_lines, max(1, clip_rect.height // line_h))
        if max_lines > 1:
            lines = wrap_text_px(app, s, clip_rect.width, max_lines=max_lines, ellipsis=ellipsis)
        else:
            lines = [ellipsize_text_px(app, s, clip_rect.width, ellipsis=ellipsis)]
    if not lines:
        return

    total_h = len(lines) * line_h
    v = str(valign or "middle").lower()
    if v == "top":
        start_y = clip_rect.y
    elif v == "bottom":
        start_y = clip_rect.bottom - total_h
    else:
        start_y = clip_rect.centery - total_h // 2

    a = str(align or "left").lower()
    old_clip = surface.get_clip()
    # Intersect with any existing clip (palette/inspector/canvas) to avoid drawing outside panels.
    try:
        new_clip = clip_rect.clip(old_clip) if old_clip is not None else clip_rect
    except Exception:
        new_clip = clip_rect
    surface.set_clip(new_clip)
    try:
        y = start_y
        for line in lines:
            if use_device:
                txt = font6x8.render_text(line, fg)
            else:
                fitted = ellipsize_text_px(app, line, clip_rect.width, ellipsis=ellipsis)
                txt = render_pixel_text(app, fitted, fg)
            if a == "center":
                x = clip_rect.centerx - txt.get_width() // 2
            elif a == "right":
                x = clip_rect.right - txt.get_width()
            else:
                x = clip_rect.x
            surface.blit(txt, (x, y))
            y += line_h
    finally:
        surface.set_clip(old_clip)


def draw_text_in_rect(
    app,
    surface: pygame.Surface,
    text: str,
    rect: pygame.Rect,
    fg: Tuple[int, int, int],
    padding: int,
    w: WidgetConfig,
) -> None:
    align = str(getattr(w, "align", "left") or "left").lower()
    valign = str(getattr(w, "valign", "middle") or "middle").lower()
    line_h = max(1, int(app.pixel_font.get_height()))
    use_device = text_metrics.is_device_profile(getattr(app, "hardware_profile", None))
    overflow = str(getattr(w, "text_overflow", "ellipsis") or "ellipsis").strip().lower()
    if overflow not in {"ellipsis", "wrap", "clip", "auto"}:
        overflow = "ellipsis"

    use_wrap = overflow == "wrap"
    if overflow == "auto":
        raw = str(text or "")
        flat = raw.replace("\t", " ").replace("\n", " ").strip()
        clip_rect = rect.inflate(-max(0, int(padding)) * 2, -max(0, int(padding)) * 2)
        if use_device:
            max_chars = max(1, int(clip_rect.width) // max(1, int(text_metrics.DEVICE_CHAR_W)))
            use_wrap = clip_rect.height >= int(text_metrics.DEVICE_CHAR_H) * 2 and (("\n" in raw) or (len(flat) > max_chars))
        else:
            use_wrap = clip_rect.height >= line_h * 2 and (("\n" in raw) or (text_width_px(app, flat) > clip_rect.width))

    if use_wrap:
        clip_rect = rect.inflate(-max(0, int(padding)) * 2, -max(0, int(padding)) * 2)
        if use_device:
            max_lines = max(1, int(clip_rect.height) // max(1, int(text_metrics.DEVICE_CHAR_H)))
        else:
            max_lines = max(1, int(clip_rect.height) // line_h)
        try:
            ml = getattr(w, "max_lines", None)
            if ml is not None and str(ml) != "":
                ml_i = int(ml)
                if ml_i > 0:
                    max_lines = min(max_lines, ml_i)
        except Exception:
            pass
    else:
        max_lines = 1

    ell = "" if overflow == "clip" else "..."
    draw_text_clipped(
        app,
        surface=surface,
        text=text,
        rect=rect,
        fg=fg,
        padding=padding,
        align=align,
        valign=valign,
        max_lines=max_lines,
        ellipsis=ell,
        use_device_font=use_device,
    )
