"""Tutor orchestration: safe context, policy, provider, validation, fallback."""

from __future__ import annotations

import asyncio
import logging
import re
from threading import RLock
from time import perf_counter
from typing import Callable

from ..learning_models import TutorMode, TutorResponse
from ..session_models import TutorTurnResponse
from ..session_service import SessionService
from .context import TutorContextProjector
from .conversation import TutorConversationStore
from .deepseek import DeepSeekResponsesAdapter
from .fallback import RuleTutor
from .policy import TutorPolicy
from .ports import TutorProvider, TutorProviderError
from .settings import DeepSeekSettings
from .telemetry import TutorMetricEvent, TutorMetrics
from .validation import UnsafeTutorResponseError, validate_tutor_response

logger = logging.getLogger(__name__)
_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class TutorService:
    def __init__(
        self,
        sessions: SessionService,
        *,
        provider: TutorProvider | None = None,
        conversations: TutorConversationStore | None = None,
        projector: TutorContextProjector | None = None,
        policy: TutorPolicy | None = None,
        fallback: RuleTutor | None = None,
        metrics: TutorMetrics | None = None,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._sessions = sessions
        self._provider = provider
        self._conversations = conversations or TutorConversationStore()
        self._projector = projector or TutorContextProjector()
        self._policy = policy or TutorPolicy()
        self._fallback = fallback or RuleTutor()
        self.metrics = metrics or TutorMetrics()
        self._clock = clock
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._session_locks_guard = RLock()

    async def ask(self, session_id: str, learner_message: str) -> TutorTurnResponse:
        # Validate before allocating a long-lived per-Session lock. Sessions are
        # process-local and currently have no deletion path.
        self._sessions.get(session_id)
        async with self._lock_for(session_id):
            return await self._ask_serialized(session_id, learner_message)

    async def _ask_serialized(
        self,
        session_id: str,
        learner_message: str,
    ) -> TutorTurnResponse:
        session = self._sessions.get(session_id)
        history = self._conversations.history(session_id)
        request = self._projector.project(session, history, learner_message)
        decision = self._policy.decide(request)
        self._sessions.record_tutor_requested(
            session_id,
            policy_rule_id=decision.rule_id,
            hint_level=decision.hint_level,
            suggested_action=(
                decision.suggested_action.value if decision.suggested_action else None
            ),
        )
        started = self._clock()

        mode = TutorMode.RULE_FALLBACK
        retry_count = 0
        fallback_reason: str | None = "llm_disabled"
        response: TutorResponse
        if self._provider is None:
            response = self._fallback.generate(request, decision)
        else:
            try:
                generation = await self._provider.generate(request, decision)
                retry_count = generation.attempts - 1
                response = validate_tutor_response(
                    request,
                    decision,
                    generation.response,
                )
                mode = TutorMode.LLM
                fallback_reason = None
            except (TutorProviderError, UnsafeTutorResponseError) as exc:
                fallback_reason = (
                    exc.code if _SAFE_REASON.fullmatch(exc.code) else "provider_error"
                )
                if isinstance(exc, TutorProviderError):
                    retry_count = max(0, exc.attempts - 1)
                logger.warning(
                    "Tutor provider fell back to rules: %s",
                    fallback_reason,
                )
                response = self._fallback.generate(request, decision)

        latency_ms = max(0, round((self._clock() - started) * 1_000))
        if mode is TutorMode.LLM:
            self._sessions.record_tutor_delivered(
                session_id,
                latency_ms=latency_ms,
                retry_count=retry_count,
            )
        else:
            assert fallback_reason is not None
            self._sessions.record_tutor_fallback(
                session_id,
                latency_ms=latency_ms,
                retry_count=retry_count,
                reason=fallback_reason,
            )
        self.metrics.record(TutorMetricEvent(
            session_id=session_id,
            mode=mode,
            latency_ms=latency_ms,
            retry_count=retry_count,
            fallback_reason=fallback_reason,
        ))
        self._conversations.append_turn(session_id, learner_message, response)
        return TutorTurnResponse(
            tutor=response,
            session=self._sessions.get(session_id),
            tutor_mode=mode,
        )

    def _lock_for(self, session_id: str) -> asyncio.Lock:
        with self._session_locks_guard:
            return self._session_locks.setdefault(session_id, asyncio.Lock())


def build_tutor_service(
    sessions: SessionService,
    settings: DeepSeekSettings | None = None,
) -> TutorService:
    resolved = settings or DeepSeekSettings.from_env()
    provider: TutorProvider | None = None
    if resolved.configured:
        provider = DeepSeekResponsesAdapter(resolved)
    return TutorService(sessions, provider=provider)
