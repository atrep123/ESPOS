"""Verify one explicitly supplied, existing owned Windows backend executable.

CLI: python tools/verify_frozen_desktop_backend.py --exe ABSOLUTE_STAGED_EXE
No build/install/discovery, Python fallback, shell, GUI or project file operation.
Seven sequential owned children at most, with no retries. Each exchange has one
12-second write/process/drain deadline and a combined 1 MiB stdout/stderr cap.
Private exchange helpers also serve explicit TEST_ONLY Python fixtures; that
test evidence is never reported as a frozen executable verification.
"""

from __future__ import annotations

import base64
import binascii
import errno
import hashlib
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

MAX_FRAME_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024
DEADLINE_SECONDS = 12
TERMINATION_GRACE_SECONDS = 0.2
ROLE = "codegraph-bundled"
_STAGED_NAMES = {
    "espos_codegraph_backend.exe",
    "espos_codegraph_backend-x86_64-pc-windows-msvc.exe",
}


class VerificationError(ValueError):
    """Fixed diagnostic code only: never raw child output, paths or OS errors."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise VerificationError(code)


def _run_owned_child(command, payload, *, cwd):
    _require(isinstance(payload, bytes) and len(payload) <= MAX_FRAME_BYTES, "request-limit")
    options = {}
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        options = {"startupinfo": startup, "creationflags": subprocess.CREATE_NO_WINDOW}
    deadline = time.monotonic() + DEADLINE_SECONDS
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            bufsize=0,
            shell=False,
            **options,
        )
    except OSError:
        raise VerificationError("launch-failed") from None
    streams = [process.stdin, process.stdout, process.stderr]
    readers = {process.stdout: 0, process.stderr: 1}
    buffers = [bytearray(), bytearray()]
    offset = 0
    try:
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        while readers or process.poll() is None:
            remaining = deadline - time.monotonic()
            _require(remaining > 0, "child-deadline")
            # Hold stdin open even after the complete line, as Tauri does.
            writable = [] if process.stdin.closed or offset == len(payload) else [process.stdin]
            if os.name == "nt":
                ready_read, ready_write = list(readers), writable
            else:
                ready_read, ready_write, _ = select.select(
                    list(readers), writable, [], min(remaining, 0.01)
                )
            for stream in ready_write:
                try:
                    offset += os.write(stream.fileno(), payload[offset : offset + 4096])
                except BlockingIOError:
                    pass
                except BrokenPipeError:
                    stream.close()
                except OSError as exc:
                    if os.name != "nt" or exc.errno != errno.EINVAL:
                        raise
                    # Windows may close a pipe just before process exit is
                    # signalled. Only that owned child's confirmed exit permits
                    # EINVAL; no live-child error is interpreted as EOF.
                    process.wait(timeout=min(TERMINATION_GRACE_SECONDS, remaining))
                    stream.close()
            for stream in ready_read:
                try:
                    chunk = os.read(stream.fileno(), 8192)
                except BlockingIOError:
                    continue
                if not chunk:
                    del readers[stream]
                    stream.close()
                else:
                    _require(sum(map(len, buffers)) + len(chunk) <= MAX_FRAME_BYTES, "output-limit")
                    buffers[readers[stream]].extend(chunk)
            if os.name == "nt":
                time.sleep(min(0.005, remaining))
        _require(offset == len(payload), "incomplete-request")
        return process.returncode, bytes(buffers[0]), bytes(buffers[1])
    except (OSError, subprocess.TimeoutExpired):
        raise VerificationError("child-io-failed") from None
    finally:
        # No process-tree kill, detached reader threads or repeated child retry.
        # Onedir backend has no extraction subprocess. Reap only our Popen child.
        try:
            if process.poll() is None:
                process.kill()
            for stream in streams:
                stream.close()
            process.wait(timeout=TERMINATION_GRACE_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            raise VerificationError("child-cleanup-failed") from None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "repeated-reply-key")
        result[key] = value
    return result


def _nonfinite(value):
    raise VerificationError("nonfinite-reply")


def _decode_reply(result, *, success):
    code, stdout, stderr = result
    _require(not stderr, "unexpected-stderr")
    _require(
        len(stdout) <= MAX_FRAME_BYTES and stdout.endswith(b"\n") and stdout.count(b"\n") == 1,
        "reply-frame",
    )
    try:
        response = json.loads(
            stdout.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_nonfinite
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, VerificationError):
            raise
        raise VerificationError("invalid-reply-json") from None
    _require(isinstance(response, dict) and type(response.get("ok")) is bool, "reply-envelope")
    _require(
        response["ok"] is success and (code == 0 if success else code not in (0, None)),
        "exit-or-result-mismatch",
    )
    if success:
        graph = response.get("graph")
        _require(isinstance(graph, dict), "missing-graph")
        raw = _source(response)
        _require(
            graph.get("sourceHash") == hashlib.sha256(raw).hexdigest()
            and graph.get("byteLength") == len(raw)
            and graph.get("schemaVersion") == 1
            and graph.get("catalogVersion") == "cpp-cst-subset-1",
            "source-identity",
        )
        _require(
            isinstance(graph.get("nodes"), list) and isinstance(graph.get("edges"), list),
            "graph-envelope",
        )
        diagnostic_sets = [graph.get("diagnostics")]
    else:
        diagnostic_sets = [response.get("diagnostics")]
        _require("sourceBase64" not in response and "graph" not in response, "partial-failure")
    for diagnostics in diagnostic_sets:
        _require(isinstance(diagnostics, list) and (success or bool(diagnostics)), "diagnostics")
        _require(
            all(
                isinstance(item, dict)
                and isinstance(item.get("message"), str)
                and isinstance(item.get("code"), str)
                for item in diagnostics
            ),
            "diagnostics",
        )
        if success:
            _require(not any(d.get("severity") == "error" for d in diagnostics), "graph-error")
    return response


def _source(response):
    value = response.get("sourceBase64")
    _require(
        isinstance(value, str) and len(value) <= 4 * ((MAX_SOURCE_BYTES + 2) // 3), "source-limit"
    )
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise VerificationError("invalid-source-base64") from None
    _require(
        len(raw) <= MAX_SOURCE_BYTES and base64.b64encode(raw).decode("ascii") == value,
        "source-limit-or-encoding",
    )
    return raw


def _frame(request):
    payload = (
        json.dumps(request, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()
        + b"\n"
    )
    _require(len(payload) <= MAX_FRAME_BYTES, "request-limit")
    return payload


def _transaction(request, response, operation, **extra):
    return {
        **request,
        "operation": operation,
        "sourceBase64": response["sourceBase64"],
        "graph": response["graph"],
        "expectedSourceHash": response["graph"]["sourceHash"],
        **extra,
    }


def _opaque(response):
    raw = _source(response)
    result = {}
    for node in response["graph"]["nodes"]:
        if node.get("kind") == "opaque":
            span = node["sourceSpan"]
            start, end = span["startByte"], span["endByte"]
            _require(
                type(start) is int and type(end) is int and 0 <= start <= end <= len(raw),
                "opaque-span",
            )
            result[node["id"]] = raw[start:end]
    return result


def _verify_cases(exchange):
    """Independent byte/identity/SDK observations, never a local parser fallback."""
    checks = []

    def good(name, request):
        response = _decode_reply(exchange(_frame(request), (ROLE,)), success=True)
        checks.append(name)
        return response

    prefix = (
        b"\xef\xbb\xbf"
        + "// přesně 🚦\r\n".encode()
        + b"template<class T>T keep(T x){return x;}\r\n"
    )
    suffix = b"\r\nauto opaque=[](){return keep(4);};\r\n"
    raw = prefix + b"void step(){\r\n int value=1;\r\n}" + suffix
    request = {
        "operation": "parse",
        "sourceBase64": base64.b64encode(raw).decode("ascii"),
        "entries": ["step"],
    }
    parsed = good("parse", request)
    _require(_source(parsed) == raw, "parse-byte-preservation")
    node = next(n for n in parsed["graph"]["nodes"] if n.get("variable") == "value")
    slot = next(s for s in node["editSlots"] if s["kind"] == "literal")
    edited = good(
        "edit",
        _transaction(
            request,
            parsed,
            "edit",
            edits=[{"nodeId": node["id"], "slotId": slot["id"], "replacement": "27"}],
        ),
    )
    _require(_source(edited) == raw.replace(b"value=1", b"value=27"), "edit-byte-preservation")
    _require(_opaque(edited) == _opaque(parsed), "edit-opaque-preservation")
    _require(
        [n["id"] for n in edited["graph"]["nodes"]] == [n["id"] for n in parsed["graph"]["nodes"]],
        "edit-node-identity",
    )

    sdk_raw = prefix + b"void step(lv_obj_t* label){\r\n}" + suffix
    sdk = {
        "operation": "parse",
        "sourceBase64": base64.b64encode(sdk_raw).decode("ascii"),
        "entries": ["step"],
        "sdkProfile": "tabos-sdk-minimal-1",
        "bindings": {
            "espos_tabos_nodes::set_label_text": {
                "operation": "espos.tabos.lvgl.label.text.v1",
                "returnType": "tabos::Status",
                "parameterTypes": ["lv_obj_t*", "const char*"],
            }
        },
    }
    sdk_parsed = good("sdkParse", sdk)
    _require(
        _source(sdk_parsed) == sdk_raw
        and sdk_parsed["graph"].get("sdkProfile") == sdk["sdkProfile"],
        "sdk-profile-or-bytes",
    )
    regions = good("sdkRegions", _transaction(sdk, sdk_parsed, "sdkRegions"))
    _require(
        regions.get("sdkConstructionVersion") == 1
        and bool(regions.get("sdkRegions"))
        and regions["graph"] == sdk_parsed["graph"],
        "sdk-regions",
    )
    cpp = 'auto status = espos_tabos_nodes::set_label_text(label, "Kliknutí");'
    constructed = good(
        "constructSdk",
        _transaction(
            sdk,
            regions,
            "constructSdk",
            mutation={
                "kind": "insertSdkStatement",
                "regionId": regions["sdkRegions"][0]["id"],
                "beforeNodeId": None,
                "cpp": cpp,
            },
        ),
    )
    changed = _source(constructed)
    _require(
        changed.startswith(prefix)
        and changed.endswith(suffix)
        and cpp.encode() in changed
        and b"\n" not in changed.replace(b"\r\n", b""),
        "sdk-byte-preservation",
    )
    _require(_opaque(constructed) == _opaque(sdk_parsed), "sdk-opaque-preservation")
    _require(
        constructed["graph"].get("sdkProfile") == sdk["sdkProfile"]
        and constructed.get("sdkConstructionVersion") == 1,
        "sdk-profile",
    )
    status = next(n for n in constructed["graph"]["nodes"] if n.get("variable") == "status")
    _require(
        status.get("cppType") == "tabos::Status"
        and status.get("binding", {}).get("operation") == "espos.tabos.lvgl.label.text.v1",
        "sdk-typed-node",
    )
    changes = constructed["changeSet"]
    _require(
        changes.get("insertedNodeIds") == [status["id"]] and changes.get("removedNodeIds") == [],
        "sdk-change-set",
    )

    _decode_reply(exchange(b'{"operation":"parse","operation":"parse"}\n', (ROLE,)), success=False)
    checks.append("malformedRequest")
    _decode_reply(exchange(b"", ("catalog",)), success=False)
    checks.append("fixedRole")
    return checks


def _check_console_pe(stream):
    """Bounded header check; reject GUI, DLL and non-x64 images before launch."""
    header = stream.read(64)
    _require(len(header) == 64 and header[:2] == b"MZ", "invalid-executable")
    offset = int.from_bytes(header[60:64], "little")
    _require(64 <= offset <= 1024 * 1024, "invalid-executable")
    stream.seek(offset)
    coff = stream.read(24)
    _require(len(coff) == 24 and coff[:6] == b"PE\x00\x00\x64\x86", "invalid-executable")
    optional_size = int.from_bytes(coff[20:22], "little")
    characteristics = int.from_bytes(coff[22:24], "little")
    _require(
        70 <= optional_size <= 4096 and characteristics & 2 and not characteristics & 0x2000,
        "invalid-executable",
    )
    optional = stream.read(optional_size)
    _require(len(optional) == optional_size and optional[:2] == b"\x0b\x02", "invalid-executable")
    _require(int.from_bytes(optional[68:70], "little") == 3, "console-backend-required")


def _staged_executable(executable):
    path = Path(executable)
    _require(
        path.is_absolute() and path.name.lower() in _STAGED_NAMES and path.is_file(),
        "staged-exe-required",
    )
    _require(not path.is_symlink(), "staged-exe-required")
    path = path.resolve(strict=True)
    _require(path.name.lower() in _STAGED_NAMES, "staged-exe-required")
    _require(os.name == "nt", "windows-required")
    # Check a genuine Windows PE header, not a .py wrapper or fabricated launch
    # placeholder. This is format validation, not an ownership/signature proof.
    with path.open("rb") as stream:
        _check_console_pe(stream)
    return path


def verify_executable(executable):
    """Caller explicitly identifies its owned staging artifact; never auto-find."""
    path = _staged_executable(executable)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    child_runs = []

    def exchange(payload, args):
        started = time.monotonic()
        result = _run_owned_child((str(path), *args), payload, cwd=path.parent)
        # The owned runner returns only after natural exit and complete drain;
        # timeout/cap/cleanup failures raise instead of producing a receipt.
        child_runs.append(
            {
                "role": args[0],
                "exitCode": result[0],
                "stdoutBytes": len(result[1]),
                "stderrBytes": len(result[2]),
                "elapsedSeconds": round(time.monotonic() - started, 6),
                "naturalCompletion": True,
            }
        )
        return result

    checks = _verify_cases(exchange)
    with path.open("rb") as stream:
        _require(hashlib.file_digest(stream, "sha256").hexdigest() == digest, "artifact-changed")
    return {
        "ok": True,
        "frozenVerified": True,
        "role": ROLE,
        "artifactSha256": digest,
        "checks": checks,
        "ownedChildren": len(checks),
        "childRuns": child_runs,
        "deadlineSeconds": DEADLINE_SECONDS,
        "combinedOutputLimitBytes": MAX_FRAME_BYTES,
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        _require(len(args) == 2 and args[0] == "--exe", "usage-explicit-exe-required")
        response = verify_executable(args[1])
        status = 0
    except VerificationError as exc:
        response, status = {"ok": False, "frozenVerified": False, "code": exc.code}, 1
    except Exception:
        response, status = {"ok": False, "frozenVerified": False, "code": "verification-failed"}, 1
    print(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
