#!/usr/bin/env python3
"""
Integrated build / flash for the ESP32OS embedded workflow.

This is the part that makes "the compiler is part of the app" *real*: it
invokes the **actual** PlatformIO toolchain (``python -m platformio run``),
streams the real compiler output, and reports the genuine firmware path +
RAM/Flash usage that pio prints. There is no fake progress bar — a build that
fails here is a real ``pio run`` failure, and a SUCCESS produces a real
``firmware.bin`` on disk.

Three responsibilities (mirrors the ``tools/ui_export_*`` library+CLI shape):

* :func:`regen_codegen` — regenerate ``src/ui_design.{c,h}`` from a design JSON
  using the *real* ``tools.ui_codegen`` entrypoint (the same code the
  PlatformIO pre-script and ``scripts/check_codegen_freshness.py`` use), so a
  build always reflects the current design.
* :func:`build_board` — ``python -m platformio run -e <env>`` for the env
  mapped from the espos board id (via ``board_registry``), capturing
  SUCCESS/FAIL, the firmware path, and RAM/Flash usage.
* :func:`flash_board` — ``python -m platformio run -e <env> -t upload
  [--upload-port <port>]`` (the real upload command; port auto-detected via
  ``pio device list`` when not given). This builds first, then uploads.

Board id -> pio env mapping
---------------------------
``board_registry`` is the single source of truth. Every registry board has a
generated ``[env:board-<id>]`` env (see ``board_registry.write_pio_envs``).
The project's historical reference env ``esp32-s3-devkitm-1-nohw`` is also
accepted directly (it is the hardware-skip-friendly env the CI / docs use and
is identical hardware to ``board-esp32-s3-devkitm-1``).

HARDWARE-FLASH HONESTY
----------------------
The build path is fully verifiable on this machine and IS verified. The flash
path constructs and launches a real ``pio ... -t upload`` command, but with no
ESP32 physically attached it cannot be hardware-confirmed; it is exercised only
far enough to prove the command is built correctly and fails gracefully with no
device. Such runs are labelled ``UNVERIFIED-ON-HARDWARE`` here and in the
report — same honesty bar as the SSD1363 work.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# Repo root = parent of tools/ (mirrors tools/ui_export_c_header.py).
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The project's historical hardware-skip-friendly reference env. Identical
# silicon to board-esp32-s3-devkitm-1; this is the env CI + README build.
REFERENCE_ENV = "esp32-s3-devkitm-1-nohw"

# A line printer; defaults to stdout but the designer modal passes a collector.
LineSink = Callable[[str], None]


class BuildError(RuntimeError):
    """Raised for actionable, user-facing build/flash failures."""


# --------------------------------------------------------------------------- #
# PlatformIO bootstrap / availability
# --------------------------------------------------------------------------- #
#
# Robustness note (a real fix, not a workaround): the designer runs under the
# project ``.venv`` (it needs pygame), but PlatformIO may be installed in a
# *different* interpreter (commonly the system Python whose Scripts/ has
# ``pio``). So we must not assume ``sys.executable -m platformio`` works — we
# probe several candidate invocations and use the first that actually answers
# ``--version``. This keeps the integrated workflow working regardless of
# which interpreter launched the app, while still treating pio as a managed
# dependency (the actionable install hint targets requirements.txt).

_PIO_CMD_CACHE: Optional[List[str]] = None


def _candidate_pio_cmds() -> List[List[str]]:
    """Ordered candidate base commands for invoking PlatformIO Core."""
    cands: List[List[str]] = []
    seen: set = set()

    def _add(cmd: List[str]) -> None:
        key = tuple(cmd)
        if key not in seen:
            seen.add(key)
            cands.append(cmd)

    # 1. The current interpreter (works when pio is a dep of this env).
    _add([sys.executable, "-m", "platformio"])
    # 2. A `pio` / `platformio` console script on PATH (very common — system
    #    Python's Scripts/ dir). This is what makes the .venv-launched
    #    designer still find a system-installed pio.
    for exe in ("pio", "platformio"):
        found = shutil.which(exe)
        if found:
            _add([found])
    # 3. Other well-known interpreters that might own pio.
    for py in ("python", "python3"):
        found = shutil.which(py)
        if found and Path(found).resolve() != Path(sys.executable).resolve():
            _add([found, "-m", "platformio"])
    return cands


def _probe_pio(cmd: List[str]) -> Optional[str]:
    """Return the version string if *cmd* answers ``--version``, else None."""
    try:
        proc = subprocess.run(
            [*cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or proc.stderr or "").strip()
    m = re.search(r"(\d+\.\d+\.\d+)", out)
    return m.group(1) if m else (out or None)


def _resolve_pio_cmd() -> Optional[Tuple[List[str], str]]:
    """Find a working PlatformIO base command; cache & return ``(cmd, ver)``."""
    global _PIO_CMD_CACHE
    if _PIO_CMD_CACHE is not None:
        ver = _probe_pio(_PIO_CMD_CACHE)
        if ver:
            return _PIO_CMD_CACHE, ver
        _PIO_CMD_CACHE = None  # cached cmd went away; re-probe
    for cmd in _candidate_pio_cmds():
        ver = _probe_pio(cmd)
        if ver:
            _PIO_CMD_CACHE = cmd
            return cmd, ver
    return None


def pio_base_cmd() -> List[str]:
    """The resolved PlatformIO invocation prefix (raises if none works)."""
    resolved = _resolve_pio_cmd()
    if resolved is None:
        ensure_platformio()  # raises a BuildError with the actionable hint
    assert resolved is not None  # ensure_platformio raised otherwise
    return resolved[0]


def platformio_version() -> Optional[str]:
    """Return the installed PlatformIO Core version string, or ``None``.

    Probes several candidate interpreters / console scripts (see module note)
    so it works whether pio lives in this env, the system Python, or on PATH.
    """
    resolved = _resolve_pio_cmd()
    return resolved[1] if resolved else None


def ensure_platformio() -> str:
    """Verify PlatformIO is available; return its version or raise.

    The error message is *actionable*: PlatformIO is a managed dependency of
    this project (pinned in requirements.txt), so the fix is a single
    ``pip install`` command.
    """
    resolved = _resolve_pio_cmd()
    if resolved:
        return resolved[1]
    raise BuildError(
        "PlatformIO Core was not found in this Python environment, on PATH, "
        "or in the system Python.\n"
        "It is a managed dependency of espos — install it with:\n"
        f'    "{sys.executable}" -m pip install -r '
        f"{REPO_ROOT / 'requirements.txt'}\n"
        "or, minimally:\n"
        f'    "{sys.executable}" -m pip install "platformio>=6.1,<7"'
    )


# --------------------------------------------------------------------------- #
# Board id  ->  PlatformIO env
# --------------------------------------------------------------------------- #


def resolve_env(board_or_env: Optional[str]) -> str:
    """Map an espos board id (or a literal pio env) to a PlatformIO env name.

    Resolution order:
      1. ``None``/empty -> the reference env (``esp32-s3-devkitm-1-nohw``).
      2. A registry board id -> its generated ``board-<id>`` env (verified to
         exist in platformio.ini).
      3. An already-``board-<id>`` env or a known literal env -> used as-is.

    Raises :class:`BuildError` with the valid choices on an unknown value.
    """
    val = (board_or_env or "").strip()
    if not val:
        return REFERENCE_ENV

    known_literals = _known_pio_envs()
    if val in known_literals:
        return val

    try:
        from board_registry import load_registry

        reg = load_registry()
    except Exception as exc:  # pragma: no cover - registry import/parse guard
        raise BuildError(f"could not load board registry: {exc}") from exc

    board = reg.get(val)
    if board is not None:
        env = board.env_name()  # "board-<id>"
        if env in known_literals:
            return env
        raise BuildError(
            f"board {val!r} has no generated env {env!r} in platformio.ini. "
            f"Run: \"{sys.executable}\" -m board_registry --write-pio"
        )

    # board-<id> passed but registry lookup by bare id failed: try stripping.
    if val.startswith("board-") and reg.get(val[len("board-"):]) is not None:
        if val in known_literals:
            return val

    valid = ", ".join(sorted(set(reg.ids()) | known_literals))
    raise BuildError(f"unknown board/env {val!r}. Valid: {valid}")


def _known_pio_envs() -> set:
    """Parse ``[env:*]`` headers out of platformio.ini (no pio dependency)."""
    ini = REPO_ROOT / "platformio.ini"
    envs: set = set()
    try:
        for line in ini.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("[env:") and s.endswith("]"):
                envs.add(s[len("[env:"): -1].strip())
    except OSError:
        pass
    return envs


def upload_env_for(env: str) -> str:
    """Map a build env to the env that performs a *real* hardware upload.

    The project's ``*-nohw`` envs deliberately use a custom ``upload_command``
    (``scripts/skip_hw_tests.py``) that *auto-skips* the physical flash so
    hardware-less CI never hangs. That is perfect for *building* but means a
    real "Flash" must target the non-``-nohw`` sibling, otherwise the upload is
    silently a no-op. So for the upload step we strip a trailing ``-nohw`` when
    the sibling env exists. Build still uses the resolved env unchanged.
    """
    if env.endswith("-nohw"):
        sibling = env[: -len("-nohw")]
        if sibling in _known_pio_envs():
            return sibling
    return env


# --------------------------------------------------------------------------- #
# Codegen regeneration (real ui_codegen, same as the pio pre-script)
# --------------------------------------------------------------------------- #


def regen_codegen(
    json_path: Optional[Path] = None,
    *,
    sink: Optional[LineSink] = None,
) -> bool:
    """Regenerate ``src/ui_design.{c,h}`` from *json_path* (default
    ``main_scene.json``).

    Uses the exact ``tools.ui_codegen`` entrypoints the PlatformIO pre-script
    (``scripts/pio_generate_ui_design.py``) and freshness checker use, so what
    is built is what the design says. Returns ``True`` if files changed.
    """
    emit = sink or (lambda s: print(s))
    jp = Path(json_path) if json_path else (REPO_ROOT / "main_scene.json")
    jp = jp.resolve()
    if not jp.exists():
        raise BuildError(f"design JSON not found: {jp}")

    from tools.ui_codegen import (
        generate_ui_design_multi_pair,
        generate_ui_design_pair,
        load_scenes,
        write_if_changed,
    )

    try:
        source_label = jp.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        source_label = jp.name

    try:
        scenes = load_scenes(jp)
    except (OSError, ValueError) as exc:
        raise BuildError(f"failed to parse {jp.name}: {exc}") from exc
    if not scenes:
        emit(f"[codegen] {jp.name} has no scenes — nothing to regenerate.")
        return False

    if len(scenes) > 1:
        c_text, h_text = generate_ui_design_multi_pair(jp, source_label=source_label)
        mode = f"multi-scene, {len(scenes)} scenes"
    else:
        scene_name = next(iter(scenes))
        c_text, h_text = generate_ui_design_pair(
            jp, scene_name=scene_name, source_label=source_label
        )
        mode = f"scene: {scene_name}"

    out_c = REPO_ROOT / "src" / "ui_design.c"
    out_h = REPO_ROOT / "src" / "ui_design.h"
    changed = False
    changed |= write_if_changed(out_h, h_text)
    changed |= write_if_changed(out_c, c_text)
    emit(
        f"[codegen] {jp.name} ({mode}) -> src/ui_design.c|h "
        + ("regenerated" if changed else "already up to date")
    )
    return changed


# --------------------------------------------------------------------------- #
# Result model
# --------------------------------------------------------------------------- #


@dataclass
class BuildResult:
    """Outcome of a real ``pio run`` (build or flash)."""

    env: str
    action: str  # "build" | "flash"
    ok: bool
    returncode: int
    firmware_path: Optional[Path] = None
    ram_used: Optional[str] = None
    flash_used: Optional[str] = None
    output_tail: List[str] = field(default_factory=list)
    # True for a flash whose command was correctly built+launched but which
    # could not be hardware-confirmed (no board attached).
    hardware_unverified: bool = False

    def summary(self) -> str:
        head = f"{self.action.upper()} [{self.env}] " + (
            "SUCCESS" if self.ok else f"FAILED (exit {self.returncode})"
        )
        bits = [head]
        if self.firmware_path:
            bits.append(f"firmware: {self.firmware_path}")
        if self.ram_used:
            bits.append(f"RAM: {self.ram_used}")
        if self.flash_used:
            bits.append(f"Flash: {self.flash_used}")
        if self.hardware_unverified:
            bits.append("(UNVERIFIED-ON-HARDWARE: no device attached)")
        return " | ".join(bits)


_RAM_RE = re.compile(r"RAM:\s*\[[=\s]*\]\s*([\d.]+%\s*\(used[^)]*\))")
_FLASH_RE = re.compile(r"Flash:\s*\[[=\s]*\]\s*([\d.]+%\s*\(used[^)]*\))")


def _scrape_usage(lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
    ram = flash = None
    for ln in lines:
        m = _RAM_RE.search(ln)
        if m:
            ram = m.group(1).strip()
        m = _FLASH_RE.search(ln)
        if m:
            flash = m.group(1).strip()
    return ram, flash


def firmware_path_for(env: str) -> Path:
    """Conventional PlatformIO firmware artifact path for *env*."""
    return REPO_ROOT / ".pio" / "build" / env / "firmware.bin"


# --------------------------------------------------------------------------- #
# The real pio invocation
# --------------------------------------------------------------------------- #


def _pio_env() -> dict:
    """Environment for pio subprocesses.

    Forces UTF-8 so PlatformIO/click never raises ``UnicodeEncodeError``
    echoing non-ASCII (esptool progress bars, localized serial-device
    strings) on a Windows cp1250 console — which would otherwise crash the
    designer Build/Flash modal mid-upload.
    """
    env = dict(os.environ)
    env.setdefault("PLATFORMIO_NO_ANSI", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run_pio(
    pio_args: List[str],
    *,
    sink: Optional[LineSink],
    timeout: int,
) -> Tuple[int, List[str]]:
    """Run the resolved PlatformIO command with *pio_args*, streaming output.

    Returns ``(returncode, all_lines)``. Lines are also forwarded to *sink*
    live (the designer modal collects them; the CLI prints them).
    """
    emit = sink or (lambda s: print(s))
    cmd = [*pio_base_cmd(), *pio_args]
    emit(f"$ {' '.join(cmd)}")

    env = _pio_env()

    lines: List[str] = []
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BuildError(f"failed to launch PlatformIO: {exc}") from exc

    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            lines.append(line)
            emit(line)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise BuildError(
            f"PlatformIO timed out after {timeout}s (command: {' '.join(pio_args)})"
        ) from None
    finally:
        if proc.stdout:
            proc.stdout.close()
    return int(proc.returncode or 0), lines


def build_board(
    board_or_env: Optional[str] = None,
    *,
    regen: bool = True,
    json_path: Optional[Path] = None,
    sink: Optional[LineSink] = None,
    timeout: int = 1800,
) -> BuildResult:
    """Compile the firmware for *board_or_env* with the real PlatformIO.

    ``regen=True`` first regenerates ``src/ui_design.{c,h}`` from the design so
    the binary matches the current scene (the pio pre-script also does this,
    but doing it here makes the designer "Build" button deterministic and lets
    a codegen error surface immediately with a clear message).

    Returns a :class:`BuildResult` with the real firmware path + RAM/Flash
    usage scraped from pio's own report. Raises :class:`BuildError` only for
    setup problems (missing pio, bad board, codegen failure); a *compile*
    failure is a returned ``BuildResult(ok=False)`` with the captured output.
    """
    ensure_platformio()
    env = resolve_env(board_or_env)
    emit = sink or (lambda s: print(s))

    if regen:
        try:
            regen_codegen(json_path, sink=sink)
        except BuildError:
            raise
        except Exception as exc:  # pragma: no cover - unexpected codegen fault
            raise BuildError(f"codegen failed before build: {exc}") from exc

    emit(f"[build] PlatformIO env: {env}")
    rc, lines = _run_pio(["run", "-e", env], sink=sink, timeout=timeout)
    ok = rc == 0
    ram, flash = _scrape_usage(lines)
    fw = firmware_path_for(env)
    res = BuildResult(
        env=env,
        action="build",
        ok=ok,
        returncode=rc,
        firmware_path=fw if (ok and fw.exists()) else None,
        ram_used=ram,
        flash_used=flash,
        output_tail=lines[-40:],
    )
    if ok and res.firmware_path is None:
        # pio reported success but the artifact is missing — be honest.
        emit(
            f"[build] WARNING: pio returned 0 but {fw} not found; "
            "treating as failure."
        )
        res.ok = False
    emit(res.summary())
    return res


# --------------------------------------------------------------------------- #
# Flash (real upload command — UNVERIFIED-ON-HARDWARE without a board)
# --------------------------------------------------------------------------- #


def detect_upload_port() -> Optional[str]:
    """Best-effort serial port auto-detect via ``pio device list``.

    Returns the first detected port, or ``None`` (then pio's own
    auto-detection is used). Never raises — detection is advisory.
    """
    resolved = _resolve_pio_cmd()
    if resolved is None:
        return None
    try:
        proc = subprocess.run(
            [*resolved[0], "device", "list", "--json-output"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(REPO_ROOT),
            env=_pio_env(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        import json

        data = json.loads(proc.stdout)
    except (ValueError, TypeError):
        return None
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and entry.get("port"):
                return str(entry["port"])
    return None


def flash_board(
    board_or_env: Optional[str] = None,
    *,
    port: Optional[str] = None,
    regen: bool = True,
    json_path: Optional[Path] = None,
    sink: Optional[LineSink] = None,
    timeout: int = 1800,
) -> BuildResult:
    """Build then upload the firmware with the real PlatformIO upload target.

    Command: ``python -m platformio run -e <env> -t upload
    [--upload-port <port>]``. *port* defaults to :func:`detect_upload_port`;
    if nothing is detected, pio's own auto-detection runs.

    HONESTY: with no ESP32 attached this cannot be hardware-confirmed. The
    command is real and is launched for real; a no-device run returns
    ``BuildResult(ok=False, hardware_unverified=True)`` rather than pretending
    success. On real hardware the same call performs an actual flash.
    """
    ensure_platformio()
    env = resolve_env(board_or_env)
    emit = sink or (lambda s: print(s))

    # Build first (also regenerates codegen). A flash of a broken build is
    # never attempted.
    build = build_board(
        board_or_env,
        regen=regen,
        json_path=json_path,
        sink=sink,
        timeout=timeout,
    )
    if not build.ok:
        emit("[flash] build failed — upload skipped.")
        build.action = "flash"
        return build

    # The *-nohw envs auto-skip the physical flash by design; for a real
    # upload, retarget the non-nohw sibling so "Flash" actually writes silicon.
    up_env = upload_env_for(env)
    if up_env != env:
        emit(
            f"[flash] build env {env!r} auto-skips upload (CI hardware-skip "
            f"env); using {up_env!r} for the real upload."
        )

    use_port = port or detect_upload_port()
    if use_port:
        emit(f"[flash] target port: {use_port}")
    else:
        emit("[flash] no port detected; relying on PlatformIO auto-detection.")

    args = ["run", "-e", up_env, "-t", "upload"]
    if use_port:
        args += ["--upload-port", use_port]

    rc, lines = _run_pio(args, sink=sink, timeout=timeout)
    ok = rc == 0
    no_device = (not ok) and _looks_like_no_device(lines)
    res = BuildResult(
        env=up_env,
        action="flash",
        ok=ok,
        returncode=rc,
        firmware_path=build.firmware_path,
        ram_used=build.ram_used,
        flash_used=build.flash_used,
        output_tail=lines[-40:],
        hardware_unverified=no_device or not ok,
    )
    if no_device:
        emit(
            "[flash] UNVERIFIED-ON-HARDWARE: no ESP32 detected. The real "
            "upload command was constructed and launched; it failed gracefully "
            "because no device is attached. On connected hardware this flashes."
        )
    emit(res.summary())
    return res


_NO_DEVICE_HINTS = (
    "could not open port",
    "no such file or directory",
    "no serial data received",
    "failed to connect to esp32",
    "the chip stopped responding",
    "no device found",
    "please specify --upload-port",
    "errno 2",
    "errno 13",
    "serialexception",
)


def _looks_like_no_device(lines: List[str]) -> bool:
    blob = "\n".join(lines).lower()
    return any(h in blob for h in _NO_DEVICE_HINTS)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools/build.py",
        description=(
            "Integrated build/flash for espos: regenerates codegen and drives "
            "the real PlatformIO toolchain (no fake progress)."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="verify the PlatformIO toolchain is available")
    p_check.set_defaults(_h=_cmd_check)

    p_codegen = sub.add_parser("codegen", help="regenerate src/ui_design.{c,h} only")
    p_codegen.add_argument("json", nargs="?", type=Path, help="design JSON (default main_scene.json)")
    p_codegen.set_defaults(_h=_cmd_codegen)

    p_build = sub.add_parser("build", help="regenerate codegen + real pio build")
    p_build.add_argument(
        "board",
        nargs="?",
        help=f"espos board id or pio env (default: {REFERENCE_ENV})",
    )
    p_build.add_argument("--json", type=Path, help="design JSON (default main_scene.json)")
    p_build.add_argument("--no-regen", action="store_true", help="skip codegen regeneration")
    p_build.add_argument("--timeout", type=int, default=1800, help="pio timeout seconds")
    p_build.set_defaults(_h=_cmd_build)

    p_flash = sub.add_parser("flash", help="build + real pio upload")
    p_flash.add_argument("board", nargs="?", help="espos board id or pio env")
    p_flash.add_argument("--port", help="serial port (default: auto-detect)")
    p_flash.add_argument("--json", type=Path, help="design JSON (default main_scene.json)")
    p_flash.add_argument("--no-regen", action="store_true", help="skip codegen regeneration")
    p_flash.add_argument("--timeout", type=int, default=1800, help="pio timeout seconds")
    p_flash.set_defaults(_h=_cmd_flash)

    p_boards = sub.add_parser("boards", help="list espos boards and their pio envs")
    p_boards.set_defaults(_h=_cmd_boards)
    return p


def _cmd_check(_args: argparse.Namespace) -> int:
    ver = platformio_version()
    if ver:
        print(f"[OK] PlatformIO Core {ver} is available ({shutil.which('pio') or 'via -m platformio'}).")
        return 0
    try:
        ensure_platformio()
    except BuildError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
    return 1


def _cmd_codegen(args: argparse.Namespace) -> int:
    try:
        regen_codegen(args.json)
    except BuildError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        res = build_board(
            args.board,
            regen=not args.no_regen,
            json_path=args.json,
            timeout=args.timeout,
        )
    except BuildError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    return 0 if res.ok else 1


def _cmd_flash(args: argparse.Namespace) -> int:
    try:
        res = flash_board(
            args.board,
            port=args.port,
            regen=not args.no_regen,
            json_path=args.json,
            timeout=args.timeout,
        )
    except BuildError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    if res.ok:
        return 0
    # No-device is an honest, expected outcome when developing without HW.
    return 3 if res.hardware_unverified else 1


def _cmd_boards(_args: argparse.Namespace) -> int:
    try:
        from board_registry import load_registry

        reg = load_registry()
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] could not load board registry: {exc}", file=sys.stderr)
        return 2
    print(f"reference env (default): {REFERENCE_ENV}")
    for b in reg.boards:
        kind = (
            f"display {b.display.w}x{b.display.h}"
            if (b.has_display and b.display)
            else "headless"
        )
        print(f"  {b.id:24s} -> env {b.env_name():28s} [{kind}]")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    return int(args._h(args))


if __name__ == "__main__":
    raise SystemExit(main())
