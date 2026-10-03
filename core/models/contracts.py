"""Pydantic representations of the frozen Phase 1 JSON contracts.

The JSON Schema files in ``contracts/schemas`` remain authoritative. These
models provide runtime validation for the Phase 2 Training Core and must stay
parity-tested against those schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FrozenStrictModel(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FaultType(StrEnum):
    OBJECT_POSE_OFFSET = "object_pose_offset"
    GRASP_FAILURE = "grasp_failure"
    OBSTACLE_COLLISION_RISK = "obstacle_collision_risk"
    PLACEMENT_TARGET_CONFLICT = "placement_target_conflict"


class DiagnosticStage(StrEnum):
    START = "START"
    OBSERVE = "OBSERVE"
    INVESTIGATE = "INVESTIGATE"
    HYPOTHESIZE = "HYPOTHESIZE"
    TEST = "TEST"
    UPDATE = "UPDATE"
    DIAGNOSE = "DIAGNOSE"
    REFLECT = "REFLECT"
    FINISH = "FINISH"


class SkillDimension(StrEnum):
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    EFFICIENCY = "efficiency"
    UPDATING = "updating"
    SAFETY = "safety"


class SkillScores(StrictModel):
    hypothesis: float = Field(ge=0, le=100)
    evidence: float = Field(ge=0, le=100)
    efficiency: float = Field(ge=0, le=100)
    updating: float = Field(ge=0, le=100)
    safety: float = Field(ge=0, le=100)

    @classmethod
    def zero(cls) -> "SkillScores":
        return cls(hypothesis=0, evidence=0, efficiency=0, updating=0, safety=0)


class Device(FrozenStrictModel):
    device_id: str = Field(min_length=1)
    device_type: Literal["industrial_robot"]
    scenario: Literal["flexible_handling"]
    display_name: str = Field(min_length=1)
    components: tuple[
        Literal["robot_arm", "gripper", "workpiece", "target_area", "obstacle"], ...
    ]

    @field_validator("components")
    @classmethod
    def validate_components(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != 5 or len(set(value)) != 5:
            raise ValueError("components must contain each of the five V0 components once")
        return value


class ContentSection(FrozenStrictModel):
    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class TrainingModule(FrozenStrictModel):
    module_id: str = Field(min_length=1)
    module_type: Literal["basic_operation", "exception_handling"]
    title: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    content_sections: tuple[ContentSection, ...]
    case_ids: tuple[str, ...]

    @field_validator("case_ids")
    @classmethod
    def validate_unique_case_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("case_ids must be unique")
        return value

    @field_validator("content_sections")
    @classmethod
    def validate_unique_section_ids(
        cls, value: tuple[ContentSection, ...]
    ) -> tuple[ContentSection, ...]:
        ids = [item.section_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("content section ids must be unique")
        return value


class Task(FrozenStrictModel):
    type: Literal["pick_and_place"]


class Fault(FrozenStrictModel):
    type: FaultType
    parameters: dict[str, Any]


class ServerEvidence(FrozenStrictModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    content: dict[str, Any]
    information_value: float
    related_faults: tuple[FaultType, ...]

    @field_validator("related_faults")
    @classmethod
    def validate_unique_related_faults(
        cls, value: tuple[FaultType, ...]
    ) -> tuple[FaultType, ...]:
        if len(value) != len(set(value)):
            raise ValueError("related_faults must be unique")
        return value


class GroundTruth(FrozenStrictModel):
    diagnosis: str = Field(min_length=1)


class ScoringCondition(FrozenStrictModel):
    field: str = Field(min_length=1)
    operator: Literal[
        "equals", "not_equals", "contains", "in", "exists", "gt", "gte", "lt", "lte"
    ]
    value: Any


class ScoringRule(FrozenStrictModel):
    rule_id: str = Field(min_length=1)
    dimension: SkillDimension
    event_type: str = Field(min_length=1)
    condition: ScoringCondition
    score_delta: float
    explanation: str = Field(min_length=1)


class ScoringRules(FrozenStrictModel):
    version: str = Field(min_length=1)
    rules: tuple[ScoringRule, ...]


class TrainingCase(FrozenStrictModel):
    case_id: str = Field(pattern=r"^ST-[0-9]{3}$")
    device_type: Literal["industrial_robot"]
    scenario: Literal["flexible_handling"]
    difficulty: int = Field(ge=1)
    task: Task
    fault: Fault
    initial_state: dict[str, Any]
    initial_observation: tuple[str, ...]
    evidence: tuple[ServerEvidence, ...]
    ground_truth: GroundTruth
    optimal_path: tuple[str, ...]
    safety_rules: tuple[str, ...]
    scoring_rules: ScoringRules

    @model_validator(mode="after")
    def validate_unique_nested_ids(self) -> "TrainingCase":
        evidence_ids = [item.id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence ids must be unique within a Case")
        rule_ids = [item.rule_id for item in self.scoring_rules.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("scoring rule ids must be unique within a Case")
        return self


class EvidenceOption(FrozenStrictModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)


class CasePublicState(FrozenStrictModel):
    case_id: str = Field(pattern=r"^ST-[0-9]{3}$")
    device_type: Literal["industrial_robot"]
    scenario: Literal["flexible_handling"]
    difficulty: int = Field(ge=1)
    task: Task
    initial_observation: tuple[str, ...]
    evidence_options: tuple[EvidenceOption, ...]
    safety_rules: tuple[str, ...]

    @field_validator("evidence_options")
    @classmethod
    def validate_unique_evidence_option_ids(
        cls, value: tuple[EvidenceOption, ...]
    ) -> tuple[EvidenceOption, ...]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence option ids must be unique")
        return value


class ReleasedEvidence(FrozenStrictModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    content: dict[str, Any]


class LearnerAction(FrozenStrictModel):
    action_type: str = Field(min_length=1)
    parameters: dict[str, Any]


class TraceEvent(StrictModel):
    timestamp: datetime
    stage: DiagnosticStage
    action_type: str = Field(min_length=1)
    evidence_id: str | None
    current_hypothesis: str | None
    tutor_hint: str | None
    result: Any


class LearnerSession(StrictModel):
    session_id: str = Field(min_length=1)
    case_id: str = Field(pattern=r"^ST-[0-9]{3}$")
    user_id: str = Field(min_length=1)
    current_stage: DiagnosticStage
    evidence_seen: list[str]
    current_hypothesis: str | None
    hypothesis_history: list[str]
    actions: list[LearnerAction]
    hint_count: int = Field(ge=0)
    wrong_branch_count: int = Field(ge=0)
    skill_scores: SkillScores
    trace: list[TraceEvent]

    @field_validator("evidence_seen")
    @classmethod
    def validate_unique_evidence_seen(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_seen must be unique")
        return value


class ModuleProgress(FrozenStrictModel):
    module_id: str = Field(min_length=1)
    completed_case_ids: tuple[str, ...]
    total_case_count: int = Field(ge=0)

    @field_validator("completed_case_ids")
    @classmethod
    def validate_unique_completed_cases(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("completed_case_ids must be unique")
        return value

    @model_validator(mode="after")
    def validate_completed_count(self) -> "ModuleProgress":
        if len(self.completed_case_ids) > self.total_case_count:
            raise ValueError("completed cases cannot exceed total_case_count")
        return self


class LearnerProfile(FrozenStrictModel):
    user_id: str = Field(min_length=1)
    module_progress: tuple[ModuleProgress, ...]
    skill_scores: SkillScores
    recommended_case_id: str | None = Field(default=None, pattern=r"^ST-[0-9]{3}$")

    @field_validator("module_progress")
    @classmethod
    def validate_unique_module_progress(
        cls, value: tuple[ModuleProgress, ...]
    ) -> tuple[ModuleProgress, ...]:
        ids = [item.module_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("module progress entries must have unique module ids")
        return value
