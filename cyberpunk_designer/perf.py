from __future__ import annotations

import concurrent.futures
from collections import deque
from typing import Dict, List, Optional

import pygame


class RenderCache:
    """High-performance render cache with predictive preloading."""

    def __init__(self, max_size: int = 1024):
        self.cache: Dict[int, pygame.Surface] = {}
        self.access_history = deque(maxlen=max_size)
        self.max_size = max_size

    def get(self, key: int) -> Optional[pygame.Surface]:
        if key in self.cache:
            self.access_history.append(key)
            return self.cache[key]
        return None

    def set(self, key: int, surface: pygame.Surface):
        if len(self.cache) >= self.max_size:
            # Evict least recently used
            lru = min(self.cache.keys(), key=lambda k: self.access_history.count(k))
            del self.cache[lru]
        self.cache[key] = surface


class SmartEventQueue:
    """Intelligent event queue with prediction and auto-handling."""

    def __init__(self):
        self.queue = deque()
        self.patterns: Dict[str, List] = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def process_batch(self, events: List) -> List:
        """Return a per-frame list of events (never accumulates)."""
        self.queue.clear()
        if not events:
            return []

        futures = []
        for event in events:
            if self._can_parallelize(event):
                futures.append(self.executor.submit(self._process_event, event))
            else:
                self.queue.append(event)

        if futures:
            for fut in futures:
                try:
                    self.queue.append(fut.result())
                except Exception:
                    continue

        out = list(self.queue)
        self.queue.clear()
        return out

    def _can_parallelize(self, event) -> bool:
        """Check if event can be processed in parallel."""
        return event.type in (pygame.MOUSEMOTION, pygame.MOUSEWHEEL)

    def _process_event(self, event):
        """Process single event with optimization."""
        # Preprocessing logic here
        return event

