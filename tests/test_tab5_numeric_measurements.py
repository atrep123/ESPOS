"""Adversarial numeric controls for Tab5 measurements, without live rendering."""

from __future__ import annotations

import json

import pytest

from tools.validate_design import (
    OREZ_KLICE,
    ZNACKA_NAVRH_VADNY,
    _navrh_ze_sceny,
    _nezaporne_cislo,
    _rez_z_klice,
    validate_data,
    validate_file,
)

BAD_NUMBERS = [
    pytest.param(float("inf"), id="positive-infinity"),
    pytest.param(float("-inf"), id="negative-infinity"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(10**400, id="integer-overflow"),
]
FIELDS = ["font_size", "vsazka", "sirka_textu", "sirka_bunky", *OREZ_KLICE]


@pytest.mark.parametrize("value", [*BAD_NUMBERS, True, False, "12", None, -1])
def test_pixel_measurements_reject_invalid_numbers_without_crashing(value):
    assert _nezaporne_cislo(value) is None


@pytest.mark.parametrize("value", [0, 0.0, 0.125, 12, 12.5, 10**300])
def test_pixel_measurements_preserve_finite_zero_and_subpixels(value):
    assert _nezaporne_cislo(value) == float(value)


@pytest.mark.parametrize(
    "value", [*BAD_NUMBERS, "inf", "Infinity", "1e400", "nan", True, False, "", 0, -1]
)
def test_font_scale_keys_reject_nonfinite_and_overflow(value):
    assert _rez_z_klice(value) is None


@pytest.mark.parametrize("value", [12, 12.5, "12", " 12.5 ", "1.25e1", 10**300])
def test_font_scale_keys_keep_finite_numeric_strings(value):
    assert _rez_z_klice(value) == float(value)


def measurement(field, value):
    if field in OREZ_KLICE:
        return {"orez": {key: value if key == field else 100 for key in OREZ_KLICE}}
    return {field: value}


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", BAD_NUMBERS)
def test_invalid_measurement_is_reported_and_discarded_atomically(field, value):
    scene = {
        "navrh": {"prvky": {"bad.0": measurement(field, value), "good.0": {"font_size": 12.5}}}
    }
    elements, _, issues = _navrh_ze_sceny(scene, "numeric", {"bad.0", "good.0"})
    assert any(
        issue.level == "ERROR" and ZNACKA_NAVRH_VADNY in issue.message and field in issue.message
        for issue in issues
    )
    assert ("orez" if field in OREZ_KLICE else field) not in elements["bad.0"]
    assert elements["good.0"]["font_size"] == 12.5


@pytest.mark.parametrize("field", FIELDS)
def test_finite_measurement_control_has_no_input_error(field):
    scene = {"navrh": {"prvky": {"good.0": measurement(field, 12.5)}}}
    elements, _, issues = _navrh_ze_sceny(scene, "numeric", {"good.0"})
    assert issues == []
    assert ("orez" if field in OREZ_KLICE else field) in elements["good.0"]


@pytest.mark.parametrize(
    "token",
    ["1e400", "Infinity", "NaN", str(10**400)],
    ids=["json-exponent-overflow", "infinity", "nan", "large-json-integer"],
)
def test_file_validation_cannot_hide_clipping_with_invalid_box_width(tmp_path, token):
    # 1e400 is valid JSON numeric syntax; the others exercise Python's permissive loader.
    widget = {
        "_widget_id": "text.0",
        "type": "label",
        "x": 100,
        "y": 100,
        "width": 100,
        "height": 30,
        "text": "text",
        "color_fg": "#e6e1ce",
        "color_bg": "#14170f",
    }
    data = {
        "device": "tab5",
        "scenes": {
            "main": {
                "width": 1280,
                "height": 720,
                "widgets": [widget],
                "navrh": {
                    "prvky": {
                        "text.0": {
                            "orez": {
                                "sirka_obsahu": 200,
                                "sirka_schranky": "INVALID_NUMBER",
                                "vyska_obsahu": 20,
                                "vyska_schranky": 30,
                            }
                        }
                    }
                },
            }
        },
    }
    path = tmp_path / "numeric.dc.json"
    path.write_text(json.dumps(data).replace('"INVALID_NUMBER"', token), encoding="utf-8")
    issues = validate_file(path, warnings_as_errors=False)
    assert any(
        issue.level == "ERROR"
        and ZNACKA_NAVRH_VADNY in issue.message
        and "sirka_schranky" in issue.message
        for issue in issues
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("vsazka", "wrong"),
        ("vsazka", 0),
        ("tucne", "false"),
        ("rodic_id", "missing.0"),
        ("inkoust", "not-a-color"),
        ("podklad", "not-a-color"),
    ],
)
def test_rejected_known_metadata_never_survives_as_unknown_extension(field, value):
    scene = {"navrh": {"prvky": {"bad.0": {field: value, "future_extension": "preserve"}}}}
    elements, _, issues = _navrh_ze_sceny(scene, "numeric", {"bad.0"})
    assert any(issue.level == "ERROR" and field in issue.message for issue in issues)
    assert field not in elements["bad.0"]
    assert elements["bad.0"]["future_extension"] == "preserve"


def contrast_document(font_size, bold=False):
    widget = {
        "_widget_id": "text.0",
        "type": "label",
        "x": 100,
        "y": 100,
        "width": 200,
        "height": 40,
        "text": "CONTRAST",
        "color_fg": "#777777",
        "color_bg": "#ffffff",
    }
    return {
        "device": "tab5",
        "scenes": {
            "main": {
                "width": 1280,
                "height": 720,
                "widgets": [widget],
                "navrh": {"prvky": {"text.0": {"font_size": font_size, "tucne": bold}}},
            }
        },
    }


@pytest.mark.parametrize("font_size", BAD_NUMBERS)
def test_invalid_font_size_cannot_buy_large_text_contrast_exemption(font_size):
    issues = validate_data(
        contrast_document(font_size), file_label="contrast", warnings_as_errors=False
    )
    assert any(issue.level == "ERROR" and "font_size" in issue.message for issue in issues)
    assert any("low contrast (4.48:1 < 4.5:1)" in issue.message for issue in issues)


@pytest.mark.parametrize("bold", ["false", 1, [], {}])
def test_invalid_bold_flag_cannot_buy_large_text_contrast_exemption(bold):
    issues = validate_data(
        contrast_document(19, bold), file_label="contrast", warnings_as_errors=False
    )
    assert any(issue.level == "ERROR" and "tucne" in issue.message for issue in issues)
    assert any("low contrast (4.48:1 < 4.5:1)" in issue.message for issue in issues)


@pytest.mark.parametrize(
    ("font_size", "bold", "warning"), [(12, False, True), (24, False, False), (19, True, False)]
)
def test_valid_small_and_large_font_contrast_controls(font_size, bold, warning):
    issues = validate_data(
        contrast_document(font_size, bold), file_label="contrast", warnings_as_errors=False
    )
    assert not any(
        issue.level == "ERROR" and ZNACKA_NAVRH_VADNY in issue.message for issue in issues
    )
    assert any("low contrast" in issue.message for issue in issues) is warning
