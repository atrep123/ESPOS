import pygame

from event_manager import EventManager


def test_priority_dispatch_orders_events(monkeypatch):
    mgr = EventManager()
    order = []

    def handler(ev):
        order.append(ev.type)

    mgr.subscribe(pygame.QUIT, handler)
    mgr.subscribe(pygame.KEYDOWN, handler)

    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}), priority=5)
    mgr.post(pygame.event.Event(pygame.QUIT), priority=0)

    mgr.dispatch_all()
    assert order == [pygame.QUIT, pygame.KEYDOWN]


def test_click_debounce_drops_rapid_left_click(monkeypatch):
    times = [0.0]

    def fake_monotonic():
        return times[0]

    mgr = EventManager(debounce_click_ms=100, monotonic=fake_monotonic)
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})
    mgr.post(click, priority=1)
    times[0] = 0.05
    mgr.post(click, priority=1)  # should be dropped
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 1


def test_fallback_handler_receives_unsubscribed(monkeypatch):
    mgr = EventManager()
    events = []
    mgr.post(pygame.event.Event(pygame.USEREVENT, {"name": "custom"}), priority=1)
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 1
    assert events[0].type == pygame.USEREVENT
