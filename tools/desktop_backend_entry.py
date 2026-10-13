"""Fixed desktop CodeGraph role; one JSON line in, one bounded JSON line out.

Source invocation: python -I -B tools/desktop_backend_entry.py codegraph-bundled
Freeze this entry with the sibling tools package and the declared Tree-sitter
extensions. Frozen startup uses its normal package loader, never a developer
tooling root, environment-selected interpreter, subprocess or project import.
The SDK catalog is a static sibling dependency, not an additional CLI role.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

MAX_FRAME_BYTES = 1024 * 1024  # desktop codegraph/transport.ts FRAME_LIMIT
MAX_SOURCE_BYTES = 64 * 1024
MAX_SOURCE_BASE64 = 4 * ((MAX_SOURCE_BYTES + 2) // 3)
_OPERATIONS = {"parse", "edit", "regions", "construct", "sdkRegions", "constructSdk"}


class _Quiet:
    """Discard incidental library output without buffering or exposing it."""

    def write(self, value):
        return len(value)

    def flush(self):
        return None


def _failure(code, message):
    return {"ok": False, "diagnostics": [{"code": code, "message": message}]}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("Non-finite JSON number")


def _source_within_budget(value):
    # Do not decode C++ here. The authoritative process_request validates fields
    # and base64 before parsing. This is only a pre-allocation byte budget; the
    # padding calculation also distinguishes 65536 from 65537 decoded bytes.
    if not isinstance(value, str):
        return True  # malformed type belongs to process_request
    padding = 2 if value.endswith("==") else int(value.endswith("="))
    return (
        len(value) <= MAX_SOURCE_BASE64
        and ((len(value) + 3) // 4) * 3 - padding <= MAX_SOURCE_BYTES
    )


def _process(request):
    if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
        return _failure("backend-request", "Expected a CodeGraph request object."), 2
    if request["operation"] not in _OPERATIONS:
        return _failure("backend-operation", "Unsupported packaged CodeGraph operation."), 2
    if not _source_within_budget(request.get("sourceBase64")):
        return _failure("backend-source-limit", "C++ source exceeds 64 KiB."), 2

    # Direct -I script boot admits only this entry's own package root. Module
    # invocation uses relative imports; a frozen executable uses its bootloader's
    # package search path unchanged. Nothing is selected by caller/env/cwd.
    if __package__:
        from . import tabos_code_graph
        from . import tabos_sdk_node_catalog as _sdk_catalog
    else:
        if not getattr(sys, "frozen", False):
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tools import tabos_code_graph
        from tools import tabos_sdk_node_catalog as _sdk_catalog  # noqa: F401

    # Keep the full request (including sdkProfile/bindings) and response. Shape,
    # hash, graph, token and construction validation live only in the parser.
    response = tabos_code_graph.process_request(request)
    if not _source_within_budget(response.get("sourceBase64")):
        return _failure("backend-source-limit", "Resulting C++ source exceeds 64 KiB."), 1
    # Exception text can contain untrusted values. Keep diagnostic fields/codes,
    # but do not echo them, or names interpolated into entry-selection messages.
    for diagnostic in response.get("diagnostics", []):
        if diagnostic.get("code") == "request-error":
            diagnostic["message"] = "CodeGraph rejected the request; no source change."
    for diagnostic in response.get("graph", {}).get("diagnostics", []):
        if diagnostic.get("code") == "entry-selection":
            diagnostic["message"] = "Selected entry must identify one supported function body."
    return response, 0 if response.get("ok") is True else 1


def _encode(response):
    # Bound the aggregate encoded output BEFORE writing any part of it. ASCII
    # makes byte accounting independent of console encoding and Unicode size.
    frame = bytearray()
    encoder = json.JSONEncoder(ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    for chunk in encoder.iterencode(response):
        if len(frame) + len(chunk) + 1 > MAX_FRAME_BYTES:
            raise ValueError("Reply exceeds frame budget")
        frame.extend(chunk.encode("ascii"))
    frame.extend(b"\n")
    return frame


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    output = sys.stdout.buffer
    # Include imports and exception handling in the quiet boundary. No usage
    # output, traceback, raw stderr, paths or environment values cross it.
    with contextlib.redirect_stdout(_Quiet()), contextlib.redirect_stderr(_Quiet()):
        try:
            if args != ["codegraph-bundled"]:
                response, status = (
                    _failure("backend-role", "Expected exactly the codegraph-bundled role."),
                    2,
                )
            else:
                # Read a line, not EOF: Tauri writes a frame and holds stdin open.
                # A second line is never admitted as another request.
                frame = sys.stdin.buffer.readline(MAX_FRAME_BYTES + 1)
                if not frame or len(frame) > MAX_FRAME_BYTES or not frame.endswith(b"\n"):
                    response, status = (
                        _failure("backend-frame", "Expected one JSON line of at most 1 MiB."),
                        2,
                    )
                else:
                    request = json.loads(
                        frame.decode("utf-8"),
                        object_pairs_hook=_unique_object,
                        parse_constant=_nonfinite,
                    )
                    response, status = _process(request)
        except ImportError:
            response, status = (
                _failure("backend-unavailable", "Packaged CodeGraph dependencies are unavailable."),
                1,
            )
        except (ValueError, UnicodeError, RecursionError):
            response, status = _failure("backend-json", "Invalid or excessive JSON request."), 2
        except Exception:
            response, status = _failure("backend-error", "CodeGraph backend failed."), 1
        try:
            reply = _encode(response)
        except Exception:
            reply = _encode(
                _failure("backend-reply", "CodeGraph reply exceeds limits or is invalid.")
            )
            status = 1
        try:
            output.write(reply)
            output.flush()
        except OSError:
            return 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
