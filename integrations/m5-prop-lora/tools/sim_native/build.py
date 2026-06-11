from __future__ import annotations

import subprocess
import sys
import os
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DLL = HERE / "protocol_abi.dll"


def main() -> int:
    cache_root = Path.home() / ".codex" / "memories" / "zig-cache-sim-native"
    (cache_root / "global").mkdir(parents=True, exist_ok=True)
    (cache_root / "local").mkdir(parents=True, exist_ok=True)
    build_dll = cache_root / "protocol_abi_build.dll"

    cmd = [
        sys.executable,
        "-m",
        "ziglang",
        "c++",
        "-shared",
        "-O2",
        "-std=c++17",
        "-Wno-nullability-completeness",
        "-I",
        "shared/protocol",
        "-I",
        "tools/sim_native/shim",
        "-x",
        "c++",
        "tools/sim_native/protocol_abi.cpp",
        "tools/sim_native/sha256.c",
        "tools/sim_native/md_shim.c",
        "-o",
        str(build_dll),
    ]
    env = os.environ.copy()
    env.setdefault("ZIG_GLOBAL_CACHE_DIR", str(cache_root / "global"))
    env.setdefault("ZIG_LOCAL_CACHE_DIR", str(cache_root / "local"))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=env)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.stdout:
            print(result.stdout, end="", file=sys.stderr)
        return result.returncode
    shutil.copy2(build_dll, DLL)
    print(f"OK {DLL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
