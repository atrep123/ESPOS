"""CLI-owned SDK stderr diagnostics, not a library-import logging policy.

Install after build_server() configures logging and before admitting stdio.
The standalone CLI owns logging configuration for this bounded lifetime.
No SDK methods, LogRecord factory, root level, or protocol handler are changed.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

_ACTIVE = False
_SEVERITY = {10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}
MAX_DIAGNOSTIC_LINE_BYTES = 48


class SdkDiagnosticError(RuntimeError):
    """Fixed, payload-free CLI diagnostic failure."""


def _sdk_name(name: str) -> bool:
    return name == "mcp" or name.startswith("mcp.")


def _inside_sdk(pathname: str, sdk_root: str) -> bool:
    # LogRecord.pathname is the logging call site, NOT a protocol input path.
    # Lexical comparison only: never stat/open a caller-controlled pathname.
    if not isinstance(pathname, str):
        return False
    path = os.path.normcase(os.path.abspath(pathname))
    return path.startswith(sdk_root + os.sep)


class _FixedSdkHandler(logging.Handler):
    def __init__(self, stream: TextIO, sdk_root: str):
        super().__init__(logging.NOTSET)
        self.stream, self.sdk_root = stream, sdk_root
        self.failed = False

    def is_sdk(self, record: logging.LogRecord) -> bool:
        return _sdk_name(record.name) or _inside_sdk(record.pathname, self.sdk_root)

    def emit(self, record: logging.LogRecord) -> None:
        # No getMessage(), Formatter, str/repr(msg/args), exception formatting,
        # stack, filename, logger name, extras, or caller-derived event code.
        severity = _SEVERITY.get(record.levelno, "OTHER")
        code = "MCP_SDK_DIAGNOSTIC"
        if record.name == "mcp.server.lowlevel.server":
            code = "MCP_SDK_SERVER"
        elif _inside_sdk(record.pathname, self.sdk_root):
            relative = os.path.relpath(
                os.path.normcase(os.path.abspath(record.pathname)), self.sdk_root
            )
            if relative == os.path.normcase(os.path.join("shared", "session.py")):
                code = "MCP_SDK_SESSION"
        line = severity + " " + code + "\n"
        if self.failed:
            return
        try:
            if self.stream.write(line) != len(line):
                self.failed = True
            else:
                self.stream.flush()
        except Exception:
            # logging.Handler.handleError can dump the original record! Never
            # call it here; retain a fixed failure for CLI settlement instead.
            self.failed = True


class _RootRouter(logging.Handler):
    def __init__(self, safe: _FixedSdkHandler, original: tuple[logging.Handler, ...]):
        super().__init__(logging.NOTSET)
        self.safe, self.original = safe, original

    def emit(self, record: logging.LogRecord) -> None:
        if self.safe.is_sdk(record):
            self.safe.handle(record)
            return
        # Non-SDK application records retain original objects, handlers,
        # thresholds, filters, formatters, exception behavior and ordering.
        for handler in self.original:
            if record.levelno >= handler.level:
                handler.handle(record)


def _sdk_loggers():
    # CPython 3.12 getChildren() skips descendants behind PlaceHolders. A
    # READ-ONLY snapshot of its registry is needed to include child handlers
    # that could otherwise emit before reaching our protected mcp ancestor.
    # Never replace the registry, classes, methods, or SDK logger objects.
    registry = logging.Logger.manager.loggerDict.copy()
    return sorted(
        (
            item
            for name, item in registry.items()
            if _sdk_name(name) and isinstance(item, logging.Logger)
        ),
        key=lambda item: item.name,
    )


def _replace_handlers(logger: logging.Logger, handlers) -> None:
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
    for handler in handlers:
        logger.addHandler(handler)


@contextmanager
def cli_sdk_diagnostics(*, stream: TextIO | None = None):
    """Temporary boundary for an already-built, standalone MCP CLI.

    Existing SDK child handlers/non-propagating children are rerouted explicitly;
    future ordinary mcp.* children propagate to the protected mcp ancestor.
    Root-logger calls originating in the actual installed SDK are also protected.
    Not an in-process multi-tenant logging API: concurrent handler reconfiguration
    or late third-party addHandler/propagate changes during serving are unsupported.
    No log payload filtering and no claim to sanitize non-SDK/direct stderr writes.
    """
    global _ACTIVE
    if _ACTIVE:
        raise SdkDiagnosticError("MCP SDK diagnostics already owned")
    import mcp

    root = logging.getLogger()
    if not root.handlers:
        raise SdkDiagnosticError("Build the MCP server before owning its diagnostics")
    sdk_root = os.path.normcase(os.path.abspath(str(Path(mcp.__file__).parent)))
    safe = _FixedSdkHandler(sys.stderr if stream is None else stream, sdk_root)
    logging.getLogger("mcp")  # protected parent for future ordinary children
    saved_root = tuple(root.handlers)
    saved_sdk = [(logger, tuple(logger.handlers), logger.propagate) for logger in _sdk_loggers()]
    _ACTIVE = True
    try:
        _replace_handlers(root, (_RootRouter(safe, saved_root),))
        for logger, _, _ in saved_sdk:
            # Do not set levels, disabled, filters, LogRecordFactory or SDK code.
            _replace_handlers(logger, (safe,))
            logger.propagate = False
        yield
    finally:
        for logger, handlers, propagate in reversed(saved_sdk):
            _replace_handlers(logger, handlers)
            logger.propagate = propagate
        _replace_handlers(root, saved_root)
        safe.close()  # Handler.close does NOT close the caller-owned stream.
        _ACTIVE = False
    if safe.failed:
        raise SdkDiagnosticError("MCP SDK diagnostic output failed")
