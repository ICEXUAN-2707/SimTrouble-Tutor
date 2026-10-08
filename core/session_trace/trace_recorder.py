"""Controlled append boundary for the frozen seven-field TraceEvent."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from core.models.contracts import DiagnosticStage, LearnerSession, TraceEvent

from .clock import Clock, normalize_utc_timestamp, utc_now


TraceActionType = Literal[
    "SessionStarted",
    "StateTransitioned",
    "StateTransitionRejected",
    "ActionPerformed",
    "EvidenceRequested",
    "EvidenceReleased",
    "EvidenceDenied",
    "HypothesisAdded",
    "HypothesisUpdated",
    "HypothesisRejected",
    "SessionFinished",
]


class SessionTraceRecorder:
    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = utc_now if clock is None else clock

    def record_session_started(self, session: LearnerSession) -> None:
        self._record(
            session,
            action_type="SessionStarted",
            result={"status": "started"},
        )

    def record_state_transitioned(
        self,
        session: LearnerSession,
        *,
        from_stage: DiagnosticStage,
    ) -> None:
        self._record(
            session,
            action_type="StateTransitioned",
            result={
                "status": "accepted",
                "from_stage": from_stage.value,
                "to_stage": session.current_stage.value,
            },
        )

    def record_state_transition_rejected(
        self,
        session: LearnerSession,
        *,
        requested_stage: DiagnosticStage,
    ) -> None:
        self._record(
            session,
            action_type="StateTransitionRejected",
            result={
                "status": "rejected",
                "from_stage": session.current_stage.value,
                "requested_stage": requested_stage.value,
                "reason": "illegal_transition",
            },
        )

    def record_session_finished(self, session: LearnerSession) -> None:
        self._record(
            session,
            action_type="SessionFinished",
            result={"status": "finished"},
        )

    def record_action_performed(self, session: LearnerSession) -> None:
        self._record(
            session,
            action_type="ActionPerformed",
            result={"status": "recorded"},
        )

    def record_evidence_requested(
        self,
        session: LearnerSession,
        *,
        evidence_id: str,
    ) -> None:
        self._record(
            session,
            action_type="EvidenceRequested",
            evidence_id=evidence_id,
            result={"status": "requested"},
        )

    def record_evidence_released(
        self,
        session: LearnerSession,
        *,
        evidence_id: str,
    ) -> None:
        self._record(
            session,
            action_type="EvidenceReleased",
            evidence_id=evidence_id,
            result={"status": "released"},
        )

    def record_evidence_denied(
        self,
        session: LearnerSession,
        *,
        evidence_id: str,
    ) -> None:
        self._record(
            session,
            action_type="EvidenceDenied",
            evidence_id=evidence_id,
            result={"status": "denied", "reason": "evidence_not_found"},
        )

    def record_hypothesis_added(self, session: LearnerSession) -> None:
        self._record(
            session,
            action_type="HypothesisAdded",
            result={"status": "recorded"},
        )

    def record_hypothesis_updated(self, session: LearnerSession) -> None:
        self._record(
            session,
            action_type="HypothesisUpdated",
            result={"status": "recorded"},
        )

    def record_hypothesis_rejected(self, session: LearnerSession) -> None:
        self._record(
            session,
            action_type="HypothesisRejected",
            result={"status": "rejected", "reason": "empty_hypothesis"},
        )

    def _record(
        self,
        session: LearnerSession,
        *,
        action_type: TraceActionType,
        result: dict[str, Any],
        evidence_id: str | None = None,
    ) -> None:
        event = TraceEvent(
            timestamp=normalize_utc_timestamp(self._clock()),
            stage=session.current_stage,
            action_type=action_type,
            evidence_id=evidence_id,
            current_hypothesis=session.current_hypothesis,
            tutor_hint=None,
            result=deepcopy(result),
        )
        session.trace.append(event.model_copy(deep=True))
