"""Deterministic Tutor for the bounded ST-001 Demo.

The rules deliberately consume only learner-visible inputs.  This module is
not the Phase 6 LangGraph/LLM Tutor and never reads the authoritative Case.
"""

from __future__ import annotations

from collections.abc import Collection


def reply_to(
    message: str,
    *,
    released_evidence_ids: Collection[str],
    current_hypothesis: str | None,
) -> str:
    seen = frozenset(released_evidence_ids)
    normalized = message.upper()

    if any(term in message for term in ("答案", "真因", "直接告诉")):
        return (
            "先不直接公布诊断。请写出一个可检验的假设，再选择证据验证；"
            "可检查项为 E01、E02、E03。"
        )
    if "E02" in normalized or any(term in message for term in ("位置", "偏移")):
        if "E02" not in seen:
            return "位置数据尚未开放。请先检查 E02，再根据开放的数值说明判断。"
        return (
            "E02 显示工件 X 方向实际位置比预期多 70 mm。这支持位置不匹配的假设；"
            "请结合 E01 的夹持结果说明它如何解释抓取失败。"
        )
    if "E01" in normalized or "夹爪" in message:
        if "E01" not in seen:
            return "夹爪状态尚未开放。请先检查 E01，再区分命令执行和实际夹持。"
        return (
            "E01 显示夹爪已闭合，但没有夹住工件。它确认抓取未成功，"
            "仍需检查 E02 等证据来区分原因。"
        )
    if "E03" in normalized or "目标" in message:
        if "E03" not in seen:
            return "目标区信息尚未开放。请先检查 E03。"
        return (
            "E03 显示目标区可用且没有冲突。请判断它与当前抓取失败的关系，"
            "再选择更有区分力的证据。"
        )
    if not current_hypothesis:
        return (
            "机械臂动作完成、夹爪命令执行，但工件未被带走。"
            "请先写一个可检验的假设，并说明准备查看哪项证据。"
        )
    return (
        "你已经提出假设。请用 E01、E02 或 E03 支持或修正它；"
        "仅凭动作完成不能认定抓取成功。"
    )
