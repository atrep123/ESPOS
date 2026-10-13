"""Actual mandatory-engine status, never a file-presence or clean-scene claim."""

import json
import sys

import pytest

from tools import validate_design as validator


def document(tmp_path, data=None):
    path = tmp_path / "scene.json"
    path.write_text(json.dumps({"scenes": {}} if data is None else data), encoding="utf-8")
    return path


def test_real_engine_completion_is_distinct_from_valid_scene(tmp_path):
    path = document(tmp_path, {"width": "bad", "height": 128, "scenes": {}})
    result = validator.validate_file_with_status(path, warnings_as_errors=False)
    assert result.schema_validated is True
    assert any(issue.level == "ERROR" and "schema:" in issue.message for issue in result.issues)
    assert result.issues == validator.validate_file(path, warnings_as_errors=False)


def test_missing_dependency_is_not_completed_even_with_existing_schema(tmp_path, monkeypatch):
    assert validator.SCHEMA_PATH.is_file()
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    result = validator.validate_file_with_status(document(tmp_path), warnings_as_errors=False)
    assert result.schema_validated is False
    assert any("not installed" in issue.message for issue in result.issues)


@pytest.mark.parametrize("kind", ["missing", "json", "schema", "reference"])
def test_missing_or_bad_trusted_schema_is_not_completion(tmp_path, monkeypatch, kind):
    path = document(tmp_path)
    schema = tmp_path / "schema.json"
    if kind == "json":
        schema.write_text("{", encoding="utf-8")
    elif kind == "schema":
        schema.write_text('{"type": 42}', encoding="utf-8")
    elif kind == "reference":
        schema.write_text('{"$ref": "#/$defs/nonexistent"}', encoding="utf-8")
    monkeypatch.setattr(validator, "SCHEMA_PATH", schema)
    result = validator.validate_file_with_status(path, warnings_as_errors=False)
    assert result.schema_validated is False
    assert any(issue.level == "ERROR" and "schema" in issue.message for issue in result.issues)


@pytest.mark.parametrize("raw", ["{", "[]", '"scene"'])
def test_unreadable_or_nonobject_scene_never_claims_schema_ran(tmp_path, raw):
    path = tmp_path / "scene.json"
    path.write_text(raw, encoding="utf-8")
    result = validator.validate_file_with_status(path, warnings_as_errors=False)
    assert result.schema_validated is False
    assert result.issues[0].level == "ERROR"


def test_missing_scene_is_not_schema_completion(tmp_path):
    result = validator.validate_file_with_status(
        tmp_path / "missing.json", warnings_as_errors=False
    )
    assert result.schema_validated is False
    assert result.issues[0].level == "ERROR"


def test_interrupted_iteration_does_not_claim_completion(tmp_path, monkeypatch):
    import jsonschema

    def broken(_self, _data):
        raise RuntimeError("TEST_ONLY interrupted engine")

    monkeypatch.setattr(jsonschema.Draft202012Validator, "iter_errors", broken)
    result = validator.validate_file_with_status(document(tmp_path), warnings_as_errors=False)
    assert result.schema_validated is False
    assert any("interrupted engine" in issue.message for issue in result.issues)
