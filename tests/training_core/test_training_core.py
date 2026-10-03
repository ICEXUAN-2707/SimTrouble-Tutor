from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from core.case_engine import CaseLoader, CaseSession
from core.errors import (
    DuplicateIdentifierError,
    EvidenceNotFoundError,
    MissingReferenceError,
)
from core.evidence_engine import EvidenceManager
from core.models import (
    CasePublicState,
    Device,
    LearnerAction,
    LearnerProfile,
    LearnerSession,
    SkillScores,
    TrainingCase,
    TrainingModule,
)
from core.models.contracts import DiagnosticStage
from core.training_engine import ProgressManager, TrainingModuleLoader


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"
MODULE_DIR = ROOT / "data" / "modules"
DEVICE_PATH = ROOT / "data" / "devices" / "DEV-IR-FH-001.json"
SCHEMA_DIR = ROOT / "contracts" / "schemas"


class LoaderTests(unittest.TestCase):
    def test_case_and_module_catalogs_load(self) -> None:
        cases = CaseLoader().load_directory(CASE_PATH.parent)
        modules = TrainingModuleLoader().load_directory(
            MODULE_DIR, known_case_ids=set(cases)
        )
        self.assertEqual({"ST-001"}, set(cases))
        self.assertEqual({"MOD-BASIC", "MOD-EXCEPTION"}, set(modules))

    def test_duplicate_identifiers_are_rejected(self) -> None:
        with self.assertRaises(DuplicateIdentifierError):
            CaseLoader().load_many([CASE_PATH, CASE_PATH])
        module_path = MODULE_DIR / "MOD-EXCEPTION.json"
        with self.assertRaises(DuplicateIdentifierError):
            TrainingModuleLoader().load_many([module_path, module_path])

    def test_missing_case_reference_is_rejected(self) -> None:
        with self.assertRaises(MissingReferenceError):
            TrainingModuleLoader().load_directory(MODULE_DIR, known_case_ids=set())

    def test_unexpected_case_field_is_rejected(self) -> None:
        payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
        payload["unfrozen_feature"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                CaseLoader().load(path)

    def test_duplicate_evidence_ids_are_rejected(self) -> None:
        payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(payload["evidence"][0])
        duplicate["type"] = "different-content-same-id"
        payload["evidence"].append(duplicate)
        with self.assertRaises(ValidationError):
            TrainingCase.model_validate_json(json.dumps(payload))


class SessionAndEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = CaseLoader().load(CASE_PATH)
        self.case_session = CaseSession(
            user_id="user-001", case=self.case, session_id="session-001"
        )

    def test_new_session_matches_frozen_defaults(self) -> None:
        session = self.case_session.session
        self.assertEqual(DiagnosticStage.START, session.current_stage)
        self.assertEqual([], session.evidence_seen)
        self.assertIsNone(session.current_hypothesis)
        self.assertEqual([], session.hypothesis_history)
        self.assertEqual([], session.actions)
        self.assertEqual(SkillScores.zero(), session.skill_scores)
        self.assertEqual([], session.trace)

    def test_public_case_has_exact_public_contract_fields(self) -> None:
        public = self.case_session.public_case_state()
        schema = json.loads(
            (SCHEMA_DIR / "case-public.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(schema["properties"]), set(public.model_dump(mode="json")))
        serialized = public.model_dump_json()
        for forbidden in (
            "fault",
            "ground_truth",
            "optimal_path",
            "scoring_rules",
            "related_faults",
            "information_value",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_authoritative_case_is_isolated_from_external_mutation(self) -> None:
        self.case.initial_state["external_mutation"] = True
        first_copy = self.case_session.authoritative_case
        self.assertNotIn("external_mutation", first_copy.initial_state)
        first_copy.initial_state["copy_mutation"] = True
        self.assertNotIn(
            "copy_mutation", self.case_session.authoritative_case.initial_state
        )

    def test_action_and_hypothesis_update_session_without_stage_change(self) -> None:
        parameters = {"target": "workpiece"}
        action = LearnerAction(action_type="inspect", parameters=parameters)
        self.case_session.record_action(action)
        parameters["target"] = "changed"
        action.parameters["target"] = "also-changed"
        self.case_session.submit_hypothesis("  object pose mismatch  ")

        session = self.case_session.session
        self.assertEqual("workpiece", session.actions[0].parameters["target"])
        self.assertEqual("object pose mismatch", session.current_hypothesis)
        self.assertEqual(["object pose mismatch"], session.hypothesis_history)
        self.assertEqual(DiagnosticStage.START, session.current_stage)

    def test_empty_hypothesis_is_rejected_without_mutation(self) -> None:
        with self.assertRaises(ValueError):
            self.case_session.submit_hypothesis("   ")
        self.assertIsNone(self.case_session.session.current_hypothesis)
        self.assertEqual([], self.case_session.session.hypothesis_history)

    def test_evidence_release_strips_internal_metadata_and_is_idempotent(self) -> None:
        manager = EvidenceManager()
        released = manager.request(self.case_session, "E02")
        self.assertEqual({"id", "type", "content"}, set(type(released).model_fields))
        self.assertFalse(hasattr(released, "related_faults"))
        self.assertFalse(hasattr(released, "information_value"))
        manager.request(self.case_session, "E02")
        self.assertEqual(["E02"], self.case_session.session.evidence_seen)

    def test_unknown_evidence_does_not_mutate_session(self) -> None:
        before = copy.deepcopy(self.case_session.session.model_dump(mode="json"))
        with self.assertRaises(EvidenceNotFoundError):
            EvidenceManager().request(self.case_session, "UNKNOWN")
        self.assertEqual(before, self.case_session.session.model_dump(mode="json"))


class ProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.modules = tuple(
            TrainingModuleLoader()
            .load_directory(MODULE_DIR, known_case_ids={"ST-001"})
            .values()
        )
        case = CaseLoader().load(CASE_PATH)
        self.finished = CaseSession(
            user_id="user-001", case=case, session_id="finished"
        ).session
        self.finished.current_stage = DiagnosticStage.FINISH

    def test_empty_history_returns_zero_profile_without_recommendation(self) -> None:
        profile = ProgressManager().build_profile(
            user_id="user-001", modules=self.modules, sessions=[]
        )
        self.assertEqual(SkillScores.zero(), profile.skill_scores)
        self.assertIsNone(profile.recommended_case_id)
        self.assertTrue(
            all(not progress.completed_case_ids for progress in profile.module_progress)
        )

    def test_finished_sessions_are_grouped_without_duplicate_cases(self) -> None:
        profile = ProgressManager().build_profile(
            user_id="user-001",
            modules=self.modules,
            sessions=[self.finished, self.finished],
            skill_scores=SkillScores(
                hypothesis=70, evidence=80, efficiency=60, updating=75, safety=90
            ),
            recommended_case_id="ST-001",
        )
        exception_progress = next(
            item for item in profile.module_progress if item.module_id == "MOD-EXCEPTION"
        )
        self.assertEqual(("ST-001",), exception_progress.completed_case_ids)
        self.assertEqual("ST-001", profile.recommended_case_id)

    def test_other_users_and_unfinished_sessions_do_not_count(self) -> None:
        other = self.finished.model_copy(deep=True)
        other.user_id = "user-002"
        unfinished = self.finished.model_copy(deep=True)
        unfinished.current_stage = DiagnosticStage.OBSERVE
        profile = ProgressManager().build_profile(
            user_id="user-001", modules=self.modules, sessions=[other, unfinished]
        )
        self.assertTrue(
            all(not progress.completed_case_ids for progress in profile.module_progress)
        )

    def test_unknown_recommendation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProgressManager().build_profile(
                user_id="user-001",
                modules=self.modules,
                sessions=[],
                recommended_case_id="ST-999",
            )

    def test_duplicate_module_inputs_are_rejected(self) -> None:
        with self.assertRaises(DuplicateIdentifierError):
            ProgressManager().build_profile(
                user_id="user-001",
                modules=[self.modules[0], self.modules[0]],
                sessions=[],
            )


class ModelParityTests(unittest.TestCase):
    def test_runtime_models_have_same_top_level_fields_as_contracts(self) -> None:
        mapping = {
            Device: "device.schema.json",
            TrainingModule: "training-module.schema.json",
            TrainingCase: "case.schema.json",
            CasePublicState: "case-public.schema.json",
            LearnerSession: "learner-session.schema.json",
            LearnerProfile: "learner-profile.schema.json",
        }
        for model, schema_name in mapping.items():
            with self.subTest(model=model.__name__):
                schema = json.loads(
                    (SCHEMA_DIR / schema_name).read_text(encoding="utf-8")
                )
                self.assertEqual(set(schema["properties"]), set(model.model_fields))

    def test_device_data_loads_and_invalid_component_set_fails(self) -> None:
        device = Device.model_validate_json(DEVICE_PATH.read_text(encoding="utf-8"))
        self.assertEqual("DEV-IR-FH-001", device.device_id)
        payload = device.model_dump(mode="json")
        payload["components"] = ["robot_arm"] * 5
        with self.assertRaises(ValidationError):
            Device.model_validate(payload)

    def test_core_has_no_out_of_scope_framework_imports(self) -> None:
        forbidden = (
            "fastapi",
            "sqlalchemy",
            "langgraph",
            "openai",
            "isaacsim",
            "rclpy",
            "gazebo",
        )
        for path in (ROOT / "core").rglob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            for package in forbidden:
                with self.subTest(path=path.name, package=package):
                    self.assertNotRegex(
                        source,
                        rf"(?:^|\n)\s*(?:from|import)\s+{re.escape(package)}\b",
                    )


if __name__ == "__main__":
    unittest.main()
