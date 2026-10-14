"""Detached caller-byte transformations over the genuine CodeGraph library.

No path, file, editor owner, native grant, execution, compiler or transport API.
Canonical parser owns all C++ semantics, regions, patches, stable IDs and fences.
This adapter only bounds/validates the envelope and verifies returned identities.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import math
import re

from espos_mcp import codegraph_readonly as source

CAPABILITIES = "get_cpp_transform_capabilities_v1"
OPERATIONS = {
    "list_cpp_regions_v1": "regions",
    "edit_cpp_v1": "edit",
    "construct_cpp_v1": "construct",
    "list_cpp_sdk_regions_v1": "sdkRegions",
    "construct_cpp_sdk_v1": "constructSdk",
}
MAX_REQUEST_BYTES = 524288
MAX_JSON_ITEMS = 32768
MAX_JSON_DEPTH = 24
MAX_EDITS = 64
MAX_TOKEN_BYTES = 256
MAX_CPP_BYTES = 4096
_HASH = re.compile(r"[0-9a-f]{64}")
_CONTEXT = set(source.ANALYZE_INPUT_SCHEMA["properties"])
_METHODS = (
    "construction_regions",
    "apply_edits",
    "apply_construction",
    "sdk_construction_regions",
    "apply_sdk_construction",
    "to_dict",
    "export_source",
)


def _reject(code="InvalidArgument", message="Invalid detached source request."):
    raise source._BoundaryError(code, message)


def _bounded_json(value, maximum=MAX_REQUEST_BYTES):
    """Strict JSON tree before copies/serialization/imports; cycles hit depth cap."""
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > MAX_JSON_DEPTH or count > MAX_JSON_ITEMS:
            _reject("LimitExceeded", "JSON shape exceeds the depth or item limit.")
        kind = type(item)
        if kind is dict:
            if len(item) > MAX_JSON_ITEMS:
                _reject("LimitExceeded", "JSON object exceeds the item limit.")
            if any(type(key) is not str for key in item):
                _reject()
            pending.extend((part, depth + 1) for pair in item.items() for part in pair)
        elif kind is list:
            if len(item) > MAX_JSON_ITEMS:
                _reject("LimitExceeded", "JSON array exceeds the item limit.")
            pending.extend((part, depth + 1) for part in item)
        elif kind is str:
            if len(item) > maximum:
                _reject("LimitExceeded", "JSON text exceeds the request limit.")
            if any(0xD800 <= ord(ch) <= 0xDFFF for ch in item):
                _reject()
        elif kind is int:
            if abs(item) > 9007199254740991:
                _reject()
        elif kind is float:
            if not math.isfinite(item):
                _reject()
        elif item is not None and kind is not bool:
            _reject()
    if len(source.json_text(value).encode("utf-8")) > maximum:
        _reject("LimitExceeded", "Structured request or result exceeds its byte limit.")


def _fragment(value, maximum):
    if type(value) is not str or not value.strip() or "\x00" in value:
        _reject()
    if len(value.encode("utf-8")) > maximum:
        _reject("LimitExceeded", "C++ fragment exceeds its byte limit.")


def _mutation(value, sdk):
    if type(value) is not dict:
        _reject()
    shapes = (
        {"insertSdkStatement": {"beforeNodeId", "cpp"}}
        if sdk
        else {
            "insertStatement": {"beforeNodeId", "cpp"},
            "deleteNode": {"nodeId"},
            "setSequence": {"nodeIds"},
        }
    )
    kind = value.get("kind")
    if type(kind) is not str or kind not in shapes:
        _reject()
    source._object(value, {"kind", "regionId"} | shapes[kind], {"kind", "regionId"} | shapes[kind])
    source._text(value["regionId"], 128)
    if kind in {"insertStatement", "insertSdkStatement"}:
        if value["beforeNodeId"] is not None:
            source._text(value["beforeNodeId"], 128)
        _fragment(value["cpp"], MAX_CPP_BYTES)
    elif kind == "deleteNode":
        source._text(value["nodeId"], 128)
    else:
        ids = value["nodeIds"]
        if type(ids) is not list or len(ids) > source.MAX_GRAPH_NODES:
            _reject()
        for node_id in ids:
            source._text(node_id, 128)
        if len(ids) != len(set(ids)):
            _reject()


def _input(operation, request):
    _bounded_json(request)
    if type(operation) is not str or operation not in OPERATIONS:
        _reject()
    api = OPERATIONS[operation]
    required = {"schemaVersion", "sourceBase64", "entries", "graph", "expectedSourceHash"}
    if api == "edit":
        required.add("edits")
    if api in {"construct", "constructSdk"}:
        required.add("mutation")
    source._object(request, required | _CONTEXT, required)
    if type(request["schemaVersion"]) is not int or request["schemaVersion"] != 1:
        _reject()
    raw, context, observation = source._analyze_input(
        {key: request[key] for key in _CONTEXT if key in request}
    )
    if api in {"sdkRegions", "constructSdk"} and context.get("sdkProfile") != source.SDK_PROFILE:
        _reject(message="SDK regions/construction require the explicit reviewed SDK profile.")
    expected = request["expectedSourceHash"]
    if type(expected) is not str or _HASH.fullmatch(expected) is None:
        _reject()
    graph = request["graph"]
    if (
        type(graph) is not dict
        or type(graph.get("nodes")) is not list
        or type(graph.get("edges")) is not list
    ):
        _reject()
    if len(graph["nodes"]) > source.MAX_GRAPH_NODES or len(graph["edges"]) > source.MAX_GRAPH_EDGES:
        _reject("LimitExceeded", "Graph exceeds the node or edge limit.")
    identity = source._identity(raw)
    if expected != identity["sha256"] or graph.get("sourceHash") != expected:
        _reject("Conflict", "Source bytes, expected hash and snapshot hash must match.")
    if api == "edit":
        edits = request["edits"]
        if type(edits) is not list or len(edits) > MAX_EDITS:
            _reject()
        seen = set()
        for edit in edits:
            wire = type(edit) is dict and edit.get("kind") == "rewireDataInput"
            fields = (
                {"kind", "regionId", "nodeId", "slotId", "sourceNodeId"}
                if wire
                else {"nodeId", "slotId", "replacement"}
            )
            source._object(edit, fields, fields)
            key = (source._text(edit["nodeId"], 128), source._text(edit["slotId"], 128))
            if key in seen:
                _reject()
            seen.add(key)
            if wire:
                source._text(edit["regionId"], 128)
                source._text(edit["sourceNodeId"], 128)
            else:
                _fragment(edit["replacement"], MAX_TOKEN_BYTES)
    elif api in {"construct", "constructSdk"}:
        _mutation(request["mutation"], api == "constructSdk")
    return raw, context, observation


def _library():
    graph, _catalog = source._libraries()
    if (
        not callable(getattr(graph, "restore_graph", None))
        or not callable(getattr(graph, "validate_graph", None))
        or not all(callable(getattr(graph.CodeGraph, name, None)) for name in _METHODS)
    ):
        raise source._Unavailable()
    return graph


def _snapshot(library, instance, raw, context):
    document = instance.to_dict()
    if type(raw) is not bytes or len(raw) > source.MAX_SOURCE_BYTES:
        _reject("LimitExceeded", "Returned source exceeds its byte limit.")
    if (
        document.get("sourceHash") != hashlib.sha256(raw).hexdigest()
        or document.get("byteLength") != len(raw)
        or document.get("entries") != context["entries"]
        or document.get("schemaVersion") != library.SCHEMA_VERSION
        or document.get("catalogVersion") != library.CATALOG_VERSION
        or document.get("sdkProfile") != context.get("sdkProfile")
    ):
        _reject("IntegrityError", "Backend returned inconsistent source identity or context.")
    if (
        len(document["nodes"]) > source.MAX_GRAPH_NODES
        or len(document["edges"]) > source.MAX_GRAPH_EDGES
    ):
        _reject("LimitExceeded", "Returned graph exceeds the node or edge limit.")
    library.validate_graph(document)
    if any(item["severity"] == "error" for item in document["diagnostics"]):
        _reject(
            "ParserRejected",
            "Source has syntax or selection diagnostics; no transformed buffer returned.",
        )
    opaque = {}
    for node in document["nodes"]:
        if node["kind"] == "opaque":
            span = node["sourceSpan"]
            chunk = raw[span["startByte"] : span["endByte"]]
            if (
                node["ports"]
                or node["editSlots"]
                or hashlib.sha256(chunk).hexdigest() != span["sha256"]
            ):
                _reject("IntegrityError", "Opaque source verification failed.")
            opaque[node["id"]] = chunk
    return document, opaque


def _data_wires(instance):
    """Fresh backend-owned allowlist. A legacy peer advertises nothing."""
    method = getattr(instance, "data_wire_inputs", None)
    if not callable(method):
        return {}
    inputs = method()
    if type(inputs) is not list:
        _reject("IntegrityError", "Backend returned invalid scalar wire capabilities.")
    return {"dataWireVersion": 1, "dataWireInputs": inputs}


def transform_receipt(operation, request):
    """No source execution/IO: restore full graph, delegate one real transaction."""
    identity = None
    try:
        raw, context, observation = _input(operation, request)
        identity = source._identity(raw)
        library = _library()
        versions = source._parser_dependencies()
    except source._BoundaryError as error:
        safe_operation = (
            operation if type(operation) is str and operation in OPERATIONS else "transform_cpp_v1"
        )
        return source.error_receipt(safe_operation, error.code, error.message)
    except (source._Unavailable, AttributeError):
        return source.error_receipt(
            operation,
            "Unavailable",
            "Reviewed backend or pinned parser dependencies are unavailable.",
            identity,
        )
    try:
        original = library.restore_graph(
            raw,
            copy.deepcopy(request["graph"]),
            entries=context["entries"],
            bindings=context.get("bindings"),
            event_bindings=context.get("eventBindings"),
            sdk_profile=context.get("sdkProfile"),
        )
        before, opaque_before = _snapshot(library, original, original.export_source(), context)
        # Python equality equates True/1 and 1.0/1. Compare the strict JSON
        # representation as well; detached snapshot types are not coercible.
        if original.export_source() != raw or source.json_text(before) != source.json_text(
            request["graph"]
        ):
            _reject(
                "IntegrityError", "Backend did not restore the exact caller snapshot and bytes."
            )
        api, result = OPERATIONS[operation], original
        kwargs = {"expected_source_hash": request["expectedSourceHash"], "current_source": raw}
        if api == "edit":
            wires = _data_wires(original)
            for edit in request["edits"]:
                if edit.get("kind") != "rewireDataInput":
                    continue
                capability = next(
                    (
                        c
                        for c in wires.get("dataWireInputs", [])
                        if (c["regionId"], c["nodeId"], c["slotId"])
                        == (edit["regionId"], edit["nodeId"], edit["slotId"])
                    ),
                    None,
                )
                if capability is None or edit["sourceNodeId"] not in capability["sourceNodeIds"]:
                    _reject(
                        "ParserRejected",
                        "Scalar wire source/input is not approved by this fresh backend snapshot.",
                    )
            result = original.apply_edits(copy.deepcopy(request["edits"]), **kwargs)
        elif api == "construct":
            result = original.apply_construction(copy.deepcopy(request["mutation"]), **kwargs)
        elif api == "constructSdk":
            result = original.apply_sdk_construction(copy.deepcopy(request["mutation"]), **kwargs)
        output = result.export_source()
        after, opaque_after = _snapshot(library, result, output, context)
        if (
            opaque_before != opaque_after
            or original.export_source() != raw
            or source.json_text(original.to_dict()) != source.json_text(before)
        ):
            _reject(
                "IntegrityError", "Backend changed opaque bytes or the original detached snapshot."
            )
        data = {
            "sourceBase64": base64.b64encode(output).decode("ascii"),
            "graph": after,
            "beforeSourceIdentity": identity,
            "sourceIdentity": source._identity(output),
            "sourceChanged": output != raw,
            "parseContext": context,
            "observation": observation,
            "identityOrigin": "caller-asserted" if observation else "not-supplied",
            "ownerValidated": False,
            "targetRegistryValidated": False,
            "filesystemWritten": False,
            "evidence": "DetachedCallerBytes",
            "backend": {
                "schemaVersion": library.SCHEMA_VERSION,
                "catalogVersion": library.CATALOG_VERSION,
                "dependencies": versions,
                "operation": api,
            },
            "semantics": [
                "No owner adoption, file write, native grant or event registration.",
                "Exact snapshot IDs are detached caller state, not a session/ABA lock.",
                "C++ syntax subset and explicit bindings only; no compiler/HW success asserted.",
            ],
        }
        if api in {"regions", "construct"}:
            data.update(constructionVersion=1, regions=result.construction_regions())
        data.update(_data_wires(result))
        if api in {"sdkRegions", "constructSdk"}:
            data.update(sdkConstructionVersion=1, sdkRegions=result.sdk_construction_regions())
        if api in {"construct", "constructSdk"}:
            old_ids, new_ids = {n["id"] for n in before["nodes"]}, {n["id"] for n in after["nodes"]}
            data["changeSet"] = {
                "insertedNodeIds": sorted(new_ids - old_ids),
                "removedNodeIds": sorted(old_ids - new_ids),
            }
        _bounded_json(data, source.MAX_RESPONSE_BYTES)
        return source._success(operation, data)
    except source._BoundaryError as error:
        return source.error_receipt(operation, error.code, error.message, identity)
    except library.GraphError:
        return source.error_receipt(
            operation,
            "ParserRejected",
            "Backend rejected snapshot, context or transaction; no transformed buffer returned.",
            identity,
        )
    except Exception:
        return source.error_receipt(
            operation,
            "Unavailable",
            "Detached transformation did not complete; no transformed buffer returned.",
            identity,
        )


def capabilities_receipt():
    """Actual source/API metadata only; does not import/claim native parser readiness."""
    try:
        graph = _library()
        installed = {name: source.metadata.version(name) for name in source.PARSER_DEPENDENCIES}
        return source._success(
            CAPABILITIES,
            {
                "backend": "tools.tabos_code_graph.CodeGraph",
                "schemaVersion": graph.SCHEMA_VERSION,
                "catalogVersion": graph.CATALOG_VERSION,
                "sdkProfile": graph.SDK_PROFILE,
                "operations": OPERATIONS.copy(),
                "backendStatus": "SourceContractPresent",
                "requiredDependencies": source.PARSER_DEPENDENCIES.copy(),
                "installedVersions": installed,
                "dependencyVersionsMatch": installed == source.PARSER_DEPENDENCIES,
                "nativeParserProbed": False,
                "runtimeAvailability": "Unverified",
                "dataWireVersion": 1
                if callable(getattr(graph.CodeGraph, "data_wire_inputs", None))
                else None,
                "registration": "ExplicitCandidateRegistrationOnly",
                "defaultReadOnlyProfileWidened": False,
                "limits": {
                    "sourceBytes": source.MAX_SOURCE_BYTES,
                    "requestBytes": MAX_REQUEST_BYTES,
                    "responseBytes": source.MAX_RESPONSE_BYTES,
                    "edits": MAX_EDITS,
                    "tokenBytes": MAX_TOKEN_BYTES,
                    "cppFragmentBytes": MAX_CPP_BYTES,
                    "jsonDepth": MAX_JSON_DEPTH,
                    "jsonItems": MAX_JSON_ITEMS,
                },
                "semantics": [
                    "In-memory output is not a filesystem/editor write or native authorization.",
                    "Eligibility is recomputed by the actual parser from a full restored snapshot.",
                    "No arbitrary edges, SDK callback synthesis, unwrapping DataPoint or force-Live.",
                    "Use existing list_sdk_nodes_v1 for actual signatures; bindings remain explicit.",
                ],
            },
        )
    except Exception:
        return source.error_receipt(
            CAPABILITIES, "Unavailable", "Reviewed backend source/API metadata is unavailable."
        )
