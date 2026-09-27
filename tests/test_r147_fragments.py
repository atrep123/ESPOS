"""Independent R147 geometry controls; legacy boxes remain strict."""

from __future__ import annotations

from copy import deepcopy

import pytest

from tools.validate_design import (
    R147_ODSTUP_PX,
    ZNACKA_NAVRH_VADNY,
    ZNACKA_R147,
    _r147_nalezy,
    validate_data,
)


def document(fragments=None, *, measured=True, lines=None):
    widget = {
        "_widget_id": "own.1",
        "type": "label",
        "x": 100,
        "y": 100,
        "width": 400,
        "height": 100,
        "text": "own text",
        "color_fg": "#e4dfcc",
        "color_bg": "#14170f",
    }
    navrh = {"cary": lines or [[450, 90, 1, 140]], "prvky": {"own.1": {}}}
    if measured:
        navrh["prvky"]["own.1"]["text_fragmenty"] = fragments
    return {
        "device": "tab5",
        "scenes": {
            "main": {
                "width": 1280,
                "height": 720,
                "widgets": [widget],
                "navrh": navrh,
            }
        },
    }


def issues(data):
    return validate_data(data, file_label="fragments", warnings_as_errors=False)


def r147(data):
    return [i for i in issues(data) if ZNACKA_R147 in i.message]


def test_outside_actual_text_is_clear_but_legacy_remains_strict():
    measured = document([[110.25, 105.5, 120.75, 20]])
    assert r147(measured) == []
    legacy = document(measured=False)
    assert len(r147(legacy)) == 1
    assert "inkoust 100,100 400x100" in r147(legacy)[0].message
    # The geometry change is exclusively R147; all other findings identical.
    assert [(i.level, i.message) for i in issues(measured) if ZNACKA_R147 not in i.message] == [
        (i.level, i.message) for i in issues(legacy) if ZNACKA_R147 not in i.message
    ]


@pytest.mark.parametrize("line", [[150, 90, 1, 140], [90, 114, 250, 1]])
def test_true_horizontal_and_vertical_crossings_still_error(line):
    found = r147(document([[110.25, 105.5, 120.75, 20]], lines=[line]))
    assert len(found) == 1 and found[0].level == "ERROR"


def test_wrapped_gap_is_not_text_and_second_line_is_measured():
    fragments = [[110, 105, 120, 20], [110, 165, 80, 20]]
    assert r147(document(fragments, lines=[[90, 145, 250, 1]])) == []
    assert len(r147(document(fragments, lines=[[90, 174, 250, 1]]))) == 1
    assert len(r147(document(fragments, lines=[[150, 90, 1, 140]]))) == 1


def test_existing_margin_and_subpixel_horizontal_overlap_are_preserved():
    fragments = [[110.25, 105.5, 120.75, 20]]
    edge = 105.5 + R147_ODSTUP_PX
    assert (
        _r147_nalezy("w", (100, 100, 400, 100), "text", [(90, edge - 1, 250, 1)], fragments) == []
    )
    assert (
        len(_r147_nalezy("w", (100, 100, 400, 100), "text", [(90, edge, 250, 1)], fragments)) == 1
    )
    assert r147(document(fragments, lines=[[110, 90, 1, 140]])) == []
    assert len(r147(document(fragments, lines=[[111, 90, 1, 140]]))) == 1


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {},
        "measured",
        [None],
        [[1, 2, 3]],
        [[1, 2, 3, 4, 5]],
        [[True, 2, 3, 4]],
        [["1", 2, 3, 4]],
        [[1, 2, 0, 4]],
        [[1, 2, 3, -4]],
        [[float("nan"), 2, 3, 4]],
        [[1, float("inf"), 3, 4]],
        [[1e308, 2, 1e308, 4]],
        [[10**400, 2, 3, 4]],
        [[110, 105, 120, 20], [0, 0, 0, 0]],
    ],
)
def test_invalid_or_partial_measurements_cannot_turn_legacy_collision_green(bad):
    data = document(bad)
    assert r147(data) == r147(document(measured=False))
    invalid = [i for i in issues(data) if ZNACKA_NAVRH_VADNY in i.message]
    assert len(invalid) == 1 and invalid[0].level == "ERROR"
    assert "text_fragmenty" in invalid[0].message and "NEZMERENO" in invalid[0].message
    assert len(_r147_nalezy("w", (100, 100, 400, 100), "text", [(450, 90, 1, 140)], bad)) == 1


def test_missing_measurement_preserves_identical_legacy_diagnostics():
    data = document(measured=False)
    no_metadata = deepcopy(data)
    del no_metadata["scenes"]["main"]["navrh"]["prvky"]
    assert issues(data) == issues(no_metadata)


def test_supplied_main_and_translation_evidence_and_conservative_internal_space():
    main = _r147_nalezy(
        "main",
        (537, 248, 686, 12),
        "Zatím není co ukazovat",
        [(x, 140, 1, 229) for x in (609, 681, 753, 825, 897, 969, 1041, 1113, 1185)],
        [[785.297, 245, 189.391, 19]],
    )
    assert len(main) == 3
    assert [int(i.message.split(": cara ")[1].split(",")[0]) for i in main] == [825, 897, 969]
    translation = _r147_nalezy(
        "translation",
        (184, 210, 900, 21),
        "Nejkratší pulz má 10 vzorků.",
        [(x, 200, 1, 320) for x in (330, 485, 640, 795, 950)],
        [[184, 208, 280.969, 24]],
    )
    assert len(translation) == 1 and "cara 330," in translation[0].message


def test_profile_and_visibility_still_gate_fragment_measurements():
    data = document([[110, 105, 120, 20]], lines=[[150, 90, 1, 140]])
    assert len(r147(data)) == 1
    data["device"] = "oled256"
    assert r147(data) == []
    data["device"] = "tab5"
    data["scenes"]["main"]["widgets"][0]["visible"] = False
    assert r147(data) == []
