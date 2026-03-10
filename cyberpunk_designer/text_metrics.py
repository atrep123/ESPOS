from __future__ import annotations

from typing import List, Optional, Tuple

from ui_designer import WidgetConfig

DEVICE_CHAR_W = 6
DEVICE_CHAR_H = 8


def is_device_profile(profile: Optional[str]) -> bool:
    p = str(profile or "").strip().lower()
    return p.startswith("esp32os_") or p.startswith("oled_")


def inner_text_area_px(w: WidgetConfig) -> Tuple[int, int]:
    """Return (inner_w, inner_h) used for runtime-like text layout (in pixels)."""
    kind = str(getattr(w, "type", "") or "").strip().lower()
    width = int(getattr(w, "width", 0) or 0)
    height = int(getattr(w, "height", 0) or 0)
    if width <= 0 or height <= 0:
        return 0, 0

    if kind in {"checkbox", "radiobutton"}:
        box = 6 if height > 6 else (height - 2)
        if box < 2:
            box = 2
        inner_w = width - box - 4
        inner_h = height
        return max(0, int(inner_w)), max(0, int(inner_h))

    border_on = bool(getattr(w, "border", True))
    inset = 1 if border_on else 0
    pad = 1
    inner_w = width - (inset + pad) * 2
    inner_h = height - (inset + pad) * 2
    return max(0, int(inner_w)), max(0, int(inner_h))


def ellipsize_chars(text: str, max_chars: int, ellipsis: str = "...") -> str:
    s = str(text or "")
    max_chars = int(max_chars)
    if max_chars <= 0 or not s:
        return ""
    if len(s) <= max_chars:
        return s
    if not ellipsis:
        return s[:max_chars]
    if len(ellipsis) >= max_chars:
        return ellipsis[:max_chars]
    return s[: max_chars - len(ellipsis)] + ellipsis


def wrap_text_chars(
    text: str,
    max_chars: int,
    max_lines: int,
    ellipsis: str = "...",
) -> Tuple[List[str], bool]:
    """Word-wrap in character cells. Returns (lines, truncated)."""
    max_chars = int(max_chars)
    max_lines = int(max_lines)
    if max_chars <= 0 or max_lines <= 0:
        return [], bool(text)

    raw = str(text or "").replace("\t", " ").replace("\r", "")
    # Preserve explicit newlines as paragraph breaks.
    paras = raw.split("\n")

    lines: List[str] = []
    truncated = False

    def _push(line: str) -> None:
        nonlocal truncated
        if len(lines) >= max_lines:
            truncated = True
            return
        lines.append(line)

    for para in paras:
        if truncated:
            break
        p = " ".join(para.split())
        if not p:
            continue
        words = p.split(" ")
        cur = ""
        for word in words:
            if truncated:
                break
            cand = word if not cur else f"{cur} {word}"
            if len(cand) <= max_chars:
                cur = cand
                continue
            if cur:
                _push(cur)
                cur = word
                continue
            # Single long word: chunk it.
            for i in range(0, len(word), max_chars):
                _push(word[i : i + max_chars])
                if truncated:
                    break
            cur = ""
        if cur and not truncated:
            _push(cur)

    if truncated and lines:
        if ellipsis:
            lines[-1] = ellipsize_chars(lines[-1], max_chars, ellipsis=ellipsis)
        else:
            lines[-1] = lines[-1][:max_chars]

    return lines, truncated


def text_truncates_in_widget(w: WidgetConfig, text: str) -> bool:
    """Return True when the full text won't be displayed without truncation."""
    inner_w, inner_h = inner_text_area_px(w)
    if inner_w <= 0 or inner_h <= 0:
        return bool(str(text or "").strip())

    max_chars = inner_w // DEVICE_CHAR_W
    max_lines_by_h = inner_h // DEVICE_CHAR_H
    if max_chars <= 0 or max_lines_by_h <= 0:
        return bool(str(text or "").strip())

    overflow = str(getattr(w, "text_overflow", "ellipsis") or "ellipsis").strip().lower()
    if overflow not in {"ellipsis", "wrap", "clip", "auto"}:
        overflow = "ellipsis"

    raw = str(text or "")
    flat = " ".join(raw.replace("\t", " ").replace("\n", " ").split())
    use_wrap = overflow == "wrap"
    if overflow == "auto":
        use_wrap = (max_lines_by_h >= 2) and (("\n" in raw) or (len(flat) > max_chars))

    if not use_wrap:
        return len(flat) > max_chars

    max_lines = max_lines_by_h
    try:
        ml = getattr(w, "max_lines", None)
        if ml is not None and str(ml) != "":
            ml_i = int(ml)
            if ml_i > 0:
                max_lines = min(max_lines, ml_i)
    except Exception:
        pass
    max_lines = max(1, int(max_lines))

    _lines, truncated = wrap_text_chars(raw, max_chars=max_chars, max_lines=max_lines, ellipsis="...")
    return truncated
