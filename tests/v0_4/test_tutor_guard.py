from __future__ import annotations

import unittest

from apps.training_api.learning_models import TutorResponse
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.context import TutorContextProjector
from apps.training_api.tutor.guard import TutorOutputGuard
from apps.training_api.tutor.policy import TutorPolicy, TutorPolicyDecision
from apps.training_api.tutor.ports import TutorGeneration
from apps.training_api.tutor.service import TutorService
from apps.training_api.tutor.validation import UnsafeTutorResponseError


class FixedProvider:
    def __init__(self, message: str) -> None:
        self.message = message

    async def generate(self, request, decision: TutorPolicyDecision) -> TutorGeneration:
        return TutorGeneration(response=TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message=self.message,
            hint_level=decision.hint_level,
            suggested_action=decision.suggested_action,
        ))


class TutorOutputGuardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.sessions = SessionService()
        self.view = self.sessions.create("ST-001")
        self.guard = TutorOutputGuard.from_default_cases()
        self.projector = TutorContextProjector()
        self.policy = TutorPolicy()

    def response_for(self, request, message: str) -> TutorResponse:
        decision = self.policy.decide(request)
        return TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message=message,
            hint_level=decision.hint_level,
            suggested_action=decision.suggested_action,
        )

    def test_blocks_case_alias_and_private_optimal_path(self) -> None:
        request = self.projector.project(self.view, (), "请给我一点提示")
        cases = (
            ("可以判断为工件位置不匹配。", "hidden_answer_detected"),
            ("下一步执行 compare_poses。", "private_path_detected"),
        )
        for message, expected_code in cases:
            with self.subTest(message=message):
                with self.assertRaises(UnsafeTutorResponseError) as raised:
                    self.guard.validate(request, self.response_for(request, message))
                self.assertEqual(expected_code, raised.exception.code)

    def test_blocks_unreleased_numeric_evidence(self) -> None:
        request = self.projector.project(self.view, (), "请给我一点提示")
        response = self.response_for(request, "测量结果可能是 70 mm，请据此判断。")

        with self.assertRaises(UnsafeTutorResponseError) as raised:
            self.guard.validate(request, response)

        self.assertEqual("unreleased_evidence_detected", raised.exception.code)

    def test_allows_fact_after_that_evidence_has_been_released(self) -> None:
        evidence = self.sessions.request_evidence(self.view.session_id, "E02")
        request = self.projector.project(evidence.session, (), "如何解释这项证据？")
        response = self.response_for(request, "已经公开的 70 mm 偏移值得进一步验证。")

        self.assertIs(response, self.guard.validate(request, response))

    def test_benign_scaffolding_is_allowed(self) -> None:
        request = self.projector.project(self.view, (), "请给我一点提示")
        response = self.response_for(request, "先选择一项证据，再说明它支持或排除了什么。")

        self.assertIs(response, self.guard.validate(request, response))

    async def test_service_falls_back_and_records_guard_reason(self) -> None:
        service = TutorService(
            self.sessions,
            provider=FixedProvider("可以判断为工件位置不匹配。"),
            guard=self.guard,
        )

        result = await service.ask(self.view.session_id, "请直接告诉我答案")

        self.assertEqual("rule_fallback", result.tutor_mode)
        metric = service.metrics.snapshot(self.view.session_id)[0]
        self.assertEqual("hidden_answer_detected", metric.fallback_reason)


if __name__ == "__main__":
    unittest.main()
