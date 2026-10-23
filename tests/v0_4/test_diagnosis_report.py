from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from apps.training_api.evaluation import DiagnosisService
from apps.training_api.evaluation.evaluator import RuleEvaluator
from apps.training_api.evaluation.repository import (
    DiagnosisAlreadySubmittedError,
    ReportNotReadyError,
)
from apps.training_api.learning_models import (
    DiagnosisAssessment,
    DiagnosisSubmission,
    DiagnosisType,
    ScoreStatus,
)
from apps.training_api.session_repository import SessionRepository
from apps.training_api.session_service import (
    DiagnosisEvidenceError,
    SessionService,
    SessionStageConflictError,
)
from core.models.contracts import DiagnosticStage, SkillDimension


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "contracts" / "v0.4"


class DiagnosisReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        report_schema = json.loads(
            (CONTRACT_DIR / "training-report.schema.json").read_text(
                encoding="utf-8"
            )
        )
        diagnosis_schema = json.loads(
            (CONTRACT_DIR / "diagnosis-submission.schema.json").read_text(
                encoding="utf-8"
            )
        )
        registry = Registry().with_resource(
            diagnosis_schema["$id"], Resource.from_contents(diagnosis_schema)
        )
        cls.report_validator = Draft202012Validator(
            report_schema, registry=registry
        )

    def setUp(self) -> None:
        self.repository = SessionRepository()
        self.sessions = SessionService(repository=self.repository)
        self.diagnoses = DiagnosisService(self.sessions)

    def ready_for_diagnosis(self) -> str:
        session_id = self.sessions.create("ST-001").session_id
        self.sessions.request_evidence(session_id, "E01")
        self.sessions.submit_hypothesis(
            session_id, "The gripper may have missed the workpiece."
        )
        self.sessions.request_evidence(session_id, "E02")
        self.sessions.submit_hypothesis(
            session_id, "The workpiece pose differs from the planned pose."
        )
        return session_id

    def submission(
        self,
        diagnosis_type: DiagnosisType = DiagnosisType.OBJECT_POSE_MISMATCH,
        cited: tuple[str, ...] = ("E01", "E02"),
    ) -> DiagnosisSubmission:
        return DiagnosisSubmission(
            contract_version="0.4.0",
            diagnosis_type=diagnosis_type,
            reasoning="The released observations support this diagnosis.",
            cited_evidence_ids=cited,
        )

    def trace(self, session_id: str):
        return self.repository.inspect(
            session_id,
            lambda aggregate: aggregate.session.model_copy(deep=True).trace,
        )

    def test_correct_submission_builds_deterministic_contract_valid_report(self) -> None:
        session_id = self.ready_for_diagnosis()

        submitted = self.diagnoses.submit(session_id, self.submission())
        report = self.diagnoses.report(session_id)
        second_read = self.diagnoses.report(session_id)

        self.assertEqual("SUBMITTED", submitted.public_stage.value)
        self.assertEqual("REVIEWED", self.sessions.get(session_id).public_stage.value)
        self.assertEqual(DiagnosisAssessment.CORRECT, report.diagnosis.assessment)
        self.assertEqual(91.75, report.overall.score)
        self.assertEqual(0.8, report.overall.coverage)
        self.assertEqual(
            ScoreStatus.NOT_ASSESSED,
            report.dimension_results[SkillDimension.SAFETY].status,
        )
        self.assertIsNone(report.dimension_results[SkillDimension.SAFETY].score)
        self.assertEqual(
            0.0, report.dimension_results[SkillDimension.SAFETY].weight
        )
        self.assertEqual(report, second_read)
        self.assertFalse(
            list(self.report_validator.iter_errors(report.model_dump(mode="json")))
        )

        trace = self.trace(session_id)
        self.assertEqual(
            [
                "StateTransitioned",
                "DiagnosisSubmitted",
                "StateTransitioned",
                "DiagnosisEvaluated",
                "ReportGenerated",
                "StateTransitioned",
                "SessionFinished",
            ],
            [event.action_type for event in trace[-7:]],
        )
        serialized_trace = json.dumps(
            [event.model_dump(mode="json") for event in trace]
        )
        for forbidden in ("ground_truth", "scoring_rules", "reasoning"):
            self.assertNotIn(forbidden, serialized_trace)

    def test_diagnosis_is_create_once_and_rejection_does_not_change_trace(self) -> None:
        session_id = self.ready_for_diagnosis()
        self.diagnoses.submit(session_id, self.submission())
        trace_before = self.trace(session_id)

        with self.assertRaises(DiagnosisAlreadySubmittedError):
            self.diagnoses.submit(session_id, self.submission())

        self.assertEqual(trace_before, self.trace(session_id))

    def test_unreleased_evidence_is_rejected_atomically(self) -> None:
        session_id = self.ready_for_diagnosis()
        trace_before = self.trace(session_id)

        with self.assertRaises(DiagnosisEvidenceError):
            self.diagnoses.submit(
                session_id,
                self.submission(cited=("E01", "E03")),
            )

        self.assertEqual(trace_before, self.trace(session_id))
        self.assertEqual(DiagnosticStage.UPDATE, self._internal_stage(session_id))

    def test_evaluator_covers_insufficient_partial_and_incorrect_results(self) -> None:
        scenarios = (
            (
                DiagnosisType.OBJECT_POSE_MISMATCH,
                ("E02",),
                DiagnosisAssessment.INSUFFICIENT,
            ),
            (
                DiagnosisType.GRASP_FAILURE,
                ("E01",),
                DiagnosisAssessment.PARTIALLY_CORRECT,
            ),
            (
                DiagnosisType.OBSTACLE_COLLISION_RISK,
                ("E01",),
                DiagnosisAssessment.INCORRECT,
            ),
        )
        for diagnosis_type, cited, expected in scenarios:
            with self.subTest(expected=expected):
                session_id = self.ready_for_diagnosis()
                self.diagnoses.submit(
                    session_id,
                    self.submission(diagnosis_type, cited),
                )
                report = self.diagnoses.report(session_id)
                self.assertEqual(expected, report.diagnosis.assessment)

    def test_report_and_diagnosis_stage_guards_are_stable(self) -> None:
        session_id = self.sessions.create("ST-001").session_id

        with self.assertRaises(ReportNotReadyError):
            self.diagnoses.report(session_id)
        with self.assertRaises(SessionStageConflictError):
            self.diagnoses.submit(session_id, self.submission())

    def test_qualitative_evaluator_contains_no_numeric_scoring_fields(self) -> None:
        session_id = self.ready_for_diagnosis()
        captured = None

        def inspect_context(context):
            nonlocal captured
            captured = RuleEvaluator().evaluate(context)
            raise RuntimeError("rollback after evaluator inspection")

        with self.assertRaises(RuntimeError):
            self.sessions.complete_diagnosis(
                session_id, self.submission(), inspect_context
            )
        assert captured is not None
        payload = captured.model_dump(mode="json")
        self.assertNotIn("score", json.dumps(payload))
        self.assertNotIn("weight", json.dumps(payload))
        self.assertEqual(DiagnosticStage.UPDATE, self._internal_stage(session_id))

    def _internal_stage(self, session_id: str) -> DiagnosticStage:
        return self.repository.inspect(
            session_id, lambda aggregate: aggregate.session.current_stage
        )


if __name__ == "__main__":
    unittest.main()
