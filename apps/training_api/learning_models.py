"""Versioned public contracts for the v0.4 tutoring and evaluation boundary.

These models intentionally keep Tutor input learner-safe and prevent the
Evaluator from returning an authoritative numeric score.  Program-controlled
scoring is represented only in the final learning report.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.models import CasePublicState, ReleasedEvidence
from core.models.contracts import SkillDimension


class FrozenContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TutorIntent(StrEnum):
    QUESTION = "question"
    HINT = "hint"
    EXPLAIN = "explain"
    REFLECT = "reflect"


class TutorAction(StrEnum):
    OBSERVE_SCENE = "observe_scene"
    INSPECT_EVIDENCE = "inspect_evidence"
    SUBMIT_HYPOTHESIS = "submit_hypothesis"
    REVISE_HYPOTHESIS = "revise_hypothesis"
    SUBMIT_DIAGNOSIS = "submit_diagnosis"
    REFLECT = "reflect"


class TutorMessage(FrozenContract):
    role: str = Field(pattern=r"^(learner|tutor)$")
    content: str = Field(min_length=1, max_length=2_000)


class TutorRequest(FrozenContract):
    contract_version: str = Field(pattern=r"^0\.4\.[0-9]+$")
    session_id: str = Field(min_length=1)
    case_public_state: CasePublicState
    released_evidence: tuple[ReleasedEvidence, ...]
    messages: tuple[TutorMessage, ...]
    hypotheses: tuple[str, ...]
    current_hypothesis: str | None
    allowed_actions: tuple[TutorAction, ...]

    @field_validator("allowed_actions")
    @classmethod
    def validate_unique_actions(
        cls, value: tuple[TutorAction, ...]
    ) -> tuple[TutorAction, ...]:
        if len(value) != len(set(value)):
            raise ValueError("allowed_actions must be unique")
        return value


class TutorResponse(FrozenContract):
    contract_version: str = Field(pattern=r"^0\.4\.[0-9]+$")
    intent: TutorIntent
    message: str = Field(min_length=1, max_length=2_000)
    hint_level: int = Field(ge=0, le=3)
    suggested_action: TutorAction | None


class DiagnosisType(StrEnum):
    OBJECT_POSE_MISMATCH = "object_pose_mismatch"
    GRASP_FAILURE = "grasp_failure"
    OBSTACLE_COLLISION_RISK = "obstacle_collision_risk"
    PLACEMENT_TARGET_CONFLICT = "placement_target_conflict"


class DiagnosisSubmission(FrozenContract):
    contract_version: str = Field(pattern=r"^0\.4\.[0-9]+$")
    diagnosis_type: DiagnosisType
    reasoning: str = Field(min_length=1, max_length=4_000)
    cited_evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("cited_evidence_ids")
    @classmethod
    def validate_unique_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("cited_evidence_ids must be unique")
        if any(not item.strip() for item in value):
            raise ValueError("cited_evidence_ids must not contain empty values")
        return value


class DiagnosisAssessment(StrEnum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    INSUFFICIENT = "insufficient"


class FindingQuality(StrEnum):
    STRONG = "strong"
    ADEQUATE = "adequate"
    WEAK = "weak"
    NOT_OBSERVED = "not_observed"


class EvaluationFinding(FrozenContract):
    code: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    message: str = Field(min_length=1, max_length=2_000)
    cited_evidence_ids: tuple[str, ...]
    trace_indices: tuple[int, ...]

    @field_validator("trace_indices")
    @classmethod
    def validate_trace_indices(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(index < 0 for index in value):
            raise ValueError("trace_indices must be non-negative")
        if len(value) != len(set(value)):
            raise ValueError("trace_indices must be unique")
        return value


class DimensionFinding(FrozenContract):
    dimension: SkillDimension
    quality: FindingQuality
    rationale: str = Field(min_length=1, max_length=2_000)
    trace_indices: tuple[int, ...]


class EvaluatorResponse(FrozenContract):
    contract_version: str = Field(pattern=r"^0\.4\.[0-9]+$")
    diagnosis_assessment: DiagnosisAssessment
    findings: tuple[EvaluationFinding, ...]
    dimension_findings: tuple[DimensionFinding, ...]
    feedback_summary: str = Field(min_length=1, max_length=4_000)
    next_learning_step: str = Field(min_length=1, max_length=2_000)

    @field_validator("dimension_findings")
    @classmethod
    def validate_unique_dimensions(
        cls, value: tuple[DimensionFinding, ...]
    ) -> tuple[DimensionFinding, ...]:
        dimensions = [item.dimension for item in value]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("dimension_findings must contain unique dimensions")
        return value


class ScoreStatus(StrEnum):
    SCORED = "scored"
    NOT_ASSESSED = "not_assessed"


class SkillDimensionResult(FrozenContract):
    status: ScoreStatus
    score: float | None = Field(default=None, ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=2_000)
    rule_ids: tuple[str, ...]
    trace_indices: tuple[int, ...]

    @model_validator(mode="after")
    def validate_assessment_state(self) -> "SkillDimensionResult":
        if self.status is ScoreStatus.SCORED and self.score is None:
            raise ValueError("scored dimensions require a score")
        if self.status is ScoreStatus.NOT_ASSESSED:
            if self.score is not None:
                raise ValueError("not_assessed dimensions require a null score")
            if self.weight != 0:
                raise ValueError("not_assessed dimensions require zero weight")
        return self


class DiagnosisReview(FrozenContract):
    submitted: DiagnosisSubmission
    assessment: DiagnosisAssessment
    reference_explanation: str = Field(min_length=1, max_length=4_000)


class OverallScore(FrozenContract):
    score: float | None = Field(default=None, ge=0, le=100)
    coverage: float = Field(ge=0, le=1)
    included_dimensions: tuple[SkillDimension, ...]

    @model_validator(mode="after")
    def validate_empty_coverage(self) -> "OverallScore":
        if not self.included_dimensions and self.score is not None:
            raise ValueError("overall score must be null when no dimensions are included")
        if self.included_dimensions and self.score is None:
            raise ValueError("overall score is required when dimensions are included")
        return self


class TutorMode(StrEnum):
    LLM = "llm"
    RULE_FALLBACK = "rule_fallback"


class TrainingReportV04(FrozenContract):
    contract_version: str = Field(pattern=r"^0\.4\.[0-9]+$")
    rubric_version: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    case_id: str = Field(pattern=r"^ST-[0-9]{3}$")
    diagnosis: DiagnosisReview
    evidence_used: tuple[str, ...]
    dimension_results: dict[SkillDimension, SkillDimensionResult]
    overall: OverallScore
    feedback_summary: str = Field(min_length=1, max_length=4_000)
    next_learning_step: str = Field(min_length=1, max_length=2_000)
    tutor_mode: TutorMode

    @model_validator(mode="after")
    def validate_dimension_coverage(self) -> "TrainingReportV04":
        if set(self.dimension_results) != set(SkillDimension):
            raise ValueError("dimension_results must contain all five skill dimensions")
        included = {
            dimension
            for dimension, result in self.dimension_results.items()
            if result.status is ScoreStatus.SCORED
        }
        if included != set(self.overall.included_dimensions):
            raise ValueError("overall included_dimensions must match scored dimensions")
        return self
