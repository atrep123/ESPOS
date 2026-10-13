"""Actual isolated entry/parser checks; no editor, SDK execution or freeze claim.

CODEGRAPH_PYTHON selects an already approved dependency interpreter for TESTS
only. The backend never reads it. Every owned child has capped output, a single
deadline and hidden Windows startup; no shell, installation or child fallback.
"""

import base64
import builtins
import copy
import errno
import hashlib
import io
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import desktop_backend_entry as entry
from tools.tabos_sdk_node_catalog import catalog

ENTRY = Path(__file__).resolve().parents[1] / "tools" / "desktop_backend_entry.py"
FRAME_LIMIT = 1024 * 1024
SOURCE_LIMIT = 64 * 1024
DEADLINE_SECONDS = 12


@pytest.fixture(scope="module")
def python():
    selected = Path(os.environ.get("CODEGRAPH_PYTHON", sys.executable))
    assert selected.is_absolute() and selected.is_file(), "Need an existing test interpreter"
    return str(selected)


def _child(python, payload, cwd, *, args=("codegraph-bundled",), env=None, hold_stdin=False):
    options = {}
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        options = {"startupinfo": startup, "creationflags": subprocess.CREATE_NO_WINDOW}
    process = subprocess.Popen(
        [python, "-I", "-B", str(ENTRY), *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        bufsize=0,
        **options,
    )
    deadline = time.monotonic() + DEADLINE_SECONDS
    streams = [process.stdin, process.stdout, process.stderr]
    readers = {process.stdout: 0, process.stderr: 1}
    buffers = [bytearray(), bytearray()]
    offset = 0
    try:
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        while readers or process.poll() is None:
            remaining = deadline - time.monotonic()
            assert remaining > 0, "Owned entry child exceeded deadline"
            if offset == len(payload) and not hold_stdin and not process.stdin.closed:
                process.stdin.close()
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
                    process.wait(timeout=min(0.2, remaining))
                    stream.close()
            for stream in ready_read:
                try:
                    chunk = os.read(stream.fileno(), 8192)
                except BlockingIOError:
                    continue
                if chunk:
                    assert sum(map(len, buffers)) + len(chunk) <= FRAME_LIMIT, (
                        "Owned child output cap"
                    )
                    buffers[readers[stream]].extend(chunk)
                else:
                    del readers[stream]
                    stream.close()
            if os.name == "nt":
                time.sleep(min(0.005, remaining))
        return process.returncode, bytes(buffers[0]), bytes(buffers[1])
    finally:
        if process.poll() is None:
            process.kill()
        for stream in streams:
            stream.close()
        process.wait(timeout=1)


def _request(raw=b"void step(){ int value=1; }", **extra):
    return {
        "operation": "parse",
        "sourceBase64": base64.b64encode(raw).decode("ascii"),
        "entries": ["step"],
        **extra,
    }


def _run(python, cwd, request=None, **options):
    payload = options.pop("payload", None)
    if payload is None:
        payload = json.dumps(request, ensure_ascii=True, allow_nan=False).encode() + b"\n"
    code, stdout, stderr = _child(python, payload, cwd, **options)
    assert stderr == b"", "Backend must not expose stderr"
    assert len(stdout) <= FRAME_LIMIT and stdout.endswith(b"\n") and stdout.count(b"\n") == 1
    response = json.loads(stdout)
    assert isinstance(response["ok"], bool)
    assert (code == 0) == response["ok"]
    if not response["ok"]:
        assert response.get("diagnostics") or response.get("graph", {}).get("diagnostics")
    return code, response


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
    raw = base64.b64decode(response["sourceBase64"])
    return {
        node["id"]: raw[node["sourceSpan"]["startByte"] : node["sourceSpan"]["endByte"]]
        for node in response["graph"]["nodes"]
        if node["kind"] == "opaque"
    }


def test_real_parse_edit_bom_crlf_opaque_bytes_and_ids(python, tmp_path):
    raw = (
        b"\xef\xbb\xbf"
        + "// přesně 🚦\r\n".encode()
        + b"template<class T> T keep(T x){return x;}\r\n"
        + b"void step(){\r\n int value=1;\r\n}\r\n"
        + b"auto opaque=[](){return keep(4);};\r\n"
    )
    request = _request(raw, eventBindings={"step": "ui.tick"})
    _, parsed = _run(python, tmp_path, request, hold_stdin=True)
    assert base64.b64decode(parsed["sourceBase64"]) == raw
    assert parsed["graph"]["sourceHash"] == hashlib.sha256(raw).hexdigest()
    selected_entry = next(n for n in parsed["graph"]["nodes"] if n["kind"] == "entry")
    assert selected_entry["eventBinding"] == "ui.tick"
    assert {"id": "event", "kind": "event", "direction": "in"} in selected_entry["ports"]
    node = next(n for n in parsed["graph"]["nodes"] if n.get("variable") == "value")
    slot = next(s for s in node["editSlots"] if s["kind"] == "literal")
    _, edited = _run(
        python,
        tmp_path,
        _transaction(
            request,
            parsed,
            "edit",
            edits=[{"nodeId": node["id"], "slotId": slot["id"], "replacement": "27"}],
        ),
    )
    assert base64.b64decode(edited["sourceBase64"]) == raw.replace(b"value=1", b"value=27")
    assert _opaque(edited) == _opaque(parsed)
    assert [n["id"] for n in edited["graph"]["nodes"]] == [
        n["id"] for n in parsed["graph"]["nodes"]
    ]
    _, unchanged = _run(python, tmp_path, _transaction(request, parsed, "edit", edits=[]))
    assert unchanged == parsed


def test_sdk_catalog_profile_regions_construct_and_edit(python, tmp_path):
    node = next(n for n in catalog()["nodes"] if n["id"] == "espos.tabos.lvgl.label.text.v1")
    binding = {
        "operation": node["id"],
        "parameterTypes": [p["cpp_type"] for p in node["bindings"] if p["direction"] == "input"],
        "returnType": next(p["cpp_type"] for p in node["bindings"] if p["direction"] == "output"),
    }
    raw = b"\xef\xbb\xbf// keep\r\nvoid step(lv_obj_t* label){\r\n}\r\n"
    request = _request(
        raw,
        sdkProfile="tabos-sdk-minimal-1",
        bindings={catalog()["namespace"] + "::" + node["functions"][0]: binding},
    )
    _, parsed = _run(python, tmp_path, request)
    assert parsed["graph"]["sdkProfile"] == request["sdkProfile"]
    _, regions = _run(python, tmp_path, _transaction(request, parsed, "sdkRegions"))
    assert regions["sdkConstructionVersion"] == 1 and regions["graph"] == parsed["graph"]
    cpp = 'auto status = espos_tabos_nodes::set_label_text(label, "Kliknutí");'
    _, constructed = _run(
        python,
        tmp_path,
        _transaction(
            request,
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
    assert constructed["sdkConstructionVersion"] == 1
    assert len(constructed["changeSet"]["insertedNodeIds"]) == 1
    assert _opaque(constructed) == _opaque(parsed)
    node = next(n for n in constructed["graph"]["nodes"] if n.get("variable") == "status")
    assert node["cppType"] == "tabos::Status"
    slot = next(s for s in node["editSlots"] if s["kind"] == "string")
    _, edited = _run(
        python,
        tmp_path,
        _transaction(
            request,
            constructed,
            "edit",
            edits=[{"nodeId": node["id"], "slotId": slot["id"], "replacement": '"Změna 🚦"'}],
        ),
    )
    assert base64.b64decode(edited["sourceBase64"]) == base64.b64decode(
        constructed["sourceBase64"]
    ).replace('"Kliknutí"'.encode(), '"Změna 🚦"'.encode())
    assert edited["graph"]["sdkProfile"] == request["sdkProfile"]


def test_scalar_regions_and_construct(python, tmp_path):
    request = _request(b"void step(){}")
    _, parsed = _run(python, tmp_path, request)
    _, regions = _run(python, tmp_path, _transaction(request, parsed, "regions"))
    _, result = _run(
        python,
        tmp_path,
        _transaction(
            request,
            regions,
            "construct",
            mutation={
                "kind": "insertStatement",
                "regionId": regions["regions"][0]["id"],
                "beforeNodeId": None,
                "cpp": "int count = 7;",
            },
        ),
    )
    assert result["constructionVersion"] == 1 and len(result["changeSet"]["insertedNodeIds"]) == 1
    assert b"int count = 7;" in base64.b64decode(result["sourceBase64"])


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("codegraph",),
        ("catalog",),
        ("--help",),
        ("codegraph-bundled", "--tooling-root", "SECRET_PATH"),
        ("codegraph-bundled", "--python-executable", "SECRET_PATH"),
        ("codegraph-bundled", "file.cpp"),
        ("codegraph-bundled", "codegraph-bundled"),
    ],
)
def test_exact_role_only_before_reading_stdin(python, tmp_path, args):
    code, response = _run(python, tmp_path, payload=b"", args=args, hold_stdin=True)
    assert code == 2 and response["diagnostics"][0]["code"] == "backend-role"
    assert "SECRET_PATH" not in json.dumps(response)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"{}",
        b"{}\n",
        b"[]\n",
        b"not JSON\n",
        b"\xff\n",
        b'{"operation":"parse","operation":"parse"}\n',
        b'{"operation":"parse","bindings":{"SECRET_PATH":1,"SECRET_PATH":2}}\n',
        b'{"operation":"parse","sourceBase64":NaN,"entries":[]}\n',
        b'{"operation":"parse","sourceBase64":Infinity,"entries":[]}\n',
        b"[" * 2000 + b"]" * 2000 + b"\n",
        b" " * FRAME_LIMIT + b"\n",
    ],
    ids=[
        "empty",
        "no-newline",
        "empty-object",
        "array",
        "syntax",
        "encoding",
        "duplicate-top",
        "duplicate-nested",
        "nan",
        "infinity",
        "depth",
        "oversize",
    ],
)
def test_bad_frames_and_repeated_keys(python, tmp_path, payload):
    code, response = _run(python, tmp_path, payload=payload)
    assert code != 0 and "SECRET_PATH" not in json.dumps(response)


