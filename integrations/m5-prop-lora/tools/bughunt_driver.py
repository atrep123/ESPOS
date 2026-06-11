"""Sequential READ-ONLY Codex bug-hunt driver for the M5 prop controller.

Runs N focused, read-only Codex missions (source file x bug "lens"), ONE AT A
TIME, saving each report to build/bughunt/NNN_<slug>.txt and a one-line status to
build/bughunt/_progress.log. Codex runs with `--sandbox read-only`, so it can
inspect but never modify the repo.

IMPORTANT: every finding still MUST be verified by a human/Claude against the
actual code -- LLM bug reports carry false positives. This driver only collects;
it does not trust.

Usage:
    python tools/bughunt_driver.py [--limit 100] [--start 1]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "bughunt"

# Meaningful, non-vendored source under review (safety-critical firmware first).
FILES = [
    "shared/protocol/prop_protocol.h",
    "shared/core/safety_logic.h",
    "shared/protocol/protocol.py",
    "firmware/din-rx/src/prop_rx.cpp",
    "firmware/din-rx/src/main.cpp",
    "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
    "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
    "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
    "firmware/dial-tx/main/apps/app_prop_tx/chain_key_poller.cpp",
    "firmware/dial-tx/main/main.cpp",
    "firmware/c6l-modem/src/main.cpp",
    "tools/preview_prop_tx.py",
    "tools/preview_din_rx_render.py",
    "tools/gemini_jury.py",
    "firmware/tests/test_safety_logic.cpp",
    "firmware/tests/test_palette.cpp",
    "tests/test_protocol.py",
]

LENSES = {
    "mem": "memory safety -- buffer/array bounds, fixed-buffer writes (snprintf/strncpy/char[]), "
           "std::vector/std::string misuse, pointer lifetime / dangling, out-of-range index",
    "int": "integer issues -- overflow/underflow, signed vs unsigned mixups, narrowing/truncation, "
           "uint32 millis() wraparound in time comparisons, undefined shifts",
    "conc": "concurrency & interrupts -- data races between task/loop and ISR/RMT/UART/timer callbacks, "
            "missing volatile/atomic on shared state, non-reentrant calls from a callback",
    "proto": "protocol & safety logic -- frame parse/length/route validation, HMAC/MAC check correctness, "
             "replay/dedup window math, 32-bit epoch handling, ARM/FIRE/STOP state machine, fail-safe defaults",
    "err": "error handling -- ignored return codes, missing failure branches, NVS/UART/radio/ESP-NOW init "
           "failures, partial/short reads, malformed or truncated input not rejected",
    "logic": "logic & boundaries -- off-by-one, wrong comparison/condition, edge cases, resource leaks, "
             "initialisation order, dead or unreachable code, copy-paste mistakes",
}
LENS_ORDER = ["mem", "int", "conc", "proto", "err", "logic"]

PROMPT = (
    "READ-ONLY bug hunt on the M5 LoRa prop controller (SAFETY-CRITICAL: it triggers theatrical/pyro "
    "effects, so reliability/safety defects matter most). Examine the single file `{file}` through this "
    "lens: {lens}. Report ONLY real, concrete bugs you can point at. For each bug use the format:\n"
    "  {file}:<line> -- <the problem> -- <why it matters> -- <suggested fix>\n"
    "If the file has no real bug for this lens, reply with exactly: NO BUGS FOUND\n"
    "No style nits, no speculation, no praise. Do not modify anything."
)


def codex_exe() -> str:
    for name in ("codex", "codex.cmd", "codex.exe"):
        found = shutil.which(name)
        if found:
            return found
    return "codex.cmd" if os.name == "nt" else "codex"


CODEX = codex_exe()


def slug(path: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_")[-40:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--start", type=int, default=1, help="1-based mission index to resume from")
    ap.add_argument("--timeout", type=int, default=360)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    missions = [(f, l) for f in FILES for l in LENS_ORDER][: args.limit]
    total = len(missions)
    print(f"bug-hunt: {total} sequential read-only Codex missions via {CODEX}")

    for idx, (f, lens_key) in enumerate(missions, 1):
        if idx < args.start:
            continue
        prompt = PROMPT.format(file=f, lens=LENSES[lens_key])
        report = OUT / f"{idx:03d}_{lens_key}_{slug(f)}.txt"
        t0 = time.time()
        try:
            proc = subprocess.run(
                [CODEX, "exec", "--skip-git-repo-check", "--sandbox", "read-only",
                 "-c", "model_reasoning_effort=medium", prompt],
                cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=args.timeout, stdin=subprocess.DEVNULL,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            out = (proc.stdout or "")
            if proc.stderr:
                out += "\n[stderr]\n" + proc.stderr
        except subprocess.TimeoutExpired:
            out = "ERROR: codex mission timed out"
        except Exception as exc:  # noqa: BLE001
            out = f"ERROR: {exc}"

        report.write_text(f"# mission {idx}/{total}: {f} | lens={lens_key}\n\n{out}\n", encoding="utf-8")
        clean = "NO BUGS FOUND" in out and "ERROR" not in out
        verdict = "clean" if clean else ("ERROR" if out.startswith("ERROR") else "REVIEW")
        dt = time.time() - t0
        line = f"[{idx:03d}/{total}] {f} :: {lens_key} -> {verdict} ({dt:.0f}s)"
        print(line)
        with open(OUT / "_progress.log", "a", encoding="utf-8") as g:
            g.write(line + "\n")

    print("bug-hunt complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
