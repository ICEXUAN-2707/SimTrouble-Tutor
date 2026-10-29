"""Build the frozen TrainingReportV04 from qualitative and numeric results."""

from __future__ import annotations

from ..learning_models import DiagnosisReview, TrainingReportV04, TutorMode
from ..session_service import DiagnosisEvaluationContext
from .evaluator import RuleEvaluator
from .scoring import DeterministicSkillEngine, RUBRIC_VERSION


class TrainingReportBuilder:
    def __init__(
        self,
        evaluator: RuleEvaluator | None = None,
        skill_engine: DeterministicSkillEngine | None = None,
    ) -> None:
        self._evaluator = evaluator or RuleEvaluator()
        self._skill_engine = skill_engine or DeterministicSkillEngine()

    def build(self, context: DiagnosisEvaluationContext) -> TrainingReportV04:
        evaluation = self._evaluator.evaluate(context)
        scores = self._skill_engine.score(context)
        return TrainingReportV04(
            contract_version="0.4.0",
            rubric_version=RUBRIC_VERSION,
            session_id=context.session.session_id,
            case_id=context.case.case_id,
            diagnosis=DiagnosisReview(
                submitted=context.submission,
                assessment=evaluation.diagnosis_assessment,
                reference_explanation=self._reference_explanation(context),
            ),
            evidence_used=context.submission.cited_evidence_ids,
            dimension_results=scores.dimensions,
            overall=scores.overall,
            feedback_summary=evaluation.feedback_summary,
            next_learning_step=evaluation.next_learning_step,
            tutor_mode=self._tutor_mode(context),
        )

    def _tutor_mode(self, context: DiagnosisEvaluationContext) -> TutorMode:
        if any(
            event.action_type == "TutorDelivered" for event in context.session.trace
        ):
            return TutorMode.LLM
        return TutorMode.RULE_FALLBACK

    def _reference_explanation(
        self, context: DiagnosisEvaluationContext
    ) -> str:
        if context.case.ground_truth.diagnosis == "object_pose_mismatch":
            pose = next(
                (item for item in context.case.evidence if item.type == "object_pose"),
                None,
            )
            if pose is not None:
                offset = pose.content.get("offset_mm")
                return (
                    "参考诊断为工件位姿不匹配。"
                    f"位置证据显示工件相对期望位置偏移 {offset} mm，"
                    "因此夹爪按原轨迹闭合时未能抓住工件。"
                )
        return f"参考诊断为 {context.case.ground_truth.diagnosis}。"