@pytest.mark.parametrize(
    "extra",
    [
        {"tooling_root": "SECRET_PATH"},
        {"pythonExecutable": "SECRET_PATH"},
        {"filename": "SECRET_PATH"},
        {"unsafe": True},
    ],
)
def test_unknown_fields_rejected_before_source_decode(python, tmp_path, extra):
    _, response = _run(python, tmp_path, _request(sourceBase64="not base64", **extra))
    assert response["diagnostics"][0]["code"] == "request-error"
    assert "graph" not in response and "sourceBase64" not in response


def test_authoritative_field_validation_before_decode(monkeypatch):
    from tools import tabos_code_graph

    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe extra fields reached source decoding")

    monkeypatch.setattr(tabos_code_graph.base64, "b64decode", forbidden)
    response, status = entry._process(_request(unsafe="SECRET_PATH"))
    assert status != 0 and response["diagnostics"][0]["code"] == "request-error"


def test_cwd_and_environment_cannot_select_imports_or_interpreter(python, tmp_path):
    env = os.environ.copy()
    env.update(
        {
            name: str(tmp_path / "SECRET_PATH")
            for name in (
                "PYTHONPATH",
                "PYTHONHOME",
                "CODEGRAPH_PYTHON",
                "ESPOS_TAB5_PYTHON",
                "ESPOS_TOOLING_ROOT",
            )
        }
    )
    _, response = _run(python, tmp_path, _request(), env=env)
    assert response["ok"] and response["graph"]["catalogVersion"] == "cpp-cst-subset-1"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("size", [SOURCE_LIMIT, SOURCE_LIMIT + 1])
