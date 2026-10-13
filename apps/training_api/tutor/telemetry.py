"""Bounded, public-safe runtime metrics for Tutor delivery."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import RLock

from ..learning_models import TutorMode


@dataclass(frozen=True)
class TutorMetricEvent:
    session_id: str
    mode: TutorMode
    latency_ms: int
    retry_count: int
    fallback_reason: str | None


class TutorMetrics:
    def __init__(self, max_events: int = 500) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._events: deque[TutorMetricEvent] = deque(maxlen=max_events)
        self._lock = RLock()

    def record(self, event: TutorMetricEvent) -> None:
        with self._lock:
            self._events.append(event)

    def snapshot(self, session_id: str | None = None) -> tuple[TutorMetricEvent, ...]:
        with self._lock:
            if session_id is None:
                return tuple(self._events)
            return tuple(
                event for event in self._events if event.session_id == session_id
            )
