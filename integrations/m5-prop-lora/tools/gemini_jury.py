"""Run a 'jury' of N independent Gemini votes per screenshot and aggregate.

Each vote evaluates ONE image (photo-by-photo) via the Gemini REST API using
GEMINI_API_KEY or the gitignored .gemini_api_key file. Votes are run with bounded concurrency.
Per image we collect a 1-10 SCORE, a SAFE yes/no (is armed/firing unmistakable?),
the top ISSUE and the best GOOD point, then aggregate (mean score, safe-fraction,
issue frequency).

Usage:
    python tools/gemini_jury.py --dir build/preview --device "M5 Dial (round 240x240)" --per 3
    python tools/gemini_jury.py --dir build/preview_dinrx --device "M5 DinMeter (240x135)" --per 3

Output: build/reviews/jury_<dirname>.md  (+ a printed summary)
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUBRIC = (
    "You are a STRICT product/UI design juror. The attached image is ONE screen of a "
    "{device} UI for a wireless LoRa THEATRICAL/PYRO prop controller — a safety device, "
    "so the ARMED/FIRING state must be unmistakable, and dark/premium/serious is the "
    "intended look. Judge ONLY this one image. Be critical, not generous.\n"
    "Respond in EXACTLY this format and nothing else:\n"
    "SCORE: <integer 1-10>\n"
    "SAFE: <yes|no>\n"
    "ISSUE: <the single most important problem, one short sentence>\n"
    "GOOD: <the single best thing, one short sentence>"
)


GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def _load_api_key() -> str:
    # Prefer GEMINI_API_KEY; fall back to the gitignored .gemini_api_key file. This tool
    # calls the REST API directly, so a local key is required for real jury runs.
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        key_file = ROOT / ".gemini_api_key"
        if key_file.exists():
            key = key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("No Gemini API key: set GEMINI_API_KEY or create .gemini_api_key")
    return key



def _endpoint(api_key: str) -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )


def run_one(img: Path, device: str, idx: int, endpoint: str) -> dict:
    prompt = RUBRIC.format(device=device)
    try:
        b64 = base64.b64encode(img.read_bytes()).decode("ascii")
        body = json.dumps({
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": b64}},
            ]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 512,
                                 "thinkingConfig": {"thinkingBudget": 0}},
        }).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        out = (data.get("candidates", [{}])[0]
                   .get("content", {}).get("parts", [{}])[0].get("text", "")) or ""
    except urllib.error.HTTPError as exc:
        return {"img": img.name, "idx": idx, "score": None, "safe": None,
                "issue": f"ERROR: HTTP {exc.code}", "good": ""}
    except Exception as exc:  # noqa: BLE001
        return {"img": img.name, "idx": idx, "score": None, "safe": None,
                "issue": f"ERROR: {exc}", "good": ""}

    score = re.search(r"SCORE:\s*(\d+)", out)
    safe = re.search(r"SAFE:\s*(yes|no)", out, re.IGNORECASE)
    issue = re.search(r"ISSUE:\s*(.+)", out)
    good = re.search(r"GOOD:\s*(.+)", out)
    return {
        "img": img.name, "idx": idx,
        "score": int(score.group(1)) if score else None,
        "safe": (safe.group(1).lower() == "yes") if safe else None,
        "issue": issue.group(1).strip() if issue else "(unparsed)",
        "good": good.group(1).strip() if good else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="dir of PNGs (relative to repo root)")
    ap.add_argument("--device", required=True, help="device label for the rubric")
    ap.add_argument("--per", type=int, default=3, help="votes per image")
    ap.add_argument("--workers", type=int, default=5, help="max concurrent Gemini calls")
    ap.add_argument("--exclude", default="contact", help="substring of filenames to skip")
    args = ap.parse_args()

    img_dir = (ROOT / args.dir).resolve()
    pngs = sorted(p for p in img_dir.glob("*.png") if args.exclude not in p.stem)
    if not pngs:
        print(f"no PNGs in {img_dir}", file=sys.stderr)
        return 2
    endpoint = _endpoint(_load_api_key())

    jobs = [(p, i) for p in pngs for i in range(args.per)]
    print(f"jury: {len(pngs)} images x {args.per} votes = {len(jobs)} Gemini calls "
          f"({args.workers} concurrent) via REST {GEMINI_MODEL}")

    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, p, args.device, i, endpoint) for (p, i) in jobs]
        for n, fut in enumerate(cf.as_completed(futs), 1):
            results.append(fut.result())
            print(f"  [{n}/{len(jobs)}] done", file=sys.stderr)

    # aggregate per image
    out_lines = [f"# Gemini jury — {args.device}", "",
                 f"{len(pngs)} screens x {args.per} votes = {len(jobs)} votes.", ""]
    by_img: dict[str, list[dict]] = {}
    for r in results:
        by_img.setdefault(r["img"], []).append(r)

    overall = []
    for name in sorted(by_img):
        votes = by_img[name]
        scores = [v["score"] for v in votes if v["score"] is not None]
        safes = [v["safe"] for v in votes if v["safe"] is not None]
        mean = sum(scores) / len(scores) if scores else float("nan")
        safe_frac = (sum(1 for s in safes if s) / len(safes)) if safes else float("nan")
        overall += scores
        issues = Counter(v["issue"] for v in votes if v["issue"])
        out_lines.append(f"## {name}  — mean {mean:.1f}/10, SAFE {safe_frac*100:.0f}% "
                         f"(n={len(scores)})")
        for issue, cnt in issues.most_common(5):
            out_lines.append(f"- ({cnt}x) {issue}")
        out_lines.append("")

    grand = sum(overall) / len(overall) if overall else float("nan")
    out_lines.insert(3, f"**Overall mean score: {grand:.1f}/10**\n")

    out_dir = ROOT / "build" / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"jury_{img_dir.name}.md"
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print("\n".join(out_lines))
    print(f"\n[saved to {out_path}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