def test_exact_source_byte_budget(python, tmp_path, size):
    raw = b"/*" + b"x" * (size - 4) + b"*/"
    _, response = _run(python, tmp_path, _request(raw, entries=[]))
    assert response["ok"] == (size == SOURCE_LIMIT)
    if response["ok"]:
        assert base64.b64decode(response["sourceBase64"]) == raw
    else:
        assert response["diagnostics"][0]["code"] == "backend-source-limit"


def test_graph_frame_budget_is_larger_than_source_and_reply_is_bounded(python, tmp_path):
    request = _request(b"void step(){" + b"int x=1;" * 350 + b"}")
    _, parsed = _run(python, tmp_path, request)
    edit = _transaction(request, parsed, "edit", edits=[])
    assert len(json.dumps(edit).encode()) > SOURCE_LIMIT
    _, unchanged = _run(python, tmp_path, edit)
    assert unchanged == parsed
    # A small source can yield a graph larger than the transport. Reject the
    # entire reply before writing it; never truncate into a success envelope.
    request = _request(b"void step(){" + b"int x=1;" * 2200 + b"}")
    _, response = _run(python, tmp_path, request)
    assert response["ok"] is False and response["diagnostics"][0]["code"] == "backend-reply"


def test_stale_edit_and_invalid_utf8_do_not_return_changed_source(python, tmp_path):
    request = _request()
    _, parsed = _run(python, tmp_path, request)
    stale = _transaction(request, parsed, "edit", edits=[], expectedSourceHash="0" * 64)
    before = copy.deepcopy(stale)
    _, response = _run(python, tmp_path, stale)
    assert not response["ok"] and "sourceBase64" not in response and stale == before
    _, binary = _run(python, tmp_path, _request(b"\xef\xbb\xbf\x00\xff"))
    assert not binary["ok"] and "sourceBase64" not in binary


