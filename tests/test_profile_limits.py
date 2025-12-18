from ui_designer import HARDWARE_PROFILES, UIDesigner


def test_profile_limits_coerce_to_float(monkeypatch):
    designer = UIDesigner(16, 16)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    monkeypatch.setitem(
        HARDWARE_PROFILES,
        "custom",
        {
            "label": "Custom",
            "width": 16,
            "height": 16,
            "color_depth": 1,
            "max_fb_kb": "5.5",
            "max_flash_kb": "7",
        },
    )

    est = designer.estimate_resources(profile="custom")

    assert est["max_fb_kb"] == 5.5
    assert est["max_flash_kb"] == 7.0
    monkeypatch.delitem(HARDWARE_PROFILES, "custom")


def test_profile_limits_negative_or_invalid_reset_to_zero(monkeypatch):
    designer = UIDesigner(8, 8)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    monkeypatch.setitem(
        HARDWARE_PROFILES,
        "bad",
        {
            "label": "Bad",
            "width": 8,
            "height": 8,
            "color_depth": 1,
            "max_fb_kb": -1,
            "max_flash_kb": None,
        },
    )

    est = designer.estimate_resources(profile="bad")

    assert est["max_fb_kb"] == 0.0
    assert est["max_flash_kb"] == 0.0
    monkeypatch.delitem(HARDWARE_PROFILES, "bad")
