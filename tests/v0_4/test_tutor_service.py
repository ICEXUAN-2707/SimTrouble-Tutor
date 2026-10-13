from __future__ import annotations

import unittest
import asyncio

from apps.training_api.learning_models import (
    TutorAction,
    TutorRequest,
    TutorResponse,
)
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.policy import TutorPolicyDecision
from apps.training_api.session_repository import SessionRepository
from apps.training_api.tutor.ports import TutorGeneration, TutorProviderError
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
    ) -> TutorGeneration:
        self.requests.append(request)
        if self.fail:
            raise TutorProviderError("provider_unavailable", retryable=True)
        action = (
            TutorAction.SUBMIT_DIAGNOSIS
            if self.invalid_action
            else decision.suggested_action
        )
        return TutorGeneration(
            response=TutorResponse(
                contract_version="0.4.0",
                intent=decision.intent,
                message=self.message,
                hint_level=decision.hint_level,
                suggested_action=action,
            ),
        )


class ConcurrentProvider(CapturingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.active = 0
        self.max_active = 0

    async def generate(
        self,
        request: TutorRequest,
        decision: TutorPolicyDecision,
    ) -> TutorGeneration:
        self.requests.append(request)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return TutorGeneration(response=TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message=self.message,
            hint_level=decision.hint_level,
            suggested_action=decision.suggested_action,
        ))


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
            CapturingProvider(message="The correct diagnosis is grasp failure."),
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

    async def test_same_session_calls_are_serialized_and_keep_history_order(self) -> None:
        sessions = SessionService()
        view = sessions.create("ST-001")
        provider = ConcurrentProvider()
        service = TutorService(sessions, provider=provider)

        await asyncio.gather(
            service.ask(view.session_id, "First"),
            service.ask(view.session_id, "Second"),
        )

        self.assertEqual(1, provider.max_active)
        self.assertEqual(1, len(provider.requests[0].messages))
        self.assertEqual(3, len(provider.requests[1].messages))

    async def test_trace_and_metrics_are_public_safe(self) -> None:
        repository = SessionRepository()
        sessions = SessionService(repository=repository)
        view = sessions.create("ST-001")
        service = TutorService(
            sessions,
            provider=CapturingProvider(fail=True),
            clock=iter((10.0, 10.125)).__next__,
        )

        await service.ask(view.session_id, "Do not store this learner prompt")

        trace = repository.inspect(view.session_id, lambda item: item.session.trace)
        self.assertEqual(
            ["TutorRequested", "TutorFallback"],
            [event.action_type for event in trace[-2:]],
        )
        self.assertEqual(125, trace[-1].result["latency_ms"])
        self.assertEqual("provider_unavailable", trace[-1].result["reason"])
        serialized = str([event.model_dump(mode="json") for event in trace[-2:]])
        self.assertNotIn("Do not store this learner prompt", serialized)
        metric = service.metrics.snapshot(view.session_id)[0]
        self.assertEqual(125, metric.latency_ms)
        self.assertEqual("provider_unavailable", metric.fallback_reason)


if __name__ == "__main__":
    unittest.main()
