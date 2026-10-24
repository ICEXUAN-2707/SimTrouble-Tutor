from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

from apps.training_api.auth.models import AuthSessionV05, AuthUserV05

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "v0.5"


class AuthContractTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))

    def test_contract_package_has_valid_draft_2020_12_schemas(self) -> None:
        for name in ("auth-user.schema.json", "auth-session.schema.json"):
            Draft202012Validator.check_schema(self.load(name))

    def test_auth_user_public_shape_is_strict(self) -> None:
        schema = self.load("auth-user.schema.json")
        validator = Draft202012Validator(schema)
        value = {
            "user_id": "e3f7df35-43b4-4598-aadc-25a957c6f6ef",
            "username": "learner01",
            "display_name": "Learner",
        }
        validator.validate(value)
        self.assertFalse(validator.is_valid({**value, "password": "secret"}))

    def test_auth_session_references_only_public_identity(self) -> None:
        user_schema = self.load("auth-user.schema.json")
        session_schema = self.load("auth-session.schema.json")
        resolver = RefResolver.from_schema(
            session_schema,
            store={user_schema["$id"]: user_schema, "auth-user.schema.json": user_schema},
        )
        validator = Draft202012Validator(session_schema, resolver=resolver)
        runtime = AuthSessionV05(
            user=AuthUserV05(
                user_id="e3f7df35-43b4-4598-aadc-25a957c6f6ef",
                username="learner01",
                display_name="Learner",
            ),
            expires_at=1_800_000_000,
            csrf_token="x" * 32,
        )
        validator.validate(runtime.model_dump(mode="json"))


if __name__ == "__main__":
    unittest.main()
