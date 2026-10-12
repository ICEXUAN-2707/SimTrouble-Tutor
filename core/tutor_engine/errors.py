"""Errors for the optional Tutor LLM layer."""

from __future__ import annotations

from core.errors import TrainingCoreError


class TutorEngineError(TrainingCoreError):
    """Base class for Tutor expression-layer failures."""


class LLMUnavailableError(TutorEngineError):
    """Raised when the online LLM cannot be reached or returns an unusable shape."""


class LLMOutputRejectedError(TutorEngineError):
    """Raised when LLM output fails contract, intent, length or leakage checks."""
