"""Version 1 read-only source analysis, over the existing product libraries.

No MCP import, project model, file/path/command input, writer, subprocess, or
registration on import. All caller shapes/lengths are bounded before backend
imports or parsing. Caller bytes remain authoritative; graphs are observations.
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import importlib
import json
import re
import sys
from importlib import metadata

RECEIPT_VERSION = 1
ANALYZE = "analyze_cpp_v1"
LIST_SDK = "list_sdk_nodes_v1"
SDK_PROFILE = "tabos-sdk-minimal-1"
MAX_SOURCE_BYTES = 65536
MAX_SOURCE_BASE64 = 4 * ((MAX_SOURCE_BYTES + 2) // 3)
MAX_REQUEST_BYTES = 131072
MAX_ENTRIES = 16
MAX_BINDINGS = 32
MAX_PARAMETERS = 8
MAX_TEXT_CHARACTERS = 256
MAX_GRAPH_NODES = 4096
MAX_GRAPH_EDGES = 8192
MAX_CATALOG_NODES = 256
MAX_PAGE_SIZE = 32
MAX_CATALOG_BYTES = 262144
MAX_RESPONSE_BYTES = 1048576  # Structured UTF-8 receipt, before MCP framing.
PARSER_DEPENDENCIES = {"tree-sitter": "0.26.0", "tree-sitter-cpp": "0.23.4"}
_BASE64 = re.compile(r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")

# Discovery metadata only; enforcement below does not depend on tool annotations
# or Pydantic coercion. A client cannot broaden this tool by adding edit fields.
ANALYZE_INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sourceBase64", "entries"],
    "properties": {
        "sourceBase64": {
            "type": "string",
            "maxLength": MAX_SOURCE_BASE64,
            "description": "Canonical base64 of <=65536 original UTF-8 bytes, BOM/CRLF retained.",
        },
        "entries": {
            "type": "array",
            "maxItems": MAX_ENTRIES,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_CHARACTERS},
        },
        "bindings": {
            "type": "object",
            "maxProperties": MAX_BINDINGS,
            "propertyNames": {"minLength": 1, "maxLength": MAX_TEXT_CHARACTERS},
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": ["operation", "returnType", "parameterTypes"],
                "properties": {
                    "operation": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_TEXT_CHARACTERS,
                    },
                    "returnType": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_TEXT_CHARACTERS,
                    },
                    "parameterTypes": {
                        "type": "array",
                        "maxItems": MAX_PARAMETERS,
                        "items": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_TEXT_CHARACTERS,
                        },
                    },
                },
            },
        },
        "eventBindings": {
            "type": "object",
            "maxProperties": MAX_ENTRIES,
            "propertyNames": {"minLength": 1, "maxLength": MAX_TEXT_CHARACTERS},
            "additionalProperties": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_TEXT_CHARACTERS,
            },
        },
        "sdkProfile": {"type": "string", "const": SDK_PROFILE},
        "observation": {
            "type": "object",
            "additionalProperties": False,
            "required": ["documentId", "revision", "targetId"],
            "properties": {
                "documentId": {"type": "string", "minLength": 1, "maxLength": 128},
                "revision": {"type": "integer", "minimum": 0, "maximum": 9007199254740991},
                "targetId": {"type": "string", "minLength": 1, "maxLength": 128},
            },
        },
    },
}


class _BoundaryError(ValueError):
    def __init__(self, code, message):
        self.code, self.message = code, message


class _Unavailable(RuntimeError):
    pass


def json_text(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def error_receipt(operation, code, message, source_identity=None):
    # Fixed messages only; no exception text, rejected payload, import path or secret.
    return {
        "schemaVersion": RECEIPT_VERSION,
        "operation": operation,
        "ok": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "retryable": False,
            "sourceIdentity": source_identity,
        },
    }


def _success(operation, data):
    result = {
        "schemaVersion": RECEIPT_VERSION,
        "operation": operation,
        "ok": True,
        "data": data,
        "error": None,
    }
    if len(json_text(result).encode("utf-8")) > MAX_RESPONSE_BYTES:
        return error_receipt(
            operation,
            "LimitExceeded",
            "Structured response exceeds its byte limit.",
            data.get("sourceIdentity"),
        )
    return result


def _text(value, maximum=MAX_TEXT_CHARACTERS):
    if type(value) is not str or not 1 <= len(value) <= maximum:
        raise _BoundaryError("InvalidArgument", "Text fields must be nonempty bounded strings.")
    if any(ord(ch) < 32 or ord(ch) == 127 or 0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise _BoundaryError(
            "InvalidArgument", "Text fields must contain valid Unicode without control characters."
        )
    return value


def _object(value, allowed, required=(), maximum=None):
    if (
        type(value) is not dict
        or (maximum is not None and len(value) > maximum)
        or any(type(k) is not str for k in value)
        or not set(required) <= value.keys()
        or not value.keys() <= set(allowed)
    ):
        raise _BoundaryError(
            "InvalidArgument", "Object contains missing, unknown or invalid fields."
        )


def _analyze_input(request):
    _object(
        request,
        {"sourceBase64", "entries", "bindings", "eventBindings", "sdkProfile", "observation"},
        {"sourceBase64", "entries"},
        maximum=6,
    )
    encoded = request["sourceBase64"]
    if type(encoded) is not str:
        raise _BoundaryError("InvalidArgument", "sourceBase64 must be a canonical base64 string.")
    if len(encoded) > MAX_SOURCE_BASE64:
        raise _BoundaryError("LimitExceeded", "Source exceeds the encoded byte limit.")
    if len(encoded) % 4 or _BASE64.fullmatch(encoded) is None:
        raise _BoundaryError("InvalidArgument", "sourceBase64 must be a canonical base64 string.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise _BoundaryError(
            "InvalidArgument", "sourceBase64 must be a canonical base64 string."
        ) from None
    if len(raw) > MAX_SOURCE_BYTES:
        raise _BoundaryError("LimitExceeded", "Source exceeds the decoded byte limit.")
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise _BoundaryError("InvalidArgument", "sourceBase64 has noncanonical padding bits.")
    try:
        raw.decode("utf-8-sig")  # Validate only; never use decoded text as source authority.
    except UnicodeDecodeError:
        raise _BoundaryError(
            "InvalidArgument", "Source must be UTF-8; invalid bytes are rejected, never replaced."
        ) from None
    entries = request["entries"]
    if type(entries) is not list or len(entries) > MAX_ENTRIES:
        raise _BoundaryError(
            "InvalidArgument", "entries must be an array of at most 16 explicit names."
        )
    for entry in entries:
        _text(entry)
        if any(ch.isspace() for ch in entry):
            raise _BoundaryError(
                "InvalidArgument", "Entry names must use canonical spelling without whitespace."
            )
    if len(set(entries)) != len(entries):
        raise _BoundaryError("InvalidArgument", "Entry names must be unique.")
    context = {"entries": entries.copy()}
    if "bindings" in request:
        bindings = request["bindings"]
        if type(bindings) is not dict or len(bindings) > MAX_BINDINGS:
            raise _BoundaryError(
                "InvalidArgument", "bindings must be an object of at most 32 explicit assertions."
            )
        for callee, binding in bindings.items():
            _text(callee)
            if any(ch.isspace() for ch in callee):
                raise _BoundaryError(
                    "InvalidArgument",
                    "Binding callees must use canonical spelling without whitespace.",
                )
            _object(
                binding,
                {"operation", "returnType", "parameterTypes"},
                {"operation", "returnType", "parameterTypes"},
                maximum=3,
            )
            _text(binding["operation"])
            _text(binding["returnType"])
            params = binding["parameterTypes"]
            if type(params) is not list or len(params) > MAX_PARAMETERS:
                raise _BoundaryError(
                    "InvalidArgument", "parameterTypes must be an array of at most 8 types."
                )
            for param in params:
                if _text(param) == "void":
                    raise _BoundaryError(
                        "InvalidArgument", "Parameter types must name explicit non-void C++ types."
                    )
        context["bindings"] = copy.deepcopy(bindings)
    if "eventBindings" in request:
        events = request["eventBindings"]
        if type(events) is not dict or len(events) > MAX_ENTRIES:
            raise _BoundaryError(
                "InvalidArgument", "eventBindings must be an object of at most 16 labels."
            )
        for entry, event in events.items():
            _text(entry)
            _text(event)
            if entry not in entries:
                raise _BoundaryError(
                    "InvalidArgument", "Event labels must refer to explicitly selected entries."
                )
        context["eventBindings"] = events.copy()
    if "sdkProfile" in request:
        if type(request["sdkProfile"]) is not str or request["sdkProfile"] != SDK_PROFILE:
            raise _BoundaryError(
                "InvalidArgument", "Only the reviewed tabos-sdk-minimal-1 profile is supported."
            )
        context["sdkProfile"] = SDK_PROFILE
    observation = request.get("observation")
    if "observation" in request:
        _object(
            observation,
            {"documentId", "revision", "targetId"},
            {"documentId", "revision", "targetId"},
            maximum=3,
        )
        _text(observation["documentId"], 128)
        _text(observation["targetId"], 128)
        if (
            type(observation["revision"]) is not int
            or not 0 <= observation["revision"] <= 9007199254740991
        ):
            raise _BoundaryError(
                "InvalidArgument", "revision must be an integer from 0 to 9007199254740991."
            )
    if len(json_text(request).encode("utf-8")) > MAX_REQUEST_BYTES:
        raise _BoundaryError(
            "LimitExceeded", "Structured source-analysis request exceeds its byte limit."
        )
    return raw, context, copy.deepcopy(observation)


def _libraries():
    # Fixed product import names, resolved by the existing package/runtime host.
    # Never add sys.path, accept a module/root/path or load caller-selected code.
    try:
        # Host must disable import bytecode writes; do not change process/global
        # config here. Launching with -B is primary/runtime ownership.
        if not sys.dont_write_bytecode:
            raise _Unavailable()
        graph = importlib.import_module("tools.tabos_code_graph")
        catalog = importlib.import_module("tools.tabos_sdk_node_catalog")
        if (
            graph.SCHEMA_VERSION != 1
            or graph.CATALOG_VERSION != "cpp-cst-subset-1"
            or graph.SDK_PROFILE != SDK_PROFILE
            or catalog.CONTRACT_VERSION != 1
        ):
            raise _Unavailable()
        return graph, catalog
    except Exception:
        raise _Unavailable() from None


def _parser_dependencies():
    try:
        versions = {package: metadata.version(package) for package in PARSER_DEPENDENCIES}
        if versions != PARSER_DEPENDENCIES:
            raise _Unavailable()
        # Verify import/ABI availability, not just installed version metadata.
        importlib.import_module("tree_sitter")
        importlib.import_module("tree_sitter_cpp")
        return versions
    except Exception:
        raise _Unavailable() from None


def _identity(raw):
    return {
        "algorithm": "SHA-256",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byteLength": len(raw),
        "encoding": "UTF-8",
        "preservation": "exact-input-bytes",
    }


def analyze_receipt(request):
    """Analyze supplied bytes only. Never accept a graph/edit or commit revision.

    Empty entries deliberately yield outside-selection opaque observations.
    Syntax/selection diagnostics are successful observations of invalid C++,
    not build success. Dependencies/type-policy rejection produce error receipts.
    """
    try:
        raw, context, observation = _analyze_input(request)
    except _BoundaryError as exc:
        return error_receipt(ANALYZE, exc.code, exc.message)
    source_identity = _identity(raw)
    try:
        graph_module, _ = _libraries()
        versions = _parser_dependencies()
    except _Unavailable:
        return error_receipt(
            ANALYZE,
            "Unavailable",
            "Reviewed parser libraries or pinned dependencies are unavailable.",
            source_identity,
        )
    try:
        projected = graph_module.parse_source(
            raw,
            entries=context["entries"],
            bindings=context.get("bindings"),
            event_bindings=context.get("eventBindings"),
            sdk_profile=context.get("sdkProfile"),
        )
        graph = projected.to_dict()
        if (
            projected.export_source() != raw
            or graph["sourceHash"] != source_identity["sha256"]
            or graph["byteLength"] != len(raw)
            or graph["entries"] != context["entries"]
            or graph.get("sdkProfile") != context.get("sdkProfile")
            or graph["schemaVersion"] != graph_module.SCHEMA_VERSION
            or graph["catalogVersion"] != graph_module.CATALOG_VERSION
        ):
            return error_receipt(
                ANALYZE,
                "IntegrityError",
                "Parser did not preserve the supplied source identity.",
                source_identity,
            )
        if len(graph["nodes"]) > MAX_GRAPH_NODES or len(graph["edges"]) > MAX_GRAPH_EDGES:
            return error_receipt(
                ANALYZE, "LimitExceeded", "Graph exceeds the node or edge limit.", source_identity
            )
        graph_module.validate_graph(graph)
        opaque = [n for n in graph["nodes"] if n["kind"] == "opaque"]
        for node in opaque:
            span = node["sourceSpan"]
            chunk = raw[span["startByte"] : span["endByte"]]
            if (
                node["ports"]
                or node["editSlots"]
                or hashlib.sha256(chunk).hexdigest() != span["sha256"]
            ):
                return error_receipt(
                    ANALYZE,
                    "IntegrityError",
                    "Opaque source spans failed exact-byte verification.",
                    source_identity,
                )
        invalid = any(d["severity"] == "error" for d in graph["diagnostics"])
        return _success(
            ANALYZE,
            {
                "sourceBase64": request["sourceBase64"],
                "sourceIdentity": source_identity,
                "parseContext": context,
                "graph": graph,
                "analysisStatus": "InvalidCppOrSelection" if invalid else "Analyzed",
                "coverage": "partial" if opaque else "selected-subset",
                "summary": {
                    "supportedNodes": len(graph["nodes"]) - len(opaque),
                    "opaqueNodes": len(opaque),
                    "opaqueSelectedNodes": sum(n.get("scope") == "selected" for n in opaque),
                    "opaqueOutsideSelectionNodes": sum(
                        n.get("scope") == "outside-selection" for n in opaque
                    ),
                    "edgeCounts": {
                        kind: sum(e["kind"] == kind for e in graph["edges"])
                        for kind in ("execution", "data", "event")
                    },
                },
                "backend": {
                    "source": "tools.tabos_code_graph.parse_source",
                    "schemaVersion": graph_module.SCHEMA_VERSION,
                    "catalogVersion": graph_module.CATALOG_VERSION,
                    "dependencies": versions,
                },
                "observation": observation,
                "identityOrigin": "caller-asserted" if observation else "not-supplied",
                "ownerValidated": False,
                "targetRegistryValidated": False,
                "evidence": "CallerSourceAnalysis",
                "semantics": [
                    "Graph is a detached observation, not a document owner or edit authorization.",
                    "Types are restricted syntax and explicit caller assertions, not C++ compilation.",
                    "Event labels do not infer callbacks or register hardware/event topics.",
                    "ok means analysis completed; consult analysisStatus and graph diagnostics.",
                    "Raw bytes retain BOM/CRLF/opaque text; no files or source changes.",
                ],
            },
        )
    except graph_module.GraphError:
        return error_receipt(
            ANALYZE,
            "ParserRejected",
            "Parser rejected the source or explicit binding assertions.",
            source_identity,
        )
    except Exception:
        return error_receipt(
            ANALYZE,
            "Unavailable",
            "Source analysis did not complete; no source change was made.",
            source_identity,
        )


def catalog_receipt(offset=0, limit=16):
    """List actual reviewed SDK catalog nodes, distinct from parser support.

    Reads only fixed library metadata; no Tree-sitter runtime needed. This private
    parser metadata read is deliberately version-bound, pending a public metadata
    accessor owned by primary; it never broadens the canonical parser's profile.
    """
    if (
        type(offset) is not int
        or not 0 <= offset <= MAX_CATALOG_NODES
        or type(limit) is not int
        or not 1 <= limit <= MAX_PAGE_SIZE
    ):
        return error_receipt(
            LIST_SDK, "InvalidArgument", "offset must be 0..256 and limit 1..32 (strict integers)."
        )
    try:
        graph_module, catalog_module = _libraries()
        catalog = catalog_module.catalog()
        if catalog["contract_version"] != 1 or catalog["auto_execute"] is not False:
            raise _Unavailable()
        nodes = catalog["nodes"]
        if (
            len(nodes) > MAX_CATALOG_NODES
            or len(json_text(catalog).encode("utf-8")) > MAX_CATALOG_BYTES
        ):
            return error_receipt(
                LIST_SDK, "LimitExceeded", "Reviewed SDK catalog exceeds its metadata limit."
            )
        operations = (
            graph_module._SDK_OPERATIONS
        )  # Read-only canonical profile metadata; no guessed bindings.
        ids = [n["id"] for n in nodes]
        if len(set(ids)) != len(ids) or any(n["status"] != "implemented" for n in nodes):
            raise _Unavailable()
        support = {}
        for node in nodes[offset : offset + limit]:
            matched = {
                callee: copy.deepcopy(binding)
                for callee, binding in operations.items()
                if binding["operation"] == node["id"]
            }
            support[node["id"]] = {
                "sdkProfile": graph_module.SDK_PROFILE,
                "reviewedSignatures": matched,
                "status": "ExplicitBindingsOnly" if matched else "OpaqueInCurrentProfile",
            }
        next_offset = offset + len(nodes[offset : offset + limit])
        return _success(
            LIST_SDK,
            {
                "source": "tools.tabos_sdk_node_catalog.catalog",
                "contractVersion": catalog_module.CONTRACT_VERSION,
                "catalogHash": hashlib.sha256(json_text(catalog).encode("utf-8")).hexdigest(),
                "catalogMetadata": {k: v for k, v in catalog.items() if k != "nodes"},
                "nodes": nodes[offset : offset + limit],
                "parserSupport": support,
                "offset": offset,
                "limit": limit,
                "total": len(nodes),
                "nextOffset": next_offset if next_offset < len(nodes) else None,
                "evidence": "ReviewedSdkCatalogMetadata",
                "ownerValidated": False,
                "semantics": [
                    "Catalog nodes are C++ helper definitions, not executed app services.",
                    "Listed/implemented does not mean lowered by this parser or hardware available.",
                    "Catalog profile tab5 is metadata, not a validated canvas target ID.",
                    "Parser signatures require explicit caller assertions; no automatic SDK binding.",
                ],
            },
        )
    except Exception:
        return error_receipt(
            LIST_SDK, "Unavailable", "Reviewed SDK catalog or parser metadata is unavailable."
        )
