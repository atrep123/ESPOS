#!/usr/bin/env python3
"""Compile and run the off-target (host) C++ unit tests for the M5 prop chain.

Cross-platform sibling of run_host_tests.ps1: auto-discovers
firmware/tests/test_*.cpp, compiles each with a host C++17 compiler and runs
it. Exits non-zero if any test fails to compile or run, so it is safe to wire
into CI or a pre-flash gate.

These tests cover the pure, target-independent logic that is too important to
leave unverified between flashes:
  * shared/core/safety_logic.h -- ARM/STOP/TTL fire authority + replay window
  * shared/protocol/prop_protocol.h palette encode/decode (via test_palette)

Usage:
  python tools/run_host_tests.py            # from the integration root
  python integrations/m5-prop-lora/tools/run_host_tests.py   # from repo root
  python tools/run_host_tests.py --compiler /usr/bin/g++ --keep-binaries

Compiler resolution order: --compiler flag, $CXX, then g++/c++/clang++ on PATH.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "firmware" / "tests"
STUB_DIR = TEST_DIR / "stubs"
OUT_DIR = ROOT / "build" / "hosttests"

CFLAGS = ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2", "-I", str(STUB_DIR)]

EXE_SUFFIX = ".exe" if os.name == "nt" else ""


def discover_tests(test_dir: Path = TEST_DIR) -> list[Path]:
    """Return firmware/tests/test_*.cpp sorted by name (stable run order)."""
    return sorted(test_dir.glob("test_*.cpp"))


def resolve_compiler(explicit: str | None = None) -> str:
    """Resolve the host C++ compiler: explicit flag, $CXX, then PATH candidates."""
    if explicit:
        found = shutil.which(explicit) or (explicit if Path(explicit).exists() else None)
        if not found:
            raise FileNotFoundError(f"Specified compiler not found: {explicit}")
        return found
    env_cxx = os.environ.get("CXX")
    if env_cxx:
        found = shutil.which(env_cxx) or (env_cxx if Path(env_cxx).exists() else None)
        if not found:
            raise FileNotFoundError(f"$CXX compiler not found: {env_cxx}")
        return found
    for candidate in ("g++", "c++", "clang++"):
        found = shutil.which(candidate)
        if found:
            return found
    raise FileNotFoundError(
        "No host C++ compiler found (tried $CXX, g++, c++, clang++). "
        "Install g++, or on Windows: winget install --id BrechtSanders.WinLibs.POSIX.UCRT"
    )


def compile_command(compiler: str, source: Path, out_exe: Path) -> list[str]:
    return [compiler, *CFLAGS, str(source), "-o", str(out_exe)]


def run_all(compiler: str, keep_binaries: bool = False) -> int:
    tests = discover_tests()
    if not tests:
        print(f"ERROR: no test_*.cpp found in {TEST_DIR}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Host test runner")
    print(f"  compiler: {compiler}")
    print(f"  tests:    {len(tests)} file(s) in firmware/tests/")
    print()

    failed: list[str] = []
    for source in tests:
        name = source.stem
        exe = OUT_DIR / (name + EXE_SUFFIX)

        print(f"[{name}] compiling...")
        compile_result = subprocess.run(compile_command(compiler, source, exe))
        if compile_result.returncode != 0:
            print(f"[{name}] COMPILE FAILED")
            failed.append(name)
            continue

        print(f"[{name}] running...")
        run_result = subprocess.run([str(exe)])
        if run_result.returncode != 0:
            print(f"[{name}] TEST FAILED (exit {run_result.returncode})")
            failed.append(name)
        else:
            print(f"[{name}] OK")
        print()

        if not keep_binaries:
            exe.unlink(missing_ok=True)

    if failed:
        print(f"HOST TESTS FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"ALL HOST TESTS PASSED ({len(tests)} file(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--compiler", help="explicit path or name of the C++ compiler")
    parser.add_argument(
        "--keep-binaries",
        action="store_true",
        help="keep build/hosttests binaries after the run",
    )
    args = parser.parse_args(argv)

    try:
        compiler = resolve_compiler(args.compiler)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return run_all(compiler, keep_binaries=args.keep_binaries)


if __name__ == "__main__":
    raise SystemExit(main())
