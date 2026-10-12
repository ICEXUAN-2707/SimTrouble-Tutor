"""Runtime models for the Tutor Contract.

These models mirror ``contracts/schemas/tutor-context.schema.json`` and
``contracts/schemas/tutor-response.schema.json``. They are an optional add-on
surface for the LLM expression layer and must not change the frozen schemas.

Boundary reminders (ADR-007 / ADR-008 / ADR-014):

- ``TutorContext`` is a public projection; hidden Case fields are structurally
  absent, not merely omitted at serialization time;
- ``TutorResponse`` is the only permitted Tutor output;
- ``TutorReply`` is an internal envelope that records whether the message came
  from the online LLM or from the deterministic fallback template.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.models import (
    CasePublicState,
    LearnerAction,
    ReleasedEvidence,
    SkillScores,
    TrainingModule,
)


class TutorIntent(StrEnum):
    QUESTION = "question"
    HINT = "hint"
    EXPLAIN = "explain"
    REFLECT = "reflect"


class TutorResponse(BaseModel):
    """The only permitted Tutor output.

    Strict mode is intentionally off: real payloads arrive as JSON primitives
    and must still be coerced into ``TutorIntent`` before validation.
    """

    model_config = ConfigDict(extra="forbid")

    intent: TutorIntent
    message: str = Field(min_length=1)
    suggested_next_step: str | None = None


class TutorContext(BaseModel):
    """The only permitted Tutor input."""

    model_config = ConfigDict(extra="forbid")

    training_module: TrainingModule
    case_public_state: CasePublicState
    evidence_seen: list[ReleasedEvidence] = Field(default_factory=list)
    learner_action_history: list[LearnerAction] = Field(default_factory=list)
    current_hypothesis: str | None = None
    current_skill_profile: SkillScores
    allowed_tutor_actions: list[TutorIntent]

    @field_validator("allowed_tutor_actions")
    @classmethod
    def validate_allowed_actions(cls, value: list[TutorIntent]) -> list[TutorIntent]:
        if not value:
            raise ValueError("allowed_tutor_actions must not be empty")
        if len(set(value)) != len(value):
            raise ValueError("allowed_tutor_actions must be unique")
        return value

    def forbidden_keys_present(self) -> list[str]:
        """Defensive self-check that hidden Case fields never enter the projection."""

        hidden = ("ground_truth", "optimal_path", "scoring_rules", "fault", "initial_state")
        dumped = self.model_dump(mode="json")
        return [key for key in hidden if key in dumped]


class TutorReply(BaseModel):
    """Internal envelope pairing a validated response with its provenance."""

    model_config = ConfigDict(extra="forbid")

    response: TutorResponse
    source: Literal["llm", "template"]
    fallback_reason: str | None = None
