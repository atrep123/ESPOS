"""TEST_ONLY trusted in-memory backend contracts; not Studio/runtime proof."""

import copy
import json

import pytest

from tools.tabos_export_adapter import AdapterError, StudioBackend, adapt_document


def inputs():
    return (
        {
            "width": 1280,
            "height": 720,
            "code_blocks": [{"language": "cpp", "source": "TEST_ONLY opaque\r\n{}"}],
            "scenes": {
                "main": {
                    "widgets": [
                        {
                            "id": "tlačítko.0",
                            "type": "button",
                            "x": 10,
                            "y": 10,
                            "width": 100,
                            "height": 64,
                            "text": "Měřit",
                        }
                    ]
                }
            },
        },
        {
            "actions": {"tlačítko.0": "test:measure"},
            "states": [
                {"kind": "error", "description": "TEST_ONLY error"},
                {"kind": "unavailable", "description": "TEST_ONLY disconnect"},
            ],
        },
    )


@pytest.fixture
def backend():
    calls = []

    def rules(tokens):
        calls.append(("tokens", copy.deepcopy(tokens)))
        touch = tokens["touch"]
        return touch["target_min_px"], touch["hard_floor_px"]

    def validate(scene, touch_rules):
        calls.append(("validate", copy.deepcopy(scene), touch_rules))
        return (
            ["TEST_ONLY target below owner minimum"]
            if scene["widgets"][0]["h"] < touch_rules[0]
            else []
        )

    def generate(scene, touch_rules):
        calls.append(("generate", copy.deepcopy(scene), touch_rules))
        return "// TEST_ONLY synthetic generation, not C++ runtime proof\n"

    return StudioBackend(rules, validate, generate, (81, 58)), calls


def test_bundled_hook_uses_actual_owner_rules_and_preserves_source(backend):
    implementation, calls = backend
    source, metadata = inputs()
    raw = json.dumps(source, ensure_ascii=False, indent=3).encode("utf-8")
    tokens = {"touch": {"target_min_px": 64, "hard_floor_px": 58}}
    before = copy.deepcopy(tokens)
    result = adapt_document(
        raw, "main", studio_backend=implementation, owner_token_data=tokens, **metadata
    )
    assert [row[0] for row in calls] == ["tokens", "validate", "generate"]
    assert calls[1][2] == calls[2][2] == (64, 58)
    assert calls[1][1]["widgets"][0]["action"] == "test:measure"
    assert result.source_bytes == raw and result.restore_document() == source
    assert result.restore_document()["code_blocks"] == source["code_blocks"]
    assert tokens == before and result.generated_cpp


def test_no_owner_tokens_uses_backend_default_and_never_invents_lower_minimum(backend):
    implementation, calls = backend
    source, metadata = inputs()
    with pytest.raises(AdapterError, match="owner minimum"):
        adapt_document(source, "main", studio_backend=implementation, **metadata)
    assert [row[0] for row in calls] == ["validate"]
    assert calls[0][2] == (81, 58)


def test_explicit_developer_root_and_backend_cannot_be_combined(backend, tmp_path):
    source, metadata = inputs()
    with pytest.raises(AdapterError, match="cannot combine"):
        adapt_document(source, "main", studio_backend=backend[0], studio_root=tmp_path, **metadata)
    assert not backend[1]


@pytest.mark.parametrize("backend_supplied", [False, True])
def test_explicit_token_data_needs_backend_and_no_path(backend, tmp_path, backend_supplied):
    source, metadata = inputs()
    with pytest.raises(AdapterError, match="owner_token_data"):
        adapt_document(
            source,
            "main",
            studio_backend=backend[0] if backend_supplied else None,
            owner_tokens=tmp_path / "tokens.json" if backend_supplied else None,
            owner_token_data={},
            **metadata,
        )


@pytest.mark.parametrize("rules", [(True, 1), (0, 1), (64, 65), (64,), "64"])
def test_invalid_actual_backend_rules_reject_before_validation_or_generation(backend, rules):
    source, metadata = inputs()
    implementation, calls = backend
    implementation = StudioBackend(
        lambda tokens: rules, implementation.validate_scene, implementation.generate, (81, 58)
    )
    with pytest.raises(AdapterError, match="invalid positive target/floor"):
        adapt_document(
            source, "main", studio_backend=implementation, owner_token_data={}, **metadata
        )
    assert calls == []


@pytest.mark.parametrize("diagnostics", [None, "wrong", [1]])
def test_invalid_validator_result_cannot_reach_generator(backend, diagnostics):
    source, metadata = inputs()
    implementation, calls = backend
    implementation = StudioBackend(
        lambda tokens: (64, 58), lambda *args: diagnostics, implementation.generate, (81, 58)
    )
    with pytest.raises(AdapterError, match="invalid Studio diagnostics"):
        adapt_document(
            source, "main", studio_backend=implementation, owner_token_data={}, **metadata
        )
    assert not calls


@pytest.mark.parametrize("output", [None, "", "   ", 1, "\ud800"])
def test_invalid_generator_output_never_returns_partial_success(backend, output):
    source, metadata = inputs()
    implementation = StudioBackend(
        lambda tokens: (64, 58), lambda *args: [], lambda *args: output, (81, 58)
    )
    before = copy.deepcopy(source)
    with pytest.raises(AdapterError, match="Studio check unavailable/failed"):
        adapt_document(
            source, "main", studio_backend=implementation, owner_token_data={}, **metadata
        )
    assert source == before


def test_owner_token_path_is_bounded_and_uses_same_backend(backend, tmp_path):
    source, metadata = inputs()
    tokens = tmp_path / "tokens.json"
    tokens.write_text('{"touch":{"target_min_px":64,"hard_floor_px":58}}', encoding="utf-8")
    result = adapt_document(
        source, "main", studio_backend=backend[0], owner_tokens=tokens, **metadata
    )
    assert result.generated_cpp and backend[1][0][0] == "tokens"
    tokens.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(AdapterError, match="tokens exceed 1 MiB"):
        adapt_document(source, "main", studio_backend=backend[0], owner_tokens=tokens, **metadata)


def test_malformed_selected_scene_never_calls_backend(backend):
    source, metadata = inputs()
    source["scenes"]["main"]["widgets"][0]["style"] = "unsupported"
    with pytest.raises(AdapterError, match="unsupported metadata"):
        adapt_document(source, "main", studio_backend=backend[0], owner_token_data={}, **metadata)
    assert not backend[1]


@pytest.mark.parametrize("as_bytes", [False, True])
def test_nonfinite_json_in_opaque_metadata_is_not_a_valid_export(backend, as_bytes):
    source, metadata = inputs()
    source["code_blocks"][0]["metadata"] = float("nan")
    document = json.dumps(source).encode() if as_bytes else source
    with pytest.raises(AdapterError, match="non-finite"):
        adapt_document(document, "main", studio_backend=backend[0], owner_token_data={}, **metadata)
    assert not backend[1]
