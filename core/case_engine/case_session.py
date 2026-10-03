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


class CaseSession:
    def __init__(
        self,
        *,
        user_id: str,
        case: TrainingCase,
        session_id: str | None = None,
    ) -> None:
        self._case = case.model_copy(deep=True)
        self.session = LearnerSession(
            session_id=session_id or str(uuid4()),
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
        self.session.actions.append(action.model_copy(deep=True))

    def submit_hypothesis(self, hypothesis: str) -> None:
        normalized = hypothesis.strip()
        if not normalized:
            raise ValueError("hypothesis must not be empty")
        self.session.current_hypothesis = normalized
        self.session.hypothesis_history.append(normalized)
