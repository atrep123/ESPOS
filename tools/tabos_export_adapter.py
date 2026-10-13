"""Strict selected-scene conversion, not an editor or runtime activation.

The envelope retains the complete source and opaque code_blocks for lossless
source roundtrip. This is opaque retention, NOT code-to-block conversion.
Code blocks are never executed or sent to Studio; their language metadata is
not reinterpreted. Coordinates are flat; parent/children metadata is rejected
until an explicit parent-relative contract exists. Optional Studio checking
uses an explicit developer checkout or the application's pinned, in-memory
backend and returns generated C++ in memory.
"""

from __future__ import annotations

import copy
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_OMITTED = object()


@dataclass(frozen=True)
class StudioBackend:
    """Application-supplied trusted implementation, never scene-selected Python.

    Bundled applications bind these functions to their exact pinned Studio
    package. JSON/project metadata cannot select modules or callbacks. This is
    an in-memory generator interface, not runtime, hardware or compiler proof.
    """

    touch_rules_from_tokens: Callable[[object], tuple[int, int]]
    validate_scene: Callable[[dict, tuple[int, int]], list[str]]
    generate: Callable[[dict, tuple[int, int]], str]
    default_touch_rules: tuple[int, int]


class AdapterError(ValueError):
    def __init__(self, diagnostics):
        self.diagnostics = tuple(diagnostics)
        super().__init__("\n".join(self.diagnostics))


@dataclass(frozen=True)
class Export:
    scene: dict
    id_map: dict[str, str]
    source_document: dict
    source_bytes: bytes | None
    source_text: str | None
    generated_cpp: str | None = None

    def restore_document(self):
        """Restore source, not reverse-apply edits to the converted scene."""
        return copy.deepcopy(self.source_document)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdapterError([f"JSON: duplicate key {key!r}; resolve before export"])
        result[key] = value
    return result


def _reject_constant(_token):
    raise AdapterError(["JSON: non-finite numeric values are unsupported"])


def _unsupported(obj, allowed, path, errors):
    for key in obj:
        if key not in allowed:
            errors.append(f"{path}.{key}: unsupported metadata; explicit mapping required")


def _check_depth(value):
    """Bound source copying, including opaque metadata, without recursion."""
    pending = [(value, 0, frozenset())]
    while pending:
        node, depth, ancestors = pending.pop()
        if isinstance(node, float) and not math.isfinite(node):
            raise AdapterError(["JSON: non-finite numeric values are unsupported"])
        if not isinstance(node, (dict, list)):
            continue
        if depth > 128 or id(node) in ancestors:
            raise AdapterError(["document depth exceeds 128 or contains a cyclic structure"])
        lineage = ancestors | {id(node)}
        children = node.values() if isinstance(node, dict) else node
        pending.extend((child, depth + 1, lineage) for child in children)


def adapt_document(
    document,
    scene_name,
    *,
    actions=None,
    states=None,
    studio_root=None,
    owner_tokens=None,
    studio_backend=None,
    owner_token_data=_OMITTED,
):
    """Atomic conversion; owner_tokens requires an explicit Studio checkout.

    Omitted tokens retain documented standalone snapshot v1 (81/58). Supplied
    tokens are read by Studio's actual load_touch_rules, with no fallback.
    """
    if studio_root is not None and studio_backend is not None:
        raise AdapterError(["studio_backend: cannot combine bundled backend and developer root"])
    if owner_tokens is not None and studio_root is None and studio_backend is None:
        raise AdapterError(["owner_tokens: explicit studio_root required; no fallback"])
    if owner_token_data is not _OMITTED and (studio_backend is None or owner_tokens is not None):
        raise AdapterError(["owner_token_data: requires bundled backend and no token path"])
    try:
        return _adapt_document(
            document,
            scene_name,
            actions=actions,
            states=states,
            studio_root=studio_root,
            owner_tokens=owner_tokens,
            studio_backend=studio_backend,
            owner_token_data=owner_token_data,
        )
    except RecursionError as exc:
        raise AdapterError(["document depth exceeds safe parser/copy limits"]) from exc


