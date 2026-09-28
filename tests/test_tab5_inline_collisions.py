"""Own-text fragments must distinguish inline layout from genuine collisions."""

from copy import deepcopy

import pytest

from tools.validate_design import validate_data


def document():
    return {
        "device": "tab5",
        "scenes": {
            "main": {
                "width": 1280,
                "height": 720,
                "widgets": [
                    {
                        "_widget_id": "field.1",
                        "type": "label",
                        "x": 100,
                        "y": 100,
                        "width": 600,
                        "height": 40,
                        "text": "typed text",
                    },
                    {
                        "_widget_id": "caption.2",
                        "type": "label",
                        "x": 100,
                        "y": 100,
                        "width": 100,
                        "height": 40,
                        "text": "CAPTION",
                    },
                ],
                "navrh": {
                    "prvky": {
                        "field.1": {"text_fragmenty": [[220, 105, 150, 20]]},
                        "caption.2": {
                            "text_fragmenty": [[100, 105, 100, 20]],
                            "rodic_id": "field.1",
                        },
                    }
                },
            }
        },
    }


def collisions(data):
    return [
        i
        for i in validate_data(
            data, file_label="inline", warnings_as_errors=False, strict_critical=True
        )
        if "OVERLAP (visible content collision)" in i.message
    ]


def test_measured_disjoint_own_text_is_not_a_collision():
    assert not collisions(document())


def test_measured_wrapped_gap_is_not_a_collision():
    data = document()
    data["scenes"]["main"]["navrh"]["prvky"]["field.1"]["text_fragmenty"] = [
        [100, 100, 150, 5],
        [100, 135, 150, 5],
    ]
    assert not collisions(data)


def test_real_inline_collision_is_still_critical_even_with_parent_id():
    data = document()
    data["scenes"]["main"]["navrh"]["prvky"]["field.1"]["text_fragmenty"] = [[190, 105, 150, 20]]
    assert len(collisions(data)) == 2
    assert all(i.level == "ERROR" for i in collisions(data))


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        [[0, 0, 0, 20]],
        [[0, 0, float("inf"), 20]],
        [[0, 0, True, 20]],
        [[0, 0, 10**400, 20]],
    ],
)
def test_invalid_or_missing_measurement_never_exempts_overlap(bad):
    data = document()
    data["scenes"]["main"]["navrh"]["prvky"]["caption.2"]["text_fragmenty"] = bad
    assert len(collisions(data)) == 2


def test_legacy_scene_keeps_strict_box_detection():
    data = document()
    data["scenes"]["main"].pop("navrh")
    assert len(collisions(data)) == 2


def test_measured_labels_cannot_exempt_interactive_hitbox_collision():
    data = document()
    data["scenes"]["main"]["widgets"][0]["type"] = "button"
    assert len(collisions(data)) == 2


def test_second_fragment_collision_is_not_hidden_by_clear_first_fragment():
    data = deepcopy(document())
    data["scenes"]["main"]["navrh"]["prvky"]["field.1"]["text_fragmenty"].append(
        [190, 105, 150, 20]
    )
    assert len(collisions(data)) == 2


@pytest.mark.parametrize(
    "bad",
    [
        [[9000, 105, 100, 20]],
        [[99, 105, 100, 20]],
        [[100, 105, 101, 20]],
    ],
)
def test_own_text_outside_its_widget_cannot_exempt_overlap(bad):
    data = document()
    data["scenes"]["main"]["navrh"]["prvky"]["caption.2"]["text_fragmenty"] = bad
    assert len(collisions(data)) == 2
