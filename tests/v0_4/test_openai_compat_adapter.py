from __future__ import annotations

import json
import unittest

import httpx

from apps.training_api.learning_models import TutorResponse
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.context import TutorContextProjector
from apps.training_api.tutor.policy import TutorPolicy
from apps.training_api.tutor.ports import TutorProviderError
from apps.training_api.tutor.providers.openai_compat import OpenAICompatChatAdapter
from apps.training_api.tutor.settings import LLMProviderSettings


def completed_response(tutor: TutorResponse) -> dict:
    return {
        "choices": [{
            "finish_reason": "stop",
            "message": {"content": tutor.model_dump_json()},
        }],
    }


class OpenAICompatChatAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        sessions = SessionService()
        view = sessions.create("ST-001")
        self.request = TutorContextProjector().project(view, (), "请提示下一步")
        self.decision = TutorPolicy().decide(self.request)
        self.settings = LLMProviderSettings(
            enabled=True,
            api_key="test-qwen-key",
            base_url="https://dashscope.test/compatible-mode/v1",
            model="qwen-plus",
            timeout_seconds=1,
            max_retries=1,
            provider="qwen",
            api_style="chat_completions",
        )
        self.tutor_response = TutorResponse(
            contract_version="0.4.0",
            intent=self.decision.intent,
            message="请先查看一项公开证据，并说明它能排查什么。",
            hint_level=self.decision.hint_level,
            suggested_action=self.decision.suggested_action,
        )

    async def test_sends_chat_completions_json_schema_and_parses_output(self) -> None:
        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            captured["body"] = json.loads((await request.aread()).decode())
            return httpx.Response(200, json=completed_response(self.tutor_response))

        result = await OpenAICompatChatAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        ).generate(self.request, self.decision)

        self.assertEqual(self.tutor_response, result.response)
        self.assertEqual(1, result.attempts)
        self.assertEqual(
            "https://dashscope.test/compatible-mode/v1/chat/completions",
            captured["url"],
        )
        self.assertEqual("Bearer test-qwen-key", captured["authorization"])
        self.assertEqual("qwen-plus", captured["body"]["model"])
        self.assertEqual(
            "json_schema",
            captured["body"]["response_format"]["type"],
        )
        serialized = json.dumps(captured["body"], ensure_ascii=False)
        for private_field in ("ground_truth", "optimal_path", "scoring_rules"):
            self.assertNotIn(private_field, serialized)

    async def test_retries_transient_status_and_reports_attempts(self) -> None:
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503, json={"error": "busy"})
            return httpx.Response(200, json=completed_response(self.tutor_response))

        result = await OpenAICompatChatAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        ).generate(self.request, self.decision)

        self.assertEqual(2, attempts)
        self.assertEqual(2, result.attempts)

    async def test_auth_error_is_not_retried(self) -> None:
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(401, json={"error": "unauthorized"})

        adapter = OpenAICompatChatAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        )
        with self.assertRaises(TutorProviderError) as raised:
            await adapter.generate(self.request, self.decision)

        self.assertEqual("qwen_http_401", raised.exception.code)
        self.assertEqual(1, raised.exception.attempts)
        self.assertEqual(1, attempts)

    async def test_incomplete_or_invalid_contract_response_is_rejected(self) -> None:
        responses = (
            (
                {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
                "qwen_incomplete_response",
            ),
            (completed_response(TutorResponse.model_construct()), "qwen_invalid_tutor_contract"),
        )
        for response, code in responses:
            with self.subTest(code=code):
                adapter = OpenAICompatChatAdapter(
                    self.settings,
                    transport=httpx.MockTransport(
                        lambda request, body=response: httpx.Response(200, json=body)
                    ),
                    retry_delay_seconds=0,
                )
                with self.assertRaises(TutorProviderError) as raised:
                    await adapter.generate(self.request, self.decision)
                self.assertEqual(code, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
