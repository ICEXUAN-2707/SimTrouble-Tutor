from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from pydantic import ValidationError
from referencing import Registry, Resource

from apps.training_api.learning_models import TrainingReportV04


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "contracts" / "v0.4"


def dimension(
    status: str,
    *,
    score: float | None,
    weight: float,
) -> dict:
    return {
        "status": status,
        "score": score,
        "weight": weight,
        "rationale": "Supported by observable learner behavior.",
        "rule_ids": ["R-01"] if status == "scored" else [],
        "trace_indices": [1] if status == "scored" else [],
    }


def valid_report_payload() -> dict:
    return {
        "contract_version": "0.4.0",
        "rubric_version": "st001-1.0",
        "session_id": "contract-session",
        "case_id": "ST-001",
        "diagnosis": {
            "submitted": {
                "contract_version": "0.4.0",
                "diagnosis_type": "object_pose_mismatch",
                "reasoning": "Released pose evidence supports the diagnosis.",
                "cited_evidence_ids": ["E02"],
            },
            "assessment": "correct",
            "reference_explanation": "The observed pose differs from the plan.",
        },
        "evidence_used": ["E02"],
        "dimension_results": {
            "hypothesis": dimension("scored", score=80, weight=1 / 3),
            "evidence": dimension("scored", score=80, weight=1 / 3),
            "efficiency": dimension("scored", score=80, weight=1 / 3),
            "updating": dimension("not_assessed", score=None, weight=0),
            "safety": dimension("not_assessed", score=None, weight=0),
        },
        "overall": {
            "score": 80,
            "coverage": 0.6,
            "included_dimensions": ["hypothesis", "evidence", "efficiency"],
        },
        "feedback_summary": "The diagnosis is supported by released evidence.",
        "next_learning_step": "Practice revising competing hypotheses.",
        "tutor_mode": "rule_fallback",
    }


class TrainingReportContractParityTests(unittest.TestCase):
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
            diagnosis_schema["$id"],
            Resource.from_contents(diagnosis_schema),
        )
        cls.validator = Draft202012Validator(report_schema, registry=registry)

    def assert_contract_result(self, payload: dict, *, accepted: bool) -> None:
        schema_accepted = not list(self.validator.iter_errors(payload))
        try:
            TrainingReportV04.model_validate(payload)
            runtime_accepted = True
        except ValidationError:
            runtime_accepted = False

        self.assertEqual(
            accepted,
            schema_accepted,
            "JSON Schema result did not match the expected contract result",
        )
        self.assertEqual(
            accepted,
            runtime_accepted,
            "Pydantic result did not match the expected contract result",
        )

    def test_valid_report_is_accepted_by_both_contracts(self) -> None:
        self.assert_contract_result(valid_report_payload(), accepted=True)

    def test_not_assessed_requires_null_score_and_zero_weight(self) -> None:
        payload = valid_report_payload()
        payload["dimension_results"]["safety"].update(score=50, weight=0.5)
        self.assert_contract_result(payload, accepted=False)

    def test_scored_dimension_requires_a_numeric_score(self) -> None:
        payload = valid_report_payload()
        payload["dimension_results"]["evidence"]["score"] = None
        self.assert_contract_result(payload, accepted=False)

    def test_included_dimensions_must_be_unique(self) -> None:
        payload = valid_report_payload()
        payload["overall"]["included_dimensions"] = [
            "hypothesis",
            "evidence",
            "evidence",
        ]
        self.assert_contract_result(payload, accepted=False)

    def test_coverage_must_match_included_dimension_count(self) -> None:
        payload = valid_report_payload()
        payload["overall"]["coverage"] = 0.9
        self.assert_contract_result(payload, accepted=False)

    def test_included_dimensions_must_match_scored_dimensions(self) -> None:
        payload = valid_report_payload()
        payload["overall"] = {
            "score": 80,
            "coverage": 0.4,
            "included_dimensions": ["hypothesis", "evidence"],
        }
        self.assert_contract_result(payload, accepted=False)

    def test_empty_coverage_requires_a_null_overall_score(self) -> None:
        payload = valid_report_payload()
        for result in payload["dimension_results"].values():
            result.update(
                status="not_assessed",
                score=None,
                weight=0,
                rule_ids=[],
                trace_indices=[],
            )
        payload["overall"] = {
            "score": 0,
            "coverage": 0,
            "included_dimensions": [],
        }
        self.assert_contract_result(payload, accepted=False)

if __name__ == "__main__":
    unittest.main()
