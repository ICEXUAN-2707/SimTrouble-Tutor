"""Application service for one-shot diagnosis evaluation and report access."""

from __future__ import annotations

from ..learning_models import DiagnosisSubmission, TrainingReportV04
from ..session_models import SessionView
from ..session_repository import SessionNotFoundError
from ..session_service import SessionService
from ..training_records import TrainingRecordStore
from .report import TrainingReportBuilder
from .repository import DiagnosisAlreadySubmittedError, ReportNotReadyError, ReportRepository


class DiagnosisService:
    def __init__(
        self,
        sessions: SessionService,
        *,
        reports: ReportRepository | None = None,
        builder: TrainingReportBuilder | None = None,
        records: TrainingRecordStore | None = None,
    ) -> None:
        self._sessions = sessions
        self._reports = reports or ReportRepository()
        self._builder = builder or TrainingReportBuilder()
        self._records = records

    def get_session(self, session_id: str, *, user_id: str | None = None) -> SessionView:
        try:
            return self._sessions.get(session_id, user_id=user_id)
        except SessionNotFoundError:
            if self._records is not None and user_id is not None:
                record = self._records.get_completed(user_id, session_id)
                if record is not None:
                    return record.session
            raise

    def submit(
        self,
        session_id: str,
        submission: DiagnosisSubmission,
        *,
        user_id: str | None = None,
    ) -> SessionView:
        # Authorize before consulting the report create-once fast path. Otherwise
        # an existing report can reveal both Session existence and completion.
        self.get_session(session_id, user_id=user_id)
        if self._records is not None and user_id is not None:
            if self._records.get_completed(user_id, session_id) is not None:
                raise DiagnosisAlreadySubmittedError(session_id)
        completion = None

        def persist(session: SessionView, report: TrainingReportV04) -> None:
            if self._records is not None and user_id is not None:
                self._records.save_completed(user_id, session, report)

        def complete() -> TrainingReportV04:
            nonlocal completion
            completion = self._sessions.complete_diagnosis(
                session_id,
                submission,
                self._builder.build,
                user_id=user_id,
                persist_completed=persist,
            )
            return completion.report

        self._reports.create_once(session_id, complete)
        assert completion is not None
        return completion.submitted_session

    def report(
        self,
        session_id: str,
        *,
        user_id: str | None = None,
    ) -> TrainingReportV04:
        self.get_session(session_id, user_id=user_id)
        try:
            return self._reports.get(session_id)
        except ReportNotReadyError:
            if self._records is not None and user_id is not None:
                record = self._records.get_completed(user_id, session_id)
                if record is not None:
                    return record.report
            raise


def build_diagnosis_service(
    sessions: SessionService, *, records: TrainingRecordStore | None = None
) -> DiagnosisService:
    return DiagnosisService(sessions, records=records)
