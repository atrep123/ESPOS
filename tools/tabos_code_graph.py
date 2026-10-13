"""Lossless, selected C++ CST projection. Never executes, builds, or writes files.

Tree-sitter is a syntax parser, NOT a C++ type checker. Bindings are explicit
caller assertions about declarations/build context, never hardware discovery.
Raw bytes are authoritative; graph edits replace only advertised token spans.
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import re
import uuid
from collections import deque
from dataclasses import dataclass
from itertools import pairwise
from typing import Mapping, Sequence

SCHEMA_VERSION = 1
CATALOG_VERSION = "cpp-cst-subset-1"
_PRIMITIVES = {"bool", "int", "float", "double"}
SDK_PROFILE = "tabos-sdk-minimal-1"
# Reviewed signatures from tabos_sdk_node_catalog.py. No implicit installation,
# receiver inference, or arbitrary caller-provided effects in this opt-in slice.
_SDK_OPERATIONS = {
    "espos_tabos_nodes::bind_click": {
        "operation": "espos.tabos.lvgl.click.bind.v1",
        "returnType": "lv_event_dsc_t*",
        "parameterTypes": ["lv_obj_t*", "lv_event_cb_t", "void*"],
    },
    "espos_tabos_nodes::set_label_text": {
        "operation": "espos.tabos.lvgl.label.text.v1",
        "returnType": "tabos::Status",
        "parameterTypes": ["lv_obj_t*", "const char*"],
    },
    "espos_tabos_nodes::sample_cpu_temperature": {
        "operation": "espos.tabos.metrics.cpu_temp.sample.v1",
        "returnType": "tabos::DataPoint<float>",
        "parameterTypes": ["tabos::ISystemMetrics&"],
    },
}
_SDK_PARAMETER_TYPES = {
    t.replace(" ", ""): t
    for t in (
        *_PRIMITIVES,
        "lv_obj_t*",
        "const char*",
        "lv_event_cb_t",
        "void*",
        "tabos::ISystemMetrics&",
    )
}
_SDK_STATES = {
    "tabos::DataState::" + state
    for state in ("Live", "Cached", "Estimated", "Mock", "Unavailable", "Error")
}


def _sdk_string(text):
    # One ordinary UTF-8 literal, no raw/prefixed/concatenated strings, NUL,
    # numeric escapes or line splicing. Never decode/re-encode original trivia.
    return bool(re.fullmatch(r'"(?:[^"\\\r\n\x00]|\\["\\nrt])*"', text))


def _sdk_parameter(param, source):
    if param.type != "parameter_declaration":
        return None
    typ, declarator = _field(param, "type"), _field(param, "declarator")
    if typ is None or declarator is None:
        return None
    identifier = declarator
    if declarator.type in {"pointer_declarator", "reference_declarator"}:
        children = _children(declarator)
        if len(children) != 1:
            return None
        identifier = children[0]
    if identifier.type != "identifier":
        return None
    if any(c not in (typ, declarator) and c.type != "type_qualifier" for c in _children(param)):
        return None
    spelling = "".join(
        _tokens(n, source)
        for n in _walk(param)
        if not n.children and n.type != "comment" and n != identifier
    )
    cpp_type = _SDK_PARAMETER_TYPES.get(spelling)
    return (_tokens(identifier, source), cpp_type) if cpp_type else None


class GraphError(ValueError):
    """Rejected transaction; the original CodeGraph/source is unchanged."""


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _id() -> str:
    return uuid.uuid4().hex


def _walk(node):
    pending = [node]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(reversed(current.children))


def _children(node):
    return [child for child in node.named_children if child.type != "comment"]


def _field(node, name):
    return node.child_by_field_name(name)


def _tokens(node, source):
    """Canonical spelling for explicit binding lookup, not semantic resolution."""
    return b"".join(
        source[n.start_byte : n.end_byte]
        for n in _walk(node)
        if not n.children and n.type != "comment"
    ).decode("utf-8")


def _plain_value_type(cpp_type):
    """No claimed auto deduction of references, pointers, qualifiers or placeholders."""
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9:<>, ]*", cpp_type)) and not re.search(
        r"\b(?:const|volatile|auto|decltype)\b", cpp_type
    )


def _bindings(value):
    result = copy.deepcopy(dict(value or {}))
    for callee, binding in result.items():
        if not isinstance(callee, str) or not callee or re.search(r"\s", callee):
            raise GraphError("Binding callee must have canonical, whitespace-free spelling")
        if not isinstance(binding, dict) or set(binding) != {
            "operation",
            "returnType",
            "parameterTypes",
        }:
            raise GraphError("Binding requires operation, returnType, parameterTypes only")
        if not all(isinstance(binding[k], str) and binding[k] for k in ("operation", "returnType")):
            raise GraphError("Binding operation/returnType must be nonempty strings")
        if not isinstance(binding["parameterTypes"], (list, tuple)) or not all(
            isinstance(t, str) and t and t != "void" for t in binding["parameterTypes"]
        ):
            raise GraphError("Binding parameterTypes must be explicit C++ type strings")
        binding["parameterTypes"] = list(binding["parameterTypes"])
    return result


@dataclass
class _Expression:
    cpp_type: str
    uses: list
    slots: list
    binding: dict | None = None


class _Projection:
    def __init__(self, source, entries, bindings, event_bindings, sdk_profile=None):
        try:
            import tree_sitter_cpp
            from tree_sitter import Language, Parser
        except ImportError as exc:
            raise GraphError(
                "Install the approved pinned Tree-sitter dependencies externally"
            ) from exc
        self.source = source
        self.source_hash = _sha(source)
        self.tree = Parser(Language(tree_sitter_cpp.language())).parse(source)
        self.nodes, self.edges, self.diagnostics = [], [], []
        self.bindings = bindings
        self.event_bindings = event_bindings
        self.sdk_profile = sdk_profile
        self.macros = set()
        for n in _walk(self.tree.root_node):
            if n.type in {"preproc_def", "preproc_function_def"}:
                name = _field(n, "name")
                if name is not None:
                    self.macros.add(_tokens(name, source))
        self._project(entries)

    def span(self, start, end):
        return {"startByte": start, "endByte": end, "sha256": _sha(self.source[start:end])}

    def diagnostic(self, code, message, node=None, severity="warning"):
        item = {"code": code, "message": message, "severity": severity}
        if node is not None:
            item["sourceSpan"] = self.span(node.start_byte, node.end_byte)
        self.diagnostics.append(item)

    def node(self, kind, syntax=None, *, start=None, end=None, **fields):
        if syntax is not None:
            start, end = syntax.start_byte, syntax.end_byte
        value = {
            "id": _id(),
            "kind": kind,
            "sourceSpan": self.span(start, end),
            "ports": [],
            "editSlots": [],
            **fields,
        }
        self.nodes.append(value)
        return value

    @staticmethod
    def port(node, name, kind, direction, cpp_type=None):
        value = {"id": name, "kind": kind, "direction": direction}
        if cpp_type is not None:
            value["cppType"] = cpp_type
        node["ports"].append(value)
        return (node["id"], name)

    def wire(self, kind, start, end):
        self.edges.append(
            {
                "id": _id(),
                "kind": kind,
                "from": {"nodeId": start[0], "portId": start[1]},
                "to": {"nodeId": end[0], "portId": end[1]},
            }
        )

    def opaque(self, syntax=None, *, start=None, end=None, reason="unsupported", scope="selected"):
        node = self.node(
            "opaque",
            syntax,
            start=start,
            end=end,
            preservation="exact-bytes",
            reason=reason,
            scope=scope,
        )
        if scope == "selected":
            self.diagnostic("opaque", reason, syntax)
        return node

    def slot(self, syntax, kind, **fields):
        return {"kind": kind, "sourceSpan": self.span(syntax.start_byte, syntax.end_byte), **fields}

    def has_macro(self, syntax):
        return any(
            _tokens(n, self.source) in self.macros
            for n in _walk(syntax)
            if not n.children and n.type != "comment"
        )

    def expression(self, syntax, env, *, allow_call=False):
        if syntax is None or self.has_macro(syntax):
            return None
        kind = syntax.type
        text = _tokens(syntax, self.source)
        if kind == "identifier" and text in env:
            typ, producer, immutable = env[text]
            return _Expression(typ, [(text, typ, producer)], [])
        if self.sdk_profile:
            if kind == "string_literal" and _sdk_string(text):
                return _Expression(
                    "const char*", [], [self.slot(syntax, "string", cppType="const char*")]
                )
            if kind == "qualified_identifier" and text in _SDK_STATES:
                if any(
                    _tokens(n, self.source) in self.local_names
                    for n in _walk(syntax)
                    if not n.children and n.type != "comment"
                ):
                    return None  # Conservative reservation; no qualified C++ lookup.
                return _Expression("tabos::DataState", [], [])
            if kind == "field_expression":
                argument, member = _field(syntax, "argument"), _field(syntax, "field")
                if (
                    argument is not None
                    and argument.type == "identifier"
                    and member is not None
                    and _tokens(member, self.source) == "state"
                    and any(c.type == "." for c in syntax.children)
                ):
                    base = self.expression(argument, env)
                    if base and base.cpp_type == "tabos::DataPoint<float>":
                        return _Expression("tabos::DataState", base.uses, [])
        if kind in {"true", "false"}:
            return _Expression("bool", [], [self.slot(syntax, "literal", cppType="bool")])
        if kind == "number_literal":
            typ = None
            if re.fullmatch(r"(?:0|[1-9][0-9]*)", text) and int(text) <= 2147483647:
                typ = "int"
            elif re.fullmatch(
                r"(?:[0-9]+\.[0-9]+(?:[eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+)[fF]?", text
            ):
                typ = "float" if text[-1] in "fF" else "double"
            if typ:
                return _Expression(typ, [], [self.slot(syntax, "literal", cppType=typ)])
            return None
        if kind == "parenthesized_expression":
            children = _children(syntax)
            return self.expression(children[0], env) if len(children) == 1 else None
        if kind == "unary_expression":
            operand = self.expression(_field(syntax, "argument"), env)
            operator = _field(syntax, "operator")
            op = _tokens(operator, self.source) if operator else ""
            if operand and operand.cpp_type in _PRIMITIVES and op in {"!", "+", "-"}:
                typ = (
                    "bool"
                    if op == "!"
                    else ("int" if operand.cpp_type == "bool" else operand.cpp_type)
                )
                return _Expression(typ, operand.uses, operand.slots)
            return None
        if kind == "binary_expression":
            left = self.expression(_field(syntax, "left"), env)
            right = self.expression(_field(syntax, "right"), env)
            operator = _field(syntax, "operator")
            op = _tokens(operator, self.source) if operator else ""
            if not left or not right or left.cpp_type != right.cpp_type:
                return None
            typ = left.cpp_type
            enum_equality = self.sdk_profile and typ == "tabos::DataState" and op in {"==", "!="}
            if typ not in _PRIMITIVES and not enum_equality:
                return None
            if op in {"==", "!=", "<", "<=", ">", ">=", "&&", "||"}:
                typ = "bool"
            elif op in {"+", "-", "*", "/"}:
                typ = "int" if typ == "bool" else typ
            elif op == "%" and typ == "int":
                pass
            else:
                return None
            return _Expression(typ, left.uses + right.uses, left.slots + right.slots)
        if kind != "call_expression" or not allow_call:
            return None
        function = _field(syntax, "function")
        arguments = _field(syntax, "arguments")
        if function is None or arguments is None:
            return None
        # The complete receiver spelling is explicitly bound. No overload search.
        callee = _tokens(function, self.source)
        if function.type == "identifier" and callee in self.local_names:
            return None  # A local may shadow a bound free function; no name lookup.
        binding = self.bindings.get(callee)
        if binding is None:
            return None
        if self.sdk_profile and any(
            _tokens(n, self.source) in self.local_names
            for n in _walk(function)
            if not n.children and n.type != "comment"
        ):
            return None  # Even a qualified catalog namespace may be shadowed.
        args = [self.expression(arg, env) for arg in _children(arguments)]
        if any(arg is None for arg in args):
            return None
        if [arg.cpp_type for arg in args] != binding["parameterTypes"]:
            return None
        leaf = function
        while leaf.type in {"field_expression", "qualified_identifier"}:
            leaf = _field(leaf, "field") or _field(leaf, "name")
            if leaf is None:
                return None
        if leaf.type not in {"identifier", "field_identifier"}:
            return None
        call_slot = self.slot(leaf, "call", callee=callee)
        return _Expression(
            binding["returnType"],
            [use for arg in args for use in arg.uses],
            [call_slot] + [slot for arg in args for slot in arg.slots],
            {"callee": callee, **binding},
        )

    def attach_expression(self, node, expression):
        node["cppType"] = expression.cpp_type
        node["typeEvidence"] = "explicit-binding" if expression.binding else "restricted-syntax"
        if expression.binding:
            node["binding"] = expression.binding
        for i, slot in enumerate(expression.slots):
            node["editSlots"].append({"id": f"token-{i}", **slot})
        seen = set()
        for name, typ, producer in expression.uses:
            if name not in seen:
                target = self.port(node, f"use:{name}", "data", "in", typ)
                self.wire("data", producer, target)
                seen.add(name)

    def sequence(self, statements, env, tails):
        for syntax in statements:
            if syntax.type == "comment":
                continue
            if syntax.type == "if_statement" and not self.has_macro(syntax):
                condition = _field(syntax, "condition")
                expression = self.expression(_field(condition, "value"), env) if condition else None
                # No condition initializers/declarations, constexpr, or extensions.
                tokens = [n.type for n in syntax.children if not n.is_named]
                if (
                    expression
                    and expression.cpp_type in _PRIMITIVES
                    and condition
                    and len(_children(condition)) == 1
                    and "constexpr" not in tokens
                    and "consteval" not in tokens
                ):
                    node = self.node("if", syntax)
                    self.attach_expression(node, expression)
                    incoming = self.port(node, "in", "execution", "in")
                    for tail in tails:
                        self.wire("execution", tail, incoming)
                    yes = self.port(node, "true", "execution", "out")
                    no = self.port(node, "false", "execution", "out")
                    consequence = _field(syntax, "consequence")
                    alternative = _field(syntax, "alternative")
                    then_env, else_env = dict(env), dict(env)
                    yes_tails = self.branch(consequence, then_env, [yes])
                    no_tails = self.branch(alternative, else_env, [no]) if alternative else [no]
                    # No invented phi nodes: invalidate variables changed in either branch.
                    for name in list(env):
                        if then_env.get(name) != env[name] or else_env.get(name) != env[name]:
                            del env[name]
                    tails = yes_tails + no_tails
                    continue
            kind, expression, name, immutable = None, None, None, False
            if syntax.type == "declaration" and not self.has_macro(syntax):
                typ = _field(syntax, "type")
                declarator = _field(syntax, "declarator")
                children = _children(syntax)
                qualifiers = [c for c in children if c.type == "type_qualifier"]
                allowed_children = [typ, declarator, *qualifiers]
                if (
                    typ is not None
                    and declarator is not None
                    and declarator.type == "init_declarator"
                    and all(c in allowed_children for c in children)
                    and all(_tokens(q, self.source) == "const" for q in qualifiers)
                ):
                    identifier = _field(declarator, "declarator")
                    if identifier is not None and identifier.type == "identifier":
                        expression = self.expression(
                            _field(declarator, "value"), env, allow_call=True
                        )
                        declared = _tokens(typ, self.source)
                        if (
                            expression
                            and expression.cpp_type != "void"
                            and (
                                (
                                    declared == "auto"
                                    and (
                                        _plain_value_type(expression.cpp_type)
                                        or (
                                            self.sdk_profile
                                            and expression.binding
                                            and expression.cpp_type == "lv_event_dsc_t*"
                                        )
                                    )
                                )
                                or (declared in _PRIMITIVES and declared == expression.cpp_type)
                            )
                        ):
                            kind, name = "declaration", _tokens(identifier, self.source)
                            immutable = bool(qualifiers)
            elif syntax.type == "expression_statement":
                children = _children(syntax)
                child = children[0] if len(children) == 1 else None
                if child is not None and child.type == "call_expression":
                    expression = self.expression(child, env, allow_call=True)
                    if expression:
                        kind = "call"
                elif child is not None and child.type == "assignment_expression":
                    left, operator = _field(child, "left"), _field(child, "operator")
                    if left is not None and left.type == "identifier" and operator is not None:
                        name = _tokens(left, self.source)
                        expression = self.expression(_field(child, "right"), env, allow_call=True)
                        if (
                            name in env
                            and not env[name][2]
                            and expression
                            and expression.cpp_type in _PRIMITIVES
                            and expression.cpp_type == env[name][0]
                            and _tokens(operator, self.source) == "="
                        ):
                            kind = "assignment"
            if not kind:
                self.opaque(syntax, reason=f"Unsupported or unresolved {syntax.type}")
                env.clear()  # An opaque statement may mutate or escape any visible value.
                tails = []  # Do not guess whether it falls through, returns, or throws.
                continue
            node = self.node(kind, syntax)
            self.attach_expression(node, expression)
            incoming = self.port(node, "in", "execution", "in")
            for tail in tails:
                self.wire("execution", tail, incoming)
            tails = [self.port(node, "next", "execution", "out")]
            if kind in {"declaration", "assignment"}:
                node["variable"] = name
                producer = self.port(node, "value", "data", "out", expression.cpp_type)
                env[name] = (expression.cpp_type, producer, immutable)
            if expression.binding and not self.sdk_profile:
                # Bound external calls have unknown effects; don't assume other locals
                # remain unmodified through globals/references held by the callee.
                env = self.retain_local_result(
                    env, name if kind in {"declaration", "assignment"} else None
                )
        return tails

    @staticmethod
    def retain_local_result(env, name):
        retained = {name: env[name]} if name is not None and name in env else {}
        env.clear()
        env.update(retained)
        return env

    def branch(self, syntax, env, tails):
        if syntax.type == "else_clause":
            children = _children(syntax)
            if len(children) != 1:
                self.opaque(syntax, reason="Unsupported else clause")
                env.clear()
                return []
            syntax = children[0]
        return self.sequence(
            _children(syntax) if syntax.type == "compound_statement" else [syntax], env, tails
        )

    def _project(self, entries):
        root = self.tree.root_node
        if root.has_error:
            for node in _walk(root):
                if node.type == "ERROR" or node.is_missing:
                    self.diagnostic(
                        "invalid-cpp", f"CST {node.type}: invalid/missing syntax", node, "error"
                    )
            self.opaque(
                start=0, end=len(self.source), reason="Invalid C++ CST", scope="outside-selection"
            )
            return
        candidates = {}
        for node in _walk(root):
            if node.type != "function_definition":
                continue
            ancestor = node.parent
            excluded = False
            while ancestor is not None:
                if ancestor.type in {
                    "template_declaration",
                    "lambda_expression",
                } or ancestor.type.startswith("preproc_"):
                    excluded = True
                ancestor = ancestor.parent
            declarator = _field(node, "declarator")
            if excluded or declarator is None or declarator.type != "function_declarator":
                continue
            name = _field(declarator, "declarator")
            if name is not None:
                candidates.setdefault(_tokens(name, self.source), []).append(node)
        bodies = []
        for name in entries:
            found = candidates.get(name, [])
            if len(found) != 1:
                self.diagnostic(
                    "entry-selection",
                    f"Entry {name!r}: expected one non-template function, found {len(found)}",
                    severity="error",
                )
                continue
            function = found[0]
            body = _field(function, "body")
            if body is None or body.type != "compound_statement":
                self.diagnostic(
                    "entry-selection", f"Entry {name!r} has no plain body", function, "error"
                )
                continue
            bodies.append((body.start_byte + 1, body.end_byte - 1))
            entry = self.node("entry", body, function=name)
            # Conservative over-approximation across nested scopes. Unknown local
            # types/callables do not turn into similarly named bound free functions.
            self.local_names = set()
            for declaration in _walk(function):
                if declaration.type == "structured_binding_declarator":
                    self.local_names.update(
                        _tokens(n, self.source)
                        for n in _walk(declaration)
                        if n.type == "identifier"
                    )
                if declaration.type not in {
                    "parameter_declaration",
                    "declaration",
                    "init_declarator",
                }:
                    continue
                for local in declaration.children_by_field_name("declarator"):
                    while local is not None and local.type != "identifier":
                        local = _field(local, "declarator")
                    if local is not None:
                        self.local_names.add(_tokens(local, self.source))
            if name in self.event_bindings:
                self.port(entry, "event", "event", "in")
                entry["eventBinding"] = self.event_bindings[name]
            env = {}
            declarator = _field(function, "declarator")
            parameters = _field(declarator, "parameters")
            if self.sdk_profile:
                entry["sdkParametersProven"] = True
            for param in _children(parameters) if parameters else []:
                if self.sdk_profile:
                    proven = (
                        _sdk_parameter(param, self.source) if not self.has_macro(param) else None
                    )
                    if proven is None:
                        entry["sdkParametersProven"] = False
                        continue
                    symbol, cpp_type = proven
                    if symbol in env:
                        entry["sdkParametersProven"] = False
                    self.local_names.add(symbol)
                    producer = self.port(entry, f"parameter:{symbol}", "data", "out", cpp_type)
                    env[symbol] = (cpp_type, producer, False)
                    continue
                typ, identifier = _field(param, "type"), _field(param, "declarator")
                if (
                    param.type == "parameter_declaration"
                    and typ is not None
                    and identifier is not None
                    and identifier.type == "identifier"
                    and _tokens(typ, self.source) in _PRIMITIVES
                    and not self.has_macro(param)
                    and all(c in [typ, identifier] for c in _children(param))
                ):
                    symbol = _tokens(identifier, self.source)
                    cpp_type = _tokens(typ, self.source)
                    producer = self.port(entry, f"parameter:{symbol}", "data", "out", cpp_type)
                    env[symbol] = (cpp_type, producer, False)
            tail = self.port(entry, "next", "execution", "out")
            self.sequence(_children(body), env, [tail])
        cursor = 0
        for start, end in sorted(bodies):
            if start < cursor:
                self.diagnostic(
                    "entry-overlap", "Selected function bodies overlap", severity="error"
                )
                continue
            if cursor < start:
                self.opaque(
                    start=cursor, end=start, scope="outside-selection", reason="Not selected"
                )
            cursor = end
        if cursor < len(self.source):
            self.opaque(
                start=cursor, end=len(self.source), scope="outside-selection", reason="Not selected"
            )


def _validate_graph(graph: Mapping) -> None:
    """Validate topology only. Does not authorize arbitrary graph rewrites."""
    if graph.get("schemaVersion") != SCHEMA_VERSION:
        raise GraphError("Unsupported schemaVersion")
    nodes = graph.get("nodes", [])
    ports, node_ids = {}, set()
    for node in nodes:
        node_id = node["id"]
        if not isinstance(node_id, str) or not node_id or node_id in node_ids:
            raise GraphError("Duplicate node ID")
        node_ids.add(node_id)
        if node["kind"] == "opaque" and (node["ports"] or node["editSlots"]):
            raise GraphError("Opaque nodes cannot have inferred ports/edit slots")
        for port in node["ports"]:
            key = (node_id, port["id"])
            if (
                key in ports
                or port["kind"] not in {"data", "execution", "event"}
                or port["direction"] not in {"in", "out"}
            ):
                raise GraphError("Invalid or duplicate port")
            ports[key] = port
    adjacency = {n: set() for n in node_ids}
    degree = dict.fromkeys(node_ids, 0)
    edges, data_targets = set(), set()
    for edge in graph.get("edges", []):
        if edge["id"] in edges:
            raise GraphError("Duplicate edge ID")
        edges.add(edge["id"])
        start = (edge["from"]["nodeId"], edge["from"]["portId"])
        end = (edge["to"]["nodeId"], edge["to"]["portId"])
        if start not in ports or end not in ports:
            raise GraphError("Dangling edge")
        a, b = ports[start], ports[end]
        if (
            a["direction"] != "out"
            or b["direction"] != "in"
            or a["kind"] != b["kind"]
            or a["kind"] != edge["kind"]
        ):
            raise GraphError("Edge direction/kind mismatch")
        if edge["kind"] == "data":
            if not a.get("cppType") or a.get("cppType") != b.get("cppType") or end in data_targets:
                raise GraphError("Data type mismatch or multiple data drivers")
            data_targets.add(end)
        if end[0] not in adjacency[start[0]]:
            adjacency[start[0]].add(end[0])
            degree[end[0]] += 1
    pending = deque(n for n in node_ids if degree[n] == 0)
    visited = 0
    while pending:
        node = pending.popleft()
        visited += 1
        for target in adjacency[node]:
            degree[target] -= 1
            if degree[target] == 0:
                pending.append(target)
    if visited != len(node_ids):
        raise GraphError("Cycles are unsupported; source has not been rewritten")


def validate_graph(graph: Mapping) -> None:
    """Report malformed/dangling/cyclic topology as GraphError, never repair it."""
    try:
        _validate_graph(graph)
    except (KeyError, TypeError, AttributeError) as exc:
        raise GraphError("Malformed graph/port/edge record") from exc


class CodeGraph:
    """In-memory source authority; JSON is a detached frontend view, not executable."""

    def __init__(self, source, entries, bindings, event_bindings, projection):
        self._source = source
        self._tree = projection.tree
        self._entries = tuple(entries)
        self._bindings = copy.deepcopy(bindings)
        self._event_bindings = copy.deepcopy(event_bindings)
        self._sdk_profile = projection.sdk_profile
        self._document = {
            "schemaVersion": SCHEMA_VERSION,
            "catalogVersion": CATALOG_VERSION,
            "language": "C++",
            "sourceHash": _sha(source),
            "byteLength": len(source),
            "entries": list(entries),
            "nodes": projection.nodes,
            "edges": projection.edges,
            "diagnostics": projection.diagnostics,
            "projection": "partial" if projection.diagnostics else "complete",
            "typeChecking": "syntax-subset-and-explicit-bindings-only",
        }
        if self._sdk_profile:
            self._document["sdkProfile"] = self._sdk_profile
        validate_graph(self._document)

    @property
    def source_hash(self):
        return self._document["sourceHash"]

    @property
    def source_bytes(self):
        return self._source

    def export_source(self) -> bytes:
        return self._source

    def to_dict(self) -> dict:
        return copy.deepcopy(self._document)

    @staticmethod
    def _scalar_statement(node):
        return (
            node["kind"] in {"declaration", "assignment"}
            and node.get("cppType") in _PRIMITIVES
            and "binding" not in node
        )

    def _regions(self):
        """Internal eligibility proof. Public JSON cannot override this result."""
        if any(d["severity"] == "error" for d in self._document["diagnostics"]):
            return []
        nodes = self._document["nodes"]
        by_span = {
            (n["sourceSpan"]["startByte"], n["sourceSpan"]["endByte"]): n
            for n in nodes
            if n["kind"] != "entry"
        }
        result = []
        for entry in (n for n in nodes if n["kind"] == "entry"):
            span = entry["sourceSpan"]
            start, end = span["startByte"], span["endByte"]
            if any(
                n["kind"] == "opaque"
                and n.get("scope") == "selected"
                and start <= n["sourceSpan"]["startByte"] < n["sourceSpan"]["endByte"] <= end
                for n in nodes
            ):
                continue
            body = next(
                (
                    n
                    for n in _walk(self._tree.root_node)
                    if n.type == "compound_statement"
                    and n.start_byte == start
                    and n.end_byte == end
                ),
                None,
            )
            if body is None:
                continue

            def append_region(members, *, body_end=end, entry_id=entry["id"]):
                first = members[0]["sourceSpan"]["startByte"] if members else body_end - 1
                last = members[-1]["sourceSpan"]["endByte"] if members else body_end - 1
                member_ids = [n["id"] for n in members]
                region_key = f"{self.source_hash}:{entry_id}:{first}:{last}:{','.join(member_ids)}"
                operations = ["insertStatement"]
                if members:
                    operations.append("deleteNode")
                    if all(
                        not self._source[
                            a["sourceSpan"]["endByte"] : b["sourceSpan"]["startByte"]
                        ].strip()
                        for a, b in pairwise(members)
                    ):
                        operations.append("setSequence")
                result.append(
                    {
                        "id": uuid.uuid5(uuid.NAMESPACE_URL, region_key).hex,
                        "entryNodeId": entry_id,
                        "nodeIds": member_ids,
                        "sourceSpan": {
                            "startByte": first,
                            "endByte": last,
                            "sha256": _sha(self._source[first:last]),
                        },
                        "allowedOperations": operations,
                    }
                )

            statements = _children(body)
            members = []
            for statement in statements:
                node = by_span.get((statement.start_byte, statement.end_byte))
                if node is not None and self._scalar_statement(node):
                    members.append(node)
                else:
                    if members:
                        append_region(members)
                        members = []
            if members or not statements:
                append_region(members)
        return result

    def construction_regions(self) -> list[dict]:
        """Snapshot-scoped general-C++ construction regions; no inferred SDK nodes."""
        return self._regions()

    def sdk_construction_regions(self) -> list[dict]:
        """Opt-in insertion only; never expose unknown bodies or callback adapters.

        Each region is a whole selected void body, with top-level statement IDs
        as anchors. Calls/branches remain ordered; SDK deletion/reorder is absent.
        """
        if not self._sdk_profile or any(
            d["severity"] == "error" for d in self._document["diagnostics"]
        ):
            return []
        result = []
        for entry in self._document["nodes"]:
            if entry["kind"] != "entry" or not entry.get("sdkParametersProven"):
                continue
            span = entry["sourceSpan"]
            body = next(
                n
                for n in _walk(self._tree.root_node)
                if n.type == "compound_statement"
                and n.start_byte == span["startByte"]
                and n.end_byte == span["endByte"]
            )
            return_type = _field(body.parent, "type")
            if return_type is None or _tokens(return_type, self._source) != "void":
                continue
            inside = [
                n
                for n in self._document["nodes"]
                if n["kind"] != "entry"
                and n.get("scope") != "outside-selection"
                and span["startByte"] < n["sourceSpan"]["startByte"] < span["endByte"]
            ]
            if any(n["kind"] == "opaque" for n in inside):
                continue
            symbols = [
                p["id"][len("parameter:") :]
                for p in entry["ports"]
                if p["id"].startswith("parameter:")
            ]
            symbols += [n["variable"] for n in inside if n["kind"] == "declaration"]
            if len(symbols) != len(set(symbols)):
                continue  # No scope/name-lookup guesses, even for sibling branches.
            statements = _children(body)
            by_start = {n["sourceSpan"]["startByte"]: n for n in inside}
            if any(s.start_byte not in by_start for s in statements):
                continue
            ids = [by_start[s.start_byte]["id"] for s in statements]
            start, end = body.start_byte + 1, body.end_byte - 1
            key = f"{self._sdk_profile}:{self.source_hash}:{entry['id']}:{start}:{end}:{','.join(ids)}"
            result.append(
                {
                    "id": uuid.uuid5(uuid.NAMESPACE_URL, key).hex,
                    "entryNodeId": entry["id"],
                    "nodeIds": ids,
                    "allowedOperations": ["insertSdkStatement"],
                    "sourceSpan": {
                        "startByte": start,
                        "endByte": end,
                        "sha256": _sha(self._source[start:end]),
                    },
                }
            )
        return result

    def apply_sdk_construction(
        self, mutation: Mapping, *, expected_source_hash: str, current_source: bytes
    ) -> CodeGraph:
        """Insert one known catalog declaration or if tree, using ordinary C++.

        Envelope: {kind: insertSdkStatement, regionId, beforeNodeId: id|null, cpp}.
        Opaque bytes, order, existing IDs, fresh hashes and exact bindings remain
        authoritative. No registration/execution occurs while parsing/inserting.
        """
        if not self._sdk_profile:
            raise GraphError("SDK construction requires explicit SDK profile")
        return self._apply_construction(
            mutation,
            expected_source_hash=expected_source_hash,
            current_source=current_source,
            sdk=True,
        )

    def apply_construction(
        self, mutation: Mapping, *, expected_source_hash: str, current_source: bytes
    ) -> CodeGraph:
        """One atomic insertStatement/deleteNode/setSequence in a proven region."""
        return self._apply_construction(
            mutation, expected_source_hash=expected_source_hash, current_source=current_source
        )

    def _apply_construction(self, mutation, *, expected_source_hash, current_source, sdk=False):
        if (
            not isinstance(current_source, bytes)
            or current_source != self._source
            or expected_source_hash != self.source_hash
        ):
            raise GraphError("Stale source hash/bytes conflict; no overwrite")
        if not isinstance(mutation, Mapping):
            raise GraphError("mutation must be an object")
        kind = mutation.get("kind")
        fields = {
            "insertStatement": {"beforeNodeId", "cpp"},
            "deleteNode": {"nodeId"},
            "setSequence": {"nodeIds"},
        }
        if sdk:
            fields = {"insertSdkStatement": {"beforeNodeId", "cpp"}}
        if (
            not isinstance(kind, str)
            or kind not in fields
            or set(mutation) != {"kind", "regionId"} | fields[kind]
        ):
            raise GraphError("Unsupported construction kind/fields")
        regions = self.sdk_construction_regions() if sdk else self._regions()
        region = next((r for r in regions if r["id"] == mutation["regionId"]), None)
        if region is None:
            raise GraphError(
                "Unknown/stale region or selected body is not proven simple (opaque/error)"
            )
        if kind not in region["allowedOperations"]:
            raise GraphError(
                "Construction unavailable: empty region or ambiguous inter-statement comments"
            )
        nodes = {n["id"]: n for n in self._document["nodes"]}
        members = [nodes[node_id] for node_id in region["nodeIds"]]
        # (start, end, new bytes, origin ID for explicit moved statement identity)
        patches, removed = [], set()
        if kind == "deleteNode":
            if mutation["nodeId"] not in region["nodeIds"]:
                raise GraphError("Deletion target is outside the eligible region")
            node = nodes[mutation["nodeId"]]
            span = node["sourceSpan"]
            patches.append((span["startByte"], span["endByte"], b"", None))
            removed.add(node["id"])
        elif kind == "setSequence":
            order = mutation["nodeIds"]
            if (
                not isinstance(order, list)
                or not all(isinstance(n, str) for n in order)
                or len(order) != len(members)
                or set(order) != set(region["nodeIds"])
            ):
                raise GraphError(
                    "Sequence must be an exact permutation: no cycle/duplicate/missing/cross-region ID"
                )
            for destination, origin_id in zip(members, order, strict=True):
                a, b = destination["sourceSpan"], nodes[origin_id]["sourceSpan"]
                patches.append(
                    (
                        a["startByte"],
                        a["endByte"],
                        self._source[b["startByte"] : b["endByte"]],
                        origin_id,
                    )
                )
        else:
            before = mutation["beforeNodeId"]
            cpp = mutation["cpp"]
            if before is not None and before not in region["nodeIds"]:
                raise GraphError("Insertion anchor is outside the eligible region")
            if not isinstance(cpp, str) or not cpp.strip():
                raise GraphError("cpp must contain one scalar C++ statement")
            position = (
                nodes[before]["sourceSpan"]["startByte"]
                if before
                else region["sourceSpan"]["endByte"]
            )
            previous_newline = self._source.rfind(b"\n", 0, position)
            following_newline = self._source.find(b"\n", position)
            newline = previous_newline if previous_newline >= 0 else following_newline
            eol = b"\r\n" if newline > 0 and self._source[newline - 1 : newline] == b"\r" else b"\n"
            indentation = self._source[previous_newline + 1 : position]
            if indentation.strip():
                indentation = b""
            # A separator on both sides prevents comment swallowing/token merging;
            # existing trivia is never rewritten or re-encoded.
            payload = eol + indentation + cpp.encode("utf-8") + eol + indentation
            patches.append((position, position, payload, None))
        patches.sort(key=lambda p: p[0])
        if any(a[1] > b[0] for a, b in pairwise(patches)):
            raise GraphError("Overlapping construction byte patches")
        chunks, cursor, delta = [], 0, 0
        destinations = {}
        inserted_range = None
        for start, end, replacement, origin in patches:
            chunks.extend([self._source[cursor:start], replacement])
            if origin is not None:
                destinations[origin] = (start + delta, start + delta + len(replacement))
            if kind in {"insertStatement", "insertSdkStatement"}:
                inserted_range = (start + delta, start + delta + len(replacement))
            cursor = end
            delta += len(replacement) - (end - start)
        chunks.append(self._source[cursor:])
        changed = b"".join(chunks)
        candidate = parse_source(
            changed,
            entries=self._entries,
            bindings=self._bindings,
            event_bindings=self._event_bindings,
            sdk_profile=self._sdk_profile,
        )
        if any(d["severity"] == "error" for d in candidate._document["diagnostics"]):
            raise GraphError("Construction introduces invalid C++/selection")

        def moved(position, is_start):
            shift = 0
            for start, end, replacement, _ in patches:
                if start == end:
                    if position > start or (position == start and is_start):
                        shift += len(replacement)
                elif position >= end:
                    shift += len(replacement) - (end - start)
                elif position > start:
                    raise GraphError("Construction cuts an unrelated source boundary")
            return position + shift

        old_map = {}
        for node in self._document["nodes"]:
            if node["id"] in removed:
                continue
            span = node["sourceSpan"]
            if node["id"] in destinations:
                start, end = destinations[node["id"]]
            else:
                start, end = moved(span["startByte"], True), moved(span["endByte"], False)
            old_map[(start, end, node["kind"])] = node
        remap, inserted, matched = {}, [], set()
        for node in candidate._document["nodes"]:
            span = node["sourceSpan"]
            key = (span["startByte"], span["endByte"], node["kind"])
            old = old_map.get(key)
            if old is None:
                allowed = (
                    (node["kind"] == "if" or (node["kind"] == "declaration" and "binding" in node))
                    if sdk
                    else self._scalar_statement(node)
                )
                if (
                    kind not in {"insertStatement", "insertSdkStatement"}
                    or not allowed
                    or not inserted_range[0]
                    <= span["startByte"]
                    < span["endByte"]
                    <= inserted_range[1]
                ):
                    raise GraphError(
                        "Construction creates an opaque/unsupported node or unresolved dependency"
                    )
                inserted.append(node)
                remap[node["id"]] = node["id"]
                continue
            if old["ports"] != node["ports"]:
                raise GraphError("Construction changes a surviving type/scope/port contract")
            if node["kind"] == "opaque":
                before = old["sourceSpan"]
                if (
                    self._source[before["startByte"] : before["endByte"]]
                    != changed[span["startByte"] : span["endByte"]]
                ):
                    raise GraphError("Construction changes opaque bytes")
            matched.add(key)
            remap[node["id"]] = old["id"]
            node["id"] = old["id"]
        if sdk:
            # A single top-level CST statement, optionally containing known if
            # descendants. All new declarations must be explicit catalog calls.
            top_level = [
                n
                for n in inserted
                if not any(
                    other is not n
                    and other["sourceSpan"]["startByte"] <= n["sourceSpan"]["startByte"]
                    and n["sourceSpan"]["endByte"] <= other["sourceSpan"]["endByte"]
                    for other in inserted
                )
            ]
            inserted_count_ok = len(top_level) == 1 and any("binding" in n for n in inserted)
        else:
            inserted_count_ok = len(inserted) == (1 if kind == "insertStatement" else 0)
        if matched != set(old_map) or not inserted_count_ok:
            raise GraphError(
                "Construction must preserve all survivors and insert exactly one allowed statement"
            )
        declarations = [n for n in inserted if n["kind"] == "declaration"]
        if declarations:
            entry = nodes[region["entryNodeId"]]
            body_span = entry["sourceSpan"]
            body = next(
                n
                for n in _walk(self._tree.root_node)
                if n.type == "compound_statement"
                and n.start_byte == body_span["startByte"]
                and n.end_byte == body_span["endByte"]
            )
            parameters = _field(_field(body.parent, "declarator"), "parameters")
            parameter_names = (
                {_tokens(n, self._source) for n in _walk(parameters) if n.type == "identifier"}
                if parameters
                else set()
            )
            bound_callees = {
                n["binding"]["callee"]
                for n in self._document["nodes"]
                if "binding" in n
                and body_span["startByte"] <= n["sourceSpan"]["startByte"] < body_span["endByte"]
            }
            binding_names = set()
            for call in _walk(body):
                if call.type != "call_expression":
                    continue
                callee = _field(call, "function")
                if callee is None or _tokens(callee, self._source) not in bound_callees:
                    continue
                # Preserve exact Unicode CST spelling, without type/name resolution.
                # Comments and literal contents are not identifier reservations.
                binding_names.update(
                    _tokens(leaf, self._source)
                    for leaf in _walk(callee)
                    if not leaf.children
                    and leaf.type
                    in {"identifier", "field_identifier", "namespace_identifier", "type_identifier"}
                )
            old_names = {
                n["variable"]
                for n in self._document["nodes"]
                if "variable" in n
                and body_span["startByte"] <= n["sourceSpan"]["startByte"] < body_span["endByte"]
            }
            new_names = [n["variable"] for n in declarations]
            if len(new_names) != len(set(new_names)) or set(new_names) & (
                old_names | parameter_names | binding_names
            ):
                raise GraphError(
                    "Inserted declaration shadows an existing local/parameter/binding name"
                )

        def edge_key(edge):
            return (
                edge["kind"],
                edge["from"]["nodeId"],
                edge["from"]["portId"],
                edge["to"]["nodeId"],
                edge["to"]["portId"],
            )

        previous_edges = {edge_key(e): e["id"] for e in self._document["edges"]}
        for edge in candidate._document["edges"]:
            for side in ("from", "to"):
                edge[side]["nodeId"] = remap[edge[side]["nodeId"]]
            edge["id"] = previous_edges.get(edge_key(edge), edge["id"])
        validate_graph(candidate._document)
        return candidate

    def apply_edits(
        self, edits: Sequence[Mapping], *, expected_source_hash: str, current_source: bytes
    ) -> CodeGraph:
        """Atomic token edits. Caller supplies fresh bytes; no filesystem writes.

        Each edit: {nodeId, slotId, replacement}. Returns a NEW snapshot with
        stable node/edge IDs. Rejected/stale requests leave both snapshots alone.
        """
        if (
            not isinstance(current_source, bytes)
            or expected_source_hash != self.source_hash
            or current_source != self._source
        ):
            raise GraphError("Stale source hash/bytes conflict; no overwrite")
        if any(d["severity"] == "error" for d in self._document["diagnostics"]):
            raise GraphError("Cannot edit a graph with syntax/selection errors")
        patches = []
        for edit in edits:
            if set(edit) != {"nodeId", "slotId", "replacement"} or not isinstance(
                edit["replacement"], str
            ):
                raise GraphError("Edit requires nodeId, slotId, replacement text only")
            node = next((n for n in self._document["nodes"] if n["id"] == edit["nodeId"]), None)
            slot = (
                next((s for s in node["editSlots"] if s["id"] == edit["slotId"]), None)
                if node
                else None
            )
            if slot is None:
                raise GraphError("Unknown/opaque edit slot")
            replacement = edit["replacement"]
            if slot["kind"] == "call" and not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", replacement):
                raise GraphError("Call edit must be a single identifier")
            if slot["kind"] == "literal" and not re.fullmatch(
                r"(?:true|false|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?[fF]?)", replacement
            ):
                raise GraphError("Literal edit must be one supported numeric/bool token")
            if slot["kind"] == "string" and (not self._sdk_profile or not _sdk_string(replacement)):
                raise GraphError("String edit must be one supported ordinary C++ literal")
            span = slot["sourceSpan"]
            start, end = span["startByte"], span["endByte"]
            if _sha(self._source[start:end]) != span["sha256"]:
                raise GraphError("Stale token hash conflict")
            patches.append((start, end, replacement.encode("utf-8")))
        patches.sort()
        if any(a[1] > b[0] for a, b in pairwise(patches)):
            raise GraphError("Overlapping byte patches")
        if not patches:
            return self
        chunks, cursor = [], 0
        for start, end, replacement in patches:
            chunks.extend([self._source[cursor:start], replacement])
            cursor = end
        chunks.append(self._source[cursor:])
        changed = b"".join(chunks)
        result = parse_source(
            changed,
            entries=self._entries,
            bindings=self._bindings,
            event_bindings=self._event_bindings,
            sdk_profile=self._sdk_profile,
        )
        if any(d["severity"] == "error" for d in result._document["diagnostics"]):
            raise GraphError("Edit introduces invalid C++/selection")

        def moved(offset):
            delta = 0
            for start, end, replacement in patches:
                if offset <= start:
                    break
                if offset < end:
                    raise GraphError("Edit cuts a mapped source boundary")
                delta += len(replacement) - (end - start)
            return offset + delta

        def key(node, translate=False):
            span = node["sourceSpan"]
            start, end = span["startByte"], span["endByte"]
            return (
                (moved(start), moved(end), node["kind"])
                if translate
                else (start, end, node["kind"])
            )

        old_map = {key(n, True): n for n in self._document["nodes"]}
        new_nodes = result._document["nodes"]
        if len(old_map) != len(new_nodes) or set(old_map) != {key(n) for n in new_nodes}:
            raise GraphError("Edit changes supported structure; explicit reimport required")
        remap = {}
        for node in new_nodes:
            old = old_map[key(node)]
            if old["ports"] != node["ports"]:
                raise GraphError("Edit changes port/type contract")
            if node["kind"] == "opaque":
                old_span, new_span = old["sourceSpan"], node["sourceSpan"]
                if (
                    self._source[old_span["startByte"] : old_span["endByte"]]
                    != changed[new_span["startByte"] : new_span["endByte"]]
                ):
                    raise GraphError("Opaque bytes changed")
            remap[node["id"]] = old["id"]
            node["id"] = old["id"]

        def edge_key(edge):
            return (
                edge["kind"],
                edge["from"]["nodeId"],
                edge["from"]["portId"],
                edge["to"]["nodeId"],
                edge["to"]["portId"],
            )

        old_edges = {edge_key(e): e["id"] for e in self._document["edges"]}
        new_edges = result._document["edges"]
        for edge in new_edges:
            for side in ("from", "to"):
                edge[side]["nodeId"] = remap[edge[side]["nodeId"]]
        if set(old_edges) != {edge_key(e) for e in new_edges}:
            raise GraphError("Edit changes data/execution dependencies")
        for edge in new_edges:
            edge["id"] = old_edges[edge_key(edge)]
        validate_graph(result._document)
        return result


def parse_source(
    source: bytes,
    *,
    entries: Sequence[str],
    bindings: Mapping | None = None,
    event_bindings: Mapping[str, str] | None = None,
    sdk_profile: str | None = None,
) -> CodeGraph:
    """Explicitly select unambiguous function names as spelled in their CST.

    bindings maps canonical callee spelling to operation/returnType/parameterTypes.
    Nothing is auto-bound to hardware, SDK topics, or similarly named functions.
    event_bindings optionally labels selected entries; it registers nothing.
    UTF-8 (including BOM) is accepted and never re-encoded on export.
    sdk_profile=SDK_PROFILE opts into exact reviewed catalog signatures and typed
    borrowed parameters. Caller owns includes/build context, UI thread/lifetimes.
    SDK calls in this non-escaping subset retain local bindings, NOT pointee state
    or a promise that physical effects succeeded. No general function inference.
    """
    if not isinstance(source, bytes):
        raise GraphError("source must be raw bytes")
    try:
        source.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise GraphError("Only losslessly retained UTF-8 source is supported") from exc
    if not isinstance(entries, (list, tuple)) or not all(isinstance(n, str) and n for n in entries):
        raise GraphError("entries must be a sequence of explicit function names")
    if len(set(entries)) != len(entries):
        raise GraphError("Duplicate selected entry")
    event_bindings = dict(event_bindings or {})
    if any(k not in entries or not isinstance(v, str) or not v for k, v in event_bindings.items()):
        raise GraphError("Event bindings require selected entries and explicit event references")
    bindings = _bindings(bindings)
    if sdk_profile is not None:
        if sdk_profile != SDK_PROFILE:
            raise GraphError("Unsupported SDK profile")
        if any(_SDK_OPERATIONS.get(callee) != binding for callee, binding in bindings.items()):
            raise GraphError("SDK binding must match an explicitly reviewed catalog signature")
    try:
        projection = _Projection(source, entries, bindings, event_bindings, sdk_profile)
    except RecursionError as exc:
        raise GraphError("CST exceeds supported projection depth; no source change") from exc
    return CodeGraph(source, entries, bindings, event_bindings, projection)


def restore_graph(
    source: bytes,
    snapshot: Mapping,
    *,
    entries: Sequence[str],
    bindings: Mapping | None = None,
    event_bindings: Mapping[str, str] | None = None,
    sdk_profile: str | None = None,
) -> CodeGraph:
    """Restore stable IDs only after re-parsing and verifying the ENTIRE snapshot.

    JSON spans/slots/ports are untrusted. A saved graph cannot authorize patches
    on arbitrary bytes, add topology, or silently bind different operations.
    """
    validate_graph(snapshot)
    if snapshot.get("sourceHash") != _sha(source):
        raise GraphError("Stale snapshot source hash conflict")
    result = parse_source(
        source,
        entries=entries,
        bindings=bindings,
        event_bindings=event_bindings,
        sdk_profile=sdk_profile,
    )
    document = result._document
    if len(document["nodes"]) != len(snapshot["nodes"]) or len(document["edges"]) != len(
        snapshot["edges"]
    ):
        raise GraphError("Snapshot does not match parsed source/catalog")
    remap = {}
    for current, previous in zip(document["nodes"], snapshot["nodes"], strict=True):
        if {k: v for k, v in current.items() if k != "id"} != {
            k: v for k, v in previous.items() if k != "id"
        }:
            raise GraphError("Snapshot node/spans/ports do not match parsed source/catalog")
        remap[current["id"]] = previous["id"]
        current["id"] = previous["id"]
    for current, previous in zip(document["edges"], snapshot["edges"], strict=True):
        for side in ("from", "to"):
            current[side]["nodeId"] = remap[current[side]["nodeId"]]
        current["id"] = previous["id"]
    if document != snapshot:
        raise GraphError("Snapshot topology/metadata does not match parsed source/catalog")
    validate_graph(document)
    return result


def process_request(request: Mapping) -> dict:
    """JSON-in/JSON-out transport-neutral API; no server, file I/O or execution.

    parse: operation, sourceBase64, entries, optional bindings/eventBindings.
    edit: same fields plus graph, edits, expectedSourceHash. Fresh sourceBase64
    must match the saved graph. No arbitrary graph rewiring is implemented.
    validate: operation, graph (topology check only; no source transformation).
    regions: parse fields plus graph/expectedSourceHash; verified eligible runs.
    construct: regions fields plus one mutation; never arbitrary edge rewrites.
    sdkRegions/constructSdk: same verified envelopes, opt-in sdkProfile required;
    separate sdkRegions/sdkConstructionVersion fields, no legacy capability widening.
    """
    try:
        operation = request["operation"]
        if operation == "validate":
            if set(request) != {"operation", "graph"}:
                raise GraphError("validate requires only operation and graph")
            validate_graph(request["graph"])
            return {"ok": True}
        required = {"operation", "sourceBase64", "entries"}
        if operation == "edit":
            required |= {"graph", "edits", "expectedSourceHash"}
        elif operation in {"regions", "construct", "sdkRegions", "constructSdk"}:
            required |= {"graph", "expectedSourceHash"}
            if operation in {"construct", "constructSdk"}:
                required.add("mutation")
        elif operation != "parse":
            raise GraphError("Unsupported API operation")
        if not required <= set(request) or set(request) - required - {
            "bindings",
            "eventBindings",
            "sdkProfile",
        }:
            raise GraphError("Missing or unsupported API fields")
        if operation in {"sdkRegions", "constructSdk"} and request.get("sdkProfile") != SDK_PROFILE:
            raise GraphError("SDK construction requires explicit SDK profile")
        source = base64.b64decode(request["sourceBase64"], validate=True)
        kwargs = {
            "entries": request["entries"],
            "bindings": request.get("bindings"),
            "event_bindings": request.get("eventBindings"),
            "sdk_profile": request.get("sdkProfile"),
        }
        if operation == "parse":
            graph = parse_source(source, **kwargs)
        else:
            graph = restore_graph(source, request["graph"], **kwargs)
            if request["expectedSourceHash"] != graph.source_hash:
                raise GraphError("Stale expected source hash conflict")
            if operation == "edit":
                if not isinstance(request["edits"], list):
                    raise GraphError("edits must be a JSON array")
                graph = graph.apply_edits(
                    request["edits"],
                    expected_source_hash=request["expectedSourceHash"],
                    current_source=source,
                )
            elif operation in {"construct", "constructSdk"}:
                before_ids = {n["id"] for n in graph._document["nodes"]}
                constructor = (
                    graph.apply_sdk_construction
                    if operation == "constructSdk"
                    else graph.apply_construction
                )
                graph = constructor(
                    request["mutation"],
                    expected_source_hash=request["expectedSourceHash"],
                    current_source=source,
                )
        document = graph.to_dict()
        response = {
            "ok": not any(d["severity"] == "error" for d in document["diagnostics"]),
            "graph": document,
            "sourceBase64": base64.b64encode(graph.export_source()).decode("ascii"),
        }
        if operation in {"regions", "construct"}:
            response.update(constructionVersion=1, regions=graph.construction_regions())
        if operation in {"sdkRegions", "constructSdk"}:
            response.update(sdkConstructionVersion=1, sdkRegions=graph.sdk_construction_regions())
        if operation in {"construct", "constructSdk"}:
            after_ids = {n["id"] for n in document["nodes"]}
            response["changeSet"] = {
                "insertedNodeIds": sorted(after_ids - before_ids),
                "removedNodeIds": sorted(before_ids - after_ids),
            }
        return response
    except (GraphError, KeyError, TypeError, ValueError, AttributeError, binascii.Error) as exc:
        return {"ok": False, "diagnostics": [{"code": "request-error", "message": str(exc)}]}