def test_parser_failure_diagnostics_do_not_echo_selected_name(python, tmp_path):
    _, response = _run(python, tmp_path, _request(entries=["C:/SECRET_PATH/token"]))
    assert not response["ok"]
    assert all("SECRET_PATH" not in d["message"] for d in response["graph"]["diagnostics"])


def test_frozen_standard_boot_does_not_change_package_search_path(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(entry, "__package__", None)
    before = list(sys.path)
    response, status = entry._process(_request(unsafe="SECRET_PATH"))
    assert status == 1 and response["diagnostics"][0]["code"] == "request-error"
    assert sys.path == before


def _in_memory_main(monkeypatch):
    output, errors = io.BytesIO(), io.StringIO()
    monkeypatch.setattr(
        sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(_request()).encode() + b"\n"))
    )
    monkeypatch.setattr(sys, "stdout", SimpleNamespace(buffer=output))
    monkeypatch.setattr(sys, "stderr", errors)
    status = entry.main(["codegraph-bundled"])
    assert status != 0 and errors.getvalue() == ""
    assert output.getvalue().count(b"\n") == 1
    response = json.loads(output.getvalue())
    assert response["ok"] is False and "SECRET_PATH" not in str(response)
    return response


def test_missing_packaged_module_fails_without_path_or_traceback(monkeypatch):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "tools":
            raise ImportError("C:/SECRET_PATH/module.py")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(entry, "__package__", None)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(builtins, "__import__", missing)
    response = _in_memory_main(monkeypatch)
    assert response["diagnostics"][0]["code"] == "backend-unavailable"


def test_unexpected_parser_exception_and_logs_are_withheld(monkeypatch):
    from tools import tabos_code_graph

    def broken(request):
        print("C:/SECRET_PATH/raw-source")
        print("SECRET_PATH/secret-stderr", file=sys.stderr)
        raise RuntimeError("C:/SECRET_PATH/private-data")

    monkeypatch.setattr(tabos_code_graph, "process_request", broken)
    response = _in_memory_main(monkeypatch)
    assert response["diagnostics"][0]["code"] == "backend-error"


def test_result_source_growth_is_bounded(python, tmp_path):
    prefix = b"/*" + b"x" * (SOURCE_LIMIT - len(b"void step(){int x=1;}") - 4) + b"*/"
    raw = prefix + b"void step(){int x=1;}"
    assert len(raw) == SOURCE_LIMIT
    request = _request(raw)
    _, parsed = _run(python, tmp_path, request)
    node = next(n for n in parsed["graph"]["nodes"] if n.get("variable") == "x")
    slot = next(s for s in node["editSlots"] if s["kind"] == "literal")
    _, response = _run(
        python,
        tmp_path,
        _transaction(
            request,
            parsed,
            "edit",
            edits=[{"nodeId": node["id"], "slotId": slot["id"], "replacement": "123"}],
        ),
    )
    assert response["diagnostics"][0]["code"] == "backend-source-limit"
    assert "sourceBase64" not in response and "graph" not in response


def test_missing_native_parser_dependency_has_nonzero_safe_reply(monkeypatch):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name in {"tree_sitter", "tree_sitter_cpp"}:
            raise ImportError("C:/SECRET_PATH/native-extension.pyd")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    response = _in_memory_main(monkeypatch)
    assert response["diagnostics"][0]["code"] == "request-error"


@pytest.mark.parametrize("operation", ["validate", "catalog", "execute", "__import__", "parse "])
def test_only_packaged_parser_operations_are_admitted(python, tmp_path, operation):
    code, response = _run(python, tmp_path, _request(operation=operation))
    assert code == 2 and response["diagnostics"][0]["code"] == "backend-operation"
