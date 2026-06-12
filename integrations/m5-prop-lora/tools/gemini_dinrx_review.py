"""Send the DinMeter renders to Gemini at MAX resolution for a design critique.

Renders every scene at the full supersampled buffer (SCREEN*S = 960x540, not the
240x135 device downscale), saves them to build/preview_dinrx_hires/, then asks
Gemini (REST, paid key in GEMINI_API_KEY, GEMINI_API_KEY_FILE, or
.gemini_api_key) for:
  1) a holistic critique of the whole contact sheet (hierarchy / safety / declutter),
  2) a per-state SCORE + top ISSUE + best GOOD.

Usage:
    python tools/gemini_dinrx_review.py
Out: build/reviews/gemini_dinrx_hires.md  (+ printed)
"""

from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from gemini_key import load_api_key
import preview_din_rx_render as P
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_ENDPOINT_PREFIX = "https://generativelanguage.googleapis.com/v1beta/models/"


def _load_api_key() -> str:
    return load_api_key(ROOT)


DEVICE = "M5 DinMeter (240x135 landscape LCD) RECEIVER of a wireless LoRa THEATRICAL/PYRO prop controller"

CONTEXT = (
    f"These are mock renders of the {DEVICE}. It is a SAFETY device: the armed (NABITO) "
    "and firing (PALI) states MUST be unmistakable across a room. UI strings are Czech "
    "(KLID=idle/safe, NABITO=armed, PALI=firing, STOP=e-stopped/latched). The agreed "
    "design is a 'decluttered hybrid' with 3 zones: a STATUS bar on top, a framed EFEKT "
    "panel (4 LED brightness curves in identity colours red/green/blue/amber + a colour "
    "PALETTE strip merged at the 0% line + a PRECHOD/SKOK fade/step tag), and a "
    "focus+scroll PARAMETRY list (2 rows). There is a 4px state-colour spine down the "
    "left edge. Danger states get a full colour flood + a hazard triangle + a screen "
    "border; STOP is a calm blue flood (no border); KLID is a quiet chip."
)


def _b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _endpoint(api_key: str) -> dict[str, object]:
    return {
        "url": f"{GEMINI_ENDPOINT_PREFIX}{GEMINI_MODEL}:generateContent",
        "headers": {"x-goog-api-key": api_key},
    }


def _ask(endpoint: dict[str, object], parts: list[dict], max_tokens: int = 1400) -> str:
    url = str(endpoint.get("url", ""))
    if not url.startswith(GEMINI_ENDPOINT_PREFIX):
        return "ERROR: invalid Gemini endpoint"
    headers = {"Content-Type": "application/json"}
    headers.update(endpoint.get("headers", {}))

    body = json.dumps(
        {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=body,
        headers=headers,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=180)  # noqa: S310
        data = json.loads(resp.read())
        return (
            data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        ) or "(empty)"
    except urllib.error.HTTPError as exc:
        return f"ERROR HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:400]}"
    except Exception as exc:
        return f"ERROR: {exc}"


def hires_contact(named: list[tuple[str, Image.Image]]) -> Image.Image:
    cols = 2
    pad = 24
    label_h = 34
    cw, ch = named[0][1].size
    rows = (len(named) + cols - 1) // cols
    sheet = Image.new(
        "RGB",
        (cols * cw + (cols + 1) * pad, rows * (ch + label_h) + (rows + 1) * pad),
        (20, 22, 26),
    )
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(P.FONT_BOLD), 26)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, im) in enumerate(named):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + label_h + pad)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + ch + 4), name, font=font, fill=(220, 230, 235))
    return sheet


def main() -> int:
    endpoint = _endpoint(_load_api_key())
    out = ROOT / "build" / "preview_dinrx_hires"
    out.mkdir(parents=True, exist_ok=True)

    named: list[tuple[str, Image.Image]] = []
    for name, (view, page) in P.scenes().items():
        im = P.render(view, page, hires=True)
        im.save(out / f"{name}.png")
        named.append((name, im))
    sheet = hires_contact(named)
    sheet_path = out / "contact_hires.png"
    sheet.save(sheet_path)
    print(
        f"hires renders -> {out}  ({named[0][1].size[0]}x{named[0][1].size[1]} each, "
        f"sheet {sheet.size[0]}x{sheet.size[1]})"
    )

    lines = [
        "# Gemini critique (MAX-RES) — DinMeter decluttered hybrid",
        "",
        f"model: {GEMINI_MODEL}; per-state renders at {named[0][1].size[0]}x"
        f"{named[0][1].size[1]} (4x supersample).",
        "",
    ]

    # 1) Holistic critique on the full contact sheet.
    holistic_prompt = (
        CONTEXT + "\n\nThe attached image shows ALL states together. Give a SHARP, "
        "specific critique (not generic praise). Cover, with concrete pixel-level "
        "suggestions where relevant:\n"
        "1. SAFETY: are NABITO (armed) and PALI (firing) instantly distinguishable from "
        "each other and from the safe states, across a room?\n"
        "2. HIERARCHY: does the STATUS dominate, or does the plot/params still fight it?\n"
        "3. The EFEKT panel: is the framed plot + merged palette + PRECHOD tag clean or "
        "cluttered?\n4. The 4px state spine and STOP=blue-flood decisions: keep, change, drop?\n"
        "5. The SINGLE most valuable change you would make next.\n"
        "Be opinionated and concrete. ~300 words."
    )
    print("  [1/2] holistic critique on contact sheet ...")
    holistic = _ask(
        endpoint,
        [
            {"text": holistic_prompt},
            {"inline_data": {"mime_type": "image/png", "data": _b64(sheet)}},
        ],
    )
    lines += ["## Holistic critique (all states)", "", holistic, ""]

    # 2) Per-state structured verdict.
    per_prompt = (
        CONTEXT + "\n\nJudge ONLY this single attached state image. Be strict. "
        "Respond in EXACTLY this format:\nSCORE: <1-10>\nSAFE: <yes|no>\n"
        "ISSUE: <single most important problem, one sentence>\n"
        "GOOD: <single best thing, one sentence>"
    )
    lines += ["## Per-state verdict", ""]
    for name, im in named:
        if name == "led_delays":
            continue
        print(f"  [2/2] scoring {name} ...")
        verdict = _ask(
            endpoint,
            [{"text": per_prompt}, {"inline_data": {"mime_type": "image/png", "data": _b64(im)}}],
            max_tokens=300,
        )
        lines += [f"### {name}", "```", verdict.strip(), "```", ""]

    rev = ROOT / "build" / "reviews"
    rev.mkdir(parents=True, exist_ok=True)
    md = rev / "gemini_dinrx_hires.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"\n[saved -> {md}]\n[hires sheet -> {sheet_path}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
