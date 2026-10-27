from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from apps.training_api.learning_models import (
    DiagnosisAssessment,
    DiagnosisReview,
    DiagnosisSubmission,
    DiagnosisType,
    DimensionFinding,
    EvaluationFinding,
    EvaluatorResponse,
    FindingQuality,
    OverallScore,
    ScoreStatus,
    SkillDimensionResult,
    TrainingReportV04,
    TutorAction,
    TutorIntent,
    TutorMode,
    TutorRequest,
    TutorResponse,
)
from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models.contracts import SkillDimension


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "contracts" / "v0.4"
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"


class LearningContractTests(unittest.TestCase):
    def setUp(self) -> None:
        case = CaseLoader().load(CASE_PATH)
        self.aggregate = CaseSession(
            user_id="contract-user",
            case=case,
            session_id="contract-session",
        )

    def test_contract_package_is_versioned_and_strict(self) -> None:
        expected = {
            "tutor-request.schema.json",
            "tutor-response.schema.json",
            "diagnosis-submission.schema.json",
            "evaluator-response.schema.json",
            "training-report.schema.json",
        }
        schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in CONTRACT_DIR.glob("*.schema.json")
        }
        self.assertEqual(expected, set(schemas))
        for schema in schemas.values():
            self.assertEqual(
                "https://json-schema.org/draft/2020-12/schema", schema["$schema"]
            )
            self.assertFalse(schema["additionalProperties"])

    def test_tutor_request_contains_only_public_released_context(self) -> None:
        released = EvidenceManager().request(self.aggregate, "E01")
        request = TutorRequest(
            contract_version="0.4.0",
            session_id=self.aggregate.session.session_id,
            case_public_state=self.aggregate.public_case_state(),
            released_evidence=(released,),
            messages=(),
            hypotheses=(),
            current_hypothesis=None,
            allowed_actions=(
                TutorAction.INSPECT_EVIDENCE,
                TutorAction.SUBMIT_HYPOTHESIS,
            ),
        )

        payload = request.model_dump_json()
        for forbidden in (
            "ground_truth",
            "optimal_path",
            "scoring_rules",
            "related_faults",
            "information_value",
            "offset_mm",
        ):
            self.assertNotIn(forbidden, payload)

        duplicate_request = request.model_dump()
        duplicate_request["allowed_actions"] = (TutorAction.INSPECT_EVIDENCE,) * 2
        with self.assertRaises(ValidationError):
            TutorRequest.model_validate(duplicate_request)

    def test_tutor_response_is_structured_and_has_no_state_authority(self) -> None:
        response = TutorResponse(
            contract_version="0.4.0",
            intent=TutorIntent.QUESTION,
            message="夹爪闭合后，工件是否随末端移动？",
            hint_level=0,
            suggested_action=TutorAction.OBSERVE_SCENE,
        )
        self.assertEqual(0, response.hint_level)
        self.assertNotIn("score", response.model_dump())
        with self.assertRaises(ValidationError):
            TutorResponse.model_validate({**response.model_dump(), "next_stage": "FINISH"})

    def test_diagnosis_requires_unique_released_evidence_references(self) -> None:
        submission = DiagnosisSubmission(
            contract_version="0.4.0",
            diagnosis_type=DiagnosisType.OBJECT_POSE_MISMATCH,
            reasoning="E01 shows no held object and E02 confirms a pose mismatch.",
            cited_evidence_ids=("E01", "E02"),
        )
        self.assertEqual(2, len(submission.cited_evidence_ids))
        with self.assertRaises(ValidationError):
            DiagnosisSubmission(
                contract_version="0.4.0",
                diagnosis_type=DiagnosisType.OBJECT_POSE_MISMATCH,
                reasoning="duplicate citation",
                cited_evidence_ids=("E02", "E02"),
            )

    def test_evaluator_returns_findings_but_no_numeric_score(self) -> None:
        response = EvaluatorResponse(
            contract_version="0.4.0",
            diagnosis_assessment=DiagnosisAssessment.CORRECT,
            findings=(
                EvaluationFinding(
                    code="diagnosis_supported",
                    message="The cited pose evidence supports the diagnosis.",
                    cited_evidence_ids=("E02",),
                    trace_indices=(5,),
                ),
            ),
            dimension_findings=(
                DimensionFinding(
                    dimension=SkillDimension.EVIDENCE,
                    quality=FindingQuality.STRONG,
                    rationale="The learner cited the discriminating evidence.",
                    trace_indices=(5,),
                ),
            ),
            feedback_summary="The conclusion is evidence-backed.",
            next_learning_step="Compare alternative causes before final submission.",
        )
        payload = json.dumps(response.model_dump(mode="json"))
        self.assertNotIn("score", payload)
        self.assertNotIn("weight", payload)

    def test_report_enforces_scored_and_not_assessed_semantics(self) -> None:
        scored = SkillDimensionResult(
            status=ScoreStatus.SCORED,
            score=80,
            weight=1 / 3,
            rationale="Supported by recorded behavior.",
            rule_ids=("R-EVIDENCE-01",),
            trace_indices=(5,),
        )
        not_assessed = SkillDimensionResult(
            status=ScoreStatus.NOT_ASSESSED,
            score=None,
            weight=0,
            rationale="No observable safety action exists in ST-001.",
            rule_ids=(),
            trace_indices=(),
        )
        dimensions = {
            SkillDimension.HYPOTHESIS: scored,
            SkillDimension.EVIDENCE: scored,
            SkillDimension.EFFICIENCY: scored,
            SkillDimension.UPDATING: not_assessed,
            SkillDimension.SAFETY: not_assessed,
        }
        submission = DiagnosisSubmission(
            contract_version="0.4.0",
            diagnosis_type=DiagnosisType.OBJECT_POSE_MISMATCH,
            reasoning="The object pose differs from the expected pose.",
            cited_evidence_ids=("E02",),
        )
        report = TrainingReportV04(
            contract_version="0.4.0",
            rubric_version="st001-1.0",
            session_id="contract-session",
            case_id="ST-001",
            diagnosis=DiagnosisReview(
                submitted=submission,
                assessment=DiagnosisAssessment.CORRECT,
                reference_explanation="The X position is offset from the planned pose.",
            ),
            evidence_used=("E02",),
            dimension_results=dimensions,
            overall=OverallScore(
                score=80,
                coverage=0.6,
                included_dimensions=(
                    SkillDimension.HYPOTHESIS,
                    SkillDimension.EVIDENCE,
                    SkillDimension.EFFICIENCY,
                ),
            ),
            feedback_summary="Good use of discriminating evidence.",
            next_learning_step="Practice revising an initial hypothesis.",
            tutor_mode=TutorMode.RULE_FALLBACK,
        )
        self.assertEqual(
            ScoreStatus.NOT_ASSESSED,
            report.dimension_results[SkillDimension.SAFETY].status,
        )

        with self.assertRaises(ValidationError):
            SkillDimensionResult(
                status=ScoreStatus.NOT_ASSESSED,
                score=0,
                weight=0,
                rationale="Invalid zero score instead of null.",
                rule_ids=(),
                trace_indices=(),
            )


if __name__ == "__main__":
    unittest.main()
