"""Application service for the frozen v0.4 Session command surface."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import TrainingCase
from core.models.contracts import DiagnosticStage

from .session_models import EvidenceResponse, SessionView
from .session_projector import SessionProjector
from .session_repository import SessionRepository


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASE_DIRECTORY = ROOT / "data" / "cases"


class CaseNotFoundError(LookupError):
    """Raised when the requested Case is absent from the approved catalog."""


class SessionStageConflictError(RuntimeError):
    """Raised when a command is not allowed in the current diagnostic stage."""


class SessionService:
    def __init__(
        self,
        repository: SessionRepository | None = None,
        cases: dict[str, TrainingCase] | None = None,
        evidence_manager: EvidenceManager | None = None,
        projector: SessionProjector | None = None,
    ) -> None:
        self._repository = repository or SessionRepository()
        self._cases = (
            cases
            if cases is not None
            else CaseLoader().load_directory(DEFAULT_CASE_DIRECTORY)
        )
        self._evidence = evidence_manager or EvidenceManager()
        self._projector = projector or SessionProjector()

    def create(self, case_id: str) -> SessionView:
        try:
            case = self._cases[case_id]
        except KeyError as exc:
            raise CaseNotFoundError(case_id) from exc

        aggregate = CaseSession(
            user_id=f"anonymous:{uuid4()}",
            case=case,
        )
        aggregate.transition_to(DiagnosticStage.OBSERVE)
        self._repository.add(aggregate)
        return self._projector.project(aggregate)

    def get(self, session_id: str) -> SessionView:
        return self._repository.inspect(session_id, self._projector.project)

    def request_evidence(
        self,
        session_id: str,
        evidence_id: str,
    ) -> EvidenceResponse:
        self._repository.mutate(
            session_id,
            lambda aggregate: self._guard_evidence_exists(aggregate, evidence_id),
        )

        def command(aggregate: CaseSession) -> EvidenceResponse:
            stage = aggregate.session.current_stage
            if stage is DiagnosticStage.OBSERVE:
                aggregate.transition_to(DiagnosticStage.INVESTIGATE)
            elif stage is DiagnosticStage.HYPOTHESIZE:
                aggregate.transition_to(DiagnosticStage.TEST)
            elif stage not in {
                DiagnosticStage.INVESTIGATE,
                DiagnosticStage.TEST,
                DiagnosticStage.UPDATE,
            }:
                raise SessionStageConflictError(
                    f"evidence is not allowed during {stage.value}"
                )

            released = self._evidence.request(aggregate, evidence_id)
            return EvidenceResponse(
                evidence=released,
                session=self._projector.project(aggregate),
            )

        return self._repository.mutate_atomically(session_id, command)

    def submit_hypothesis(self, session_id: str, hypothesis: str) -> SessionView:
        normalized = hypothesis.strip()
        if not normalized:
            raise ValueError("hypothesis must not be empty")

        def command(aggregate: CaseSession) -> SessionView:
            stage = aggregate.session.current_stage
            if stage is DiagnosticStage.INVESTIGATE:
                aggregate.transition_to(DiagnosticStage.HYPOTHESIZE)
            elif stage is DiagnosticStage.TEST:
                aggregate.transition_to(DiagnosticStage.UPDATE)
            elif stage not in {
                DiagnosticStage.HYPOTHESIZE,
                DiagnosticStage.UPDATE,
            }:
                raise SessionStageConflictError(
                    f"hypothesis is not allowed during {stage.value}"
                )

            aggregate.submit_hypothesis(normalized)
            return self._projector.project(aggregate)

        return self._repository.mutate_atomically(session_id, command)

    def _guard_evidence_exists(
        self,
        aggregate: CaseSession,
        evidence_id: str,
    ) -> None:
        if any(item.id == evidence_id for item in aggregate.authoritative_case.evidence):
            return
        # Preserve the Core denial Trace without advancing the diagnostic stage.
        self._evidence.request(aggregate, evidence_id)
        raise AssertionError("EvidenceManager must reject an unknown Evidence ID")
