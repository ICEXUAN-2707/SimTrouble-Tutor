"""Mutable learner Session isolated from an immutable authoritative Case."""

from __future__ import annotations

from uuid import uuid4

from core.models import (
    CasePublicState,
    EvidenceOption,
    LearnerAction,
    LearnerSession,
    SkillScores,
    TrainingCase,
)
from core.models.contracts import DiagnosticStage
from core.errors import InvalidStateTransitionError
from core.session_trace import Clock, SessionTraceRecorder
from core.state_machine import DiagnosticStateMachine


class CaseSession:
    def __init__(
        self,
        *,
        user_id: str,
        case: TrainingCase,
        session_id: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._case = case.model_copy(deep=True)
        self._state_machine = DiagnosticStateMachine()
        self._trace_recorder = SessionTraceRecorder(clock=clock)
        self._session = LearnerSession(
            session_id=str(uuid4()) if session_id is None else session_id,
            case_id=case.case_id,
            user_id=user_id,
            current_stage=DiagnosticStage.START,
            evidence_seen=[],
            current_hypothesis=None,
            hypothesis_history=[],
            actions=[],
            hint_count=0,
            wrong_branch_count=0,
            skill_scores=SkillScores.zero(),
            trace=[],
        )
        self._trace_recorder.record_session_started(self._session)

    @property
    def session(self) -> LearnerSession:
        """Return a snapshot that cannot mutate authoritative Session state."""

        return self._session.model_copy(deep=True)

    @property
    def authoritative_case(self) -> TrainingCase:
        """Internal service access only; never serialize this to learner/Tutor clients."""

        return self._case.model_copy(deep=True)

    def public_case_state(self) -> CasePublicState:
        return CasePublicState(
            case_id=self._case.case_id,
            device_type=self._case.device_type,
            scenario=self._case.scenario,
            difficulty=self._case.difficulty,
            task=self._case.task,
            initial_observation=self._case.initial_observation,
            evidence_options=tuple(
                EvidenceOption(id=item.id, type=item.type) for item in self._case.evidence
            ),
            safety_rules=self._case.safety_rules,
        )

    def record_action(self, action: LearnerAction) -> None:
        self._session.actions.append(action.model_copy(deep=True))

    def transition_to(self, target_stage: DiagnosticStage) -> None:
        """Apply an explicit transition through the Core state authority."""

        candidate = self._session.model_copy(deep=True)
        from_stage = candidate.current_stage
        try:
            self._state_machine.transition(candidate, target_stage)
        except InvalidStateTransitionError:
            self._trace_recorder.record_state_transition_rejected(
                candidate,
                requested_stage=target_stage,
            )
            self._session = candidate
            raise

        self._trace_recorder.record_state_transitioned(
            candidate,
            from_stage=from_stage,
        )
        if candidate.current_stage is DiagnosticStage.FINISH:
            self._trace_recorder.record_session_finished(candidate)
        self._session = candidate

    def submit_hypothesis(self, hypothesis: str) -> None:
        normalized = hypothesis.strip()
        if not normalized:
            raise ValueError("hypothesis must not be empty")
        self._session.current_hypothesis = normalized
        self._session.hypothesis_history.append(normalized)

    def _record_evidence_seen(self, evidence_id: str) -> None:
        """EvidenceManager-only mutation after authoritative Case validation."""

        if evidence_id not in self._session.evidence_seen:
            self._session.evidence_seen.append(evidence_id)
