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
        for name in (
            "auth-user.schema.json",
            "auth-session.schema.json",
            "auth-register-request.schema.json",
            "auth-login-request.schema.json",
        ):
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
        for username in ("", "   ", "ab", "a" * 33, "bad.name", " user"):
            self.assertFalse(validator.is_valid({**value, "username": username}))
        for display_name in ("A\u0080B", "A\u0085B", "A\u009fB"):
            with self.subTest(display_name=display_name):
                self.assertFalse(validator.is_valid({**value, "display_name": display_name}))

    def test_registration_request_boundaries_and_defaults(self) -> None:
        validator = Draft202012Validator(self.load("auth-register-request.schema.json"))
        valid = {"username": "学员-A", "password": "correct horse 1"}
        validator.validate(valid)
        validator.validate(
            {**valid, "username": "a" * 32, "password": "p" * 128, "display_name": "Learner One"}
        )

        invalid_values = (
            {**valid, "username": "ab"},
            {**valid, "username": "a" * 33},
            {**valid, "username": " learner"},
            {**valid, "username": "learner "},
            {**valid, "username": "learner.name"},
            {**valid, "password": "p" * 14},
            {**valid, "password": "p" * 129},
            {**valid, "display_name": ""},
            {**valid, "display_name": "   "},
            {**valid, "display_name": " Learner"},
            {**valid, "display_name": "Learner\n"},
            {**valid, "display_name": "A\u0080B"},
            {**valid, "display_name": "A\u0085B"},
            {**valid, "display_name": "A\u009fB"},
            {**valid, "display_name": None},
            {**valid, "unexpected": True},
            {"username": "learner01"},
        )
        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))

    def test_login_request_is_strict_but_accepts_historical_password_lengths(self) -> None:
        validator = Draft202012Validator(self.load("auth-login-request.schema.json"))
        validator.validate({"username": "Learner-01", "password": "x"})
        validator.validate({"username": "Learner-01", "password": "x" * 128})

        invalid_values = (
            {"username": "Learner-01", "password": ""},
            {"username": "Learner-01", "password": "x" * 129},
            {"username": " Learner-01", "password": "secret"},
            {"username": "Learner.01", "password": "secret"},
            {"username": "Learner-01", "password": "secret", "display_name": "No"},
            {"password": "secret"},
        )
        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))

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
