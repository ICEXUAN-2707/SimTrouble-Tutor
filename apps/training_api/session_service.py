"""Application service for the frozen v0.4 Session command surface."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import LearnerSession, TrainingCase
from core.models.contracts import DiagnosticStage

from .learning_models import DiagnosisSubmission, TrainingReportV04
from .session_models import EvidenceResponse, SessionView
from .session_projector import SessionProjector
from .session_repository import SessionNotFoundError, SessionRepository


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASE_DIRECTORY = ROOT / "data" / "cases"


class CaseNotFoundError(LookupError):
    """Raised when the requested Case is absent from the approved catalog."""


class SessionStageConflictError(RuntimeError):
    """Raised when a command is not allowed in the current diagnostic stage."""


class DiagnosisEvidenceError(ValueError):
    """Raised when a diagnosis cites Evidence not released to the Session."""


@dataclass(frozen=True)
class DiagnosisEvaluationContext:
    case: TrainingCase
    session: LearnerSession
    submission: DiagnosisSubmission


@dataclass(frozen=True)
class DiagnosisCompletion:
    submitted_session: SessionView
    report: TrainingReportV04


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

    def create(self, case_id: str, *, user_id: str | None = None) -> SessionView:
        try:
            case = self._cases[case_id]
        except KeyError as exc:
            raise CaseNotFoundError(case_id) from exc

        aggregate = CaseSession(
            user_id=user_id or f"anonymous:{uuid4()}",
            case=case,
        )
        aggregate.transition_to(DiagnosticStage.OBSERVE)
        self._repository.add(aggregate)
        return self._projector.project(aggregate)

    def get(self, session_id: str, *, user_id: str | None = None) -> SessionView:
        def reader(aggregate: CaseSession) -> SessionView:
            self._guard_owner(aggregate, user_id)
            return self._projector.project(aggregate)

        return self._repository.inspect(session_id, reader)

    def request_evidence(
        self,
        session_id: str,
        evidence_id: str,
        *,
        user_id: str | None = None,
    ) -> EvidenceResponse:
        def validate_request(aggregate: CaseSession) -> None:
            self._guard_owner(aggregate, user_id)
            self._guard_evidence_exists(aggregate, evidence_id)

        self._repository.mutate(session_id, validate_request)

        def command(aggregate: CaseSession) -> EvidenceResponse:
            self._guard_owner(aggregate, user_id)
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

    def submit_hypothesis(
        self,
        session_id: str,
        hypothesis: str,
        *,
        user_id: str | None = None,
    ) -> SessionView:
        normalized = hypothesis.strip()
        if not normalized:
            raise ValueError("hypothesis must not be empty")

        def command(aggregate: CaseSession) -> SessionView:
            self._guard_owner(aggregate, user_id)
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

    def record_tutor_requested(
        self,
        session_id: str,
        *,
        policy_rule_id: str,
        hint_level: int,
        suggested_action: str | None,
        user_id: str | None = None,
    ) -> None:
        def command(aggregate: CaseSession) -> None:
            self._guard_owner(aggregate, user_id)
            aggregate.record_tutor_requested(
                policy_rule_id=policy_rule_id,
                hint_level=hint_level,
                suggested_action=suggested_action,
            )

        self._repository.mutate(session_id, command)

    def record_tutor_delivered(
        self,
        session_id: str,
        *,
        latency_ms: int,
        retry_count: int,
        user_id: str | None = None,
    ) -> None:
        def command(aggregate: CaseSession) -> None:
            self._guard_owner(aggregate, user_id)
            aggregate.record_tutor_delivered(
                latency_ms=latency_ms,
                retry_count=retry_count,
            )

        self._repository.mutate(session_id, command)

    def record_tutor_fallback(
        self,
        session_id: str,
        *,
        latency_ms: int,
        retry_count: int,
        reason: str,
        user_id: str | None = None,
    ) -> None:
        def command(aggregate: CaseSession) -> None:
            self._guard_owner(aggregate, user_id)
            aggregate.record_tutor_fallback(
                latency_ms=latency_ms,
                retry_count=retry_count,
                reason=reason,
            )

        self._repository.mutate(session_id, command)

    def complete_diagnosis(
        self,
        session_id: str,
        submission: DiagnosisSubmission,
        build_report: Callable[[DiagnosisEvaluationContext], TrainingReportV04],
        *,
        user_id: str | None = None,
    ) -> DiagnosisCompletion:
        def command(aggregate: CaseSession) -> DiagnosisCompletion:
            self._guard_owner(aggregate, user_id)
            if aggregate.session.current_stage is not DiagnosticStage.UPDATE:
                raise SessionStageConflictError(
                    "diagnosis is allowed only after hypothesis update"
                )
            released = set(aggregate.session.evidence_seen)
            if not set(submission.cited_evidence_ids).issubset(released):
                raise DiagnosisEvidenceError(
                    "diagnosis may cite only Evidence released to this Session"
                )

            aggregate.transition_to(DiagnosticStage.DIAGNOSE)
            aggregate.record_diagnosis_submitted(
                diagnosis_type=submission.diagnosis_type.value,
                cited_evidence_ids=submission.cited_evidence_ids,
            )
            aggregate.transition_to(DiagnosticStage.REFLECT)
            submitted_session = self._projector.project(aggregate)
            context = DiagnosisEvaluationContext(
                case=aggregate.authoritative_case,
                session=aggregate.session,
                submission=submission,
            )
            report = build_report(context)
            aggregate.record_diagnosis_evaluated(
                assessment=report.diagnosis.assessment.value,
            )
            aggregate.record_report_generated(
                rubric_version=report.rubric_version,
            )
            aggregate.transition_to(DiagnosticStage.FINISH)
            return DiagnosisCompletion(
                submitted_session=submitted_session,
                report=report,
            )

        return self._repository.mutate_atomically(session_id, command)

    @staticmethod
    def _guard_owner(aggregate: CaseSession, user_id: str | None) -> None:
        owner = aggregate.session.user_id
        if user_id is None and owner.startswith("anonymous:"):
            return
        if user_id is not None and hmac.compare_digest(owner, user_id):
            return
        # Wrong-owner and absent Sessions intentionally share one public error.
        raise SessionNotFoundError(aggregate.session.session_id)

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
