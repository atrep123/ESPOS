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


def test_multiple_handlers_same_event():
    mgr = EventManager()
    a, b = [], []
    mgr.subscribe(pygame.KEYDOWN, lambda ev: a.append(ev))
    mgr.subscribe(pygame.KEYDOWN, lambda ev: b.append(ev))
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_x}))
    mgr.dispatch_all()
    assert len(a) == 1
    assert len(b) == 1


def test_right_click_not_debounced():
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    rc = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3})
    mgr.post(rc)
    times[0] = 0.01
    mgr.post(rc)
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 2


def test_dispatch_all_empty_queue():
    mgr = EventManager()
    called = []
    mgr.dispatch_all(lambda ev: called.append(ev))
    assert called == []


def test_left_click_allowed_after_debounce_window():
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})
    mgr.post(click)
    times[0] = 0.2  # 200ms > 100ms debounce
    mgr.post(click)
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 2


def test_post_preserves_insertion_order_same_priority():
    mgr = EventManager()
    events = []
    mgr.subscribe(pygame.KEYDOWN, lambda ev: events.append(ev.key))
    for k in [pygame.K_a, pygame.K_b, pygame.K_c]:
        mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": k}), priority=5)
    mgr.dispatch_all()
    assert events == [pygame.K_a, pygame.K_b, pygame.K_c]


def test_subscribe_does_not_affect_already_queued():
    mgr = EventManager()
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_z}))
    late = []
    mgr.subscribe(pygame.KEYDOWN, lambda ev: late.append(ev))
    mgr.dispatch_all()
    # handler registered after post still receives event
    assert len(late) == 1


def test_default_debounce_ms_is_80():
    """Kill mutant: debounce_click_ms=80 → 81."""
    mgr = EventManager()
    assert mgr._debounce_click_s == 80 / 1000.0


def test_seq_starts_at_zero():
    """Kill mutant: _seq=0 → 1."""
    mgr = EventManager()
    assert mgr._seq == 0


def test_last_click_ts_very_negative():
    """Kill mutant: _last_click_ts=-1e9 → -2e9."""
    mgr = EventManager()
    assert mgr._last_click_ts == -1e9


def test_debounce_division_exact():
    """Kill mutant: / 1000.0 → / 1001.0."""
    mgr = EventManager(debounce_click_ms=100)
    assert mgr._debounce_click_s == 0.1


def test_default_priority_is_10():
    """Kill mutant: priority=10 → 11."""
    mgr = EventManager()
    ev_lo = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a})
    ev_hi = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_b})
    # Post with explicit priority 10 — should interleave correctly with default
    mgr.post(ev_lo)  # default priority=10
    mgr.post(ev_hi, priority=10)  # same priority, should come after due to seq
    events = []
    mgr.subscribe(pygame.KEYDOWN, lambda ev: events.append(ev.key))
    mgr.dispatch_all()
    assert events == [pygame.K_a, pygame.K_b]


# ---------------------------------------------------------------------------
# AV: Event manager re-entrancy and edge-case tests
# ---------------------------------------------------------------------------


def test_exception_in_handler_propagates():
    """An exception in a handler propagates (no silent swallow)."""
    mgr = EventManager()

    def bad_handler(ev):
        raise ValueError("boom")

    mgr.subscribe(pygame.KEYDOWN, bad_handler)
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
    import pytest

    with pytest.raises(ValueError, match="boom"):
        mgr.dispatch_all()


def test_exception_in_first_handler_stops_rest():
    """If first handler raises, second handler is not called."""
    mgr = EventManager()
    called = []

    def bad(ev):
        raise RuntimeError("fail")

    def good(ev):
        called.append(ev)

    mgr.subscribe(pygame.KEYDOWN, bad)
    mgr.subscribe(pygame.KEYDOWN, good)
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
    import pytest

    with pytest.raises(RuntimeError):
        mgr.dispatch_all()
    assert called == []


def test_mass_subscriptions():
    """100 handlers for the same event type all get called."""
    mgr = EventManager()
    counters = [0] * 100
    for i in range(100):
        idx = i
        mgr.subscribe(pygame.KEYDOWN, lambda ev, j=idx: counters.__setitem__(j, 1))
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
    mgr.dispatch_all()
    assert sum(counters) == 100


def test_many_events_dispatched_in_order():
    """50 events maintain priority + insertion order."""
    mgr = EventManager()
    received = []
    mgr.subscribe(pygame.KEYDOWN, lambda ev: received.append(ev.key))
    for i in range(50):
        mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": i}), priority=10)
    mgr.dispatch_all()
    assert received == list(range(50))


def test_debounce_exact_boundary():
    """Click exactly at debounce boundary is allowed."""
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})
    mgr.post(click)
    times[0] = 0.1  # exactly 100ms
    mgr.post(click)
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 2


def test_debounce_just_under_boundary():
    """Click just under debounce boundary is dropped."""
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})
    mgr.post(click)
    times[0] = 0.099  # 99ms < 100ms
    mgr.post(click)
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 1


def test_middle_click_not_debounced():
    """Middle mouse button (button=2) is not debounced."""
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 2})
    mgr.post(click)
    times[0] = 0.01
    mgr.post(click)
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 2


def test_mixed_event_types_only_left_click_debounced():
    """Other events between debounced clicks are not affected."""
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})
    key = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a})
    mgr.post(click)
    times[0] = 0.01
    mgr.post(key)  # should not be debounced
    mgr.post(click)  # should be debounced
    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 2  # click + key, second click dropped


def test_dispatch_all_clears_queue():
    """After dispatch_all, queue is empty."""
    mgr = EventManager()
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
    mgr.dispatch_all()
    second = []
    mgr.dispatch_all(lambda ev: second.append(ev))
    assert second == []


def test_subscribe_multiple_types():
    """One handler can subscribe to multiple event types."""
    mgr = EventManager()
    received = []
    for etype in [pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN]:
        mgr.subscribe(etype, lambda ev: received.append(ev.type))
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
    mgr.post(pygame.event.Event(pygame.KEYUP, {"key": pygame.K_a}))
    mgr.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3}))
    mgr.dispatch_all()
    assert received == [pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN]


def test_seq_increments_by_one():
    """Kill mutant: _seq += 1 → _seq += 2."""
    mgr = EventManager()
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
    assert mgr._seq == 1
    mgr.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_b}))
    assert mgr._seq == 2


def test_debounce_uses_subtraction_not_addition():
    """Kill mutant: (now - last) → (now + last)."""
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})

    # First click at t=1.0
    times[0] = 1.0
    mgr.post(click)
    # Second click at t=1.05 — within 100ms, should be debounced
    times[0] = 1.05
    mgr.post(click)

    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 1  # only first click


def test_debounce_boundary_exact_window():
    """Kill mutant: < → <= (boundary at exactly debounce window)."""
    times = [0.0]
    mgr = EventManager(debounce_click_ms=100, monotonic=lambda: times[0])
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1})

    times[0] = 0.0
    mgr.post(click)
    # Second click at exactly 100ms — should NOT be debounced (< not <=)
    times[0] = 0.1
    mgr.post(click)

    events = []
    mgr.dispatch_all(lambda ev: events.append(ev))
    assert len(events) == 2
