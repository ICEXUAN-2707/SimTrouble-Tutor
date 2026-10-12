"""Deterministic Tutor policy used whenever the online LLM is unavailable.

ADR-008 requires template fallback for timeout, missing key, non-compliant
output or suspected leakage, so training can always continue.
"""

from __future__ import annotations

from core.tutor_engine.models import TutorContext, TutorIntent, TutorResponse


class RuleTutorPolicy:
    """Rule-based Tutor used as the guaranteed fallback and as the offline mode."""

    def reply(
        self,
        context: TutorContext,
        question: str,
        *,
        finished: bool = False,
    ) -> TutorResponse:
        seen = {item.id for item in context.evidence_seen}

        if finished:
            return TutorResponse(
                intent=TutorIntent.REFLECT,
                message="本轮训练已经提交诊断。请查看结果或点击“重新开始”。",
                suggested_next_step=None,
            )

        if "答案" in question or "真因" in question or "直接告诉" in question:
            return TutorResponse(
                intent=TutorIntent.QUESTION,
                message="先不直接公布诊断。请写出一个可检验的假设，再选择证据验证；已开放的检查项为 E01、E02、E03。",
                suggested_next_step="提交一个可检验的假设",
            )

        if "E02" in question.upper() or "位置" in question or "偏移" in question:
            if "E02" not in seen:
                return TutorResponse(
                    intent=TutorIntent.QUESTION,
                    message="位置数据尚未开放。请先点击 E02 检查，再结合观察到的数值说明你的判断。",
                    suggested_next_step="检查 E02 工件位置",
                )
            return TutorResponse(
                intent=TutorIntent.EXPLAIN,
                message="E02 显示工件 X 方向实际位置比预期多 70 mm。这支持位置不匹配的假设；请结合 E01 的夹持结果，说明它如何解释抓取失败，再提交诊断。",
                suggested_next_step="结合 E01 与 E02 提交诊断",
            )

        if "E01" in question.upper() or "夹爪" in question:
            if "E01" not in seen:
                return TutorResponse(
                    intent=TutorIntent.QUESTION,
                    message="夹爪状态尚未开放。请先点击 E01 检查，再区分“闭合命令执行”和“实际夹住工件”。",
                    suggested_next_step="检查 E01 夹爪状态",
                )
            return TutorResponse(
                intent=TutorIntent.EXPLAIN,
                message="E01 显示夹爪已闭合，但没有夹住工件。这个证据只能确认抓取未成功，还不足以单独确定原因。下一步可以检查 E02 的工件位置。",
                suggested_next_step="检查 E02 工件位置",
            )

        if "E03" in question.upper() or "目标" in question:
            if "E03" not in seen:
                return TutorResponse(
                    intent=TutorIntent.QUESTION,
                    message="目标区信息尚未开放。请先点击 E03 检查。",
                    suggested_next_step="检查 E03 目标区状态",
                )
            return TutorResponse(
                intent=TutorIntent.EXPLAIN,
                message="E03 显示目标区可用且没有冲突。请判断它与当前“抓取失败”症状的关系，再选择更有区分力的证据。",
                suggested_next_step="比较 E01 与 E02 的区分力",
            )

        if not context.current_hypothesis:
            return TutorResponse(
                intent=TutorIntent.QUESTION,
                message="机械臂动作完成、夹爪命令执行，但工件未被带走。请先写一个可检验的假设，并说明准备查看哪项证据。",
                suggested_next_step="提交一个可检验的假设",
            )

        return TutorResponse(
            intent=TutorIntent.HINT,
            message="你已经提出假设。请用 E01、E02 或 E03 检查来支持或修正它；仅凭动作完成不能认定抓取成功。",
            suggested_next_step="选择一项检查证据",
        )
