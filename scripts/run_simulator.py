"""Helper target for launching the simulator via SCons."""

from __future__ import annotations

import os
import subprocess

env = None  # type: ignore

try:
    from SCons.Script import Import  # type: ignore
except ImportError:
    Import = None  # type: ignore
else:
    Import("env")  # type: ignore


def run_simulator(*args, **kwargs):
    """Run the compiled simulator executable."""
    program_path = env.get("PROGPATH") if env else None

    if program_path and os.path.exists(program_path):
        print("\n" + "=" * 70)
        print("Running UI Simulator...")
        print("=" * 70 + "\n")

        try:
            result = subprocess.run([program_path], check=False, shell=False)
            print("\n" + "=" * 70)
            print(f"Simulator exited with code: {result.returncode}")
            print("=" * 70)
        except Exception as exc:  # pragma: no cover - best effort logging
            print(f"Error running simulator: {exc}")
    else:
        print(f"Simulator executable not found at: {program_path}")


if env:
    env.AlwaysBuild(env.Alias("run", env.get("PROGPATH"), run_simulator))
