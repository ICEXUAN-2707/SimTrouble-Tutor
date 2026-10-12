"""Offline tests for the optional Tutor LLM layer.

No test here performs network I/O: the online port is exercised through
``ScriptedLLMClient`` and an injected transport stub. Real provider calls are
covered by ``tools/llm_smoke_test.py``.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import LearnerAction, TrainingModule
from core.tutor_engine import (
    LeakGuard,
    OpenAICompatClient,
    RuleTutorPolicy,
    ScriptedLLMClient,
    TutorService,
    TutorIntent,
)
from core.tutor_engine.errors import LLMUnavailableError

ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"
MODULE_PATH = ROOT / "data" / "modules" / "MOD-EXCEPTION.json"


def build_session() -> tuple[CaseSession, TrainingModule]:
    case = CaseLoader().load(CASE_PATH)
    module = TrainingModule.model_validate_json(MODULE_PATH.read_text(encoding="utf-8"))
    return CaseSession(user_id="test-user", case=case), module


def valid_reply() -> str:
    return json.dumps(
        {
            "intent": "question",
            "message": "你观察到的现象和夹爪命令结果之间有什么差异？",
            "suggested_next_step": "检查 E01",
        },
        ensure_ascii=False,
    )


class TutorContextTests(unittest.TestCase):
    def test_context_is_a_public_projection_only(self) -> None:
        session, module = build_session()
        session.record_action(LearnerAction(action_type="inspect", parameters={"evidence_id": "E01"}))
        context = TutorService.build_context(module=module, case_session=session)

        self.assertEqual([], context.forbidden_keys_present())
        dumped = context.model_dump(mode="json")
        for hidden in ("ground_truth", "optimal_path", "scoring_rules", "fault", "initial_state"):
            self.assertNotIn(hidden, dumped)
            self.assertNotIn(hidden, json.dumps(dumped, ensure_ascii=False))

    def test_context_rejects_hidden_extra_fields(self) -> None:
        session, module = build_session()
        context = TutorService.build_context(module=module, case_session=session)
        payload = context.model_dump(mode="json")
        payload["ground_truth"] = {"diagnosis": "object_pose_mismatch"}
        with self.assertRaises(Exception):
            type(context).model_validate(payload)


class OfflineFallbackTests(unittest.TestCase):
    def test_without_client_uses_deterministic_template(self) -> None:
        session, module = build_session()
        service = TutorService(client=None)
        context = TutorService.build_context(module=module, case_session=session)

        reply = service.respond(context, "直接告诉我答案")

        self.assertEqual("template", reply.source)
        self.assertIn("先不直接公布诊断", reply.response.message)
        self.assertFalse(service.online)

    def test_llm_failure_falls_back(self) -> None:
        session, module = build_session()
        service = TutorService(ScriptedLLMClient([]))
        context = TutorService.build_context(module=module, case_session=session)

        with self.assertRaises(LLMUnavailableError):
            service._client.complete(system="s", user="u")

        reply = service.respond(context, "我该看什么？")
        self.assertEqual("template", reply.source)
        self.assertIsNotNone(reply.fallback_reason)

    def test_unparsable_output_falls_back(self) -> None:
        session, module = build_session()
        service = TutorService(ScriptedLLMClient(["这不是 JSON"]))
        context = TutorService.build_context(module=module, case_session=session)

        reply = service.respond(context, "我该看什么？")

        self.assertEqual("template", reply.source)
        self.assertIn("未找到 JSON 对象", reply.fallback_reason or "")


class OnlineOutputValidationTests(unittest.TestCase):
    def test_valid_output_is_used(self) -> None:
        session, module = build_session()
        client = ScriptedLLMClient([valid_reply()])
        service = TutorService(client)
        context = TutorService.build_context(module=module, case_session=session)

        reply = service.respond(context, "我该看什么？")

        self.assertEqual("llm", reply.source)
        self.assertIsNone(reply.fallback_reason)
        self.assertEqual(TutorIntent.QUESTION, reply.response.intent)
        self.assertTrue(service.online)
        system_prompt, user_prompt = client.prompts[0]
        self.assertIn("SimTrouble", system_prompt)
        self.assertIn("学员提问", user_prompt)

    def test_intent_outside_allowlist_falls_back(self) -> None:
        session, module = build_session()
        forbidden = json.dumps(
            {"intent": "reflect", "message": "反思一下吧", "suggested_next_step": None},
            ensure_ascii=False,
        )
        service = TutorService(ScriptedLLMClient([forbidden]))
        context = TutorService.build_context(
            module=module,
            case_session=session,
            allowed_tutor_actions=[TutorIntent.QUESTION, TutorIntent.HINT],
        )

        reply = service.respond(context, "我该看什么？")

        self.assertEqual("template", reply.source)
        self.assertIn("白名单", reply.fallback_reason or "")

    def test_overlong_message_falls_back(self) -> None:
        session, module = build_session()
        long_message = "很" * 500
        payload = json.dumps(
            {"intent": "question", "message": long_message, "suggested_next_step": None},
            ensure_ascii=False,
        )
        service = TutorService(ScriptedLLMClient([payload]), max_message_chars=300)
        context = TutorService.build_context(module=module, case_session=session)

        reply = service.respond(context, "我该看什么？")

        self.assertEqual("template", reply.source)
        self.assertIn("超过上限", reply.fallback_reason or "")

    def test_leaked_ground_truth_falls_back(self) -> None:
        session, module = build_session()
        leaked = json.dumps(
            {
                "intent": "explain",
                "message": "真因是 object_pose_mismatch，工件位置不匹配。",
                "suggested_next_step": None,
            },
            ensure_ascii=False,
        )
        service = TutorService(ScriptedLLMClient([leaked]))
        context = TutorService.build_context(module=module, case_session=session)
        guard = LeakGuard.from_case(session.authoritative_case)

        reply = service.respond(context, "真因是什么？", leak_guard=guard)

        self.assertEqual("template", reply.source)
        self.assertIn("疑似泄漏", reply.fallback_reason or "")

    def test_released_evidence_values_are_not_treated_as_leak(self) -> None:
        session, module = build_session()
        released = EvidenceManager().request(session, "E02")
        context = TutorService.build_context(
            module=module, case_session=session, released_evidence=[released]
        )
        guard = LeakGuard.from_case(
            session.authoritative_case, released_ids=[released.id]
        )
        message = "E02 显示工件 X 方向偏移 70 mm，你怎么解释？"

        self.assertEqual([], guard.scan(message))

    def test_unreleased_evidence_values_are_blocked(self) -> None:
        session, module = build_session()
        guard = LeakGuard.from_case(session.authoritative_case, released_ids=["E01"])
        payload = json.dumps(
            {
                "intent": "explain",
                "message": "工件实际位置是 70 mm，属于 object_pose_offset。",
                "suggested_next_step": None,
            },
            ensure_ascii=False,
        )
        service = TutorService(ScriptedLLMClient([payload]))
        context = TutorService.build_context(module=module, case_session=session)

        reply = service.respond(context, "位置呢？", leak_guard=guard)

        self.assertEqual("template", reply.source)
        self.assertIn("疑似泄漏", reply.fallback_reason or "")


class OpenAICompatClientTests(unittest.TestCase):
    def test_parses_chat_completion_payload(self) -> None:
        captured: dict[str, object] = {}

        def transport(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
            captured.update({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": valid_reply()}}
                ]
            }

        client = OpenAICompatClient(api_key="test-key", model="demo-model", transport=transport)
        text = client.complete(system="system-prompt", user="user-prompt")

        self.assertEqual(valid_reply(), text)
        self.assertEqual("https://api.openai.com/v1/chat/completions", captured["url"])
        self.assertEqual("Bearer test-key", captured["headers"]["Authorization"])
        self.assertEqual("demo-model", captured["payload"]["model"])
        self.assertEqual("user-prompt", captured["payload"]["messages"][1]["content"])

    def test_unexpected_shape_raises(self) -> None:
        client = OpenAICompatClient(api_key="k", transport=lambda *args: {"choices": []})
        with self.assertRaises(LLMUnavailableError):
            client.complete(system="s", user="u")

    def test_from_env_returns_none_without_key(self) -> None:
        self.assertIsNone(OpenAICompatClient.from_env({}))

    def test_from_env_reads_configuration(self) -> None:
        client = OpenAICompatClient.from_env(
            {
                "SIMTROUBLE_LLM_API_KEY": "sk-demo",
                "SIMTROUBLE_LLM_BASE_URL": "https://api.deepseek.com/v1",
                "SIMTROUBLE_LLM_MODEL": "deepseek-chat",
                "SIMTROUBLE_LLM_TIMEOUT": "15",
            }
        )
        self.assertIsNotNone(client)
        assert client is not None
        self.assertEqual("https://api.deepseek.com/v1", client.base_url)
        self.assertEqual("deepseek-chat", client.model)
        self.assertEqual(15.0, client.timeout)


class RulePolicyTests(unittest.TestCase):
    def test_policy_prompts_for_hypothesis_first(self) -> None:
        session, module = build_session()
        context = TutorService.build_context(module=module, case_session=session)

        response = RuleTutorPolicy().reply(context, "工件没被带走")

        self.assertEqual(TutorIntent.QUESTION, response.intent)
        self.assertIn("可检验的假设", response.message)

    def test_policy_uses_released_evidence(self) -> None:
        session, module = build_session()
        released = EvidenceManager().request(session, "E01")
        context = TutorService.build_context(
            module=module, case_session=session, released_evidence=[released]
        )

        response = RuleTutorPolicy().reply(context, "夹爪状态说明什么？")

        self.assertEqual(TutorIntent.EXPLAIN, response.intent)
        self.assertIn("E02", response.message)


if __name__ == "__main__":
    unittest.main()
