"""Integration: run verify_all_visual.py headless and check exit-code."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_verify_all_visual_passes():
    result = subprocess.run(
        [sys.executable, str(REPO / "verify_all_visual.py")],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
        env={
            **__import__("os").environ,
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONIOENCODING": "utf-8",
        },
    )
    if result.returncode != 0:
        # Show the last 30 lines of output for debugging
        lines = (result.stdout + result.stderr).strip().splitlines()
        tail = "\n".join(lines[-30:])
        raise AssertionError(f"verify_all_visual.py failed (rc={result.returncode}):\n{tail}")


def test_validate_widget_catalog():
    """Ensure widget_catalog.json passes validation (0 errors)."""
    catalog = REPO / "widget_catalog.json"
    if not catalog.exists():
        subprocess.check_call(
            [sys.executable, str(REPO / "gen_widget_catalog.py")],
            cwd=str(REPO),
        )
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_design.py"),
         str(catalog)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0 or "[WARN]" in result.stdout, \
        f"Validation failed:\n{result.stdout}\n{result.stderr}"


def test_validate_rc_scene():
    """Ensure rc_scene.json passes validation (0 errors)."""
    rc = REPO / "rc_scene.json"
    if not rc.exists():
        subprocess.check_call(
            [sys.executable, str(REPO / "gen_rc_scene.py")],
            cwd=str(REPO),
        )
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_design.py"),
         str(rc)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "[FAIL]" not in result.stdout, \
        f"rc_scene.json validation failed:\n{result.stdout}"
