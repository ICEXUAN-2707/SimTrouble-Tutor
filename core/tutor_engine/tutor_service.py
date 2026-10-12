"""Tutor Service: public projection -> optional LLM -> validation -> fallback.

The service never owns business truth. It builds a ``TutorContext`` projection,
asks the optional LLM for a constrained ``TutorResponse``, validates that output
against intent/length/leakage rules and falls back to :class:`RuleTutorPolicy`
on any failure. Session state stays in Core Domain.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from core.case_engine import CaseSession
from core.models import ReleasedEvidence, TrainingModule
from core.tutor_engine.errors import LLMUnavailableError
from core.tutor_engine.leak_guard import LeakGuard
from core.tutor_engine.llm_client import LLMClient, OpenAICompatClient
from core.tutor_engine.models import TutorContext, TutorIntent, TutorReply, TutorResponse
from core.tutor_engine.policy import RuleTutorPolicy

SYSTEM_PROMPT = """你是 SimTrouble Tutor 的受限表达层，面向工业机器人柔性搬运工作站的运维学员。

硬性约束：
1. 只能使用上下文中的公开信息；不得透露真因、最优诊断路径、未释放的证据内容或评分规则。
2. 采用苏格拉底式引导：先追问、再提示、最后才解释；每次只推进一步。
3. 不替学员下结论，不写诊断答案，不编造上下文中不存在的数值或设备状态。
4. 学员提出错误假设时，指出它与哪条已开放证据冲突，而不是直接给出正确结论。
5. 只输出一个 JSON 对象，不要输出解释、Markdown 或代码块。

输出格式：
{"intent": "question|hint|explain|reflect", "message": "中文回复，不超过 200 字", "suggested_next_step": "一句话建议或 null"}
"""

OUTPUT_TEMPLATE = (
    '{"intent": "question", "message": "...", "suggested_next_step": "..."}'
)

DEFAULT_ALLOWED_ACTIONS = (
    TutorIntent.QUESTION,
    TutorIntent.HINT,
    TutorIntent.EXPLAIN,
)


class TutorService:
    def __init__(
        self,
        client: LLMClient | None = None,
        *,
        policy: RuleTutorPolicy | None = None,
        max_message_chars: int = 300,
    ) -> None:
        self._client = client
        self._policy = policy or RuleTutorPolicy()
        self._max_message_chars = max_message_chars

    @property
    def online(self) -> bool:
        return self._client is not None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "TutorService":
        """Build a service from environment variables.

        Recognised variables: ``SIMTROUBLE_LLM_API_KEY`` (required for online
        mode), ``SIMTROUBLE_LLM_BASE_URL``, ``SIMTROUBLE_LLM_MODEL``,
        ``SIMTROUBLE_LLM_TIMEOUT``. Without an API key the service runs purely
        on the deterministic fallback.
        """

        return cls(OpenAICompatClient.from_env(env))

    @staticmethod
    def build_context(
        *,
        module: TrainingModule,
        case_session: CaseSession,
        released_evidence: Sequence[ReleasedEvidence] = (),
        allowed_tutor_actions: Sequence[TutorIntent] = DEFAULT_ALLOWED_ACTIONS,
    ) -> TutorContext:
        return TutorContext(
            training_module=module,
            case_public_state=case_session.public_case_state(),
            evidence_seen=list(released_evidence),
            learner_action_history=list(case_session.session.actions),
            current_hypothesis=case_session.session.current_hypothesis,
            current_skill_profile=case_session.session.skill_scores,
            allowed_tutor_actions=list(allowed_tutor_actions),
        )

    def respond(
        self,
        context: TutorContext,
        question: str,
        *,
        finished: bool = False,
        leak_guard: LeakGuard | None = None,
    ) -> TutorReply:
        fallback = self._policy.reply(context, question, finished=finished)

        if self._client is None:
            return TutorReply(
                response=fallback, source="template", fallback_reason="未配置在线大模型"
            )

        try:
            raw = self._client.complete(
                system=SYSTEM_PROMPT, user=self._user_prompt(context, question)
            )
            candidate = self._parse(raw)
        except (LLMUnavailableError, ValueError) as exc:
            return TutorReply(
                response=fallback,
                source="template",
                fallback_reason=f"在线大模型不可用：{exc}",
            )

        rejection = self._reject_reason(candidate, context, leak_guard)
        if rejection is not None:
            return TutorReply(
                response=fallback, source="template", fallback_reason=rejection
            )

        return TutorReply(response=candidate, source="llm", fallback_reason=None)

    @staticmethod
    def _user_prompt(context: TutorContext, question: str) -> str:
        payload = context.model_dump(mode="json")
        return (
            "以下是本次允许的 Tutor 输入上下文（公开投影，JSON）：\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            f"学员提问：{question}\n\n"
            f"只输出如下 JSON：{OUTPUT_TEMPLATE}"
        )

    @classmethod
    def _parse(cls, raw: str) -> TutorResponse:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("模型输出中未找到 JSON 对象")
        data = json.loads(text[start : end + 1])
        return TutorResponse.model_validate(data)

    def _reject_reason(
        self,
        candidate: TutorResponse,
        context: TutorContext,
        leak_guard: LeakGuard | None,
    ) -> str | None:
        if candidate.intent not in context.allowed_tutor_actions:
            return f"intent {candidate.intent!s} 不在 allowed_tutor_actions 白名单内"
        if len(candidate.message) > self._max_message_chars:
            return f"message 长度 {len(candidate.message)} 超过上限 {self._max_message_chars}"
        if leak_guard is not None:
            leaked = leak_guard.scan(candidate.message)
            if leaked:
                return f"疑似泄漏隐藏信息：{', '.join(leaked)}"
        return None
