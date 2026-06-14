from tools.validate_design import validate_data


def _make(widget, *, margin=8):
    return {
        "scenes": {
            "dial": {
                "width": 240,
                "height": 240,
                "display_shape": "round",
                "round_safe_margin": margin,
                "widgets": [widget],
            }
        }
    }


def _round_issues(data, **kwargs):
    return [
        issue
        for issue in validate_data(data, file_label="test", warnings_as_errors=False, **kwargs)
        if "round safe area" in issue.message
    ]


def test_round_display_warns_when_widget_corner_enters_clipped_area():
    data = _make(
        {
            "type": "label",
            "x": 5,
            "y": 110,
            "width": 80,
            "height": 16,
            "text": "EDGE",
        }
    )

    issues = _round_issues(data)

    assert len(issues) == 1
    assert issues[0].level == "WARN"
    assert "outside round safe area" in issues[0].message


def test_round_display_accepts_widget_inside_safe_circle():
    data = _make(
        {
            "type": "label",
            "x": 80,
            "y": 110,
            "width": 80,
            "height": 16,
            "text": "CENTER",
        }
    )

    assert _round_issues(data) == []


def test_round_safe_area_warning_is_critical_under_strict_mode():
    data = _make(
        {
            "type": "button",
            "x": 8,
            "y": 150,
            "width": 224,
            "height": 34,
            "text": "TOO WIDE",
        }
    )

    issues = _round_issues(data, strict_critical=True)

    assert len(issues) == 1
    assert issues[0].level == "ERROR"
