from __future__ import annotations

import json
import unittest

import httpx

from apps.training_api.learning_models import TutorResponse
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.context import TutorContextProjector
from apps.training_api.tutor.deepseek import DeepSeekResponsesAdapter
from apps.training_api.tutor.policy import TutorPolicy
from apps.training_api.tutor.ports import TutorProviderError
from apps.training_api.tutor.settings import DeepSeekSettings


def completed_response(tutor: TutorResponse) -> dict:
    return {
        "status": "completed",
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": tutor.model_dump_json(),
            }],
        }],
    }


class DeepSeekAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        sessions = SessionService()
        view = sessions.create("ST-001")
        self.request = TutorContextProjector().project(view, (), "Help me")
        self.decision = TutorPolicy().decide(self.request)
        self.settings = DeepSeekSettings(
            enabled=True,
            api_key="test-key",
            base_url="https://deepseek.test",
            model="deepseek-flash",
            timeout_seconds=1,
            max_retries=1,
        )
        self.tutor_response = TutorResponse(
            contract_version="0.4.0",
            intent=self.decision.intent,
            message="Inspect one evidence item and explain what it can test.",
            hint_level=self.decision.hint_level,
            suggested_action=self.decision.suggested_action,
        )

    async def test_sends_structured_responses_request_and_parses_output(self) -> None:
        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            captured["body"] = json.loads((await request.aread()).decode())
            return httpx.Response(200, json=completed_response(self.tutor_response))

        adapter = DeepSeekResponsesAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        )
        result = await adapter.generate(self.request, self.decision)

        self.assertEqual(self.tutor_response, result.response)
        self.assertEqual(1, result.attempts)
        self.assertEqual("https://deepseek.test/responses", captured["url"])
        self.assertEqual("Bearer test-key", captured["authorization"])
        self.assertEqual("deepseek-flash", captured["body"]["model"])
        self.assertEqual(
            "json_schema",
            captured["body"]["text"]["format"]["type"],
        )
        self.assertEqual("none", captured["body"]["reasoning"]["effort"])
        serialized = json.dumps(captured["body"])
        self.assertNotIn("ground_truth", serialized)
        self.assertNotIn("optimal_path", serialized)

    async def test_retries_transient_status_once(self) -> None:
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503, json={"error": "busy"})
            return httpx.Response(200, json=completed_response(self.tutor_response))

        adapter = DeepSeekResponsesAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        )
        result = await adapter.generate(self.request, self.decision)
        self.assertEqual(2, attempts)
        self.assertEqual(2, result.attempts)

    async def test_auth_error_is_not_retried(self) -> None:
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(401, json={"error": "unauthorized"})

        adapter = DeepSeekResponsesAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        )
        with self.assertRaisesRegex(TutorProviderError, "deepseek_http_401"):
            await adapter.generate(self.request, self.decision)
        self.assertEqual(1, attempts)

    async def test_timeout_retries_once_and_reports_attempt_count(self) -> None:
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            raise httpx.ReadTimeout("timed out", request=request)

        adapter = DeepSeekResponsesAdapter(
            self.settings,
            transport=httpx.MockTransport(handler),
            retry_delay_seconds=0,
        )
        with self.assertRaises(TutorProviderError) as raised:
            await adapter.generate(self.request, self.decision)
        self.assertEqual("deepseek_transport_error", raised.exception.code)
        self.assertEqual(2, raised.exception.attempts)
        self.assertEqual(2, attempts)

    async def test_invalid_contract_is_rejected(self) -> None:
        response = {
            "status": "completed",
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "{}"}],
            }],
        }
        adapter = DeepSeekResponsesAdapter(
            self.settings,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=response)
            ),
            retry_delay_seconds=0,
        )
        with self.assertRaisesRegex(
            TutorProviderError, "deepseek_invalid_tutor_contract"
        ):
            await adapter.generate(self.request, self.decision)

    async def test_non_object_provider_response_is_rejected(self) -> None:
        adapter = DeepSeekResponsesAdapter(
            self.settings,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=[])
            ),
            retry_delay_seconds=0,
        )
        with self.assertRaisesRegex(
            TutorProviderError, "deepseek_invalid_response_shape"
        ):
            await adapter.generate(self.request, self.decision)


class DeepSeekSettingsTests(unittest.TestCase):
    def test_defaults_to_disabled_and_does_not_expose_key_in_repr(self) -> None:
        disabled = DeepSeekSettings.from_env({})
        self.assertFalse(disabled.configured)
        configured = DeepSeekSettings.from_env({
            "SIMTROUBLE_LLM_ENABLED": "true",
            "DEEPSEEK_API_KEY": "secret-value",
        })
        self.assertTrue(configured.configured)
        self.assertNotIn("secret-value", repr(configured))


if __name__ == "__main__":
    unittest.main()
