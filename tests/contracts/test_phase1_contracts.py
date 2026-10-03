from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "contracts" / "schemas"
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"


class ContractValidationError(AssertionError):
    pass


class SchemaSet:
    """Small Draft 2020-12 subset validator for the keywords used in Phase 1.

    This is contract-test support, not a product validation engine. Runtime schema
    validation technology is intentionally left to a later implementation spec.
    """

    def __init__(self) -> None:
        self.schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in SCHEMA_DIR.glob("*.schema.json")
        }

    def validate(self, instance: Any, schema_name: str) -> None:
        self._validate(instance, self.schemas[schema_name], schema_name, "$")

    def _resolve(self, ref: str, current_name: str) -> tuple[dict[str, Any], str]:
        if ref.startswith("#"):
            file_name, pointer = current_name, ref[1:]
        else:
            file_part, marker, fragment = ref.partition("#")
            file_name = Path(file_part).name
            pointer = fragment if marker else ""

        target: Any = self.schemas[file_name]
        if pointer:
            if not pointer.startswith("/"):
                raise ContractValidationError(f"Unsupported JSON pointer in {ref}")
            for token in pointer[1:].split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                target = target[token]
        return target, file_name

    @staticmethod
    def _is_type(value: Any, expected: str) -> bool:
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }
        return checks[expected](value)

    def _validate(
        self,
        instance: Any,
        schema: dict[str, Any],
        current_name: str,
        path: str,
    ) -> None:
        if "$ref" in schema:
            target, target_name = self._resolve(schema["$ref"], current_name)
            self._validate(instance, target, target_name, path)
            return

        if "const" in schema and instance != schema["const"]:
            raise ContractValidationError(f"{path}: expected const {schema['const']!r}")
        if "enum" in schema and instance not in schema["enum"]:
            raise ContractValidationError(f"{path}: {instance!r} is not in enum")

        expected_type = schema.get("type")
        if expected_type is not None:
            accepted = expected_type if isinstance(expected_type, list) else [expected_type]
            if not any(self._is_type(instance, item) for item in accepted):
                raise ContractValidationError(f"{path}: invalid type")

        if isinstance(instance, str):
            if len(instance) < schema.get("minLength", 0):
                raise ContractValidationError(f"{path}: string is too short")
            if "pattern" in schema and re.search(schema["pattern"], instance) is None:
                raise ContractValidationError(f"{path}: pattern mismatch")

        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                raise ContractValidationError(f"{path}: below minimum")
            if "maximum" in schema and instance > schema["maximum"]:
                raise ContractValidationError(f"{path}: above maximum")

        if isinstance(instance, list):
            if len(instance) < schema.get("minItems", 0):
                raise ContractValidationError(f"{path}: too few items")
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                raise ContractValidationError(f"{path}: too many items")
            if schema.get("uniqueItems"):
                normalized = [json.dumps(item, sort_keys=True) for item in instance]
                if len(normalized) != len(set(normalized)):
                    raise ContractValidationError(f"{path}: duplicate items")
            if "items" in schema:
                for index, item in enumerate(instance):
                    self._validate(item, schema["items"], current_name, f"{path}[{index}]")

        if isinstance(instance, dict):
            required = schema.get("required", [])
            missing = [key for key in required if key not in instance]
            if missing:
                raise ContractValidationError(f"{path}: missing {missing}")
            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False:
                extra = sorted(set(instance) - set(properties))
                if extra:
                    raise ContractValidationError(f"{path}: unexpected {extra}")
            for key, value in instance.items():
                if key in properties:
                    self._validate(value, properties[key], current_name, f"{path}.{key}")


