"""Provider-neutral port for learner-safe Tutor text generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..learning_models import TutorRequest, TutorResponse
from .policy import TutorPolicyDecision


class TutorProviderError(RuntimeError):
    """Raised when an external Tutor provider cannot return a valid response."""

    def __init__(
        self,
        code: str,
        *,
        retryable: bool = False,
        attempts: int = 1,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.attempts = attempts


@dataclass(frozen=True)
class TutorGeneration:
    response: TutorResponse
    attempts: int = 1

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be at least 1")


class TutorProvider(Protocol):
    async def generate(
        self,
        request: TutorRequest,
        decision: TutorPolicyDecision,
    ) -> TutorGeneration:
        """Generate wording for a decision already made by program policy."""
