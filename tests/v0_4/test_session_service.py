from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.case_engine import CaseLoader
from core.errors import EvidenceNotFoundError
from core.evidence_engine import EvidenceManager
from core.models.contracts import DiagnosticStage

from apps.training_api.session_models import PublicSessionStage
from apps.training_api.session_repository import SessionRepository
from apps.training_api.session_service import (
    SessionService,
    SessionStageConflictError,
)


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"


class FailingAfterReleaseEvidenceManager(EvidenceManager):
    def request(self, case_session, evidence_id):
        super().request(case_session, evidence_id)
        raise RuntimeError("injected downstream failure")


class SessionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        case = CaseLoader().load(CASE_PATH)
        self.repository = SessionRepository()
        self.service = SessionService(
            repository=self.repository,
            cases={case.case_id: case},
        )

    def test_create_returns_a_learner_safe_ready_view(self) -> None:
        view = self.service.create("ST-001")

        self.assertEqual(PublicSessionStage.READY, view.public_stage)
        self.assertEqual((), view.released_evidence)
        self.assertIsNone(view.current_hypothesis)
        payload = view.model_dump_json()
        for forbidden in (
            "ground_truth",
            "optimal_path",
            "scoring_rules",
            "information_value",
            "related_faults",
            "offset_mm",
            "skill_scores",
            "user_id",
        ):
            self.assertNotIn(forbidden, payload)

    def test_sessions_are_isolated(self) -> None:
        first = self.service.create("ST-001")
        second = self.service.create("ST-001")

        self.service.request_evidence(first.session_id, "E01")
        self.service.submit_hypothesis(first.session_id, "gripper did not hold")

        first_view = self.service.get(first.session_id)
        second_view = self.service.get(second.session_id)
        self.assertEqual(("E01",), tuple(item.id for item in first_view.released_evidence))
        self.assertEqual((), second_view.released_evidence)
        self.assertIsNone(second_view.current_hypothesis)

    def test_canonical_investigation_advances_only_through_core(self) -> None:
        created = self.service.create("ST-001")
        first_evidence = self.service.request_evidence(created.session_id, "E01")
        first_hypothesis = self.service.submit_hypothesis(
            created.session_id,
            "gripper state may explain the failure",
        )
        second_evidence = self.service.request_evidence(created.session_id, "E02")
        revised = self.service.submit_hypothesis(
            created.session_id,
            "object pose is offset on the x axis",
        )

        self.assertEqual(PublicSessionStage.INVESTIGATING, first_evidence.session.public_stage)
        self.assertEqual(1, len(first_hypothesis.hypotheses))
        self.assertEqual(("E01", "E02"), tuple(
            item.id for item in second_evidence.session.released_evidence
        ))
        self.assertEqual(2, len(revised.hypotheses))
        snapshot = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )
        self.assertIs(DiagnosticStage.UPDATE, snapshot.current_stage)
        self.assertEqual(
            [
                "SessionStarted",
                "StateTransitioned",
                "StateTransitioned",
                "EvidenceRequested",
                "EvidenceReleased",
                "StateTransitioned",
                "HypothesisAdded",
                "StateTransitioned",
                "EvidenceRequested",
                "EvidenceReleased",
                "StateTransitioned",
                "HypothesisUpdated",
            ],
            [event.action_type for event in snapshot.trace],
        )

    def test_precollected_evidence_does_not_block_hypothesis_revision(self) -> None:
        created = self.service.create("ST-001")
        for evidence_id in ("E01", "E02", "E03"):
            self.service.request_evidence(created.session_id, evidence_id)

        initial = self.service.submit_hypothesis(
            created.session_id,
            "the gripper may not have retained the object",
        )
        initial_snapshot = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )
        revised = self.service.submit_hypothesis(
            created.session_id,
            "the object pose is offset from the planned position",
        )
        revised_snapshot = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )

        self.assertIs(DiagnosticStage.TEST, initial_snapshot.current_stage)
        self.assertIn("revise_hypothesis", initial.allowed_actions)
        self.assertNotIn("submit_diagnosis", initial.allowed_actions)
        self.assertIs(DiagnosticStage.UPDATE, revised_snapshot.current_stage)
        self.assertIn("submit_diagnosis", revised.allowed_actions)
        self.assertEqual(2, len(revised.hypotheses))

    def test_invalid_stage_and_unknown_evidence_do_not_advance_stage(self) -> None:
        created = self.service.create("ST-001")
        with self.assertRaises(SessionStageConflictError):
            self.service.submit_hypothesis(created.session_id, "too early")

        with self.assertRaises(EvidenceNotFoundError):
            self.service.request_evidence(created.session_id, "E99")

        snapshot = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )
        self.assertIs(DiagnosticStage.OBSERVE, snapshot.current_stage)
        self.assertEqual([], snapshot.evidence_seen)
        self.assertEqual("EvidenceDenied", snapshot.trace[-1].action_type)

    def test_direct_blank_hypothesis_call_is_atomic(self) -> None:
        created = self.service.create("ST-001")
        self.service.request_evidence(created.session_id, "E01")

        before = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )
        with self.assertRaises(ValueError):
            self.service.submit_hypothesis(created.session_id, "   ")
        after = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )
        self.assertEqual(before, after)

    def test_repeated_evidence_is_visible_once_but_traceable(self) -> None:
        created = self.service.create("ST-001")
        self.service.request_evidence(created.session_id, "E01")
        response = self.service.request_evidence(created.session_id, "E01")

        self.assertEqual(1, len(response.session.released_evidence))
        snapshot = self.repository.inspect(
            created.session_id,
            lambda aggregate: aggregate.session,
        )
        self.assertEqual(["E01"], snapshot.evidence_seen)
        self.assertEqual(
            2,
            sum(event.action_type == "EvidenceReleased" for event in snapshot.trace),
        )

    def test_evidence_command_rolls_back_after_downstream_failure(self) -> None:
        case = CaseLoader().load(CASE_PATH)
        repository = SessionRepository()
        service = SessionService(
            repository=repository,
            cases={case.case_id: case},
            evidence_manager=FailingAfterReleaseEvidenceManager(),
        )
        created = service.create("ST-001")
        before = repository.inspect(created.session_id, lambda aggregate: aggregate.session)

        with self.assertRaisesRegex(RuntimeError, "injected downstream failure"):
            service.request_evidence(created.session_id, "E01")

        after = repository.inspect(created.session_id, lambda aggregate: aggregate.session)
        self.assertEqual(before, after)

    def test_projected_evidence_is_a_defensive_copy(self) -> None:
        created = self.service.create("ST-001")
        response = self.service.request_evidence(created.session_id, "E02")
        response.evidence.content["offset_mm"] = -1

        fresh = self.service.get(created.session_id)
        payload = json.loads(fresh.model_dump_json())
        self.assertEqual(70, payload["released_evidence"][0]["content"]["offset_mm"])


if __name__ == "__main__":
    unittest.main()
