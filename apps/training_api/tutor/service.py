"""Tutor orchestration: safe context, policy, provider, validation, fallback."""

from __future__ import annotations

import logging

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
from .validation import UnsafeTutorResponseError, validate_tutor_response

logger = logging.getLogger(__name__)


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
    ) -> None:
        self._sessions = sessions
        self._provider = provider
        self._conversations = conversations or TutorConversationStore()
        self._projector = projector or TutorContextProjector()
        self._policy = policy or TutorPolicy()
        self._fallback = fallback or RuleTutor()

    async def ask(self, session_id: str, learner_message: str) -> TutorTurnResponse:
        session = self._sessions.get(session_id)
        history = self._conversations.history(session_id)
        request = self._projector.project(session, history, learner_message)
        decision = self._policy.decide(request)

        mode = TutorMode.RULE_FALLBACK
        response: TutorResponse
        if self._provider is None:
            response = self._fallback.generate(request, decision)
        else:
            try:
                candidate = await self._provider.generate(request, decision)
                response = validate_tutor_response(request, decision, candidate)
                mode = TutorMode.LLM
            except (TutorProviderError, UnsafeTutorResponseError) as exc:
                logger.warning(
                    "Tutor provider fell back to rules: %s", type(exc).__name__
                )
                response = self._fallback.generate(request, decision)

        self._conversations.append_turn(session_id, learner_message, response)
        return TutorTurnResponse(
            tutor=response,
            session=self._sessions.get(session_id),
            tutor_mode=mode,
        )


def build_tutor_service(
    sessions: SessionService,
    settings: DeepSeekSettings | None = None,
) -> TutorService:
    resolved = settings or DeepSeekSettings.from_env()
    provider: TutorProvider | None = None
    if resolved.configured:
        provider = DeepSeekResponsesAdapter(resolved)
    return TutorService(sessions, provider=provider)