def _adapt_document(
    document,
    scene_name,
    *,
    actions,
    states,
    studio_root,
    owner_tokens,
    studio_backend,
    owner_token_data,
):
    """Convert an explicitly selected legacy scene atomically.

    actions uses original widget IDs. Missing action/state metadata must be
    supplied by the caller, never inferred. Exact supported kinds are label,
    container, tile and button; no panel/box aliases or style erasure.
    """
    source_bytes = document if isinstance(document, bytes) else None
    try:
        if not isinstance(document, (str, bytes)):
            _check_depth(document)
        source = (
            json.loads(document, object_pairs_hook=_unique, parse_constant=_reject_constant)
            if isinstance(document, (str, bytes))
            else copy.deepcopy(document)
        )
        _check_depth(source)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, AdapterError):
            raise
        raise AdapterError([f"JSON: {exc}"]) from exc
    if not isinstance(source, dict):
        raise AdapterError(["document: expected object"])
    errors = []
    _unsupported(
        source, {"width", "height", "scenes", "groups", "device", "code_blocks"}, "document", errors
    )
    if source.get("groups") not in (None, {}):
        errors.append("document.groups: group semantics require explicit mapping")
    if "device" in source and source["device"] != "tab5":
        errors.append("document.device: only explicit tab5 is supported")
    if not isinstance(scene_name, str) or not scene_name:
        errors.append("scene_name: explicit nonempty selection required")
    scenes = source.get("scenes")
    if isinstance(scenes, dict):
        selected = scenes.get(scene_name) if isinstance(scene_name, str) else None
    elif isinstance(scenes, list):
        matches = [
            s for s in scenes if isinstance(s, dict) and s.get("name", s.get("id")) == scene_name
        ]
        if len(matches) != 1:
            errors.append("scenes: selection must resolve exactly once")
        selected = matches[0] if len(matches) == 1 else None
    else:
        selected = None
    if not isinstance(selected, dict):
        raise AdapterError([*errors, f"scenes: unknown/invalid selection {scene_name!r}"])
    _unsupported(
        selected,
        {"name", "id", "description", "width", "height", "widgets", "states", "code_blocks"},
        "scene",
        errors,
    )
    for field, expected in (("width", 1280), ("height", 720)):
        value = selected.get(field, source.get(field))
        if type(value) is not int or value != expected:
            errors.append(f"scene.{field}: requires explicit Tab5 {expected}")
    scene = {"name": scene_name, "width": 1280, "height": 720, "widgets": []}
    if "description" in selected:
        if not isinstance(selected["description"], str):
            errors.append("scene.description: expected string")
        else:
            scene["description"] = selected["description"]
    if states is not None and "states" in selected and states != selected["states"]:
        errors.append("scene.states: caller metadata conflicts with source")
    real_states = selected.get("states") if states is None else states
    if not isinstance(real_states, list):
        errors.append("scene.states: caller must supply actual error/unavailable metadata")
    else:
        kinds = set()
        for i, state in enumerate(real_states):
            if not isinstance(state, dict):
                errors.append(f"states[{i}]: expected object")
                continue
            _unsupported(state, {"kind", "description"}, f"states[{i}]", errors)
            kind = state.get("kind")
            if not isinstance(kind, str) or kind not in {"normal", "error", "unavailable"}:
                errors.append(f"states[{i}].kind: unsupported state")
            else:
                kinds.add(kind)
            if "description" in state and not isinstance(state["description"], str):
                errors.append(f"states[{i}].description: expected string")
        if not {"error", "unavailable"} <= kinds:
            errors.append("scene.states: actual error and unavailable metadata required")
        scene["states"] = copy.deepcopy(real_states)
    if actions is None:
        actions = {}
    if not isinstance(actions, dict):
        errors.append("actions: expected original-ID to real action mapping")
        actions = {}
    widgets = selected.get("widgets")
    if not isinstance(widgets, list) or not widgets:
        raise AdapterError([*errors, "scene.widgets: nonempty array required"])
    ids = {}
    used_actions = set()
    for i, widget in enumerate(widgets):
        where = f"widgets[{i}]"
        if not isinstance(widget, dict):
            errors.append(f"{where}: expected object")
            continue
        _unsupported(
            widget,
            {
                "_widget_id",
                "id",
                "type",
                "x",
                "y",
                "width",
                "height",
                "z_index",
                "text",
                "font_size",
                "action",
            },
            where,
            errors,
        )
        wid = widget.get("_widget_id", widget.get("id"))
        if not isinstance(wid, str) or not wid:
            errors.append(f"{where}: stable nonempty source id required")
            continue
        if "_widget_id" in widget and "id" in widget and widget["id"] != wid:
            errors.append(f"{where}: id aliases conflict")
        if wid in ids:
            errors.append(f"{where}: duplicate source id {wid!r}")
            continue
        # Injective UTF-8 encoding, independent of list order and punctuation.
        try:
            ids[wid] = "w_" + wid.encode("utf-8").hex()
        except UnicodeError:
            errors.append(f"{where}: id must be valid UTF-8")
            continue
        kind = widget.get("type")
        if not isinstance(kind, str) or kind not in {"label", "container", "tile", "button"}:
            errors.append(f"{where}.type: unsupported {kind!r}; no implicit widget substitution")
            continue
        node = {"id": ids[wid], "type": kind}
        for old, new, minimum in (
            ("x", "x", 0),
            ("y", "y", 0),
            ("width", "w", 1),
            ("height", "h", 1),
        ):
            value = widget.get(old)
            if type(value) is not int or not minimum <= value <= 32767:
                errors.append(f"{where}.{old}: integer {minimum}..32767 required")
            else:
                node[new] = value
        for position, size, bound in (("x", "w", 1280), ("y", "h", 720)):
            if position in node and size in node and node[position] + node[size] > bound:
                errors.append(f"{where}: rectangle exceeds Tab5 canvas")
        layer = widget.get("z_index", 0)
        if type(layer) is not int or not -32768 <= layer <= 32767:
            errors.append(f"{where}.z_index: bounded integer required")
        else:
            node["layer"] = layer
        for old, new in (("text", "text"), ("font_size", "font_px")):
            if old in widget:
                value = widget[old]
                if kind == "container":
                    errors.append(f"{where}.{old}: container requires separate child label")
                elif old == "text" and not isinstance(value, str):
                    errors.append(f"{where}.text: expected string")
                elif old == "font_size" and (type(value) is not int or not 1 <= value <= 32767):
                    errors.append(f"{where}.font_size: positive bounded integer required")
                else:
                    node[new] = value
        action = actions.get(wid, widget.get("action"))
        if wid in actions:
            used_actions.add(wid)
            if "action" in widget and widget["action"] != action:
                errors.append(f"{where}.action: caller metadata conflicts with source")
        if kind in {"button", "tile"} or action is not None or "action" in widget:
            if kind not in {"button", "tile"}:
                errors.append(f"{where}.action: requires button/tile")
            elif not isinstance(action, str) or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_.:-]*", action
            ):
                errors.append(f"{where}.action: caller must supply real action token")
            else:
                node["action"] = action
            if (
                studio_root is None
                and studio_backend is None
                and "w" in node
                and "h" in node
                and min(node["w"], node["h"]) < 81
            ):
                errors.append(f"{where}: interactive target below standalone 81 px minimum")
        scene["widgets"].append(node)
    for wid in actions:
        if wid not in used_actions:
            errors.append(f"actions[{wid!r}]: unused metadata; select matching widget")
    if errors:
        raise AdapterError(errors)
    generated = (
        check_backend(
            scene, studio_backend, owner_tokens=owner_tokens, owner_token_data=owner_token_data
        )
        if studio_backend is not None
        else check_studio(scene, studio_root, owner_tokens=owner_tokens)
        if studio_root is not None
        else None
    )
    return Export(
        scene,
        ids,
        copy.deepcopy(source),
        source_bytes,
        document if isinstance(document, str) else None,
        generated,
    )


