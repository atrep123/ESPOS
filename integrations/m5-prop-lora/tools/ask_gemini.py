"""Send preview images to a Gemini model for a design critique.

The API key is read through tools/gemini_key.py so it never lands in the repo.
Usage:

    GEMINI_API_KEY=... python tools/ask_gemini.py img1.png img2.png ...
    GEMINI_API_KEY_FILE=... python tools/ask_gemini.py img1.png img2.png ...
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request

from gemini_key import load_api_key

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

PROMPT = (
    "You are a senior product/UI designer reviewing the on-device UI for an "
    "M5Stack Dial: a small ROUND 240x240 pixel LCD with a rotary encoder + touch. "
    "The device is a handheld controller that drives wireless RGB LED 'props' over "
    "LoRa (4 addressable LED channels, a brightness level, and commands like "
    "PREVIEW / ARM / ODPAL[=fire] / STOP / PING).\n\n"
    "Design intent: a dark, premium, serious instrument look (NOT playful). It has "
    "two modes that must be visually distinct:\n"
    " - SETUP mode (caption 'NASTAVENI'): the currently selected LED becomes a big "
    "central orb whose colour you tune directly; channels 1-4 shown as an indicator "
    "row at the bottom.\n"
    " - COMMAND mode (caption 'PRIKAZ'): a hollow 'transmit target' ring shows the "
    "action to send; left/right chevrons mean you can scroll actions.\n"
    "An outer ring is the brightness gauge, coloured by connection/state "
    "(green=ready, amber=waiting for ACK, red=armed/error).\n\n"
    "The attached images are renders of several states (a contact sheet plus close "
    "ups). Critique honestly: does it look good, professional and serious? Is the "
    "two-mode distinction clear at a glance? Are the LED indicators professional? "
    "Any legibility, hierarchy, balance, spacing, or colour problems on a small "
    "round screen? Give a short verdict (good / needs work) and a concise, "
    "prioritised list of concrete improvements."
)


def main() -> int:
    key = load_api_key()
    paths = sys.argv[1:]
    if not paths:
        print("ERROR: pass image paths", file=sys.stderr)
        return 2

    parts = [{"text": PROMPT}]
    for p in paths:
        with open(p, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        parts.append({"inline_data": {"mime_type": "image/png", "data": data}})

    body = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    )
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1

    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        print(json.dumps(payload, indent=2))
        return 1
    out_path = os.path.join(
        os.path.dirname(__file__), "..", "build", "preview", "gemini_review.txt"
    )
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"=== {MODEL} verdict ===\n\n{text}\n")
    sys.stdout.buffer.write((f"=== {MODEL} verdict ===\n\n{text}\n").encode("utf-8"))
    sys.stderr.write(f"\n[saved to {out_path}]\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
