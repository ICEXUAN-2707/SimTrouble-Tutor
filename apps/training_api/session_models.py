"""Learner-safe HTTP contracts for Product v0.4 Sessions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator

from core.models import CasePublicState, ReleasedEvidence

from .learning_models import FrozenContract, TutorAction, TutorMode, TutorResponse


class PublicSessionStage(StrEnum):
    READY = "READY"
    PLAYING = "PLAYING"
    INVESTIGATING = "INVESTIGATING"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"


class CreateSessionRequest(FrozenContract):
    case_id: str = Field(pattern=r"^ST-[0-9]{3}$")


class EvidenceRequest(FrozenContract):
    evidence_id: str = Field(min_length=1, max_length=100)

    @field_validator("evidence_id")
    @classmethod
    def normalize_evidence_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("evidence_id must not be empty")
        return normalized


class HypothesisRequest(FrozenContract):
    hypothesis: str = Field(min_length=1, max_length=2_000)

    @field_validator("hypothesis")
    @classmethod
    def normalize_hypothesis(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("hypothesis must not be empty")
        return normalized


class SessionView(FrozenContract):
    contract_version: str = Field(pattern=r"^0\.4\.[0-9]+$")
    session_id: str = Field(min_length=1)
    case_public_state: CasePublicState
    public_stage: PublicSessionStage
    released_evidence: tuple[ReleasedEvidence, ...]
    current_hypothesis: str | None
    hypotheses: tuple[str, ...]
    allowed_actions: tuple[TutorAction, ...]


class EvidenceResponse(FrozenContract):
    evidence: ReleasedEvidence
    session: SessionView


class TutorTurnRequest(FrozenContract):
    message: str = Field(min_length=1, max_length=2_000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message must not be empty")
        return normalized


class TutorTurnResponse(FrozenContract):
    tutor: TutorResponse
    session: SessionView
    tutor_mode: TutorMode
