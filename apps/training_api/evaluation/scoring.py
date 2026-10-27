"""Versioned deterministic scoring derived only from authoritative Trace."""

from __future__ import annotations

from dataclasses import dataclass

from core.models.contracts import SkillDimension

from ..learning_models import OverallScore, ScoreStatus, SkillDimensionResult
from ..session_service import DiagnosisEvaluationContext


RUBRIC_VERSION = "st001-1.0"
_WEIGHTS = {
    SkillDimension.HYPOTHESIS: 0.30,
    SkillDimension.EVIDENCE: 0.35,
    SkillDimension.EFFICIENCY: 0.15,
    SkillDimension.UPDATING: 0.20,
}


@dataclass(frozen=True)
class ScoreBundle:
    dimensions: dict[SkillDimension, SkillDimensionResult]
    overall: OverallScore


class DeterministicSkillEngine:
    def score(self, context: DiagnosisEvaluationContext) -> ScoreBundle:
        hypothesis_indices = self._indices(
            context, {"HypothesisAdded", "HypothesisUpdated"}
        )
        update_indices = self._indices(context, {"HypothesisUpdated"})
        evidence_indices = tuple(
            index
            for index, event in enumerate(context.session.trace)
            if event.action_type == "EvidenceReleased"
            and event.evidence_id in context.submission.cited_evidence_ids
        )
        diagnosis_indices = self._indices(context, {"DiagnosisSubmitted"})

        hypothesis_score = 90.0 if update_indices else 70.0
        hypothesis_rule = (
            "ST001-HYP-UPDATED" if update_indices else "ST001-HYP-RECORDED"
        )
        cited_count = len(context.submission.cited_evidence_ids)
        evidence_score = (
            100.0 if cited_count >= 3 else 85.0 if cited_count == 2 else 60.0
        )
        evidence_rule = f"ST001-EVD-CITED-{min(cited_count, 3)}"

        repeated, denied, efficiency_indices = self._efficiency(context)
        efficiency_score = max(0.0, 100.0 - repeated * 15.0 - denied * 25.0)
        efficiency_rule = (
            "ST001-EFF-DIRECT"
            if not repeated and not denied
            else "ST001-EFF-DEDUCTIONS"
        )
        dimensions = {
            SkillDimension.HYPOTHESIS: SkillDimensionResult(
                status=ScoreStatus.SCORED,
                score=hypothesis_score,
                weight=_WEIGHTS[SkillDimension.HYPOTHESIS],
                rationale="根据假设提出与后续修正记录计算。",
                rule_ids=(hypothesis_rule,),
                trace_indices=hypothesis_indices,
            ),
            SkillDimension.EVIDENCE: SkillDimensionResult(
                status=ScoreStatus.SCORED,
                score=evidence_score,
                weight=_WEIGHTS[SkillDimension.EVIDENCE],
                rationale="根据诊断中引用的已释放证据数量计算。",
                rule_ids=(evidence_rule,),
                trace_indices=tuple(sorted({*evidence_indices, *diagnosis_indices})),
            ),
            SkillDimension.EFFICIENCY: SkillDimensionResult(
                status=ScoreStatus.SCORED,
                score=efficiency_score,
                weight=_WEIGHTS[SkillDimension.EFFICIENCY],
                rationale="从满分中扣除重复取证和无效取证事件。",
                rule_ids=(efficiency_rule,),
                trace_indices=efficiency_indices,
            ),
            SkillDimension.UPDATING: self._updating_result(context),
            SkillDimension.SAFETY: SkillDimensionResult(
                status=ScoreStatus.NOT_ASSESSED,
                score=None,
                weight=0.0,
                rationale="ST-001 没有可观察的安全交互，不能据此评分。",
                rule_ids=(),
                trace_indices=(),
            ),
        }
        included = tuple(
            dimension
            for dimension in SkillDimension
            if dimensions[dimension].status is ScoreStatus.SCORED
        )
        effective_weight = sum(dimensions[item].weight for item in included)
        overall_score = (
            round(
                sum(
                    (dimensions[item].score or 0.0) * dimensions[item].weight
                    for item in included
                )
                / effective_weight,
                2,
            )
            if included
            else None
        )
        return ScoreBundle(
            dimensions=dimensions,
            overall=OverallScore(
                score=overall_score,
                coverage=len(included) / len(SkillDimension),
                included_dimensions=included,
            ),
        )

    def _indices(
        self,
        context: DiagnosisEvaluationContext,
        action_types: set[str],
    ) -> tuple[int, ...]:
        return tuple(
            index
            for index, event in enumerate(context.session.trace)
            if event.action_type in action_types
        )

    def _efficiency(
        self, context: DiagnosisEvaluationContext
    ) -> tuple[int, int, tuple[int, ...]]:
        seen: set[str] = set()
        repeated = 0
        denied = 0
        indices: list[int] = []
        for index, event in enumerate(context.session.trace):
            if event.action_type == "EvidenceDenied":
                denied += 1
                indices.append(index)
            elif event.action_type == "EvidenceReleased" and event.evidence_id:
                if event.evidence_id in seen:
                    repeated += 1
                seen.add(event.evidence_id)
                indices.append(index)
        return repeated, denied, tuple(indices)

    def _updating_result(
        self, context: DiagnosisEvaluationContext
    ) -> SkillDimensionResult:
        trace = context.session.trace
        first_hypothesis = next(
            (
                index
                for index, event in enumerate(trace)
                if event.action_type == "HypothesisAdded"
            ),
            None,
        )
        evidence_after = tuple(
            index
            for index, event in enumerate(trace)
            if event.action_type == "EvidenceReleased"
            and first_hypothesis is not None
            and index > first_hypothesis
        )
        if not evidence_after:
            return SkillDimensionResult(
                status=ScoreStatus.NOT_ASSESSED,
                score=None,
                weight=0.0,
                rationale="本次路径没有出现假设后的新证据，缺少更新评价机会。",
                rule_ids=(),
                trace_indices=(),
            )
        updates = tuple(
            index
            for index, event in enumerate(trace)
            if event.action_type == "HypothesisUpdated"
            and index > evidence_after[0]
        )
        return SkillDimensionResult(
            status=ScoreStatus.SCORED,
            score=100.0 if updates else 40.0,
            weight=_WEIGHTS[SkillDimension.UPDATING],
            rationale=(
                "获取新证据后主动修正了假设。"
                if updates
                else "获取新证据后没有记录假设修正。"
            ),
            rule_ids=(
                "ST001-UPD-RESPONDED" if updates else "ST001-UPD-NOT-RESPONDED",
            ),
            trace_indices=tuple(sorted({*evidence_after, *updates})),
        )
