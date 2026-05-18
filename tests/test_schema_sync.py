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


# Schema-only widget properties that are intentionally NOT WidgetConfig fields.
# These are read-side tolerances: keys an externally-authored or exported design
# may legally carry, normalized away on load and never emitted by save
# (ui_designer.save_to_json -> asdict). Adding to this set is a deliberate,
# reviewed decision — it must be a true alias/export key, not a forgotten model
# field. The schema declares `additionalProperties: false`, so anything not a
# model field and not listed here would make saved files schema-invalid.
SCHEMA_ONLY_ALIASES = frozenset(
    {
        "id",  # external/scene-style widget id; model uses `_widget_id`
        "constraints_json",  # exported firmware metadata (C-header form of `runtime`/constraints)
        "animations_csv",  # exported CSV form of the `animations` list
        "list_items",  # legacy/external read alias normalized into `items`
    }
)


def test_schema_properties_match_widget_config_bidirectionally():
    """The schema must be authoritative for save output AND read tolerance.

    Direction 1 (save-validity): every WidgetConfig dataclass field MUST have a
    schema property. ui_designer.save_to_json serializes via asdict(), dumping
    *every* field; with `additionalProperties: false` any model field absent
    from the schema makes every saved design schema-invalid.

    Direction 2 (read-tolerance): every schema widget property MUST be either a
    real WidgetConfig field or an explicitly documented alias in
    SCHEMA_ONLY_ALIASES. This prevents the schema from silently drifting to
    accept keys nothing in the model produces or consumes (the dead-`parent_id`
    class of bug).
    """
    schema = _load_schema()
    schema_props = set(schema["$defs"]["widget"]["properties"].keys())
    model_fields = {f.name for f in WidgetConfig.__dataclass_fields__.values()}

    model_without_schema = model_fields - schema_props
    assert not model_without_schema, (
        "WidgetConfig fields missing a schema property — saved designs would be "
        f"schema-INVALID under additionalProperties:false: {sorted(model_without_schema)}"
    )

    schema_without_model = schema_props - model_fields - SCHEMA_ONLY_ALIASES
    assert not schema_without_model, (
        "Schema declares widget properties that are neither WidgetConfig fields "
        "nor documented aliases (add to SCHEMA_ONLY_ALIASES only if truly an "
        f"alias/export key): {sorted(schema_without_model)}"
    )

    # The alias list itself must stay honest: an alias must NOT also be a real
    # model field (that would mean it is not actually schema-only).
    stale_aliases = SCHEMA_ONLY_ALIASES & model_fields
    assert not stale_aliases, (
        f"SCHEMA_ONLY_ALIASES lists real WidgetConfig fields (remove them): "
        f"{sorted(stale_aliases)}"
    )


def test_schema_valid_json():
    """Schema file must be valid JSON."""
    schema = _load_schema()
    assert "$schema" in schema
    assert "$defs" in schema
    assert "widget" in schema["$defs"]
