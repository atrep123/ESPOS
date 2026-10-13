"""Bounded Windows native-library tests. No editor/IPC/HW activation.

Uses the existing workspace-owned Job Object helper: assign before command
release; zero descendants and natural exit are required, forced cleanup fails.
The only writes are build output, fresh test fixtures, and report artifacts.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OWNER = Path("C:/Sumilek-git/tabos-core-integration-20261001/tools/overeni_workspace.py")
OWNER_SHA = "097a09c23ee671466f710afd5b077d743b2bbf7a44fdb8366a4eb4a5506cc719"
TOOLCHAIN = Path("C:/Users/atrep/.rustup/toolchains/stable-x86_64-pc-windows-msvc/bin")
MSVC = Path(
    "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207"
)
SDK = Path("C:/Program Files (x86)/Windows Kits/10/Lib/10.0.22621.0")
LLD = TOOLCHAIN.parent / "lib/rustlib/x86_64-pc-windows-msvc/bin/rust-lld.exe"


def source_snapshot():
    paths = [
        ROOT / "Cargo.toml",
        ROOT / "Cargo.lock",
        ROOT / "run_tests.py",
        *sorted((ROOT / "src").glob("*.rs")),
    ]
    result = {}
    for path in paths:
        if path.stat().st_file_attributes & 0x400 or not path.resolve().is_relative_to(ROOT):
            raise RuntimeError("Redirected source input")
        result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    if sys.platform != "win32" or sys.argv[1:]:
        raise RuntimeError("Fixed Windows test entry; no alternate command/fixture")
    if hashlib.sha256(OWNER.read_bytes()).hexdigest() != OWNER_SHA:
        raise RuntimeError("Owned-process helper changed; review before running")
    for path in (ROOT, *ROOT.parents):
        if path.stat().st_file_attributes & 0x400:
            raise RuntimeError("Redirected test/output ancestor")
    command = [
        str(TOOLCHAIN / "cargo.exe"),
        "test",
        "--offline",
        "--locked",
        "--manifest-path",
        str(ROOT / "Cargo.toml"),
        "--jobs",
        "2",
        "--",
        "--test-threads=1",
    ]
    for path in (
        TOOLCHAIN / "cargo.exe",
        TOOLCHAIN / "rustc.exe",
        LLD,
        MSVC / "lib/x64/libcmt.lib",
        SDK / "um/x64/kernel32.lib",
        SDK / "ucrt/x64/ucrt.lib",
    ):
        if not path.is_file():
            raise RuntimeError("Missing reviewed toolchain input: " + str(path))
    reports = ROOT / "target" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    run = reports / ("native-" + uuid.uuid4().hex)
    run.mkdir()
    temp = run / "temp"
    temp.mkdir()
    env = {
        key: os.environ[key]
        for key in ("SystemRoot", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA")
        if key in os.environ
    }
    env.update(
        PATH=os.pathsep.join(
            (
                str(TOOLCHAIN),
                str(MSVC / "bin/Hostx64/x64"),
                str(Path(env["SystemRoot"]) / "System32"),
            )
        ),
        LIB=os.pathsep.join((str(MSVC / "lib/x64"), str(SDK / "um/x64"), str(SDK / "ucrt/x64"))),
        CARGO_HOME="C:/Users/atrep/.cargo",
        RUSTC=str(TOOLCHAIN / "rustc.exe"),
        CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER=str(LLD),
        RUSTFLAGS="-C linker-flavor=lld-link",
        TEMP=str(temp),
        TMP=str(temp),
        CARGO_TERM_COLOR="never",
    )
    spec = importlib.util.spec_from_file_location("_espos_owned_process", OWNER)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    before = source_snapshot()
    receipt = {}
    code = None
    error = None
    try:
        code = owner.run_process(
            command,
            cwd=ROOT,
            env=env,
            timeout=180,
            log=run / "stdout.log",
            stderr_log=run / "stderr.log",
            containment_receipt=receipt,
            containment_log=run / "job.json",
            natural_settle_seconds=1,
        )
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    bounded = all(
        p.stat().st_size <= 1024 * 1024
        for p in (run / "stdout.log", run / "stderr.log")
        if p.exists()
    )
    after = source_snapshot()
    unchanged = before == after
    success = (
        error is None
        and code == 0
        and bounded
        and unchanged
        and receipt.get("root_exit") == 0
        and receipt.get("natural_descendant_zero") is True
        and receipt.get("forced_cleanup") is False
        and receipt.get("accounting_status") == "confirmed"
    )
    result = {
        "success": success,
        "returnedExit": code,
        "error": error,
        "job": receipt,
        "boundedLogs": bounded,
        "sourcesUnchanged": unchanged,
        "sourceSnapshot": before,
        "linker": "bundled-rust-lld (lld-link)",
        "evidence": str(run),
        "mode": "NATIVE_LIBRARY_FIXTURES_NOT_EDITOR_GUI",
    }
    (run / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), flush=True)
    return 0 if success else (code if code not in (None, 0) else 125)


if __name__ == "__main__":
    raise SystemExit(main())
