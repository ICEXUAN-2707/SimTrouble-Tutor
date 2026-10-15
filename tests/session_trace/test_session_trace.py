from __future__ import annotations

import itertools
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.case_engine import CaseLoader, CaseSession
from core.errors import InvalidStateTransitionError
from core.models.contracts import DiagnosticStage


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"
APPROVED_PATH = tuple(DiagnosticStage)
APPROVED_EDGES = dict(zip(APPROVED_PATH[:-1], APPROVED_PATH[1:], strict=True))


def without_trace(value: dict) -> dict:
    result = dict(value)
    result.pop("trace")
    return result


class SessionTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = CaseLoader().load(CASE_PATH)

    def build_session(
        self,
        *,
        stage: DiagnosticStage = DiagnosticStage.START,
        clock=None,
    ) -> CaseSession:
        session = CaseSession(
            user_id="trace-test-user",
            case=self.case,
            session_id=f"trace-{stage.value.lower()}",
            clock=clock,
        )
        for target in APPROVED_PATH[1 : APPROVED_PATH.index(stage) + 1]:
            session.transition_to(target)
        return session

    def test_new_session_appends_exact_session_started_event(self) -> None:
        session = self.build_session().session

        self.assertEqual(1, len(session.trace))
        event = session.trace[0]
        self.assertIs(DiagnosticStage.START, event.stage)
        self.assertEqual("SessionStarted", event.action_type)
        self.assertIsNone(event.evidence_id)
        self.assertIsNone(event.current_hypothesis)
        self.assertIsNone(event.tutor_hint)
        self.assertEqual({"status": "started"}, event.result)
        self.assertIsNotNone(event.timestamp.tzinfo)
        self.assertEqual(timedelta(0), event.timestamp.utcoffset())

    def test_complete_path_has_exact_order_and_result_shapes(self) -> None:
        aggregate = self.build_session()
        for target in APPROVED_PATH[1:]:
            aggregate.transition_to(target)

        trace = aggregate.session.trace
        self.assertEqual(10, len(trace))
        self.assertEqual("SessionStarted", trace[0].action_type)
        for index, (source, target) in enumerate(APPROVED_EDGES.items(), start=1):
            event = trace[index]
            self.assertEqual("StateTransitioned", event.action_type)
            self.assertIs(target, event.stage)
            self.assertEqual(
                {
                    "status": "accepted",
                    "from_stage": source.value,
                    "to_stage": target.value,
                },
                event.result,
            )
        self.assertEqual("SessionFinished", trace[-1].action_type)
        self.assertIs(DiagnosticStage.FINISH, trace[-1].stage)
        self.assertEqual({"status": "finished"}, trace[-1].result)

    def test_all_73_rejected_pairs_append_only_rejection_event(self) -> None:
        denied_count = 0
        for source, target in itertools.product(DiagnosticStage, repeat=2):
            if APPROVED_EDGES.get(source) is target:
                continue
            denied_count += 1
            with self.subTest(source=source, target=target):
                aggregate = self.build_session(stage=source)
                before = aggregate.session.model_dump(mode="json")

                with self.assertRaises(InvalidStateTransitionError):
                    aggregate.transition_to(target)

                after = aggregate.session.model_dump(mode="json")
                self.assertEqual(without_trace(before), without_trace(after))
                self.assertEqual(len(before["trace"]) + 1, len(after["trace"]))
                rejected = after["trace"][-1]
                self.assertEqual("StateTransitionRejected", rejected["action_type"])
                self.assertEqual(source.value, rejected["stage"])
                self.assertEqual(
                    {
                        "status": "rejected",
                        "from_stage": source.value,
                        "requested_stage": target.value,
                        "reason": "illegal_transition",
                    },
                    rejected["result"],
                )

        self.assertEqual(73, denied_count)

    def test_trace_snapshot_cannot_rewrite_authoritative_history(self) -> None:
        aggregate = self.build_session()
        aggregate.transition_to(DiagnosticStage.OBSERVE)
        expected = aggregate.session.model_dump(mode="json")["trace"]

        snapshot = aggregate.session
        snapshot.trace[0].result["status"] = "rewritten"
        snapshot.trace.reverse()
        snapshot.trace.pop()

        self.assertEqual(
            expected,
            aggregate.session.model_dump(mode="json")["trace"],
        )

    def test_transition_captures_current_hypothesis_snapshot(self) -> None:
        aggregate = self.build_session()
        aggregate.submit_hypothesis("object pose mismatch")

        aggregate.transition_to(DiagnosticStage.OBSERVE)

        event = aggregate.session.trace[-1]
        self.assertEqual("object pose mismatch", event.current_hypothesis)
        self.assertIsNone(event.evidence_id)
        self.assertIsNone(event.tutor_hint)

    def test_injected_clock_is_deterministic_and_normalized_to_utc(self) -> None:
        plus_eight = timezone(timedelta(hours=8))
        supplied = iter(
            [
                datetime(2026, 10, 7, 8, 0, tzinfo=plus_eight),
                datetime(2026, 10, 7, 8, 1, tzinfo=plus_eight),
            ]
        )
        aggregate = self.build_session(clock=supplied.__next__)
        aggregate.transition_to(DiagnosticStage.OBSERVE)

        timestamps = [event.timestamp for event in aggregate.session.trace]
        self.assertEqual(
            [
                datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 10, 7, 0, 1, tzinfo=timezone.utc),
            ],
            timestamps,
        )

    def test_invalid_transition_clock_failure_preserves_authoritative_session(self) -> None:
        calls = iter(
            [
                datetime(2026, 10, 7, tzinfo=timezone.utc),
                datetime(2026, 10, 7),
            ]
        )
        aggregate = self.build_session(clock=calls.__next__)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(ValueError):
            aggregate.transition_to(DiagnosticStage.FINISH)

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))

    def test_legal_transition_clock_failure_preserves_authoritative_session(self) -> None:
        calls = 0

        def clock() -> datetime:
            nonlocal calls
            calls += 1
            if calls == 1:
                return datetime(2026, 10, 7, tzinfo=timezone.utc)
            raise RuntimeError("clock failed")

        aggregate = self.build_session(clock=clock)
        before = aggregate.session.model_dump(mode="json")

        with self.assertRaises(RuntimeError):
            aggregate.transition_to(DiagnosticStage.OBSERVE)

        self.assertEqual(before, aggregate.session.model_dump(mode="json"))

    def test_trace_uses_only_approved_vocabulary_and_public_safe_results(self) -> None:
        aggregate = self.build_session()
        aggregate.transition_to(DiagnosticStage.OBSERVE)
        with self.assertRaises(InvalidStateTransitionError):
            aggregate.transition_to(DiagnosticStage.FINISH)

        serialized = json.dumps(
            [event.model_dump(mode="json") for event in aggregate.session.trace],
            ensure_ascii=False,
        )
        action_types = {event.action_type for event in aggregate.session.trace}
        self.assertLessEqual(
            action_types,
            {
                "SessionStarted",
                "StateTransitioned",
                "StateTransitionRejected",
                "SessionFinished",
            },
        )
        for forbidden in (
            "ground_truth",
            "optimal_path",
            "scoring_rules",
            "related_faults",
            "information_value",
            "object_pose_mismatch",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
