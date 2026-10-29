"""Deterministic response used whenever the external provider is unavailable."""

from __future__ import annotations

from ..learning_models import TutorAction, TutorRequest, TutorResponse
from .policy import TutorPolicyDecision


class RuleTutor:
    def generate(
        self,
        request: TutorRequest,
        decision: TutorPolicyDecision,
    ) -> TutorResponse:
        message = self._message(request, decision.suggested_action)
        return TutorResponse(
            contract_version="0.4.0",
            intent=decision.intent,
            message=message,
            hint_level=decision.hint_level,
            suggested_action=decision.suggested_action,
        )

    def _message(
        self,
        request: TutorRequest,
        action: TutorAction | None,
    ) -> str:
        if action is TutorAction.INSPECT_EVIDENCE:
            seen = {item.id for item in request.released_evidence}
            unseen = [
                item.id
                for item in request.case_public_state.evidence_options
                if item.id not in seen
            ]
            options = "、".join(unseen) if unseen else "可用证据"
            return (
                f"先别急着下结论。你可以从 {options} 中选一项检查，并说明："
                "它能减少哪个不确定性？"
            )
        if action is TutorAction.SUBMIT_HYPOTHESIS:
            return "请把当前观察写成一个可验证假设，并说明哪条已释放证据支持它。"
        if action is TutorAction.REVISE_HYPOTHESIS:
            return "对照最新证据：它支持、削弱还是推翻了当前假设？请据此修正假设。"
        if action is TutorAction.SUBMIT_DIAGNOSIS:
            return "提交诊断前，请至少引用两条已释放证据，并说明它们如何共同支持判断。"
        if action is TutorAction.REFLECT:
            return "回顾这次判断：哪条证据最关键？如果重来一次，你会先检查什么？"
        if action is TutorAction.OBSERVE_SCENE:
            return "先只描述你看见的现象，不要加入原因判断；再指出最值得验证的异常。"
        return "当前没有可由 Tutor 执行的动作，请使用页面中的可用操作继续学习。"
