"""Generate a non-secret first-upload readiness report for the three-device stack."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "build" / "first_upload_preflight.md"

PLACEHOLDER_PORTS = {
    "dial-tx": "COM6",
    "c6l-modem-dial": "COM7",
    "c6l-modem-prop": "COM8",
    "din-rx": "COM9",
    "sticks3-terminal": "COM10",
}

RENDER_ARTIFACTS = [
    ROOT / "build" / "preview" / "contact.png",
    ROOT / "build" / "preview" / "terminal_external_oled_128x64_x4.png",
    ROOT / "build" / "preview_dinrx" / "contact.png",
]


def run_command(args: list[str], *, timeout: int = 30) -> tuple[bool, str]:
    command = resolve_command(args[0])
    if command is None:
        return False, f"{args[0]} was not found"
    try:
        completed = subprocess.run(
            [command, *args[1:]],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return completed.returncode == 0, completed.stdout.strip()


def resolve_command(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct
    if os.name == "nt" and "." not in Path(name).name:
        for suffix in (".exe", ".cmd", ".bat", ".ps1"):
            candidate = shutil.which(name + suffix)
            if candidate:
                return candidate
    return None


def one_line(text: str) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip())


def tool_status() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, list[str], int]] = [
        ("pio", ["pio", "--version"], 30),
        ("esptool", [sys.executable, "-m", "esptool", "version"], 30),
        ("mpremote", [sys.executable, "-m", "mpremote", "--version"], 30),
        ("idf.py", ["idf.py", "--version"], 30),
        ("Claude Code via npx", ["npx", "@anthropic-ai/claude-code", "--version"], 120),
    ]
    rows: list[tuple[str, bool, str]] = []
    for name, command, timeout in checks:
        ok, output = run_command(command, timeout=timeout)
        rows.append((name, ok, one_line(output)[:240]))
    return rows


def gemini_key_status() -> tuple[bool, str]:
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return True, "GEMINI_API_KEY is set"
    if os.environ.get("GEMINI_API_KEY_FILE", "").strip():
        path = Path(os.environ["GEMINI_API_KEY_FILE"]).expanduser()
        return path.is_file(), f"GEMINI_API_KEY_FILE points to {'existing' if path.is_file() else 'missing'} file"

    candidates = [ROOT / ".gemini_api_key", Path.home() / ".gemini_api_key"]
    for path in candidates:
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            return True, f"local key file exists: {path}"
    return False, "no GEMINI_API_KEY, GEMINI_API_KEY_FILE, repo .gemini_api_key, or home .gemini_api_key"


def serial_ports() -> tuple[bool, str, list[str]]:
    ok, output = run_command(["pio", "device", "list"], timeout=30)
    ports = sorted(set(re.findall(r"\bCOM\d+\b|/dev/(?:ttyACM|ttyUSB)\d+\b", output)))
    return ok, output, ports


def dry_run_flash_commands() -> list[tuple[str, bool, str]]:
    script = ROOT / "tools" / "flash.ps1"
    commands = [
        ("c6l-modem-dial", "c6l-modem", PLACEHOLDER_PORTS["c6l-modem-dial"]),
        ("c6l-modem-prop", "c6l-modem", PLACEHOLDER_PORTS["c6l-modem-prop"]),
        ("din-rx", "din-rx", PLACEHOLDER_PORTS["din-rx"]),
        ("sticks3-terminal", "sticks3-terminal", PLACEHOLDER_PORTS["sticks3-terminal"]),
        ("dial-tx", "dial-tx", PLACEHOLDER_PORTS["dial-tx"]),
    ]
    rows: list[tuple[str, bool, str]] = []
    for label, target, port in commands:
        ok, output = run_command(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Target",
                target,
                "-Port",
                port,
                "-DryRun",
            ],
            timeout=60,
        )
        rows.append((label, ok, output))
    return rows


def render_artifact_rows() -> list[tuple[Path, bool, int]]:
    return [(path, path.is_file(), path.stat().st_size if path.is_file() else 0) for path in RENDER_ARTIFACTS]


def build_report() -> tuple[str, list[str]]:
    blockers: list[str] = []
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# First Upload Preflight - {now}",
        "",
        "Scope: M5 Dial odpalovac, M5StickS3 Terminal, DinMeter/prop receiver.",
        "This report contains no API keys or runtime HMAC key bytes.",
        "",
        "## Tooling",
    ]

    tools = tool_status()
    for name, ok, detail in tools:
        lines.append(f"- {name}: {'OK' if ok else 'BLOCKED'} - {detail}")
        if name == "idf.py" and not ok:
            blockers.append("Load ESP-IDF before Dial C++ build/flash (`idf.py` is not available).")

    gemini_ok, gemini_detail = gemini_key_status()
    lines.append(f"- Gemini key source: {'OK' if gemini_ok else 'BLOCKED'} - {gemini_detail}")
    if not gemini_ok:
        blockers.append("Set an ignored Gemini key source before AI visual/code gates.")

    lines.extend(["", "## Serial Ports"])
    ports_ok, ports_output, ports = serial_ports()
    lines.append(f"- pio device list: {'OK' if ports_ok else 'BLOCKED'}")
    lines.append("```text")
    lines.append(ports_output or "<no output>")
    lines.append("```")
    upload_ports = [port for port in ports if port.upper() != "COM1"]
    if not upload_ports:
        blockers.append("No upload target ports are visible; current enumeration shows only non-target/legacy ports.")
    lines.append(f"- detected upload candidates excluding COM1: {', '.join(upload_ports) if upload_ports else '<none>'}")

    lines.extend(["", "## Render Artifacts"])
    for path, exists, size in render_artifact_rows():
        rel = path.relative_to(ROOT)
        lines.append(f"- {rel}: {'OK' if exists and size > 0 else 'MISSING'} ({size} bytes)")
        if not exists or size <= 0:
            blockers.append(f"Render artifact missing: {rel}")

    lines.extend(["", "## Dry-run Flash Commands"])
    for label, ok, output in dry_run_flash_commands():
        lines.append(f"- {label}: {'OK' if ok else 'BLOCKED'}")
        lines.append("```text")
        lines.append(output or "<no output>")
        lines.append("```")
        if not ok:
            blockers.append(f"Dry-run flash command failed for {label}.")

    lines.extend(
        [
            "",
            "## Required Before Real Upload",
            "- Fill fresh `<DIAL_COM>`, `<TERMINAL_COM>`, `<DIN_COM>`, `<MODEM_DIAL_COM>`, `<MODEM_PROP_COM>` from actual enumeration.",
            "- Complete `prop_key_receipt.template.json`; `PENDING_HARDWARE` blocks positive PREVIEW/ARM/FIRE acceptance.",
            "- Keep live pyro/actuator outputs disconnected; first smoke is LED-only dummy load.",
            "- Run Gemini visual/code gates only from an ignored local key source; rotate any key pasted into chat before production.",
            "",
            "## Blockers",
        ]
    )
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- None detected by this local preflight.")

    return "\n".join(lines) + "\n", blockers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when preflight blockers are present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report, blockers = build_report()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8", newline="\n")
    print(f"wrote first-upload preflight to {out}")
    print(f"blockers: {len(blockers)}")
    return 1 if args.strict and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
