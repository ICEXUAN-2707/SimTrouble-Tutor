from __future__ import annotations

import itertools
import unittest
from pathlib import Path

from core.case_engine import CaseLoader, CaseSession
from core.errors import InvalidStateTransitionError, TrainingCoreError
from core.evidence_engine import EvidenceManager
from core.models import LearnerAction, LearnerSession, SkillScores
from core.models.contracts import DiagnosticStage
from core.state_machine import DiagnosticStateMachine


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"

APPROVED_PATH = (
    DiagnosticStage.START,
    DiagnosticStage.OBSERVE,
    DiagnosticStage.INVESTIGATE,
    DiagnosticStage.HYPOTHESIZE,
    DiagnosticStage.TEST,
    DiagnosticStage.UPDATE,
    DiagnosticStage.DIAGNOSE,
    DiagnosticStage.REFLECT,
    DiagnosticStage.FINISH,
)
APPROVED_EDGES = dict(zip(APPROVED_PATH[:-1], APPROVED_PATH[1:], strict=True))


def build_session(stage: DiagnosticStage) -> LearnerSession:
    return LearnerSession(
        session_id=f"state-machine-{stage.value.lower()}",
        case_id="ST-001",
        user_id="state-machine-test-user",
        current_stage=stage,
        evidence_seen=[],
        current_hypothesis=None,
        hypothesis_history=[],
        actions=[],
        hint_count=0,
        wrong_branch_count=0,
        skill_scores=SkillScores.zero(),
        trace=[],
    )


class DiagnosticStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = DiagnosticStateMachine()
        case = CaseLoader().load(CASE_PATH)
        self.case_session = CaseSession(
            user_id="state-machine-test-user",
            case=case,
            session_id="aggregate-state-machine",
        )

    def test_every_approved_edge_changes_only_stage(self) -> None:
        for source, target in APPROVED_EDGES.items():
            with self.subTest(source=source, target=target):
                session = build_session(source)
                expected = session.model_dump(mode="json")
                expected["current_stage"] = target.value

                self.machine.transition(session, target)

                self.assertEqual(expected, session.model_dump(mode="json"))
                self.assertEqual([], session.trace)

    def test_all_73_unapproved_pairs_are_rejected_without_mutation(self) -> None:
        denied_count = 0
        for source, target in itertools.product(DiagnosticStage, repeat=2):
            if APPROVED_EDGES.get(source) is target:
                continue
            denied_count += 1
            with self.subTest(source=source, target=target):
                session = build_session(source)
                before = session.model_dump(mode="json")

                with self.assertRaises(InvalidStateTransitionError):
                    self.machine.transition(session, target)

                self.assertEqual(before, session.model_dump(mode="json"))

        self.assertEqual(73, denied_count)
        self.assertTrue(issubclass(InvalidStateTransitionError, TrainingCoreError))

    def test_case_session_executes_the_complete_explicit_path(self) -> None:
        for target in APPROVED_PATH[1:]:
            self.case_session.transition_to(target)
            snapshot = self.case_session.session
            self.assertIs(target, snapshot.current_stage)
            self.assertEqual([], snapshot.trace)

    def test_rejected_aggregate_transition_is_atomic(self) -> None:
        before = self.case_session.session.model_dump(mode="json")

        with self.assertRaises(InvalidStateTransitionError):
            self.case_session.transition_to(DiagnosticStage.FINISH)

        self.assertEqual(before, self.case_session.session.model_dump(mode="json"))

    def test_existing_commands_never_advance_stage(self) -> None:
        EvidenceManager().request(self.case_session, "E02")
        self.case_session.submit_hypothesis("pose mismatch")
        self.case_session.record_action(
            LearnerAction(action_type="inspect", parameters={"target": "workpiece"})
        )

        self.assertIs(DiagnosticStage.START, self.case_session.session.current_stage)

    def test_public_snapshot_cannot_bypass_state_machine(self) -> None:
        snapshot = self.case_session.session
        snapshot.current_stage = DiagnosticStage.FINISH

        self.assertIs(DiagnosticStage.START, self.case_session.session.current_stage)
        self.case_session.transition_to(DiagnosticStage.OBSERVE)
        self.assertIs(DiagnosticStage.OBSERVE, self.case_session.session.current_stage)

    def test_finish_is_terminal_through_the_aggregate(self) -> None:
        for target in APPROVED_PATH[1:]:
            self.case_session.transition_to(target)

        for target in DiagnosticStage:
            with self.subTest(target=target):
                before = self.case_session.session.model_dump(mode="json")
                with self.assertRaises(InvalidStateTransitionError):
                    self.case_session.transition_to(target)
                self.assertEqual(
                    before,
                    self.case_session.session.model_dump(mode="json"),
                )
