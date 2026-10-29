from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.errors import EvidenceNotFoundError
from core.models import LearnerAction


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"
NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


class CommandTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = CaseLoader().load(CASE_PATH)

    def build_session(self, clock=None) -> CaseSession:
        return CaseSession(
            user_id="command-trace-user",
            case=self.case,
            session_id="command-trace-session",
            clock=clock,
        )

    def test_action_records_one_public_safe_event(self) -> None:
        aggregate = self.build_session()
        aggregate.record_action(
            LearnerAction(
                action_type="inspect",
                parameters={"target": "workpiece", "private_note": "do-not-copy"},
            )
        )

        session = aggregate.session
        event = session.trace[-1]
        self.assertEqual("ActionPerformed", event.action_type)
        self.assertEqual({"status": "recorded"}, event.result)
        self.assertIsNone(event.evidence_id)
        self.assertNotIn(
            "do-not-copy",
            json.dumps(event.model_dump(mode="json"), ensure_ascii=False),
        )

    def test_first_and_later_hypotheses_use_exact_events(self) -> None:
        aggregate = self.build_session()

        aggregate.submit_hypothesis("grasp failure")
        aggregate.submit_hypothesis("object pose mismatch")

        session = aggregate.session
        self.assertEqual(
            ["HypothesisAdded", "HypothesisUpdated"],
            [event.action_type for event in session.trace[-2:]],
        )
        self.assertEqual("grasp failure", session.trace[-2].current_hypothesis)
        self.assertEqual("object pose mismatch", session.trace[-1].current_hypothesis)
        self.assertTrue(
            all(event.result == {"status": "recorded"} for event in session.trace[-2:])
        )

    def test_evidence_success_and_denial_use_exact_order_and_results(self) -> None:
        aggregate = self.build_session()
        manager = EvidenceManager()

        released = manager.request(aggregate, "E02")
        with self.assertRaises(EvidenceNotFoundError):
            manager.request(aggregate, "UNKNOWN")

        self.assertEqual("E02", released.id)
        events = aggregate.session.trace[-4:]
        self.assertEqual(
            [
                "EvidenceRequested",
                "EvidenceReleased",
                "EvidenceRequested",
                "EvidenceDenied",
            ],
            [event.action_type for event in events],
        )
        self.assertEqual({"status": "requested"}, events[0].result)
        self.assertEqual({"status": "released"}, events[1].result)
        self.assertEqual({"status": "requested"}, events[2].result)
        self.assertEqual(
            {"status": "denied", "reason": "evidence_not_found"},
            events[3].result,
        )
        self.assertEqual(["E02"], aggregate.session.evidence_seen)
        serialized = json.dumps(
            [event.model_dump(mode="json") for event in events],
            ensure_ascii=False,
        )
        for forbidden in (
            "offset_mm",
            "related_faults",
            "information_value",
            "ground_truth",
            "optimal_path",
            "scoring_rules",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_action_clock_failure_is_atomic(self) -> None:
        calls = iter([NOW, datetime(2026, 10, 8)])
        aggregate = self.build_session(clock=calls.__next__)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(ValueError):
            aggregate.record_action(
                LearnerAction(action_type="inspect", parameters={"target": "workpiece"})
            )

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))

    def test_hypothesis_clock_failure_is_atomic(self) -> None:
        calls = iter([NOW, datetime(2026, 10, 8)])
        aggregate = self.build_session(clock=calls.__next__)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(ValueError):
            aggregate.submit_hypothesis("object pose mismatch")

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))

    def test_rejected_hypothesis_clock_failure_is_atomic(self) -> None:
        calls = iter([NOW, datetime(2026, 10, 8)])
        aggregate = self.build_session(clock=calls.__next__)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(ValueError):
            aggregate.submit_hypothesis("   ")

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))

    def test_evidence_second_event_clock_failure_is_atomic(self) -> None:
        calls = iter([NOW, NOW, datetime(2026, 10, 8)])
        aggregate = self.build_session(clock=calls.__next__)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(ValueError):
            EvidenceManager().request(aggregate, "E02")

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))

    def test_denied_evidence_second_event_clock_failure_is_atomic(self) -> None:
        calls = iter([NOW, NOW, datetime(2026, 10, 8)])
        aggregate = self.build_session(clock=calls.__next__)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(ValueError):
            EvidenceManager().request(aggregate, "UNKNOWN")

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))


if __name__ == "__main__":
    unittest.main()
