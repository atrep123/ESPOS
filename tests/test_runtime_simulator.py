"""Integration regressions execute the production C task, not Python UI logic."""

import json
import os
import shutil

import pytest

from tools.espos_runtime_simulator import run


@pytest.fixture
def scene(tmp_path):
    path = tmp_path / "scene.json"
    path.write_text(
        json.dumps(
            {
                "scenes": {
                    "main": {
                        "width": 256,
                        "height": 128,
                        "widgets": [
                            {
                                "type": "slider",
                                "id": "level",
                                "x": 10,
                                "y": 10,
                                "width": 90,
                                "height": 20,
                                "value": 4,
                                "min_value": 0,
                                "max_value": 6,
                            },
                            {
                                "type": "checkbox",
                                "id": "enabled",
                                "x": 10,
                                "y": 50,
                                "width": 90,
                                "height": 20,
                                "text": "Enabled",
                            },
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.skipif(not shutil.which("gcc"), reason="existing GCC required")
def test_production_edit_clamp_exit_navigation_and_checkbox(scene, tmp_path):
    initial = tmp_path / "initial.pgm"
    edited = tmp_path / "edited.pgm"
    before = run(scene, initial, [])
    # A enters editor; right adds 5/clamps; B exits; down moves; A toggles.
    after = run(scene, edited, [0, 6, 6, 6, 6, 1, 4, 0])
    assert before["widgets"][0]["value"] == 4
    assert after["widgets"][0]["value"] == 6
    assert after["widgets"][1]["checked"] == 1
    assert initial.read_bytes() != edited.read_bytes()
    assert edited.read_bytes().startswith(b"P5\n256 128\n255\n")
    assert len(edited.read_bytes().split(b"\n", 3)[3]) == 256 * 128


@pytest.mark.skipif(not shutil.which("gcc"), reason="existing GCC required")
@pytest.mark.parametrize("state", ["disconnected", "error"])
def test_simulated_transport_failure_keeps_frame_black(scene, tmp_path, state):
    output = tmp_path / "failed.pgm"
    result = run(scene, output, [0, 6], state)
    assert result["display_status"] != 0
    assert result["widgets"][0]["value"] == 6
    assert not any(output.read_bytes().split(b"\n", 3)[3])


def test_bounded_input_rejected_before_compile(tmp_path):
    with pytest.raises(ValueError, match="At most 256"):
        run(tmp_path / "unused.json", tmp_path / "unused.pgm", [0] * 257)
    with pytest.raises(ValueError, match="At most 256"):
        run(tmp_path / "unused.json", tmp_path / "unused.pgm", [-1])


@pytest.mark.skipif(
    os.name != "nt" or not shutil.which("gcc"), reason="Windows fibers and GCC required"
)
def test_actual_app_subscriber_and_visual_logic_roundtrip(tmp_path):
    scene = tmp_path / "app.json"
    widgets = [
        {
            "type": "button",
            "id": "menu.item0",
            "x": 10,
            "y": 10,
            "width": 90,
            "height": 20,
            "text": "Display",
            "events": {
                "on_press": [
                    {"type": "set_widget", "widget": "status", "prop": "text", "text": "pressed"}
                ]
            },
        },
        {
            "type": "button",
            "id": "list.item0",
            "x": 10,
            "y": 35,
            "width": 90,
            "height": 20,
            "text": "Contrast",
        },
        {
            "type": "button",
            "id": "edit_contrast.value",
            "x": 10,
            "y": 60,
            "width": 90,
            "height": 20,
            "text": "0",
            "runtime": "bind=contrast;kind=int;min=0;max=255;step=8",
        },
        {
            "type": "label",
            "id": "status",
            "x": 120,
            "y": 10,
            "width": 110,
            "height": 20,
            "text": "cold",
        },
    ]
    rules = [
        {
            "trigger": {"type": "boot"},
            "actions": [
                {"type": "set_widget", "widget": "status", "prop": "text", "text": "booted"}
            ],
        }
    ]
    scene.write_text(
        json.dumps(
            {"scenes": {"main": {"width": 256, "height": 128, "widgets": widgets, "rules": rules}}}
        ),
        encoding="utf-8",
    )
    initial = run(scene, tmp_path / "boot.pgm", [], app=True)
    # Inject the real widget-action topic; handlers and commands execute unchanged.
    # This isolates subscriber/logic coverage; the numeric-input test covers focus.
    display = run(scene, tmp_path / "display.pgm", ["action:menu.item0:0"], app=True)
    editor = run(
        scene, tmp_path / "editor.pgm", ["action:menu.item0:0", "action:list.item0:0"], app=True
    )
    returned = run(
        scene,
        tmp_path / "returned.pgm",
        ["action:menu.item0:0", "action:list.item0:0", 1, 1],
        app=True,
    )
    repeated = run(
        scene, tmp_path / "repeated.pgm", ["action:menu.item0:0", "action:list.item0:0"], app=True
    )
    assert repeated == editor
    assert (tmp_path / "repeated.pgm").read_bytes() == (tmp_path / "editor.pgm").read_bytes()
    assert [state["app_screen"] for state in (initial, display, editor, returned)] == [0, 1, 4, 0]
    assert initial["texts"][3] == "booted"
    assert display["texts"][3] == "pressed"
    assert [w["visible"] for w in initial["widgets"][:3]] == [1, 0, 0]
    assert [w["visible"] for w in display["widgets"][:3]] == [0, 1, 0]
    assert [w["visible"] for w in editor["widgets"][:3]] == [0, 0, 1]
    assert [w["visible"] for w in returned["widgets"][:3]] == [1, 0, 0]
    for state in (initial, display, editor, returned):
        assert state["logic_booted"] == 1
        assert state["bus_drops"] == 0
        assert 0 < state["scheduler_steps"] < 100000
    assert (tmp_path / "boot.pgm").read_bytes() != (tmp_path / "editor.pgm").read_bytes()


@pytest.mark.skipif(
    os.name != "nt" or not shutil.which("gcc"), reason="Windows fibers and GCC required"
)
def test_app_roundtrip_via_input_ids_only(tmp_path):
    """No TOP_UI_ACTION injection: production focus must recover at app boot."""
    scene = tmp_path / "input-app.json"
    widgets = [
        {
            "type": "button",
            "id": "menu.item0",
            "x": 10,
            "y": 10,
            "width": 90,
            "height": 20,
            "text": "Display",
        },
        {
            "type": "button",
            "id": "list.item0",
            "x": 10,
            "y": 35,
            "width": 90,
            "height": 20,
            "text": "Contrast",
        },
        {
            "type": "button",
            "id": "edit_contrast.value",
            "x": 10,
            "y": 60,
            "width": 90,
            "height": 20,
            "text": "0",
            "runtime": "bind=contrast;kind=int;min=0;max=255;step=8",
        },
    ]
    scene.write_text(
        json.dumps({"scenes": {"main": {"width": 256, "height": 128, "widgets": widgets}}}),
        encoding="utf-8",
    )
    # Assert every checkpoint immediately so boot focus failure reports promptly.
    checkpoints = [
        ("menu", [], 0, [1, 0, 0]),
        ("display", [0], 1, [0, 1, 0]),
        ("contrast", [0, 0], 4, [0, 0, 1]),
        ("back_display", [0, 0, 1], 1, [0, 1, 0]),
        ("back_menu", [0, 0, 1, 1], 0, [1, 0, 0]),
    ]
    frames = []
    for name, inputs, expected_screen, expected_visibility in checkpoints:
        output = tmp_path / f"input-{name}.pgm"
        state = run(scene, output, inputs, app=True)
        assert state["app_screen"] == expected_screen, (
            f"{name}: INPUT IDs {inputs} expected app screen {expected_screen}, "
            f"got {state['app_screen']}; production focus recovery required"
        )
        assert [w["visible"] for w in state["widgets"]] == expected_visibility
        assert state["bus_drops"] == 0
        frames.append(output.read_bytes())
    assert frames[0] != frames[1]
    assert frames[1] != frames[2]


@pytest.mark.skipif(
    os.name != "nt" or not shutil.which("gcc"), reason="Windows fibers and GCC required"
)
@pytest.mark.parametrize(
    ("kind", "root"),
    [(2, "rows.item0"), (3, "rows.item0"), (20, "rows")],
    ids=["single-visible", "single-enabled", "listmodel-length"],
)
def test_command_restores_focus_for_activation(tmp_path, kind, root):
    """Actual UI_CMD followed by A must recover from the last target disappearing."""
    scene = tmp_path / "focus-command.json"
    scene.write_text(
        json.dumps(
            {
                "scenes": {
                    "main": {
                        "width": 256,
                        "height": 128,
                        "widgets": [
                            {
                                "type": "button",
                                "id": "rows.item0",
                                "x": 10,
                                "y": 10,
                                "width": 90,
                                "height": 20,
                                "text": "Activate",
                                "events": {
                                    "on_press": [
                                        {
                                            "type": "set_widget",
                                            "widget": "marker",
                                            "prop": "value",
                                            "value": 7,
                                        }
                                    ]
                                },
                            },
                            {
                                "type": "label",
                                "id": "marker",
                                "x": 120,
                                "y": 10,
                                "width": 90,
                                "height": 20,
                                "text": "Marker",
                                "value": 0,
                            },
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "restored.pgm"
    state = run(scene, output, [f"cmd:{kind}:{root}:0", f"cmd:{kind}:{root}:1", 0], app=True)
    assert state["widgets"][0]["visible"] == 1
    assert state["widgets"][1]["value"] == 7, (
        f"command {kind} restored target but INPUT_ID_A could not activate it"
    )
    assert state["bus_drops"] == 0


@pytest.mark.skipif(
    os.name != "nt" or not shutil.which("gcc"), reason="Windows fibers and GCC required"
)
@pytest.mark.parametrize(
    ("kind", "root"),
    [(2, "rows.item0"), (3, "rows.item0"), (20, "rows")],
    ids=["single-visible", "single-enabled", "listmodel-length"],
)
def test_command_preserves_existing_focus(tmp_path, kind, root):
    """Restoring another target must not redirect activation away from valid focus."""
    scene = tmp_path / "focus-preserved.json"
    scene.write_text(
        json.dumps(
            {
                "scenes": {
                    "main": {
                        "width": 256,
                        "height": 128,
                        "widgets": [
                            {
                                "type": "button",
                                "id": "stable",
                                "x": 10,
                                "y": 40,
                                "width": 90,
                                "height": 20,
                                "text": "Stable",
                                "events": {
                                    "on_press": [
                                        {
                                            "type": "set_widget",
                                            "widget": "marker",
                                            "prop": "value",
                                            "value": 7,
                                        }
                                    ]
                                },
                            },
                            {
                                "type": "button",
                                "id": "rows.item0",
                                "x": 10,
                                "y": 10,
                                "width": 90,
                                "height": 20,
                                "text": "Other",
                                "events": {
                                    "on_press": [
                                        {
                                            "type": "set_widget",
                                            "widget": "marker",
                                            "prop": "value",
                                            "value": 9,
                                        }
                                    ]
                                },
                            },
                            {
                                "type": "label",
                                "id": "marker",
                                "x": 120,
                                "y": 10,
                                "width": 90,
                                "height": 20,
                                "text": "Marker",
                                "value": 0,
                            },
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    state = run(
        scene,
        tmp_path / "preserved.pgm",
        [f"cmd:{kind}:{root}:0", f"cmd:{kind}:{root}:1", 0],
        app=True,
    )
    assert state["widgets"][2]["value"] == 7
    assert state["bus_drops"] == 0
