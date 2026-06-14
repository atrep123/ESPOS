"""Run a 'jury' of N independent Gemini votes per screenshot and aggregate.

Each vote evaluates ONE image (photo-by-photo) via the Gemini REST API using
GEMINI_API_KEY, GEMINI_API_KEY_FILE, or a gitignored .gemini_api_key file.
Votes are run with bounded concurrency.
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

from gemini_code_review import redact_secrets, safe_print
from gemini_key import load_api_key

ROOT = Path(__file__).resolve().parents[1]

RUBRIC = (
    "You are a STRICT product/UI design juror. The attached image is ONE screen of a "
    "{device} UI for a wireless LoRa THEATRICAL/PYRO prop controller — a safety device, "
    "so the safety state must be unmistakable, and dark/premium/serious is the "
    "intended look. Judge ONLY this one image. Be critical, not generous. "
    "SAFE yes if the screen is unmistakably safe, setup/editing, armed, firing, waiting, "
    "acknowledged, or error/no-ack. Do not mark safe/setup/ACK screens unsafe merely "
    "because they are not armed. Mark SAFE no only when a dangerous state is ambiguous, "
    "or a safe/editing state could be mistaken for armed or firing.\n"
    "Respond in EXACTLY this format and nothing else:\n"
    "SCORE: <integer 1-10>\n"
    "SAFE: <yes|no>\n"
    "ISSUE: <the single most important problem, one short sentence>\n"
    "GOOD: <the single best thing, one short sentence>"
)


GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_ENDPOINT_PREFIX = "https://generativelanguage.googleapis.com/v1beta/models/"


def _load_api_key() -> str:
    return load_api_key(ROOT)


def _endpoint(api_key: str) -> dict[str, object]:
    return {
        "url": f"{GEMINI_ENDPOINT_PREFIX}{GEMINI_MODEL}:generateContent",
        "headers": {"x-goog-api-key": api_key},
    }


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def parse_vote_output(text: str) -> dict[str, object]:
    match = re.fullmatch(
        r"\s*SCORE:\s*(10|[1-9])\s*\n"
        r"SAFE:\s*(yes|no)\s*\n"
        r"ISSUE:\s*(\S[^\r\n]*)\s*\n"
        r"GOOD:\s*(\S[^\r\n]*)\s*",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("malformed Gemini vote")
    return {
        "score": int(match.group(1)),
        "safe": match.group(2).lower() == "yes",
        "issue": match.group(3).strip(),
        "good": match.group(4).strip(),
    }


def resolve_image_dir(value: str, allow_external: bool = False) -> Path:
    raw = Path(value)
    img_dir = (raw if raw.is_absolute() else ROOT / raw).resolve()
    if allow_external:
        return img_dir
    try:
        rel = img_dir.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(
            "--dir must stay inside this repo unless --allow-external-images is supplied"
        ) from exc
    if not (
        len(rel.parts) >= 2
        and rel.parts[0] == "build"
        and rel.parts[1].startswith("preview")
    ):
        raise ValueError(
            "--dir must point at build/preview* unless --allow-external-images is supplied"
        )
    return img_dir


def select_pngs(img_dir: Path, image_names: list[str] | None, exclude: str) -> list[Path]:
    if image_names:
        selected: list[Path] = []
        for name in image_names:
            requested = Path(name)
            if requested.name != name or requested.is_absolute():
                raise ValueError(f"--image must be a filename inside --dir: {name}")
            if requested.suffix.lower() != ".png":
                raise ValueError(f"--image must name a PNG file: {name}")
            path = img_dir / requested
            if not path.is_file():
                raise ValueError(f"--image not found in {img_dir}: {name}")
            selected.append(path)
        return selected
    return sorted(p for p in img_dir.glob("*.png") if exclude not in p.stem)


def run_one(img: Path, device: str, idx: int, endpoint: dict[str, object]) -> dict:
    prompt = RUBRIC.format(device=device)
    try:
        headers = {"Content-Type": "application/json"}
        headers.update(endpoint.get("headers", {}))
        b64 = base64.b64encode(img.read_bytes()).decode("ascii")
        body = json.dumps(
            {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": b64}},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 512,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            }
        ).encode("utf-8")
        req = urllib.request.Request(str(endpoint["url"]), data=body, headers=headers)
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        out = (
            data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        ) or ""
    except urllib.error.HTTPError as exc:
        return {
            "img": img.name,
            "idx": idx,
            "score": None,
            "safe": None,
            "issue": f"ERROR: HTTP {exc.code}",
            "good": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "img": img.name,
            "idx": idx,
            "score": None,
            "safe": None,
            "issue": redact_secrets(f"ERROR: {exc}"),
            "good": "",
        }

    out = redact_secrets(out)
    try:
        parsed = parse_vote_output(out)
    except ValueError as exc:
        return {
            "img": img.name,
            "idx": idx,
            "score": None,
            "safe": None,
            "issue": f"ERROR: {exc}",
            "good": "",
        }
    return {
        "img": img.name,
        "idx": idx,
        "score": parsed["score"],
        "safe": parsed["safe"],
        "issue": parsed["issue"],
        "good": parsed["good"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="dir of PNGs (relative to repo root)")
    ap.add_argument("--device", required=True, help="device label for the rubric")
    ap.add_argument("--per", type=_positive_int, default=3, help="votes per image")
    ap.add_argument("--workers", type=_positive_int, default=5, help="max concurrent Gemini calls")
    ap.add_argument(
        "--image",
        action="append",
        dest="images",
        help="exact PNG filename inside --dir to review; repeat to select multiple images",
    )
    ap.add_argument("--exclude", default="contact", help="substring of filenames to skip")
    ap.add_argument(
        "--allow-errors",
        action="store_true",
        help="exit 0 even when one or more Gemini votes fail or cannot be parsed",
    )
    ap.add_argument(
        "--allow-external-images",
        action="store_true",
        help="allow --dir outside repo build/preview*; otherwise avoids uploading unrelated PNGs",
    )
    args = ap.parse_args(argv)

    try:
        img_dir = resolve_image_dir(args.dir, allow_external=args.allow_external_images)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        pngs = select_pngs(img_dir, args.images, args.exclude)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not pngs:
        print(f"no PNGs in {img_dir}", file=sys.stderr)
        return 2
    endpoint = _endpoint(_load_api_key())

    jobs = [(p, i) for p in pngs for i in range(args.per)]
    print(
        f"jury: {len(pngs)} images x {args.per} votes = {len(jobs)} Gemini calls "
        f"({args.workers} concurrent) via REST {GEMINI_MODEL}"
    )

    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, p, args.device, i, endpoint) for (p, i) in jobs]
        for n, fut in enumerate(cf.as_completed(futs), 1):
            results.append(fut.result())
            print(f"  [{n}/{len(jobs)}] done", file=sys.stderr)

    # aggregate per image
    out_lines = [
        f"# Gemini jury — {args.device}",
        "",
        f"{len(pngs)} screens x {args.per} votes = {len(jobs)} votes.",
        "",
    ]
    by_img: dict[str, list[dict]] = {}
    for r in results:
        by_img.setdefault(r["img"], []).append(r)

    overall = []
    error_votes = [
        r
        for r in results
        if r.get("score") is None
        or r.get("safe") is None
        or str(r.get("issue", "")).startswith("ERROR:")
    ]
    for name in sorted(by_img):
        votes = by_img[name]
        scores = [v["score"] for v in votes if v["score"] is not None]
        safes = [v["safe"] for v in votes if v["safe"] is not None]
        mean = sum(scores) / len(scores) if scores else float("nan")
        safe_frac = (sum(1 for s in safes if s) / len(safes)) if safes else float("nan")
        overall += scores
        issues = Counter(v["issue"] for v in votes if v["issue"])
        out_lines.append(
            f"## {name}  — mean {mean:.1f}/10, SAFE {safe_frac * 100:.0f}% (n={len(scores)})"
        )
        for issue, cnt in issues.most_common(5):
            out_lines.append(f"- ({cnt}x) {issue}")
        out_lines.append("")

    grand = sum(overall) / len(overall) if overall else float("nan")
    out_lines.insert(3, f"**Overall mean score: {grand:.1f}/10**\n")
    if error_votes:
        out_lines.append("## Errors")
        out_lines.append("")
        for vote in sorted(error_votes, key=lambda item: (item["img"], item["idx"])):
            out_lines.append(
                f"- {vote['img']} vote {vote['idx']}: {vote.get('issue', '(unparsed)')}"
            )
        out_lines.append("")

    out_dir = ROOT / "build" / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"jury_{img_dir.name}.md"
    report = redact_secrets("\n".join(out_lines))
    out_path.write_text(report, encoding="utf-8")
    safe_print(report)
    print(f"\n[saved to {out_path}]", file=sys.stderr)
    return 0 if args.allow_errors or not error_votes else 1


if __name__ == "__main__":
    raise SystemExit(main())
