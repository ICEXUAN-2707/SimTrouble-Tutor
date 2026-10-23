"""Application service for one-shot diagnosis evaluation and report access."""

from __future__ import annotations

from ..learning_models import DiagnosisSubmission, TrainingReportV04
from ..session_models import SessionView
from ..session_service import SessionService
from .report import TrainingReportBuilder
from .repository import ReportRepository


class DiagnosisService:
    def __init__(
        self,
        sessions: SessionService,
        *,
        reports: ReportRepository | None = None,
        builder: TrainingReportBuilder | None = None,
    ) -> None:
        self._sessions = sessions
        self._reports = reports or ReportRepository()
        self._builder = builder or TrainingReportBuilder()

    def submit(
        self,
        session_id: str,
        submission: DiagnosisSubmission,
    ) -> SessionView:
        completion = None

        def complete() -> TrainingReportV04:
            nonlocal completion
            completion = self._sessions.complete_diagnosis(
                session_id,
                submission,
                self._builder.build,
            )
            return completion.report

        self._reports.create_once(session_id, complete)
        assert completion is not None
        return completion.submitted_session

    def report(self, session_id: str) -> TrainingReportV04:
        self._sessions.get(session_id)
        return self._reports.get(session_id)


def build_diagnosis_service(sessions: SessionService) -> DiagnosisService:
    return DiagnosisService(sessions)
