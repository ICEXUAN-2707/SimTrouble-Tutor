"""Process-local, create-once storage for authoritative v0.4 reports."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from ..learning_models import TrainingReportV04


class DiagnosisAlreadySubmittedError(RuntimeError):
    """Raised when a Session already owns an authoritative report."""


class ReportNotReadyError(LookupError):
    """Raised when evaluation has not produced a report for a Session."""


class ReportRepository:
    def __init__(self) -> None:
        self._reports: dict[str, TrainingReportV04] = {}
        self._lock = RLock()

    def create_once(
        self,
        session_id: str,
        factory: Callable[[], TrainingReportV04],
    ) -> TrainingReportV04:
        with self._lock:
            if session_id in self._reports:
                raise DiagnosisAlreadySubmittedError(session_id)
            report = factory()
            self._reports[session_id] = report.model_copy(deep=True)
            return report.model_copy(deep=True)

    def get(self, session_id: str) -> TrainingReportV04:
        with self._lock:
            try:
                return self._reports[session_id].model_copy(deep=True)
            except KeyError as exc:
                raise ReportNotReadyError(session_id) from exc
