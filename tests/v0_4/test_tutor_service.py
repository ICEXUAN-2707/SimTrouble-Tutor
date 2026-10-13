from __future__ import annotations

import unittest

from apps.training_api.learning_models import (
    TutorAction,
    TutorRequest,
    TutorResponse,
)
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.policy import TutorPolicyDecision
from apps.training_api.tutor.ports import TutorProviderError
from apps.training_api.tutor.service import TutorService


class CapturingProvider:
    def __init__(
        self,
        *,
        invalid_action: bool = False,
        fail: bool = False,
        message: str = "Please inspect one public evidence item.",
    ) -> None:
        self.requests: list[TutorRequest] = []
        self.invalid_action = invalid_action
        self.fail = fail
        self.message = message

    async def generate(
        self,
        request: TutorRequest,
        decision: TutorPolicyDecision,
    ) -> TutorResponse:
        self.requests.append(request)
        if self.fail:
            raise TutorProviderError("provider_unavailable", retryable=True)
        action = (
            TutorAction.SUBMIT_DIAGNOSIS
            if self.invalid_action
            else decision.suggested_action
        )
        return TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message=self.message,
            hint_level=decision.hint_level,
            suggested_action=action,
        )


class TutorServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_provider_uses_deterministic_fallback(self) -> None:
        sessions = SessionService()
        view = sessions.create("ST-001")
        result = await TutorService(sessions).ask(view.session_id, "Help me")

        self.assertEqual("rule_fallback", result.tutor_mode)
        self.assertEqual(TutorAction.INSPECT_EVIDENCE, result.tutor.suggested_action)
        self.assertEqual(view.session_id, result.session.session_id)

    async def test_valid_provider_output_is_used_and_history_is_session_scoped(self) -> None:
        sessions = SessionService()
        first = sessions.create("ST-001")
        second = sessions.create("ST-001")
        provider = CapturingProvider()
        service = TutorService(sessions, provider=provider)

        first_result = await service.ask(first.session_id, "First question")
        await service.ask(first.session_id, "Second question")
        await service.ask(second.session_id, "Another learner")

        self.assertEqual("llm", first_result.tutor_mode)
        self.assertEqual(1, len(provider.requests[0].messages))
        self.assertEqual(3, len(provider.requests[1].messages))
        self.assertEqual(1, len(provider.requests[2].messages))
        for request in provider.requests:
            payload = request.model_dump_json()
            for forbidden in (
                "ground_truth",
                "optimal_path",
                "scoring_rules",
                "information_value",
                "related_faults",
            ):
                self.assertNotIn(forbidden, payload)

    async def test_invalid_or_failed_provider_falls_back(self) -> None:
        for provider in (
            CapturingProvider(invalid_action=True),
            CapturingProvider(fail=True),
            CapturingProvider(message="The ground_truth field says the answer."),
        ):
            with self.subTest(provider=provider):
                sessions = SessionService()
                view = sessions.create("ST-001")
                result = await TutorService(
                    sessions, provider=provider
                ).ask(view.session_id, "Help")
                self.assertEqual("rule_fallback", result.tutor_mode)
                self.assertEqual(
                    TutorAction.INSPECT_EVIDENCE,
                    result.tutor.suggested_action,
                )


if __name__ == "__main__":
    unittest.main()
