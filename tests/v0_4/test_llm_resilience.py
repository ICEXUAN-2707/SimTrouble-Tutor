from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from apps.training_api.learning_models import TutorResponse
from apps.training_api.main import create_app
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.context import TutorContextProjector
from apps.training_api.tutor.guard import TutorOutputGuard
from apps.training_api.tutor.policy import TutorPolicy, TutorPolicyDecision
from apps.training_api.tutor.ports import TutorGeneration
from apps.training_api.tutor.service import TutorService
from apps.training_api.tutor.validation import UnsafeTutorResponseError


class FixedProvider:
    async def generate(self, request, decision: TutorPolicyDecision) -> TutorGeneration:
        return TutorGeneration(response=TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message="请先检查一项公开证据。",
            hint_level=decision.hint_level,
            suggested_action=decision.suggested_action,
        ))


class BrokenGuard:
    def validate(self, request, response):
        raise RuntimeError("private implementation details must not escape")


class LLMResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_environment_does_not_block_health_or_rule_tutor(self) -> None:
        invalid_environment = {
            "SIMTROUBLE_LLM_ENABLED": "true",
            "SIMTROUBLE_LLM_PROVIDER": "qwen",
            "SIMTROUBLE_LLM_TIMEOUT_SECONDS": "invalid",
            "DASHSCOPE_API_KEY": "must-not-be-used",
        }
        with patch.dict(os.environ, invalid_environment, clear=False):
            app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            health = await client.get("/healthz")
            created = await client.post(
                "/api/v0.4/sessions",
                json={"case_id": "ST-001"},
            )
            session_id = created.json()["session_id"]
            tutor = await client.post(
                f"/api/v0.4/sessions/{session_id}/tutor",
                json={"message": "请提示下一步"},
            )

        self.assertEqual(200, health.status_code)
        self.assertEqual(201, created.status_code)
        self.assertEqual(200, tutor.status_code)
        self.assertEqual("rule_fallback", tutor.json()["tutor_mode"])

    async def test_guard_internal_error_fails_closed_with_safe_reason(self) -> None:
        sessions = SessionService()
        view = sessions.create("ST-001")
        service = TutorService(
            sessions,
            provider=FixedProvider(),
            guard=BrokenGuard(),
        )

        result = await service.ask(view.session_id, "请提示下一步")

        self.assertEqual("rule_fallback", result.tutor_mode)
        metric = service.metrics.snapshot(view.session_id)[0]
        self.assertEqual("guard_internal_error", metric.fallback_reason)

    def test_guard_blocks_authoritative_internal_fault_id(self) -> None:
        sessions = SessionService()
        view = sessions.create("ST-001")
        request = TutorContextProjector().project(view, (), "请提示下一步")
        decision = TutorPolicy().decide(request)
        response = TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message="内部故障类型是 object_pose_offset。",
            hint_level=decision.hint_level,
            suggested_action=decision.suggested_action,
        )

        with self.assertRaises(UnsafeTutorResponseError) as raised:
            TutorOutputGuard.from_default_cases().validate(request, response)

        self.assertEqual("hidden_answer_detected", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