def check_backend(scene, backend, *, owner_tokens=None, owner_token_data=_OMITTED):
    """Run the pinned application's real validator/generator without a child.

    The optional token path is legacy data only; packaged callers pass a parsed,
    bounded JSON object instead. Unknown/invalid owner rules never fall back.
    """
    if not isinstance(backend, StudioBackend) or not all(
        callable(function)
        for function in (backend.touch_rules_from_tokens, backend.validate_scene, backend.generate)
    ):
        raise AdapterError(["studio_backend: trusted StudioBackend implementation required"])
    try:
        if owner_tokens is not None:
            path = Path(owner_tokens)
            if path.name.casefold() == "wifi_udaje.h" or not path.is_file():
                raise ValueError("owner tokens must be a regular JSON data file")
            with path.open("rb") as stream:
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("owner tokens exceed 1 MiB")
            owner_token_data = json.loads(
                raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_reject_constant
            )
        rules = (
            backend.default_touch_rules
            if owner_token_data is _OMITTED
            else backend.touch_rules_from_tokens(owner_token_data)
        )
        if (
            not isinstance(rules, (tuple, list))
            or len(rules) != 2
            or any(type(number) is not int or number < 1 for number in rules)
            or rules[1] > rules[0]
        ):
            raise ValueError("invalid positive target/floor rules")
        errors = backend.validate_scene(scene, rules)
        if not isinstance(errors, list) or any(not isinstance(error, str) for error in errors):
            raise ValueError("invalid Studio diagnostics")
        if errors:
            raise AdapterError([f"Studio: {error}" for error in errors])
        generated = backend.generate(scene, rules)
        if not isinstance(generated, str) or not generated.strip():
            raise ValueError("Studio returned no generated C++")
        generated.encode("utf-8", errors="strict")
        return generated
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, AdapterError):
            raise
        raise AdapterError([f"Studio check unavailable/failed: {exc}"]) from exc


