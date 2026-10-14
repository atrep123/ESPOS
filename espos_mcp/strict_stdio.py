"""Application-owned bounded stdio files for the official MCP SDK transport.

Strict JSON admission precedes SDK model parsing. The SDK still owns protocol
models, initialize/session/notification handling, dispatch and stream lifetimes.
No server, standard stream, event loop or transport is opened at import time.
"""

from __future__ import annotations

import io
import json
import math
import sys
import threading
from typing import BinaryIO

import anyio
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

MAX_INPUT_FRAME_BYTES = 1_048_576  # Entire line, including any LF/CRLF.
MAX_OUTPUT_FRAME_BYTES = 8_388_608  # Entire serialized line, including LF.

# Preserve the SDK's malformed-frame path without forwarding rejected bytes:
# its JSONRPCMessage parser rejects this fixed token, and the existing session
# emits its fixed log notification, NOT a fabricated response with a guessed id.
_REJECTED_FRAME = "null\n"


class StdioBoundaryError(RuntimeError):
    """A fixed-message terminal I/O/boundary failure; never retry an operation."""


class _InvalidJson(ValueError):
    pass


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise _InvalidJson()
        value[key] = item
    return value


def _no_constant(_token):
    raise _InvalidJson()


def _finite_float(token):
    value = float(token)
    if not math.isfinite(value):
        raise _InvalidJson()
    return value


def _strict_json(text):
    # No replacement protocol parser: only the stdlib JSON decoder with a
    # duplicate-member hook. Escaped-equivalent names compare AFTER unescaping.
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_no_constant,
        parse_float=_finite_float,
    )


def admit_frame(raw: bytes) -> tuple[str, str | None]:
    """Return (forward|reject|reply|drop, text); no I/O and no tool dispatch.

    forward preserves the original decoded line. reply uses the actual SDK's
    invalid-parameters envelope. Rejected raw/model frames have no trusted id.
    drop preserves the SDK rule that invalid notifications get no response.
    """
    if len(raw) > MAX_INPUT_FRAME_BYTES:
        raise StdioBoundaryError("MCP input frame exceeds its byte limit.")
    try:
        text = raw.decode("utf-8", errors="strict")
        _strict_json(text)  # MUST precede every SDK model parse.
        message = types.JSONRPCMessage.model_validate_json(text)
    except Exception:
        # Do not keep, format, log or expose the exception or rejected bytes.
        return "reject", _REJECTED_FRAME

    root = message.root
    if isinstance(root, types.JSONRPCRequest):
        try:
            # Same public SDK model and dump shape used by BaseSession before
            # request dispatch. No new method/schema/business registry.
            types.ClientRequest.model_validate(
                root.model_dump(by_alias=True, mode="json", exclude_none=True)
            )
        except Exception:
            error = types.JSONRPCError(
                jsonrpc="2.0",
                id=root.id,
                error=types.ErrorData(
                    code=types.INVALID_PARAMS, message="Invalid request parameters", data=""
                ),
            )
            return "reply", types.JSONRPCMessage(error).model_dump_json(
                by_alias=True, exclude_none=True
            ) + "\n"
    elif isinstance(root, types.JSONRPCNotification):
        try:
            types.ClientNotification.model_validate(
                root.model_dump(by_alias=True, mode="json", exclude_none=True)
            )
        except Exception:
            return "drop", None
    # Responses/errors must reach the SDK's outstanding-request correlation;
    # do not invent a second request ledger or reject valid client responses.
    return "forward", text


