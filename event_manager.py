import heapq
import time
from typing import Callable, Dict, List, Optional, Tuple

import pygame


class EventManager:
    """
    Small event manager with priority queue, simple debouncing, and subscriptions.

    - post(event, priority): enqueue an event with a priority (lower = earlier).
    - subscribe(event_type, handler): register a handler for a pygame event type.
    - dispatch_all(fallback): dispatch events to subscribers or fallback handler.
    """

    def __init__(
        self,
        *,
        debounce_click_ms: int = 80,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.subscriptions: Dict[int, List[Callable[[pygame.event.Event], None]]] = {}
        self._queue: List[Tuple[int, int, pygame.event.Event]] = []
        self._seq = 0
        self._last_click_ts = -1e9
        self._debounce_click_s = debounce_click_ms / 1000.0
        self._monotonic = monotonic

    def subscribe(self, event_type: int, handler: Callable[[pygame.event.Event], None]) -> None:
        self.subscriptions.setdefault(event_type, []).append(handler)

    def post(self, event: pygame.event.Event, priority: int = 10) -> None:
        if self._is_debounced(event):
            return
        heapq.heappush(self._queue, (priority, self._seq, event))
        self._seq += 1

    def dispatch_all(self, fallback: Optional[Callable[[pygame.event.Event], None]] = None) -> None:
        while self._queue:
            _, _, ev = heapq.heappop(self._queue)
            handlers = self.subscriptions.get(ev.type, [])
            if handlers:
                for h in handlers:
                    h(ev)
            elif fallback:
                fallback(ev)

    def _is_debounced(self, event: pygame.event.Event) -> bool:
        if (
            getattr(event, "type", None) == pygame.MOUSEBUTTONDOWN
            and getattr(event, "button", None) == 1
        ):
            now = self._monotonic()
            if self._last_click_ts >= 0 and (now - self._last_click_ts) < self._debounce_click_s:
                return True
            self._last_click_ts = now
        return False
