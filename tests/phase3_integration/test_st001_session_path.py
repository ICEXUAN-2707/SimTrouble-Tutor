from __future__ import annotations

import unittest
from pathlib import Path

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import LearnerAction
from core.models.contracts import DiagnosticStage


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"


class ST001SessionPathTests(unittest.TestCase):
    def test_explicit_st001_path_reaches_finish_with_exact_trace_order(self) -> None:
        case = CaseLoader().load(CASE_PATH)
        aggregate = CaseSession(
            user_id="st001-integration-user",
            case=case,
            session_id="st001-integration-session",
        )
        evidence = EvidenceManager()

        aggregate.transition_to(DiagnosticStage.OBSERVE)
        aggregate.record_action(
            LearnerAction(action_type="inspect", parameters={"target": "gripper"})
        )
        aggregate.transition_to(DiagnosticStage.INVESTIGATE)
        evidence.request(aggregate, "E01")
        aggregate.transition_to(DiagnosticStage.HYPOTHESIZE)
        aggregate.submit_hypothesis("gripper failed to hold the workpiece")
        aggregate.transition_to(DiagnosticStage.TEST)
        evidence.request(aggregate, "E02")
        aggregate.transition_to(DiagnosticStage.UPDATE)
        aggregate.submit_hypothesis("object pose is offset on the x axis")
        aggregate.transition_to(DiagnosticStage.DIAGNOSE)
        aggregate.transition_to(DiagnosticStage.REFLECT)
        aggregate.transition_to(DiagnosticStage.FINISH)

        session = aggregate.session
        self.assertIs(DiagnosticStage.FINISH, session.current_stage)
        self.assertEqual(["E01", "E02"], session.evidence_seen)
        self.assertEqual(
            [
                "gripper failed to hold the workpiece",
                "object pose is offset on the x axis",
            ],
            session.hypothesis_history,
        )
        self.assertEqual(
            [
                "SessionStarted",
                "StateTransitioned",
                "ActionPerformed",
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
                "StateTransitioned",
                "StateTransitioned",
                "StateTransitioned",
                "SessionFinished",
            ],
            [event.action_type for event in session.trace],
        )
        self.assertTrue(all(event.tutor_hint is None for event in session.trace))


if __name__ == "__main__":
    unittest.main()
