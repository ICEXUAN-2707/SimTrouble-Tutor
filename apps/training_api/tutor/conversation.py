"""Small process-local conversation store for the v0.4 runtime."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import RLock

from ..learning_models import TutorMessage, TutorResponse


class TutorConversationStore:
    def __init__(self, max_messages: int = 12) -> None:
        if max_messages < 2:
            raise ValueError("max_messages must be at least 2")
        self._messages: dict[str, deque[TutorMessage]] = defaultdict(
            lambda: deque(maxlen=max_messages)
        )
        self._lock = RLock()

    def history(self, session_id: str) -> tuple[TutorMessage, ...]:
        with self._lock:
            return tuple(self._messages.get(session_id, ()))

    def append_turn(
        self,
        session_id: str,
        learner_message: str,
        response: TutorResponse,
    ) -> None:
        with self._lock:
            messages = self._messages[session_id]
            messages.append(TutorMessage(role="learner", content=learner_message))
            messages.append(TutorMessage(role="tutor", content=response.message))