class BoundedTextOutput(io.TextIOBase):
    """One UTF-8 JSON line per write; shared SDK/admission writes are serialized.

    Never closes the supplied process-owned binary stream. An oversized result
    closes the session before this frame is written; it does not fake rollback.
    """

    def __init__(self, binary: BinaryIO):
        super().__init__()
        self._binary = binary
        # close() calls IOBase.close(), which calls our flush() again. The
        # same reentrant lock orders encoding, physical I/O, flush and close.
        self._lock = threading.RLock()
        self._failed = False

    def _fail(self, message: str):
        with self._lock:
            self._failed = True
        raise StdioBoundaryError(message) from None

    def write(self, text: str) -> int:
        with self._lock:
            if self.closed:
                raise StdioBoundaryError("MCP output stream is closed.")
            if self._failed:
                raise StdioBoundaryError("MCP output stream is closed after a boundary failure.")
            try:
                raw = text.encode("utf-8", errors="strict")
            except Exception:
                self._fail("MCP output frame is not valid UTF-8.")
            if len(raw) > MAX_OUTPUT_FRAME_BYTES:
                self._fail("MCP output frame exceeds its byte limit.")
            if not raw.endswith(b"\n") or b"\n" in raw[:-1]:
                self._fail("MCP output must contain exactly one framed message.")
            try:
                remaining = memoryview(raw)
                while remaining:
                    written = self._binary.write(remaining)
                    if type(written) is not int or not 0 < written <= len(remaining):
                        raise StdioBoundaryError("MCP output stream did not accept the frame.")
                    remaining = remaining[written:]
                self._binary.flush()
            except Exception:
                self._failed = True
                # Physical partial write is possible. No later frame may append
                # to it; do not retry or claim complete delivery to the peer.
                raise StdioBoundaryError("MCP output stream failed.") from None
            return len(text)

    def flush(self):
        with self._lock:
            if self.closed:
                raise StdioBoundaryError("MCP output stream is closed.")
            if self._failed:
                return  # IOBase.close must not retry failed physical I/O.
            try:
                self._binary.flush()
            except Exception:
                self._failed = True
                raise StdioBoundaryError("MCP output stream failed.") from None

    def close(self):
        with self._lock:
            if not self.closed:
                # Never close _binary. IOBase marks this wrapper closed even
                # if flush raises; failed streams must not retry physical I/O.
                super().close()


class StrictTextInput(io.TextIOBase):
    """Actual bounded binary readline, exposed as an SDK-compatible text file.

    Byte limit is checked BEFORE decode/JSON/SDK validation. A too-long line is
    terminal (no unbounded drain or treating its suffix as another request).
    A valid final line without LF follows the official text-iterator behavior.
    """

    def __init__(self, binary: BinaryIO, output: BoundedTextOutput):
        super().__init__()
        self._binary = binary
        self._output = output
        self._failed = False
        self._lock = threading.RLock()

    def _check_open(self):
        # Caller holds _lock. Closure wins over any late read result/error.
        if self.closed:
            raise StdioBoundaryError("MCP input stream is closed.")
        if self._failed:
            raise StdioBoundaryError("MCP input stream is closed after a boundary failure.")

    def close(self):
        with self._lock:
            if not self.closed:
                super().close()  # No binary close, drain, cancellation or flush.

    def readline(self, size: int = -1) -> str:
        while True:
            with self._lock:
                self._check_open()
                if size != -1:
                    raise StdioBoundaryError("MCP input requires whole framed messages.")
            # An admitted read may block indefinitely. NEVER hold the lifecycle
            # lock here: close marks the wrapper without interrupting _binary.
            # A read already admitted before close may still consume bytes;
            # its eventual result is discarded before admission/reply below.
            try:
                raw = self._binary.readline(MAX_INPUT_FRAME_BYTES + 1)
            except Exception:
                with self._lock:
                    self._check_open()
                    self._failed = True
                    raise StdioBoundaryError("MCP input stream failed.") from None
            with self._lock:
                self._check_open()  # Includes EOF, oversized and invalid frames.
                if not raw:
                    return ""
                try:
                    action, text = admit_frame(raw)
                except StdioBoundaryError:
                    self._failed = True
                    raise
                if action in ("forward", "reject"):
                    return text
                if action == "reply":
                    try:
                        self._output.write(text)
                    except StdioBoundaryError:
                        self._failed = True
                        raise
            # Invalid notifications are consumed without a response. Rejected
            # DTOs never enter the SDK warning that interpolates input values.


async def _serve_existing(server: FastMCP):
    output = BoundedTextOutput(sys.stdout.buffer)
    input_file = StrictTextInput(sys.stdin.buffer, output)
    # MCP 1.30.0 FastMCP has no public getter/run-with-streams method. This one
    # READ of its existing low-level instance is version-bound and reviewable;
    # no SDK private mutation, replacement server or new capability is involved.
    lowlevel = server._mcp_server
    async with stdio_server(stdin=anyio.wrap_file(input_file), stdout=anyio.wrap_file(output)) as (
        read_stream,
        write_stream,
    ):
        await lowlevel.run(read_stream, write_stream, lowlevel.create_initialization_options())


def run_stdio(server: FastMCP) -> None:
    """Explicit CLI-only activation point. Never called by source-only tests."""
    try:
        anyio.run(_serve_existing, server)
    except Exception:
        # Suppress ExceptionGroup/transport diagnostics that may contain context.
        # KeyboardInterrupt/SystemExit and other BaseException signals propagate.
        raise StdioBoundaryError("MCP stdio session failed; do not automatically retry.") from None
