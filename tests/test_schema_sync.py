"""Verify JSON schema stays in sync with Python enums and WidgetConfig."""

from __future__ import annotations

import json
from pathlib import Path

from ui_models import BorderStyle, WidgetConfig, WidgetType

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "ui_design.schema.json"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_widget_type_enum_matches_schema():
    schema = _load_schema()
    schema_types = set(schema["$defs"]["widget"]["properties"]["type"]["enum"])
    python_types = {wt.value for wt in WidgetType}
    assert schema_types == python_types, (
        f"Schema type enum mismatch.\n"
        f"  Only in schema: {schema_types - python_types}\n"
        f"  Only in Python: {python_types - schema_types}"
    )


def test_border_style_enum_matches_schema():
    schema = _load_schema()
    schema_styles = set(schema["$defs"]["widget"]["properties"]["border_style"]["enum"])
    python_styles = {bs.value for bs in BorderStyle}
    assert schema_styles == python_styles, (
        f"Schema border_style enum mismatch.\n"
        f"  Only in schema: {schema_styles - python_styles}\n"
        f"  Only in Python: {python_styles - schema_styles}"
    )


def test_schema_widget_required_fields():
    """Widget required fields must be a subset of WidgetConfig attributes."""
    schema = _load_schema()
    required = set(schema["$defs"]["widget"]["required"])
    config_attrs = {f.name for f in WidgetConfig.__dataclass_fields__.values()}
    missing = required - config_attrs
    assert not missing, f"Schema requires fields missing from WidgetConfig: {missing}"


def test_schema_valid_json():
    """Schema file must be valid JSON."""
    schema = _load_schema()
    assert "$schema" in schema
    assert "$defs" in schema
    assert "widget" in schema["$defs"]