class Phase1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema_set = SchemaSet()
        cls.case = json.loads(CASE_PATH.read_text(encoding="utf-8"))

    def test_expected_schema_set_exists_and_uses_one_draft(self) -> None:
        expected = {
            "action.schema.json",
            "device.schema.json",
            "training-module.schema.json",
            "case.schema.json",
            "case-public.schema.json",
            "evidence-public.schema.json",
            "learner-profile.schema.json",
            "learner-session.schema.json",
            "skill.schema.json",
            "training-report.schema.json",
            "tutor-context.schema.json",
            "tutor-response.schema.json",
        }
        self.assertEqual(expected, set(self.schema_set.schemas))
        for schema in self.schema_set.schemas.values():
            self.assertEqual(
                "https://json-schema.org/draft/2020-12/schema", schema["$schema"]
            )
            self.assertEqual("object", schema["type"])
            self.assertFalse(schema["additionalProperties"])

    def test_schema_examples_are_valid(self) -> None:
        for name in (
            "device.schema.json",
            "training-module.schema.json",
            "skill.schema.json",
        ):
            for example in self.schema_set.schemas[name].get("examples", []):
                self.schema_set.validate(example, name)

    def test_frozen_enums_and_dimensions_are_exact(self) -> None:
        self.assertEqual(
            {
                "object_pose_offset",
                "grasp_failure",
                "obstacle_collision_risk",
                "placement_target_conflict",
            },
            set(
                self.schema_set.schemas["case.schema.json"]["$defs"]["faultType"][
                    "enum"
                ]
            ),
        )
        self.assertEqual(
            [
                "START",
                "OBSERVE",
                "INVESTIGATE",
                "HYPOTHESIZE",
                "TEST",
                "UPDATE",
                "DIAGNOSE",
                "REFLECT",
                "FINISH",
            ],
            self.schema_set.schemas["learner-session.schema.json"]["$defs"][
                "stage"
            ]["enum"],
        )
        self.assertEqual(
            {"hypothesis", "evidence", "efficiency", "updating", "safety"},
            set(self.schema_set.schemas["skill.schema.json"]["required"]),
        )
        self.assertEqual(
            {"question", "hint", "explain", "reflect"},
            set(
                self.schema_set.schemas["tutor-response.schema.json"]["properties"][
                    "intent"
                ]["enum"]
            ),
        )

    def test_st001_matches_authoritative_case_schema(self) -> None:
        self.schema_set.validate(self.case, "case.schema.json")
        self.assertEqual("object_pose_offset", self.case["fault"]["type"])
        self.assertEqual("object_pose_mismatch", self.case["ground_truth"]["diagnosis"])

    def test_authoritative_case_rejects_unfrozen_top_level_fields(self) -> None:
        invalid = copy.deepcopy(self.case)
        invalid["auto_generated_explanation"] = "out of scope"
        with self.assertRaises(ContractValidationError):
            self.schema_set.validate(invalid, "case.schema.json")

    def test_public_case_projection_excludes_hidden_fields(self) -> None:
        allowed = set(
            self.schema_set.schemas["case-public.schema.json"]["properties"]
        )
        public_case = {key: value for key, value in self.case.items() if key in allowed}
        public_case["evidence_options"] = [
            {"id": item["id"], "type": item["type"]}
            for item in self.case["evidence"]
        ]
        self.schema_set.validate(public_case, "case-public.schema.json")
        for forbidden in (
            "fault",
            "evidence",
            "ground_truth",
            "optimal_path",
            "scoring_rules",
            "initial_state",
        ):
            invalid = copy.deepcopy(public_case)
            invalid[forbidden] = self.case[forbidden]
            with self.assertRaises(ContractValidationError):
                self.schema_set.validate(invalid, "case-public.schema.json")

    def test_session_and_tutor_contracts_validate_minimal_examples(self) -> None:
        scores = {
            "hypothesis": 0,
            "evidence": 0,
            "efficiency": 0,
            "updating": 0,
            "safety": 0,
        }
        session = {
            "session_id": "session-001",
            "case_id": "ST-001",
            "user_id": "user-001",
            "current_stage": "START",
            "evidence_seen": [],
            "current_hypothesis": None,
            "hypothesis_history": [],
            "actions": [],
            "hint_count": 0,
            "wrong_branch_count": 0,
            "skill_scores": scores,
            "trace": [],
        }
        self.schema_set.validate(session, "learner-session.schema.json")

        module = self.schema_set.schemas["training-module.schema.json"]["examples"][0]
        public_properties = self.schema_set.schemas["case-public.schema.json"]["properties"]
        public_case = {
            key: value for key, value in self.case.items() if key in public_properties
        }
        public_case["evidence_options"] = [
            {"id": item["id"], "type": item["type"]}
            for item in self.case["evidence"]
        ]
        released_evidence = {
            key: value
            for key, value in self.case["evidence"][0].items()
            if key in {"id", "type", "content"}
        }
        context = {
            "training_module": module,
            "case_public_state": public_case,
            "evidence_seen": [released_evidence],
            "learner_action_history": [],
            "current_hypothesis": None,
            "current_skill_profile": scores,
            "allowed_tutor_actions": ["question", "hint"],
        }
        self.schema_set.validate(context, "tutor-context.schema.json")

        leaked_evidence = copy.deepcopy(context)
        leaked_evidence["evidence_seen"][0]["related_faults"] = ["object_pose_offset"]
        with self.assertRaises(ContractValidationError):
            self.schema_set.validate(leaked_evidence, "tutor-context.schema.json")

        leaked = copy.deepcopy(context)
        leaked["ground_truth"] = self.case["ground_truth"]
        with self.assertRaises(ContractValidationError):
            self.schema_set.validate(leaked, "tutor-context.schema.json")

        response = {
            "intent": "question",
            "message": "你目前有哪些可验证的观察？",
            "suggested_next_step": None,
        }
        self.schema_set.validate(response, "tutor-response.schema.json")

        report = {
            "session_id": "session-001",
            "case_id": "ST-001",
            "ground_truth": self.case["ground_truth"],
            "learner_path": [],
            "recommended_path": self.case["optimal_path"],
            "skill_scores": scores,
            "tutor_reflection": None,
            "next_case_id": None,
        }
        self.schema_set.validate(report, "training-report.schema.json")

        profile = {
            "user_id": "user-001",
            "module_progress": [
                {
                    "module_id": "MOD-EXCEPTION",
                    "completed_case_ids": ["ST-001"],
                    "total_case_count": 1,
                }
            ],
            "skill_scores": scores,
            "recommended_case_id": None,
        }
        self.schema_set.validate(profile, "learner-profile.schema.json")

    def test_api_and_adapter_contracts_keep_frozen_surface(self) -> None:
        api_text = (ROOT / "contracts" / "api-contract.md").read_text(encoding="utf-8")
        routes = re.findall(r"\| (GET|POST) \| `([^`]+)` \|", api_text)
        self.assertEqual(11, len(routes))
        self.assertEqual(11, len(set(routes)))

        adapter_text = (ROOT / "contracts" / "simulation-adapter-contract.md").read_text(
            encoding="utf-8"
        )
        methods = set(re.findall(r"def ([a-z_]+)\(", adapter_text))
        self.assertEqual(
            {
                "reset_scenario",
                "get_state",
                "perform_action",
                "get_evidence",
                "inject_fault",
                "get_result",
            },
            methods,
        )

    def test_workspace_has_one_governance_source(self) -> None:
        self.assertTrue((ROOT / "SimTrouble_FreezePack_v0.2").is_dir())
        self.assertFalse((ROOT / "simtrouble_codex_handoff").exists())
        self.assertFalse((ROOT / "参赛详情.txt").exists())
        self.assertFalse((ROOT / "方案——仿真运维培训Agent.txt").exists())
        self.assertTrue((ROOT / "docs" / "product" / "参赛详情.txt").is_file())
        self.assertTrue(
            (ROOT / "docs" / "product" / "方案——仿真运维培训Agent.txt").is_file()
        )


if __name__ == "__main__":
    unittest.main()
