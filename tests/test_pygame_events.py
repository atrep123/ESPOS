from types import SimpleNamespace

import pygame

from cyberpunk_editor import CyberpunkEditorApp


def test_coalesce_motion_and_wheel_keeps_latest_only(monkeypatch):
    # Build fake events (do not require display)
    e1 = SimpleNamespace(type=pygame.MOUSEMOTION, pos=(0, 0))
    e2 = SimpleNamespace(type=pygame.MOUSEMOTION, pos=(10, 10))
    e3 = SimpleNamespace(type=pygame.MOUSEWHEEL, x=0, y=1)
    e4 = SimpleNamespace(type=pygame.MOUSEWHEEL, x=0, y=-1)
    e5 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a)

    events = [e1, e2, e3, e4, e5]
    filtered = CyberpunkEditorApp._coalesce_motion_and_wheel(events)  # type: ignore[attr-defined]

    # Only latest motion and wheel should remain, plus other events
    assert e2 in filtered and e1 not in filtered
    assert e4 in filtered and e3 not in filtered
    assert e5 in filtered
    # Order: non-motion/non-wheel in original order, then last motion, last wheel
    assert filtered[0] is e5
    assert filtered[-2] is e2
    assert filtered[-1] is e4


def test_dedupe_keydowns_keeps_first_only():
    e1 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=False)
    e2 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=True)  # duplicate
    e3 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_b)
    e4 = SimpleNamespace(type=pygame.KEYUP, key=pygame.K_a)

    filtered = CyberpunkEditorApp._dedupe_keydowns([e1, e2, e3, e4])  # type: ignore[attr-defined]

    assert e1 in filtered
    assert e2 not in filtered
    assert e3 in filtered
    assert e4 in filtered  # KEYUP must pass through