def check_studio(scene, studio_root, *, owner_tokens=None):
    """Call actual validator/generator from explicit root, without file output.

    Studio's actual token parser/rules apply; omitted tokens use its standalone
    snapshot v1 (81/58). This checks C++ generation, not LVGL
    linking, real fonts, binding behavior or hardware support.
    """
    root = Path(studio_root).resolve()
    for name in ("tabos_design_check.py", "tabos_scene_codegen.py"):
        if not (root / "tools" / name).is_file():
            raise AdapterError([f"studio_root: missing tools/{name}; no fallback"])
    program = (
        "import sys,json; sys.path.insert(0,sys.argv[1]); "
        "from tabos_design_check import validate_scene,load_touch_rules,DEFAULT_TOUCH_RULES_V1; "
        "from tabos_scene_codegen import generate; "
        "rules=load_touch_rules(sys.argv[2]) if len(sys.argv)>2 else DEFAULT_TOUCH_RULES_V1; "
        "s=json.load(sys.stdin); e=validate_scene(s,rules); "
        "sys.stdout.write(json.dumps({'errors':e,'cpp':None if e else generate(s,rules)}))"
    )
    try:
        command = [sys.executable, "-B", "-c", program, str(root / "tools")]
        if owner_tokens is not None:
            command.append(str(Path(owner_tokens).resolve()))
        result = subprocess.run(
            command,
            input=json.dumps(scene),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode:
            raise AdapterError([f"Studio generation failed: {result.stderr.strip()}"])
        payload = json.loads(result.stdout)
        if payload["errors"]:
            raise AdapterError([f"Studio: {error}" for error in payload["errors"]])
        return payload["cpp"]
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
        if isinstance(exc, AdapterError):
            raise
        raise AdapterError([f"Studio check unavailable/failed: {exc}"]) from exc
