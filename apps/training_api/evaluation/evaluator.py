"""Qualitative diagnosis evaluator; it never produces numeric scores."""

from __future__ import annotations

from core.models.contracts import FaultType, SkillDimension

from ..learning_models import (
    DiagnosisAssessment,
    DiagnosisType,
    DimensionFinding,
    EvaluationFinding,
    EvaluatorResponse,
    FindingQuality,
)
from ..session_service import DiagnosisEvaluationContext


_DIAGNOSIS_TO_FAULT = {
    DiagnosisType.OBJECT_POSE_MISMATCH: FaultType.OBJECT_POSE_OFFSET,
    DiagnosisType.GRASP_FAILURE: FaultType.GRASP_FAILURE,
    DiagnosisType.OBSTACLE_COLLISION_RISK: FaultType.OBSTACLE_COLLISION_RISK,
    DiagnosisType.PLACEMENT_TARGET_CONFLICT: FaultType.PLACEMENT_TARGET_CONFLICT,
}


class RuleEvaluator:
    """Produce reproducible qualitative findings after diagnosis submission."""

    def evaluate(self, context: DiagnosisEvaluationContext) -> EvaluatorResponse:
        assessment = self._assessment(context)
        trace = context.session.trace
        submitted_index = next(
            index
            for index, event in enumerate(trace)
            if event.action_type == "DiagnosisSubmitted"
        )
        cited = context.submission.cited_evidence_ids
        evidence_indices = tuple(
            index
            for index, event in enumerate(trace)
            if event.action_type == "EvidenceReleased" and event.evidence_id in cited
        )
        hypothesis_indices = tuple(
            index
            for index, event in enumerate(trace)
            if event.action_type in {"HypothesisAdded", "HypothesisUpdated"}
        )
        findings = (
            self._diagnosis_finding(
                assessment,
                cited,
                tuple(sorted({*evidence_indices, submitted_index})),
            ),
        )
        dimensions = (
            DimensionFinding(
                dimension=SkillDimension.HYPOTHESIS,
                quality=(
                    FindingQuality.STRONG
                    if len(hypothesis_indices) >= 2
                    else FindingQuality.ADEQUATE
                ),
                rationale="已形成并记录可追溯的诊断假设。",
                trace_indices=hypothesis_indices,
            ),
            DimensionFinding(
                dimension=SkillDimension.EVIDENCE,
                quality=(
                    FindingQuality.STRONG if len(cited) >= 2 else FindingQuality.WEAK
                ),
                rationale="诊断引用了当前会话已释放的证据。",
                trace_indices=tuple(sorted({*evidence_indices, submitted_index})),
            ),
            DimensionFinding(
                dimension=SkillDimension.EFFICIENCY,
                quality=self._efficiency_quality(context),
                rationale="根据重复取证和无效取证事件评价诊断路径效率。",
                trace_indices=self._efficiency_indices(context),
            ),
            DimensionFinding(
                dimension=SkillDimension.UPDATING,
                quality=(
                    FindingQuality.STRONG
                    if any(event.action_type == "HypothesisUpdated" for event in trace)
                    else FindingQuality.NOT_OBSERVED
                ),
                rationale="根据新证据出现后的假设修正记录评价更新能力。",
                trace_indices=tuple(
                    index
                    for index, event in enumerate(trace)
                    if event.action_type == "HypothesisUpdated"
                ),
            ),
            DimensionFinding(
                dimension=SkillDimension.SAFETY,
                quality=FindingQuality.NOT_OBSERVED,
                rationale="ST-001 当前没有可观察的安全操作评价机会。",
                trace_indices=(),
            ),
        )
        feedback, next_step = self._feedback(assessment)
        return EvaluatorResponse(
            contract_version="0.4.0",
            diagnosis_assessment=assessment,
            findings=findings,
            dimension_findings=dimensions,
            feedback_summary=feedback,
            next_learning_step=next_step,
        )

    def _assessment(
        self, context: DiagnosisEvaluationContext
    ) -> DiagnosisAssessment:
        submitted = context.submission.diagnosis_type.value
        if submitted == context.case.ground_truth.diagnosis:
            return (
                DiagnosisAssessment.CORRECT
                if len(context.submission.cited_evidence_ids) >= 2
                else DiagnosisAssessment.INSUFFICIENT
            )
        submitted_fault = _DIAGNOSIS_TO_FAULT[context.submission.diagnosis_type]
        cited = set(context.submission.cited_evidence_ids)
        if any(
            item.id in cited and submitted_fault in item.related_faults
            for item in context.case.evidence
        ):
            return DiagnosisAssessment.PARTIALLY_CORRECT
        return DiagnosisAssessment.INCORRECT

    def _diagnosis_finding(
        self,
        assessment: DiagnosisAssessment,
        cited: tuple[str, ...],
        trace_indices: tuple[int, ...],
    ) -> EvaluationFinding:
        messages = {
            DiagnosisAssessment.CORRECT: "诊断与参考结论一致，且证据引用充分。",
            DiagnosisAssessment.PARTIALLY_CORRECT: "诊断能解释部分现象，但尚未定位根因。",
            DiagnosisAssessment.INCORRECT: "诊断与参考结论不一致，需要重新核对关键证据。",
            DiagnosisAssessment.INSUFFICIENT: "诊断方向正确，但当前引用证据不足。",
        }
        return EvaluationFinding(
            code=f"diagnosis_{assessment.value}",
            message=messages[assessment],
            cited_evidence_ids=cited,
            trace_indices=trace_indices,
        )

    def _efficiency_indices(
        self, context: DiagnosisEvaluationContext
    ) -> tuple[int, ...]:
        return tuple(
            index
            for index, event in enumerate(context.session.trace)
            if event.action_type in {"EvidenceReleased", "EvidenceDenied"}
        )

    def _efficiency_quality(
        self, context: DiagnosisEvaluationContext
    ) -> FindingQuality:
        seen: set[str] = set()
        repeated = 0
        denied = 0
        for event in context.session.trace:
            if event.action_type == "EvidenceDenied":
                denied += 1
            elif event.action_type == "EvidenceReleased" and event.evidence_id:
                if event.evidence_id in seen:
                    repeated += 1
                seen.add(event.evidence_id)
        if denied or repeated > 1:
            return FindingQuality.WEAK
        if repeated == 1:
            return FindingQuality.ADEQUATE
        return FindingQuality.STRONG

    def _feedback(
        self, assessment: DiagnosisAssessment
    ) -> tuple[str, str]:
        if assessment is DiagnosisAssessment.CORRECT:
            return (
                "你完成了从现象、证据到根因的闭环判断。",
                "下一案例继续保持先比较关键测量值、再下结论的顺序。",
            )
        if assessment is DiagnosisAssessment.INSUFFICIENT:
            return (
                "你的诊断方向正确，但证据链还不够完整。",
                "练习用至少两条相互补充的证据支持同一个结论。",
            )
        if assessment is DiagnosisAssessment.PARTIALLY_CORRECT:
            return (
                "你识别到了直接异常，但还需要区分症状与根因。",
                "重新比较工件实际位置、期望位置与夹爪状态。",
            )
        return (
            "当前结论尚不能解释已经释放的关键证据。",
            "回到证据差异，逐项排除碰撞、目标位姿和抓取状态。",
        )
