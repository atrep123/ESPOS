"""Read-only discovery receipts over the existing target registry.

This module does not import MCP, inspect devices, run codegen, or launch anything.
Target profiles remain owned by espos_targets; the models below describe only
the discovery wire envelope, not a second target/business model.
"""

from __future__ import annotations

import hashlib
import json
import re
from importlib import metadata
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

import espos_targets
from espos_mcp import __version__

RECEIPT_VERSION = 1
MAX_TARGETS = 256
MAX_PAGE_SIZE = 32
MAX_RESPONSE_BYTES = 65536  # UTF-8 structured receipt, before MCP framing
MAX_REGISTRY_BYTES = 262144
MAX_TOOL_COUNT = 128
MAX_TARGET_ID = 128
TARGET_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")


class DiscoveryError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Literal["InvalidArgument", "UnknownTarget", "Unavailable", "LimitExceeded"]
    message: str = Field(max_length=256)
    retryable: Literal[False] = False


class DiscoveryReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: Literal[1]
    operation: Literal["get_capabilities", "list_targets", "get_target"]
    ok: bool
    data: dict[str, Any] | None
    error: DiscoveryError | None

    @model_validator(mode="after")
    def coherent_outcome(self):
        if self.ok != (self.error is None) or self.ok != (self.data is not None):
            raise ValueError("inconsistent discovery outcome")
        return self


def _json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def error_receipt(operation: str, code: str, message: str) -> dict[str, Any]:
    # All callers supply fixed messages, never exception text or rejected input.
    receipt = {
        "schemaVersion": RECEIPT_VERSION,
        "operation": operation,
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message, "retryable": False},
    }
    return DiscoveryReceipt.model_validate(receipt).model_dump()


def _success(operation: str, data: dict[str, Any]) -> dict[str, Any]:
    receipt = {
        "schemaVersion": RECEIPT_VERSION,
        "operation": operation,
        "ok": True,
        "data": data,
        "error": None,
    }
    if len(_json(receipt).encode("utf-8")) > MAX_RESPONSE_BYTES:
        return error_receipt(operation, "LimitExceeded", "Discovery result exceeds its byte limit.")
    return DiscoveryReceipt.model_validate(receipt).model_dump()


class _RegistryBound(ValueError):
    pass


def _registry_snapshot():
    registry = espos_targets.load_registry()
    if len(registry.ids()) > MAX_TARGETS:
        raise _RegistryBound()
    # Delegate validation and serialization; do not reconstruct profile fields.
    document = registry.to_dict()
    espos_targets.TargetRegistry.from_dict(document)
    for profile in document["profiles"]:
        if len(profile["profile_id"]) > MAX_TARGET_ID:
            raise _RegistryBound()
    encoded = _json(document).encode("utf-8")
    if len(encoded) > MAX_REGISTRY_BYTES:
        raise _RegistryBound()
    return registry, document, hashlib.sha256(encoded).hexdigest()


def _registry_error(operation: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, _RegistryBound):
        return error_receipt(
            operation, "LimitExceeded", "Target registry exceeds discovery limits."
        )
    return error_receipt(
        operation, "Unavailable", "Target registry could not be read or validated."
    )


def targets_receipt(offset: int = 0, limit: int = 16) -> dict[str, Any]:
    """Stable registry-order page; clients compare registryHash between pages."""
    operation = "list_targets"
    if (
        type(offset) is not int
        or not 0 <= offset <= MAX_TARGETS
        or type(limit) is not int
        or not 1 <= limit <= MAX_PAGE_SIZE
    ):
        return error_receipt(
            operation,
            "InvalidArgument",
            "offset must be 0..256 and limit 1..32 (integers, not booleans).",
        )
    try:
        _, document, digest = _registry_snapshot()
        profiles = document["profiles"]
        page = profiles[offset : offset + limit]
        next_offset = offset + len(page)
        return _success(
            operation,
            {
                "registrySchemaVersion": document["schema_version"],
                "registryHash": digest,
                "source": "espos_targets.load_registry",
                "total": len(profiles),
                "offset": offset,
                "limit": limit,
                "targets": page,
                "nextOffset": next_offset if next_offset < len(profiles) else None,
            },
        )
    except Exception as exc:
        return _registry_error(operation, exc)


def target_receipt(target_id: str) -> dict[str, Any]:
    """Exact profile-ID lookup; no alias, path, board selection or dynamic import."""
    operation = "get_target"
    if (
        type(target_id) is not str
        or len(target_id) > MAX_TARGET_ID
        or TARGET_ID.fullmatch(target_id) is None
    ):
        return error_receipt(
            operation, "InvalidArgument", "target_id must be an exact registry ID."
        )
    try:
        registry, document, digest = _registry_snapshot()
        if target_id not in registry.ids():
            return error_receipt(operation, "UnknownTarget", "Target ID is not registered.")
        profile = registry.get(target_id)
        return _success(
            operation,
            {
                "registrySchemaVersion": document["schema_version"],
                "registryHash": digest,
                "source": "espos_targets.load_registry",
                "target": profile.to_dict(),
                "capabilityStatus": {
                    name: "Available" if name in profile.capabilities else "Unavailable"
                    for name in sorted(espos_targets.CAPABILITIES)
                },
                "evidence": "Declared tooling metadata; not hardware or backend readiness.",
            },
        )
    except Exception as exc:
        return _registry_error(operation, exc)


def capabilities_receipt(tool_names: list[str]) -> dict[str, Any]:
    """tool_names must come from this server's actual list_tools(), not a catalog."""
    operation = "get_capabilities"
    try:
        if (
            type(tool_names) is not list
            or len(tool_names) > MAX_TOOL_COUNT
            or any(type(n) is not str or not 1 <= len(n) <= 128 for n in tool_names)
            or len(set(tool_names)) != len(tool_names)
        ):
            return error_receipt(
                operation, "LimitExceeded", "Tool inventory exceeds discovery limits."
            )
        _, document, digest = _registry_snapshot()
        try:
            sdk_version = metadata.version("mcp")
        except metadata.PackageNotFoundError:
            sdk_version = None
        return _success(
            operation,
            {
                "server": {"name": "espos", "version": __version__, "mcpSdkVersion": sdk_version},
                "registrySchemaVersion": document["schema_version"],
                "registryHash": digest,
                "targetCount": len(document["profiles"]),
                "targetSource": "espos_targets.load_registry",
                "capabilityVocabulary": sorted(espos_targets.CAPABILITIES),
                "registeredTools": sorted(tool_names),
                "limits": {
                    "maxPageSize": MAX_PAGE_SIZE,
                    "maxTargets": MAX_TARGETS,
                    "maxTargetIdCharacters": MAX_TARGET_ID,
                    "maxStructuredReceiptBytes": MAX_RESPONSE_BYTES,
                },
                "semantics": [
                    "Registered tools are inventory, not authorization or readiness.",
                    "Discovery and codegraph observation tools are read-only; legacy tools may mutate.",
                    "Targets are canvas profiles, not board IDs. Use existing list_boards for board metadata.",
                    "runtime is a declared target runtime, not a connected or launchable backend.",
                    "codegen unavailable forbids inferring legacy C export support for that target.",
                    "This discovery surface does not establish Studio, simulator, hardware or native transport readiness.",
                    "SDK version metadata is not a supported-version or transport verification receipt.",
                ],
            },
        )
    except Exception as exc:
        return _registry_error(operation, exc)
