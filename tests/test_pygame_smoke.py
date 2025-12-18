
import pytest


@pytest.mark.smoke
def test_pygame_headless_import_and_display(monkeypatch):
    """
    Basic headless smoke to ensure pygame can initialize and the UI module imports.
    """
    # Force headless mode to avoid display/audio issues in CI
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")

    import pygame

    pygame.display.init()
    try:
        screen = pygame.display.set_mode((1, 1))
        assert screen is not None

        # Import main pygame-based module to catch import errors early
        import ui_designer  # noqa: F401
    finally:
        pygame.quit()


@pytest.mark.smoke
def test_designer_scene_create_and_save(tmp_path, monkeypatch):
    """
    Ensure UIDesigner can build a scene, add a widget, and save JSON without auto-export side effects.
    """
    monkeypatch.setenv("ESP32OS_AUTO_EXPORT", "0")
    from ui_designer import UIDesigner

    designer = UIDesigner(width=128, height=64)
    scene = designer.create_scene("demo")
    designer.current_scene = scene.name
    designer.enable_pixel_art_mode()

    designer.add_widget("button", scene_name="demo", x=10, y=8, width=30, height=12, text="OK")

    out = tmp_path / "demo.json"
    designer.save_to_json(str(out))

    data = out.read_text(encoding="utf-8")
    assert '"demo"' in data
    assert '"button"' in data
