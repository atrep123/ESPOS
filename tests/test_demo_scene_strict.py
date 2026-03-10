from pathlib import Path

from tools.validate_design import validate_data, validate_file

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_strict_critical_promotes_overlap_warning() -> None:
    data = {
        "width": 64,
        "height": 32,
        "scenes": {
            "main": {
                "width": 64,
                "height": 32,
                "widgets": [
                    {"type": "box", "x": 0, "y": 0, "width": 20, "height": 20},
                    {"type": "box", "x": 10, "y": 10, "width": 20, "height": 20},
                ],
            }
        },
    }

    plain = validate_data(data, file_label="test", warnings_as_errors=False)
    strict = validate_data(data, file_label="test", warnings_as_errors=False, strict_critical=True)

    assert any(i.level == "WARN" and "OVERLAP" in i.message for i in plain)
    assert any(i.level == "ERROR" and "OVERLAP" in i.message for i in strict)


def test_demo_scene_passes_strict_critical() -> None:
    issues = validate_file(
        REPO_ROOT / "demo_scene.json", warnings_as_errors=False, strict_critical=True
    )
    errors = [i for i in issues if i.level == "ERROR"]
    assert not errors, "\n".join(i.message for i in errors)
