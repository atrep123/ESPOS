#!/usr/bin/env python3
"""Board/module registry for the ESP32OS embedded workflow.

Single Python entry point over ``boards.json`` (repo-root, the language-agnostic
source of truth). Responsibilities:

* parse + **validate** every board entry against a strict schema (so a
  malformed bulk-fill fails loudly instead of silently shipping a stub),
* expose the registry to the pygame designer's board selector,
* bridge a display-bearing board to ``ui_designer.HARDWARE_PROFILES`` (the
  designer canvas uses the *same* profile keys — no duplicate display data),
* render a deterministic PlatformIO ``[env:*]`` block so each board has a
  real, pio-valid build env.

Honesty contract: a board with ``has_display = False`` carries pins /
peripherals / backend build flags only — the UI designer does not apply to
it, and that is represented explicitly (``display`` is ``None``), never faked
with a placeholder panel.

The schema is intentionally small and self-describing so a Codex agent can
bulk-fill more boards against it; see ``feat_board_registry.md`` for the
spec and ``validate_registry()`` for the enforced rules.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse the designer's display profiles — display-bearing boards reference a
# profile *key* here rather than redefining w/h/depth (single source of truth).
try:
    from ui_designer import HARDWARE_PROFILES
except Exception:  # pragma: no cover - designer import is optional for pio use
    HARDWARE_PROFILES = {}  # type: ignore[assignment]

REGISTRY_PATH = Path(__file__).resolve().parent / "boards.json"

# A board id must also be a legal PlatformIO env name and C-ish token.
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# Markers delimiting the generated block appended to platformio.ini. Anything
# between them is owned by this generator and rewritten wholesale.
PIO_BLOCK_BEGIN = "# >>> espos board_registry generated envs (do not edit by hand) >>>"
PIO_BLOCK_END = "# <<< espos board_registry generated envs <<<"

# Recognized peripheral tokens. Extra tokens are *allowed* (warning only) so
# the registry can grow without code changes, but the common set is checked
# for typos during validation.
KNOWN_PERIPHERALS = {
    "ws2812",
    "lora_sx1262",
    "lora_sx1276",
    "ble",
    "wifi",
    "ir",
    "imu",
    "pmic_axp192",
    "pmic_axp2101",
    "microsd",
    "buzzer",
    "button",
    "rtc",
    "microphone",
    "grove",
    "can",
    "rs485",
}


class RegistryError(ValueError):
    """Raised when boards.json is structurally invalid."""


@dataclass(frozen=True)
class DisplaySpec:
    """Resolved display geometry for a display-bearing board.

    ``w``/``h``/``depth`` mirror the keys used by
    ``ui_designer.HARDWARE_PROFILES`` so the designer canvas matches the panel.
    """

    w: int
    h: int
    depth: int
    driver: str
    bus: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Board:
    """One physical board/module entry (validated)."""

    id: str
    label: str
    platformio_board: str
    platform: str
    mcu: str
    has_display: bool
    display_profile: Optional[str]
    display: Optional[DisplaySpec]
    pins: Dict[str, int]
    peripherals: List[str]
    build_flags: List[str]
    notes: str
    vendor: str = ""

    def env_name(self) -> str:
        """PlatformIO env name for this board."""
        return f"board-{self.id}"


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise RegistryError(msg)


def _coerce_board(raw: Any, idx: int) -> Board:
    """Validate + normalize one raw dict into a :class:`Board`."""
    where = f"boards[{idx}]"
    _require(isinstance(raw, dict), f"{where} must be an object")

    bid = raw.get("id")
    _require(
        isinstance(bid, str) and bool(_ID_RE.match(bid)),
        f"{where}.id must match {_ID_RE.pattern!r} (also a valid pio env id); got {bid!r}",
    )
    where = f"boards[{idx}] ({bid})"

    for key in ("label", "platformio_board", "platform", "mcu"):
        val = raw.get(key)
        _require(
            isinstance(val, str) and val.strip() != "",
            f"{where}.{key} must be a non-empty string",
        )

    has_display = raw.get("has_display")
    _require(isinstance(has_display, bool), f"{where}.has_display must be a bool")

    pins = raw.get("pins", {})
    _require(isinstance(pins, dict), f"{where}.pins must be an object")
    norm_pins: Dict[str, int] = {}
    for pname, pval in pins.items():
        _require(
            isinstance(pname, str) and isinstance(pval, int) and not isinstance(pval, bool),
            f"{where}.pins['{pname}'] must be an int gpio (use -1 for not-connected)",
        )
        norm_pins[pname] = pval

    peripherals = raw.get("peripherals", [])
    _require(
        isinstance(peripherals, list)
        and all(isinstance(p, str) and p for p in peripherals),
        f"{where}.peripherals must be a list of non-empty strings",
    )

    build_flags = raw.get("build_flags", [])
    _require(
        isinstance(build_flags, list)
        and all(isinstance(f, str) and f for f in build_flags),
        f"{where}.build_flags must be a list of non-empty strings",
    )

    notes = raw.get("notes", "")
    _require(isinstance(notes, str), f"{where}.notes must be a string")

    display_profile = raw.get("display_profile")
    raw_display = raw.get("display")
    display: Optional[DisplaySpec] = None

    if has_display:
        _require(
            isinstance(display_profile, str) and display_profile != "",
            f"{where}.display_profile must name a ui_designer.HARDWARE_PROFILES "
            f"key when has_display is true",
        )
        if HARDWARE_PROFILES:
            _require(
                display_profile in HARDWARE_PROFILES,
                f"{where}.display_profile {display_profile!r} is not a known "
                f"HARDWARE_PROFILES key {sorted(HARDWARE_PROFILES)!r}",
            )
        _require(
            isinstance(raw_display, dict),
            f"{where}.display must be an object when has_display is true",
        )
        for key in ("w", "h", "depth"):
            _require(
                isinstance(raw_display.get(key), int)
                and not isinstance(raw_display.get(key), bool)
                and raw_display[key] > 0,
                f"{where}.display.{key} must be a positive int",
            )
        driver = raw_display.get("driver", "")
        _require(
            isinstance(driver, str) and driver != "",
            f"{where}.display.driver must be a non-empty string",
        )
        # Cross-check geometry against the referenced profile (catch mismatched
        # bulk-fill where the panel size disagrees with the designer canvas).
        if HARDWARE_PROFILES and display_profile in HARDWARE_PROFILES:
            prof = HARDWARE_PROFILES[display_profile]
            _require(
                int(prof["width"]) == raw_display["w"]
                and int(prof["height"]) == raw_display["h"],
                f"{where}.display {raw_display['w']}x{raw_display['h']} disagrees "
                f"with profile {display_profile!r} "
                f"{prof['width']}x{prof['height']}",
            )
        extra = {
            k: v
            for k, v in raw_display.items()
            if k not in ("w", "h", "depth", "driver", "bus")
        }
        display = DisplaySpec(
            w=raw_display["w"],
            h=raw_display["h"],
            depth=raw_display["depth"],
            driver=driver,
            bus=str(raw_display.get("bus", "")),
            extra=extra,
        )
    else:
        _require(
            display_profile in (None, ""),
            f"{where}.display_profile must be null/absent when has_display is "
            f"false (non-display module — the UI designer does not apply)",
        )
        _require(
            raw_display in (None, {}),
            f"{where}.display must be null/absent when has_display is false",
        )
        display_profile = None

    return Board(
        id=bid,
        label=raw["label"],
        platformio_board=raw["platformio_board"],
        platform=raw["platform"],
        mcu=raw["mcu"],
        vendor=str(raw.get("vendor", "")),
        has_display=has_display,
        display_profile=display_profile,
        display=display,
        pins=norm_pins,
        peripherals=list(peripherals),
        build_flags=list(build_flags),
        notes=notes,
    )


@dataclass
class BoardRegistry:
    """Loaded, validated collection of boards keyed by id."""

    boards: List[Board]
    schema_version: int = 1

    def __post_init__(self) -> None:
        self._by_id: Dict[str, Board] = {}
        for b in self.boards:
            _require(
                b.id not in self._by_id,
                f"duplicate board id {b.id!r} in registry",
            )
            self._by_id[b.id] = b

    # -- access ---------------------------------------------------------
    def ids(self) -> List[str]:
        return [b.id for b in self.boards]

    def get(self, board_id: str) -> Optional[Board]:
        return self._by_id.get(board_id)

    def display_boards(self) -> List[Board]:
        return [b for b in self.boards if b.has_display]

    def headless_boards(self) -> List[Board]:
        return [b for b in self.boards if not b.has_display]

    def profile_for(self, board_id: str) -> Optional[str]:
        """HARDWARE_PROFILES key for a display board, else ``None``.

        This is the bridge the designer board selector uses to drive the
        existing ``set_hardware_profile`` path — no display data is duplicated.
        """
        b = self.get(board_id)
        return b.display_profile if (b and b.has_display) else None

    # -- platformio codegen --------------------------------------------
    def render_pio_block(self) -> str:
        """Render the full generated ``platformio.ini`` block (no markers)."""
        lines: List[str] = [
            "# AUTO-GENERATED by board_registry.py from boards.json.",
            "# Regenerate: python -m board_registry --write-pio",
            "# One [env:board-<id>] per registry entry; safe to `pio run -e board-<id>`.",
        ]
        for b in self.boards:
            lines.append("")
            disp = (
                f"{b.display.w}x{b.display.h}@{b.display.depth}bpp "
                f"{b.display.driver}"
                if b.display
                else "headless (no display)"
            )
            lines.append(f"# {b.label} — {disp}")
            lines.append(f"[env:{b.env_name()}]")
            lines.append("extends = esp32_base")
            lines.append(f"board = {b.platformio_board}")
            flags = list(b.build_flags)
            if not b.has_display:
                # Defensive: guarantee headless modules never try to bring up a
                # panel even if a flag was omitted from the registry entry.
                if not any("ESPOS_NO_DISPLAY" in f for f in flags):
                    flags.append("-DESPOS_NO_DISPLAY=1")
            if flags:
                lines.append("build_flags =")
                lines.append("    ${esp32_base.build_flags}")
                for fl in flags:
                    lines.append(f"    {fl}")
        return "\n".join(lines) + "\n"

    def write_pio_envs(self, ini_path: Optional[Path] = None) -> bool:
        """Append/replace the generated block in ``platformio.ini``.

        Returns ``True`` if the file content changed. Idempotent: the block is
        delimited by sentinel comments and rewritten wholesale, so existing
        hand-written envs are never touched.
        """
        ini_path = ini_path or (REGISTRY_PATH.parent / "platformio.ini")
        original = ini_path.read_text(encoding="utf-8")
        block = (
            f"\n{PIO_BLOCK_BEGIN}\n"
            f"{self.render_pio_block()}"
            f"{PIO_BLOCK_END}\n"
        )

        begin = original.find(PIO_BLOCK_BEGIN)
        end = original.find(PIO_BLOCK_END)
        if begin != -1 and end != -1:
            # Replace existing block (incl. the leading blank line we added).
            pre = original[:begin].rstrip("\n")
            post = original[end + len(PIO_BLOCK_END):].lstrip("\n")
            new_text = pre + "\n" + block.lstrip("\n")
            if post:
                new_text += "\n" + post
        else:
            new_text = original.rstrip("\n") + "\n" + block

        if new_text == original:
            return False
        ini_path.write_text(new_text, encoding="utf-8")
        return True


def load_registry(path: Optional[Path] = None) -> BoardRegistry:
    """Parse + validate ``boards.json`` into a :class:`BoardRegistry`."""
    p = path or REGISTRY_PATH
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry file not found: {p}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"{p.name} is not valid JSON: {exc}") from exc

    _require(isinstance(raw, dict), "registry root must be an object")
    version = raw.get("$schema_version", 1)
    _require(
        isinstance(version, int) and version >= 1,
        "$schema_version must be a positive int",
    )
    entries = raw.get("boards")
    _require(
        isinstance(entries, list) and len(entries) > 0,
        "registry must have a non-empty 'boards' list",
    )
    boards = [_coerce_board(e, i) for i, e in enumerate(entries)]
    return BoardRegistry(boards=boards, schema_version=version)


def validate_registry(path: Optional[Path] = None) -> List[str]:
    """Validate the registry; return a list of human-readable warnings.

    Raises :class:`RegistryError` on hard schema violations. Warnings are
    non-fatal advisories (e.g. an unrecognized peripheral token — allowed so
    the registry can grow, but surfaced so typos are caught in review).
    """
    reg = load_registry(path)
    warnings: List[str] = []
    for b in reg.boards:
        for per in b.peripherals:
            if per not in KNOWN_PERIPHERALS:
                warnings.append(
                    f"{b.id}: peripheral {per!r} not in KNOWN_PERIPHERALS "
                    f"(allowed, but verify it is not a typo)"
                )
        if b.has_display and b.display is None:  # pragma: no cover - defensive
            warnings.append(f"{b.id}: has_display but no resolved display spec")
    return warnings


def _main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="ESP32OS board registry tool")
    parser.add_argument(
        "--validate", action="store_true", help="validate boards.json and exit"
    )
    parser.add_argument(
        "--write-pio",
        action="store_true",
        help="append/refresh the generated [env:board-*] block in platformio.ini",
    )
    parser.add_argument(
        "--list", action="store_true", help="list registered boards"
    )
    args = parser.parse_args(argv)

    reg = load_registry()
    if args.list or not (args.validate or args.write_pio):
        for b in reg.boards:
            kind = (
                f"display {b.display.w}x{b.display.h} ({b.display_profile})"
                if b.has_display
                else "headless"
            )
            print(f"  {b.id:22s} {b.platformio_board:22s} {kind}")
    if args.validate or not (args.write_pio or args.list):
        warns = validate_registry()
        for w in warns:
            print(f"[WARN] {w}")
        print(f"[OK] {len(reg.boards)} board(s) valid")
    if args.write_pio:
        changed = reg.write_pio_envs()
        print(
            "[OK] platformio.ini "
            + ("updated" if changed else "already up to date")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
