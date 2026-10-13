"""Provider-neutral port for learner-safe Tutor text generation."""

from __future__ import annotations

from typing import Protocol

from ..learning_models import TutorRequest, TutorResponse
from .policy import TutorPolicyDecision


class TutorProviderError(RuntimeError):
    """Raised when an external Tutor provider cannot return a valid response."""

    def __init__(self, code: str, *, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class TutorProvider(Protocol):
    async def generate(
        self,
        request: TutorRequest,
        decision: TutorPolicyDecision,
    ) -> TutorResponse:
        """Generate wording for a decision already made by program policy."""
