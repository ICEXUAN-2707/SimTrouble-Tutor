"""Optional Tutor expression layer with an online LLM port (ADR-008).

Public pieces:

- :class:`TutorService` — builds the public context projection, calls the
  optional LLM, validates output and falls back to the deterministic policy;
- :class:`OpenAICompatClient` — OpenAI-compatible Chat Completions client;
- :class:`ScriptedLLMClient` — deterministic client for tests;
- :class:`LeakGuard` — rejects output exposing hidden Case material;
- :class:`RuleTutorPolicy` — guaranteed template fallback.
"""

from __future__ import annotations

from core.tutor_engine.errors import (
    LLMOutputRejectedError,
    LLMUnavailableError,
    TutorEngineError,
)
from core.tutor_engine.leak_guard import LeakGuard
from core.tutor_engine.llm_client import (
    LLMClient,
    OpenAICompatClient,
    ScriptedLLMClient,
    http_transport,
)
from core.tutor_engine.models import (
    TutorContext,
    TutorIntent,
    TutorReply,
    TutorResponse,
)
from core.tutor_engine.policy import RuleTutorPolicy
from core.tutor_engine.tutor_service import TutorService

__all__ = [
    "LLMClient",
    "LLMOutputRejectedError",
    "LLMUnavailableError",
    "LeakGuard",
    "OpenAICompatClient",
    "RuleTutorPolicy",
    "ScriptedLLMClient",
    "TutorContext",
    "TutorEngineError",
    "TutorIntent",
    "TutorReply",
    "TutorResponse",
    "TutorService",
    "http_transport",
]
