"""Thread-safe process-local storage for authoritative CaseSession objects."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from threading import RLock
from typing import TypeVar

from core.case_engine import CaseSession


class SessionNotFoundError(LookupError):
    """Raised when a Session ID is absent from the process-local repository."""


class DuplicateSessionError(RuntimeError):
    """Raised when a generated Session ID already exists."""


ResultT = TypeVar("ResultT")


class SessionRepository:
    """Own mutable aggregates and expose them only inside locked callbacks."""

    def __init__(self) -> None:
        self._sessions: dict[str, CaseSession] = {}
        self._lock = RLock()

    def add(self, aggregate: CaseSession) -> None:
        session_id = aggregate.session.session_id
        with self._lock:
            if session_id in self._sessions:
                raise DuplicateSessionError(session_id)
            self._sessions[session_id] = aggregate

    def inspect(
        self,
        session_id: str,
        reader: Callable[[CaseSession], ResultT],
    ) -> ResultT:
        with self._lock:
            return reader(self._require(session_id))

    def mutate(
        self,
        session_id: str,
        command: Callable[[CaseSession], ResultT],
    ) -> ResultT:
        with self._lock:
            return command(self._require(session_id))

    def mutate_atomically(
        self,
        session_id: str,
        command: Callable[[CaseSession], ResultT],
    ) -> ResultT:
        """Commit a command only after every operation succeeds."""

        with self._lock:
            candidate = deepcopy(self._require(session_id))
            result = command(candidate)
            self._sessions[session_id] = candidate
            return result

    def _require(self, session_id: str) -> CaseSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc
